# NetWorth Tracker — Local Setup Guide

## Prerequisites
- Python 3.11+
- Node.js 18+
- A Google account
- Git

---

## Step 1 — Google Sheets & API Setup

### 1a. Create your Google Spreadsheet
1. Go to https://sheets.google.com and create a **new blank spreadsheet**
2. Name it: `NetWorth Tracker`
3. Copy the **Spreadsheet ID** from the URL:
   ```
   https://docs.google.com/spreadsheets/d/THIS_IS_YOUR_ID/edit
   ```

### 1b. Create a Google Cloud Service Account
1. Go to https://console.cloud.google.com
2. Create a **new project** (e.g., `networth-tracker`)
3. Enable these APIs:
   - **Google Sheets API**
   - **Google Drive API**
4. Go to **IAM & Admin → Service Accounts → Create Service Account**
   - Name: `networth-bot`
   - Role: **Editor** (or "Basic → Editor")
5. Click the service account → **Keys → Add Key → Create new key → JSON**
6. Download the JSON file — this is your credentials file

### 1c. Share your Spreadsheet with the Service Account
1. Open the downloaded JSON — find the `"client_email"` field
   (looks like `networth-bot@your-project.iam.gserviceaccount.com`)
2. Open your Google Spreadsheet
3. Click **Share** → paste that email → **Editor** → Done

### 1d. Place credentials in the project
```bash
mkdir -p backend/credentials
# Move your downloaded JSON here:
mv ~/Downloads/your-project-*.json backend/credentials/service_account.json
```

---

## Step 2 — Backend Setup

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### Configure environment variables
```bash
cp .env.example .env
```

Edit `backend/.env`:
```
GOOGLE_SERVICE_ACCOUNT_FILE=credentials/service_account.json
GOOGLE_SPREADSHEET_ID=paste_your_spreadsheet_id_here
SECRET_KEY=generate-a-random-string-here
APP_PASSWORD=your-chosen-login-password
```

Generate a secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Start the backend
```bash
uvicorn main:app --reload --port 8000
```

Test it: http://localhost:8000/api/health → should return `{"status":"ok"}`

---

## Step 3 — Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

---

## Step 4 — GitHub Setup

```bash
cd "C:\Anand\AI and Prompting\Projects\NetWorth Tracker"
git init
git remote add origin https://github.com/ANDANK/Net-worth-Tracker.git
git add .
git commit -m "Initial project scaffold"
git branch -M main
git push -u origin main
```

> The `.gitignore` already excludes `.env` and `credentials/` — your secrets are safe.

---

## First Run Checklist

- [ ] Google Spreadsheet created
- [ ] Service account JSON in `backend/credentials/service_account.json`
- [ ] Spreadsheet shared with service account email
- [ ] `backend/.env` configured with spreadsheet ID and password
- [ ] Backend running on port 8000
- [ ] Frontend running on port 5173
- [ ] Log in with your chosen `APP_PASSWORD`
- [ ] Add your first account via the Accounts page
- [ ] Record a net worth snapshot via Settings

---

## Supported Broker Files

| Broker | Export Location |
|--------|----------------|
| Robinhood | Account → Statements → Export |
| Schwab | Accounts → History → Export |
| Fidelity | Activity & Orders → Download |
| Vanguard | My Accounts → Transaction History → Export |
| Webull | Orders → Export |
| E\*TRADE | Accounts → Transactions → Download |

All exports should be CSV or XLSX format.
