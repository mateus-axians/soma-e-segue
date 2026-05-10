import os
from dotenv import load_dotenv
 
load_dotenv()
 
# ─── Bot identity ────────────────────────────────────────────────────────────
BOT_NAME = os.getenv("BOT_NAME", "Soma e Segue")   # Change this to whatever you name it
 
# ─── WhatsApp / Meta ─────────────────────────────────────────────────────────
# All from Meta Developer Dashboard → Your App → WhatsApp → API Setup
WHATSAPP_TOKEN    = os.getenv("WHATSAPP_TOKEN")      # Permanent token (from System User)
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")   # "Phone number ID", NOT the number itself
VERIFY_TOKEN      = os.getenv("VERIFY_TOKEN", "my_verify_secret")  # Any string you choose
 
# ─── Google Sheets ───────────────────────────────────────────────────────────
# SPREADSHEET_ID is the long ID in your Google Sheet URL:
# https://docs.google.com/spreadsheets/d/THIS_PART_HERE/edit
SPREADSHEET_ID            = os.getenv("SPREADSHEET_ID")
# Paste the entire contents of your service account JSON file as a single-line string
GOOGLE_CREDENTIALS_JSON   = os.getenv("GOOGLE_CREDENTIALS_JSON")
 
# ─── Sheet ranges ────────────────────────────────────────────────────────────
# These match the exact layout of the Finance Tracker template.
# Only change these if you've rearranged the Setup sheet.
SETUP_RANGES = {
    "accounts":     "'⚙️ Setup'!B8:B17",    # Account names (col B, rows 8-17)
    "categories":   "'⚙️ Setup'!B21:B50",   # Expense categories (col B, rows 21-50)
    "income_types": "'⚙️ Setup'!B54:B63",   # Income types (col B, rows 54-63)
    "members":      "'⚙️ Setup'!D8:D12",    # Member names (col D, rows 8-12)
}
 
# Where new transactions are appended (col B = Date, through col J = Notes)
LOG_RANGE = "'📝 Transaction Log'!B:J"
 
# Re-read config from Sheets every N seconds (avoids hitting API on every message)
CONFIG_CACHE_TTL = 3600  # 1 hour
