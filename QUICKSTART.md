# Quick Start Guide

Get the Football Predictor running in 10 minutes.

## Prerequisites

- Python 3.8+
- Sportmonks API key (free tier)
- Supabase account (free tier)

## Step 1: Clone & Install (2 minutes)

```bash
# Clone repository
git clone https://github.com/benclark-personal/football-predictor.git
cd football-predictor

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Configure Environment (3 minutes)

```bash
# Copy example environment file
cp .env.example .env

# Edit with your credentials
nano .env  # or use your preferred editor
```

Add your API keys:

```bash
SPORTMONKS_API_KEY=your_sportmonks_api_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
```

**Get API Keys:**
- **Sportmonks**: https://my.sportmonks.com → Dashboard → API
- **Supabase**: https://app.supabase.com → Settings → API

## Step 3: Set Up Database (2 minutes)

1. Go to your Supabase dashboard
2. Click **SQL Editor**
3. Copy contents of `database/schema.sql`
4. Paste and click **Run**

## Step 4: Run First Prediction (3 minutes)

```bash
python main.py predict
```

You should see:

```
2025-11-22 10:30:15 - Predictor initialised successfully
2025-11-22 10:30:16 - Found 8 fixtures
2025-11-22 10:30:20 - Processing: Celtic vs Rangers
2025-11-22 10:30:25 - Stored prediction for Celtic vs Rangers
...
2025-11-22 10:31:00 - Processed 8 fixtures successfully
```

## Step 5: Check Results

**In Supabase:**
1. Go to **Table Editor**
2. Open `predictions` table
3. See your predictions!

**In Terminal:**
```bash
cat predictor.log
```

## Next Steps

### Daily Automation

Add to crontab (macOS/Linux):

```bash
crontab -e
```

Add these lines:

```bash
# Predictions at 8am
0 8 * * * cd /path/to/football-predictor && /path/to/venv/bin/python main.py predict

# Learn from results at 11pm
0 23 * * * cd /path/to/football-predictor && /path/to/venv/bin/python main.py learn
```

### Optional: Google Sheets Export

1. Follow [SETUP_GUIDE.md](docs/SETUP_GUIDE.md#google-sheets-setup-optional)
2. Place `credentials.json` in project root
3. Run predictions again

### Build React Frontend

See [FRONTEND_PLAN.md](docs/FRONTEND_PLAN.md) for complete guide.

```bash
cd frontend
npm install
npm run dev
```

## Common Issues

### "Module not found"
```bash
pip install -r requirements.txt
```

### "Invalid API key"
- Check your Sportmonks API key is correct
- Verify it's active at https://my.sportmonks.com

### "Connection refused" (Supabase)
- Verify `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
- Check Supabase project is running

### "No fixtures found"
- Normal if no matches scheduled in next 7 days
- Try increasing days: edit `main.py` line with `days_ahead=14`

## Getting Help

- **Documentation**: See `docs/` folder
- **Issues**: https://github.com/benclark-personal/football-predictor/issues
- **Detailed Setup**: [SETUP_GUIDE.md](docs/SETUP_GUIDE.md)

---

**That's it! Your prediction system is running.** ⚽

Check back after matches finish and run:

```bash
python main.py learn
```

The system will fetch results and adjust its weights automatically.
