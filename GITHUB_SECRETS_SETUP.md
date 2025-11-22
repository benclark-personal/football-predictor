# GitHub Secrets Setup for Daily Predictions

## What This Does

GitHub Actions will automatically run your predictions every day at **06:00 UTC** (07:00 BST in summer, 06:00 GMT in winter).

The workflow was just pushed to your repository: [https://github.com/benclark-personal/football-predictor](https://github.com/benclark-personal/football-predictor)

---

## Step 1: Add Secrets to GitHub

You need to add 3 secrets to your GitHub repository so the workflow can access your APIs.

### Go to GitHub Secrets Settings:

1. Open: **https://github.com/benclark-personal/football-predictor/settings/secrets/actions**
2. Click **"New repository secret"** button
3. Add each secret below:

### Secret 1: FOOTBALL_DATA_API_KEY

- **Name**: `FOOTBALL_DATA_API_KEY`
- **Value**: `28eb85e7c65845f084eee774037e4344`

Click "Add secret"

### Secret 2: SUPABASE_URL

- **Name**: `SUPABASE_URL`
- **Value**: `https://haeocsilkykqrukjzyzw.supabase.co`

Click "Add secret"

### Secret 3: SUPABASE_KEY

- **Name**: `SUPABASE_KEY`
- **Value**:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhhZW9jc2lsa3lrcXJ1a2p6eXp3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM4MTAzNDksImV4cCI6MjA3OTM4NjM0OX0.CjD_M0PMeJazOKOf2vCk-U6D5GL-O_d-oFf8llmKTm0
```

Click "Add secret"

---

## Step 2: Verify Setup

After adding the secrets:

1. Go to: **https://github.com/benclark-personal/football-predictor/actions**
2. Click on **"Daily Football Predictions"** workflow
3. Click **"Run workflow"** dropdown → **"Run workflow"** button
4. This will test the workflow manually (don't wait until tomorrow!)

---

## Expected Behavior

### Automatic Schedule
- **Every day at 06:00 UTC**
- Processes all 13 leagues
- Takes ~13-15 minutes
- Updates Supabase database
- Logs saved for 7 days

### Manual Trigger
You can also trigger it manually anytime:
1. Go to Actions tab
2. Click "Daily Football Predictions"
3. Click "Run workflow" button

---

## View Logs

To see what happened during a run:

1. Go to: **https://github.com/benclark-personal/football-predictor/actions**
2. Click on any workflow run
3. Click "generate-predictions" job
4. Expand each step to see logs
5. Download "prediction-logs" artifact for full log file

---

## Troubleshooting

### Workflow not running?
- Check secrets are added correctly (no extra spaces)
- Verify workflow file exists in `.github/workflows/`
- GitHub Actions must be enabled in Settings → Actions

### Workflow failing?
- Check the logs in Actions tab
- Common issues:
  - Missing secrets
  - API rate limits (Football-Data.org free tier)
  - Network timeouts

### Change the time?
Edit `.github/workflows/daily-predictions.yml`:
```yaml
schedule:
  - cron: '0 6 * * *'  # Change '6' to different hour (UTC)
```

Commit and push the change.

---

## What Happens Next

1. **Today**: Add secrets and test manually
2. **Tomorrow at 06:00 UTC**: First automatic run
3. **Every day**: Fresh predictions appear in your dashboard
4. **Your Mac can be off** - runs in GitHub's cloud!

---

## Remove Cron Job (Optional)

Since GitHub Actions is now handling this, you can remove the local cron job:

```bash
crontab -l  # View current cron jobs
crontab -r  # Remove all cron jobs
```

Or edit to keep other jobs:
```bash
crontab -e  # Opens editor to remove specific line
```

---

**Your automated predictions are ready to go!** Just add the 3 secrets and test the workflow. 🚀
