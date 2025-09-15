#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urljoin

import gspread
import requests
from bs4 import BeautifulSoup

# Optional project modules (feature-detected)
try:
    from . import search as search_mod
except Exception:
    search_mod = None  # type: ignore

try:
    from . import crawl as crawl_mod
except Exception:
    crawl_mod = None  # type: ignore

try:
    from . import extract as extract_mod
except Exception:
    extract_mod = None  # type: ignore

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
LOG = logging.getLogger("main")

# ===== Constants / defaults
DEFAULT_CONTACT_SLUGS = [
    "contact",
    "contact-us",
    "contactus",
    "get-in-touch",
    "getintouch",
]
ANCHOR_KEYWORDS = ["contact", "get in touch", "enquire", "enquiry", "enquiries", "support", "help"]
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)

BAD_HOSTS = {
    "facebook.com","m.facebook.com","instagram.com","twitter.com","x.com","linkedin.com","youtube.com",
    "wikipedia.org","reddit.com","medium.com","blogspot.com","wordpress.com","typepad.com",
    "pinterest.com","yelp.com","foursquare.com","amazon.com","amazon.co.uk","aws.amazon.com",
}
def is_bad_host(host: str) -> bool:
    h = (host or "").lower()
    if not h:
        return True
    if h in BAD_HOSTS:
        return True
    # de-prioritize generic .gov mega-portals
    if h.endswith(".gov") or h.endswith(".gov.uk"):
        return True
    return False

# ===== Secrets / auth helpers
def b64_to_json(s: str) -> dict:
    s = (s or "").strip()
    if not s:
        raise RuntimeError("GOOGLE_SA_JSON_B64 is empty")
    if s.startswith("{") and s.endswith("}"):
        return json.loads(s)
    if "base64" in s[:60] and "," in s:
        s = s.split(",", 1)[1]
    s = re.sub(r"\s+", "", s)
    try:
        pad = (-len(s)) % 4
        if pad:
            s += "=" * pad
        data = base64.b64decode(s)
        return json.loads(data.decode("utf-8"))
    except Exception:
        data = base64.urlsafe_b64decode(s + "=" * ((4 - len(s) % 4) % 4))
        return json.loads(data.decode("utf-8"))

def open_sheet(sheet_id: str, sheet_tab: str) -> gspread.Worksheet:
    creds = b64_to_json(os.getenv("GOOGLE_SA_JSON_B64", ""))
    gc = gspread.service_account_from_dict(creds)
    return gc.open_by_key(sheet_id).worksheet(sheet_tab)

def header_map(ws: gspread.Worksheet) -> Dict[str, int]:
    return {h.strip(): i + 1 for i, h in enumerate(ws.row_values(1)) if h.strip()}

def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

# ===== Fetch / parse
def safe_fetch(url: str, timeout: int = 15) -> Optional[str]:
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        if 200 <= r.status_code < 300:
            return r.text
    except Exception:
        pass
    return None

def extract_contacts_from_html(html: str, page_url: str) -> Tuple[List[str], bool]:
    # Prefer project extractor if present
    if extract_mod:
        try:
            info = extract_mod.extract_contacts(html, base_url=page_url)  # type: ignore
            emails = sorted(set(info.get("emails", []) or []))
            has_form = bool(info.get("has_form") or info.get("forms"))
            return emails, has_form
        except TypeError:
            try:
                info = extract_mod.extract_contacts(html)  # type: ignore
                emails = sorted(set(info.get("emails", []) or []))
                has_form = bool(info.get("has_form") or info.get("forms"))
                return emails, has_form
            except Exception:
                pass
        except Exception:
            pass

    soup = BeautifulSoup(html or "", "html.parser")
    emails = set()
    for a in soup.find_all("a", href=True):
        href = a["href"] or ""
        if href.lower().startswith("mailto:"):
            addr = href.split(":", 1)[1].split("?", 1)[0].strip()
            if addr:
                emails.add(addr)
    emails.update(EMAIL_RE.findall(soup.get_text(" ")))
    emails = {e for e in emails if "@" in e and not e.lower().startswith("noreply")}
    has_form = bool(soup.find("form"))
    return sorted(emails), has_form

def collect_contactish_links(base_url: str, html: str, limit: int = 20) -> List[str]:
    out: List[str] = []
    if not html:
        return out
    soup = BeautifulSoup(html, "html.parser")
    base_host = urlparse(base_url).netloc.lower()
    seen = set()
    for a in soup.find_all("a", href=True):
        txt = (a.get_text(" ") or "").strip().lower()
        href = a["href"]
        if any(k in txt for k in ANCHOR_KEYWORDS) or "contact" in href.lower():
            u = urljoin(base_url, href)
            p = urlparse(u)
            if p.scheme in ("http", "https") and p.netloc.lower().endswith(base_host):
                if u not in seen:
                    seen.add(u)
                    out.append(u)
        if len(out) >= limit:
            break
    return out

def discover_contact_pages(base_url: str) -> List[str]:
    base = base_url.rstrip("/")
    candidates: List[str] = []

    # start with the homepage
    candidates.append(base)

    # try clean slugs (with and without trailing slash)
    for slug in DEFAULT_CONTACT_SLUGS:
        u1 = f"{base}/{slug}"
        u2 = f"{u1}/"
        candidates.extend([u1, u2])

    # include anchor-discovered links from the homepage
    homepage_html = fetch_page(base)
    candidates.extend(collect_contactish_links(base, homepage_html))

    # dedupe, keep order
    seen = set()
    ordered = []
    for u in candidates:
        if u not in seen:
            seen.add(u)
            ordered.append(u)
    return ordered[:40]

def fetch_page(url: str) -> Optional[str]:
    # Use project fetcher if present
    if crawl_mod and hasattr(crawl_mod, "fetch"):
        try:
            html = crawl_mod.fetch(url)  # type: ignore
            if isinstance(html, tuple):
                html = html[0]
            return html
        except Exception:
            pass
    return safe_fetch(url)

# ===== Official site resolution
def find_official_site(company: str, domain_hint: str = "") -> Optional[str]:
    # Prefer explicit domain
    dom = (domain_hint or "").strip()
    if dom and "." in dom and " " not in dom:
        return dom if dom.startswith("http") else f"https://{dom}"

    # Use project search if available
    if search_mod and hasattr(search_mod, "find_official_site"):
        try:
            return search_mod.find_official_site(company, domain_hint)  # type: ignore
        except Exception:
            pass

    # Nothing safe to infer
    return None

# ===== Google CSE fallback (never guess)
def cse_search(query: str, num: int = 4) -> List[str]:
    key = os.getenv("GOOGLE_CSE_KEY", "").strip()
    cx = os.getenv("GOOGLE_CSE_CX", "").strip()
    if not key or not cx:
        return []
    params = {
        "key": key,
        "cx": cx,
        "q": query,
        "num": max(1, min(num, 10)),
        "safe": "off",
    }
    try:
        r = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        items = data.get("items", []) or []
        urls = []
        for it in items:
            link = it.get("link")
            if not link:
                continue
            host = urlparse(link).netloc
            if is_bad_host(host):
                continue
            urls.append(link)
        # polite delay for quotas
        delay_ms = int(os.getenv("GOOGLE_CSE_QPS_DELAY_MS", "600") or "600")
        time.sleep(max(0, delay_ms) / 1000.0)
        return urls
    except Exception:
        return []

def google_contact_hunt(company: str, location: str, domain_for_site: Optional[str]=None, limit: int = 4) -> Tuple[List[str], Optional[str], Optional[str]]:
    """
    Returns (emails_found, form_url, source_url)
    """
    queries = [f"\"{company}\" {location} email contact"]
    # tighten to site if we know it
    if domain_for_site:
        host = urlparse(domain_for_site if domain_for_site.startswith("http") else f"https://{domain_for_site}").netloc
        if host:
            queries.append(f"site:{host} contact email")

    tried = set()
    best_emails: List[str] = []
    best_form: Optional[str] = None
    source_url: Optional[str] = None

    for q in queries:
        urls = cse_search(q, num=limit)
        if not urls:
            continue
        LOG.info(f"Google candidates: {urls}")
        for u in urls:
            if u in tried:
                continue
            tried.add(u)
            html = fetch_page(u)
            if not html:
                continue
            emails, has_form = extract_contacts_from_html(html, u)
            if emails and not best_emails:
                best_emails = emails
                source_url = u
            if has_form and not best_form:
                best_form = u
            if best_emails and best_form:
                return best_emails, best_form, source_url

    return best_emails, best_form, source_url

# ===== Row processing
def set_cell(ws: gspread.Worksheet, row: int, col: Optional[int], value: Optional[str]) -> None:
    if col and value is not None:
        try:
            ws.update_cell(row, col, value)
        except Exception as e:
            LOG.warning(f"Cell update failed (row {row}, col {col}): {e}")

def process_one(ws: gspread.Worksheet, row_idx: int, H: Dict[str, int], default_location: str) -> None:
    def val(col_name: str) -> str:
        c = H.get(col_name)
        if not c:
            return ""
        row_vals = ws.row_values(row_idx)
        return row_vals[c - 1].strip() if len(row_vals) >= c else ""

    company = val("Company")
    domain_hint = val("Domain")
    website_existing = val("Website")

    if not company and not domain_hint:
        return

    # 1) Resolve site
    homepage = website_existing or find_official_site(company, domain_hint) or ""
    if homepage:
        LOG.info(f"[INFO] [{company}] Google resolved: {homepage}")
        set_cell(ws, row_idx, H.get("Website"), homepage)

    # 2) Site-first crawl
    emails_found: List[str] = []
    form_url: Optional[str] = None
    source_url: Optional[str] = None

    candidates: List[str] = []
    if homepage:
        candidates = discover_contact_pages(homepage)

    for url in candidates[:40]:
        html = fetch_page(url)
        if not html:
            continue
        emails, has_form = extract_contacts_from_html(html, url)
        if emails and not emails_found:
            emails_found = emails
            source_url = url
        if has_form and not form_url:
            form_url = url
        if emails_found and form_url:
            break

    # 3) Google fallback ONLY if nothing found on site
    if not emails_found and not form_url:
        emails, form, src = google_contact_hunt(company, default_location, domain_for_site=homepage or domain_hint, limit=4)
        if emails:
            emails_found = emails
            source_url = src or source_url
        if form:
            form_url = form

    # 4) Update sheet (never guess)
    if emails_found:
        set_cell(ws, row_idx, H.get("ContactEmail"), ", ".join(emails_found))
    if form_url:
        set_cell(ws, row_idx, H.get("ContactFormURL"), form_url)
    if source_url:
        set_cell(ws, row_idx, H.get("SourceURL"), source_url)

    status_msg = "Found" if (emails_found or form_url) else "No public contact"
    set_cell(ws, row_idx, H.get("Status"), status_msg)
    set_cell(ws, row_idx, H.get("LastChecked"), now_iso())

def find_start_row(ws: gspread.Worksheet, H: Dict[str, int]) -> int:
    status_col = H.get("Status")
    email_col = H.get("ContactEmail")
    form_col = H.get("ContactFormURL")
    for r in range(2, (ws.row_count or 2000) + 1):
        vals = ws.row_values(r)
        if not any(v.strip() for v in vals):
            continue
        status_ok = True
        if status_col:
            v = vals[status_col - 1].strip() if len(vals) >= status_col else ""
            status_ok = (v == "") or (v.lower() not in {"done", "skip"})
        email_blank = (not email_col) or (len(vals) < email_col) or (vals[email_col - 1].strip() == "")
        form_blank = (not form_col) or (len(vals) < form_col) or (vals[form_col - 1].strip() == "")
        if status_ok and email_blank and form_blank:
            return r
    return 2

# ===== Runner
def run() -> None:
    sheet_id = os.getenv("SHEET_ID", "").strip()
    sheet_tab = os.getenv("SHEET_TAB", "Sheet1").strip()
    default_location = os.getenv("DEFAULT_LOCATION", "Ely").strip()
    max_rows = int(os.getenv("MAX_ROWS", "40") or "40")

    if not sheet_id:
        LOG.error("SHEET_ID is missing.")
        sys.exit(1)

    ws = open_sheet(sheet_id, sheet_tab)
    H = header_map(ws)
    start_row = find_start_row(ws, H)
    LOG.info(f"Starting at first unprocessed row: {start_row}")

    processed = 0
    row = start_row
    last_row = ws.row_count or (start_row + max_rows + 10)

    while processed < max_rows and row <= last_row:
        vals = ws.row_values(row)
        if not any(v.strip() for v in vals):
            row += 1
            continue
        company = vals[H.get("Company", 1) - 1] if len(vals) >= H.get("Company", 1) else ""
        if not company.strip():
            row += 1
            continue

        LOG.info(f"== {company.strip()} ==")
        t0 = time.time()
        try:
            process_one(ws, row, H, default_location)
        except Exception as e:
            LOG.info(f"Site crawl error: {e}")
            set_cell(ws, row, H.get("LastChecked"), now_iso())
            set_cell(ws, row, H.get("Status"), f"Error: {type(e).__name__}")
        finally:
            processed += 1
            elapsed = time.time() - t0
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)
        row += 1

    LOG.info("Done.")

if __name__ == "__main__":
    run()
