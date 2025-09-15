# src/crawl.py
from __future__ import annotations
import logging, time, re
from urllib.parse import urljoin, urlparse
import requests
from .config import (
    HEADERS, HTTP_TIMEOUT, FETCH_DELAY_MS,
    MAX_PAGES_PER_SITE, MIN_PAGES_BEFORE_FALLBACK, SITE_BUDGET_SECONDS,
    BAD_EXTENSIONS, BAD_PATH_SNIPPETS, CONTACT_PATHS,
    SCRAPERAPI_KEY, SCRAPERAPI_BASE, SCRAPERAPI_COUNTRY, SCRAPERAPI_RENDER,
)

_session = requests.Session()
_session.headers.update(HEADERS)

def _ok(url: str) -> bool:
    ul = url.lower()
    if any(ul.endswith(ext) for ext in BAD_EXTENSIONS):
        return False
    if any(sn in ul for sn in BAD_PATH_SNIPPETS):
        return False
    return True

def _same_host(a: str, b: str) -> bool:
    try:
        ah = urlparse(a).netloc.split(":")[0].lower()
        bh = urlparse(b).netloc.split(":")[0].lower()
        return ah.endswith(bh)
    except Exception:
        return False

def _norm(base: str, href: str) -> str | None:
    try:
        u = urljoin(base, href)
        p = urlparse(u)
        if p.scheme not in ("http", "https"):
            return None
        return u.split("#")[0]
    except Exception:
        return None

def _scraperapi(url: str) -> str:
    if not SCRAPERAPI_KEY:
        return url
    from urllib.parse import urlencode
    params = {"api_key": SCRAPERAPI_KEY, "url": url}
    if SCRAPERAPI_RENDER:
        params["render"] = "true"
    if SCRAPERAPI_COUNTRY:
        params["country_code"] = SCRAPERAPI_COUNTRY
    return f"{SCRAPERAPI_BASE.rstrip('/')}/?{urlencode(params)}"

def fetch(url: str) -> str | None:
    try:
        target = _scraperapi(url)
        r = _session.get(target, timeout=HTTP_TIMEOUT, allow_redirects=True)
        r.raise_for_status()
        return r.text
    except Exception as e:
        logging.info("Skip %s: %s", url, e)
        return None

def crawl_candidate_pages(base_url: str, max_pages: int = 6) -> dict[str, str]:
    out: dict[str, str] = {}
    tried = 0
    for pat in CONTACT_PATHS:
        if tried >= max_pages:
            break
        path = pat if pat.startswith("/") else f"/{pat}"
        url = urljoin(base_url, path)
        if not _ok(url):
            continue
        html = fetch(url)
        tried += 1
        if html:
            out[url] = html
        time.sleep(FETCH_DELAY_MS / 1000.0)
    return out

def crawl_site(base_url: str) -> dict[str, str]:
    start = time.monotonic()
    seen: set[str] = set()
    q: list[str] = [base_url]
    pages: dict[str, str] = {}

    # try “contact-ish” pages first
    seeded = crawl_candidate_pages(base_url, max_pages=min(6, MAX_PAGES_PER_SITE))
    pages.update(seeded)
    seen.update(seeded.keys())

    while q and len(pages) < MAX_PAGES_PER_SITE:
        if time.monotonic() - start > SITE_BUDGET_SECONDS:
            logging.info("⏳ Site budget reached for %s (%d pages).", base_url, len(pages))
            break

        url = q.pop(0)
        if url in seen:
            continue
        seen.add(url)

        if not _same_host(url, base_url) or not _ok(url):
            continue

        html = fetch(url)
        if not html:
            continue
        pages[url] = html

        # lightweight link discovery
        try:
            for href in re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE):
                u = _norm(url, href)
                if not u or u in seen:
                    continue
                if not _same_host(u, base_url) or not _ok(u):
                    continue
                q.append(u)
        except Exception:
            pass

        time.sleep(FETCH_DELAY_MS / 1000.0)

        # early exit if we already touched some pages and any looks contact-y
        if len(pages) >= MIN_PAGES_BEFORE_FALLBACK:
            if any(re.search(pat, p, flags=re.IGNORECASE) for p in pages for pat in CONTACT_PATHS):
                break

    logging.info("Crawled %d pages on %s", len(pages), base_url)
    return pages
