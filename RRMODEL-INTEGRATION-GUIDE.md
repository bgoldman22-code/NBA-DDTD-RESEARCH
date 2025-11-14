# NBA DD/TD Model Integration - Implementation Guide

This guide explains how to integrate the NBA Double-Double / Triple-Double prediction model with RRMODEL using the **Hybrid Approach** (Option 3).

## Architecture Overview

**Python Side (NBA-DDTD-RESEARCH):**
- Generates picks daily using Gradient Boosting model (200 trees)
- Runs via GitHub Actions at 10 AM daily
- Commits JSON to `data/nba/ddtd_today_picks.json`

**JavaScript Side (RRMODEL):**
- Netlify function reads pre-generated JSON from GitHub
- Caches in Netlify Blobs (24hr TTL)
- React component displays picks on frontend
- **No model inference in JavaScript** - just serving pre-computed picks

## Files Created

### NBA-DDTD-RESEARCH (This Repo)
1. `scripts/generate_picks_for_rrmodel.py` - Daily picks generator
2. `.github/workflows/generate-daily-picks.yml` - GitHub Action
3. `data/nba/ddtd_today_picks.json` - Daily picks output (generated)

### RRMODEL (Copy These Files)
Located in `RRMODEL-files/` directory:

1. **netlify/functions/_lib/blobs-nba.mjs** - Blob cache helper
2. **netlify/functions/nbaddtd-picks.mjs** - Main Netlify function
3. **src/components/NBADDTDPicks.jsx** - React component

Also copy these existing files:
- `models/nba/ddtd/acceptance_gates_v3.json`
- `models/nba/ddtd/current_teams.json`

## Installation Steps

### Step 1: Configure GitHub Secrets (NBA-DDTD-RESEARCH)

Add your Odds API key to GitHub repository secrets:

```bash
# Go to: https://github.com/YOUR_USERNAME/NBA-DDTD-RESEARCH/settings/secrets/actions
# Click "New repository secret"
# Name: ODDS_API_KEY
# Value: <your-odds-api-key>
```

### Step 2: Test Python Script Locally

```bash
# Set API key as environment variable
export ODDS_API_KEY="your-key-here"

# Run the script
cd /path/to/NBA-DDTD-RESEARCH
python scripts/generate_picks_for_rrmodel.py

# Verify output
cat data/nba/ddtd_today_picks.json
```

Expected output structure:
```json
{
  "date": "2025-01-14",
  "generated_at": "2025-01-14T10:00:00Z",
  "model_version": "v3",
  "picks": {
    "dd": [
      {
        "player": "Luka Doncic",
        "model_prob": 0.8542,
        "best_odds": -150,
        "implied_prob": 0.6000,
        "edge": 0.2542,
        "avg_minutes": 35.2,
        "l20_dd_rate": 0.750,
        "game": "DAL @ LAL"
      }
    ],
    "td": []
  },
  "summary": {
    "total_dd": 1,
    "total_td": 0,
    "avg_edge_dd": 0.2542,
    "avg_edge_td": 0
  }
}
```

### Step 3: Commit and Push GitHub Action

```bash
cd /path/to/NBA-DDTD-RESEARCH

git add scripts/generate_picks_for_rrmodel.py
git add .github/workflows/generate-daily-picks.yml
git add data/nba/ddtd_today_picks.json  # If generated
git commit -m "Add daily picks generation for RRMODEL"
git push
```

### Step 4: Test GitHub Action

```bash
# Go to: https://github.com/YOUR_USERNAME/NBA-DDTD-RESEARCH/actions
# Click "Generate Daily NBA DD/TD Picks"
# Click "Run workflow" button
# Select branch: main
# Click "Run workflow"

# Wait for completion, then check:
# - Actions tab shows green checkmark
# - data/nba/ddtd_today_picks.json was updated
```

### Step 5: Copy Files to RRMODEL

```bash
cd /path/to/RRMODEL

# Copy Netlify functions
mkdir -p netlify/functions/_lib
cp /path/to/NBA-DDTD-RESEARCH/RRMODEL-files/netlify/functions/_lib/blobs-nba.mjs netlify/functions/_lib/
cp /path/to/NBA-DDTD-RESEARCH/RRMODEL-files/netlify/functions/nbaddtd-picks.mjs netlify/functions/

# Copy React component
mkdir -p src/components
cp /path/to/NBA-DDTD-RESEARCH/RRMODEL-files/src/components/NBADDTDPicks.jsx src/components/

# Copy model metadata (optional)
mkdir -p data/nba
cp /path/to/NBA-DDTD-RESEARCH/models/nba/ddtd/acceptance_gates_v3.json data/nba/
cp /path/to/NBA-DDTD-RESEARCH/models/nba/ddtd/current_teams.json data/nba/
```

### Step 6: Update RRMODEL Files

**Update `netlify/functions/nbaddtd-picks.mjs`:**

Replace `YOUR_GITHUB_USERNAME` with your actual GitHub username:
```javascript
const PICKS_JSON_URL = 'https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/NBA-DDTD-RESEARCH/main/data/nba/ddtd_today_picks.json';
```

**Update `src/pages/NBA.jsx`:**

Add import at top:
```javascript
import NBADDTDPicks from '../components/NBADDTDPicks';
```

Add component at bottom (before closing div):
```javascript
{/* ... existing NBA content ... */}

{/* NEW: DD/TD Picks */}
<NBADDTDPicks />
```

**Update `package.json`:**

Add dependencies if not present:
```json
{
  "dependencies": {
    "@netlify/blobs": "^7.0.0",
    "@netlify/functions": "^2.0.0"
  }
}
```

### Step 7: Install Dependencies and Deploy

```bash
cd /path/to/RRMODEL

# Install new dependencies
npm install

# Test locally (optional)
netlify dev

# Commit and push
git add .
git commit -m "Add NBA DD/TD picks integration"
git push

# Netlify will auto-deploy
```

### Step 8: Verify Deployment

1. **Check GitHub Action**: https://github.com/YOUR_USERNAME/NBA-DDTD-RESEARCH/actions
   - Should run daily at 10 AM
   - Should commit `data/nba/ddtd_today_picks.json`

2. **Check Netlify Function**: https://your-site.netlify.app/.netlify/functions/nbaddtd-picks
   - Should return JSON with picks
   - Response headers should show `X-Cache: HIT` or `MISS`

3. **Check Frontend**: https://your-site.netlify.app/nba
   - Should display DD/TD picks section at bottom
   - Should show picks table with edge color coding

## Troubleshooting

### GitHub Action Not Running

```bash
# Check workflow file syntax
cat .github/workflows/generate-daily-picks.yml

# Check repository secrets
# Go to: https://github.com/YOUR_USERNAME/NBA-DDTD-RESEARCH/settings/secrets/actions
# Verify ODDS_API_KEY exists

# Manually trigger workflow
# Go to: https://github.com/YOUR_USERNAME/NBA-DDTD-RESEARCH/actions
# Click "Generate Daily NBA DD/TD Picks" → "Run workflow"
```

### Netlify Function Errors

```bash
# Check function logs in Netlify dashboard
# Go to: https://app.netlify.com/sites/YOUR_SITE/functions/nbaddtd-picks

# Common issues:
# 1. GitHub URL incorrect (check YOUR_GITHUB_USERNAME)
# 2. JSON file not committed (check repo)
# 3. Netlify Blobs not enabled (check Netlify dashboard)
```

### Frontend Not Showing Picks

```bash
# Check browser console for errors
# F12 → Console tab

# Check network tab for API calls
# F12 → Network tab → Filter: "nbaddtd-picks"

# Verify component is imported in NBA.jsx
grep -n "NBADDTDPicks" src/pages/NBA.jsx
```

## Daily Operation

Once deployed, the system runs automatically:

1. **10 AM Daily (UTC)**: GitHub Action runs Python script
2. **Script fetches odds** from The Odds API
3. **Model generates predictions** (Gradient Boosting inference)
4. **JSON committed** to `data/nba/ddtd_today_picks.json`
5. **Netlify function** reads JSON on first request
6. **Cached in Blobs** for 24 hours
7. **Frontend displays** picks to users

## Manual Updates

To manually refresh picks:

```bash
# Trigger GitHub Action manually
# Go to: https://github.com/YOUR_USERNAME/NBA-DDTD-RESEARCH/actions
# Click "Generate Daily NBA DD/TD Picks" → "Run workflow"

# Clear Netlify cache (if needed)
# Picks will auto-refresh on next request after cache expires
```

## Cost Considerations

- **Odds API**: ~5-10 requests per run (daily limit: 500)
- **GitHub Actions**: Free for public repos
- **Netlify Functions**: Free tier includes 125k requests/month
- **Netlify Blobs**: Free tier includes 1 GB storage

Estimated monthly cost: **$0** (within free tiers)

## Support

For issues:
1. Check GitHub Action logs
2. Check Netlify function logs
3. Check browser console
4. Verify JSON file exists in repo
5. Verify GitHub secrets are set

## Next Steps

- [ ] Test local Python script
- [ ] Configure GitHub secrets
- [ ] Test GitHub Action
- [ ] Copy files to RRMODEL
- [ ] Update RRMODEL configuration
- [ ] Deploy and verify
