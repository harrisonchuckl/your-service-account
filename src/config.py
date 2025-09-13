import os

# Required
GOOGLE_SA_JSON_B64 = os.getenv("GOOGLE_SA_JSON_B64")
SHEET_ID = os.getenv("SHEET_ID")

# Optional
SHEET_TAB = os.getenv("SHEET_TAB") or None
MAX_ROWS = int(os.getenv("MAX_ROWS", "80"))  # keep modest to respect free quotas

# Location bias for search fallbacks
DEFAULT_LOCATION = os.getenv("DEFAULT_LOCATION", "Ely")

# Google Custom Search secrets are read inside search.py via env:
# GOOGLE_CSE_KEY, GOOGLE_CSE_CX

# Crawling provider (optional but helpful for SSL/CAPTCHA)
SCRAPERAPI_KEY = os.getenv("SCRAPERAPI_KEY")

# Crawl behaviour
TIMEOUT = int(os.getenv("TIMEOUT", "30"))
USER_AGENT = os.getenv("USER_AGENT",
    "Mozilla/5.0 (compatible; ChucklContactFinder/1.1; +https://github.com/your-org)")

# Common places to try directly off the root
CONTACT_PATHS = [
    "/", "/contact", "/contact/", "/contact-us", "/contact-us/",
    "/contactus", "/get-in-touch", "/getintouch", "/support", "/help",
    "/find-us", "/where-to-find-us",
    "/about", "/about-us", "/company/contact",
    "/privacy", "/privacy-policy", "/legal", "/imprint", "/impressum", "/team"
]

# Keywords to discover on-page links to follow (matched in href OR link text)
CONTACT_KEYWORDS = [
    "contact", "get in touch", "enquir", "support", "customer", "help",
    "find us", "where to find", "privacy", "data protection", "gdpr",
    "imprint", "impressum", "legal", "about", "team", "email us"
]

# Hosts to avoid when picking an "official" site
BAD_HOSTS = [
    "facebook.com","twitter.com","x.com","linkedin.com","instagram.com",
    "youtube.com","wikipedia.org","yelp.com","service.gov.uk","gov.uk",
    "companieshouse.gov.uk","glassdoor.com","indeed.com","nsf.gov",
    "tripadvisor.com","crunchbase.com","yell.com","thomsonlocal.com"
]
