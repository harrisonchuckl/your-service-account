import base64, json, datetime
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

HEADERS = [
    "Company","Domain","Website","ContactEmail","ContactFormURL",
    "SourceURL","Status","LastChecked","Notes","ReadyToSend",
    "EmailSubject","EmailBody","SentAt"
]

def _client(sa_json_b64):
    info = json.loads(base64.b64decode(sa_json_b64))
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)

def open_sheet(sa_json_b64, sheet_id, worksheet_name=None):
    gc = _client(sa_json_b64)
    sh = gc.open_by_key(sheet_id)
    return sh.worksheet(worksheet_name) if worksheet_name else sh.sheet1

def read_rows(ws):
    # expects header row present
    return ws.get_all_records()

def ensure_headers(ws):
    current = ws.row_values(1)
    if current != HEADERS:
        ws.update("A1", [HEADERS])

def write_result(ws, row_idx_1_based, result: dict):
    """
    Writes columns C..I (Website..Notes) and updates LastChecked (H).
    """
    values = [
        result.get("Website", ""),
        result.get("ContactEmail", ""),
        result.get("ContactFormURL", ""),
        result.get("SourceURL", ""),
        result.get("Status", ""),
        datetime.datetime.utcnow().isoformat(),
        result.get("Notes", "")
    ]
    ws.update(range_name=f"C{row_idx_1_based}:I{row_idx_1_based}", values=[values])

