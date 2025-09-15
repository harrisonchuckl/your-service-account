# src/extract.py
from __future__ import annotations

import re
from html import unescape
from typing import Dict, Set, Any
from urllib.parse import urlparse

import tldextract
from bs4 import BeautifulSoup

# ---- Safe imports from config with sensible fallbacks ----
# Email regexes
try:
    from .config import EMAIL_RE  # compiled regex
except Exception:
    EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)

try:
    from .config import MAILTO_RE  # compiled regex for mailto:
except Exception:
    MAILTO_RE = re.compile(r"mailto:([^\s\"'>?#]+)", re.I)

# Prefer company-domain emails?
try:
    from .config import PREFER_COMPANY_DOMAIN  # bool
except Exception:
    PREFER_COMPANY_DOMAIN = True

# Hints that a <form> is a contact form
try:
    from .config import CONTACT_FORM_HINTS  # iterable[str]
except Exception:
    CONTACT_FORM_HINTS = {
        "contact", "enquiry", "inquiry", "message", "support", "help",
        "feedback", "get-in-touch", "getintouch"
    }


# ---- Helpers ----
def _registrable_domain(url_or_host: str) -> str:
    """Return eTLD+1 from a URL or host (e.g., www.foo.co.uk -> foo.co.uk)."""
    if not url_or_host:
        return ""
    host = url_or_host
    if "://" in url_or_host:
        host = urlparse(url_or_host).netloc
    ext = tldextract.extract(host)
    if not ext.domain:
        return host.lower()
    return f"{ext.domain}.{ext.suffix}".lower() if ext.suffix else ext.domain.lower()


def _looks_like_contact_url(url: str) -> bool:
    u = (url or "").lower()
    if any(k in u for k in ["contact", "get-in-touch", "enquire", "inquiry", "kontakt", "impressum"]):
        return True
    # common “/support”, “/help” pages
    if re.search(r"/(support|help)(/|$)", u):
        return True
    return False


def _looks_like_contact_title(soup: BeautifulSoup) -> bool:
    try:
        title = (soup.title.string or "").strip().lower()
    except Exception:
        title = ""
    return any(k in title for k in ["contact", "get in touch", "support", "help", "impressum", "kontakt"])


def _extract_emails_from_html(html: str) -> Set[str]:
    out: Set[str] = set()
    if not isinstance(html, str):
        return out

    # mailto: links
    for m in MAILTO_RE.findall(html or ""):
        e = unescape(m).split("?")[0].strip()
        if e:
            out.add(e)

    # visible text
    try:
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    except Exception:
        text = ""
    for m in EMAIL_RE.findall(text):
        out.add(m.strip())

    return out


def _has_contact_form(soup: BeautifulSoup) -> bool:
    forms = soup.find_all("form")
    for f in forms:
        classes = " ".join((f.get("class") or [])) if f.has_attr("class") else ""
        elem_id = f.get("id") or ""
        blob = f"{classes} {elem_id}".lower()
        if any(h in blob for h in CONTACT_FORM_HINTS):
            return True

        # field-based heuristic
        inputs = f.find_all(["input", "textarea", "select"])
        names = " ".join((i.get("name") or "") for i in inputs).lower()
        placeholders = " ".join((i.get("placeholder") or "") for i in inputs).lower()
        labels = " ".join(l.get_text(" ", strip=True).lower() for l in f.find_all("label"))
        field_blob = f"{names} {placeholders} {labels}"
        if any(k in field_blob for k in ["email", "e-mail"]) and any(
            k in field_blob for k in ["message", "enquiry", "inquiry", "subject"]
        ):
            return True
    return False


# ---- Public API (backwards-compatible signature) ----
def extract_contacts(
    pages: Dict[str, Any],
    base_url: str | None = None,                 # now OPTIONAL
    location: str | None = None,                 # accepted, not required
    preferred_domain: str | None = None,         # accepted
    **kwargs,                                    # absorb any future args
) -> dict:
    """
    Extract emails and detect contact-like pages.
    Compatible with older callers that *don't* pass base_url.

    Returns:
      {
        "emails": [list of emails, preferring company-domain if configured],
        "email_sources": {email: url_where_found},
        "forms": [list of URLs that look like contact pages/forms],
        "best_email": "chosen email or ''",
        "best_form": "chosen form URL or ''",
      }
    """
    # Derive a reasonable base if not provided
    if not base_url:
        if preferred_domain:
            base_url = preferred_domain
        elif pages:
            base_url = next(iter(pages.keys()))
        else:
            base_url = ""

    reg_base = _registrable_domain(preferred_domain or base_url)

    emails_all: Set[str] = set()
    email_sources: Dict[str, str] = {}
    forms: Set[str] = set()

    for url, html in (pages or {}).items():
        # Some callers accidentally pass tuples or None; ignore non-strings safely
        if not isinstance(html, str):
            continue

        soup = BeautifulSoup(html, "html.parser")

        # 1) Emails
        found = _extract_emails_from_html(html)
        for e in found:
            if e not in email_sources:
                email_sources[e] = url
        emails_all.update(found)

        # 2) Contact forms / pages
        if _looks_like_contact_url(url) or _looks_like_contact_title(soup) or _has_contact_form(soup):
            forms.add(url)

    # Prefer company-domain emails when configured
    def _is_company_email(e: str) -> bool:
        try:
            host = e.split("@", 1)[1].lower()
        except Exception:
            return False
        reg = _registrable_domain(host)
        return bool(reg_base) and reg.endswith(reg_base)

    prioritized = [e for e in emails_all if (not PREFER_COMPANY_DOMAIN) or _is_company_email(e)]
    fallback = [e for e in emails_all if e not in prioritized]

    best_email = prioritized[0] if prioritized else (fallback[0] if fallback else "")
    best_form = next(iter(forms), "")

    return {
        "emails": sorted(prioritized) + sorted(fallback),
        "email_sources": email_sources,
        "forms": sorted(forms),
        "best_email": best_email,
        "best_form": best_form,
    }
