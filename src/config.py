import os

# --- Required ---
GOOGLE_SA_JSON_B64 = os.getenv("GOOGLE_SA_JSON_B64")
SHEET_ID = os.getenv("SHEET_ID")

# --- Sheet / run control ---
SHEET_TAB = os.getenv("SHEET_TAB") or None
MAX_ROWS = int(os.getenv("MAX_ROWS", "40"))  # keep modest while testing
DEFAULT_LOCATION = os.getenv("DEFAULT_LOCATION", "Ely")

# --- Google Programmable Search (set as repo secrets) ---
# GOOGLE_CSE_KEY
# GOOGLE_CSE_CX

# --- Crawling behaviour ---
TIMEOUT = int(os.getenv("TIMEOUT", "30"))
USER_AGENT = os.getenv("USER_AGENT",
    "Mozilla/5.0 (compatible; ChucklContactFinder/1.3; +https://github.com/your-org)")
SCRAPERAPI_KEY = os.getenv("SCRAPERAPI_KEY")  # optional proxy
SCRAPERAPI_RENDER = os.getenv("SCRAPERAPI_RENDER", "0") == "1"  # if your proxy supports JS rendering

# Crawl scope/limits
FOLLOW_DEPTH = int(os.getenv("FOLLOW_DEPTH", "2"))     # homepage + discovered links up to depth 2
MAX_CRAWL_PAGES = int(os.getenv("MAX_CRAWL_PAGES", "20"))
MAX_DISCOVERED_PER_PAGE = int(os.getenv("MAX_DISCOVERED_PER_PAGE", "10"))

# Common places to try directly off the root
CONTACT_PATHS = [
    "/", "/contact", "/contact/", "/contact-us", "/contact-us/", "/contactus",
    "/get-in-touch", "/getintouch", "/support", "/help", "/find-us",
    "/where-to-find-us", "/about", "/about-us", "/company/contact",
    "/privacy", "/privacy-policy", "/legal", "/imprint", "/impressum", "/team"
]

# Anchor/link text/href keywords to follow
CONTACT_KEYWORDS = [
    "contact", "get in touch", "enquir", "support", "customer", "help",
    "find us", "where to find", "privacy", "data protection", "gdpr",
    "imprint", "impressum", "legal", "about", "team", "email us", "email"
]

# --- Picking/filters ---
BAD_HOSTS = [
    "facebook.com","twitter.com","x.com","linkedin.com","instagram.com",
    "youtube.com","wikipedia.org","yelp.com","service.gov.uk","gov.uk",
    "companieshouse.gov.uk","glassdoor.com","indeed.com","nsf.gov",
    "tripadvisor.com","crunchbase.com","yell.com","thomsonlocal.com"
]

# Accept only emails on the company domain? (still falls back if none)
PREFER_COMPANY_DOMAIN = os.getenv("PREFER_COMPANY_DOMAIN", "1") == "1"

# As a last resort, guess common inboxes like info@domain (clearly labeled).
GUESS_GENERICS = os.getenv("GUESS_GENERICS", "1") == "1"
GENERIC_GUESS_PREFIXES = [
    "info", "contact", "enquiries", "enquiry", "sales", "hello",
    "support", "office", "admin", "press", "media"
]
