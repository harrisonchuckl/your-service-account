# src/config.py
from __future__ import annotations
import os, re

# ----------------------------
# Helpers
# ----------------------------
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

# ----------------------------
# Sheet / general
# ----------------------------
GOOGLE_SA_JSON_B64 = _getstr("GOOGLE_SA_JSON_B64", "")
SHEET_ID           = _getstr("SHEET_ID", "")
SHEET_TAB          = _getstr("SHEET_TAB", "Sheet1")
DEFAULT_LOCATION   = _getstr("DEFAULT_LOCATION", "Ely")
MAX_ROWS           = _getint("MAX_ROWS", 100)

# ----------------------------
# HTTP / crawling
# ----------------------------
USER_AGENT             = _getstr("USER_AGENT", "Mozilla/5.0 (compatible; ContactCrawler/1.0; +https://example.com/bot)")
HTTP_TIMEOUT           = _getint("HTTP_TIMEOUT", 15)       # seconds per request
FETCH_DELAY_MS         = _getint("FETCH_DELAY_MS", 400)    # polite delay between fetches
MAX_PAGES_PER_SITE     = _getint("MAX_PAGES_PER_SITE", 40)
MIN_PAGES_BEFORE_FALLBACK = _getint("MIN_PAGES_BEFORE_FALLBACK", 6)
SITE_BUDGET_SECONDS    = _getint("SITE_BUDGET_SECONDS", 25)

# Some modules still import TIMEOUT
TIMEOUT = HTTP_TIMEOUT

# Requests headers (fixes ImportError: HEADERS)
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Cache-Control": "no-cache",
}

# Prioritised paths (privacy/legal removed per your tweak)
CONTACT_PATHS = [
    r"/contact([-/]|$)",
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

# ----------------------------
# Email / form extraction
# ----------------------------
EMAIL_RE  = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,24}", re.IGNORECASE)
MAILTO_RE = re.compile(r'href=["\']mailto:([^"\']+)["\']', re.IGNORECASE)

CONTACT_FORM_HINTS       = ["wpcf7", "wpforms", "hs-form", "hubspot", "formspree", "gravityforms", "contact-form"]
FORM_REQUIRE_FIELDS_ANY  = ["email"]
FORM_REQUIRE_FIELDS_ALL  = ["message"]

PREFER_COMPANY_DOMAIN = _getbool("PREFER_COMPANY_DOMAIN", True)
EMAIL_GUESS_ENABLE    = _getbool("EMAIL_GUESS_ENABLE", False)  # keep False to avoid guessed addresses
GENERIC_GUESS_PREFIXES = ["info"]
GUESS_GENERICS = GENERIC_GUESS_PREFIXES  # back-compat alias

# ----------------------------
# Search (Google CSE / Bing)
# ----------------------------
GOOGLE_CSE_KEY            = _getstr("GOOGLE_CSE_KEY", "")
GOOGLE_CSE_CX             = _getstr("GOOGLE_CSE_CX", "")
GOOGLE_CSE_QPS_DELAY_MS   = _getint("GOOGLE_CSE_QPS_DELAY_MS", 800)
GOOGLE_CSE_MAX_RETRIES    = _getint("GOOGLE_CSE_MAX_RETRIES", 5)
MAX_GOOGLE_CANDIDATES     = _getint("MAX_GOOGLE_CANDIDATES", 4)

BING_API_KEY              = _getstr("BING_API_KEY", "")

# Exclude generic/low-signal hosts
BAD_HOSTS = [
    "facebook.com", "linkedin.com", "twitter.com", "x.com", "instagram.com", "youtube.com",
    "wikipedia.org", "reddit.com", "medium.com", "blogspot.com", "wordpress.com",
    "typepad.com", "pinterest.com", "foursquare.com", "yelp.com",
    "fda.gov", "opentable.com",
    "amazon.com", "amazon.co.uk", "aws.amazon.com",
    "ubuy.com", "tumblr.com",
]

# ----------------------------
# ScraperAPI (optional)
# ----------------------------
SCRAPERAPI_KEY     = _getstr("SCRAPERAPI_KEY", "")
SCRAPERAPI_BASE    = _getstr("SCRAPERAPI_BASE", "https://api.scraperapi.com")
SCRAPERAPI_COUNTRY = _getstr("SCRAPERAPI_COUNTRY", "")
SCRAPERAPI_RENDER  = _getbool("SCRAPERAPI_RENDER", False)
