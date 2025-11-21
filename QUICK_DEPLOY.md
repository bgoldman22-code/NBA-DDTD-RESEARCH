# 🚀 Quick Deployment Commands

## Copy-Paste This Entire Section:

```bash
# ============================================
# STEP 1: Navigate to your RRMODEL directory
# ============================================
cd /path/to/your/RRMODEL

# ============================================
# STEP 2: Copy the Netlify function
# ============================================
cp ~/Desktop/REPO33/NBA-DDTD-RESEARCH/RRMODEL-files/netlify/functions/nba-ddtd-picks.mjs netlify/functions/

# ============================================
# STEP 3: Copy the React component
# ============================================
cp ~/Desktop/REPO33/NBA-DDTD-RESEARCH/RRMODEL-files/src/components/NBADDTDPicks.jsx src/components/

# ============================================
# STEP 4: Verify files copied
# ============================================
ls -la netlify/functions/nba-ddtd-picks.mjs
ls -la src/components/NBADDTDPicks.jsx

# ============================================
# STEP 5: Import the component in your NBA page
# ============================================
# Edit src/pages/NBA.jsx (or wherever your NBA page is)
# Add this import at the top:
#   import NBADDTDPicks from '../components/NBADDTDPicks';
# 
# Add the component in your JSX:
#   <NBADDTDPicks />

# ============================================
# STEP 6: Commit and push to GitHub
# ============================================
git add netlify/functions/nba-ddtd-picks.mjs
git add src/components/NBADDTDPicks.jsx
git add src/pages/NBA.jsx  # Or whatever file you modified
git commit -m "Add DD/TD picks component with Kelly sizing"
git push

# ============================================
# Netlify will auto-deploy!
# ============================================
```

---

## Set GitHub Secret (Do this FIRST!)

1. Go to: https://github.com/YOUR_USERNAME/NBA-DDTD-RESEARCH/settings/secrets/actions
2. Click **"New repository secret"**
3. Name: `ODDS_API_KEY`
4. Value: `c5d3fe15e6c5be83b2acd8695cff012b`
5. Click **"Add secret"**

---

## Manual Test of GitHub Action

```bash
# Go to:
# https://github.com/YOUR_USERNAME/NBA-DDTD-RESEARCH/actions
# 
# 1. Click "Generate Daily NBA DD/TD Picks"
# 2. Click "Run workflow" dropdown
# 3. Click green "Run workflow" button
# 4. Wait for green checkmark (takes ~1 minute)
# 5. Check that data/nba/ddtd_today_picks.json was updated
```

---

## Test the Live API Endpoint

```bash
# Replace with your actual domain
curl https://yourdomain.com/.netlify/functions/nba-ddtd-picks | jq

# Should return JSON with:
# - date
# - generated_at
# - model_version
# - bankroll: 4500
# - unit_size: 10
# - recommended_picks (dd/td arrays)
# - high_probability array
```

---

## Quick Verification Checklist

After deployment:

```bash
# ✅ GitHub Secret is set
# ✅ Files copied to RRMODEL
# ✅ Component imported in NBA page
# ✅ Changes committed and pushed
# ✅ Netlify build succeeded
# ✅ Live site loads component
# ✅ Both tabs work (Recommended + High Prob)
# ✅ Data displays correctly
# ✅ No console errors
# ✅ GitHub Action runs daily at 10 AM ET
```

---

## If You Need to Update Picks Manually

```bash
cd ~/Desktop/REPO33/NBA-DDTD-RESEARCH
export ODDS_API_KEY=c5d3fe15e6c5be83b2acd8695cff012b
python scripts/generate_picks_for_rrmodel_v2.py
git add data/nba/ddtd_today_picks.json
git commit -m "🤖 Manual picks update"
git push
```

---

## Troubleshooting Quick Fixes

### Component not showing?
```bash
# Check browser console (F12)
# Look for fetch errors or CORS issues
# Verify Netlify function deployed:
netlify functions:list
```

### Picks not updating?
```bash
# Check GitHub Actions tab
# Manually trigger the workflow
# Verify ODDS_API_KEY secret exists
```

### Old cached data?
```bash
# Cache expires after 24 hours
# Or clear Netlify Blobs cache manually
# Hard refresh browser: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
```

---

## 📁 Files Summary

**Created in NBA-DDTD-RESEARCH:**
- ✅ `RRMODEL-files/netlify/functions/nba-ddtd-picks.mjs` (Serverless API)
- ✅ `RRMODEL-files/src/components/NBADDTDPicks.jsx` (React UI)
- ✅ `DEPLOYMENT_GUIDE.md` (Full documentation)
- ✅ `DEPLOYMENT_SUMMARY.md` (Quick overview)
- ✅ `.github/workflows/generate-daily-picks.yml` (Updated to use v2)

**To Copy to RRMODEL:**
- → `netlify/functions/nba-ddtd-picks.mjs`
- → `src/components/NBADDTDPicks.jsx`

**To Edit in RRMODEL:**
- → `src/pages/NBA.jsx` (or your NBA page - import and add component)

---

## 🎯 End Result

When live, your users will see:

**Tab 1: Recommended Picks**
```
Player              | Model % | Odds      | Bookmaker | Edge   | Units  | Bet $
--------------------------------------------------------------------------------
Rudy Gobert        | 99.0%   | +135      | FanDuel   | 57.3%  | 22.5U  | $225
Julius Randle      | 40.7%   | +260      | BetMGM    | 12.8%  | 20.2U  | $202
Alperen Sengun (TD)| 45.5%   | +550      | BetMGM    | 29.6%  | 22.5U  | $225
```

**Tab 2: All >35% Probability**
```
Player              | Model % | Odds      | Bookmaker | Edge   | L20 Stats
---------------------------------------------------------------------------
Nikola Jokić       | 37.7%   | +125      | FanDuel   | 7.8%   | 22.5p/12.8r/9.4a
Josh Giddey        | 41.1%   | +225      | BetMGM    | 10.4%  | 15.2p/9.1r/6.3a
...and 5 more
```

---

**Ready to deploy? Follow the commands above! 🚀**
