# Pre-Deployment Checklist

## ⚠️ CRITICAL: Read This Before Deploying

### Repository Visibility

**NBA-DDTD-RESEARCH must be PUBLIC** for the Netlify function to fetch the JSON file via raw GitHub URL.

If you want to keep NBA-DDTD-RESEARCH private:
- **Option A**: Use a GitHub Personal Access Token in the Netlify function
- **Option B**: Have the GitHub Action push JSON directly to RRMODEL repo instead
- **Option C**: Have the GitHub Action push JSON directly to Netlify Blobs (requires NETLIFY_AUTH_TOKEN)

**Current implementation assumes PUBLIC repo.** If private, you'll need to modify the approach.

---

## Pre-Deployment Checklist

### NBA-DDTD-RESEARCH Repository

- [ ] **Repo is public** (or chosen alternative approach above)
- [ ] **GitHub Secret configured**: `ODDS_API_KEY`
  - Go to: `https://github.com/YOUR_USERNAME/NBA-DDTD-RESEARCH/settings/secrets/actions`
  - Add secret: `ODDS_API_KEY` = your Odds API key
- [ ] **Python script tested locally**:
  ```bash
  export ODDS_API_KEY="your-key-here"
  python scripts/generate_picks_for_rrmodel.py
  # Should create: data/nba/ddtd_today_picks.json
  ```
- [ ] **Validate JSON output**:
  ```bash
  cat data/nba/ddtd_today_picks.json | python -m json.tool
  # Should have: date, generated_at, picks.dd, picks.td, summary
  ```
- [ ] **Files committed and pushed**:
  - `scripts/generate_picks_for_rrmodel.py`
  - `.github/workflows/generate-daily-picks.yml`
  - `data/nba/ddtd_today_picks.json` (initial version)
- [ ] **GitHub Action tested manually**:
  - Go to: Actions tab → "Generate Daily NBA DD/TD Picks" → "Run workflow"
  - Verify: Green checkmark, JSON file updated

### RRMODEL Repository

- [ ] **Files copied from NBA-DDTD-RESEARCH/RRMODEL-files/**:
  ```bash
  # From RRMODEL root:
  cp ../NBA-DDTD-RESEARCH/RRMODEL-files/netlify/functions/_lib/blobs-nba.mjs netlify/functions/_lib/
  cp ../NBA-DDTD-RESEARCH/RRMODEL-files/netlify/functions/nbaddtd-picks.mjs netlify/functions/
  cp ../NBA-DDTD-RESEARCH/RRMODEL-files/src/components/NBADDTDPicks.jsx src/components/
  ```

- [ ] **GitHub username updated in `nbaddtd-picks.mjs`**:
  ```javascript
  // Line 7: Replace YOUR_GITHUB_USERNAME
  const PICKS_JSON_URL = 'https://raw.githubusercontent.com/YOUR_ACTUAL_USERNAME/NBA-DDTD-RESEARCH/main/data/nba/ddtd_today_picks.json';
  ```

- [ ] **Component imported in `src/pages/NBA.jsx`**:
  ```javascript
  // At top of file:
  import NBADDTDPicks from '../components/NBADDTDPicks';
  
  // At bottom (before closing </div>):
  <NBADDTDPicks />
  ```

- [ ] **Dependencies installed**:
  ```bash
  npm install @netlify/blobs @netlify/functions
  ```

- [ ] **Verify package.json has**:
  ```json
  {
    "dependencies": {
      "@netlify/blobs": "^7.0.0",
      "@netlify/functions": "^2.0.0"
    }
  }
  ```

- [ ] **Local test (optional but recommended)**:
  ```bash
  netlify dev
  # Visit: http://localhost:8888/.netlify/functions/nbaddtd-picks
  # Should return JSON with picks
  ```

- [ ] **All changes committed and pushed**

---

## Deployment Verification

### After Pushing to GitHub

1. **Verify GitHub Action runs**:
   - URL: `https://github.com/YOUR_USERNAME/NBA-DDTD-RESEARCH/actions`
   - Should see: Green checkmark on latest workflow run
   - Should see: Commit with message "Update daily DD/TD picks [automated]"

2. **Verify JSON file exists**:
   - URL: `https://raw.githubusercontent.com/YOUR_USERNAME/NBA-DDTD-RESEARCH/main/data/nba/ddtd_today_picks.json`
   - Should return: Valid JSON (not 404)

3. **Verify Netlify function deployed**:
   - URL: `https://your-site.netlify.app/.netlify/functions/nbaddtd-picks`
   - Should return: JSON with picks
   - Headers should include: `X-Cache: MISS` (first time), then `X-Cache: HIT`

4. **Verify frontend displays picks**:
   - URL: `https://your-site.netlify.app/nba`
   - Should see: "🏀 Double-Double & Triple-Double Picks" section at bottom
   - Should see: Table with players, odds, edges (if picks available)
   - Should see: "No picks available for today" (if empty)

5. **Check browser console (F12)**:
   - Should see: No errors
   - Network tab should show: Successful fetch to `nbaddtd-picks` function

---

## Timezone Configuration

The GitHub Action is set to run at **3:00 PM UTC** = **10:00 AM Eastern Time**.

```yaml
# .github/workflows/generate-daily-picks.yml, line 4:
- cron: '0 15 * * *'  # 3 PM UTC = 10 AM ET
```

**Why 10 AM ET?**
- Gives time for odds to settle before games (typically 7-10 PM ET)
- Avoids running during peak GitHub Actions load (midnight UTC)
- Can manually trigger earlier if needed via "Run workflow" button

**Adjust if needed:**
- 9 AM ET: `0 14 * * *`
- 11 AM ET: `0 16 * * *`
- Noon ET: `0 17 * * *`

**Note**: During Daylight Saving Time transitions, UTC offset changes. GitHub Actions use UTC exclusively.

---

## Edge Cases to Test

### No Picks Day
- **What happens**: Model finds no qualifying picks
- **Expected**: JSON with empty arrays: `{ "picks": { "dd": [], "td": [] } }`
- **Frontend shows**: "No picks available for today"
- **Test**: Run script on a day with no games (e.g., All-Star break)

### Odds API Limit Reached
- **What happens**: API returns 429 Too Many Requests
- **Expected**: Script writes empty picks JSON with error message
- **Frontend shows**: "No picks available for today"
- **Check**: GitHub Action logs show API error

### GitHub Raw URL 404
- **What happens**: JSON file doesn't exist or repo is private
- **Expected**: Netlify function returns 503 Service Unavailable
- **Frontend shows**: "Error: Unable to fetch picks from source"
- **Fix**: Verify repo is public, JSON file exists

### Netlify Blobs Cache Miss
- **What happens**: Cache expired (24hr TTL)
- **Expected**: Function fetches from GitHub, caches again
- **Response header**: `X-Cache: MISS`
- **Next request**: `X-Cache: HIT`

---

## Rollback Plan

If something breaks after deployment:

### Quick Fix (Disable Feature)
```javascript
// In RRMODEL src/pages/NBA.jsx:
// Comment out the component:
{/* <NBADDTDPicks /> */}

// Commit and push
git add src/pages/NBA.jsx
git commit -m "Temporarily disable DD/TD picks"
git push
```

### Full Rollback (Remove Integration)
```bash
cd RRMODEL

# Remove files
rm netlify/functions/_lib/blobs-nba.mjs
rm netlify/functions/nbaddtd-picks.mjs
rm src/components/NBADDTDPicks.jsx

# Revert NBA.jsx changes
git checkout HEAD~1 -- src/pages/NBA.jsx

# Uninstall dependencies (optional)
npm uninstall @netlify/blobs @netlify/functions

# Commit
git add .
git commit -m "Rollback DD/TD integration"
git push
```

### Pause GitHub Action
```bash
# In NBA-DDTD-RESEARCH:
# Edit .github/workflows/generate-daily-picks.yml
# Change line 4:
# - cron: '0 15 * * *'
# To:
# - cron: '0 15 31 2 *'  # Never runs (Feb 31 doesn't exist)

git add .github/workflows/generate-daily-picks.yml
git commit -m "Pause daily picks generation"
git push
```

---

## Monitoring & Maintenance

### Daily Checks (First Week)
- [ ] GitHub Action ran successfully (green checkmark)
- [ ] JSON file updated with today's date
- [ ] Netlify function returns picks
- [ ] Frontend displays correctly
- [ ] No errors in browser console

### Weekly Checks (Ongoing)
- [ ] Odds API usage within limits (check API dashboard)
- [ ] GitHub Action success rate >95%
- [ ] Netlify function errors <1%

### Monthly Checks
- [ ] Review picks performance (if tracking results)
- [ ] Update model if needed (new .pkl file)
- [ ] Update acceptance gates if needed (new .json file)

---

## Support & Debugging

### GitHub Action Fails

**Check logs**:
```bash
# Go to: https://github.com/YOUR_USERNAME/NBA-DDTD-RESEARCH/actions
# Click on failed workflow run
# Click on "generate-picks" job
# Read error messages
```

**Common issues**:
- `ODDS_API_KEY` not set → Add to repo secrets
- API rate limit exceeded → Wait for reset or increase limit
- Python dependency missing → Update workflow to install it

### Netlify Function Fails

**Check logs**:
```bash
# Go to: https://app.netlify.com/sites/YOUR_SITE/functions/nbaddtd-picks
# Click on invocation
# Read error message and stack trace
```

**Common issues**:
- GitHub URL 404 → Verify repo is public, file exists
- Blobs error → Verify Netlify Blobs is enabled
- JSON parse error → Verify JSON file is valid

### Frontend Not Showing

**Check browser console (F12)**:
- Fetch error → Netlify function issue
- Component error → React syntax error
- Import error → File path incorrect

**Check network tab (F12)**:
- Request to `nbaddtd-picks` failing? → Backend issue
- Request succeeds but empty? → No picks available (expected)

---

## Final Pre-Deploy Commands

### NBA-DDTD-RESEARCH
```bash
cd /path/to/NBA-DDTD-RESEARCH

# Test script locally
export ODDS_API_KEY="your-key-here"
python scripts/generate_picks_for_rrmodel.py

# Verify JSON output
cat data/nba/ddtd_today_picks.json | python -m json.tool

# Commit and push
git add scripts/ .github/ data/ *.md
git commit -m "Add daily DD/TD picks generation for RRMODEL"
git push

# Verify GitHub Action
# Go to: https://github.com/YOUR_USERNAME/NBA-DDTD-RESEARCH/actions
# Click "Generate Daily NBA DD/TD Picks" → "Run workflow"
# Wait for green checkmark
```

### RRMODEL
```bash
cd /path/to/RRMODEL

# Copy files
cp ../NBA-DDTD-RESEARCH/RRMODEL-files/netlify/functions/_lib/blobs-nba.mjs netlify/functions/_lib/
cp ../NBA-DDTD-RESEARCH/RRMODEL-files/netlify/functions/nbaddtd-picks.mjs netlify/functions/
cp ../NBA-DDTD-RESEARCH/RRMODEL-files/src/components/NBADDTDPicks.jsx src/components/

# Update GitHub username in nbaddtd-picks.mjs
# Update NBA.jsx to import and use component

# Install dependencies
npm install @netlify/blobs @netlify/functions

# Test locally (optional)
netlify dev
# Visit: http://localhost:8888/.netlify/functions/nbaddtd-picks

# Commit and push
git add .
git commit -m "Add NBA DD/TD picks integration"
git push

# Verify deployment
# Wait ~2 minutes for Netlify to deploy
# Visit: https://your-site.netlify.app/nba
# Check: DD/TD picks section appears
```

---

## Success Criteria

✅ **Ready for production** when ALL of these are true:

1. GitHub Action runs successfully (green checkmark)
2. JSON file exists and is valid at raw GitHub URL
3. Netlify function returns JSON at `/.netlify/functions/nbaddtd-picks`
4. Frontend displays picks section on `/nba` page
5. No errors in browser console
6. Cache headers present (`X-Cache: HIT` or `MISS`)
7. Empty picks handled gracefully ("No picks available")
8. Manual workflow trigger works (Actions → Run workflow)

---

**Last Updated**: November 14, 2025
**Architecture**: Hybrid (Python generation + JS serving)
**Timezone**: 3:00 PM UTC = 10:00 AM ET
