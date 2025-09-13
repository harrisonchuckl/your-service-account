import requests
from urllib.parse import urljoin, urlparse
from requests.exceptions import SSLError, ConnectionError
from .config import SCRAPERAPI_KEY, TIMEOUT, USER_AGENT, CONTACT_PATHS, CONTACT_KEYWORDS
from .logging_utils import get_logger

logger = get_logger("crawl")

def _through_scraper(url, headers):
    api = "http://api.scraperapi.com"
    params = {"api_key": SCRAPERAPI_KEY, "url": url, "render": "false"}
    return requests.get(api, params=params, headers=headers, timeout=TIMEOUT)

def fetch(url):
    """
    Fetch a URL. If TLS/hostname issues, try scheme flip https<->http.
    Uses ScraperAPI if configured.
    """
    headers = {"User-Agent": USER_AGENT}
    try:
        r = _through_scraper(url, headers) if SCRAPERAPI_KEY else requests.get(url, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        return r.text
    except (SSLError, ConnectionError, requests.HTTPError) as e:
        # scheme fallback
        parsed = urlparse(url)
        alt = url.replace("https://", "http://") if parsed.scheme == "https" else url.replace("http://", "https://")
        if alt != url:
            try:
                r = _through_scraper(alt, headers) if SCRAPERAPI_KEY else requests.get(alt, headers=headers, timeout=TIMEOUT)
                r.raise_for_status()
                return r.text
            except Exception as e2:
                raise e2
        raise e

def _discover_links(html, base_url):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.find_all("a"):
        href = (a.get("href") or "").strip()
        text = (a.get_text(" ", strip=True) or "").lower()
        target = href.lower() + " " + text
        if any(k in target for k in CONTACT_KEYWORDS):
            abs_url = urljoin(base_url, href)
            if _same_host(base_url, abs_url):
                links.add(abs_url)
    return list(links)

def _same_host(root, url):
    pr = urlparse(root); pu = urlparse(url)
    return pr.hostname == pu.hostname

def crawl_candidate_pages(root_url):
    """
    1) Fetch root
    2) Try common contact-like paths
    3) Parse root to discover and crawl contact-like anchors
    """
    html_by_url = {}

    # 1. root
    try:
        html_by_url[root_url] = fetch(root_url)
        logger.info(f"Fetched homepage: {root_url}")
    except Exception as e:
        logger.info(f"Skip {root_url}: {e}")
        return html_by_url

    # 2. fixed paths
    for path in CONTACT_PATHS:
        u = root_url.rstrip("/") + path
        if u in html_by_url:  # "/" already fetched
            continue
        try:
            html_by_url[u] = fetch(u)
        except Exception as e:
            logger.info(f"Skip {u}: {e}")

    # 3. discovered links on homepage
    try:
        discovered = _discover_links(html_by_url[root_url], root_url)
        if discovered:
            logger.info(f"Discovered {len(discovered)} contact-like links on homepage")
        for u in discovered:
            if u in html_by_url:
                continue
            try:
                html_by_url[u] = fetch(u)
            except Exception as e:
                logger.info(f"Skip {u}: {e}")
    except Exception:
        pass

    return html_by_url
