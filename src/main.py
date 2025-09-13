import os, time
import tldextract

from .logging_utils import get_logger
from . import sheet, search, crawl, extract
from .config import (
    GOOGLE_SA_JSON_B64, SHEET_ID, SHEET_TAB, MAX_ROWS, DEFAULT_LOCATION,
    PREFER_COMPANY_DOMAIN, GUESS_GENERICS, GENERIC_GUESS_PREFIXES
)

logger = get_logger("main")
DRY_RUN = (os.getenv("DRY_RUN","0") == "1")

def _registered_domain(url):
    ext = tldextract.extract(url or "")
    return ext.registered_domain or ""

def _guess_generics(domain):
    return [f"{p}@{domain}" for p in GENERIC_GUESS_PREFIXES]

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

        # 1) Resolve site if needed
        if not website:
            website = search.find_official_site(company, domain_hint)

        preferred_domain = _registered_domain(website) if website else (domain_hint or "").lower()
        contact_info = {}
        found = False

        # 2) Crawl site
        if website:
            try:
                html_by_url = crawl.crawl_candidate_pages(website)
                info = extract.extract_contacts(
                    html_by_url,
                    preferred_domain=preferred_domain,
                    location=DEFAULT_LOCATION
                )
                em = info.get("ContactEmail"); form = info.get("ContactFormURL")
                if em:
                    if PREFER_COMPANY_DOMAIN and preferred_domain and not em.lower().endswith(preferred_domain):
                        logger.info(f"Email found ({em}) but not on company domain; will still accept if nothing better.")
                    logger.info(f"✓ Email from site: {em} (source {info.get('SourceURL')})")
                    contact_info = info; found = True
                elif form:
                    logger.info(f"✓ Contact form from site: {form}")
                    contact_info = info; found = True
                else:
                    logger.info("No email/form on site pages, trying Google contact hunt…")
            except Exception as e:
                logger.info(f"Site crawl error: {e}")
                contact_info = {"Status": "Error", "Notes": str(e)}

        # 3) Fallback: Google contact hunt (site:domain and general)
        if not found:
            candidates = search.google_contact_hunt(company, DEFAULT_LOCATION, domain_for_site=preferred_domain, limit=4)
            if candidates:
                logger.info(f"Google candidates: {candidates}")
            html_by_url = {}
            for u in candidates:
                try:
                    html_by_url[u] = crawl.fetch(u)
                except Exception as e:
                    logger.info(f"Skip {u}: {e}")
            if html_by_url:
                info = extract.extract_contacts(
                    html_by_url,
                    preferred_domain=preferred_domain,
                    location=DEFAULT_LOCATION
                )
                em = info.get("ContactEmail"); form = info.get("ContactFormURL")
                if em:
                    logger.info(f"✓ Email via Google: {em} (source {info.get('SourceURL')})")
                    contact_info = info; found = True
                elif form:
                    logger.info(f"✓ Contact form via Google: {form}")
                    contact_info = info; found = True

        # 4) Final safety: if still nothing and we have a domain, optionally guess info@ etc.
        guessed = ""
        if not found and preferred_domain and GUESS_GENERICS:
            guesses = _guess_generics(preferred_domain)
            guessed = guesses[0]  # pick the most common (info@)
            logger.info(f"⚠ No public email or form; guessing {guessed}")
            contact_info = {
                "ContactEmail": guessed,
                "ContactFormURL": "",
                "SourceURL": "",
            }
            found = True  # mark as found but we'll label as 'Guessed'

        # 5) Write result
        status = "OK" if found else ("NoWebsiteFound" if not website else "NotFound")
        notes = "" if status == "OK" else ("No email/form discovered" if website else "Search yielded no site")
        if guessed:
            notes = f"Guessed generic inbox (no public email/form found)"

        result = {
            "Website": website or "",
            **(contact_info or {}),
            "Status": status,
            "Notes": notes
        }

        if DRY_RUN:
            logger.info(f"[DRY_RUN] Row {i} would update: {result}")
        else:
            sheet.write_result(ws, i, result)
            writes += 1
            time.sleep(1.1)  # throttle to avoid Sheets write limits

        processed += 1

if __name__ == "__main__":
    run()
