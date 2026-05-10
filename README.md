# WhatsApp Finance Bot — Full Setup Guide

Everything free. Estimated time: 3–4 hours total.

---

## Overview of what you're building

```
You & partner (WhatsApp)
        ↓  message
  Meta Cloud API  (free, handles WhatsApp protocol)
        ↓  POST to your webhook
  Flask app on Render.com  (free hosting)
        ↓  read config / write rows
  Google Sheets  (your Finance Tracker spreadsheet)
        ↑
  cron-job.org pings /ping every 14 min  (keeps server warm)
```

---

## Part 1 — Google Sheets setup  (~30 min)

### 1.1 — Upload your spreadsheet to Google Sheets

1. Open Google Drive → **New → File Upload** → select `Household_Finance_Tracker.xlsx`
2. Once uploaded, right-click → **Open with → Google Sheets**
3. Copy the **Spreadsheet ID** from the URL:
   ```
   https://docs.google.com/spreadsheets/d/THIS_IS_YOUR_ID/edit
   ```
   Save it — you'll need it later.

### 1.2 — Create a Google Cloud project

1. Go to https://console.cloud.google.com
2. Click the project dropdown (top left) → **New Project**
3. Name it anything (e.g. "finance-bot") → **Create**
4. Make sure your new project is selected in the dropdown

### 1.3 — Enable the Google Sheets API

1. In the left menu → **APIs & Services → Library**
2. Search for "Google Sheets API" → click it → **Enable**

### 1.4 — Create a Service Account (your bot's identity for Sheets)

1. **APIs & Services → Credentials → Create Credentials → Service Account**
2. Name: `finance-bot` → **Create and Continue** → **Done**
3. Click the service account email you just created
4. Tab **Keys → Add Key → Create new key → JSON → Create**
5. A `.json` file downloads automatically — **keep this safe, treat it like a password**

### 1.5 — Share the spreadsheet with the service account

1. Open the `.json` file — find the `client_email` field:
   ```
   "client_email": "finance-bot@your-project.iam.gserviceaccount.com"
   ```
2. Open your Google Sheet → **Share** (top right)
3. Paste that email address → set role to **Editor** → **Send**

The bot can now read and write your spreadsheet.

### 1.6 — Prepare the credentials for your .env

Open the `.json` key file in a text editor.
Minify it to a single line (you can use https://jsonformatter.org/json-minifier).
This single-line JSON is your `GOOGLE_CREDENTIALS_JSON` value.

---

## Part 2 — Meta / WhatsApp setup  (~60 min, mostly waiting)

### 2.1 — Create a Meta Developer account

1. Go to https://developers.facebook.com
2. Sign in with any Facebook account (personal is fine, it won't affect it)
3. Click **My Apps → Create App**
4. Choose **Business** type → give it any name → **Create App**

### 2.2 — Add WhatsApp to your app

1. In your app dashboard → scroll to **Add Products** → find **WhatsApp** → **Set up**
2. You'll land on the WhatsApp API Setup page

### 2.3 — Get a free test phone number

Meta provides a free test sender number automatically.
On the API Setup page you'll see:
- **From** — the test phone number Meta gave you (you don't pay for this)
- **To** — your own WhatsApp number

Click **Add phone number** under "To" to pre-approve your number and your partner's number.
You can approve up to 5 numbers on the free test number — more than enough.

### 2.4 — Get your credentials

On the API Setup page, collect:
- **Phone Number ID** (a long number, NOT the phone number itself)
- **Temporary access token** — copy it, but we'll replace it with a permanent one next

### 2.5 — Create a permanent access token (important — test tokens expire in 24h)

1. Go to **Business Settings** (business.facebook.com/settings)
2. **Users → System Users → Add** → name it "finance-bot" → role: **Admin**
3. Click **Generate New Token** → select your app → grant `whatsapp_business_messaging` permission
4. Copy the token — this one **never expires**

This permanent token is your `WHATSAPP_TOKEN`.

---

## Part 3 — Deploy to Render.com  (~30 min)

### 3.1 — Push code to GitHub

1. Create a new **private** repository on GitHub
2. In the `whatsapp-bot/` folder on your machine:
   ```bash
   git init
   git add .
   git commit -m "initial bot"
   git remote add origin https://github.com/YOUR_USERNAME/finance-bot.git
   git push -u origin main
   ```
   ⚠️ Make sure `.env` is in `.gitignore` — **never** push real credentials.

### 3.2 — Create a Render web service

1. Go to https://render.com → **New → Web Service**
2. Connect your GitHub account → select your `finance-bot` repo
3. Settings:
   | Field | Value |
   |---|---|
   | Name | finance-bot (or whatever) |
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1` |
   | Plan | **Free** |

### 3.3 — Set environment variables in Render

In Render → your service → **Environment** tab, add these:

| Key | Value |
|---|---|
| `BOT_NAME` | Whatever you want to name the bot |
| `WHATSAPP_TOKEN` | Your permanent Meta system user token |
| `WHATSAPP_PHONE_ID` | The Phone Number ID from Meta |
| `VERIFY_TOKEN` | Any string you choose (e.g. `my_secret_2025`) |
| `SPREADSHEET_ID` | From your Google Sheet URL |
| `GOOGLE_CREDENTIALS_JSON` | The minified single-line JSON from your service account key |

### 3.4 — Deploy and get your URL

Click **Deploy**. After ~2 minutes, Render gives you a URL like:
```
https://finance-bot-xxxx.onrender.com
```

Test it: open `https://your-url.onrender.com/ping` in a browser.
You should see: `{"bot": "MoneyBot", "status": "alive"}`

---

## Part 4 — Register the webhook with Meta  (~10 min)

### 4.1 — Configure the webhook

1. In Meta Developer Dashboard → your app → **WhatsApp → Configuration**
2. Under **Webhook**, click **Edit**
3. Fill in:
   - **Callback URL**: `https://your-url.onrender.com/webhook`
   - **Verify Token**: the exact string you set as `VERIFY_TOKEN`
4. Click **Verify and Save**

If it says "Verified" ✅ you're good. If it fails, check that your Render service is running.

### 4.2 — Subscribe to messages

Still in **WhatsApp → Configuration → Webhook fields**:
- Find `messages` → click **Subscribe**

This tells Meta to forward all incoming messages to your webhook.

---

## Part 5 — Set up the ping to avoid cold starts  (~5 min)

### 5.1 — Create a free cron job

1. Go to https://cron-job.org → **Sign up free**
2. **Cronjobs → Create cronjob**
3. Settings:
   | Field | Value |
   |---|---|
   | URL | `https://your-url.onrender.com/ping` |
   | Schedule | Every 14 minutes |
4. **Save**

This pings your server every 14 minutes. Render's free tier sleeps after 15 minutes of inactivity, so this keeps it perpetually warm.

### 5.2 — What to expect without the ping

| Scenario | Cold start time |
|---|---|
| Server was pinged recently | < 1 second |
| Server slept (no ping) | 20–40 seconds |
| Mid-conversation restart | User gets "cancelled" message, must restart flow |

---

## Part 6 — Test it end to end

1. Open WhatsApp and message the test number Meta gave you
2. Send any text — you should get the welcome menu
3. Log a test expense
4. Open your Google Sheet → Transaction Log tab → should see the new row

---

## Part 7 — Keeping it fresh

### Updating categories or accounts

Edit the Setup sheet in Google Drive, then either:
- Wait up to 1 hour (cache auto-expires), or
- Visit `https://your-url.onrender.com/refresh` to reload immediately

### Adding your partner

Your partner just messages the same bot number. Meta's test number supports up to 5 approved numbers — add theirs in Meta Dashboard → WhatsApp → API Setup → To field.

### Upgrading to a real phone number (optional, ~€1-2/month)

When you're ready to move beyond the test number:
1. In Meta Dashboard → **WhatsApp → Phone Numbers → Add phone number**
2. Use a virtual number from Twilio or Vonage (~€1/month)
3. The rest stays the same — just update `WHATSAPP_PHONE_ID` in Render

---

## File structure

```
whatsapp-bot/
├── app.py            Main Flask app, webhook endpoints
├── conversation.py   State machine — all conversation logic
├── sheets.py         Google Sheets read/write
├── config.py         Environment variables + sheet range config
├── requirements.txt  Python dependencies
├── Procfile          Render/Heroku start command
├── .env.example      Template (copy to .env, never commit .env)
└── README.md         This file
```

## Customising the bot

### Change the bot's name
Set `BOT_NAME` in Render environment variables.

### Change the welcome message or question wording
Edit `conversation.py` — all user-facing strings are plain Python strings.
The `_step_idle()` function is the first message users see.

### Add a new transaction type or question
The state machine in `conversation.py` follows a simple pattern:
each step handler sets `_set(phone, next_step, data)` and returns the next question.
Add new steps by following the same pattern.

### If the Setup sheet layout changes
Update `SETUP_RANGES` in `config.py` with the new row ranges,
then visit `/refresh` to reload.

---

## Cost summary

| Service | Cost |
|---|---|
| Meta Cloud API (WhatsApp) | Free (≤1,000 conversations/month) |
| Google Sheets API | Free |
| Google Cloud (service account) | Free |
| Render.com (web service) | Free |
| cron-job.org (ping) | Free |
| GitHub (private repo) | Free |
| **Total** | **€0 / month** |