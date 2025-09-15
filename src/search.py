# src/search.py
import logging
import time
import random
from urllib.parse import urlparse

import requests

from .config import (
    BAD_HOSTS,
    DEFAULT_LOCATION,  # not used here but kept for parity
    GOOGLE_CSE_KEY,
    GOOGLE_CSE_CX,
    GOOGLE_CSE_QPS_DELAY_MS,
    GOOGLE_CSE_MAX_RETRIES,
)

_GOOGLE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"

def _host_ok(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    if not host:
        return False
    return host not in BAD_HOSTS

def _google_search(query: str, num: int = 5) -> list[str]:
    """Call Google CSE with throttling + retry/backoff. Return list of links or [] on issues."""
    if not GOOGLE_CSE_KEY or not GOOGLE_CSE_CX:
        logging.info("[search] Google CSE not configured; skipping")
        return []

    params = {
        "key": GOOGLE_CSE_KEY,  # already stripped in config
        "cx": GOOGLE_CSE_CX,    # already stripped in config
        "q": query,
        "num": num,
        "safe": "off",
    }

    delay = max(0, GOOGLE_CSE_QPS_DELAY_MS) / 1000.0

    for attempt in range(GOOGLE_CSE_MAX_RETRIES):
        try:
            r = requests.get(_GOOGLE_ENDPOINT, params=params, timeout=20)
            # Retry on common transient conditions
            if r.status_code in (429, 500, 502, 503, 504):
                wait = (2 ** attempt) + random.random()
                logging.warning(f"[search] Google CSE {r.status_code}; backing off {wait:.1f}s (attempt {attempt+1})")
                time.sleep(wait)
                continue

            r.raise_for_status()
            data = r.json()
            items = data.get("items", []) or []
            links = [it.get("link") for it in items if it.get("link")]
            time.sleep(delay)  # QPS pacing
            return links

        except requests.RequestException as e:
            # Network/HTTP error: backoff and retry
            wait = (2 ** attempt) + random.random()
            logging.warning(f"[search] Exception {type(e).__name__}: {e}; backing off {wait:.1f}s (attempt {attempt+1})")
            time.sleep(wait)

    logging.warning("[search] Google CSE failed after retries; returning no results")
    return []

def _first_good_url(links: list[str]) -> str | None:
    for url in links:
        if _host_ok(url):
            return url
    return None

def _google_first_good_url(query: str) -> str | None:
    links = _google_search(query, 5)
    return _first_good_url(links)

def find_official_site(company: str, domain_hint: str | None = None) -> str | None:
    """
    Use Google CSE to find the official site. Returns URL or None.
    """
    # Prefer domain already on the row if present and sane
    if domain_hint:
        try:
            parsed = urlparse(domain_hint if domain_hint.startswith("http") else f"https://{domain_hint}")
            if parsed.netloc and _host_ok(domain_hint):
                return parsed.geturl()
        except Exception:
            pass

    # Try a couple of queries that usually work well
    queries = [
        f"{company} official site",
        f"{company} website",
        f"{company} {DEFAULT_LOCATION} website",
    ]

    for q in queries:
        url = _google_first_good_url(q)
        if url:
            logging.info(f"[{company}] Google resolved: {url}")
            return url

    logging.info(f"[{company}] No search provider result.")
    return None
