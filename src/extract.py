# src/extract.py
from __future__ import annotations
from bs4 import BeautifulSoup
from html import unescape
from urllib.parse import urlparse
import re
import tldextract

from .config import (
    EMAIL_RE, MAILTO_RE,
    CONTACT_FORM_HINTS, CONTACT_KEYWORDS,
    PREFER_COMPANY_DOMAIN,
)

def _registrable_domain(url_or_host: str) -> str:
    """
    Return the registrable domain (eTLD+1) from a URL or host.
    """
    host = url_or_host
    if "://" in url_or_host:
        host = urlparse(url_or_host).netloc
    ext = tldextract.extract(host)
    if not ext.domain:
        return host.lower()
    return f"{ext.domain}.{ext.suffix}".lower() if ext.suffix else ext.domain.lower()

def _looks_like_contact_url(url: str) -> bool:
    u = url.lower()
    if "contact" in u or "get-in-touch" in u or "enquire" in u or "inquiry" in u:
        return True
    # common variants
    if re.search(r"/(kontakt|impressum|support|help)(/|$)", u):
        return True
    return False

def _looks_like_contact_title(soup: BeautifulSoup) -> bool:
    try:
        title = (soup.title.string or "").strip().lower()
    except Exception:
        title = ""
    if any(k in title for k in ["contact", "get in touch", "support", "help", "impressum", "kontakt"]):
        return True
    return False

def _extract_emails_from_html(html: str) -> set[str]:
    out: set[str] = set()
    if not isinstance(html, str):
        return out
    # mailto: links
    for m in MAILTO_RE.findall(html or ""):
        e = unescape(m).split("?")[0].strip()
        if e:
            out.add(e)
    # visible text emails
    try:
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    except Exception:
        text = ""
    for m in EMAIL_RE.findall(text):
        out.add(m.strip())
    return out

def _has_contact_form(soup: BeautifulSoup) -> bool:
    # Heuristics: a form with an email field OR a form whose class/id hints at contact,
    # OR a page that otherwise looks like a contact page (title/URL handled outside).
    forms = soup.find_all("form")
    for f in forms:
        # any hint in class/id
        classes = " ".join((f.get("class") or [])) if f.has_attr("class") else ""
        elem_id = f.get("id") or ""
        blob = f"{classes} {elem_id}".lower()
        if any(h in blob for h in CONTACT_FORM_HINTS):
            return True
        # has typical fields
        inputs = f.find_all(["input", "textarea", "select"])
        names = " ".join((i.get("name") or "") for i in inputs).lower()
        placeholders = " ".join((i.get("placeholder") or "") for i in inputs).lower()
        labels = " ".join(l.get_text(" ", strip=True).lower() for l in f.find_all("label"))
        field_blob = f"{names} {placeholders} {labels}"
        if any(k in field_blob for k in ["email", "e-mail"]) and any(k in field_blob for k in ["message", "enquiry", "inquiry", "subject"]):
            return True
    return False

def extract_contacts(
    pages: dict[str, str],
    base_url: str,
    location: str | None = None,
    preferred_domain: str | None = None,
    **kwargs,
) -> dict:
    """
    Robust extractor:
    - Accepts extra kwargs (location, preferred_domain, …) so callers never break.
    - Finds emails and contact-like pages (treated as "forms" to avoid guessing).
    Returns a dict with keys: emails, email_sources, forms, best_email, best_form
    """
    reg_base = _registrable_domain(preferred_domain or base_url)

    emails_all: set[str] = set()
    email_sources: dict[str, str] = {}
    forms: set[str] = set()

    for url, html in (pages or {}).items():
        if not isinstance(html, str):
            # Defensive: sometimes a tuple or None can sneak in
            continue

        soup = BeautifulSoup(html, "html.parser")

        # 1) Emails
        found_here = _extract_emails_from_html(html)
        for e in found_here:
            if e not in email_sources:
                email_sources[e] = url
        emails_all.update(found_here)

        # 2) Contact form / page
        page_is_contacty = _looks_like_contact_url(url) or _looks_like_contact_title(soup)
        if page_is_contacty or _has_contact_form(soup):
            forms.add(url)

    # Prefer company-domain emails if requested
    def _is_company_email(e: str) -> bool:
        try:
            host = e.split("@", 1)[1].lower()
        except Exception:
            return False
        reg = _registrable_domain(host)
        return reg.endswith(reg_base)

    prioritized = [e for e in emails_all if not PREFER_COMPANY_DOMAIN or _is_company_email(e)]
    fallback = [e for e in emails_all if e not in prioritized]

    best_email = prioritized[0] if prioritized else (fallback[0] if fallback else "")
    best_form = next(iter(forms), "")

    return {
        "emails": sorted(prioritized) + sorted(fallback),
        "email_sources": email_sources,    # map of email -> url found on
        "forms": sorted(forms),            # list of URLs that look like contact pages/forms
        "best_email": best_email,
        "best_form": best_form,
    }
