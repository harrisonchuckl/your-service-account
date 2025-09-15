# src/config.py
import os

# -------------------------
# Helpers to read env vars
# -------------------------
def _get(name: str, default: str = "") -> str:
    v = os.getenv(name)
    if v is None:
        return default
    s = str(v).strip()
    return s if s != "" else default

def _getint(name: str, default: int) -> int:
    v = os.getenv(name)
    try:
        s = "" if v is None else str(v).strip()
        return int(s) if s != "" else default
    except Exception:
        return default

def _getbool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    s = str(v).strip().lower()
    return s in {"1", "true", "yes", "y", "on"}

# ----------------------------------
# Required auth / Google Sheet info
# ----------------------------------
GOOGLE_SA_JSON_B64 = _get("GOOGLE_SA_JSON_B64")  # base64 of Service Account JSON
SHEET_ID           = _get("SHEET_ID")
SHEET_TAB          = _get("SHEET_TAB", "Sheet1")

# -----------------------
# General run parameters
# -----------------------
DEFAULT_LOCATION          = _get("DEFAULT_LOCATION", "Ely")
MAX_ROWS                  = _getint("MAX_ROWS", 100)  # how many rows to process per run

# -----------------------
# Email selection knobs
# -----------------------
PREFER_COMPANY_DOMAIN     = _getbool("PREFER_COMPANY_DOMAIN", True)   # prefer emails at company domain
ACCEPT_OFFDOMAIN_EMAILS   = _getbool("ACCEPT_OFFDOMAIN_EMAILS", True) # accept e.g. gov.uk/privacy if nothing else

# If no public email is found, optionally guess info@, hello@, etc.
GUESS_GENERICS            = _getbool("GUESS_GENERICS", True)

# The generic prefixes we might guess (info@{domain}, etc.)
GENERIC_GUESS_PREFIXES = [
    "info", "hello", "contact", "enquiries", "enquiry", "sales", "admin",
    "office", "support", "team", "press", "media", "bookings", "boxoffice",
    "customerservice", "customer.service", "help", "accounts",
]

# Some code bases score generic addresses by checking startswith("<prefix>@")
# Provide that form as well for convenience.
GENERIC_PRIORITY = [p + "@" for p in GENERIC_GUESS_PREFIXES]

# Bad/no-reply style prefixes to ignore
BAD_PREFIXES = [
    "example@", "test@", "noreply@", "no-reply@", "donotreply@", "do-not-reply@",
    "mailer-daemon@", "postmaster@", "bounce@", "support-noreply@", "auto@",
]

# --------------------------
# Google Programmable Search
# --------------------------
GOOGLE_CSE_KEY            = _get("GOOGLE_CSE_KEY")
GOOGLE_CSE_CX             = _get("GOOGLE_CSE_CX")
GOOGLE_CSE_QPS_DELAY_MS   = _getint("GOOGLE_CSE_QPS_DELAY_MS", 800)  # polite delay between API calls
GOOGLE_CSE_MAX_RETRIES    = _getint("GOOGLE_CSE_MAX_RETRIES", 5)
GOOGLE_CONTACT_HUNT       = _getbool("GOOGLE_CONTACT_HUNT", True)     # search for contact pages if crawl fails
MAX_GOOGLE_CANDIDATES     = _getint("MAX_GOOGLE_CANDIDATES", 6)

# --------------------------
# Crawl / HTTP configuration
# --------------------------
HTTP_TIMEOUT       = _getint("HTTP_TIMEOUT", 15)      # seconds per HTTP request
FETCH_DELAY_MS     = _getint("FETCH_DELAY_MS", 250)   # delay between requests
MAX_PAGES_PER_SITE = _getint("MAX_PAGES_PER_SITE", 20)

USER_AGENT = _get(
    "USER_AGENT",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Back-compat aliases some modules import
TIMEOUT   = HTTP_TIMEOUT
DELAY_MS  = FETCH_DELAY_MS
MAX_PAGES = MAX_PAGES_PER_SITE

# Optional proxy / rendering service (ScraperAPI)
BING_API_KEY       = _get("BING_API_KEY", "")
SCRAPERAPI_KEY     = _get("SCRAPERAPI_KEY", "")
SCRAPERAPI_RENDER  = _getbool("SCRAPERAPI_RENDER", False)   # use render=true if your plan supports it
SCRAPERAPI_COUNTRY = _get("SCRAPERAPI_COUNTRY", "")         # e.g. "uk"
SCRAPERAPI_BASE    = _get("SCRAPERAPI_BASE", "https://api.scraperapi.com")

# --------------------------
# Site / host filtering
# --------------------------
BAD_HOSTS = {
    "facebook.com", "m.facebook.com", "instagram.com", "twitter.com", "x.com",
    "linkedin.com", "youtube.com", "yelp.com", "wikipedia.org", "pinterest.com",
}

# Contact-like paths we probe on a homepage (exact + a few variants)
CONTACT_PATHS = [
    "/contact", "/contact/", "/contact-us", "/contact-us/", "/contactus",
    "/contact.html", "/contact.htm", "/contact.php",
    "/company/contact",
    "/get-in-touch", "/get-in-touch/", "/getintouch",
    "/support", "/help",
    "/about", "/about-us", "/find-us", "/where-to-find-us",
    "/privacy", "/privacy-policy", "/legal", "/imprint", "/impressum",
    "/team",
]
# Allow adding extra probe paths from env
_extra = [p.strip() for p in _get("CONTACT_PATHS_EXTRA", "").split(",") if p.strip()]
if _extra:
    seen = set(CONTACT_PATHS)
    for p in _extra:
        if p not in seen:
            CONTACT_PATHS.append(p)
            seen.add(p)
