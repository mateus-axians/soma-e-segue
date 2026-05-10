"""
sheets.py
Handles all Google Sheets interactions:
  - Reading config (categories, accounts, members) from Setup sheet
  - Appending new transaction rows to the Transaction Log
"""

import json
import time
import logging
from datetime import datetime

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# ─── Auth ─────────────────────────────────────────────────────────────────────

def _get_service():
    """Build and return an authenticated Sheets API service."""
    creds_dict = json.loads(config.GOOGLE_CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


# ─── Config cache ─────────────────────────────────────────────────────────────

_cache: dict = {}
_cache_loaded_at: float = 0.0

def _read_range(service, range_name: str) -> list[str]:
    """Read a single-column range and return non-empty string values."""
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=config.SPREADSHEET_ID,
            range=range_name
        ).execute()
        rows = result.get("values", [])
        # Flatten single-column rows, strip whitespace, drop empties
        return [row[0].strip() for row in rows if row and row[0].strip()]
    except HttpError as e:
        logger.error("Sheets read error for %s: %s", range_name, e)
        return []

def get_config() -> dict:
    """
    Return config dict with lists: accounts, categories, income_types, members.
    Results are cached for CONFIG_CACHE_TTL seconds to avoid hammering the API.
    """
    global _cache, _cache_loaded_at
    now = time.time()
    if _cache and (now - _cache_loaded_at) < config.CONFIG_CACHE_TTL:
        return _cache

    logger.info("Refreshing config from Google Sheets...")
    try:
        service = _get_service()
        fresh: dict = {}
        for key, range_name in config.SETUP_RANGES.items():
            fresh[key] = _read_range(service, range_name)
            logger.info("  %s: %d items", key, len(fresh[key]))
        _cache = fresh
        _cache_loaded_at = now
        return _cache
    except Exception as e:
        logger.error("Failed to load config from Sheets: %s", e)
        # Return stale cache if available, otherwise empty
        return _cache or {k: [] for k in config.SETUP_RANGES}

def force_refresh():
    """Force a config reload on next get_config() call."""
    global _cache_loaded_at
    _cache_loaded_at = 0.0


# ─── Writing transactions ──────────────────────────────────────────────────────

def log_transaction(
    date: datetime,
    description: str,
    tx_type: str,        # "Expense" | "Income" | "Savings Transfer"
    category: str,       # expense category or income type
    amount: float,
    account: str,
    person: str,
    notes: str = "",
) -> bool:
    """
    Append one row to the Transaction Log sheet.
    Returns True on success, False on failure.

    Column mapping (matches the tracker template):
      B: Date        C: Description   D: Type
      E: Category    F: Amount        G: Account
      H: Person      I: Month         J: Notes
    """
    date_str  = date.strftime("%d/%m/%Y")
    month_str = date.strftime("%b %Y")   # e.g. "May 2025"

    row = [
        date_str,           # B — Date
        description,        # C — Description
        tx_type,            # D — Type
        category,           # E — Category / Income Type
        amount,             # F — Amount
        account,            # G — Account
        person,             # H — Paid By / Received By
        month_str,          # I — Month (we write it directly; sheet formula handles existing rows)
        notes,              # J — Notes
    ]

    try:
        service = _get_service()
        body = {"values": [row]}
        service.spreadsheets().values().append(
            spreadsheetId=config.SPREADSHEET_ID,
            range=config.LOG_RANGE,
            valueInputOption="USER_ENTERED",   # Lets Sheets parse the date string
            insertDataOption="INSERT_ROWS",
            body=body,
        ).execute()
        logger.info("Logged %s €%.2f (%s / %s)", tx_type, amount, category, person)
        return True
    except HttpError as e:
        logger.error("Failed to write transaction: %s", e)
        return False