# src/main.py
from __future__ import annotations

import base64
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional, Set
from urllib.parse import urljoin, urlparse

import requests
import tldextract
from bs4 import BeautifulSoup

# ---- Logging ----
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
log = logging.getLogger("main")

# ---- Config (env-driven, no guessing) ----
SHEET_ID = os.getenv("SHEET_ID", "")
SHEET_TAB = os.getenv("SHEET_TAB", "Sheet1")
MAX_ROWS = int(os.getenv("MAX_ROWS", "100"))
DEFAULT_LOCATION = os.getenv("DEFAULT_LOCATION", "Ely")

GOOGLE_CSE_KEY = os.getenv("GOOGLE_CSE_KEY", "")
GOOGLE_CSE_CX = os.getenv("GOOGLE_CSE_CX", "")
GOOGLE_QPS_DELAY = int(os.getenv("GOOGLE_CSE_QPS_DELAY_MS", "600")) / 1000.0
GOOGLE_MAX_RETRIES = int(os.getenv("GOOGLE_CSE_MAX_RETRIES", "4"))

HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "15"))
MAX_PAGES_PER_SITE = int(os.getenv("MAX_PAGES_PER_SITE", "15"))
MIN_PAGES_BEFORE_FALLBACK = int(os.getenv("MIN_PAGES_BEFORE_FALLBACK", "5"))
ALLOW_GUESS = os.getenv("ALLOW_GUESS", "false").lower() == "true"  # we will not guess if false
PREFER_COMPANY_DOMAIN = os.getenv("PREFER_COMPANY_DOMAIN", "true").lower() == "true"

BAD_HOSTS = set([
    "facebook.com", "linkedin.com", "twitter.com", "x.com", "instagram.com", "youtube.com",
    "wikipedia.org", "reddit.com", "medium.com", "blogspot.com", "wordpress.com",
    "typepad.com", "pinterest.com", "foursquare.com", "yelp.com", "fda.gov", "amazon.com", "opentable.com",
])

HEADERS = {
    "User-Agent": os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )
}

# ---- Utilities ----
def registrable_domain(url_or_host: str) -> str:
    if not url_or_host:
        return ""
    host = url_or_host
    if "://" in url_or_host:
        host = urlparse(url_or_host).netloc
    ext = tldextract.extract(host)
    if not ext.domain:
        return host.lower()
    return f"{ext.domain}.{ext.suffix}".lower() if ext.suffix else ext.domain.lower()

def same_reg_domain(a: str, b: str) -> bool:
    ra, rb = registrable_domain(a), registrable_domain(b)
    return bool(ra and rb and ra == rb)

def b64_to_json(b64: str) -> dict:
    data = base64.b64decode(b64).decode("utf-8")
    return json.loads(data)

def open_sheet(sheet_id: str, tab_name: str):
    import gspread  # lazy import
    sa_b64 = os.getenv("GOOGLE_SA_JSON_B64", "")
    if not sa_b64:
        raise RuntimeError("GOOGLE_SA_JSON_B64 is not set")
    creds = b64_to_json(sa_b64)
    client = gspread.service_account_from_dict(creds)
    sh = client.open_by_key(sheet_id)
    ws = sh.worksheet(tab_name)
    return ws

def get_table(ws) -> Tuple[List[str], List[List[str]]]:
    values = ws.get_all_values()
    if not values:
        return [], []
    headers = values[0]
    rows = values[1:]
    return headers, rows

def header_map(headers: List[str]) -> Dict[str, int]:
    return {h.strip(): i for i, h in enumerate(headers)}

def find_first_unprocessed(headers: List[str], rows: List[List[str]]) -> int:
    h = header_map(headers)
    idx_email = h.get("ContactEmail")
    idx_form = h.get("ContactFormURL")
    idx_status = h.get("Status")
    for i, row in enumerate(rows, start=2):  # sheet rows start at 2 for first data row
        email = row[idx_email] if idx_email is not None and idx_email < len(row) else ""
        form = row[idx_form] if idx_form is not None and idx_form < len(row) else ""
        status = row[idx_status] if idx_status is not None and idx_status < len(row) else ""
        if not email and not form and status != "done":
            return i
    return 2

# ---- Fetch & crawl ----
def fetch(url: str) -> Optional[str]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT, allow_redirects=True)
        if r.status_code >= 400:
            return None
        ct = (r.headers.get("content-type") or "").lower()
        if "text/html" not in ct and "application/xhtml" not in ct and "<html" not in r.text.lower():
            return None
        return r.text
    except Exception:
        return None

def candidate_links(base_url: str, html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        u = urljoin(base_url, href)
        links.append(u)
    # Filter to same site and contact-like
    base_host = registrable_domain(base_url)
    out = []
    for u in links:
        if not same_reg_domain(u, base_host):
            continue
        lu = u.lower()
        if any(x in lu for x in ["/contact", "contact-", "contactus", "contact-us", "get-in-touch", "getintouch",
                                  "/about", "/impressum", "/kontakt", "/find-us", "/where-to-find-us", "/support", "/help"]):
            out.append(u)
    # dedupe
    seen = set()
    uniq = []
    for u in out:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq[:MAX_PAGES_PER_SITE]

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
MAILTO_RE = re.compile(r"mailto:([^\s\"'>?#]+)", re.I)

def extract_emails_and_forms(url: str, html: str) -> Tuple[Set[str], bool]:
    emails: Set[str] = set()
    if isinstance(html, str):
        for m in MAILTO_RE.findall(html or ""):
            e = m.split("?")[0].strip()
            if e:
                emails.add(e)
        soup = BeautifulSoup(html, "html.parser")
        txt = soup.get_text(" ", strip=True)
        for m in EMAIL_RE.findall(txt):
            emails.add(m.strip())
        # simple contact form heuristic
        has_form = False
        for f in soup.find_all("form"):
            blob = " ".join([f.get("id") or "", " ".join(f.get("class") or [])]).lower()
            inputs = f.find_all(["input", "textarea", "select"])
            names = " ".join((i.get("name") or "") for i in inputs).lower()
            placeholders = " ".join((i.get("placeholder") or "") for i in inputs).lower()
            labels = " ".join(l.get_text(" ", strip=True).lower() for l in f.find_all("label"))
            alltxt = f"{blob} {names} {placeholders} {labels}"
            if any(k in alltxt for k in ["contact", "enquiry", "inquiry", "message", "support", "help", "email"]):
                has_form = True
                break
        # Count explicit contact-like URLs as forms
        if not has_form:
            u = (url or "").lower()
            if "contact" in u or "get-in-touch" in u or "kontakt" in u or "impressum" in u:
                has_form = True
        return emails, has_form
    return set(), False

def find_official_site(company: str, domain_hint: str = "") -> Optional[str]:
    # If a plausible website is already in hint, use it
    if domain_hint and "." in domain_hint and "/" not in domain_hint:
        return f"https://{domain_hint.strip().lower()}"
    # Use Google CSE
    if not GOOGLE_CSE_KEY or not GOOGLE_CSE_CX:
        return None
    queries = [
        f"{company} official site",
        f"{company} {DEFAULT_LOCATION} official site",
        f"{company} website",
    ]
    if domain_hint:
        queries.insert(0, f"{company} {domain_hint} official site")
    seen = set()
    for q in queries:
        for attempt in range(GOOGLE_MAX_RETRIES):
            try:
                resp = requests.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params={"key": GOOGLE_CSE_KEY, "cx": GOOGLE_CSE_CX, "q": q, "num": 5, "safe": "off"},
                    timeout=HTTP_TIMEOUT,
                )
                if resp.status_code == 429:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                resp.raise_for_status()
                data = resp.json()
                items = data.get("items", []) or []
                for it in items:
                    link = it.get("link", "")
                    if not link or link in seen:
                        continue
                    seen.add(link)
                    host = registrable_domain(link)
                    if host in BAD_HOSTS:
                        continue
                    # prefer company or hint in domain
                    if company.lower().split()[0] in host or (domain_hint and domain_hint.split(".")[0] in host):
                        return link
                break
            except Exception:
                pass
            finally:
                time.sleep(GOOGLE_QPS_DELAY)
    # fallback: first item not in BAD_HOSTS
    for q in queries:
        try:
            resp = requests.get(
                "https://www.googleapis.com/customsearch/v1",
                params={"key": GOOGLE_CSE_KEY, "cx": GOOGLE_CSE_CX, "q": q, "num": 5, "safe": "off"},
                timeout=HTTP_TIMEOUT,
            )
            data = resp.json()
            for it in data.get("items", []) or []:
                link = it.get("link", "")
                if link and registrable_domain(link) not in BAD_HOSTS:
                    return link
        except Exception:
            pass
        finally:
            time.sleep(GOOGLE_QPS_DELAY)
    return None

def google_contact_hunt(site_url: str) -> Tuple[Set[str], Optional[str], Dict[str, str]]:
    """
    Search Google for contact pages on the same domain, then fetch & extract.
    Returns (emails, best_form_url, email_sources)
    """
    emails: Set[str] = set()
    email_sources: Dict[str, str] = {}
    best_form: Optional[str] = None
    if not GOOGLE_CSE_KEY or not GOOGLE_CSE_CX or not site_url:
        return emails, best_form, email_sources
    dom = registrable_domain(site_url)
    q_list = [
        f"site:{dom} contact",
        f"site:{dom} email",
        f"site:{dom} get in touch",
    ]
    candidates: List[str] = []
    seen = set()
    for q in q_list:
        try:
            resp = requests.get(
                "https://www.googleapis.com/customsearch/v1",
                params={"key": GOOGLE_CSE_KEY, "cx": GOOGLE_CSE_CX, "q": q, "num": 5, "safe": "off"},
                timeout=HTTP_TIMEOUT,
            )
            if resp.status_code == 429:
                time.sleep(1.2)
                continue
            resp.raise_for_status()
            data = resp.json()
            for it in data.get("items", []) or []:
                link = it.get("link", "")
                if not link or link in seen:
                    continue
                seen.add(link)
                if not same_reg_domain(link, dom):
                    continue
                if registrable_domain(link) in BAD_HOSTS:
                    continue
                candidates.append(link)
        except Exception:
            pass
        finally:
            time.sleep(GOOGLE_QPS_DELAY)
    # fetch candidates
    for url in candidates[:10]:
        html = fetch(url)
        if not html:
            continue
        found, has_form = extract_emails_and_forms(url, html)
        for e in found:
            emails.add(e)
            if e not in email_sources:
                email_sources[e] = url
        if has_form and not best_form:
            best_form = url
        if emails and best_form:
            break
    return emails, best_form, email_sources

# ---- Main run ----
def run():
    ws = open_sheet(SHEET_ID, SHEET_TAB)
    headers, rows = get_table(ws)
    if not headers:
        log.error("No headers found")
        return
    h = header_map(headers)
    idx_company = h.get("Company")
    idx_domain  = h.get("Domain")
    idx_website = h.get("Website")
    idx_email   = h.get("ContactEmail")
    idx_form    = h.get("ContactFormURL")
    idx_source  = h.get("SourceURL")
    idx_status  = h.get("Status")
    idx_checked = h.get("LastChecked")
    idx_notes   = h.get("Notes")
    start_row = find_first_unprocessed(headers, rows)
    log.info("Starting at first unprocessed row: %d", start_row-1)

    processed = 0
    for rownum in range(start_row, min(len(rows)+1, start_row - 1 + MAX_ROWS) + 1):
        # Fetch fresh row values (in case of manual edits)
        row_vals = ws.row_values(rownum)
        # pad
        if len(row_vals) < len(headers):
            row_vals += [""] * (len(headers)-len(row_vals))
        company = row_vals[idx_company] if idx_company is not None else ""
        domain_hint = row_vals[idx_domain] if idx_domain is not None else ""
        website = row_vals[idx_website] if idx_website is not None else ""
        if not company:
            continue
        print(f"[INFO] == {company} ==")

        # 1) Find official site
        if not website:
            site = find_official_site(company, domain_hint)
            if site:
                website = site
                if idx_website is not None:
                    ws.update_cell(rownum, idx_website+1, website)
                print(f"[INFO] [{company}] Google resolved: {website}")
        else:
            print(f"[INFO] [{company}] Using existing website: {website}")

        emails: Set[str] = set()
        forms: List[str] = []
        email_sources: Dict[str, str] = {}

        # 2) Crawl homepage and contact-like pages
        if website:
            home_html = fetch(website)
            cand = []
            if home_html:
                cand = candidate_links(website, home_html)
                # include homepage itself for email scraping
                cand = [website] + cand
            else:
                cand = [website]
            seen_pages = set()
            for url in cand[:MAX_PAGES_PER_SITE]:
                if url in seen_pages:
                    continue
                seen_pages.add(url)
                html = home_html if url == website and home_html else fetch(url)
                if not html:
                    continue
                found, has_form = extract_emails_and_forms(url, html)
                # Prefer company domain emails
                for e in found:
                    if not PREFER_COMPANY_DOMAIN or same_reg_domain(e.split("@")[-1], website):
                        emails.add(e)
                        if e not in email_sources:
                            email_sources[e] = url
                if has_form:
                    forms.append(url)

        # 3) If still nothing, try Google contact hunt on same domain
        if not emails and not forms and website:
            print("[INFO] No email/form on site pages, trying Google contact hunt…")
            ge, gf, es = google_contact_hunt(website)
            emails |= ge
            email_sources.update(es)
            if gf:
                forms.append(gf)

        # 4) Decide outcome — NEVER GUESS if ALLOW_GUESS is False
        status = ""
        notes = ""
        best_email = next(iter(emails)) if emails else ""
        best_form = forms[0] if forms else ""

        if best_email:
            status = "email_found"
            if idx_email is not None:
                ws.update_cell(rownum, idx_email+1, best_email)
            if idx_source is not None and best_email in email_sources:
                ws.update_cell(rownum, idx_source+1, email_sources[best_email])
            notes = f"Found {len(emails)} email(s)"
        elif best_form:
            status = "form_found"
            if idx_form is not None:
                ws.update_cell(rownum, idx_form+1, best_form)
            notes = "No email found; contact form available"
        else:
            if ALLOW_GUESS:
                # we still log but do not set guessed email; safer default
                dom = registrable_domain(website or domain_hint)
                print(f"[INFO] ⚠ No public email or form; ALLOW_GUESS=true but skipping setting guessed email info@{dom}")
                status = "no_contact"
                notes = "Would guess, but safe-mode skip"
            else:
                print("[INFO] ⚠ No public email or form; NOT guessing (skipped)")
                status = "no_contact"
                notes = "No email/form; guessing disabled"

        # 5) Write status + timestamp
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
        if idx_status is not None:
            ws.update_cell(rownum, idx_status+1, status)
        if idx_checked is not None:
            ws.update_cell(rownum, idx_checked+1, now)
        if idx_notes is not None:
            ws.update_cell(rownum, idx_notes+1, notes)

        processed += 1
        # gentle pacing to respect APIs
        time.sleep(0.5)

    log.info("Processed %d row(s).", processed)


if __name__ == "__main__":
    run()
