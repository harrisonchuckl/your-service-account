import base64, json, datetime, binascii
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

HEADERS = [
    "Company","Domain","Website","ContactEmail","ContactFormURL",
    "SourceURL","Status","LastChecked","Notes","ReadyToSend",
    "EmailSubject","EmailBody","SentAt"
]

def _load_sa_info(value: str):
    """
    Accepts either:
    - Raw JSON (starts with '{')
    - Base64-encoded JSON (with or without perfect padding)
    """
    s = (value or "").strip()
    if not s:
        raise RuntimeError("GOOGLE_SA_JSON_B64 is empty")
    if s.startswith("{"):
        return json.loads(s)
    try:
        missing = len(s) % 4
        if missing:
            s += "=" * (4 - missing)
        decoded = base64.b64decode(s)
        return json.loads(decoded)
    except (binascii.Error, json.JSONDecodeError) as e:
        raise RuntimeError("GOOGLE_SA_JSON_B64 is neither valid JSON nor valid base64 JSON") from e

def _client(sa_json_value):
    info = _load_sa_info(sa_json_value)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)

def open_sheet(sa_json_value, sheet_id, worksheet_name=None):
    gc = _client(sa_json_value)
    sh = gc.open_by_key(sheet_id)
    return sh.worksheet(worksheet_name) if worksheet_name else sh.sheet1

def read_rows(ws):
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
    # IMPORTANT: this must be a real f-string like below (no asterisks around the variable name)
    ws.update(range_name=f"C{row_idx_1_based}:I{row_idx_1_based}", values=[values])
