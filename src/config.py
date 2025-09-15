# src/config.py
from __future__ import annotations
import os
from typing import List

def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default)

def _getint(name: str, default: str) -> int:
    try:
        return int(_get(name, default).strip() or default)
    except Exception:
        return int(default)

def _getbool(name: str, default: str = "false") -> bool:
    return (_get(name, default).strip().lower() in {"1", "true", "yes", "on"})

# === Core environment (Sheets & Google CSE) ===========================
GOOGLE_SA_JSON_B64 = _get("GOOGLE_SA_JSON_B64", "")
SHEET_ID           = _get("SHEET_ID", "")
SHEET_TAB          = _get("SHEET_TAB", "Sheet1")
DEFAULT_LOCATION   = _get("DEFAULT_LOCATION", "Ely")
MAX_ROWS           = _getint("MAX_ROWS", "100")

GOOGLE_CSE_KEY     = _get("GOOGLE_CSE_KEY", "")
GOOGLE_CSE_CX      = _get("GOOGLE_CSE_CX", "")
GOOGLE_CSE_QPS_DELAY_MS = _getint("GOOGLE_CSE_QPS_DELAY_MS", "800")
GOOGLE_CSE_MAX_RETRIES  = _getint("GOOGLE_CSE_MAX_RETRIES", "5")
MAX_GOOGLE_CANDIDATES   = _getint("MAX_GOOGLE_CANDIDATES", "6")

# === Crawl / HTTP =====================================================
HTTP_TIMEOUT   = _getint("HTTP_TIMEOUT", "20")     # seconds
TIMEOUT        = HTTP_TIMEOUT                      # backward-compat alias
FETCH_DELAY_MS = _getint("FETCH_DELAY_MS", "300")
FETCH_MAX_PAGES = _getint("FETCH_MAX_PAGES", "40")
MAX_CONTACT_PAGES = _getint("MAX_CONTACT_PAGES", "20")

# Optional proxy/render provider
SCRAPERAPI_KEY    = _get("SCRAPERAPI_KEY", "")
SCRAPERAPI_BASE   = _get("SCRAPERAPI_BASE", "https://api.scraperapi.com/")
SCRAPERAPI_RENDER = _getbool("SCRAPERAPI_RENDER", "false")

# === Heuristics & preferences =========================================
PREFER_COMPANY_DOMAIN = _getbool("PREFER_COMPANY_DOMAIN", "true")

# Turn this ON only if you want fallback guesses like info@domain.
GUESS_GENERICS = _getbool("GUESS_GENERICS", "false")

# If guessing is enabled, we’ll try these in order.
_DEFAULT_GUESS_PREFIXES: List[str] = [
    "info", "hello", "contact", "sales", "enquiries", "enquiry", "admin"
]
GENERIC_GUESS_PREFIXES: List[str] = _DEFAULT_GUESS_PREFIXES if GUESS_GENERICS else []

# Paths on a site that are likely to contain contact details
CONTACT_PATHS: List[str] = [
    "contact", "contact-us", "contactus", "get-in-touch", "getintouch",
    "support", "help", "privacy", "imprint", "impressum", "about", "team",
    "where-to-find-us", "find-us"
]

# Hosts we consider low-signal or irrelevant for outreach
BAD_HOSTS: List[str] = [
    # social / platforms
    "facebook.com", "linkedin.com", "twitter.com", "x.com", "instagram.com",
    "youtube.com", "tiktok.com", "pinterest.com", "yelp.com", "foursquare.com",
    "medium.com", "blogspot.com", "wordpress.com", "typepad.com", "reddit.com",
    "wikipedia.org",

    # marketplaces / aggregators / big portals
    "amazon.com", "amazon.co.uk", "opentable.com", "ubuy.com",
    "tripadvisor.com", "tripadvisor.co.uk",

    # very large gov / non-local portals (often drown out SMEs)
    "fda.gov",
    # add others as you see them pollute results
]

# Basic UA
USER_AGENT = _get("USER_AGENT", "Mozilla/5.0 (compatible; ChucklScraper/1.0; +https://example.com/bot)")

# Convenience for other modules
HEADERS = {"User-Agent": USER_AGENT}
