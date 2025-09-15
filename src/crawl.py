# src/crawl.py
from __future__ import annotations

import logging
import time
import re
from collections import deque
from dataclasses import dataclass
from typing import Iterable, List, Set, Tuple
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

from .config import (
    USER_AGENT,
    HTTP_TIMEOUT,
    FETCH_DELAY_MS,
    MAX_PAGES_PER_SITE,
    MIN_PAGES_BEFORE_FALLBACK,
    SITE_BUDGET_SECONDS,
    CONTACT_PATHS,
    CONTACT_KEYWORDS,
    BAD_EXTENSIONS,
    BAD_PATH_SNIPPETS,
    SCRAPERAPI_KEY,
    SCRAPERAPI_BASE,
    SCRAPERAPI_COUNTRY,
    SCRAPERAPI_RENDER,
)

log = logging.getLogger(__name__)

# ---------- Helpers

def _canonical(u: str) -> str:
    """Normalise URL for deduping and host checks."""
    try:
        p = urlparse(u)
        # Strip fragments & default ports
        netloc = p.hostname or ""
        if p.port and p.port not in (80, 443):
            netloc = f"{netloc}:{p.port}"
        return urlunparse((p.scheme or "https", netloc, p.path or "/", "", p.query, ""))
    except Exception:
        return u

def _same_host(a: str, b: str) -> bool:
    try:
        ha = urlparse(a).hostname or ""
        hb = urlparse(b).hostname or ""
        return ha.lower() == hb.lower()
    except Exception:
        return False

def _is_bad_path(path: str) -> bool:
    path_lower = path.lower()
    if any(path_lower.endswith(ext) for ext in BAD_EXTENSIONS):
        return True
    if any(snippet in path_lower for snippet in BAD_PATH_SNIPPETS):
        return True
    return False

def _score_link(href: str) -> int:
    """
    Higher score = crawl sooner. Contact-like URLs first, then about/privacy,
    then short, shallow paths. Penalise deep/asset paths.
    """
    pth = urlparse(href).path.lower()
    score = 0
    # Top priority: contact-ish
    for pat in CONTACT_PATHS:
        if re.search(pat, pth):
            score += 100
            break
    # Secondary: typical info pages
    if any(x in pth for x in ("/about", "/team", "/impressum", "/privacy", "/legal")):
        score += 25
    # Short & shallow boost
    depth = pth.count("/")
    score += max(0, 10 - depth)
    # Penalise clearly static-ish paths
    if _is_bad_path(pth):
        score -= 50
    return score

def _extract_links(base_url: str, html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        abs_url = urljoin(base_url, href)
        links.add(abs_url)
    return list(links)

def _client_headers() -> dict:
    return {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}

def _scraperapi_url(target: str) -> str:
    params = {
        "api_key": SCRAPERAPI_KEY,
        "url": target,
    }
    if SCRAPERAPI_COUNTRY:
        params["country_code"] = SCRAPERAPI_COUNTRY
    if SCRAPERAPI_RENDER:
        params["render"] = "true"
    # Build querystring manually to avoid extra deps
    from urllib.parse import urlencode
    return f"{SCRAPERAPI_BASE}?{urlencode(params)}"

# ---------- Public API

def fetch(url: str) -> str | None:
    """
    Fetch a single URL and return text HTML, or None on failure.
    Uses ScraperAPI if configured, otherwise direct requests.
    """
    try:
        target = url
        if SCRAPERAPI_KEY:
            target = _scraperapi_url(url)
        r = requests.get(target, headers=_client_headers(), timeout=HTTP_TIMEOUT, allow_redirects=True)
        ct = r.headers.get("Content-Type", "")
        if "text/html" not in ct and "application/xhtml+xml" not in ct:
            return None
        r.raise_for_status()
        return r.text
    except Exception as e:
        log.info("Fetch failed for %s: %s", url, e)
        return None

def crawl_candidate_pages(start_url: str) -> List[Tuple[str, str]]:
    """
    Breadth-first crawl of same-host pages, prioritising ‘contact-ish’ paths.
    Returns list of (url, html) limited by MAX_PAGES_PER_SITE and time budget.
    """
    start_ts = time.time()
    out: List[Tuple[str, str]] = []
    seen: Set[str] = set()
    q: deque[str] = deque()

    root = _canonical(start_url)
    q.append(root)
    seen.add(_canonical(root))

    pages_fetched = 0
    min_pages = max(1, MIN_PAGES_BEFORE_FALLBACK)

    while q and pages_fetched < MAX_PAGES_PER_SITE:
        # Time budget guard
        if time.time() - start_ts > SITE_BUDGET_SECONDS:
            log.info("[INFO] Time budget hit (%.1fs); stopping site crawl.", SITE_BUDGET_SECONDS)
            break

        url = q.popleft()

        html = fetch(url)
        if not html:
            continue

        out.append((url, html))
        pages_fetched += 1

        # Collect internal links, score, and enqueue
        links = _extract_links(url, html)
        internal = [u for u in links if _same_host(u, root)]
        # De-dupe and filter obviously bad
        next_links = []
        for u in internal:
            cu = _canonical(u)
            if cu in seen:
                continue
            if _is_bad_path(urlparse(cu).path):
                continue
            seen.add(cu)
            next_links.append(cu)

        # Prioritise by score (higher first)
        next_links.sort(key=_score_link, reverse=True)
        for u in next_links:
            q.append(u)

        # Gentle politeness
        if FETCH_DELAY_MS > 0:
            time.sleep(FETCH_DELAY_MS / 1000.0)

        # Keep going until limits/time; the caller decides when to stop based on findings
        # We purposely do NOT bail early here; extraction decides when it's “good enough”.

    # Ensure we at least tried a few pages before the caller falls back to Google
    if len(out) < min_pages:
        log.info("[INFO] Only crawled %d page(s) on %s (min before fallback: %d).",
                 len(out), start_url, min_pages)

    return out
