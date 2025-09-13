import os
import requests, tldextract
from .logging_utils import get_logger

logger = get_logger("search")

# Google Programmable Search (Custom Search JSON API)
GOOGLE_CSE_KEY = os.getenv("GOOGLE_CSE_KEY")
GOOGLE_CSE_CX  = os.getenv("GOOGLE_CSE_CX")
GOOGLE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"

# Optional Bing fallback (only used if Google vars aren’t set)
BING_API_KEY = os.getenv("BING_API_KEY")
BING_ENDPOINT = os.getenv("BING_ENDPOINT") or "https://api.bing.microsoft.com/v7.0/search"

def find_official_site(company, domain_hint):
    # If you’ve filled the Domain column, prefer it.
    if domain_hint and "." in domain_hint:
        url = normalize_site(f"https://{domain_hint}")
        if url:
            logger.info(f"[{company}] Using domain hint: {url}")
            return url

    # Try Google first (free 100/day)
    if GOOGLE_CSE_KEY and GOOGLE_CSE_CX:
        u = _google_find(company)
        if u:
            logger.info(f"[{company}] Google resolved: {u}")
            return u

    # Optional fallback to Bing if configured
    if BING_API_KEY:
        u = _bing_find(company)
        if u:
            logger.info(f"[{company}] Bing resolved: {u}")
            return u

    logger.info(f"[{company}] No search provider configured or no result.")
    return None

def _google_find(query):
    params = {
        "key": GOOGLE_CSE_KEY,
        "cx": GOOGLE_CSE_CX,
        "q": query,
        "num": 5,
        "safe": "off",
    }
    r = requests.get(GOOGLE_ENDPOINT, params=params, timeout=20)
    r.raise_for_status()
    items = (r.json() or {}).get("items", []) or []
    for it in items:
        url = it.get("link") or it.get("formattedUrl") or ""
        if looks_like_official(url):
            return normalize_site(url)
    if items:
        return normalize_site(items[0].get("link", ""))
    return None

def _bing_find(query):
    params = {"q": query, "count": 5, "responseFilter": "Webpages", "mkt": "en-GB"}
    headers = {"Ocp-Apim-Subscription-Key": BING_API_KEY}
    r = requests.get(BING_ENDPOINT, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    items = r.json().get("webPages", {}).get("value", []) or []
    for it in items:
        url = it.get("url", "")
        if looks_like_official(url):
            return normalize_site(url)
    if items:
        return normalize_site(items[0].get("url", ""))
    return None

def looks_like_official(url):
    bad = ["facebook.com","twitter.com","x.com","linkedin.com","instagram.com",
           "youtube.com","wikipedia.org","glassdoor.com"]
    u = (url or "").lower()
    return bool(u) and not any(b in u for b in bad)

def normalize_site(url):
    ext = tldextract.extract(url or "")
    if not ext.registered_domain:
        return None
    return f"https://{ext.registered_domain}"
