# src/extract.py
from __future__ import annotations
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from typing import Any, Dict, List, Tuple, Optional

# Simple email regex (good enough for web scraping)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.I)

CONTACT_HINTS = (
    "contact", "enquiry", "inquiry", "support", "help", "get-in-touch", "feedback",
    "sales", "customer", "service", "reach", "connect"
)

def _ensure_text(html: Any) -> str:
    if html is None:
        return ""
    if isinstance(html, bytes):
        try:
            return html.decode("utf-8", errors="ignore")
        except Exception:
            return html.decode(errors="ignore")
    return str(html)

def _dedupe(seq):
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def _extract_emails_from_text(text: str) -> List[str]:
    return _dedupe([m.group(0) for m in EMAIL_RE.finditer(text)])

def _extract_emails(soup: BeautifulSoup) -> List[str]:
    emails: List[str] = []
    # mailto: links
    for a in soup.select('a[href^="mailto:"]'):
        href = a.get("href", "")
        addr = href.split("mailto:", 1)[-1].split("?")[0].strip()
        if addr:
            emails.append(addr)
    # visible text
    emails.extend(_extract_emails_from_text(soup.get_text(" ", strip=True)))
    # Meta tags sometimes hide emails
    for tag in soup.find_all(["meta", "script"]):
        content = (tag.get("content") or tag.string or "") or ""
        if content:
            emails.extend(_extract_emails_from_text(content))
    # Clean+dedupe
    emails = [e.strip().strip(".,;:()[]{}<>") for e in emails if "@" in e]
    emails = [e.lower() for e in emails]
    return _dedupe(emails)

def _extract_forms(soup: BeautifulSoup, base_url: Optional[str]) -> List[str]:
    actions: List[str] = []
    # Form actions
    for f in soup.find_all("form"):
        action = (f.get("action") or "").strip()
        if not action:
            continue
        if base_url:
            action = urljoin(base_url, action)
        actions.append(action)
    # Links that look like “contact” pages
    for a in soup.find_all("a"):
        href = (a.get("href") or "").strip()
        if not href:
            continue
        label = (a.get_text(" ", strip=True) or "").lower()
        href_l = href.lower()
        looks_contact = any(h in href_l for h in CONTACT_HINTS) or any(h in label for h in CONTACT_HINTS)
        if looks_contact:
            if base_url:
                href = urljoin(base_url, href)
            actions.append(href)
    # Keep only distinct, http(s) targets
    actions = [u for u in actions if u.startswith("http")]
    return _dedupe(actions)

def extract_contacts(
    html_or_tuple: Any,
    base_url: Optional[str] = None,
    **_ignore_kwargs: Any,  # swallows legacy kwargs like preferred_domain
) -> Dict[str, Any]:
    """
    Backward-compatible extractor.

    Accepts:
      - extract_contacts(html)
      - extract_contacts(html, base_url)
      - extract_contacts((html, base_url))
      - extract_contacts(html, base_url, preferred_domain=...)
    Returns:
      {
        "emails": [str, ...],
        "forms": [str, ...],
        # single-item aliases for older callers:
        "email": Optional[str],
        "form": Optional[str],
        "notes": [str, ...]
      }
    """
    # Legacy: (html, base_url) passed as a single tuple
    if isinstance(html_or_tuple, tuple) and len(html_or_tuple) >= 1 and base_url is None:
        html_or_tuple = list(html_or_tuple)  # type: ignore
        _html = _ensure_text(html_or_tuple[0])
        _base = html_or_tuple[1] if len(html_or_tuple) > 1 else None
    else:
        _html = _ensure_text(html_or_tuple)
        _base = base_url

    soup = BeautifulSoup(_html, "html.parser")

    emails = _extract_emails(soup)
    forms = _extract_forms(soup, _base)

    result: Dict[str, Any] = {
        "emails": emails,
        "forms": forms,
        "email": emails[0] if emails else None,
        "form": forms[0] if forms else None,
        "notes": [],
    }
    return result
