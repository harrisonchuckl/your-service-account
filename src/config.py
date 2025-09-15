# src/config.py
from __future__ import annotations
import os, re

def _getstr(name: str, default: str) -> str:
    v = os.getenv(name)
    return default if v is None or v == "" else v

def _getint(name: str, default: int) -> int:
    v = os.getenv(name)
    try:
        return int(v) if v not in (None, "") else int(default)
    except Exception:
        return int(default)

def _getbool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    v = v.strip().lower()
    return v in ("1", "true", "t", "yes", "y", "on")

# ===== Global toggles =====
FAST_MODE = _getbool("FAST_MODE", True)   # <— turn fast mode on by default

# ===== Sheets / general =====
GOOGLE_SA_JSON_B64 = _getstr("GOOGLE_SA_JSON_B64", "")
SHEET_ID           = _getstr("SHEET_ID", "")
SHEET_TAB          = _getstr("SHEET_TAB", "Sheet1")
DEFAULT_LOCATION   = _getstr("DEFAULT_LOCATION", "Ely")
MAX_ROWS           = _getint("MAX_ROWS", 100)

# ===== HTTP / crawling =====
USER_AGENT   = _getstr("USER_AGENT", "Mozilla/5.0 (compatible; ContactCrawler/1.0; +https://example.com/bot)")
# Fast, separate connect/read timeouts help avoid hanging hosts
CONNECT_TIMEOUT = _getint("CONNECT_TIMEOUT", 5 if FAST_MODE else 8)
READ_TIMEOUT    = _getint("READ_TIMEOUT",    7 if FAST_MODE else 12)
HTTP_TIMEOUT    = (CONNECT_TIMEOUT, READ_TIMEOUT)
TIMEOUT         = READ_TIMEOUT  # back-compat alias

# throttle & budgets
FETCH_DELAY_MS      = _getint("FETCH_DELAY_MS",       120 if FAST_MODE else 250)
MAX_PAGES_PER_SITE  = _getint("MAX_PAGES_PER_SITE",   8   if FAST_MODE else 14)
MIN_PAGES_BEFORE_FALLBACK = _getint("MIN_PAGES_BEFORE_FALLBACK", 3 if FAST_MODE else 8)
SITE_BUDGET_SECONDS = _getint("SITE_BUDGET_SECONDS",  20  if FAST_MODE else 60)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Cache-Control": "no-cache",
}

# prioritised paths (you asked to exclude privacy/legal)
CONTACT_PATHS = [
    r"/contact([-/]|$)",
    r"/contact-us",
    r"/get[-_]?in[-_]?touch",
    r"/support",
    r"/help",
    r"/about",
    r"/impressum",
    r"/company/contact",
]

CONTACT_KEYWORDS = ["contact", "enquire", "inquiry", "get in touch", "email us"]

BAD_EXTENSIONS = [
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
    ".zip", ".rar", ".7z"
]
BAD_PATH_SNIPPETS = ["/wp-content/", "/static/", "/assets/", "/uploads/", "/media/"]

# ===== Email / form extraction =====
EMAIL_RE  = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,24}", re.IGNORECASE)
MAILTO_RE = re.compile(r'href=["\']mailto:([^"\']+)["\']', re.IGNORECASE)

CONTACT_FORM_HINTS       = ["wpcf7", "wpforms", "hs-form", "hubspot", "formspree", "gravityforms", "contact-form"]
FORM_REQUIRE_FIELDS_ANY  = ["email"]
FORM_REQUIRE_FIELDS_ALL  = ["message"]

PREFER_COMPANY_DOMAIN = _getbool("PREFER_COMPANY_DOMAIN", True)
EMAIL_GUESS_ENABLE    = _getbool("EMAIL_GUESS_ENABLE", False)  # <— stay False so we don’t guess
GENERIC_GUESS_PREFIXES = ["info"]  # kept for completeness
GUESS_GENERICS = GENERIC_GUESS_PREFIXES  # alias

# ===== Search (Google CSE / Bing) =====
GOOGLE_CSE_KEY          = _getstr("GOOGLE_CSE_KEY", "")
GOOGLE_CSE_CX           = _getstr("GOOGLE_CSE_CX", "")
GOOGLE_CSE_QPS_DELAY_MS = _getint("GOOGLE_CSE_QPS_DELAY_MS", 600 if FAST_MODE else 800)
GOOGLE_CSE_MAX_RETRIES  = _getint("GOOGLE_CSE_MAX_RETRIES",  2   if FAST_MODE else 4)
MAX_GOOGLE_CANDIDATES   = _getint("MAX_GOOGLE_CANDIDATES",   3   if FAST_MODE else 4)
BING_API_KEY            = _getstr("BING_API_KEY", "")

# Downrank/noise hosts (added Amazon + Opentable + Ubuy etc.)
BAD_HOSTS = [
    "facebook.com", "linkedin.com", "twitter.com", "x.com", "instagram.com", "youtube.com",
    "wikipedia.org", "reddit.com", "medium.com", "blogspot.com", "wordpress.com",
    "typepad.com", "pinterest.com", "foursquare.com", "yelp.com",
    "fda.gov", "opentable.com",
    "amazon.com", "amazon.co.uk", "aws.amazon.com",
    "ubuy.com", "tumblr.com",
]

# ===== ScraperAPI (optional) =====
SCRAPERAPI_KEY     = _getstr("SCRAPERAPI_KEY", "")
SCRAPERAPI_BASE    = _getstr("SCRAPERAPI_BASE", "https://api.scraperapi.com")
SCRAPERAPI_COUNTRY = _getstr("SCRAPERAPI_COUNTRY", "")
SCRAPERAPI_RENDER  = _getbool("SCRAPERAPI_RENDER", False)
