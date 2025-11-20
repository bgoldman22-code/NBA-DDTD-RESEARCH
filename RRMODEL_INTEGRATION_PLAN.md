# NBA DD/TD Model Integration Plan - V2
## Connecting NBA-DDTD-RESEARCH → RRMODEL (Production Ready)

**Target:** https://github.com/bgoldman22-code/RRMODEL.git (Netlify deployed)  
**Source:** Local NBA-DDTD-RESEARCH model  
**Goal:** Display today's DD/TD picks in RRMODEL frontend without breaking existing features

**Strategy:** JavaScript-first, match existing RRMODEL patterns, append to NBA page (don't rewrite)

---

## Phase 1: Repository Audit & Architecture Analysis

### Current RRMODEL Structure (Verified):
```
RRMODEL/
├── netlify/
│   └── functions/
│       ├── _lib/                  # Shared function utilities
│       │   ├── blobs-nfl.js      # Blob helpers (NFL pattern to mirror)
│       │   ├── blobs-mlb.js
│       │   └── odds.mjs          # Existing Odds API helper (if present)
│       ├── nfl-picks.mjs
│       ├── mlb-picks.mjs
│       └── nbaddtd-picks.mjs     # ✅ NEW - DD/TD function
├── src/
│   ├── pages/
│   │   ├── NBA.jsx               # EXISTING - DO NOT REPLACE, APPEND TO
│   │   ├── NFL.jsx
│   │   └── NHL.jsx
│   ├── components/
│   └── App.jsx                   # Main router
├── models/
│   └── nba/
│       └── ddtd/                 # ✅ NEW - DD/TD model files
│           ├── model_params_v3.json
│           ├── acceptance_gates_v3.json
│           └── current_teams.json
├── data/
│   └── nba/
│       └── ddtd_l20_cache.json   # ✅ NEW - L20 stats cache
└── public/
```

### Existing NBA Features to Preserve:
- `src/pages/NBA.jsx` - **CRITICAL: DO NOT REPLACE OR REWRITE**
  - Append `<NBADDTDPicks />` component to existing layout
  - Match existing card/table styling
  - Keep all existing NBA props/RCI/projections intact

### New NBADDTD Namespace:
- **Function**: `netlify/functions/nbaddtd-picks.mjs` (Node/JavaScript)
- **Helpers**: `netlify/functions/_lib/blobs-nba.mjs` (mirror blobs-nfl.js pattern)
- **Model**: `models/nba/ddtd/` (JSON format, not .pkl)
- **Cache**: `data/nba/ddtd_l20_cache.json` (daily refresh via GitHub Action)
- **Frontend**: `<NBADDTDPicks />` component appended to NBA.jsx
- **Endpoint**: `/.netlify/functions/nbaddtd-picks`

### Key Technologies in Use:
- **Frontend**: React (Vite build)
- **Backend**: Netlify Functions (Node.js/JavaScript only - no Python)
- **Deployment**: Netlify (auto-deploy from GitHub)
- **Data Storage**: Netlify Blobs (via blobs-nba.mjs helper)
- **APIs**: The Odds API (via existing odds helper or new odds-nba.mjs)

---

## Phase 2: Model Packaging for Deployment

### Critical Decision: JavaScript Implementation (Not Python)

**Why JavaScript:**
- ✅ Matches all existing RRMODEL functions (NFL, MLB, NHL)
- ✅ Faster cold starts (no Python runtime overhead)
- ✅ Reuse existing blob/odds helpers
- ✅ No scikit-learn packaging complexity
- ✅ Simpler deployment (same runtime as everything else)

**Implementation Strategy:**
Convert the trained model to JavaScript-compatible format:
1. Extract model parameters (coefficients, thresholds) from .pkl
2. Export as JSON with decision logic
3. Implement feature calculation in JavaScript
4. Replicate gate logic and calibration in JS

### Files to Port from NBA-DDTD-RESEARCH:

#### 1. **Model Parameters** (Convert .pkl → JSON):
```json
// models/nba/ddtd/model_params_v3.json
{
  "version": "v3",
  "dd_model": {
    "type": "xgboost",
    "feature_importance": { ... },
    "trees": [ ... ],  // or simplified decision logic
    "calibration_curve": [ ... ]
  },
  "td_model": { ... },
  "feature_names": [
    "avg_minutes", "avg_points", "avg_rebounds", ...
  ]
}
```

#### 2. **Acceptance Gates** (Already JSON):
```json
// models/nba/ddtd/acceptance_gates_v3.json
{
  "dd": {
    "min_prob": 0.15,
    "min_minutes": 30,
    "elite_prob": 0.90,
    "elite_minutes": 29,
    "expected_edge": 0.346
  },
  "td": { ... }
}
```

#### 3. **Current Teams Mapping** (Already JSON):
```json
// models/nba/ddtd/current_teams.json
{
  "Domantas Sabonis": "SAC",
  "Karl-Anthony Towns": "NY",
  ...
}
```

#### 4. **L20 Stats Cache** (Generated daily):
```json
// data/nba/ddtd_l20_cache.json
{
  "last_updated": "2025-11-14T14:00:00Z",
  "players": {
    "Domantas Sabonis": {
      "dd_rate_l20": 0.75,
      "td_rate_l20": 0.15,
      "avg_minutes_l20": 31.1,
      "avg_points_l20": 14.9,
      "avg_rebounds_l20": 12.3,
      "avg_assists_l20": 8.2,
      "games_played_l20": 20
    },
    ...
  }
}
```

### JavaScript Dependencies (package.json):
```json
{
  "dependencies": {
    "@netlify/functions": "^2.0.0",
    "@netlify/blobs": "^6.2.0"
  }
}
```

**Notes:**
- No `node-fetch` needed - Netlify Functions v2+ has global `fetch`
- No Python dependencies needed!
- If you already have these packages, no changes required

---

## Phase 3: Netlify Function Design (JavaScript Implementation)

### Function Architecture (RRMODEL-Conformant):

```
netlify/functions/
├── nbaddtd-picks.mjs              # Main function (Node/ESM)
└── _lib/
    ├── blobs-nba.mjs              # NEW: NBA blob helper (mirror blobs-nfl.js)
    ├── odds-nba.mjs               # NEW: NBA odds helper (or reuse existing odds.mjs)
    └── ddtd-predictor.mjs         # NEW: Core prediction logic
```

### Function Naming Convention:
- **File**: `netlify/functions/nbaddtd-picks.mjs`
- **Endpoint**: `/.netlify/functions/nbaddtd-picks`
- **Cache Key**: `nbaddtd-picks-{YYYY-MM-DD}`
- **Environment Vars**: `NBADDTD_*` prefix (plus shared `ODDS_API_KEY`)

### Shared Helpers (Match Existing Patterns):

#### blobs-nba.mjs (Mirror blobs-nfl.js pattern):
```javascript
// netlify/functions/_lib/blobs-nba.mjs
import { getStore } from '@netlify/blobs';

// IMPORTANT: Use 'nba-ddtd' store name consistently across all DD/TD functions
const store = getStore('nba-ddtd');

export async function getJson(key) {
  try {
    const data = await store.get(key);
    return data ? JSON.parse(data) : null;
  } catch {
    return null;
  }
}

export async function setJson(key, value, ttlSeconds = 86400) {
  await store.setJSON(key, value, {
    ttl: ttlSeconds
  });
}

export async function exists(key) {
  const metadata = await store.getMetadata(key);
  return metadata !== null;
}
```

#### odds-nba.mjs (Use existing odds helper or create):
```javascript
// netlify/functions/_lib/odds-nba.mjs
// If odds.mjs exists, reuse it. Otherwise:
// Note: Using global fetch (available in Netlify Functions v2+)

export async function fetchNBADDTDOdds(apiKey) {
  const BASE_URL = 'https://api.the-odds-api.com/v4';
  
  // IMPORTANT: Verify these market keys match what The Odds API actually returns
  // for NBA DD/TD props. Adjust if needed based on their API documentation.
  const MARKETS = 'player_double_double,player_triple_double';
  
  // Fetch NBA events
  const eventsRes = await fetch(
    `${BASE_URL}/sports/basketball_nba/events?apiKey=${apiKey}`
  );
  const events = await eventsRes.json();
  
  // Fetch DD/TD props for each event
  const allProps = [];
  for (const event of events) {
    const propsRes = await fetch(
      `${BASE_URL}/sports/basketball_nba/events/${event.id}/odds?` +
      `apiKey=${apiKey}&regions=us&markets=${MARKETS}`
    );
    const propsData = await propsRes.json();
    
    // Parse bookmaker odds
    for (const bookmaker of propsData.bookmakers || []) {
      for (const market of bookmaker.markets || []) {
        for (const outcome of market.outcomes || []) {
          allProps.push({
            player: outcome.description,
            type: market.key === 'player_double_double' ? 'DD' : 'TD',
            odds: outcome.price,
            bookmaker: bookmaker.title
          });
        }
      }
    }
  }
  
  // Return best odds per player/type
  return getBestOdds(allProps);
}

function getBestOdds(props) {
  const best = {};
  for (const prop of props) {
    const key = `${prop.player}-${prop.type}`;
    if (!best[key] || prop.odds > best[key].odds) {
      best[key] = prop;
    }
  }
  return Object.values(best);
}
```

### Main Function Implementation:

```javascript
// netlify/functions/nbaddtd-picks.mjs
import { getJson, setJson } from './_lib/blobs-nba.mjs';
import { fetchNBADDTDOdds } from './_lib/odds-nba.mjs';
import { generatePredictions } from './_lib/ddtd-predictor.mjs';

export async function handler(event, context) {
  const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
  const cacheKey = `picks-${today}`;
  
  try {
    // 1. Check cache
    const cached = await getJson(cacheKey);
    if (cached) {
      console.log('✅ Returning cached picks');
      return {
        statusCode: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cached)
      };
    }
    
    // 2. Fetch fresh odds
    console.log('📡 Fetching fresh odds from The Odds API');
    const apiKey = process.env.ODDS_API_KEY || process.env.NBADDTD_ODDS_API_KEY;
    if (!apiKey) throw new Error('ODDS_API_KEY not configured');
    
    const odds = await fetchNBADDTDOdds(apiKey);
    
    // 3. Generate predictions
    console.log('🤖 Generating DD/TD predictions');
    const picks = await generatePredictions(odds, today);
    
    // 4. Cache for 24 hours
    await setJson(cacheKey, picks, 86400);
    
    // 5. Return
    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(picks)
    };
    
  } catch (error) {
    console.error('❌ Error generating picks:', error);
    
    // Fallback: try yesterday's cached picks
    const yesterday = new Date(Date.now() - 86400000).toISOString().split('T')[0];
    const fallback = await getJson(`picks-${yesterday}`);
    
    if (fallback) {
      console.warn('⚠️  Returning yesterday\'s picks as fallback');
      return {
        statusCode: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...fallback,
          warning: 'Using cached data due to API error'
        })
      };
    }
    
    return {
      statusCode: 500,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        error: 'Failed to generate picks',
        message: error.message
      })
    };
  }
}
```

### Core Prediction Logic (ddtd-predictor.mjs):

```javascript
// netlify/functions/_lib/ddtd-predictor.mjs

// IMPORTANT: If ESM JSON imports cause build issues, use fs.readFileSync instead:
// import { readFileSync } from 'fs';
// import { fileURLToPath } from 'url';
// const modelParams = JSON.parse(readFileSync('./models/nba/ddtd/model_params_v3.json', 'utf8'));

import modelParams from '../../../models/nba/ddtd/model_params_v3.json' assert { type: 'json' };
import gates from '../../../models/nba/ddtd/acceptance_gates_v3.json' assert { type: 'json' };
import currentTeams from '../../../models/nba/ddtd/current_teams.json' assert { type: 'json' };
import l20Cache from '../../../data/nba/ddtd_l20_cache.json' assert { type: 'json' };

export async function generatePredictions(odds, date) {
  const predictions = [];
  
  for (const prop of odds) {
    // Get player L20 stats
    const l20 = l20Cache.players[prop.player];
    if (!l20 || l20.games_played_l20 < 10) continue;
    
    // Calculate model probability
    const ddProb = calculateDDProbability(l20, modelParams);
    const tdProb = calculateTDProbability(l20, modelParams);
    
    // Check acceptance gates (standard + elite exception)
    const passesDD = checkGates(ddProb, l20.avg_minutes_l20, gates.dd);
    const passesTD = checkGates(tdProb, l20.avg_minutes_l20, gates.td);
    
    if (prop.type === 'DD' && passesDD) {
      const impliedProb = oddsToProb(prop.odds);
      const edge = ddProb - impliedProb;
      
      if (edge > 0) {
        predictions.push({
          player: prop.player,
          team: currentTeams[prop.player] || '?',
          type: 'DD',
          model_prob: ddProb,
          best_odds: prop.odds,
          implied_prob: impliedProb,
          edge: edge,
          l20_dd_rate: l20.dd_rate_l20,
          avg_minutes: l20.avg_minutes_l20,
          is_elite_exception: isEliteException(ddProb, l20.avg_minutes_l20, gates.dd)
        });
      }
    }
    
    // Same for TD...
  }
  
  return {
    date,
    generated_at: new Date().toISOString(),
    model_version: 'v3',
    picks: {
      dd: predictions.filter(p => p.type === 'DD').sort((a, b) => b.edge - a.edge),
      td: predictions.filter(p => p.type === 'TD').sort((a, b) => b.edge - a.edge)
    },
    summary: {
      total_dd: predictions.filter(p => p.type === 'DD').length,
      total_td: predictions.filter(p => p.type === 'TD').length,
      avg_edge_dd: avgEdge(predictions.filter(p => p.type === 'DD'))
    }
  };
}

function checkGates(prob, minutes, gate) {
  // Standard gates
  if (prob >= gate.min_prob && minutes >= gate.min_minutes) return true;
  
  // Elite exception
  if (prob >= gate.elite_prob && minutes >= gate.elite_minutes) return true;
  
  return false;
}

function isEliteException(prob, minutes, gate) {
  return prob >= gate.elite_prob && minutes >= gate.elite_minutes && minutes < gate.min_minutes;
}

function oddsToProb(odds) {
  return odds > 0 ? 100 / (odds + 100) : Math.abs(odds) / (Math.abs(odds) + 100);
}

function calculateDDProbability(l20, model) {
  // Implement JS version of model prediction
  // For XGBoost, this could be:
  // 1. Walk decision trees
  // 2. Apply calibration curve
  // Or use simplified decision rules exported from Python model
  
  // Placeholder - replace with actual model logic
  return l20.dd_rate_l20; // Temporary: use historical rate
}

// Similar for TD...
```

### API Response Format:
```json
{
  "date": "2025-11-14",
  "generated_at": "2025-11-14T15:30:00Z",
  "model_version": "v3",
  "picks": {
    "dd": [
      {
        "player": "Karl-Anthony Towns",
        "team": "NY",
        "type": "DD",
        "model_prob": 0.995,
        "best_odds": 250,
        "implied_prob": 0.286,
        "edge": 0.709,
        "l20_dd_rate": 0.95,
        "avg_minutes": 35.4,
        "is_elite_exception": false
      }
    ],
    "td": []
  },
  "summary": {
    "total_dd": 9,
    "total_td": 0,
    "avg_edge_dd": 0.43
  }
}
```

---

## Phase 4: Frontend Integration (Append to NBA.jsx)

### **CRITICAL: DO NOT REPLACE NBA.jsx - APPEND ONLY**

**Strategy:**
1. Add `<NBADDTDPicks />` component **below** existing NBA content
2. Match existing card/table styling from other NBA modules (RCI/props)
3. Keep all existing NBA features intact
4. Use same data fetching patterns as NFL/MLB pages

### Implementation (Add to bottom of NBA.jsx):

```jsx
// At top of NBA.jsx, add import:
import { useState, useEffect } from 'react';

// At bottom of NBA.jsx return statement, add:
export default function NBA() {
  return (
    <div>
      {/* EXISTING NBA CONTENT - DO NOT MODIFY */}
      {/* ... existing props, RCI, etc. ... */}
      
      {/* NEW: DD/TD SECTION - APPEND HERE */}
      <NBADDTDPicks />
    </div>
  );
}

// New component (add at end of file):
function NBADDTDPicks() {
  const [picks, setPicks] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  useEffect(() => {
    fetchPicks();
  }, []);

  const fetchPicks = async () => {
    try {
      setLoading(true);
      const response = await fetch('/.netlify/functions/nbaddtd-picks');
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      setPicks(data);
      setLastUpdated(new Date(data.generated_at));
      setError(null);
    } catch (err) {
      setError('Failed to load DD/TD picks. Please try again.');
      console.error('NBADDTD Error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="nbaddtd-section">
        <h2>🔥 Double-Double & Triple-Double Picks</h2>
        <div className="loading">Loading picks...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="nbaddtd-section">
        <h2>🔥 Double-Double & Triple-Double Picks</h2>
        <div className="error">
          {error}
          <button onClick={fetchPicks}>Retry</button>
        </div>
      </div>
    );
  }

  const { dd = [], td = [] } = picks?.picks || {};

  return (
    <div className="nbaddtd-section">
      <div className="section-header">
        <h2>🔥 Double-Double & Triple-Double Picks</h2>
        <span className="last-updated">
          Updated: {lastUpdated?.toLocaleString()}
        </span>
      </div>
      
      {picks?.warning && (
        <div className="warning">⚠️  {picks.warning}</div>
      )}
      
      {/* DD Picks Table */}
      {dd.length > 0 && (
        <div className="picks-group">
          <h3>Double-Double Picks ({dd.length})</h3>
          <table className="picks-table">
            <thead>
              <tr>
                <th>Player</th>
                <th>Team</th>
                <th>Model</th>
                <th>Odds</th>
                <th>Edge</th>
                <th>Form (L20)</th>
                <th>Minutes</th>
              </tr>
            </thead>
            <tbody>
              {dd.map((pick, idx) => (
                <tr key={idx} className={getEdgeClass(pick.edge)}>
                  <td className="player-name">
                    {pick.player}
                    {pick.is_elite_exception && (
                      <span className="elite-badge" title="Elite Exception: Passed via high probability">
                        🌟
                      </span>
                    )}
                  </td>
                  <td>{pick.team}</td>
                  <td className="model-prob">{(pick.model_prob * 100).toFixed(1)}%</td>
                  <td className="odds">{formatOdds(pick.best_odds)}</td>
                  <td className="edge">+{(pick.edge * 100).toFixed(1)}%</td>
                  <td>{(pick.l20_dd_rate * 100).toFixed(0)}%</td>
                  <td>{pick.avg_minutes.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      
      {/* TD Picks Table */}
      {td.length > 0 && (
        <div className="picks-group">
          <h3>Triple-Double Picks ({td.length})</h3>
          <table className="picks-table">
            {/* Similar structure to DD table */}
          </table>
        </div>
      )}
      
      {dd.length === 0 && td.length === 0 && (
        <div className="no-picks">
          No picks passing acceptance gates today
        </div>
      )}
      
      {/* Summary Stats */}
      {picks?.summary && (
        <div className="summary">
          <div>Avg DD Edge: +{(picks.summary.avg_edge_dd * 100).toFixed(1)}%</div>
          <div>Model: v{picks.model_version}</div>
        </div>
      )}
    </div>
  );
}

// Helper functions
function getEdgeClass(edge) {
  if (edge > 0.5) return 'edge-elite';    // >50% edge
  if (edge > 0.2) return 'edge-strong';   // 20-50% edge
  return 'edge-positive';                 // 0-20% edge
}

function formatOdds(odds) {
  return odds > 0 ? `+${odds}` : odds;
}
```

### CSS Styling (Match RRMODEL Theme):

```css
/* Add to NBA.jsx styles or global CSS */

.nbaddtd-section {
  margin: 2rem 0;
  padding: 1.5rem;
  background: var(--card-bg, #1a1a1a);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.last-updated {
  color: var(--text-muted, #888);
  font-size: 0.85em;
}

.warning {
  background: rgba(255, 165, 0, 0.1);
  border-left: 3px solid orange;
  padding: 0.75rem;
  margin-bottom: 1rem;
}

.picks-group {
  margin-bottom: 2rem;
}

.picks-group h3 {
  margin-bottom: 0.75rem;
  color: var(--text-primary, #fff);
}

.picks-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.95em;
}

.picks-table th {
  background: var(--header-bg, #2a2a2a);
  padding: 0.75rem;
  text-align: left;
  font-weight: 600;
  border-bottom: 2px solid var(--border-color, #444);
}

.picks-table td {
  padding: 0.75rem;
  border-bottom: 1px solid var(--border-color, #333);
}

.picks-table tbody tr:hover {
  background: rgba(255, 255, 255, 0.02);
}

/* Edge color coding */
.edge-elite {
  background: rgba(0, 255, 0, 0.08);
  border-left: 3px solid #0f0;
}

.edge-strong {
  background: rgba(255, 255, 0, 0.06);
  border-left: 3px solid #ff0;
}

.edge-positive {
  background: rgba(255, 255, 255, 0.02);
}

/* Column-specific styling */
.model-prob {
  font-weight: 600;
  color: var(--accent-blue, #4a9eff);
}

.edge {
  font-weight: 700;
  color: var(--accent-green, #0f0);
}

.odds {
  font-family: 'Courier New', monospace;
}

.elite-badge {
  margin-left: 0.5rem;
  cursor: help;
}

.no-picks {
  text-align: center;
  padding: 2rem;
  color: var(--text-muted, #888);
}

.summary {
  display: flex;
  gap: 2rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color, #333);
  font-size: 0.9em;
  color: var(--text-muted, #888);
}

/* Mobile responsive */
@media (max-width: 768px) {
  .picks-table {
    font-size: 0.85em;
  }
  
  .picks-table th,
  .picks-table td {
    padding: 0.5rem 0.25rem;
  }
  
  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
}
```

---

## Phase 5: Environment Variables Setup

### Netlify Dashboard Configuration:
```bash
# Navigate to: Netlify Dashboard → Site Settings → Environment Variables
# Click "Add a variable" for each:

ODDS_API_KEY=YOUR_ODDS_API_KEY_HERE
NBADDTD_MODEL_VERSION=v3
NBADDTD_CACHE_TTL=86400
NBADDTD_ENABLED=true
```

**IMPORTANT:** 
- Replace `YOUR_ODDS_API_KEY_HERE` with actual key (not committed to git)
- These are shared across all Netlify Functions
- No secrets in source code!

### Local Development (.env.local):
```bash
# Create in RRMODEL root for local testing with `netlify dev`
ODDS_API_KEY=YOUR_ODDS_API_KEY_HERE
NBADDTD_MODEL_VERSION=v3
NBADDTD_CACHE_TTL=3600
NBADDTD_ENABLED=true
```

**Add to .gitignore:**
```
.env
.env.local
.env.*.local
```

---

## Phase 6: Deployment Strategy

### File Checklist (Verify Before Deploy):

**Models & Data:**
```
✅ models/nba/ddtd/model_params_v3.json
✅ models/nba/ddtd/acceptance_gates_v3.json
✅ models/nba/ddtd/current_teams.json
✅ data/nba/ddtd_l20_cache.json
```

**Netlify Functions:**
```
✅ netlify/functions/nbaddtd-picks.mjs
✅ netlify/functions/_lib/blobs-nba.mjs
✅ netlify/functions/_lib/odds-nba.mjs
✅ netlify/functions/_lib/ddtd-predictor.mjs
```

**Frontend:**
```
✅ src/pages/NBA.jsx (updated with <NBADDTDPicks /> component)
```

**Configuration:**
```
✅ package.json (added @netlify/blobs dependency)
✅ Environment variables configured in Netlify Dashboard
✅ .gitignore (excludes .env, .env.local)
```

### Deployment Steps:

1. **Verify Local Testing:**
```bash
# In RRMODEL directory
netlify dev

# Test function endpoint
curl http://localhost:8888/.netlify/functions/nbaddtd-picks

# Expected response:
{
  "picks": {
    "dd": [...],
    "td": [...]
  },
  "generated_at": "2025-01-20T10:00:00Z",
  "model_version": "v3"
}
```

2. **Commit Changes to Git:**
```bash
cd ~/RRMODEL
git status  # verify only intended files

git add netlify/functions/nbaddtd-picks.mjs
git add netlify/functions/_lib/blobs-nba.mjs
git add netlify/functions/_lib/odds-nba.mjs
git add netlify/functions/_lib/ddtd-predictor.mjs
git add models/nba/ddtd/
git add data/nba/ddtd_l20_cache.json
git add src/pages/NBA.jsx
git add package.json

git commit -m "feat: Add NBA DD/TD prediction system

- Implement nbaddtd-picks Netlify function
- Add DD/TD model files (v3) in JavaScript format
- Integrate NBADDTD picks component into NBA page
- Add L20 stats cache with daily refresh
- Reuse existing blob/odds helper patterns
"

git push origin main
```

3. **Monitor Netlify Deploy:**
```bash
# Watch deploy logs in Netlify Dashboard
# Typical deploy time: 2-3 minutes

# Check for errors:
# - Function build errors
# - Missing dependencies
# - Environment variable access issues
```

4. **Verify Production:**
```bash
# Test production function endpoint
curl https://YOUR-SITE.netlify.app/.netlify/functions/nbaddtd-picks

# Check frontend integration
# Navigate to: https://YOUR-SITE.netlify.app/nba
# Scroll to bottom → should see "🔥 Double-Double & Triple-Double Picks" section
```

5. **Monitor First 24 Hours:**
- Check Netlify Function logs for errors
- Verify cache hits/misses
- Ensure odds API calls succeed
- Watch for any timeout issues

### Rollback Plan (If Issues Occur):

```bash
# Emergency rollback to previous working version
git revert HEAD
git push origin main

# Or use Netlify dashboard:
# Site → Deploys → Click previous deploy → "Publish deploy"
```

---

## Phase 7: Testing & Validation Checklist

### Pre-Deploy Tests (Local):

**1. Function Endpoint Test:**
```bash
# Start local dev server
netlify dev

# Test picks endpoint
curl http://localhost:8888/.netlify/functions/nbaddtd-picks | jq '.'

# Expected keys in response:
# - picks.dd (array)
# - picks.td (array)
# - generated_at (ISO timestamp)
# - model_version ("v3")
# - summary.avg_edge_dd (number)
```

**2. Cache Behavior Test:**
```bash
# First call (cold start - no cache)
time curl http://localhost:8888/.netlify/functions/nbaddtd-picks

# Second call (should be <100ms from cache)
time curl http://localhost:8888/.netlify/functions/nbaddtd-picks

# Expected: Second call much faster
```

**3. Error Handling Test:**
```bash
# Test with invalid API key (temporarily set wrong key in .env.local)
ODDS_API_KEY=invalid_key netlify dev
curl http://localhost:8888/.netlify/functions/nbaddtd-picks

# Expected: Fallback to yesterday's cache OR empty picks with warning
```

**4. Model Validation:**
```javascript
// Run in Node.js console or test file
const modelParams = require('./models/nba/ddtd/model_params_v3.json');
const gates = require('./models/nba/ddtd/acceptance_gates_v3.json');

// Verify structure
console.assert(modelParams.coefficients, 'Missing coefficients');
console.assert(modelParams.intercept !== undefined, 'Missing intercept');
console.assert(gates.standard, 'Missing standard gates');
console.assert(gates.elite_exception, 'Missing elite exception gates');

// Verify reasonable values
const coefNames = Object.keys(modelParams.coefficients);
console.log('Model features:', coefNames);
// Expected: ['dd_rate_l20', 'avg_minutes_l20', 'avg_pts_l20', ...]
```

**5. Frontend Integration Test:**
```bash
# Start dev server (React/Vite)
npm run dev

# Navigate to /nba page
# Verify:
# - Component loads without React errors
# - Loading state shows initially
# - Picks render in table format
# - Styling matches existing RRMODEL theme
# - Elite badges (🌟) show on elite exception picks
# - Edge colors coded correctly (green > yellow > white)
```

### Post-Deploy Tests (Production):

**1. Production Function Test:**
```bash
curl https://YOUR-SITE.netlify.app/.netlify/functions/nbaddtd-picks | jq '.generated_at'
# Should return today's ISO timestamp
```

**2. Cache Expiration Test:**
```bash
# Wait 25 hours after deploy
curl https://YOUR-SITE.netlify.app/.netlify/functions/nbaddtd-picks | jq '.generated_at'
# Timestamp should update to new day
```

**3. Performance Test:**
```bash
# Cold start (after cache expires)
time curl https://YOUR-SITE.netlify.app/.netlify/functions/nbaddtd-picks

# Warm start (within cache TTL)
time curl https://YOUR-SITE.netlify.app/.netlify/functions/nbaddtd-picks

# Expected:
# - Cold start: 2-5 seconds (fetching odds + computing)
# - Warm start: <500ms (reading from cache)
```

**4. Browser Console Test:**
```javascript
// Open DevTools on /nba page
fetch('/.netlify/functions/nbaddtd-picks')
  .then(r => r.json())
  .then(console.log);

// Check for:
// - No CORS errors
// - Successful 200 response
// - Valid JSON structure
```

**5. Edge Case Test:**
```bash
# Test on day with no valid picks (rare but possible)
# Manually trigger by temporarily raising gate thresholds

# Expected response:
{
  "picks": { "dd": [], "td": [] },
  "generated_at": "...",
  "warning": "No picks passing acceptance gates today"
}
```

### Validation Criteria (Must Pass All):

- [ ] Function responds within 5 seconds (cold start)
- [ ] Function responds within 500ms (cached)
- [ ] Picks include all required fields (player, model_prob, best_odds, edge)
- [ ] Edge calculations reasonable (0-100% range)
- [ ] Elite exceptions flagged correctly
- [ ] Frontend renders without errors
- [ ] Styling matches existing RRMODEL theme
- [ ] Mobile responsive (test on phone)
- [ ] No console errors in browser
- [ ] Cache TTL respected (24 hours)

---

## Phase 8: Maintenance & Operations

### Daily Operations:

**1. L20 Cache Refresh (Automated Recommended):**
```bash
# Option A: GitHub Action (create .github/workflows/refresh-nba-l20.yml)
name: Refresh NBA L20 Cache
on:
  schedule:
    - cron: '0 10 * * *'  # 10 AM daily
  workflow_dispatch:  # Manual trigger

jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install pandas nba_api
      
      - name: Run L20 calculation
        run: python scripts/calculate_l20_stats.py
      
      - name: Commit updated cache
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add data/nba/ddtd_l20_cache.json
          git commit -m "chore: Update L20 cache $(date +%Y-%m-%d)" || exit 0
          git push

# Option B: Manual refresh (if GitHub Action not set up)
cd ~/Desktop/REPO33/NBA-DDTD-RESEARCH
python scripts/calculate_l20_stats.py
# Copy updated data/nba/ddtd_l20_cache.json to RRMODEL repo
```

**2. Monitor Function Performance:**
```bash
# Check Netlify Function logs daily
# Navigate to: Netlify Dashboard → Functions → nbaddtd-picks → Logs

# Look for:
# - Timeout errors (>10 seconds)
# - API rate limit errors (429 responses)
# - Cache miss patterns (should be once per day)
# - Unusual error spikes
```

**3. Verify Picks Quality:**
```bash
# Daily quick check
curl https://YOUR-SITE.netlify.app/.netlify/functions/nbaddtd-picks | jq '.picks.dd | length'

# Expected: 0-5 picks on typical day
# Alert if: >10 picks (gates may be too loose) OR no picks for 3+ days
```

### Weekly Tasks:

**1. Review Model Performance:**
```bash
# Track actual outcomes vs. predictions
# (Requires separate tracking system - not covered in this integration)

# Example tracking structure:
{
  "2025-01-20": {
    "dd_picks": 3,
    "dd_hits": 2,
    "dd_accuracy": 0.667,
    "avg_edge": 0.23
  }
}
```

**2. Check Odds API Usage:**
```bash
# Monitor API quota (if applicable)
# The Odds API free tier: 500 requests/month
# Calculate: 1 request/day * 30 days = 30/month (well within limits)
```

### Model Update Workflow:

**When New Model Version is Ready (v4, v5, etc.):**

1. **Export Model Parameters to JSON:**
```python
# In NBA-DDTD-RESEARCH repo
import joblib
import json

model = joblib.load('models/ddtd_model_v4.pkl')

# Extract coefficients
params = {
    "coefficients": dict(zip(feature_names, model.coef_)),
    "intercept": float(model.intercept_),
    "model_type": "logistic_regression",
    "features": feature_names
}

with open('models/nba/ddtd/model_params_v4.json', 'w') as f:
    json.dump(params, f, indent=2)
```

2. **Update RRMODEL Files:**
```bash
cd ~/RRMODEL

# Copy new model files
cp ~/Desktop/REPO33/NBA-DDTD-RESEARCH/models/nba/ddtd/model_params_v4.json models/nba/ddtd/
cp ~/Desktop/REPO33/NBA-DDTD-RESEARCH/models/nba/ddtd/acceptance_gates_v4.json models/nba/ddtd/

# Update predictor to use v4
# Edit netlify/functions/_lib/ddtd-predictor.mjs
# Change: import modelParams from '../../../models/nba/ddtd/model_params_v4.json';

# Update environment variable
# Netlify Dashboard → Environment Variables → NBADDTD_MODEL_VERSION = v4

git add models/nba/ddtd/model_params_v4.json
git add models/nba/ddtd/acceptance_gates_v4.json
git add netlify/functions/_lib/ddtd-predictor.mjs
git commit -m "feat: Upgrade NBADDTD model to v4"
git push
```

3. **Canary Testing:**
```bash
# After deploy, compare v4 vs v3 picks side-by-side
# (Temporarily run both versions if possible)

# Monitor for 3-5 days:
# - Pick count stability
# - Edge value reasonableness
# - No unexpected errors
```

### Troubleshooting Guide:

**Issue: Function Times Out (>10 seconds)**
```
Root Cause: Odds API slow or cold start overhead
Fix Options:
1. Increase cache TTL (reduce API calls)
2. Pre-warm function daily via cron job
3. Optimize prediction calculation logic
4. Add response timeout handling
```

**Issue: No Picks Returned for Multiple Days**
```
Root Cause: Gates too strict OR L20 cache stale
Fix Options:
1. Check ddtd_l20_cache.json last_updated timestamp
2. Manually refresh L20 cache
3. Review gate thresholds in acceptance_gates_v3.json
4. Check if NBA season is active (no games = no picks)
```

**Issue: Stale Picks (Yesterday's Data Showing)**
```
Root Cause: Cache not expiring properly
Fix Options:
1. Check NBADDTD_CACHE_TTL environment variable (should be 86400)
2. Manually clear Netlify Blobs cache:
   - Use Netlify CLI: netlify blobs:delete store picks-2025-01-19
3. Verify cache key generation uses correct date
```

**Issue: Odds API 429 Error (Rate Limit)**
```
Root Cause: Too many API calls
Fix Options:
1. Verify cache hit rate (should be 1 miss/day)
2. Check for double-calling bug in function
3. Upgrade The Odds API plan if needed
4. Add exponential backoff retry logic
```

### Monitoring Dashboard (Optional):

**Recommended Metrics to Track:**
- Daily pick count (DD vs TD)
- Average model probability
- Average edge percentage
- Function execution time (p50, p95, p99)
- Cache hit rate
- API success rate
- L20 cache age

**Tools:**
- Netlify Analytics (built-in)
- Custom logging to external service (Datadog, LogRocket)
- Simple JSON log file committed to repo

---

## Success Metrics

### MVP (Phase 1 Launch):
- [ ] Picks display on NBA page without breaking existing features
- [ ] No errors in production logs
- [ ] Caching working (24hr TTL)
- [ ] Mobile responsive
- [ ] Elite exceptions displaying correctly

### V1.1 Enhancements (Future):
- [ ] Near-miss candidates section
- [ ] Historical pick tracking
- [ ] Performance dashboard
- [ ] Alert system for elite bets
- [ ] Automated model retraining pipeline

---

## Appendix A: Model Conversion Guide (Python .pkl → JavaScript JSON)

### Step-by-Step Conversion Process:

**1. Extract Model Parameters from .pkl File:**
```python
# In NBA-DDTD-RESEARCH repo
import joblib
import json
import numpy as np

# Load trained model
model = joblib.load('models/ddtd_model_v3.pkl')

# Extract feature names (from training script or model object)
feature_names = [
    'dd_rate_l20',
    'avg_minutes_l20',
    'avg_pts_l20',
    'avg_rebs_l20',
    'avg_asts_l20',
    'elite_rebounder',
    'elite_playmaker',
    'usage_rate_l20'
]

# Build JSON-compatible structure
model_params = {
    "model_type": "logistic_regression",
    "version": "v3",
    "coefficients": {},
    "intercept": float(model.intercept_[0]),
    "features": feature_names,
    "trained_on": "2024-2025 NBA Season",
    "notes": "Exported from scikit-learn for JavaScript deployment"
}

# Extract coefficients (handle both numpy arrays and single values)
for i, feature in enumerate(feature_names):
    coef_value = model.coef_[0][i] if hasattr(model.coef_, '__iter__') else model.coef_[i]
    model_params["coefficients"][feature] = float(coef_value)

# Save to JSON
output_path = 'models/nba/ddtd/model_params_v3.json'
with open(output_path, 'w') as f:
    json.dump(model_params, f, indent=2)

print(f"✅ Model parameters exported to {output_path}")
print(f"   - {len(feature_names)} features")
print(f"   - Intercept: {model_params['intercept']:.4f}")
```

**2. Verify Exported JSON Structure:**
```json
{
  "model_type": "logistic_regression",
  "version": "v3",
  "coefficients": {
    "dd_rate_l20": 2.45,
    "avg_minutes_l20": 0.18,
    "avg_pts_l20": 0.12,
    "avg_rebs_l20": 0.31,
    "avg_asts_l20": 0.22,
    "elite_rebounder": 0.87,
    "elite_playmaker": 0.65,
    "usage_rate_l20": 0.09
  },
  "intercept": -5.234,
  "features": ["dd_rate_l20", "avg_minutes_l20", ...],
  "trained_on": "2024-2025 NBA Season"
}
```

**3. Implement Prediction Logic in JavaScript:**
```javascript
// netlify/functions/_lib/ddtd-predictor.mjs
import modelParams from '../../../models/nba/ddtd/model_params_v3.json' assert { type: 'json' };

/**
 * Calculate logistic regression probability
 * P(Y=1) = 1 / (1 + exp(-z))
 * where z = intercept + sum(coefficient_i * feature_i)
 */
function predictProbability(features) {
  const { coefficients, intercept } = modelParams;
  
  // Calculate linear combination
  let z = intercept;
  for (const [featureName, value] of Object.entries(features)) {
    if (coefficients[featureName] !== undefined) {
      z += coefficients[featureName] * value;
    }
  }
  
  // Apply sigmoid function
  const probability = 1 / (1 + Math.exp(-z));
  
  return probability;
}

/**
 * Example feature extraction for a player
 */
function extractFeatures(playerStats, l20Stats) {
  return {
    dd_rate_l20: l20Stats.dd_rate_l20 || 0,
    avg_minutes_l20: l20Stats.avg_minutes_l20 || 0,
    avg_pts_l20: l20Stats.avg_pts_l20 || 0,
    avg_rebs_l20: l20Stats.avg_rebs_l20 || 0,
    avg_asts_l20: l20Stats.avg_asts_l20 || 0,
    elite_rebounder: l20Stats.avg_rebs_l20 >= 10 ? 1 : 0,
    elite_playmaker: l20Stats.avg_asts_l20 >= 8 ? 1 : 0,
    usage_rate_l20: l20Stats.usage_rate_l20 || 0
  };
}

// Export for use in main function
export { predictProbability, extractFeatures };
```

**4. Test Parity with Python Model:**
```python
# In NBA-DDTD-RESEARCH repo - validation script
import joblib
import json
import numpy as np

# Load both versions
python_model = joblib.load('models/ddtd_model_v3.pkl')
with open('models/nba/ddtd/model_params_v3.json') as f:
    js_params = json.load(f)

# Test case: sample player stats
test_features = {
    'dd_rate_l20': 0.75,
    'avg_minutes_l20': 32.5,
    'avg_pts_l20': 24.3,
    'avg_rebs_l20': 11.2,
    'avg_asts_l20': 6.8,
    'elite_rebounder': 1.0,
    'elite_playmaker': 0.0,
    'usage_rate_l20': 0.28
}

# Python prediction
X = np.array([[test_features[f] for f in js_params['features']]])
python_prob = python_model.predict_proba(X)[0][1]

# JavaScript prediction (manual calculation)
z = js_params['intercept']
for feature, coef in js_params['coefficients'].items():
    z += coef * test_features[feature]
js_prob = 1 / (1 + np.exp(-z))

# Compare
print(f"Python probability: {python_prob:.6f}")
print(f"JavaScript probability: {js_prob:.6f}")
print(f"Difference: {abs(python_prob - js_prob):.8f}")

# Assert parity (should be < 0.0001)
assert abs(python_prob - js_prob) < 0.0001, "Model parity check failed!"
print("✅ Model parity verified - predictions match!")
```

---

## Appendix B: Quick Reference

### File Locations (RRMODEL):
```
netlify/functions/
  ├── nbaddtd-picks.mjs                  # Main endpoint
  └── _lib/
      ├── blobs-nba.mjs                  # Blob storage helper
      ├── odds-nba.mjs                   # Odds API helper
      └── ddtd-predictor.mjs             # Prediction logic

models/nba/ddtd/
  ├── model_params_v3.json               # Model coefficients
  ├── acceptance_gates_v3.json           # Gate thresholds
  └── current_teams.json                 # Player→team mapping

data/nba/
  └── ddtd_l20_cache.json                # L20 stats cache

src/pages/
  └── NBA.jsx                            # Frontend (append component)
```

### Environment Variables:
```bash
ODDS_API_KEY=YOUR_ODDS_API_KEY_HERE
NBADDTD_MODEL_VERSION=v3
NBADDTD_CACHE_TTL=86400
NBADDTD_ENABLED=true
```

### Useful Commands:
```bash
# Local testing
netlify dev
curl http://localhost:8888/.netlify/functions/nbaddtd-picks | jq

# Check production
curl https://YOUR-SITE.netlify.app/.netlify/functions/nbaddtd-picks | jq '.picks.dd | length'

# Clear cache manually
netlify blobs:delete store picks-2025-01-20

# Refresh L20 cache
cd ~/Desktop/REPO33/NBA-DDTD-RESEARCH
python scripts/calculate_l20_stats.py
```

### Common Edge Values:
- **0-10%**: Low confidence (display but highlight risk)
- **10-20%**: Standard pick (green)
- **20-50%**: Strong pick (yellow/gold)
- **50%+**: Elite pick (bright green/starred)

---

## Implementation Guidelines for Claude/Copilot

### **Critical Instructions:**

1. **Follow this plan exactly** - Do not invent new folder structures or patterns
2. **JavaScript-only** - No Python runtime, no .pkl files in production
3. **DO NOT touch existing NBA features** - NBA.jsx already has props/RCI/other content
4. **Append, don't replace** - Add `<NBADDTDPicks />` to bottom of NBA.jsx only
5. **Use exact naming** - `nbaddtd-picks.mjs`, store name `'nba-ddtd'`, etc.
6. **Check API market keys** - Verify The Odds API uses `player_double_double`/`player_triple_double`
7. **Test before deploying** - Run `netlify dev` and validate endpoint locally

### **If you encounter issues:**

- **JSON import errors?** → Switch to `fs.readFileSync` (see note in Phase 3)
- **API key missing?** → Placeholder is `YOUR_ODDS_API_KEY_HERE`
- **Blob store errors?** → Ensure store name is exactly `'nba-ddtd'`
- **Frontend errors?** → Check you're appending to NBA.jsx, not replacing it
- **Model predictions wrong?** → Run parity check from Appendix A

### **Execution Order:**

1. Export model to JSON (Appendix A)
2. Create `_lib/` helpers (blobs-nba, odds-nba, ddtd-predictor)
3. Create main function (nbaddtd-picks.mjs)
4. Append frontend component to NBA.jsx
5. Test locally with `netlify dev`
6. Deploy via git push

---

## Next Steps

**Immediate Actions**:
1. ✅ Plan v2 created with RRMODEL-specific architecture
2. ⏭️ Convert .pkl model to JSON using Appendix A guide
3. ⏭️ Create helper modules in RRMODEL `_lib/` directory
4. ⏭️ Implement nbaddtd-picks.mjs function
5. ⏭️ Append `<NBADDTDPicks />` component to NBA.jsx
6. ⏭️ Test locally with `netlify dev`
7. ⏭️ Deploy to production and monitor

**Questions Resolved**:
- ✅ JavaScript-only implementation (no Python runtime)
- ✅ NBADDTD naming throughout (clarity from existing NBA features)
- ✅ Append to NBA.jsx (don't create separate page)
- ✅ Reuse existing _lib patterns (blobs, odds)
- ✅ L20 cache schema defined explicitly
- ✅ API key placeholder for documentation
- ✅ Blob store name specified ('nba-ddtd')
- ✅ Fallback for JSON imports if needed
- ✅ Global fetch vs node-fetch clarified

---

**END OF INTEGRATION PLAN v2**
