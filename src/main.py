import os, time
from .logging_utils import get_logger
from . import sheet, search, crawl, extract
from .config import GOOGLE_SA_JSON_B64, SHEET_ID, SHEET_TAB, MAX_ROWS

logger = get_logger("main")

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

        if not website:
            website = search.find_official_site(company, domain_hint)
            if not website:
                # Still write a status so you can see it was attempted
                sheet.write_result(ws, i, {
                    "Status": "NoWebsiteFound",
                    "Notes": "Search provider not configured or no result"
                })
                writes += 1
                processed += 1

                # gentle throttling: every 25 writes, pause ~65s
                if writes % 25 == 0:
                    time.sleep(65)
                else:
                    time.sleep(1.2)
                continue

        try:
            html_by_url = crawl.crawl_candidate_pages(website)
            info = extract.extract_contacts(html_by_url)
            status = "OK" if (info.get("ContactEmail") or info.get("ContactFormURL")) else "NotFound"
            result = {
                "Website": website,
                **info,
                "Status": status,
                "Notes": "" if status == "OK" else "No generic email or contact form discovered"
            }
            sheet.write_result(ws, i, result)
        except Exception as e:
            sheet.write_result(ws, i, {
                "Website": website,
                "Status": "Error",
                "Notes": str(e)
            })

        writes += 1
        processed += 1

        # throttle to avoid Google's per-minute write limit
        if writes % 25 == 0:
            time.sleep(65)
        else:
            time.sleep(1.2)

if __name__ == "__main__":
    run()
