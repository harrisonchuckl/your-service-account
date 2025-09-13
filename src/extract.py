import re
from bs4 import BeautifulSoup
from .config import PRIORITISE_GENERIC

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}", re.I)

GENERIC_PRIORITY_PREFIXES = [
    "info@", "hello@", "contact@", "enquiries@", "enquiry@",
    "boxoffice@", "bookings@", "sales@", "admin@", "office@", "support@", "team@", "press@", "media@"
]

def extract_contacts(html_by_url):
    best_email, form_url, source_url = None, None, None
    candidates = []

    for url, html in html_by_url.items():
        soup = BeautifulSoup(html, "html.parser")

        # mailto links
        for a in soup.select('a[href^="mailto:"]'):
            email = (a.get("href") or "").replace("mailto:", "").split("?")[0].strip()
            if valid_email(email):
                candidates.append((email, url))

        # visible text emails
        text = soup.get_text(" ", strip=True)
        for m in EMAIL_RE.findall(text[:500000]):
            if valid_email(m):
                candidates.append((m, url))

        # any contact-looking form
        if not form_url:
            if "contact" in url.lower():
                form_url = url
            else:
                form = soup.find("form")
                if form and ("contact" in (form.get("id","") + " ".join(form.get("class", []) if isinstance(form.get("class"), list) else [str(form.get("class",""))]).lower())):
                    form_url = url

    chosen = None
    if candidates:
        if PRIORITISE_GENERIC:
            generic = [c for c in candidates if any(c[0].lower().startswith(p) for p in GENERIC_PRIORITY_PREFIXES)]
            chosen = generic[0] if generic else candidates[0]
        else:
            chosen = candidates[0]

    if chosen:
        best_email, source_url = chosen[0], chosen[1]

    return {
        "ContactEmail": best_email or "",
        "ContactFormURL": form_url or "",
        "SourceURL": source_url or ""
    }

def valid_email(e):
    low = e.lower()
    if any(x in low for x in ["example@", "test@", "noreply@", "no-reply@", "donotreply@"]):
        return False
    # lightly de-prioritise personal patterns but still allow if nothing else
    return True

