# src/crawl.py
from __future__ import annotations

import time
import logging
from typing import Dict, Iterable, List, Tuple, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
import tldextract

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


# ---------- Networking helpers ----------

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

    return requests.get(
        SCRAPERAPI_BASE,
        params=params,
        timeout=HTTP_TIMEOUT,
        headers=HEADERS,
    )


def _direct_get(url: str) -> requests.Response:
    return requests.get(url, timeout=HTTP_TIMEOUT, headers=HEADERS, allow_redirects=True)


def _fetch(url: str) -> Tuple[Optional[str], Optional[str]]:
    """Fetch a URL and return (html, error_message)."""
    try:
        r = _scraperapi_get(url) if SCRAPERAPI_KEY else _direct_get(url)
        ctype = r.headers.get("content-type", "").lower()
        if r.status_code == 200 and ctype.startswith("text"):
            return r.text, None
        err = f"{r.status_code} Client Error: {r.reason} for url: {r.url}"
        return None, err
    except requests.RequestException as e:
        return None, str(e)


# Public alias so main.py can call crawl.fetch(...)
def fetch(url: str) -> Tuple[Optional[str], Optional[str]]:
    return _fetch(url)


# ---------- URL sanity + discovery ----------

def _same_host(base: str, href: str) -> bool:
    try:
        b = urlparse(base)
        h = urlparse(href)
        bhost = (b.netloc or "").split(":")[0].lower()
        hhost = (h.netloc or b.netloc or "").split(":")[0].lower()
        return hhost.endswith(bhost) if bhost else True
    except Exception:
        return True


def _is_plausible_http_url(u: str) -> bool:
    """Reject junk like https://h, https://:, javascript:, mailto:, etc."""
    if not u:
        return False
    u = u.strip()
    low = u.lower()
    if any(low.startswith(s) for s in ("mailto:", "tel:", "javascript:", "data:", "about:")):
        return False
    try:
        p = urlparse(u)
        if p.scheme not in ("http", "https"):
            return False
        if not p.netloc:
            return False
        host = p.netloc.split("@")[-1].split(":")[0]
        if not host or " " in host or host.startswith("-") or host.endswith("-"):
            return False
        # real public suffix (avoids hosts like "h", "-", etc.)
        ext = tldextract.extract(host)
        if not ext.suffix:
            return False
        return True
    except Exception:
        return False


def _is_contactish(href: str) -> bool:
    if not href:
        return False
    h = href.lower()
    return any(
        token in h
        for token in (
            "contact", "kontakt", "impressum", "privacy", "support", "help",
            "about", "team", "find-us", "where-to-find-us"
        )
    )


def _discover_contactish_links(base_url: str, html: str, max_links: int = 30) -> List[str]:
    """Collect contact-ish links (absolute, deduped, same host, plausible)."""
    out: List[str] = []
    seen = set()
    soup = BeautifulSoup(html or "", "html.parser")

    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        if not href:
            continue

        # Ignore pure fragments and non-http schemes early
        low = href.lower()
        if low.startswith("#") or any(low.startswith(s) for s in ("mailto:", "tel:", "javascript:", "data:", "about:")):
            continue

        abs_url = urljoin(base_url, href)

        # Must be plausible and same host
        if not _is_plausible_http_url(abs_url):
            continue
        if not _same_host(base_url, abs_url):
            continue
        if not _is_contactish(abs_url):
            continue

        if abs_url in seen:
            continue
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
    return u


# ---------- Public crawl functions ----------

def crawl_site(start_url: str) -> Dict[str, str]:
    """
    Crawl a site looking for contact-like pages.
    Returns {url: html} for pages fetched successfully.
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
        return out

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
            # Keep the prior "Skip ..." style for continuity
            print(f"[INFO] Skip {url}: {err2}")

    # Discover additional candidates from homepage (tight filtering)
    more = _discover_contactish_links(start_url, html, max_links=50)
    if more:
        print(f"[INFO] Discovered {len(more)} contact-like links on homepage")

    for url in more:
        if fetched >= MAX_PAGES_PER_SITE:
            break
        if url in out or not _is_plausible_http_url(url):
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
        if not _is_plausible_http_url(u):
            continue
        html, err = _fetch(u)
        if html:
            out[u] = html
        else:
            print(f"[INFO] Skip {u}: {err}")
        time.sleep(FETCH_DELAY_MS / 1000.0)
    return out
