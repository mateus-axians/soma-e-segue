# Finance Tracker PWA — Full Setup Guide

Zero cost. No server. No Meta. No verification. Works on any phone.

---

## What you're building

```
Browser (iPhone / Android / Desktop)
        ↓  HTTPS
  GitHub Pages  (free static hosting)
    index.html  — the app UI
        ↓  fetch()
  Google Apps Script  (free serverless, lives in your Google account)
    Code.gs  — reads config, writes rows
        ↓  Sheets API (internal, no key needed)
  Google Sheets  (your Finance Tracker spreadsheet)
```

Total cost: €0. No cold starts. No pinging. No accounts besides GitHub and Google.

---

## Part 1 — Google Sheets  (~5 min)

If you haven't already from the previous guide:

1. Upload `Household_Finance_Tracker.xlsx` to Google Drive
2. Open with Google Sheets
3. Copy the **Spreadsheet ID** from the URL:
   `docs.google.com/spreadsheets/d/THIS_IS_YOUR_ID/edit`

---

## Part 2 — Deploy the Apps Script backend  (~10 min)

This is the only backend you need. It runs inside Google's servers for free.

### 2.1 — Open Apps Script

1. In your Google Sheet: **Extensions → Apps Script**
2. A new tab opens with a code editor

### 2.2 — Paste the backend code

1. Delete everything in the editor
2. Open `Code.gs` from this project and paste the entire contents
3. Find this line at the top and paste your Spreadsheet ID:
   ```js
   const SPREADSHEET_ID = "PASTE_YOUR_SPREADSHEET_ID_HERE";
   ```
4. Set your PIN (or leave `""` to disable):
   ```js
   const ACCESS_PIN = "1234";
   ```
5. **Save** (Ctrl+S / Cmd+S) — name the project anything, e.g. "Finance Bot"

### 2.3 — Check the sheet ranges

Open your spreadsheet and verify the row numbers for your Setup sheet.
The defaults in `Code.gs` assume the template layout:
- Accounts: rows 8–17, column B
- Categories: rows 21–50, column B
- Income Types: rows 54–63, column B
- Members: rows 8–12, column D

If your layout differs, update the `RANGES` object in `Code.gs`.

### 2.4 — Deploy as Web App

1. Click **Deploy → New deployment**
2. Click the gear icon ⚙️ next to "Type" → select **Web app**
3. Settings:
   | Field | Value |
   |---|---|
   | Description | Finance Tracker API |
   | Execute as | **Me** |
   | Who has access | **Anyone** |
4. Click **Deploy**
5. You'll be asked to authorise — click through ("Allow")
6. **Copy the Web App URL** — it looks like:
   `https://script.google.com/macros/s/LONG_RANDOM_ID/exec`

⚠️ **Important**: every time you change `Code.gs` you must click  
**Deploy → Manage deployments → Edit → New version → Deploy**  
to publish the update. Just saving the file is not enough.

### 2.5 — Test the backend

Paste this into your browser (swap in your URL and PIN):
```
https://script.google.com/macros/s/YOUR_ID/exec?pin=1234
```
You should see a JSON response like:
```json
{"ok":true,"accounts":["Checking Account","Savings Account",...],...}
```
If you see `{"ok":false,"error":"Invalid PIN"}` — wrong PIN.  
If you see an error about the spreadsheet — check the SPREADSHEET_ID.

---

## Part 3 — Set up the PWA frontend  (~10 min)

### 3.1 — Edit index.html

Open `index.html` and find this line near the bottom:
```js
const SCRIPT_URL = "PASTE_YOUR_APPS_SCRIPT_URL_HERE";
```
Replace it with your Web App URL from Step 2.4.

### 3.2 — (Optional) Change the PIN length

The default is 4 digits. To change:
```js
const PIN_LENGTH = 4;  // change to any number
```
Match it with `ACCESS_PIN` in `Code.gs`.

### 3.3 — Create a GitHub repository

1. Go to github.com → **New repository**
2. Name it anything, e.g. `finance-tracker`
3. Set visibility to **Private** (so the URL isn't public)
   - Note: GitHub Pages requires a paid plan for private repos.
   - If you want free hosting, set it to **Public** — the code is just HTML,
     no secrets are in it (your PIN is validated server-side in Apps Script).
4. Upload all files from the `finance-pwa/` folder:
   - `index.html`
   - `manifest.json`
   - `sw.js`
   - (You don't need `Code.gs` or this README in the repo)

### 3.4 — Enable GitHub Pages

1. Go to your repo → **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / `(root)`
4. Click **Save**
5. After ~60 seconds, GitHub shows your URL:
   `https://YOUR_USERNAME.github.io/finance-tracker/`

That's your app link. Bookmark it. Share it with your partner.

---

## Part 4 — Install on your phone (feels like a real app)  (~2 min)

### iPhone (Safari)
1. Open the link in **Safari** (must be Safari, not Chrome)
2. Tap the **Share** button (box with arrow)
3. Tap **Add to Home Screen**
4. Name it "Finance" → **Add**

### Android (Chrome)
1. Open the link in **Chrome**
2. Tap the three-dot menu → **Add to Home screen**
3. Name it → **Add**

The app now appears on your home screen with its own icon, opens full-screen with no browser chrome, and works like a native app.

---

## Part 5 — Share with your partner

Just send them the GitHub Pages link. They open it, enter the PIN, and they're in.

Both of you can log simultaneously — Apps Script handles concurrent writes safely.

---

## How to update categories or accounts

1. Edit your Google Sheet (Setup tab) — add/remove categories, accounts, etc.
2. The app reads config live from the Sheet on every PIN login.
   No redeployment needed.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| PIN screen says "Network error" | Your SCRIPT_URL in index.html is wrong or missing |
| PIN accepted but lists are empty | Check RANGES in Code.gs match your sheet layout |
| "Transaction Log sheet not found" | The sheet tab name must be exactly `📝 Transaction Log` |
| Changes to Code.gs not working | You must deploy a new version (Step 2.4 warning) |
| App not installing on iPhone | Must use Safari, not Chrome or Firefox |

---

## File structure

```
finance-pwa/
├── index.html     The entire app (UI + logic)
├── manifest.json  PWA metadata (name, icon, colors)
├── sw.js          Service worker (offline support)
└── Code.gs        Google Apps Script backend (NOT uploaded to GitHub)
```

---

## Cost summary

| Service | Cost |
|---|---|
| GitHub Pages | Free |
| Google Apps Script | Free |
| Google Sheets | Free |
| **Total** | **€0 / month, forever** |
