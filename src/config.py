# src/config.py
from __future__ import annotations
import os
from typing import List

# ---------------------------
# Env helpers
# ---------------------------
def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default)

def _getint(name: str, default: str) -> int:
    raw = _get(name, default).strip()
    try:
        return int(raw if raw != "" else default)
    except Exception:
        return int(default)

def _getbool(name: str, default: str = "false") -> bool:
    return _get(name, default).strip().lower() in {"1", "true", "yes", "on"}

# ---------------------------
# Core (Sheets & Google CSE)
# ---------------------------
GOOGLE_SA_JSON_B64 = _get("GOOGLE_SA_JSON_B64", "")
SHEET_ID           = _get("SHEET_ID", "")
SHEET_TAB          = _get("SHEET_TAB", "Sheet1")
DEFAULT_LOCATION   = _get("DEFAULT_LOCATION", "Ely")
MAX_ROWS           = _getint("MAX_ROWS", "100")

GOOGLE_CSE_KEY           = _get("GOOGLE_CSE_KEY", "")
GOOGLE_CSE_CX            = _get("GOOGLE_CSE_CX", "")
GOOGLE_CSE_QPS_DELAY_MS  = _getint("GOOGLE_CSE_QPS_DELAY_MS", "800")
GOOGLE_CSE_MAX_RETRIES   = _getint("GOOGLE_CSE_MAX_RETRIES", "5")
MAX_GOOGLE_CANDIDATES    = _getint("MAX_GOOGLE_CANDIDATES", "6")

# ---------------------------
# HTTP / crawling
# ---------------------------
HTTP_TIMEOUT     = _getint("HTTP_TIMEOUT", "20")   # seconds
TIMEOUT          = HTTP_TIMEOUT                    # legacy alias
FETCH_DELAY_MS   = _getint("FETCH_DELAY_MS", "300")
FETCH_MAX_PAGES  = _getint("FETCH_MAX_PAGES", "40")
MAX_CONTACT_PAGES = _getint("MAX_CONTACT_PAGES", "20")

# Optional proxy / rendering
SCRAPERAPI_KEY    = _get("SCRAPERAPI_KEY", "")
SCRAPERAPI_BASE   = _get("SCRAPERAPI_BASE", "https://api.scraperapi.com/")
SCRAPERAPI_RENDER = _getbool("SCRAPERAPI_RENDER", "false")

# ---------------------------
# Heuristics & preferences
# ---------------------------
PREFER_COMPANY_DOMAIN = _getbool("PREFER_COMPANY_DOMAIN", "true")

# Turn on ONLY if you want to guess info@ / hello@, etc.
GUESS_GENERICS = _getbool("GUESS_GENERICS", "false")
_DEFAULT_GUESS_PREFIXES: List[str] = [
    "info", "hello", "contact", "sales", "enquiries", "enquiry", "admin"
]
GENERIC_GUESS_PREFIXES: List[str] = _DEFAULT_GUESS_PREFIXES if GUESS_GENERICS else []

# Likely contact-ish paths to probe on a site
CONTACT_PATHS: List[str] = [
    "contact", "contact-us", "contactus", "get-in-touch", "getintouch",
    "support", "help", "privacy", "imprint", "impressum", "about", "team",
    "where-to-find-us", "find-us"
]

# Deprioritize / skip these hosts from results
BAD_HOSTS: List[str] = [
    # social / platforms
    "facebook.com", "linkedin.com", "twitter.com", "x.com", "instagram.com",
    "youtube.com", "tiktok.com", "pinterest.com", "yelp.com", "foursquare.com",
    "medium.com", "blogspot.com", "wordpress.com", "typepad.com", "reddit.com",
    "wikipedia.org",

    # marketplaces / aggregators / portals
    "amazon.com", "amazon.co.uk", "opentable.com", "ubuy.com",
    "tripadvisor.com", "tripadvisor.co.uk",

    # large gov / non-local portals that drown out SMEs
    "fda.gov",
]

# ---------------------------
# Headers / UA
# ---------------------------
USER_AGENT = _get("USER_AGENT", "Mozilla/5.0 (compatible; ChucklScraper/1.0; +https://example.com/bot)")
HEADERS = {"User-Agent": USER_AGENT}

# ---------------------------
# Backward-compat aliases
# ---------------------------
# Some modules import these legacy names:
MAX_PAGES_PER_SITE = FETCH_MAX_PAGES
REQUEST_HEADERS    = HEADERS
