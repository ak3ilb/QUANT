"""FinBERT + VADER ensemble sentiment (FinBERT optional if transformers installed)."""
from intelligence_store import get_recent_sentiment, store_sentiment

_vader = None
_finbert = None
_finbert_tokenizer = None
_finbert_available = None


def _get_vader():
    global _vader
    if _vader is None:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        _vader = SentimentIntensityAnalyzer()
    return _vader


def _finbert_score(text: str) -> float | None:
    global _finbert, _finbert_tokenizer, _finbert_available
    if _finbert_available is False:
        return None
    try:
        if _finbert is None:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            import torch
            _finbert_tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
            _finbert = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
            _finbert.eval()
            _finbert_available = True
        import torch
        inputs = _finbert_tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
        with torch.no_grad():
            logits = _finbert(**inputs).logits
            probs = torch.nn.functional.softmax(logits, dim=-1)[0]
        # FinBERT labels: positive, negative, neutral
        return float(probs[0] - probs[1])
    except Exception:
        _finbert_available = False
        return None


def score_headline(headline_id: str, text: str) -> dict:
    vader = _get_vader()
    vs = vader.polarity_scores(text)
    vader_score = float(vs["compound"])

    fb = _finbert_score(text)
    if fb is not None:
        ensemble = 0.5 * vader_score + 0.5 * fb
    else:
        ensemble = vader_score

    if ensemble >= 0.15:
        label = "bullish"
    elif ensemble <= -0.15:
        label = "bearish"
    else:
        label = "neutral"

    store_sentiment(headline_id, fb or 0.0, vader_score, ensemble, label)
    return {
        "finbert_score": fb,
        "vader_score": vader_score,
        "ensemble_score": ensemble,
        "label": label,
    }


def score_headlines_batch(headlines: list[dict], context: dict | None = None) -> list[dict]:
    from ai.nlp.impact_scorer import score_headline_impact

    scored = []
    for h in headlines:
        result = score_headline(h["id"], h["headline"])
        row = {**h, **result}
        score_headline_impact(
            h["id"],
            result["ensemble_score"],
            result["label"],
            h.get("symbols") or [],
            context,
        )
        scored.append(row)
    return scored


def rolling_sentiment(symbols: list[str], hours: int = 4) -> dict:
    rows = get_recent_sentiment(symbols, hours=hours)
    if not rows:
        return {"score": 0.0, "label": "neutral", "count": 0}
    scores = [r["ensemble_score"] for r in rows if r.get("ensemble_score") is not None]
    if not scores:
        return {"score": 0.0, "label": "neutral", "count": 0}
    avg = sum(scores) / len(scores)
    label = "bullish" if avg > 0.1 else ("bearish" if avg < -0.1 else "neutral")
    return {"score": float(avg), "label": label, "count": len(scores), "headlines": rows[:10]}
