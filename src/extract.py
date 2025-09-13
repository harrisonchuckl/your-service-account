import re, json
from html import unescape
from bs4 import BeautifulSoup

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}", re.I)

GENERIC_PRIORITY = [
    "info@", "hello@", "contact@", "enquiries@", "enquiry@", "boxoffice@",
    "bookings@", "sales@", "admin@", "office@", "support@", "team@", "press@", "media@", "privacy@", "dataprotection@", "dpo@"
]

BAD_PREFIXES = ["example@", "test@", "noreply@", "no-reply@", "donotreply@"]

def _is_valid_email(email: str) -> bool:
    e = (email or "").lower()
    return bool(e) and not any(b in e for b in BAD_PREFIXES)

def _score_email(email: str, source_url: str, page_text_lower: str, preferred_domain: str = None, location: str = None) -> int:
    score = 0
    e = (email or "").lower()
    src = (source_url or "").lower()

    if preferred_domain and e.split("@")[-1].endswith(preferred_domain):
        score += 3
    if any(e.startswith(p) for p in GENERIC_PRIORITY):
        score += 2
    if location and location.lower() in page_text_lower:
        score += 1
    if "contact" in src:
        score += 1
    return score

_OBFUSCATE_PATTERNS = [
    (re.compile(r"\s*(?:\(|\[)?at(?:\)|\])\s*", re.I), "@"),
    (re.compile(r"\s*(?:\(|\[)?\[?@(?:\)|\])?\s*", re.I), "@"),
    (re.compile(r"\s*(?:\(|\[)?dot(?:\)|\])\s*", re.I), "."),
    (re.compile(r"\s*\(dot\)\s*", re.I), "."),
    (re.compile(r"\s*\[dot\]\s*", re.I), "."),
]

def _deobfuscate(text: str) -> str:
    s = unescape(text or "")
    for rx, repl in _OBFUSCATE_PATTERNS:
        s = rx.sub(repl, s)
    return s

def _emails_from_text(s: str):
    return EMAIL_RE.findall(s or "")

def _emails_from_json_ld(soup: BeautifulSoup):
    emails = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "{}")
        except Exception:
            continue
        def walk(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k.lower() == "email" and isinstance(v, str):
                        emails.append(v)
                    else:
                        walk(v)
            elif isinstance(obj, list):
                for it in obj:
                    walk(it)
        walk(data)
    return [e for e in emails if _is_valid_email(e)]

def extract_contacts(html_by_url, preferred_domain=None, location=None):
    """
    Given {url: html}, return best email + source and a contact form URL if seen.
    """
    best_email, best_src, best_score = None, None, -1
    form_url = None

    for url, html in html_by_url.items():
        soup = BeautifulSoup(html, "html.parser")

        # Whole-page text (once)
        raw_text = soup.get_text(" ", strip=True)[:700000]
        text = _deobfuscate(raw_text)
        text_low = text.lower()

        # (A) contact form / contact URL
        if not form_url:
            if "contact" in (url or "").lower():
                form_url = url
            else:
                form = soup.find("form")
                if form:
                    id_txt = (form.get("id", "") or "").lower()
                    cls_txt = " ".join(form.get("class", [])).lower() if isinstance(form.get("class", []), list) else str(form.get("class", "")).lower()
                    if "contact" in id_txt or "contact" in cls_txt:
                        form_url = url

        # (B) mailto links
        for a in soup.select('a[href^="mailto:"]'):
            raw = (a.get("href") or "").replace("mailto:", "").split("?")[0].strip()
            raw = _deobfuscate(raw)
            if not _is_valid_email(raw):
                continue
            score = _score_email(raw, url, text_low, preferred_domain, location)
            if score > best_score:
                best_email, best_src, best_score = raw, url, score

        # (C) JSON-LD "email" fields
        for em in _emails_from_json_ld(soup):
            score = _score_email(em, url, text_low, preferred_domain, location)
            if score > best_score:
                best_email, best_src, best_score = em, url, score

        # (D) visible text emails (after deobfuscation)
        for em in _emails_from_text(text):
            if not _is_valid_email(em):
                continue
            score = _score_email(em, url, text_low, preferred_domain, location)
            if score > best_score:
                best_email, best_src, best_score = em, url, score

    return {
        "ContactEmail": best_email or "",
        "ContactFormURL": form_url or "",
        "SourceURL": best_src or (form_url or "")
    }
