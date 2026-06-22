"""Rate limiting, backoff, and retry helpers for free API fetchers."""
import random
import time
from functools import wraps

import requests

# Delays (seconds) — tune to avoid API bans
DELAY_BETWEEN_JOBS_MIN = 45
DELAY_BETWEEN_JOBS_MAX = 90
DELAY_BETWEEN_ROUNDS = 120

DELAY_BINANCE_PAGE = 0.6
DELAY_KRAKEN_PAGE = 1.2
DELAY_YFINANCE = 2.5

MAX_HTTP_RETRIES = 4
BACKOFF_BASE = 30  # seconds after rate limit


def jitter_sleep(min_s: float, max_s: float, label: str = ""):
    delay = random.uniform(min_s, max_s)
    time.sleep(delay)
    return delay


def job_delay():
    return jitter_sleep(DELAY_BETWEEN_JOBS_MIN, DELAY_BETWEEN_JOBS_MAX)


def round_delay():
    return jitter_sleep(DELAY_BETWEEN_ROUNDS, DELAY_BETWEEN_ROUNDS + 30)


def request_with_retry(url: str, params: dict | None = None, timeout: int = 30, source: str = "api") -> requests.Response:
    """GET with exponential backoff on 429/5xx."""
    last_err = None
    for attempt in range(1, MAX_HTTP_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            if resp.status_code == 429:
                wait = BACKOFF_BASE * attempt + random.uniform(0, 10)
                time.sleep(wait)
                last_err = RuntimeError(f"{source} rate limited (429), waited {wait:.0f}s")
                continue
            if resp.status_code >= 500:
                wait = 10 * attempt
                time.sleep(wait)
                last_err = RuntimeError(f"{source} HTTP {resp.status_code}")
                continue
            return resp
        except requests.RequestException as e:
            last_err = e
            time.sleep(5 * attempt)
    raise RuntimeError(f"{source} failed after {MAX_HTTP_RETRIES} retries: {last_err}")


def backoff_seconds(attempts: int) -> float:
    """Exponential backoff before retrying a failed manifest job."""
    return min(3600, BACKOFF_BASE * (2 ** max(0, attempts - 1))) + random.uniform(0, 15)
