import requests, tldextract
from .logging_utils import get_logger
from .config import BING_API_KEY
logger = get_logger("search")

def find_official_site(company, domain_hint):
    if domain_hint and "." in domain_hint:
        url = normalize_site(f"https://{domain_hint}")
        if url:
            logger.info(f"[{company}] Using domain hint: {url}")
            return url

    if BING_API_KEY:
        url = _bing_find(company)
        if url:
            logger.info(f"[{company}] Bing resolved: {url}")
            return url
    logger.info(f"[{company}] No search provider configured or no result.")
    return None

def _bing_find(query):
    endpoint = "https://api.bing.microsoft.com/v7.0/search"
    params = {"q": query, "count": 5, "responseFilter": "Webpages", "mkt": "en-GB"}
    headers = {"Ocp-Apim-Subscription-Key": BING_API_KEY}
    r = requests.get(endpoint, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    items = r.json().get("webPages", {}).get("value", [])
    for it in items:
        url = it.get("url", "")
        if looks_like_official(url):
            return normalize_site(url)
    return items[0]["url"] if items else None

def looks_like_official(url):
    bad = ["facebook.com","twitter.com","x.com","linkedin.com","instagram.com",
           "youtube.com","wikipedia.org"]
    u = url.lower()
    return not any(b in u for b in bad)

def normalize_site(url):
    ext = tldextract.extract(url)
    if not ext.registered_domain:
        return None
    return f"https://{ext.registered_domain}"
