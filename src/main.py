import os, time
from urllib.parse import urlparse
import tldextract
from .logging_utils import get_logger
from . import sheet, search, crawl, extract
from .config import GOOGLE_SA_JSON_B64, SHEET_ID, SHEET_TAB, MAX_ROWS, DEFAULT_LOCATION

logger = get_logger("main")

def _registered_domain(url):
    ext = tldextract.extract(url or "")
    return ext.registered_domain or ""

def run():
    if not GOOGLE_SA_JSON_B64 or not SHEET_ID:
        raise RuntimeError("Missing GOOGLE_SA_JSON_B64 or SHEET_ID")

    ws = sheet.open_sheet(GOOGLE_SA_JSON_B64, SHEET_ID, SHEET_TAB)
    sheet.ensure_headers(ws)
    rows = sheet.read_rows(ws)

    processed = 0
    writes = 0

    for i, row in enumerate(rows, start=2):  # data starts at row 2
        if processed >= MAX_ROWS:
            break

        company = (row.get("Company") or "").strip()
        if not company:
            continue

        website = (row.get("Website") or "").strip()
        domain_hint = (row.get("Domain") or "").strip()

        logger.info(f"== {company} ==")

        # 1) Resolve official site
        if not website:
            website = search.find_official_site(company, domain_hint)

        contact_info = {}
        preferred_domain = ""
        found = False

        # 2) Crawl site (homepage + discovered links)
        if website:
            preferred_domain = _registered_domain(website)
            try:
                html_by_url = crawl.crawl_candidate_pages(website)
                info = extract.extract_contacts(html_by_url, preferred_domain=preferred_domain, location=DEFAULT_LOCATION)
                if info.get("ContactEmail") or info.get("ContactFormURL"):
                    contact_info = info
                    found = True
            except Exception as e:
                contact_info = {"Status": "Error", "Notes": str(e)}

        # 3) Fallback: Google contact hunt
        if not found:
            candidates = search.google_contact_hunt(company, DEFAULT_LOCATION, limit=3)
            html_by_url = {}
            for u in candidates:
                try:
                    html_by_url[u] = crawl.fetch(u)
                except Exception as e:
                    logger.info(f"Skip {u}: {e}")
            if html_by_url:
                info = extract.extract_contacts(html_by_url, preferred_domain=preferred_domain, location=DEFAULT_LOCATION)
                if info.get("ContactEmail") or info.get("ContactFormURL"):
                    contact_info = info
                    found = True

        # 4) Write result
        status = "OK" if found else ("NoWebsiteFound" if not website else "NotFound")
        result = {
            "Website": website or "",
            **(contact_info or {}),
            "Status": status,
            "Notes": "" if status == "OK" else ("No email/form discovered" if website else "Search yielded no site")
        }
        sheet.write_result(ws, i, result)

        writes += 1
        processed += 1

        # throttle to avoid Sheets write limits
        if writes % 25 == 0:
            time.sleep(65)
        else:
            time.sleep(1.2)

if __name__ == "__main__":
    run()
