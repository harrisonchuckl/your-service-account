# src/config.py
import os

def _int(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None:
        return default
    val = str(val).strip()
    try:
        return int(val)
    except Exception:
        return default

def _str(name: str, default: str) -> str:
    val = os.getenv(name)
    if val is None:
        return default
    val = str(val).strip()
    return val or default

# ===== Public config used by other modules =====
DEFAULT_LOCATION = _str("DEFAULT_LOCATION", "Ely")

# How many sheet rows to process per run
MAX_ROWS = _int("MAX_ROWS", 40)

# Crawl tuning
CRAWL_MAX_PAGES_PER_SITE = _int("CRAWL_MAX_PAGES_PER_SITE", 20)
CRAWL_TIMEOUT_SECS       = _int("CRAWL_TIMEOUT_SECS", 12)

# Google Custom Search (CSE)
GOOGLE_CSE_KEY           = _str("GOOGLE_CSE_KEY", "")
GOOGLE_CSE_CX            = _str("GOOGLE_CSE_CX", "")
GOOGLE_CSE_QPS_DELAY_MS  = _int("GOOGLE_CSE_QPS_DELAY_MS", 500)  # 0.5s between calls
GOOGLE_CSE_MAX_RETRIES   = _int("GOOGLE_CSE_MAX_RETRIES", 4)     # backoff attempts

# Known “bad” hosts we don’t want as company sites
BAD_HOSTS = {
    "facebook.com", "www.facebook.com",
    "twitter.com", "x.com", "www.twitter.com", "www.x.com",
    "linkedin.com", "www.linkedin.com",
    "instagram.com", "www.instagram.com",
    "youtube.com", "www.youtube.com",
    "yelp.com", "www.yelp.com",
    "uk.linkedin.com", "en-gb.facebook.com",
    "m.facebook.com", "mobile.twitter.com",
}

# Sheet tab default (still overridable via env)
SHEET_TAB = _str("SHEET_TAB", "Sheet1")
