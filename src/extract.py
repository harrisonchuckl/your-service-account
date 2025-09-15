# src/extract.py
from __future__ import annotations

import re
from html import unescape
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .config import (
    EMAIL_RE,
    MAILTO_RE,
    CONTACT_FORM_HINTS,
    FORM_REQUIRE_FIELDS_ANY,
    FORM_REQUIRE_FIELDS_ALL,
    PREFER_COMPANY_DOMAIN,
    EMAIL_GUESS_ENABLE,
    GENERIC_GUESS_PREFIXES,
    BAD_HOSTS,
)

def _domain(host_or_url: str) -> str:
    try:
        host = urlparse(host_or_url).hostname or host_or_url
        return host.lower()
    except Exception:
        return host_or_url.lower()

def _same_domain(a: str, b: str) -> bool:
    return _domain(a) == _domain(b)

def _decode_cfemail(encoded: str) -> str:
    """
    Cloudflare email obfuscation decoder.
    `encoded` should be hex string after data-cfemail attribute.
    """
    try:
        r = int(encoded[:2], 16)
        out = "".join(chr(int(encoded[i : i + 2], 16) ^ r) for i in range(2, len(encoded), 2))
        return out
    except Exception:
        return ""

def _gather_emails(html: str) -> Set[str]:
    emails: Set[str] = set()

    # 1) mailto: links
    for m in MAILTO_RE.finditer(html):
        addr = m.group(1)
        if addr:
            emails.add(addr.strip())

    # 2) direct emails in text
    for m in EMAIL_RE.finditer(html):
        emails.add(m.group(0).strip())

    # 3) Cloudflare obfuscation
    # data-cfemail="HEX"
    for m in re.finditer(r'data-cfemail="([0-9a-fA-F]+)"', html):
        decoded = _decode_cfemail(m.group(1))
        if decoded and "@" in decoded:
            emails.add(decoded.strip())

    return emails

def _prefer_domain(emails: Set[str], preferred_domain: Optional[str]) -> Optional[str]:
    if not emails:
        return None
    if preferred_domain:
        pd = _domain(preferred_domain)
        same = [e for e in emails if _domain(e.split("@")[-1]) == pd]
        if same:
            return sorted(same, key=len)[0]
    # else return the shortest-looking businessy address
    # Avoid obvious no-reply types
    ranked = sorted(
        emails,
        key=lambda e: (
            any(x in e for x in ("noreply", "no-reply", "do-not-reply")),
            len(e),
        ),
    )
    return ranked[0] if ranked else None

def _find_contact_forms(base_url: str, soup: BeautifulSoup) -> List[str]:
    forms: List[str] = []
    # Any explicit contact-page hint in headings / hero text
    text = soup.get_text(" ", strip=True).lower()
    if any(k in text for k in ("contact us", "get in touch", "enquire", "enquiry", "email us")):
        pass  # just a soft signal; the actual form detection is below

    for form in soup.find_all("form"):
        form_text = form.get_text(" ", strip=True).lower()
        attrs = " ".join(f"{k}={v}" for k, v in form.attrs.items()).lower()
        # quick hints (plugins, etc.)
        if any(h in attrs or h in form_text for h in CONTACT_FORM_HINTS):
            forms.append(base_url)
            continue

        # look for required fields
        inputs = " ".join(
            [
                (inp.get("name") or "") + " " + (inp.get("id") or "") + " " + (inp.get("placeholder") or "")
                for inp in form.find_all(["input", "textarea", "select"])
            ]
        ).lower()

        any_ok = any(any_key in inputs for any_key in FORM_REQUIRE_FIELDS_ANY)
        all_ok = all(all_key in inputs for all_key in FORM_REQUIRE_FIELDS_ALL)
        if any_ok and all_ok:
            forms.append(base_url)

    # also consider explicit “contact” links on the page pointing to another URL
    for a in soup.find_all("a", href=True):
        label = (a.get_text(" ", strip=True) or "").lower()
        href = a["href"]
        if any(k in label for k in ("contact", "enquire", "get in touch")):
            absu = urljoin(base_url, href)
            forms.append(absu)

    # de-dup keeping order
    seen = set()
    ordered = []
    for u in forms:
        if u not in seen:
            ordered.append(u)
            seen.add(u)
    return ordered

def _safe_guess(preferred_domain: Optional[str], company: Optional[str]) -> Optional[str]:
    if not EMAIL_GUESS_ENABLE or not preferred_domain:
        return None
    dom = _domain(preferred_domain)
    if any(bad in dom for bad in BAD_HOSTS):
        return None
    guesses = [f"{p}@{dom}" for p in GENERIC_GUESS_PREFIXES]
    # a tiny nod to “company-ish” match: prefer ‘info@’ only
    return guesses[0] if guesses else None

def extract_contacts(html: str, base_url: str, preferred_domain: Optional[str] = None, company: Optional[str] = None) -> Dict[str, Optional[str] | List[str]]:
    """
    Parse one HTML page. Return a dict with:
      - emails: list[str]
      - forms: list[str]
      - email (alias of best_email)
      - form_url (alias of best_form)
    """
    # html may sometimes arrive as bytes; force to str
    if isinstance(html, (bytes, bytearray)):
        html = html.decode("utf-8", errors="ignore")

    soup = BeautifulSoup(html, "html.parser")
    raw = soup.decode()

    emails = _gather_emails(raw)

    # If we prefer the site’s domain, filter to that first
    if PREFER_COMPANY_DOMAIN and preferred_domain:
        dom = _domain(preferred_domain)
        emails = {e for e in emails if e.split("@")[-1].lower().endswith(dom)}

    best_email = _prefer_domain(emails, preferred_domain)
    forms = _find_contact_forms(base_url, soup)
    best_form = forms[0] if forms else None

    # last-ditch: a very conservative guess (only if enabled)
    guessed = None
    if not best_email and not best_form:
        guessed = _safe_guess(preferred_domain, company)

    # Provide both detailed lists and convenient aliases
    result = {
        "emails": sorted(emails),
        "forms": forms,
        "best_email": best_email,
        "best_form": best_form,
        # Aliases for existing code paths:
        "email": best_email,
        "form_url": best_form,
        "guessed_email": guessed,
    }
    return result
