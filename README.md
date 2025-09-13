# Company Contact Finder (Chuckl.)

Finds company websites and generic contact details, writes them into a Google Sheet.

## Columns (must exist in row 1)

Company | Domain | Website | ContactEmail | ContactFormURL | SourceURL | Status | LastChecked | Notes | ReadyToSend | EmailSubject | EmailBody | SentAt

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export GOOGLE_SA_JSON_B64=...   # base64 of service account JSON
export SHEET_ID=...             # Google Sheet ID
export BING_API_KEY=...         # optional
export SCRAPERAPI_KEY=...       # optional

python -m src.main

