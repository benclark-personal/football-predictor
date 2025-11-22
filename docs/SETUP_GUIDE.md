# Football Predictor - Detailed Setup Guide

Complete step-by-step guide to get the football prediction system running.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Sportmonks API Setup](#sportmonks-api-setup)
3. [Supabase Setup](#supabase-setup)
4. [Google Sheets Setup](#google-sheets-setup-optional)
5. [Local Installation](#local-installation)
6. [First Run](#first-run)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required

- **Python 3.8 or higher**
  ```bash
  python3 --version  # Should show 3.8+
  ```

- **pip** (Python package manager)
  ```bash
  pip3 --version
  ```

- **Git**
  ```bash
  git --version
  ```

### Accounts Needed

1. **Sportmonks** - Football data API (free tier available)
2. **Supabase** - Database hosting (free tier available)
3. **Google Cloud** - For Sheets integration (optional, free)
4. **GitHub** - Code hosting (free)

---

## Sportmonks API Setup

### Step 1: Create Account

1. Go to https://www.sportmonks.com
2. Click "Sign Up" or "Get Started"
3. Choose **Free Plan** (includes 2 leagues)
4. Complete registration

### Step 2: Get API Key

1. Log in to https://my.sportmonks.com
2. Navigate to **Dashboard** → **API**
3. Copy your **API Token**
4. Save it securely (you'll need this later)

### Step 3: Verify Access

Test your API key:

```bash
curl "https://api.sportmonks.com/v3/football/leagues?api_token=YOUR_API_KEY"
```

You should see JSON data with league information.

### Free Tier Limits

- **180 requests per minute**
- **2 leagues** (Scottish Premiership, Danish Superliga included)
- **Historical data** limited to last 3 months

---

## Supabase Setup

### Step 1: Create Project

1. Go to https://supabase.com
2. Click "Start your project"
3. Sign in with GitHub
4. Click "New project"
5. Fill in:
   - **Name**: football-predictor
   - **Database Password**: (create a strong password, save it)
   - **Region**: Choose closest to you
   - **Plan**: Free
6. Click "Create new project"

Wait 2-3 minutes for project to initialise.

### Step 2: Get API Credentials

1. In your Supabase dashboard, go to **Settings** → **API**
2. Copy these values:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon/public key**: Long string starting with `eyJ...`

### Step 3: Create Database Tables

1. Go to **SQL Editor** in the left menu
2. Click "+ New query"
3. Open `database/schema.sql` from this repo
4. Copy all contents and paste into the SQL editor
5. Click "Run" or press `Ctrl+Enter`
6. You should see "Success" message

### Step 4: Verify Tables

1. Go to **Table Editor** in the left menu
2. You should see 3 tables:
   - `predictions`
   - `prediction_accuracy`
   - `learning_weights`

---

## Google Sheets Setup (Optional)

If you want predictions exported to Google Sheets, follow these steps.

### Step 1: Create Google Cloud Project

1. Go to https://console.cloud.google.com
2. Click "Select a project" → "New Project"
3. Name: "Football Predictor"
4. Click "Create"

### Step 2: Enable APIs

1. In the search bar, type "Google Sheets API"
2. Click "Google Sheets API" → "Enable"
3. Go back, search "Google Drive API"
4. Click "Google Drive API" → "Enable"

### Step 3: Create Service Account

1. Go to **IAM & Admin** → **Service Accounts**
2. Click "Create Service Account"
3. Name: "football-predictor-service"
4. Click "Create and Continue"
5. Role: Select "Editor"
6. Click "Continue" → "Done"

### Step 4: Generate Credentials

1. Click on the service account you just created
2. Go to **Keys** tab
3. Click "Add Key" → "Create new key"
4. Choose **JSON**
5. Click "Create"
6. A JSON file will download automatically
7. Rename it to `credentials.json`
8. Copy the `client_email` from the JSON file (looks like `football-predictor-service@...`)

### Step 5: Create and Share Google Sheet

1. Go to https://sheets.google.com
2. Create a new spreadsheet
3. Name it "Football Momentum Predictor"
4. Click "Share" button
5. Paste the `client_email` you copied earlier
6. Give it "Editor" access
7. Click "Done"

---

## Local Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/Benclark-personal/football-predictor.git
cd football-predictor
```

### Step 2: Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt.

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install all required packages.

### Step 4: Configure Environment Variables

```bash
# Copy example file
cp .env.example .env

# Edit with your favourite editor
nano .env
# or
code .env
```

Fill in your API keys:

```bash
# Sportmonks
SPORTMONKS_API_KEY=your_sportmonks_key_here

# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Google Sheets (if using)
GOOGLE_CREDENTIALS_PATH=credentials.json
```

Save and close.

### Step 5: Add Google Credentials (If Using)

```bash
# Copy your downloaded JSON file to the project root
cp ~/Downloads/your-service-account-key.json credentials.json
```

---

## First Run

### Test Configuration

```bash
python main.py predict
```

You should see:

```
2025-11-22 10:30:15 - Predictor initialised successfully
2025-11-22 10:30:15 - Starting Momentum Predictor with Learning...
2025-11-22 10:30:16 - Fetched 8 fixtures for league 501
2025-11-22 10:30:17 - Fetched 12 fixtures for league 271
...
```

### Check the Output

1. **Terminal**: See progress logs
2. **Supabase**: Check `predictions` table for new rows
3. **Google Sheets**: Check your spreadsheet for data
4. **Logs**: Check `predictor.log` file

### First Learning Run

Wait until some matches finish (check next day), then:

```bash
python main.py learn
```

You should see:

```
2025-11-23 10:00:00 - Starting learning mode
2025-11-23 10:00:01 - Found 5 pending predictions to check
2025-11-23 10:00:02 - Updated result: Celtic 3-1 Rangers
...
2025-11-23 10:00:10 - Made 3 weight adjustments
```

---

## Troubleshooting

### "Missing required environment variables"

**Problem**: `.env` file not configured correctly.

**Solution**:
```bash
# Check .env exists
ls -la .env

# Verify contents
cat .env

# Make sure all three required variables are set:
# SPORTMONKS_API_KEY
# SUPABASE_URL
# SUPABASE_KEY
```

### "401 Unauthorized" from Sportmonks

**Problem**: Invalid API key.

**Solution**:
1. Log in to Sportmonks dashboard
2. Verify your API key is correct
3. Check if you copied it completely (no spaces)
4. Make sure your subscription is active

### "Connection refused" from Supabase

**Problem**: Supabase credentials incorrect or project not ready.

**Solution**:
1. Check Supabase project is fully initialised (green status)
2. Verify `SUPABASE_URL` and `SUPABASE_KEY` are correct
3. Test connection:
   ```bash
   curl "YOUR_SUPABASE_URL/rest/v1/predictions?select=*" \
     -H "apikey: YOUR_SUPABASE_KEY"
   ```

### "Table does not exist"

**Problem**: Database schema not created.

**Solution**:
1. Go to Supabase SQL Editor
2. Run `database/schema.sql` script
3. Verify tables exist in Table Editor

### "Google Sheets authentication failed"

**Problem**: Credentials not set up correctly.

**Solution**:
1. Verify `credentials.json` exists in project root
2. Check service account email is shared with the Sheet
3. Ensure both Google Sheets API and Drive API are enabled
4. Try creating a new service account key

### "Rate limit exceeded"

**Problem**: Making too many API requests.

**Solution**:
- System should prevent this automatically
- If it happens, check `.env`:
  ```bash
  RATE_LIMIT_CALLS=150  # Reduce if needed
  RATE_LIMIT_PERIOD=60
  ```
- Wait 1 minute before retrying

### "No fixtures found"

**Problem**: No matches scheduled in date range.

**Solution**:
- Check Sportmonks website for upcoming matches
- Try increasing days ahead:
  ```python
  # In main.py
  fixtures = self.fetch_fixtures(days_ahead=14)  # Look 14 days ahead
  ```

### "Insufficient match data"

**Problem**: Team hasn't played many matches yet (season start).

**Solution**:
- This is expected early in the season
- Predictions will have low confidence scores
- System still works but with reduced accuracy
- More matches = better predictions

### "Module not found" errors

**Problem**: Dependencies not installed.

**Solution**:
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Reinstall dependencies
pip install -r requirements.txt

# Verify installation
pip list
```

---

## Next Steps

Once everything is working:

1. **Set up automation** (see README for cron examples)
2. **Monitor logs** regularly
3. **Check accuracy** after a week using Supabase queries
4. **Adjust configuration** based on results
5. **Start building the React frontend**

---

## Getting Help

If you're still having issues:

1. Check `predictor.log` for detailed error messages
2. Review the error message carefully
3. Search the issue in GitHub Issues
4. Create a new issue with:
   - Error message
   - What you tried
   - Your environment (OS, Python version)
   - Relevant log output

---

## Security Checklist

Before deploying:

- ✅ `.env` file in `.gitignore`
- ✅ `credentials.json` in `.gitignore`
- ✅ API keys never committed to git
- ✅ Supabase Row Level Security configured (if needed)
- ✅ Strong database password used
- ✅ Service account has minimal permissions

---

**Setup complete! You're ready to start predicting football matches.** ⚽
