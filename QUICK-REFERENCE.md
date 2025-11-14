# NBA DD/TD Integration - Quick Reference

## What Was Built

### Option 3 (Hybrid Architecture)
- **Python** (NBA-DDTD-RESEARCH): Generates picks daily via GitHub Actions
- **JavaScript** (RRMODEL): Serves pre-generated picks (no model inference)

## Files Created

### NBA-DDTD-RESEARCH Repository
```
scripts/
  generate_picks_for_rrmodel.py    ← Picks generator (uses existing run_today.py logic)

.github/workflows/
  generate-daily-picks.yml         ← GitHub Action (runs daily at 10 AM)

data/nba/
  ddtd_today_picks.json            ← Daily picks output (auto-generated)

RRMODEL-files/                     ← Files to copy to RRMODEL
  netlify/functions/
    _lib/
      blobs-nba.mjs                ← Blob cache helper
    nbaddtd-picks.mjs              ← Netlify function (serves picks)
  src/components/
    NBADDTDPicks.jsx               ← React component

RRMODEL-INTEGRATION-GUIDE.md      ← Full installation guide
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. GitHub Action (Daily 10 AM)                                  │
│    └─> Runs scripts/generate_picks_for_rrmodel.py              │
│        └─> Fetches odds from The Odds API                       │
│        └─> Loads 200-tree Gradient Boosting model               │
│        └─> Generates predictions with calibration               │
│        └─> Applies acceptance gates (positive edge only)        │
│        └─> Exports to data/nba/ddtd_today_picks.json           │
│        └─> Commits and pushes to repo                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. RRMODEL Netlify Function                                     │
│    └─> User visits website → Fetches /.netlify/functions/...   │
│        └─> Checks Netlify Blobs cache (24hr TTL)               │
│            └─> Cache HIT: Return cached picks                   │
│            └─> Cache MISS: Fetch from GitHub raw URL            │
│                └─> Cache for 24 hours                           │
│                └─> Return picks                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. React Frontend Component                                     │
│    └─> Displays picks in table                                 │
│        └─> Color-coded edge values (green = best)              │
│        └─> Shows: Player, Game, Model Prob, Odds, Edge         │
└─────────────────────────────────────────────────────────────────┘
```

## JSON Schema

**data/nba/ddtd_today_picks.json:**
```json
{
  "date": "2025-01-14",
  "generated_at": "2025-01-14T10:00:00Z",
  "model_version": "v3",
  "picks": {
    "dd": [
      {
        "player": "Luka Doncic",
        "model_prob": 0.8542,       // Model probability (0-1)
        "best_odds": -150,           // American odds
        "implied_prob": 0.6000,      // Odds-implied probability
        "edge": 0.2542,              // model_prob - implied_prob
        "avg_minutes": 35.2,         // L20 average minutes
        "l20_dd_rate": 0.750,        // L20 DD rate
        "game": "DAL @ LAL"          // Matchup
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

## Manual Commands

### Test Python Script Locally
```bash
export ODDS_API_KEY="your-key-here"
cd /path/to/NBA-DDTD-RESEARCH
python scripts/generate_picks_for_rrmodel.py
cat data/nba/ddtd_today_picks.json
```

### Trigger GitHub Action Manually
1. Go to: https://github.com/YOUR_USERNAME/NBA-DDTD-RESEARCH/actions
2. Click "Generate Daily NBA DD/TD Picks"
3. Click "Run workflow"

### Test Netlify Function Locally
```bash
cd /path/to/RRMODEL
netlify dev
# Visit: http://localhost:8888/.netlify/functions/nbaddtd-picks
```

### Deploy RRMODEL
```bash
cd /path/to/RRMODEL
npm install
git add .
git commit -m "Add NBA DD/TD picks integration"
git push  # Netlify auto-deploys
```

## Configuration Checklist

### NBA-DDTD-RESEARCH
- [ ] **Repo is PUBLIC** (or use GitHub token for private)
- [ ] GitHub Secret `ODDS_API_KEY` set
- [ ] Python script tested locally
- [ ] GitHub Action workflow committed
- [ ] Initial JSON file generated
- [ ] **Timezone verified**: 3 PM UTC = 10 AM ET

### RRMODEL
- [ ] Files copied from `RRMODEL-files/`
- [ ] GitHub username updated in `nbaddtd-picks.mjs`
- [ ] `NBADDTDPicks` component imported in `NBA.jsx`
- [ ] Dependencies installed (`@netlify/blobs`, `@netlify/functions`)
- [ ] Deployed to Netlify

## Acceptance Gates (Model V3)

**Double-Double:**
- Model Prob: ≥15%
- Minutes: ≥30
- Elite Exception: ≥90% prob, ≥29 min
- **Positive edge required**

**Triple-Double:**
- Model Prob: ≥8%
- Minutes: ≥35
- Elite Exception: ≥80% prob, ≥33 min
- **Positive edge required**

## Edge Color Coding

- **≥30%**: Green (Excellent)
- **≥20%**: Light Green (Good)
- **≥10%**: Lime (Decent)
- **<10%**: Yellow (Marginal)

## API Usage

**The Odds API:**
- ~5-10 requests per run
- Daily run = 10 requests
- Free tier: 500 requests/month
- Sufficient for daily operation

## Monitoring

**GitHub Actions:**
- https://github.com/YOUR_USERNAME/NBA-DDTD-RESEARCH/actions
- Should show green checkmark
- Check logs for errors

**Netlify Functions:**
- https://app.netlify.com/sites/YOUR_SITE/functions/nbaddtd-picks
- Check invocation logs
- Response time should be <500ms (cached)

**Frontend:**
- Browser Console (F12)
- Network tab for API calls
- Should see picks table with color-coded edges

## Troubleshooting

| Issue | Solution |
|-------|----------|
| GitHub Action fails | Check `ODDS_API_KEY` secret is set |
| No picks generated | Check Odds API remaining requests |
| Netlify function 503 | Check JSON file exists in GitHub repo |
| Frontend doesn't load | Check browser console, verify import in NBA.jsx |
| Cache not working | Check Netlify Blobs is enabled |

## Cost Estimate

| Service | Usage | Cost |
|---------|-------|------|
| Odds API | 10 req/day | $0 (free tier) |
| GitHub Actions | 1 run/day | $0 (public repo) |
| Netlify Functions | ~100 req/day | $0 (free tier) |
| Netlify Blobs | <1 MB | $0 (free tier) |
| **Total** | | **$0/month** |

## Support

**Common Issues:**
1. Check GitHub Action logs first
2. Verify JSON file exists in repo
3. Check Netlify function logs
4. Clear browser cache
5. Verify all files copied correctly

**Documentation:**
- Full guide: `RRMODEL-INTEGRATION-GUIDE.md`
- Integration plan: (original 1598-line document)
- Model inspection: Run `python -c "import joblib; ..."`

---

**Created:** January 2025
**Model Version:** v3 (Gradient Boosting, 200 trees)
**Architecture:** Hybrid (Python generation + JS serving)
