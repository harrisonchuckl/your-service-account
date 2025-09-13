import requests
from urllib.parse import urljoin
from requests.exceptions import SSLError, ConnectionError
import tldextract

from .config import (
    SCRAPERAPI_KEY, SCRAPERAPI_RENDER, TIMEOUT, USER_AGENT,
    CONTACT_PATHS, CONTACT_KEYWORDS, BAD_HOSTS,
    MAX_CRAWL_PAGES, MAX_DISCOVERED_PER_PAGE, FOLLOW_DEPTH
)
from .logging_utils import get_logger

logger = get_logger("crawl")

def _through_scraper(url, headers):
    api = "http://api.scraperapi.com"
    params = {"api_key": SCRAPERAPI_KEY, "url": url}
    if SCRAPERAPI_RENDER:
        params["render"] = "true"
    return requests.get(api, params=params, headers=headers, timeout=TIMEOUT)

def fetch(url):
    headers = {"User-Agent": USER_AGENT}
    try:
        r = _through_scraper(url, headers) if SCRAPERAPI_KEY else requests.get(
            url, headers=headers, timeout=TIMEOUT, allow_redirects=True
        )
        r.raise_for_status()
        return r.text
    except (SSLError, ConnectionError, requests.HTTPError) as e:
        raise e

def _same_registered_domain(a, b):
    ea = tldextract.extract(a); eb = tldextract.extract(b)
    return ea.registered_domain and (ea.registered_domain == eb.registered_domain)

def _is_bad_host(url: str) -> bool:
    u = (url or "").lower()
    return any(b in u for b in BAD_HOSTS)

def _discover_links(html, base_url):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a"):
        href = (a.get("href") or "").strip()
        if not href:
            continue
        abs_url = urljoin(base_url, href)
        if _is_bad_host(abs_url):
            continue
        text = (a.get_text(" ", strip=True) or "").lower()
        target = (href or "").lower() + " " + text
        if any(k in target for k in CONTACT_KEYWORDS):
            links.append(abs_url)
        if len(links) >= MAX_DISCOVERED_PER_PAGE:
            break
    return links

def crawl_candidate_pages(root_url):
    """
    BFS to depth FOLLOW_DEPTH within same registered domain.
    Start with root + fixed contact paths.
    """
    seen = set()
    queue = []
    html_by_url = {}

    # seed
    queue.append((root_url, 0))
    for path in CONTACT_PATHS:
        u = root_url.rstrip("/") + path
        if u != root_url:
            queue.append((u, 1))

    while queue and len(html_by_url) < MAX_CRAWL_PAGES:
        url, depth = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            html = fetch(url)
            html_by_url[url] = html
            if depth == 0:
                logger.info(f"Fetched homepage: {url}")
            # discover more if depth allows
            if depth < FOLLOW_DEPTH:
                for nxt in _discover_links(html, url):
                    if nxt not in seen and _same_registered_domain(root_url, nxt):
                        queue.append((nxt, depth + 1))
        except Exception as e:
            logger.info(f"Skip {url}: {e}")

    logger.info(f"Crawled {len(html_by_url)} pages on {root_url}")
    return html_by_url
