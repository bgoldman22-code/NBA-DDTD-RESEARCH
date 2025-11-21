# NBA DD/TD Picks - Deployment Guide

## Overview
This guide walks through deploying the DD/TD picks system to your live RRMODEL website. The system includes:
- Daily automated picks generation via GitHub Actions
- Netlify serverless function for serving picks with caching
- React component for displaying picks with Kelly unit sizing
- Two-table UI: Recommended picks + All >35% probability players

## Security Requirements
🔒 **CRITICAL**: The Odds API key must NEVER be pushed to GitHub. It should only exist in:
1. GitHub Secrets (for Actions)
2. Netlify Environment Variables (for functions, if needed)
3. Local `.env` files (ignored by git)

## Prerequisites
- GitHub repository for NBA-DDTD-RESEARCH
- Netlify account with RRMODEL site deployed
- The Odds API key: `c5d3fe15e6c5be83b2acd8695cff012b`
- $4,500 bankroll, $10/unit base

---

## Step 1: Set Up GitHub Secret

1. Go to your GitHub repository: `github.com/YOUR_USERNAME/NBA-DDTD-RESEARCH`
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `ODDS_API_KEY`
5. Value: `c5d3fe15e6c5be83b2acd8695cff012b`
6. Click **Add secret**

This allows the GitHub Action to fetch live odds without exposing the key.

---

## Step 2: Verify GitHub Action Workflow

The workflow should already exist at `.github/workflows/generate-daily-picks.yml`. It should:
- Run daily at 3 PM UTC (10 AM ET, before games start)
- Install Python dependencies
- Run `scripts/generate_picks_for_rrmodel_v2.py` with the secret API key
- Commit the updated `data/nba/ddtd_today_picks.json`
- Push to main branch

**Verify the workflow:**

```bash
cat .github/workflows/generate-daily-picks.yml
```

Expected structure:
```yaml
name: Generate Daily NBA DD/TD Picks

on:
  schedule:
    - cron: '0 15 * * *'  # 3 PM UTC = 10 AM ET
  workflow_dispatch:  # Manual trigger

jobs:
  generate-picks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Generate picks
        env:
          ODDS_API_KEY: ${{ secrets.ODDS_API_KEY }}
        run: python scripts/generate_picks_for_rrmodel_v2.py
      - name: Commit picks
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add data/nba/ddtd_today_picks.json
          git commit -m "🤖 Daily picks update" || exit 0
          git push
```

**Test manually:**
1. Go to Actions tab in GitHub
2. Select "Generate Daily NBA DD/TD Picks"
3. Click "Run workflow"
4. Verify it succeeds and commits the JSON file

---

## Step 3: Copy Netlify Function

Copy the serverless function to your RRMODEL repository:

```bash
# From NBA-DDTD-RESEARCH directory
cp RRMODEL-files/netlify/functions/nba-ddtd-picks.mjs /path/to/RRMODEL/netlify/functions/

# Verify it exists
ls -la /path/to/RRMODEL/netlify/functions/nba-ddtd-picks.mjs
```

The function serves picks with 24-hour caching and falls back to GitHub raw URL if Netlify Blobs fails.

**Function endpoint:** `https://yourdomain.com/.netlify/functions/nba-ddtd-picks`

---

## Step 4: Set Up Netlify Environment Variable (Optional)

If you want the Netlify function to directly fetch odds (for future enhancements):

1. Go to Netlify dashboard
2. Select your RRMODEL site
3. Navigate to **Site settings** → **Environment variables**
4. Click **Add a variable**
5. Key: `ODDS_API_KEY`
6. Value: `c5d3fe15e6c5be83b2acd8695cff012b`
7. Scopes: Production, Deploy Previews, Branch deploys (as needed)
8. Click **Create variable**

**Note:** Currently, the function only serves pre-generated JSON from GitHub, so this is optional.

---

## Step 5: Copy React Component

Copy the updated component to your RRMODEL repository:

```bash
# From NBA-DDTD-RESEARCH directory
cp RRMODEL-files/src/components/NBADDTDPicks.jsx /path/to/RRMODEL/src/components/

# Verify it exists
ls -la /path/to/RRMODEL/src/components/NBADDTDPicks.jsx
```

---

## Step 6: Import Component in NBA Page

Edit your main NBA page (likely `src/pages/NBA.jsx` or similar):

```jsx
import NBADDTDPicks from '../components/NBADDTDPicks';

function NBAPage() {
  return (
    <div>
      <h1>NBA Picks & Analysis</h1>
      
      {/* Add DD/TD Picks Component */}
      <NBADDTDPicks />
      
      {/* ...other components */}
    </div>
  );
}

export default NBAPage;
```

---

## Step 7: Deploy to Netlify

### Option A: Auto-deploy (if connected to GitHub)
1. Push changes to your RRMODEL repository
2. Netlify will automatically build and deploy
3. Check build logs for any errors

### Option B: Manual deploy
```bash
# From RRMODEL directory
netlify deploy --prod

# Or use Netlify CLI
npm run build
netlify deploy --dir=dist --prod
```

---

## Step 8: Verify Live Deployment

### Test the API endpoint:
```bash
curl https://yourdomain.com/.netlify/functions/nba-ddtd-picks | jq
```

Expected response:
```json
{
  "date": "2025-11-21",
  "generated_at": "2025-11-21T14:30:00Z",
  "model_version": "v3",
  "bankroll": 4500,
  "unit_size": 10,
  "kelly_fraction": 0.25,
  "recommended_picks": {
    "dd": [...],
    "td": [...]
  },
  "high_probability": [...]
}
```

### Test the UI:
1. Visit `https://yourdomain.com/nba` (or wherever you added the component)
2. Verify the component loads
3. Check that both tabs work:
   - **Recommended Picks**: Shows DD/TD picks with Kelly units and $ amounts
   - **All >35% Probability**: Shows all high-probability players with/without edge
4. Verify data displays correctly:
   - Model probabilities
   - Best odds with bookmaker names (FanDuel, BetMGM, etc.)
   - Edge percentages (color-coded)
   - Kelly units and bet amounts
   - Player stats (pts/reb/ast)

---

## Monitoring & Maintenance

### Daily Checks
1. **Verify GitHub Action runs successfully** at 10 AM ET
   - Check Actions tab for green checkmark
   - Verify `ddtd_today_picks.json` updated

2. **Check live site loads picks**
   - Visit your NBA page
   - Confirm new picks display (date should be current)
   - Test refresh button

3. **Validate odds data**
   - Ensure bookmaker names appear
   - Check that odds look reasonable
   - Verify API request count (check The Odds API dashboard)

### Manual Update (if GitHub Action fails)

```bash
# Run locally
cd /Users/brentgoldman/Desktop/REPO33/NBA-DDTD-RESEARCH
export ODDS_API_KEY=c5d3fe15e6c5be83b2acd8695cff012b
python scripts/generate_picks_for_rrmodel_v2.py

# Verify output
cat data/nba/ddtd_today_picks.json

# Commit and push
git add data/nba/ddtd_today_picks.json
git commit -m "🤖 Manual picks update"
git push
```

The Netlify function will automatically serve the new JSON (cache expires after 24 hours).

---

## Troubleshooting

### Issue: Component shows "Error loading picks"
**Solutions:**
1. Check browser console for errors
2. Verify Netlify function deployed: `netlify functions:list`
3. Test API endpoint directly with curl
4. Check Netlify function logs

### Issue: GitHub Action fails
**Solutions:**
1. Check Actions tab for error details
2. Verify `ODDS_API_KEY` secret exists and is correct
3. Check if The Odds API quota exceeded (4.7M requests remaining)
4. Run script locally to reproduce error

### Issue: Picks not updating daily
**Solutions:**
1. Verify GitHub Action schedule is correct (3 PM UTC)
2. Check if Action is disabled (Settings → Actions)
3. Manually trigger Action to test
4. Verify git push permissions for Action

### Issue: Odds data missing or stale
**Solutions:**
1. Check The Odds API status and quota
2. Verify API key is valid
3. Check if markets available for today's games
4. Fall back to manual odds entry if needed

### Issue: Netlify function returns cached old data
**Solutions:**
1. Cache expires after 24 hours automatically
2. Clear Netlify Blobs cache manually if needed
3. Check if GitHub commit triggered but didn't update file

---

## File Structure Summary

```
NBA-DDTD-RESEARCH/
├── .github/workflows/generate-daily-picks.yml  # Daily automation
├── scripts/generate_picks_for_rrmodel_v2.py    # Picks generator
├── data/nba/ddtd_today_picks.json              # Output JSON (committed to repo)
├── RRMODEL-files/                              # Files to copy to RRMODEL
│   ├── netlify/functions/nba-ddtd-picks.mjs    # Serverless API
│   └── src/components/NBADDTDPicks.jsx         # React UI

RRMODEL/ (separate repo)
├── netlify/functions/nba-ddtd-picks.mjs        # Copy here
├── src/components/NBADDTDPicks.jsx             # Copy here
└── src/pages/NBA.jsx                           # Import component here
```

---

## API Key Security Checklist

Before pushing to GitHub, verify:
- [ ] No `.env` files committed (add to `.gitignore`)
- [ ] No hardcoded API keys in any Python scripts
- [ ] No API keys in Netlify function code
- [ ] GitHub secret `ODDS_API_KEY` is set
- [ ] Netlify environment variable `ODDS_API_KEY` is set (optional)
- [ ] `.gitignore` includes:
  ```
  .env
  .env.local
  *.env
  ```

---

## Success Criteria

✅ Deployment is successful when:
1. GitHub Action runs daily without errors
2. `ddtd_today_picks.json` updates every day at 10 AM ET
3. Live website displays fresh picks with correct data
4. Both UI tables work (Recommended + High Probability)
5. Kelly units and bet amounts display correctly
6. Bookmaker names appear next to odds
7. No API keys visible in browser or source code
8. Refresh button updates data from API

---

## Support & Resources

- **The Odds API Docs**: https://the-odds-api.com/
- **Netlify Functions**: https://docs.netlify.com/functions/overview/
- **GitHub Actions**: https://docs.github.com/en/actions
- **Model Documentation**: See `FINAL_DELIVERY_SUMMARY.md` and `RETRAINED-MODEL-RESULTS.md`

---

## Notes

- Picks are generated daily for games happening that evening
- Model uses data through Nov 20, 2025 (will need periodic updates)
- Quarter Kelly sizing ensures conservative bankroll management
- API costs ~$0.02 per day (500 requests @ $0.00004/request)
- Cache reduces Netlify function invocations and improves performance
- GitHub serves as free CDN for JSON file (raw.githubusercontent.com)

---

**Last Updated:** November 21, 2025  
**Model Version:** v3 (retrained Nov 20, 2025)  
**Bankroll:** $4,500 | **Unit:** $10 | **Kelly:** 0.25
