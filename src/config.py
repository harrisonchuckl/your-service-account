import os

# --- Required ---
GOOGLE_SA_JSON_B64 = os.getenv("GOOGLE_SA_JSON_B64")  # base64 of the service account JSON
SHEET_ID = os.getenv("SHEET_ID")                      # Google Sheet ID (the long string in the URL)

# --- Optional / recommended ---
SHEET_TAB = os.getenv("SHEET_TAB") or None            # default: first worksheet
MAX_ROWS = int(os.getenv("MAX_ROWS", "500"))          # how many rows to process per run

# Search provider (pick one you have keys for)
BING_API_KEY = os.getenv("BING_API_KEY")              # If set, uses Bing Web Search API

# Crawling provider (ScraperAPI or similar)
SCRAPERAPI_KEY = os.getenv("SCRAPERAPI_KEY")          # If set, routes requests via ScraperAPI

# Crawl behaviour
TIMEOUT = int(os.getenv("TIMEOUT", "30"))
USER_AGENT = os.getenv("USER_AGENT",
    "Mozilla/5.0 (compatible; ChucklContactFinder/1.0; +https://github.com/chuckl)")
CONTACT_PATHS = [
    "/", "/contact", "/contact-us", "/contacts", "/about", "/impressum", "/privacy", "/team"
]

# Extraction behaviour
PRIORITISE_GENERIC = os.getenv("PRIORITISE_GENERIC", "true").lower() == "true"

