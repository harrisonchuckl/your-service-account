# src/config.py
from __future__ import annotations

import os
import re

# ----------------------------
# Helpers to read environment
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
# General / sheet settings
# ----------------------------

GOOGLE_SA_JSON_B64 = _getstr("GOOGLE_SA_JSON_B64", "")
SHEET_ID           = _getstr("SHEET_ID", "")
SHEET_TAB          = _getstr("SHEET_TAB", "Sheet1")
DEFAULT_LOCATION   = _getstr("DEFAULT_LOCATION", "Ely")
MAX_ROWS           = _getint("MAX_ROWS", 100)

# ----------------------------
# HTTP / crawl settings
# ----------------------------

USER_AGENT            = _getstr("USER_AGENT", "Mozilla/5.0 (compatible; ContactCrawler/1.0; +https://example.com/bot)")
HTTP_TIMEOUT          = _getint("HTTP_TIMEOUT", 15)         # seconds per request
FETCH_DELAY_MS        = _getint("FETCH_DELAY_MS", 400)      # polite delay between fetches
MAX_PAGES_PER_SITE    = _getint("MAX_PAGES_PER_SITE", 40)   # hard cap per domain
MIN_PAGES_BEFORE_FALLBACK = _getint("MIN_PAGES_BEFORE_FALLBACK", 6)  # try at least this many pages before using Google fallback
SITE_BUDGET_SECONDS   = _getint("SITE_BUDGET_SECONDS", 25)  # per-site time budget

# Back-compat alias some code may import
TIMEOUT = HTTP_TIMEOUT

# Paths/keywords to prioritise while crawling
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

CONTACT_FORM_HINTS     = ["wpcf7", "wpforms", "hs-form", "hubspot", "formspree", "gravityforms", "contact-form"]
FORM_REQUIRE_FIELDS_ANY = ["email"]
FORM_REQUIRE_FIELDS_ALL = ["message"]  # matched via id/name/placeholder/label text

# Behaviour toggles
PREFER_COMPANY_DOMAIN  = _getbool("PREFER_COMPANY_DOMAIN", True)
EMAIL_GUESS_ENABLE     = _getbool("EMAIL_GUESS_ENABLE", False)  # keep False to avoid guesses

GENERIC_GUESS_PREFIXES = ["info"]  # very conservative if guessing is ever enabled
# Back-compat alias if older modules import this name
GUESS_GENERICS = GENERIC_GUESS_PREFIXES

# ----------------------------
# Search (Google CSE / Bing)
# ----------------------------

GOOGLE_CSE_KEY            = _getstr("GOOGLE_CSE_KEY", "")
GOOGLE_CSE_CX             = _getstr("GOOGLE_CSE_CX", "")
GOOGLE_CSE_QPS_DELAY_MS   = _getint("GOOGLE_CSE_QPS_DELAY_MS", 800)
GOOGLE_CSE_MAX_RETRIES    = _getint("GOOGLE_CSE_MAX_RETRIES", 5)
MAX_GOOGLE_CANDIDATES     = _getint("MAX_GOOGLE_CANDIDATES", 4)

BING_API_KEY              = _getstr("BING_API_KEY", "")

# Filter out generic/low-signal hosts when evaluating search candidates
BAD_HOSTS = [
    "facebook.com", "linkedin.com", "twitter.com", "x.com", "instagram.com", "youtube.com",
    "wikipedia.org", "reddit.com", "medium.com", "blogspot.com", "wordpress.com",
    "typepad.com", "pinterest.com", "foursquare.com", "yelp.com",
    "fda.gov", "opentable.com", "amazon.com", "amazon.co.uk", "aws.amazon.com",
    "ubuy.com", "tumblr.com"
]

# ----------------------------
# ScraperAPI (optional)
# ----------------------------

SCRAPERAPI_KEY     = _getstr("SCRAPERAPI_KEY", "")
SCRAPERAPI_BASE    = _getstr("SCRAPERAPI_BASE", "https://api.scraperapi.com")
SCRAPERAPI_COUNTRY = _getstr("SCRAPERAPI_COUNTRY", "")   # e.g., "uk", "us"
SCRAPERAPI_RENDER  = _getbool("SCRAPERAPI_RENDER", False)
