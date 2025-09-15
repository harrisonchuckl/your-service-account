# src/config.py
import os

# ---------- helpers ----------
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

def _getbool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    s = str(v).strip().lower()
    return s in {"1", "true", "yes", "y", "on"}

# ---------- required auth / sheet ----------
GOOGLE_SA_JSON_B64 = _get("GOOGLE_SA_JSON_B64")  # base64 of the service account JSON
SHEET_ID           = _get("SHEET_ID")            # Google Sheet ID
SHEET_TAB          = _get("SHEET_TAB", "Sheet1")

# ---------- scraping/search behavior ----------
DEFAULT_LOCATION   = _get("DEFAULT_LOCATION", "Ely")

# network / crawl knobs
HTTP_TIMEOUT       = _getint("HTTP_TIMEOUT", 15)          # seconds
FETCH_DELAY_MS     = _getint("FETCH_DELAY_MS", 250)       # polite delay between requests
MAX_PAGES_PER_SITE = _getint("MAX_PAGES_PER_SITE", 20)    # depth/limit per site
USER_AGENT = _get(
    "USER_AGENT",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Back-compat aliases (other modules may import these names)
TIMEOUT   = HTTP_TIMEOUT
DELAY_MS  = FETCH_DELAY_MS
MAX_PAGES = MAX_PAGES_PER_SITE

# limit how many sheet rows to process per run
MAX_ROWS = _getint("MAX_ROWS", 100)

# ---------- Google Programmable Search (CSE) ----------
GOOGLE_CSE_KEY           = _get("GOOGLE_CSE_KEY")
GOOGLE_CSE_CX            = _get("GOOGLE_CSE_CX")
GOOGLE_CSE_QPS_DELAY_MS  = _getint("GOOGLE_CSE_QPS_DELAY_MS", 800)
GOOGLE_CSE_MAX_RETRIES   = _getint("GOOGLE_CSE_MAX_RETRIES", 5)

# ---------- optional fallbacks / proxies ----------
BING_API_KEY       = _get("BING_API_KEY", "")
SCRAPERAPI_KEY     = _get("SCRAPERAPI_KEY", "")
SCRAPERAPI_RENDER  = _getbool("SCRAPERAPI_RENDER", False)
SCRAPERAPI_COUNTRY = _get("SCRAPERAPI_COUNTRY", "")            # e.g. "uk" or "us"
SCRAPERAPI_BASE    = _get("SCRAPERAPI_BASE", "https://api.scraperapi.com")

# ---------- site filters ----------
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

# ---------- paths the crawler should try on a homepage for contacts/about/legal ----------
# These are relative paths that will be joined to the detected base URL.
CONTACT_PATHS = [
    # contact pages
    "/contact", "/contact/", "/contact-us", "/contact-us/", "/contactus",
    "/get-in-touch", "/get-in-touch/", "/getintouch",
    "/contact.html", "/contact.htm", "/contact.php",
    "/contact-us.html", "/contact-us.htm", "/contact-us.php",
    "/company/contact",
    # support/help
    "/support", "/help",
    # about / location pages (often contain emails or forms)
    "/about", "/about-us", "/find-us", "/where-to-find-us",
    # legal/privacy/imprint often list an email
    "/privacy", "/privacy-policy", "/legal", "/imprint", "/impressum",
    # team directory sometimes lists emails
    "/team",
]

# Optional: allow adding extra paths via env (comma-separated)
_extra = [p.strip() for p in _get("CONTACT_PATHS_EXTRA", "").split(",") if p.strip()]
if _extra:
    # Keep order but avoid duplicates
    seen = set(CONTACT_PATHS)
    for p in _extra:
        if p not in seen:
            CONTACT_PATHS.append(p)
            seen.add(p)
