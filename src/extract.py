import re
from bs4 import BeautifulSoup

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}", re.I)

GENERIC_PRIORITY = [
    "info@", "hello@", "contact@", "enquiries@", "enquiry@", "boxoffice@",
    "bookings@", "sales@", "admin@", "office@", "support@", "team@", "press@", "media@"
]

BAD_PREFIXES = ["example@", "test@", "noreply@", "no-reply@", "donotreply@"]


def _is_valid_email(email: str) -> bool:
    e = (email or "").lower()
    return bool(e) and not any(b in e for b in BAD_PREFIXES)


def _score_email(email: str, source_url: str, page_text_lower: str, preferred_domain: str = None, location: str = None) -> int:
    """
    Score candidates so we pick the most useful one:
    +3 same company domain
    +2 generic inbox (info@, contact@, etc.)
    +1 page mentions the location (e.g. Ely)
    +1 email was found on a 'contact' URL
    """
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


def extract_contacts(html_by_url, preferred_domain=None, location=None):
    """
    Given {url: html}, return best email + source and a contact form URL if seen.
    """
    best_email, best_src, best_score = None, None, -1
    form_url = None

    for url, html in html_by_url.items():
        soup = BeautifulSoup(html, "html.parser")

        # Whole-page text (lower-cased once for scoring)
        text = soup.get_text(" ", strip=True)[:600000]
        text_low = text.lower()

        # (A) Look for contact-like form or URL
        if not form_url:
            if "contact" in (url or "").lower():
                form_url = url
            else:
                # Try to detect a contact form element
                form = soup.find("form")
                if form:
                    id_txt = (form.get("id", "") or "").lower()
                    cls_txt = " ".join(form.get("class", [])).lower() if isinstance(form.get("class", []), list) else str(form.get("class", "")).lower()
                    if "contact" in id_txt or "contact" in cls_txt:
                        form_url = url

        # (B) mailto: links
        for a in soup.select('a[href^="mailto:"]'):
            raw = (a.get("href") or "").replace("mailto:", "").split("?")[0].strip()
            if not _is_valid_email(raw):
                continue
            score = _score_email(raw, url, text_low, preferred_domain, location)
            if score > best_score:
                best_email, best_src, best_score = raw, url, score

        # (C) visible emails in text
        for m in EMAIL_RE.findall(text):
            raw = m.strip()
            if not _is_valid_email(raw):
                continue
            score = _score_email(raw, url, text_low, preferred_domain, location)
            if score > best_score:
                best_email, best_src, best_score = raw, url, score

    return {
        "ContactEmail": best_email or "",
        "ContactFormURL": form_url or "",
        "SourceURL": best_src or (form_url or "")
    }
