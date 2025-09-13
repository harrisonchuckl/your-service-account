import requests
from .config import SCRAPERAPI_KEY, TIMEOUT, USER_AGENT, CONTACT_PATHS
from .logging_utils import get_logger
logger = get_logger("crawl")

def fetch(url):
    headers = {"User-Agent": USER_AGENT}
    if SCRAPERAPI_KEY:
        api = "http://api.scraperapi.com"
        params = {"api_key": SCRAPERAPI_KEY, "url": url, "render": "false"}
        r = requests.get(api, params=params, headers=headers, timeout=TIMEOUT)
    else:
        r = requests.get(url, headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text

def crawl_candidate_pages(root_url):
    html_by_url = {}
    for path in CONTACT_PATHS:
        u = root_url.rstrip("/") + path
        try:
            html_by_url[u] = fetch(u)
        except Exception as e:
            logger.info(f"Skip {u}: {e}")
    return html_by_url

