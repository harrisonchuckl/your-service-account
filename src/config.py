# src/config.py
from __future__ import annotations
import os
from typing import List

# -----------------------------
# Helpers to read environment
# -----------------------------
def _getenv(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    if v is None:
        return default
    v = v.strip()
    return v if v != "" else default

def _getint(name: str, default: int) -> int:
    v = _getenv(name)
    if v is None:
        return default
    try:
        return int(v)
    except Exception:
        return default

def _getbool(name: str, default: bool) -> bool:
    v = _getenv(name)
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes", "y", "on")

def _getlist(name: str, default: List[str]) -> List[str]:
    v = _getenv(name)
    if v is None:
        return default
    parts = [p.strip() for p in v.split(",")]
    return [p for p in parts if p]

# -----------------------------
# General HTTP / crawling
# -----------------------------
USER_AGENT         = _getenv("USER_AGENT", "Mozilla/5.0 (compatible; ChucklBot/1.0)")
HTTP_TIMEOUT       = _getint("HTTP_TIMEOUT", 15)      # seconds
TIMEOUT            = HTTP_TIMEOUT                     # alias for older imports
FETCH_DELAY_MS     = _getint("FETCH_DELAY_MS", 400)   # ms between fetches
MAX_PAGES_PER_SITE = _getint("MAX_PAGES_PER_SITE", 20)

# Common paths to probe on a site root for contact info
CONTACT_PATHS = [
    "/contact", "/contact/", "/contact-us", "/contact-us/", "/contactus",
    "/get-in-touch", "/getintouch",
    "/support", "/help",
    "/find-us", "/where-to-find-us",
    "/about", "/about-us",
    "/company/contact",
    "/privacy", "/privacy-policy",
    "/imprint", "/impressum",
    "/team",
]

# -----------------------------
# ScraperAPI (optional)
# -----------------------------
SCRAPERAPI_KEY     = _getenv("SCRAPERAPI_KEY", None)
SCRAPERAPI_BASE    = _getenv("SCRAPERAPI_BASE", "https://api.scraperapi.com/")
SCRAPERAPI_RENDER  = _getbool("SCRAPERAPI_RENDER", False)
SCRAPERAPI_COUNTRY = _getenv("SCRAPERAPI_COUNTRY", "")  # e.g. "uk", "us"

# -----------------------------
# Google CSE / Bing (optional)
# -----------------------------
GOOGLE_CSE_KEY            = _getenv("GOOGLE_CSE_KEY", "")
GOOGLE_CSE_CX             = _getenv("GOOGLE_CSE_CX", "")
GOOGLE_CSE_QPS_DELAY_MS   = _getint("GOOGLE_CSE_QPS_DELAY_MS", 800)  # throttle between CSE calls
GOOGLE_CSE_MAX_RETRIES    = _getint("GOOGLE_CSE_MAX_RETRIES", 5)

BING_API_KEY              = _getenv("BING_API_KEY", "")

# How many candidate search results to consider when resolving “official site”
MAX_GOOGLE_CANDIDATES     = _getint("MAX_GOOGLE_CANDIDATES", 6)

# Skip sending us to generic/low-signal destinations in search results
BAD_HOSTS: List[str] = _getlist(
    "BAD_HOSTS",
    [
        "facebook.com", "linkedin.com", "twitter.com", "instagram.com", "youtube.com",
        "wikipedia.org", "reddit.com", "medium.com", "blogspot.com", "wordpress.com",
        "typepad.com", "pinterest.com", "foursquare.com", "yelp.com", "fda.gov",
    ],
)

# -----------------------------
# Business logic / heuristics
# -----------------------------
DEFAULT_LOCATION         = _getenv("DEFAULT_LOCATION", "Ely")
MAX_ROWS                 = _getint("MAX_ROWS", 100)  # how many rows to process per run

# Prefer company’s own domain if we have both a marketplace/profile and a real site
PREFER_COMPANY_DOMAIN    = _getbool("PREFER_COMPANY_DOMAIN", True)

# If we don’t find a public email, optionally guess common mailboxes at the domain
GUESS_GENERICS           = _getbool("GUESS_GENERICS", True)
GENERIC_GUESS_PREFIXES   = _getlist(
    "GENERIC_GUESS_PREFIXES",
    ["info", "hello", "contact", "sales", "enquiries", "support"],
)

# -----------------------------
# Sheets / Service Account
# -----------------------------
SHEET_ID                 = _getenv("SHEET_ID", None)
SHEET_TAB                = _getenv("SHEET_TAB", "Sheet1")
GOOGLE_SA_JSON_B64       = _getenv("GOOGLE_SA_JSON_B64", "")  # <- added

# -----------------------------
# Export convenience
# -----------------------------
__all__ = [
    "USER_AGENT", "HTTP_TIMEOUT", "TIMEOUT", "FETCH_DELAY_MS", "MAX_PAGES_PER_SITE",
    "CONTACT_PATHS",
    "SCRAPERAPI_KEY", "SCRAPERAPI_BASE", "SCRAPERAPI_RENDER", "SCRAPERAPI_COUNTRY",
    "GOOGLE_CSE_KEY", "GOOGLE_CSE_CX", "GOOGLE_CSE_QPS_DELAY_MS", "GOOGLE_CSE_MAX_RETRIES",
    "BING_API_KEY", "MAX_GOOGLE_CANDIDATES", "BAD_HOSTS",
    "DEFAULT_LOCATION", "MAX_ROWS",
    "PREFER_COMPANY_DOMAIN", "GUESS_GENERICS", "GENERIC_GUESS_PREFIXES",
    "SHEET_ID", "SHEET_TAB", "GOOGLE_SA_JSON_B64",
]
