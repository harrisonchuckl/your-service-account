# src/extract.py
from __future__ import annotations

import re
from typing import Dict, List, Set, Tuple, Iterable, Optional, Union
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    re.IGNORECASE,
)

# Skip obviously junk/placeholder emails
BAD_EMAIL_SUFFIXES = {
    ".invalid", ".test", ".example"
}
BAD_EMAIL_PARTS = {
    "example@", "noreply@", "no-reply@", "donotreply@", "do-not-reply@"
}


def _normalize_html(doc: Union[str, bytes, Tuple, None]) -> str:
    """
    Accepts:
      - str HTML
      - bytes HTML
      - tuple where first element is HTML (e.g., (html, final_url) or (html, ...))
      - None
    Returns a safe string (possibly empty).
    """
    if isinstance(doc, tuple):
        # Heuristic: first string/bytes-ish entry is the html
        for part in doc:
            if isinstance(part, (str, bytes)):
                doc = part
                break

    if doc is None:
        return ""

    if isinstance(doc, bytes):
        try:
            return doc.decode("utf-8", "ignore")
        except Exception:
            return ""

    if isinstance(doc, str):
        return doc

    # Anything else we don't recognize
    return ""


def _clean_email(e: str) -> Optional[str]:
    e = e.strip().strip(".,;:()[]{}<>")
    # lower for checks but return original casing (most MTAs are case-insensitive)
    el = e.lower()
    if any(el.endswith(sfx) for sfx in BAD_EMAIL_SUFFIXES):
        return None
    if any(p in el for p in BAD_EMAIL_PARTS):
        return None
    # Basic sanity: must still match full regex
    m = EMAIL_RE.fullmatch(e) or EMAIL_RE.fullmatch(el)
    return e if m else None


def _dedupe_preserve_order(items: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for it in items:
        if it not in seen:
            out.append(it)
            seen.add(it)
    return out


def _extract_mailtos(soup: BeautifulSoup, base_url: str) -> List[Tuple[str, str]]:
    found: List[Tuple[str, str]] = []
    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        if href.lower().startswith("mailto:"):
            email = href.split(":", 1)[1].split("?")[0].strip()
            email = _clean_email(email) or ""
            if email:
                found.append((email, base_url))
    return found


def _extract_emails_text(soup: BeautifulSoup, base_url: str) -> List[Tuple[str, str]]:
    # Search visible text for emails
    text = soup.get_text(" ", strip=True) if soup else ""
    emails = EMAIL_RE.findall(text) if text else []
    cleaned = []
    for e in emails:
        ce = _clean_email(e)
        if ce:
            cleaned.append((ce, base_url))
    return cleaned


def _looks_like_contact_form(form) -> bool:
    """
    Heuristic: form with an action containing 'contact', or contains inputs typical of contact forms.
    """
    action = (form.get("action") or "").lower()
    if "contact" in action:
        return True

    # Look for fields frequently used in contact forms
    inputs = [i.get("name", "").lower() for i in form.find_all(["input", "textarea", "select"])]
    candidates = ("email", "message", "subject", "name", "company", "phone")
    score = sum(1 for n in inputs if any(c in n for c in candidates))
    return score >= 2


def _extract_forms(soup: BeautifulSoup, base_url: str) -> List[Tuple[str, str]]:
    forms: List[Tuple[str, str]] = []
    if not soup:
        return forms
    for form in soup.find_all("form"):
        if not _looks_like_contact_form(form):
            continue
        action = (form.get("action") or "").strip()
        if not action:
            # form posts to same page
            forms.append((base_url, base_url))
            continue
        try:
            absolute = urljoin(base_url, action)
        except Exception:
            absolute = base_url
        forms.append((absolute, base_url))
    # Also catch obvious contact links masquerading as buttons
    for a in soup.find_all("a", href=True):
        txt = (a.get_text() or "").strip().lower()
        if "contact" in txt:
            try:
                absolute = urljoin(base_url, a["href"])
            except Exception:
                absolute = base_url
            forms.append((absolute, base_url))
    # de-dupe
    dedup: List[Tuple[str, str]] = []
    seen: Set[Tuple[str, str]] = set()
    for f in forms:
        if f not in seen:
            dedup.append(f)
            seen.add(f)
    return dedup


def extract_contacts(html_or_tuple: Union[str, bytes, Tuple, None], base_url: str) -> Dict[str, List[Tuple[str, str]]]:
    """
    Returns:
      {
        "emails": [(email, source_url), ...],
        "forms":  [(form_url, source_url), ...]
      }
    """
    html = _normalize_html(html_or_tuple)
    soup = BeautifulSoup(html, "html.parser") if html else None

    emails = _extract_mailtos(soup, base_url) + _extract_emails_text(soup, base_url)
    # De-dupe emails while preserving first-seen source
    seen_e: Set[str] = set()
    emails_dedup: List[Tuple[str, str]] = []
    for e, src in emails:
        if e not in seen_e:
            emails_dedup.append((e, src))
            seen_e.add(e)

    forms = _extract_forms(soup, base_url)

    return {
        "emails": emails_dedup,
        "forms": forms,
    }
