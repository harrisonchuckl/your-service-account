import re
from bs4 import BeautifulSoup

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}", re.I)

GENERIC_PRIORITY = [
    "info@", "hello@", "contact@", "enquiries@", "enquiry@", "boxoffice@",
    "bookings@", "sales@", "admin@", "office@", "support@", "team@", "press@", "media@"
]

def extract_contacts(html_by_url, preferred_domain=None, location=None):
    best = None
    best_score = -1
    form_url = None

    for url, html in html_by_url.items():
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)[:600000]
        text_low = text.lower()

        # 1) find mailto emails first (often footer)
        for a in soup.select('a[href^="mailto:"]'):
            email = (a.get("href") or "").replace("mailto:", "").split("?")[0].strip()
            _maybe_pick(email, url, text_low, preferred_domain, location, state=(lambda e,u,s: _pick(e,u,s)))

        # 2) visible emails in text
        for m in EMAIL_RE.findall(text):
            email = m.strip()
            _maybe_pick(email, url, text_low, preferred_domain, location, state=(lambda e,u,s: _pick(e,u,s)))

        # 3) remember a contact form if seen
        if not form_url:
            if "contact" in url.lower():
                form_url = url
            else:
                form = soup.find("form")
                if form and ("contact" in (form.get("id","") + " ".join(form.get("class", []) if isinstance(form.get("class"), list) else [str(form.get("class",""))]).lower())):
                    form_url = url

        def _pick(email, src, page_text):
            nonlocal best, best_score
            score = 0
            e_low = email.lower()

            # prefer the company's domain if we know it
            if preferred_domain and e_low.split("@")[-1].endswith(preferred_domain):
                score += 3

            # prefer generic catch-all inboxes
            if any(e_low.startswith(p) for p in GENERIC_PRIORITY):
                score += 2

            # bonus if page mentions the location
            if location and location.lower() in page_text:
                score += 1

            # slight bonus if 'contact' in URL
            if "contact" in src.lower():
                score += 1

            if score > best_score:
                best_score = score
                best = (email, src)

        def _maybe_pick(email, src, page_text, domain, loc, state):
            # filter obvious non-sendable
            el = email.lower()
            if any(bad in el for bad in ["example@", "test@", "noreply@", "no-reply@", "donotreply@"]):
                return
            state(email, src, page_text)

    result = {
        "ContactEmail": best[0] if best else "",
        "ContactFormURL": form_url or "",
        "SourceURL": best[1] if best else (form_url or "")
    }
    return result
