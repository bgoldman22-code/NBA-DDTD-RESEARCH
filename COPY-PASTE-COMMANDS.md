# Copy-Paste Commands for Deployment

## Prerequisites
- NBA-DDTD-RESEARCH repo must be PUBLIC (or configure GitHub token)
- ODDS_API_KEY available
- Both repos cloned locally

---

## Step 1: Test Python Script

```bash
# Terminal 1: Test in NBA-DDTD-RESEARCH
cd ~/Desktop/REPO33/NBA-DDTD-RESEARCH
export ODDS_API_KEY="your-actual-api-key-here"
python scripts/generate_picks_for_rrmodel.py

# Verify output
cat data/nba/ddtd_today_picks.json | python -m json.tool
```

**Expected output**: JSON with today's date, picks arrays, summary

---

## Step 2: Configure GitHub Secret

```bash
# Open in browser:
echo "https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/settings/secrets/actions"

# Click "New repository secret"
# Name: ODDS_API_KEY
# Value: <paste your API key>
# Click "Add secret"
```

---

## Step 3: Commit NBA-DDTD-RESEARCH Changes

```bash
cd ~/Desktop/REPO33/NBA-DDTD-RESEARCH

# Add all new files
git add scripts/generate_picks_for_rrmodel.py
git add .github/workflows/generate-daily-picks.yml
git add data/nba/ddtd_today_picks.json
git add RRMODEL-files/
git add RRMODEL-INTEGRATION-GUIDE.md
git add QUICK-REFERENCE.md
git add PRE-DEPLOYMENT-CHECKLIST.md

# Commit
git commit -m "Add hybrid DD/TD integration for RRMODEL

- Python script generates daily picks JSON
- GitHub Action runs at 10 AM ET (3 PM UTC)
- RRMODEL files ready to copy
- Complete documentation included"

# Push
git push origin main
```

---

## Step 4: Test GitHub Action

```bash
# Open in browser:
echo "https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/actions"

# Click "Generate Daily NBA DD/TD Picks"
# Click "Run workflow" button
# Select branch: main
# Click "Run workflow"
# Wait for green checkmark (~1-2 minutes)
```

---

## Step 5: Copy Files to RRMODEL

```bash
cd ~/Desktop/REPO33/RRMODEL

# Create directories if needed
mkdir -p netlify/functions/_lib
mkdir -p src/components

# Copy files
cp ~/Desktop/REPO33/NBA-DDTD-RESEARCH/RRMODEL-files/netlify/functions/_lib/blobs-nba.mjs netlify/functions/_lib/
cp ~/Desktop/REPO33/NBA-DDTD-RESEARCH/RRMODEL-files/netlify/functions/nbaddtd-picks.mjs netlify/functions/
cp ~/Desktop/REPO33/NBA-DDTD-RESEARCH/RRMODEL-files/src/components/NBADDTDPicks.jsx src/components/

# Verify files copied
ls -la netlify/functions/_lib/blobs-nba.mjs
ls -la netlify/functions/nbaddtd-picks.mjs
ls -la src/components/NBADDTDPicks.jsx
```

---

## Step 6: Update GitHub Username in Netlify Function

```bash
cd ~/Desktop/REPO33/RRMODEL

# Get your GitHub username
GITHUB_USERNAME=$(git config user.name | tr ' ' '-' | tr '[:upper:]' '[:lower:]')
echo "GitHub username: $GITHUB_USERNAME"

# Replace in file (macOS/BSD sed)
sed -i '' "s/YOUR_GITHUB_USERNAME/$GITHUB_USERNAME/g" netlify/functions/nbaddtd-picks.mjs

# Or if on Linux:
# sed -i "s/YOUR_GITHUB_USERNAME/$GITHUB_USERNAME/g" netlify/functions/nbaddtd-picks.mjs

# Verify replacement
grep "raw.githubusercontent.com" netlify/functions/nbaddtd-picks.mjs
```

**Manual alternative**: Open `netlify/functions/nbaddtd-picks.mjs` and replace `YOUR_GITHUB_USERNAME` with your actual username

---

## Step 7: Update NBA.jsx

```bash
cd ~/Desktop/REPO33/RRMODEL

# Backup original (optional)
cp src/pages/NBA.jsx src/pages/NBA.jsx.backup

# Open in editor
code src/pages/NBA.jsx  # or: nano, vim, etc.
```

**Add these lines manually**:

1. At the top (with other imports):
   ```javascript
   import NBADDTDPicks from '../components/NBADDTDPicks';
   ```

2. At the bottom (before the final closing `</div>` or `</>`):
   ```javascript
   {/* NBA DD/TD Picks */}
   <NBADDTDPicks />
   ```

---

## Step 8: Install Dependencies

```bash
cd ~/Desktop/REPO33/RRMODEL

# Install Netlify packages
npm install @netlify/blobs@^7.0.0 @netlify/functions@^2.0.0

# Verify installation
npm list @netlify/blobs @netlify/functions
```

---

## Step 9: Test Locally (Optional)

```bash
cd ~/Desktop/REPO33/RRMODEL

# Start Netlify dev server
netlify dev

# In another terminal, test the function:
curl http://localhost:8888/.netlify/functions/nbaddtd-picks | python -m json.tool

# Open in browser:
open http://localhost:8888/nba
# or: http://localhost:8888 and navigate to NBA page

# Press Ctrl+C to stop dev server when done
```

---

## Step 10: Commit and Deploy RRMODEL

```bash
cd ~/Desktop/REPO33/RRMODEL

# Check what changed
git status

# Add all changes
git add netlify/functions/_lib/blobs-nba.mjs
git add netlify/functions/nbaddtd-picks.mjs
git add src/components/NBADDTDPicks.jsx
git add src/pages/NBA.jsx
git add package.json package-lock.json

# Commit
git commit -m "Add NBA DD/TD picks integration

- Netlify function fetches pre-generated picks from NBA-DDTD-RESEARCH
- Caches in Netlify Blobs (24hr TTL)
- React component displays picks with edge color coding
- Appended to NBA.jsx page"

# Push (triggers Netlify deploy)
git push origin main
```

---

## Step 11: Verify Deployment

### Check Netlify Deploy

```bash
# Open Netlify dashboard
echo "https://app.netlify.com"

# Wait for deploy to finish (~2 minutes)
# Status should show: "Published"
```

### Test Netlify Function

```bash
# Get your site URL from Netlify dashboard, then:
SITE_URL="https://your-site.netlify.app"  # Replace with your actual URL

# Test function
curl "$SITE_URL/.netlify/functions/nbaddtd-picks" | python -m json.tool

# Should return JSON with picks
```

### Test Frontend

```bash
# Open in browser
open "https://your-site.netlify.app/nba"

# Or:
echo "https://your-site.netlify.app/nba"
```

**Check for**:
- "🏀 Double-Double & Triple-Double Picks" section at bottom
- Table with players, odds, edges (if picks available)
- No errors in browser console (F12)

---

## Troubleshooting Quick Fixes

### GitHub Action Failed

```bash
# Check logs
echo "https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/actions"

# Common fix: Re-run workflow
# Go to Actions → Click failed run → Click "Re-run jobs"
```

### Netlify Function 503 Error

```bash
# Verify JSON file exists
GITHUB_USERNAME="your-username"  # Replace
curl "https://raw.githubusercontent.com/$GITHUB_USERNAME/NBA-DDTD-RESEARCH/main/data/nba/ddtd_today_picks.json"

# Should return JSON, not 404
```

### Frontend Not Showing Picks

```bash
# Check if component is imported
cd ~/Desktop/REPO33/RRMODEL
grep -n "NBADDTDPicks" src/pages/NBA.jsx

# Should show:
# [line number]: import NBADDTDPicks from '../components/NBADDTDPicks';
# [line number]: <NBADDTDPicks />
```

### Clear Netlify Cache

```bash
# Option 1: Wait 24 hours for automatic cache expiry

# Option 2: Force refresh by committing to NBA-DDTD-RESEARCH
cd ~/Desktop/REPO33/NBA-DDTD-RESEARCH
git commit --allow-empty -m "Force cache refresh"
git push
```

---

## Daily Operations (Automated)

After deployment, these run automatically:

1. **3:00 PM UTC (10:00 AM ET)**: GitHub Action runs
2. **Script generates picks**: Fetches odds, runs model, applies gates
3. **JSON committed**: `data/nba/ddtd_today_picks.json` updated
4. **First user visit**: Netlify function fetches JSON from GitHub
5. **Cached for 24 hours**: Subsequent visitors get cached picks
6. **Next day**: Repeat

---

## Manual Refresh Commands

### Trigger GitHub Action Manually

```bash
# Option 1: Via browser
echo "https://github.com/$(cd ~/Desktop/REPO33/NBA-DDTD-RESEARCH && git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/actions"
# Click "Generate Daily NBA DD/TD Picks" → "Run workflow"

# Option 2: Via GitHub CLI (if installed)
cd ~/Desktop/REPO33/NBA-DDTD-RESEARCH
gh workflow run generate-daily-picks.yml
```

### Check Odds API Usage

```bash
# Make a test request with your key
ODDS_API_KEY="your-key"
curl "https://api.the-odds-api.com/v4/sports/basketball_nba/events?apiKey=$ODDS_API_KEY" -I | grep "x-requests-remaining"

# Shows: x-requests-remaining: 490 (or similar)
```

---

## Rollback Commands

### Quick Disable (Keep Files)

```bash
cd ~/Desktop/REPO33/RRMODEL

# Comment out component in NBA.jsx
sed -i '' 's/<NBADDTDPicks \/>/<!-- <NBADDTDPicks \/> -->/' src/pages/NBA.jsx

git add src/pages/NBA.jsx
git commit -m "Temporarily disable DD/TD picks"
git push
```

### Full Rollback (Remove Integration)

```bash
cd ~/Desktop/REPO33/RRMODEL

# Remove files
rm netlify/functions/_lib/blobs-nba.mjs
rm netlify/functions/nbaddtd-picks.mjs
rm src/components/NBADDTDPicks.jsx

# Restore NBA.jsx from backup
cp src/pages/NBA.jsx.backup src/pages/NBA.jsx

git add .
git commit -m "Rollback DD/TD integration"
git push
```

---

## Success Verification Checklist

Run these commands to verify everything works:

```bash
# 1. Check GitHub Action ran
cd ~/Desktop/REPO33/NBA-DDTD-RESEARCH
echo "https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/actions"
# → Should show green checkmark

# 2. Check JSON file exists
GITHUB_USERNAME="your-username"  # Replace
curl -I "https://raw.githubusercontent.com/$GITHUB_USERNAME/NBA-DDTD-RESEARCH/main/data/nba/ddtd_today_picks.json"
# → Should return 200 OK, not 404

# 3. Check Netlify function works
SITE_URL="https://your-site.netlify.app"  # Replace
curl "$SITE_URL/.netlify/functions/nbaddtd-picks" -I
# → Should return 200 OK

# 4. Check frontend loads
curl "$SITE_URL/nba" -I
# → Should return 200 OK

# 5. Check picks data
curl "$SITE_URL/.netlify/functions/nbaddtd-picks" | python -m json.tool | head -20
# → Should show: date, generated_at, picks, summary
```

✅ **If all 5 checks pass, deployment is successful!**

---

**File**: `COPY-PASTE-COMMANDS.md`  
**Created**: November 14, 2025  
**Purpose**: Quick deployment reference with copy-paste commands  
**Prerequisites**: NBA-DDTD-RESEARCH public, ODDS_API_KEY available
