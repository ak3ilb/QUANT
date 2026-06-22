"""RSS news ingestion for BTC and gold headlines."""
import hashlib
import logging
from datetime import datetime, timezone

import feedparser

from intelligence.nlp.headline_tagger import tag_headline
from intelligence_store import store_headline

_log = logging.getLogger(__name__)

RSS_FEEDS = {
    "coindesk": ("https://www.coindesk.com/arc/outboundfeeds/rss/", ["BTCUSD"]),
    "cointelegraph": ("https://cointelegraph.com/rss", ["BTCUSD"]),
    "kitco": ("https://www.kitco.com/news/category/news/rss", ["XAUUSD"]),
}


def _headline_id(source: str, url: str, title: str) -> str:
    return hashlib.md5(f"{source}:{url}:{title}".encode()).hexdigest()


def fetch_rss_headlines(max_per_feed: int = 15) -> list[dict]:
    headlines = []
    for source, (url, default_symbols) in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            if getattr(feed, "bozo", False) and not feed.entries:
                _log.warning("RSS feed empty or invalid: %s (%s)", source, url)
                continue
            count = 0
            for entry in feed.entries[:max_per_feed]:
                title = entry.get("title", "").strip()
                if not title:
                    continue
                link = entry.get("link", "")
                published = entry.get("published_parsed")
                if published:
                    published_at = datetime(*published[:6], tzinfo=timezone.utc)
                else:
                    published_at = datetime.now(timezone.utc)
                symbols = tag_headline(title, default_symbols)
                hid = _headline_id(source, link, title)
                store_headline(hid, published_at, source, title, link, symbols)
                headlines.append({
                    "id": hid,
                    "published_at": published_at.isoformat(),
                    "source": source,
                    "headline": title,
                    "url": link,
                    "symbols": symbols,
                })
                count += 1
            _log.info("RSS %s: ingested %d headlines from %s", source, count, url)
        except Exception as exc:
            _log.warning("RSS fetch failed %s: %s", source, exc)
            continue
    return headlines
