# src/crawl.py
from __future__ import annotations

import time
import logging
from typing import Dict, Iterable, List, Tuple, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .config import (
    USER_AGENT,
    HTTP_TIMEOUT,
    FETCH_DELAY_MS,
    MAX_PAGES_PER_SITE,
    CONTACT_PATHS,
    SCRAPERAPI_KEY,
    SCRAPERAPI_BASE,
    SCRAPERAPI_RENDER,
    SCRAPERAPI_COUNTRY,
)

log = logging.getLogger(__name__)

HEADERS = {"User-Agent": USER_AGENT}


def _scraperapi_get(url: str) -> requests.Response:
    """Route a request through ScraperAPI if a key is configured."""
    params = {
        "api_key": SCRAPERAPI_KEY,
        "url": url,
    }
    if SCRAPERAPI_RENDER:
        params["render"] = "true"
    if SCRAPERAPI_COUNTRY:
        params["country_code"] = SCRAPERAPI_COUNTRY

    r = requests.get(SCRAPERAPI_BASE, params=params, timeout=HTTP_TIMEOUT, headers=HEADERS)
    return r


def _direct_get(url: str) -> requests.Response:
    return requests.get(url, timeout=HTTP_TIMEOUT, headers=HEADERS, allow_redirects=True)


def _fetch(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch a URL and return (html, error_message).
    On non-200, returns (None, reason) but also prints a line like earlier logs.
    """
    try:
        if SCRAPERAPI_KEY:
            r = _scraperapi_get(url)
        else:
            r = _direct_get(url)
        if r.status_code == 200 and r.headers.get("content-type", "").lower().startswith("text"):
            return r.text, None
        else:
            err = f"{r.status_code} Client Error: {r.reason} for url: {r.url}"
            return None, err
    except requests.RequestException as e:
        return None, str(e)


def _is_contactish(href: str) -> bool:
    if not href:
        return False
    h = href.lower()
    return any(
        token in h
        for token in [
            "contact", "impressum", "imprint", "privacy", "support", "help",
            "about", "team", "find-us", "where-to-find-us"
        ]
    )


def _same_host(base: str, href: str) -> bool:
    try:
        b = urlparse(base)
        h = urlparse(href)
        return (h.netloc or b.netloc).split(":")[0].lower().endswith(b.netloc.split(":")[0].lower())
    except Exception:
        return True  # be permissive if parsing fails


def _discover_contactish_links(base_url: str, html: str, max_links: int = 30) -> List[str]:
    """From a page, collect contact-ish links (same host), absolute and deduped."""
    out: List[str] = []
    seen = set()
    soup = BeautifulSoup(html or "", "html.parser")
    for a in soup.find_all("a", href=True):
        href = a.get("href")
        abs_url = urljoin(base_url, href)
        if abs_url in seen:
            continue
        if _is_contactish(href) and _same_host(base_url, abs_url):
            out.append(abs_url)
            seen.add(abs_url)
            if len(out) >= max_links:
                break
    return out


def _normalize(url: str) -> str:
    if not url:
        return url
    u = url.strip()
    if u.startswith("//"):
        u = "https:" + u
    if not u.startswith("http://") and not u.startswith("https://"):
        u = "https://" + u
    return u


def crawl_site(start_url: str) -> Dict[str, str]:
    """
    Crawl a site looking for contact-like pages.
    Returns {url: html} for pages fetched successfully.
    Mirrors the logging style you saw earlier.
    """
    start_url = _normalize(start_url)
    out: Dict[str, str] = {}
    fetched = 0

    print(f"[INFO] Fetched homepage: {start_url}")
    html, err = _fetch(start_url)
    if html:
        out[start_url] = html
    else:
        print(f"[INFO] Skip {start_url}: {err}")
        return out  # nothing else we can do

    # Probe common contact-ish paths off the root
    parsed = urlparse(start_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    for p in CONTACT_PATHS:
        if fetched >= MAX_PAGES_PER_SITE:
            break
        url = urljoin(root, p)
        if url in out:
            continue
        html2, err2 = _fetch(url)
        if html2:
            out[url] = html2
            fetched += 1
            time.sleep(FETCH_DELAY_MS / 1000.0)
        else:
            print(f"[INFO] Skip {url}: {err2}")

    # Discover additional candidates from homepage
    more = _discover_contactish_links(start_url, html, max_links=50)
    if more:
        print(f"[INFO] Discovered {len(more)} contact-like links on homepage")

    for url in more:
        if fetched >= MAX_PAGES_PER_SITE:
            break
        if url in out:
            continue
        html3, err3 = _fetch(url)
        if html3:
            out[url] = html3
            fetched += 1
            time.sleep(FETCH_DELAY_MS / 1000.0)
        else:
            print(f"[INFO] Skip {url}: {err3}")

    print(f"[INFO] Crawled {len(out)} pages on {root}")
    return out


def crawl_candidate_pages(urls: Iterable[str]) -> Dict[str, str]:
    """
    Fetch a small set of specific candidate URLs (e.g., from Google contact hunt).
    Returns {url: html} for successes.
    """
    out: Dict[str, str] = {}
    for u in urls:
        url = _normalize(u)
        html, err = _fetch(url)
        if html:
            out[url] = html
        else:
            print(f"[INFO] Skip {url}: {err}")
        time.sleep(FETCH_DELAY_MS / 1000.0)
    return out
