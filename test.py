import os, base64, json, datetime, gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
sa = json.loads(base64.b64decode(os.environ["GOOGLE_SA_JSON_B64"]))
creds = Credentials.from_service_account_info(sa, scopes=SCOPES)
gc = gspread.authorize(creds)

ws = gc.open_by_key(os.environ["SHEET_ID"]).sheet1
rows = ws.get_all_records()
print("Read rows:", len(rows), rows[:5])

# Write a quick timestamp to row 2, LastChecked (which is column H = 8)
ws.update("H2", datetime.datetime.utcnow().isoformat())
print("Wrote LastChecked to row 2.")
