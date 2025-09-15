# src/search.py
from __future__ import annotations
import time
import re
from typing import List, Iterable
from urllib.parse import urlparse

import requests
import tldextract

from .config import (
    GOOGLE_CSE_KEY,
    GOOGLE_CSE_CX,
    GOOGLE_CSE_QPS_DELAY_MS,
    GOOGLE_CSE_MAX_RETRIES,
    MAX_GOOGLE_CANDIDATES,
    DEFAULT_LOCATION,
    BAD_HOSTS,
    CONTACT_PATHS,
    HEADERS,
    PREFER_COMPANY_DOMAIN,
)

# ---- helpers ----------------------------------------------------------

_DEF_EXCLUDE_EXT = re.compile(r"\.(pdf|docx?|xlsx?|pptx?|zip|rar)(?:$|\?)", re.I)

def _is_bad_host(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return True
    host = host.lstrip("www.")
    return any(host == bad or host.endswith("." + bad) for bad in BAD_HOSTS)

def _same_registered_domain(a: str, b: str) -> bool:
    ea = tldextract.extract(a)
    eb = tldextract.extract(b)
    return (ea.domain, ea.suffix) == (eb.domain, eb.suffix) and ea.suffix != ""

def _normalize_url(u: str) -> str:
    u = u.strip()
    if u.startswith("//"):
        return "https:" + u
    if not u.startswith("http"):
        return "https://" + u
    return u

def _google_search(query: str, num: int = 5) -> List[str]:
    """Call Google CSE with backoff, return list of urls."""
    params = {
        "key": GOOGLE_CSE_KEY,
        "cx":  GOOGLE_CSE_CX,
        "q":   query,
        "num": max(1, min(num, 10)),
        "safe": "off",
    }
    backoff = 0.5
    for attempt in range(GOOGLE_CSE_MAX_RETRIES):
        r = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params=params,
            headers=HEADERS,
            timeout=20,
        )
        if r.status_code == 200:
            data = r.json()
            items = data.get("items") or []
            urls = []
            for it in items:
                link = it.get("link", "")
                if not link:
                    continue
                link = _normalize_url(link)
                if _DEF_EXCLUDE_EXT.search(link):
                    continue
                if _is_bad_host(link):
                    continue
                urls.append(link)
            # gentle throttle
            time.sleep(GOOGLE_CSE_QPS_DELAY_MS / 1000.0)
            return urls
        elif r.status_code == 429:
            time.sleep(backoff)
            backoff = min(8.0, backoff * 2)
            continue
        else:
            # small pause but keep going
            time.sleep(0.25)
    return []

def _uniq_keep_order(seq: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for s in seq:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out

# ---- public API -------------------------------------------------------

def find_official_site(company: str, domain_hint: str | None = None) -> str | None:
    """
    Try to resolve the company's official site:
      1) If domain_hint is provided, prefer it.
      2) Try queries with DEFAULT_LOCATION to localize.
      3) Return the first non-bad host result.
    """
    if domain_hint:
        try:
            # trust the hint; normalize
            return _normalize_url(domain_hint)
        except Exception:
            pass

    qlist = [
        f"{company} official site {DEFAULT_LOCATION}",
        f"{company} website {DEFAULT_LOCATION}",
        f"{company} contact {DEFAULT_LOCATION}",
        f"{company} {DEFAULT_LOCATION}",
    ]

    for q in qlist:
        urls = _google_search(q, 5)
        for u in urls:
            if not _is_bad_host(u):
                return u
    return None

def google_contact_hunt(
    company: str,
    location: str | None = None,
    domain_for_site: str | None = None,
    limit: int = MAX_GOOGLE_CANDIDATES,
) -> List[str]:
    """
    Build a small set of likely 'contact-ish' URLs, favoring the official domain if known.
    We return raw URLs; upstream code should fetch and extract emails/forms.
    """
    loc = location or DEFAULT_LOCATION
    queries: List[str] = []

    # If we know the domain, stick to it.
    if domain_for_site:
        host = urlparse(_normalize_url(domain_for_site)).netloc
        root = tldextract.extract(host)
        site_root = ".".join([p for p in [root.domain, root.suffix] if p])
        if site_root:
            # site-restricted queries
            for path in CONTACT_PATHS + ["privacy-policy", "contact-us"]:
                queries.append(f"site:{site_root} {path}")
            queries.append(f"site:{site_root} email")
            queries.append(f"site:{site_root} mailto")
            queries.append(f"site:{site_root} contact email")
    else:
        # No domain known: search with company+location + contact-y words
        base = f"{company} {loc}"
        queries.extend([
            f"{base} contact",
            f"{base} email",
            f"{base} privacy",
            f"{base} contact us",
            f"{base} support",
            f"{base} about",
        ])

    # De-dup queries, run them, collect URLs
    urls: List[str] = []
    for q in _uniq_keep_order(queries):
        urls.extend(_google_search(q, 5))
        if len(urls) >= (limit * 2):
            break

    # Candidate post-filter:
    # - drop bad hosts
    # - if we know the official domain, prefer same registered domain
    urls = [u for u in urls if not _is_bad_host(u)]
    urls = _uniq_keep_order(urls)

    if domain_for_site and PREFER_COMPANY_DOMAIN:
        preferred, other = [], []
        for u in urls:
            try:
                if _same_registered_domain(u, domain_for_site):
                    preferred.append(u)
                else:
                    other.append(u)
            except Exception:
                other.append(u)
        urls = preferred + other

    # Keep the first N
    return urls[:max(1, limit)]
