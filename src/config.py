# src/config.py
import os

# ---------- helper getters ----------
def _get(name: str, default: str = "") -> str:
    v = os.getenv(name)
    if v is None:
        return default
    v = str(v).strip()
    return v if v != "" else default

def _getint(name: str, default: int) -> int:
    v = os.getenv(name)
    try:
        s = ("" if v is None else str(v).strip())
        return int(s) if s != "" else default
    except Exception:
        return default

def _getbool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    s = str(v).strip().lower()
    return s in {"1", "true", "yes", "y", "on"}

# ---------- required auth / sheet ----------
GOOGLE_SA_JSON_B64 = _get("GOOGLE_SA_JSON_B64")  # base64 of the Service Account JSON
SHEET_ID           = _get("SHEET_ID")
SHEET_TAB          = _get("SHEET_TAB", "Sheet1")

# ---------- general behavior ----------
DEFAULT_LOCATION   = _get("DEFAULT_LOCATION", "Ely")
MAX_ROWS           = _getint("MAX_ROWS", 100)  # how many sheet rows to process per run

# Prefer emails on the company’s own domain if available (e.g. info@company.com)
PREFER_COMPANY_DOMAIN = _getbool("PREFER_COMPANY_DOMAIN", True)
# If nothing on-company-domain is found, still accept an off-domain email (e.g. gov.uk) rather than nothing
ACCEPT_OFFDOMAIN_EMAILS = _getbool("ACCEPT_OFFDOMAIN_EMAILS", True)

# ---------- crawl / network knobs ----------
HTTP_TIMEOUT       = _getint("HTTP_TIMEOUT_
