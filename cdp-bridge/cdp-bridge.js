/**
 * QUANT CDP Bridge — Connects to TradingView Desktop App via Chrome DevTools Protocol
 * 
 * Provides an Express REST API for the Python backend to:
 *   - Extract live OHLCV data from the chart
 *   - Change symbol and timeframe
 *   - Export historical chart data
 *   - Take chart screenshots
 *   - Read indicator/study values
 */

const WebSocket = require('ws');
const http = require('http');
const express = require('express');
const cors = require('cors');

const CDP_PORT = process.env.CDP_PORT || 9222;
const API_PORT = process.env.API_PORT || 3001;

// ─── CDP Connection Manager ───────────────────────────────────────────────────

class CDPConnection {
  constructor(port) {
    this.port = port;
    this.ws = null;
    this.msgId = 1;
    this.pendingCallbacks = new Map();
    this.connected = false;
    this.chartPageId = null;
  }

  // HTTP GET helper
  _httpGet(path) {
    return new Promise((resolve, reject) => {
      http.get(`http://localhost:${this.port}${path}`, (res) => {
        let data = '';
        res.on('data', (c) => (data += c));
        res.on('end', () => {
          try { resolve(JSON.parse(data)); }
          catch (e) { reject(new Error(`Failed to parse response: ${data.substring(0, 200)}`)); }
        });
      }).on('error', reject);
    });
  }

  // Find the TradingView chart page target
  async findChartTarget() {
    const targets = await this._httpGet('/json/list');
    const chart = targets.find((t) => t.url && t.url.includes('/chart/'));
    if (!chart) throw new Error('No TradingView chart page found. Is TradingView open with a chart?');
    this.chartPageId = chart.id;
    return chart;
  }

  // Connect WebSocket to the chart page
  async connect() {
    if (this.connected && this.ws?.readyState === WebSocket.OPEN) return;

    const target = await this.findChartTarget();
    console.log(`[CDP] Connecting to chart: ${target.url}`);

    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(target.webSocketDebuggerUrl, {
        perMessageDeflate: false,
        maxPayload: 256 * 1024 * 1024,
        handshakeTimeout: 10000,
      });

      this.ws.on('open', async () => {
        this.connected = true;
        console.log('[CDP] WebSocket connected!');
        try {
          await this.send('Runtime.enable');
          console.log('[CDP] Runtime domain enabled');
          resolve();
        } catch (e) {
          reject(e);
        }
      });

      this.ws.on('message', (raw) => {
        const msg = JSON.parse(raw.toString());
        if (msg.id && this.pendingCallbacks.has(msg.id)) {
          const { resolve, reject, timer } = this.pendingCallbacks.get(msg.id);
          clearTimeout(timer);
          this.pendingCallbacks.delete(msg.id);
          if (msg.error) reject(new Error(JSON.stringify(msg.error)));
          else resolve(msg.result);
        }
      });

      this.ws.on('close', () => {
        this.connected = false;
        console.log('[CDP] WebSocket closed');
      });

      this.ws.on('error', (err) => {
        this.connected = false;
        console.error('[CDP] WebSocket error:', err.message);
        reject(err);
      });

      setTimeout(() => {
        if (!this.connected) reject(new Error('WebSocket connection timeout'));
      }, 12000);
    });
  }

  // Send a CDP command
  send(method, params = {}, timeout = 15000) {
    return new Promise((resolve, reject) => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        return reject(new Error('WebSocket not connected'));
      }
      const id = this.msgId++;
      const timer = setTimeout(() => {
        this.pendingCallbacks.delete(id);
        reject(new Error(`CDP timeout for ${method}`));
      }, timeout);

      this.pendingCallbacks.set(id, { resolve, reject, timer });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  // Execute JavaScript in the TradingView page context
  async evaluate(expression, awaitPromise = false) {
    const result = await this.send('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise,
    });
    if (result?.result?.value !== undefined) return result.result.value;
    if (result?.exceptionDetails) {
      throw new Error(`JS Error: ${JSON.stringify(result.exceptionDetails)}`);
    }
    return result;
  }

  // Evaluate and parse JSON result
  async evaluateJSON(expression, awaitPromise = false) {
    const raw = await this.evaluate(expression, awaitPromise);
    if (typeof raw === 'string') return JSON.parse(raw);
    return raw;
  }

  async disconnect() {
    if (this.ws) {
      this.ws.close();
      this.connected = false;
    }
  }
}

// ─── TradingView Data Extractor ───────────────────────────────────────────────

class TVDataExtractor {
  constructor(cdp) {
    this.cdp = cdp;
  }

  // Ensure connected
  async ensureConnected() {
    if (!this.cdp.connected) await this.cdp.connect();
  }

  // Extract current OHLCV + metadata from the chart legend
  async extractCurrentOHLCV() {
    await this.ensureConnected();
    return this.cdp.evaluateJSON(`
      (function() {
        const result = { timestamp: Date.now() };

        // Parse legend text: "O64,153.80H64,158.56L64,141.06C64,142.15"
        const legendEls = document.querySelectorAll('[class*="valuesWrapper"]');
        let legendText = '';
        legendEls.forEach(el => { legendText += el.textContent || ''; });

        // Extract OHLCV from legend
        const oMatch = legendText.match(/O([\\d,]+\\.\\d+)/);
        const hMatch = legendText.match(/H([\\d,]+\\.\\d+)/);
        const lMatch = legendText.match(/L([\\d,]+\\.\\d+)/);
        const cMatch = legendText.match(/C([\\d,]+\\.\\d+)/);
        const volMatch = legendText.match(/Vol[^\\d]*([\\d,]+\\.?\\d*)/);

        const parseNum = (s) => s ? parseFloat(s.replace(/,/g, '')) : null;

        result.open = parseNum(oMatch?.[1]);
        result.high = parseNum(hMatch?.[1]);
        result.low = parseNum(lMatch?.[1]);
        result.close = parseNum(cMatch?.[1]);
        result.volume = parseNum(volMatch?.[1]);

        // Extract change info
        const changeMatch = legendText.match(/([+−-][\\d,]+\\.\\d+)\\s*\\(([+−-]?[\\d.]+)%\\)/);
        if (changeMatch) {
          result.change = parseNum(changeMatch[1].replace('−', '-'));
          result.changePercent = parseFloat(changeMatch[2].replace('−', '-'));
        }

        // Get symbol info from the legend
        const symbolMatch = legendText.match(/^([A-Z].*?\\/.*?)\\d/);
        result.legendRaw = legendText.substring(0, 200);

        return JSON.stringify(result);
      })()
    `);
  }

  // Extract symbol info
  async extractSymbolInfo() {
    await this.ensureConnected();
    return this.cdp.evaluateJSON(`
      (function() {
        const title = document.title;
        // Title format: "BTCUSD 64,142.15 ▲ +0.02% — Bitcoin / US Dollar ..."
        const parts = title.split('—');
        const priceMatch = title.match(/([\\d,]+\\.\\d+)/);
        const changeMatch = title.match(/([▲▼])\\s*([+−-]?[\\d.]+%)/);

        return JSON.stringify({
          fullTitle: title,
          symbolName: parts.length > 1 ? parts[1].trim().split(' on ')[0] : title,
          currentPrice: priceMatch ? parseFloat(priceMatch[1].replace(/,/g, '')) : null,
          direction: changeMatch ? (changeMatch[1] === '▲' ? 'up' : 'down') : null,
          changePercent: changeMatch ? changeMatch[2] : null,
        });
      })()
    `);
  }

  // Get all visible price levels from the chart
  async extractVisiblePrices() {
    await this.ensureConnected();
    return this.cdp.evaluateJSON(`
      (function() {
        const priceRegex = /^[\\d,]+\\.\\d{2,8}$/;
        const prices = [];
        document.querySelectorAll('div, span').forEach(el => {
          if (el.children.length === 0) {
            const t = (el.textContent || '').trim();
            if (priceRegex.test(t) && prices.length < 30) {
              prices.push(parseFloat(t.replace(/,/g, '')));
            }
          }
        });
        // Deduplicate and sort
        const unique = [...new Set(prices)].sort((a, b) => b - a);
        return JSON.stringify(unique);
      })()
    `);
  }

  // Change the chart symbol
  async changeSymbol(symbol) {
    await this.ensureConnected();
    return this.cdp.evaluateJSON(`
      (function() {
        try {
          const col = _exposed_chartWidgetCollection;
          if (col && col.setSymbol) {
            col.setSymbol('${symbol}');
            return JSON.stringify({ success: true, symbol: '${symbol}' });
          }
          return JSON.stringify({ success: false, error: 'setSymbol not available' });
        } catch(e) {
          return JSON.stringify({ success: false, error: e.message });
        }
      })()
    `);
  }

  // Change the chart timeframe/resolution
  async changeTimeframe(resolution) {
    await this.ensureConnected();
    return this.cdp.evaluateJSON(`
      (function() {
        try {
          const col = _exposed_chartWidgetCollection;
          if (col && col.setResolution) {
            col.setResolution('${resolution}');
            return JSON.stringify({ success: true, resolution: '${resolution}' });
          }
          return JSON.stringify({ success: false, error: 'setResolution not available' });
        } catch(e) {
          return JSON.stringify({ success: false, error: e.message });
        }
      })()
    `);
  }

  // Export full chart data (historical OHLCV) via the widget collection
  async exportChartData() {
    await this.ensureConnected();
    return this.cdp.evaluateJSON(`
      new Promise((resolve) => {
        try {
          const col = _exposed_chartWidgetCollection;
          const widget = col.activeChartWidget || col.getAll()[0];
          if (!widget) {
            resolve(JSON.stringify({ error: 'No active chart widget' }));
            return;
          }
          
          const model = widget.model ? widget.model() : widget;
          const mainSeries = model.mainSeries ? model.mainSeries() : null;
          
          if (mainSeries && mainSeries.bars) {
            const barsObj = mainSeries.bars();
            const data = [];
            
            if (barsObj && barsObj.size) {
              // Try to iterate the bars
              const first = barsObj.firstIndex ? barsObj.firstIndex() : 0;
              const last = barsObj.lastIndex ? barsObj.lastIndex() : barsObj.size() - 1;
              
              for (let i = first; i <= last && data.length < 5000; i++) {
                const bar = barsObj.valueAt ? barsObj.valueAt(i) : null;
                if (bar) {
                  data.push({
                    time: bar[0] || bar.time,
                    open: bar[1] || bar.open,
                    high: bar[2] || bar.high,
                    low: bar[3] || bar.low,
                    close: bar[4] || bar.close,
                    volume: bar[5] || bar.volume
                  });
                }
              }
            }
            
            resolve(JSON.stringify({ 
              bars: data, 
              count: data.length,
              source: 'mainSeries.bars'
            }));
          } else {
            // Fallback: try exportData on active chart widget methods
            const proto = Object.getOwnPropertyNames(Object.getPrototypeOf(widget));
            resolve(JSON.stringify({ 
              error: 'Could not access mainSeries.bars',
              widgetMethods: proto.slice(0, 40),
              hasModel: !!model,
              hasMainSeries: !!mainSeries,
              mainSeriesKeys: mainSeries ? Object.keys(mainSeries).slice(0, 20) : []
            }));
          }
        } catch(e) {
          resolve(JSON.stringify({ error: e.message, stack: e.stack?.substring(0, 300) }));
        }
      })
    `, true);
  }

  // Take a screenshot of the chart
  async takeScreenshot() {
    await this.ensureConnected();
    const result = await this.cdp.send('Page.captureScreenshot', {
      format: 'png',
      quality: 90,
    });
    return result.data; // base64 encoded PNG
  }

  // Get chart state (symbol, timeframe, studies, etc.)
  async getChartState() {
    await this.ensureConnected();
    return this.cdp.evaluateJSON(`
      (function() {
        try {
          const col = _exposed_chartWidgetCollection;
          const state = col.state ? col.state() : null;
          const widgets = col.getAll ? col.getAll() : [];
          
          return JSON.stringify({
            widgetCount: widgets.length,
            layoutType: col._layoutType,
            hasState: !!state,
            stateKeys: state ? Object.keys(state).slice(0, 20) : [],
          });
        } catch(e) {
          return JSON.stringify({ error: e.message });
        }
      })()
    `);
  }

  // Get available window API keys for exploration
  async getAvailableAPIs() {
    await this.ensureConnected();
    return this.cdp.evaluateJSON(`
      (function() {
        return JSON.stringify({
          chartKeys: Object.keys(window).filter(k => /chart|trading|widget|datafeed|tv/i.test(k)),
          globals: {
            TradingView: typeof TradingView,
            ChartApiInstance: typeof ChartApiInstance,
            TradingViewApi: typeof TradingViewApi,
            _exposed_chartWidgetCollection: typeof _exposed_chartWidgetCollection,
            TVSettings: typeof TVSettings,
            widgetbar: typeof widgetbar,
          }
        });
      })()
    `);
  }
}

// ─── Express API Server ───────────────────────────────────────────────────────

async function startServer() {
  const cdp = new CDPConnection(CDP_PORT);
  const extractor = new TVDataExtractor(cdp);
  const app = express();

  app.use(cors());
  app.use(express.json());

  // Health check
  app.get('/health', async (req, res) => {
    try {
      await extractor.ensureConnected();
      res.json({ status: 'ok', connected: cdp.connected, chartPageId: cdp.chartPageId });
    } catch (e) {
      res.status(503).json({ status: 'error', message: e.message });
    }
  });

  // Get current OHLCV from the chart
  app.get('/extract/ohlcv', async (req, res) => {
    try {
      const data = await extractor.extractCurrentOHLCV();
      res.json(data);
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  // Get symbol info
  app.get('/extract/symbol', async (req, res) => {
    try {
      const data = await extractor.extractSymbolInfo();
      res.json(data);
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  // Get visible price levels
  app.get('/extract/prices', async (req, res) => {
    try {
      const data = await extractor.extractVisiblePrices();
      res.json(data);
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  // Export full chart data (historical OHLCV)
  app.get('/extract/history', async (req, res) => {
    try {
      const data = await extractor.exportChartData();
      res.json(data);
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  // Change symbol
  app.post('/control/symbol', async (req, res) => {
    const { symbol } = req.body;
    if (!symbol) return res.status(400).json({ error: 'symbol is required' });
    try {
      const result = await extractor.changeSymbol(symbol);
      res.json(result);
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  // Change timeframe
  app.post('/control/timeframe', async (req, res) => {
    const { resolution } = req.body;
    if (!resolution) return res.status(400).json({ error: 'resolution is required (e.g., "1", "5", "60", "D", "W")' });
    try {
      const result = await extractor.changeTimeframe(resolution);
      res.json(result);
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  // Take screenshot
  app.get('/extract/screenshot', async (req, res) => {
    try {
      const base64 = await extractor.takeScreenshot();
      res.json({ image: base64 });
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  // Chart state
  app.get('/extract/state', async (req, res) => {
    try {
      const data = await extractor.getChartState();
      res.json(data);
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  // Available APIs
  app.get('/extract/apis', async (req, res) => {
    try {
      const data = await extractor.getAvailableAPIs();
      res.json(data);
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  app.listen(API_PORT, () => {
    console.log(`\n🚀 QUANT CDP Bridge running at http://localhost:${API_PORT}`);
    console.log(`   Connecting to TradingView CDP at port ${CDP_PORT}\n`);
    console.log('   Endpoints:');
    console.log('   GET  /health           — Connection status');
    console.log('   GET  /extract/ohlcv    — Current candle OHLCV');
    console.log('   GET  /extract/symbol   — Symbol info + price');
    console.log('   GET  /extract/prices   — Visible price levels');
    console.log('   GET  /extract/history  — Historical OHLCV bars');
    console.log('   GET  /extract/state    — Chart state');
    console.log('   GET  /extract/apis     — Available APIs');
    console.log('   POST /control/symbol   — Change symbol');
    console.log('   POST /control/timeframe— Change timeframe');
    console.log('   GET  /extract/screenshot— Chart screenshot\n');
  });
}

startServer().catch(console.error);
