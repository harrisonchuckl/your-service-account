# src/config.py
import os

def _get(name: str, default: str = "") -> str:
    v = os.getenv(name)
    if v is None:
        return default
    v = str(v).strip()
    return v if v != "" else default

def _getint(name: str, default: int) -> int:
    v = os.getenv(name)
    try:
        s = ("" if v is None else str(v).strip())
        return int(s) if s != "" else default
    except Exception:
        return default

# === Google Sheets auth ===
GOOGLE_SA_JSON_B64 = _get("GOOGLE_SA_JSON_B64")    # required
SHEET_ID            = _get("SHEET_ID")             # required
SHEET_TAB           = _get("SHEET_TAB", "Sheet1")

# === Scraper behavior ===
DEFAULT_LOCATION    = _get("DEFAULT_LOCATION", "Ely")
MAX_ROWS            = _getint("MAX_ROWS", 100)
HTTP_TIMEOUT        = _getint("HTTP_TIMEOUT", 15)
MAX_PAGES_PER_SITE  = _getint("MAX_PAGES_PER_SITE", 20)

# User-Agent used by requests
USER_AGENT = _get(
    "USER_AGENT",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# === Google Programmable Search (CSE) ===
GOOGLE_CSE_KEY             = _get("GOOGLE_CSE_KEY")   # your API key
GOOGLE_CSE_CX              = _get("GOOGLE_CSE_CX")    # your search engine ID
GOOGLE_CSE_QPS_DELAY_MS    = _getint("GOOGLE_CSE_QPS_DELAY_MS", 800)
GOOGLE_CSE_MAX_RETRIES     = _getint("GOOGLE_CSE_MAX_RETRIES", 5)

# === Optional fallbacks / proxies ===
BING_API_KEY    = _get("BING_API_KEY", "")
SCRAPERAPI_KEY  = _get("SCRAPERAPI_KEY", "")   # define this even if empty

# Hosts we don’t want to treat as “official websites”
BAD_HOSTS = {
    "facebook.com",
    "m.facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "youtube.com",
    "yelp.com",
    "wikipedia.org",
}
