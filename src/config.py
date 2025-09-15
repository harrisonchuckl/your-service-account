# src/config.py
import os

def _getenv(name: str, default: str = "") -> str:
    v = os.getenv(name)
    return (v if v is not None else default).strip()

def _getint(name: str, default: int | str) -> int:
    try:
        return int(_getenv(name, str(default)))
    except Exception:
        return int(default)

def _getbool(name: str, default: bool) -> bool:
    raw = _getenv(name, "true" if default else "false").lower()
    return raw in ("1", "true", "yes", "y", "on")

# === Google Sheet / Auth ===
GOOGLE_SA_JSON_B64 = _getenv("GOOGLE_SA_JSON_B64", "")
SHEET_ID           = _getenv("SHEET_ID", "")
SHEET_TAB          = _getenv("SHEET_TAB", "Sheet1")

# === Run parameters ===
DEFAULT_LOCATION   = _getenv("DEFAULT_LOCATION", "Ely")
MAX_ROWS           = _getint("MAX_ROWS", 40)   # safe if env is blank

# === HTTP / crawling ===
HTTP_TIMEOUT       = _getint("HTTP_TIMEOUT", 15)
TIMEOUT            = HTTP_TIMEOUT                          # backward compat
USER_AGENT         = _getenv("USER_AGENT", "Mozilla/5.0 (compatible; chuckl-bot/1.0)")
FETCH_DELAY_MS     = _getint("FETCH_DELAY_MS", 250)        # NEW: politely space requests
FETCH_MAX_RETRIES  = _getint("FETCH_MAX_RETRIES", 3)       # NEW: retry on transient errors
RESPECT_ROBOTS     = _getbool("RESPECT_ROBOTS", False)     # optional toggle
MAX_PAGES_PER_SITE = _getint("MAX_PAGES_PER_SITE", 25)

# Paths we try on a site for contact pages
CONTACT_PATHS = [
    "/contact", "/contact/", "/contact-us", "/contact-us/",
    "/get-in-touch", "/getintouch", "/support", "/help",
    "/about", "/company/contact", "/legal", "/imprint", "/impressum",
    "/team", "/where-to-find-us", "/find-us",
]

# Prefer the company's own domain over marketplaces/directories
PREFER_COMPANY_DOMAIN = _getbool("PREFER_COMPANY_DOMAIN", True)

# When we must guess a generic address at a domain
GENERIC_GUESS_PREFIXES = ["info", "hello", "contact", "support", "enquiries", "enquiry", "sales"]
# Back-compat alias for older imports
GUESS_GENERICS = GENERIC_GUESS_PREFIXES

# Domains to skip (generic hosts, social networks, marketplaces, big govt portals, etc.)
BAD_HOSTS = [
    "facebook.com", "linkedin.com", "twitter.com", "x.com", "instagram.com", "youtube.com",
    "wikipedia.org", "reddit.com", "medium.com", "blogspot.com", "wordpress.com", "typepad.com",
    "pinterest.com", "foursquare.com", "yelp.com",
    "fda.gov",
    # Marketplaces / Amazon (requested)
    "amazon.com", "amazon.co.uk", "aws.amazon.com",
]

# Optional: TLD preference (used by some filters—non-critical)
GOOD_TLDS = ["com", "co.uk", "org", "net", "io"]

# === Google Custom Search ===
GOOGLE_CSE_KEY            = _getenv("GOOGLE_CSE_KEY", "")
GOOGLE_CSE_CX             = _getenv("GOOGLE_CSE_CX", "")
GOOGLE_CSE_QPS_DELAY_MS   = _getint("GOOGLE_CSE_QPS_DELAY_MS", 800)
GOOGLE_CSE_MAX_RETRIES    = _getint("GOOGLE_CSE_MAX_RETRIES", 5)
MAX_GOOGLE_CANDIDATES     = _getint("MAX_GOOGLE_CANDIDATES", 8)

# === Optional fallback providers ===
BING_API_KEY              = _getenv("BING_API_KEY", "")
SCRAPERAPI_KEY            = _getenv("SCRAPERAPI_KEY", "")
SCRAPERAPI_RENDER         = _getbool("SCRAPERAPI_RENDER", False)
