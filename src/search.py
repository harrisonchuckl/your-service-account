# src/search.py
from __future__ import annotations

import time
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

import requests

from .config import (
    BAD_HOSTS,
    GOOGLE_CSE_KEY,
    GOOGLE_CSE_CX,
    GOOGLE_CSE_QPS_DELAY_MS,
    GOOGLE_CSE_MAX_RETRIES,
    MAX_GOOGLE_CANDIDATES,
)

log = logging.getLogger(__name__)

CSE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"


def _host(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def _is_bad(url: str) -> bool:
    h = _host(url)
    return any(h.endswith(bad) for bad in BAD_HOSTS)


def _google_search(query: str, num: int = 5) -> List[Dict[str, Any]]:
    """
    Thin wrapper over Google Programmable Search JSON API with retry/backoff.
    Returns the raw 'items' list (may be empty).
    """
    if not GOOGLE_CSE_KEY or not GOOGLE_CSE_CX:
        return []

    params = {
        "key": GOOGLE_CSE_KEY.strip(),
        "cx": GOOGLE_CSE_CX.strip(),
        "q": query,
        "num": max(1, min(10, num)),
        "safe": "off",
    }

    delay = max(100, GOOGLE_CSE_QPS_DELAY_MS) / 1000.0
    tries = max(1, GOOGLE_CSE_MAX_RETRIES)

    last_exc: Optional[Exception] = None
    for attempt in range(tries):
        try:
            r = requests.get(CSE_ENDPOINT, params=params, timeout=15)
            if r.status_code == 200:
                data = r.json()
                return data.get("items", []) or []
            # Handle 429/5xx with backoff
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(delay * (2 ** attempt))
                continue
            # Other errors: raise
            r.raise_for_status()
        except Exception as e:
            last_exc = e
            time.sleep(delay * (2 ** attempt))

    if last_exc:
        raise last_exc
    return []


def _first_good_url(items: List[Dict[str, Any]]) -> Optional[str]:
    for it in items:
        url = (it.get("link") or "").strip()
        if not url or _is_bad(url):
            continue
        return url
    return None


def _prefer_domain(urls: List[str], domain_hint: Optional[str]) -> Optional[str]:
    if not urls:
        return None
    if not domain_hint:
        return urls[0]
    dom = domain_hint.lower().lstrip("@").strip()
    for u in urls:
        if _host(u).endswith(dom):
            return u
    return urls[0]


def find_official_site(company: str, domain_hint: Optional[str] = None) -> Optional[str]:
    """
    Try to get the company's official site via CSE. If a domain hint is provided,
    prefer URLs on that domain.
    """
    queries = []
    company_clean = (company or "").strip()
    if not company_clean:
        return None

    if domain_hint:
        dom = domain_hint.strip().lower()
        queries.extend([
            f"{company_clean} site:{dom}",
            f"{company_clean} official site site:{dom}",
        ])

    # General queries
    queries.extend([
        f"{company_clean} official site",
        f"{company_clean} website",
        f"{company_clean}",
    ])

    candidates: List[str] = []
    seen = set()
    for q in queries:
        items = _google_search(q, num=5)
        for it in items:
            url = (it.get("link") or "").strip()
            if not url or _is_bad(url):
                continue
            if url not in seen:
                candidates.append(url)
                seen.add(url)
        if candidates:
            break  # good enough

    if not candidates:
        return None
    chosen = _prefer_domain(candidates, domain_hint)
    print(f"[INFO] [{company_clean}] Google resolved: {chosen}")
    return chosen


def google_contact_hunt(
    company: str,
    location: Optional[str] = None,
    domain_for_site: Optional[str] = None,
    limit: int = 4,
) -> List[str]:
    """
    Use CSE to find contact-ish pages for a company. Returns a list of candidate URLs.
    """
    company = (company or "").strip()
    location = (location or "").strip()
    limit = max(1, min(limit, MAX_GOOGLE_CANDIDATES))

    queries: List[str] = []

    # If we know the official domain, focus there first
    if domain_for_site:
        dom = domain_for_site.strip().lower()
        base = f"site:{dom}"
        queries.extend([
            f"{base} contact",
            f"{base} contact us",
            f"{base} kontakt",
            f"{base} impressum",
            f"{base} privacy",
            f"{base} support",
        ])

    # Company + contact permutations
    queries.extend([
        f"{company} contact",
        f"{company} contact us",
        f"{company} email",
        f"{company} privacy",
    ])
    if location:
        queries.extend([
            f"{company} {location} contact",
            f"{company} {location} email",
        ])

    results: List[str] = []
    seen = set()

    for q in queries:
        try:
            items = _google_search(q, num=5)
        except Exception:
            # swallow CSE transient failures so the run continues
            items = []

        for it in items:
            url = (it.get("link") or "").strip()
            if not url or _is_bad(url):
                continue
            # prefer obviously contact-ish pages
            path = urlparse(url).path.lower()
            if any(tok in path for tok in ("contact", "kontakt", "impressum", "privacy")) or domain_for_site and _host(url).endswith(domain_for_site.lower()):
                if url not in seen:
                    results.append(url)
                    seen.add(url)
                    if len(results) >= limit:
                        break
        if len(results) >= limit:
            break

        time.sleep(max(0.1, GOOGLE_CSE_QPS_DELAY_MS / 1000.0))

    if results:
        print(f"[INFO] Google candidates: {results}")
    else:
        print("[INFO] Google candidates: []")

    return results
