import os
import requests, tldextract
from .logging_utils import get_logger
from .config import BAD_HOSTS, DEFAULT_LOCATION

logger = get_logger("search")

GOOGLE_CSE_KEY = os.getenv("GOOGLE_CSE_KEY")
GOOGLE_CSE_CX  = os.getenv("GOOGLE_CSE_CX")
GOOGLE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"

def find_official_site(company, domain_hint):
    """Try to find the company's official root site."""
    if domain_hint and "." in domain_hint:
        url = normalize_site(f"https://{domain_hint}")
        if url:
            logger.info(f"[{company}] Using domain hint: {url}")
            return url

    if GOOGLE_CSE_KEY and GOOGLE_CSE_CX:
        queries = [
            f"{company} {DEFAULT_LOCATION} official site",
            f"{company} {DEFAULT_LOCATION}",
            f"{company} website",
            f"{company}"
        ]
        for q in queries:
            url = _google_first_good_url(q)
            if url:
                logger.info(f"[{company}] Google resolved: {url}")
                return url

    logger.info(f"[{company}] No search provider configured or no result.")
    return None

def google_contact_hunt(company, location=None, domain_for_site=None, limit=4):
    """
    Return up to `limit` URLs likely to show an email/contact.
    Prefer site-scoped queries if we know the domain.
    """
    if not (GOOGLE_CSE_KEY and GOOGLE_CSE_CX):
        return []
    loc = location or DEFAULT_LOCATION
    queries = []

    # site-scoped first if we know the domain
    if domain_for_site:
        queries += [
            f'site:{domain_for_site} "@{domain_for_site}"',
            f"site:{domain_for_site} contact",
            f"site:{domain_for_site} email",
            f'site:{domain_for_site} "contact us"',
            f"site:{domain_for_site} privacy",
        ]

    # general with locality
    queries += [
        f"{company} {loc} email",
        f"{company} {loc} contact",
        f"{company} email address",
        f"{company} contact details",
    ]

    urls = []
    for q in queries:
        items = _google_search(q, 5)
        for it in items:
            url = (it.get("link") or "").strip()
            if url and looks_like_candidate(url):
                urls.append(url)
            if len(urls) >= limit:
                return dedupe(urls)
    return dedupe(urls)

# ---- helpers ----

def _google_first_good_url(query):
    items = _google_search(query, 5)
    for it in items:
        url = it.get("link") or it.get("formattedUrl") or ""
        if looks_like_official(url):
            return normalize_site(url)
    return None  # don't pick a random bad host

def _google_search(query, num=5):
    params = {"key": GOOGLE_CSE_KEY, "cx": GOOGLE_CSE_CX, "q": query, "num": num, "safe": "off"}
    r = requests.get(GOOGLE_ENDPOINT, params=params, timeout=20)
    r.raise_for_status()
    return (r.json() or {}).get("items", []) or []

def looks_like_official(url):
    u = (url or "").lower()
    return bool(u) and not any(b in u for b in BAD_HOSTS)

def looks_like_candidate(url):
    u = (url or "").lower()
    if not u or any(b in u for b in BAD_HOSTS):
        return False
    # Anything on the same site or typical contact pages
    return any(x in u for x in ["contact", "about", "privacy", "impressum", "imprint", "@"])

def normalize_site(url):
    ext = tldextract.extract(url or "")
    if not ext.registered_domain:
        return None
    return f"https://{ext.registered_domain}"

def dedupe(seq):
    out, seen = [], set()
    for x in seq:
        if x not in seen:
            out.append(x); seen.add(x)
    return out
