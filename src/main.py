#!/usr/bin/env python3
"""
Main entrypoint for the scraper.
- Opens the Google Sheet via service account credentials provided in GOOGLE_SA_JSON_B64.
- Processes up to MAX_ROWS rows starting at the first unprocessed row.
- For each company, tries to find the official site, then hunts for a public email or contact form.
- NEVER guesses email addresses. If nothing is found, it leaves cells blank and moves on.

Environment variables expected:
  GOOGLE_SA_JSON_B64   (required)  – Base64 of your service account JSON (or raw JSON).
  SHEET_ID             (required)  – Google Sheet ID (not URL).
  SHEET_TAB            (optional)  – Worksheet/tab name (default "Sheet1").
  DEFAULT_LOCATION     (optional)  – Used by some search fallbacks (default "Ely").
  MAX_ROWS             (optional)  – Max rows to process per run (default "40").
  GOOGLE_CSE_*         (optional)  – If your search module needs them, those are read in that module.

This file is defensive: it wraps calls to optional functions in your submodules and falls back to simple
logic so the workflow won’t crash if a function is missing or has a different signature.
"""

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

import gspread

# Optional helpers for light-weight crawling if your crawl module is unavailable for a specific call
import requests
from bs4 import BeautifulSoup

# Your project modules. We’ll feature-detect functions so mismatches won’t crash the run.
try:
    from . import search
except Exception:  # pragma: no cover
    search = None  # type: ignore

try:
    from . import crawl
except Exception:  # pragma: no cover
    crawl = None  # type: ignore

try:
    from . import extract
except Exception:  # pragma: no cover
    extract = None  # type: ignore

# ------------ Logging ------------
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)
LOG = logging.getLogger("main")


# ------------ Robust SA secret handling ------------
def b64_to_json(s: str) -> dict:
    """
    Accepts:
      - Proper Base64 (with or without padding/newlines)
      - URL-safe Base64
      - Raw JSON
      - 'data:application/json;base64,<...>' strings
    Returns parsed dict.
    """
    s = (s or "").strip()
    if not s:
        raise RuntimeError("GOOGLE_SA_JSON_B64 is empty")

    # Raw JSON?
    if s.startswith("{") and s.endswith("}"):
        return json.loads(s)

    # data URL variant?
    if "base64" in s[:60] and "," in s:
        s = s.split(",", 1)[1]

    # Normalize: strip whitespace and fix padding
    s = re.sub(r"\s+", "", s)
    # Try standard b64 with padding fix
    try:
        pad = (-len(s)) % 4
        if pad:
            s += "=" * pad
        data = base64.b64decode(s)
        return json.loads(data.decode("utf-8"))
    except Exception:
        # Try URL-safe variant
        data = base64.urlsafe_b64decode(s + "=" * ((4 - len(s) % 4) % 4))
        return json.loads(data.decode("utf-8"))


# ------------ Google Sheets helpers ------------
def open_sheet(sheet_id: str, sheet_tab: str) -> gspread.Worksheet:
    sa_b64 = os.getenv("GOOGLE_SA_JSON_B64", "")
    creds_dict = b64_to_json(sa_b64)
    gc = gspread.service_account_from_dict(creds_dict)
    sh = gc.open_by_key(sheet_id)
    return sh.worksheet(sheet_tab)


def header_map(ws: gspread.Worksheet) -> Dict[str, int]:
    headers = ws.row_values(1)
    return {h.strip(): idx + 1 for idx, h in enumerate(headers) if h.strip()}


def find_start_row(ws: gspread.Worksheet, H: Dict[str, int]) -> int:
    """
    Heuristic: first row where Status is blank (or not 'Done') AND (ContactEmail and ContactFormURL are blank).
    Falls back to the first row after header if these headers don’t exist.
    """
    max_rows = ws.row_count or 1000
    status_col = H.get("Status")
    email_col = H.get("ContactEmail")
    form_col = H.get("ContactFormURL")

    # Always start from 2 (data starts below header)
    for r in range(2, max_rows + 1):
        row_vals = ws.row_values(r)
        # If entire row is empty, skip
        if not any(v.strip() for v in row_vals):
            continue

        status_ok = True
        if status_col:
            status_val = row_vals[status_col - 1].strip() if len(row_vals) >= status_col else ""
            status_ok = (status_val == "") or (status_val.lower() not in {"done", "skip"})

        email_blank = True
        form_blank = True
        if email_col:
            email_val = row_vals[email_col - 1].strip() if len(row_vals) >= email_col else ""
            email_blank = (email_val == "")
        if form_col:
            form_val = row_vals[form_col - 1].strip() if len(row_vals) >= form_col else ""
            form_blank = (form_val == "")

        if status_ok and email_blank and form_blank:
            return r

    return 2


def set_cell(ws: gspread.Worksheet, row: int, col: Optional[int], value: Optional[str]) -> None:
    if col and value is not None:
        try:
            ws.update_cell(row, col, value)
        except Exception as e:
            LOG.warning(f"Cell update failed (row {row}, col {col}): {e}")


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


# ------------ Lightweight crawling & extraction fallbacks ------------
DEFAULT_CONTACT_PATHS = [
    "contact", "contact-us", "contacts", "contactus", "get-in-touch", "getintouch",
    "about", "team", "imprint", "impressum", "legal", "support", "help",
]

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)


def safe_fetch(url: str, timeout: int = 15) -> Optional[str]:
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code >= 200 and r.status_code < 300:
            return r.text
    except Exception:
        pass
    return None


def find_emails_in_html(html: str) -> List[str]:
    if not html:
        return []
    found = set(EMAIL_RE.findall(html))
    # Filter obvious junk like tracking placeholders
    return sorted(e for e in found if "@" in e and not e.lower().startswith("noreply"))


def discover_contact_pages(base_url: str) -> List[str]:
    pages: List[str] = []
    # Prefer calling your crawl module if it provides something richer
    if crawl:
        if hasattr(crawl, "crawl_candidate_pages"):
            try:
                pages = list(crawl.crawl_candidate_pages(base_url))  # type: ignore
                return pages[:20]
            except Exception:
                pass
        if hasattr(crawl, "crawl_site"):
            try:
                pages = list(crawl.crawl_site(base_url, max_pages=20))  # type: ignore
                return pages[:20]
            except Exception:
                pass

    # Fallback: just try a set of common contact paths
    base = base_url.rstrip("/")
    tried = {base}
    cand = [f"{base}/{p.strip('/')}" for p in DEFAULT_CONTACT_PATHS]
    out: List[str] = []
    for u in cand:
        if u in tried:
            continue
        tried.add(u)
        out.append(u)
    return out[:20]


def extract_contacts_from_html(html: str, page_url: str) -> Tuple[List[str], bool]:
    """
    Returns (emails, has_contact_form)
    Uses your extract module if available, else a simple BeautifulSoup scan.
    """
    if extract:
        # Try calling with (html, base_url=...)
        try:
            info = extract.extract_contacts(html, base_url=page_url)  # type: ignore
            emails = sorted(set(info.get("emails", []) or []))
            has_form = bool(info.get("has_form") or info.get("forms"))
            return emails, has_form
        except TypeError:
            # Try simplest signature
            try:
                info = extract.extract_contacts(html)  # type: ignore
                emails = sorted(set(info.get("emails", []) or []))
                has_form = bool(info.get("has_form") or info.get("forms"))
                return emails, has_form
            except Exception:
                pass
        except Exception:
            pass

    # Fallback: basic soup scan
    soup = BeautifulSoup(html or "", "html.parser")
    # mailto links
    emails = set()
    for a in soup.find_all("a", href=True):
        href = a["href"] or ""
        if href.lower().startswith("mailto:"):
            addr = href.split(":", 1)[1].split("?")[0].strip()
            if addr:
                emails.add(addr)
    # plus regex in the page text
    emails.update(find_emails_in_html(soup.get_text(" ")))
    has_form = bool(soup.find("form"))
    return sorted(emails), has_form


# ------------ Official site resolution ------------
def find_official_site(company: str, domain_hint: str = "") -> Optional[str]:
    """
    Try your search module first, then a simple heuristic.
    """
    if search:
        if hasattr(search, "find_official_site"):
            try:
                return search.find_official_site(company, domain_hint)  # type: ignore
            except Exception:
                pass
        # Older name?
        if hasattr(search, "resolve_official_site"):
            try:
                return search.resolve_official_site(company, domain_hint)  # type: ignore
            except Exception:
                pass

    # Very simple heuristic: if we have a plausible domain, use it; else None.
    domain_hint = (domain_hint or "").strip()
    if domain_hint and "." in domain_hint and " " not in domain_hint:
        if not domain_hint.startswith("http"):
            domain_hint = "https://" + domain_hint
        return domain_hint
    return None


# ------------ Row processing ------------
def process_one(ws: gspread.Worksheet, row_idx: int, H: Dict[str, int], default_location: str) -> None:
    """
    Process a single sheet row: attempt to find site, then public email or contact form.
    Never guesses emails.
    """
    def val(col_name: str) -> str:
        c = H.get(col_name)
        if not c:
            return ""
        vals = ws.row_values(row_idx)
        return vals[c - 1].strip() if len(vals) >= c else ""

    company = val("Company")
    domain_hint = val("Domain")
    website_existing = val("Website")

    if not company and not domain_hint:
        return  # nothing to do

    if website_existing:
        homepage = website_existing
    else:
        homepage = find_official_site(company, domain_hint) or ""

    if homepage:
        LOG.info(f"[INFO] [{company}] Google resolved: {homepage}")
        set_cell(ws, row_idx, H.get("Website"), homepage)

    # Crawl candidate pages
    emails_found: List[str] = []
    form_url: Optional[str] = None
    source_url: Optional[str] = None

    candidates = []
    if homepage:
        candidates = [homepage] + discover_contact_pages(homepage)

    # Try each candidate quickly; bail as soon as we find an email or a form
    for url in candidates[:20]:
        html = None

        # Prefer your crawl module if it exposes fetch()
        if crawl and hasattr(crawl, "fetch"):
            try:
                html = crawl.fetch(url)  # type: ignore
                if isinstance(html, tuple):
                    # some versions return (html, final_url)
                    html = html[0]
            except Exception:
                html = None

        if html is None:
            html = safe_fetch(url)

        if not html:
            continue

        emails, has_form = extract_contacts_from_html(html, url)

        if emails and not emails_found:
            emails_found = emails
            source_url = url

        if has_form and not form_url:
            form_url = url

        if emails_found and form_url:
            break  # we’re good

    # Update sheet WITHOUT guessing
    if emails_found:
        set_cell(ws, row_idx, H.get("ContactEmail"), ", ".join(emails_found))
    if form_url:
        set_cell(ws, row_idx, H.get("ContactFormURL"), form_url)
    if source_url:
        set_cell(ws, row_idx, H.get("SourceURL"), source_url)

    status_msg = "Found" if (emails_found or form_url) else "No public contact"
    set_cell(ws, row_idx, H.get("Status"), status_msg)
    set_cell(ws, row_idx, H.get("LastChecked"), now_iso())


# ------------ Runner ------------
def run() -> None:
    sheet_id = os.getenv("SHEET_ID", "").strip()
    sheet_tab = os.getenv("SHEET_TAB", "Sheet1").strip()
    default_location = os.getenv("DEFAULT_LOCATION", "Ely").strip()
    max_rows = int(os.getenv("MAX_ROWS", "40") or "40")

    if not sheet_id:
        LOG.error("SHEET_ID is missing. Set it as a GitHub secret and pass it to the workflow env.")
        sys.exit(1)

    ws = open_sheet(sheet_id, sheet_tab)
    H = header_map(ws)
    start_row = find_start_row(ws, H)
    LOG.info(f"Starting at first unprocessed row: {start_row}")

    # Process up to max_rows rows
    processed = 0
    row = start_row
    # Stop when we reach the bottom or hit our batch limit
    max_sheet_rows = ws.row_count or (start_row + max_rows + 10)

    while processed < max_rows and row <= max_sheet_rows:
        try:
            vals = ws.row_values(row)
        except Exception:
            break

        if not any(v.strip() for v in vals):
            row += 1
            continue

        try:
            company = vals[H.get("Company", 1) - 1] if len(vals) >= H.get("Company", 1) else ""
        except Exception:
            company = ""

        if not company.strip():
            row += 1
            continue

        LOG.info(f"== {company.strip()} ==")
        t0 = time.time()
        try:
            process_one(ws, row, H, default_location)
        except Exception as e:
            LOG.info(f"Site crawl error: {e}")
            # Mark attempt time anyway
            set_cell(ws, row, H.get("LastChecked"), now_iso())
            set_cell(ws, row, H.get("Status"), f"Error: {type(e).__name__}")
        finally:
            processed += 1
            # Small polite delay between companies (helps rate limits)
            elapsed = time.time() - t0
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)

        row += 1

    LOG.info("Done.")


if __name__ == "__main__":
    run()
