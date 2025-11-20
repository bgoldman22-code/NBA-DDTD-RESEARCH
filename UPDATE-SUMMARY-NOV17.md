# NBA DD/TD Model Updates - November 17, 2025

## Critical Bug Fix + TD System Redesign

---

## 🐛 CRITICAL BUG FIX: YES/NO Odds Filtering

### The Problem
The Odds API returns **both YES and NO outcomes** for each player prop. Our script was collecting ALL outcomes without filtering, which caused:

- **For favorites**: We'd pick up both YES (-339) and NO (+280) odds
- **The `max()` function** would select +280 (the NO bet) since it's numerically larger
- **Result**: Showing incorrect "NO DD" odds instead of "YES DD" odds
- **Impact**: Massive fake edges (e.g., KAT showing +280 with 73% edge instead of -339 with 22% edge)

### The Fix

**File**: `scripts/generate_picks_for_rrmodel.py`

**Location**: Lines ~95-105 (in the `fetch_player_props_odds()` function)

**BEFORE**:
```python
for outcome in market.get('outcomes', []):
    odds_data.append({
        'player_name': outcome.get('description'),
        'bet_type': 'DD' if market_key == 'player_double_double' else 'TD',
        'odds': outcome.get('price'),
        'bookmaker': bookmaker.get('title'),
        'game': f"{away_team} @ {home_team}"
    })
```

**AFTER**:
```python
for outcome in market.get('outcomes', []):
    # CRITICAL: Only include "Yes" outcomes (filter out "No" bets)
    if outcome.get('name') != 'Yes':
        continue
        
    odds_data.append({
        'player_name': outcome.get('description'),
        'bet_type': 'DD' if market_key == 'player_double_double' else 'TD',
        'odds': outcome.get('price'),
        'bookmaker': bookmaker.get('title'),
        'game': f"{away_team} @ {home_team}"
    })
```

### Verification Example (Karl-Anthony Towns)

**BEFORE FIX**:
- Odds: +280 (NO DD)
- Edge: 73.1% ❌ (WRONG)
- Implied Prob: 26.3%

**AFTER FIX**:
- Odds: -339 (YES DD)
- Edge: 22.2% ✅ (CORRECT)
- Implied Prob: 77.2%

---

## 🎯 TD SYSTEM REDESIGN: Two-Tier Profitability Framework

### The Problem
Old TD gates were too strict:
- `min_prob = 0.10` (10%)
- `min_minutes = 35`
- Result: **0 TD picks on most slates**, even though odds and model outputs existed

### The Solution: Two-Tier System

---

## FILE 1: `acceptance_gates_v3.json`

**Complete New Structure**:

```json
{
  "dd": {
    "min_prob": 0.15,
    "min_minutes": 30,
    "elite_prob": 0.90,
    "elite_minutes": 29,
    "near_miss_prob": 0.13,
    "near_miss_minutes": 28,
    "expected_edge": 0.3464705882352941,
    "hit_rate": 0.4964705882352941
  },
  "td": {
    "core": {
      "min_prob": 0.085,
      "min_minutes": 33,
      "min_edge": 0.045,
      "min_odds": 400,
      "description": "High-confidence TD plays with sustainable edge",
      "target_picks_per_slate": "0-3",
      "profile": "core"
    },
    "lotto": {
      "min_prob": 0.045,
      "min_minutes": 30,
      "min_edge": 0.10,
      "min_odds": 800,
      "max_prob": 0.085,
      "description": "High-variance longshots with extreme value",
      "target_picks_per_week": "0-5",
      "profile": "lotto",
      "stake_multiplier": 0.5
    },
    "legacy": {
      "min_prob": 0.1,
      "min_minutes": 35,
      "elite_prob": 0.80,
      "elite_minutes": 33,
      "near_miss_prob": 0.08,
      "near_miss_minutes": 33,
      "expected_edge": 0.18888888888888886,
      "hit_rate": 0.28888888888888886,
      "note": "Historical gates - kept for reference"
    }
  }
}
```

**Key Changes**:
- Split `td` into three profiles: `core`, `lotto`, `legacy`
- TD Core: 8.5% prob, 33 min, 4.5% edge, +400 odds minimum
- TD Lotto: 4.5% prob, 30 min, 10% edge, +800 odds minimum, 0.5x stake size

---

## FILE 2: `scripts/generate_picks_for_rrmodel.py`

### Change 1: Load New Gates Structure

**Location**: Lines ~245-248

**BEFORE**:
```python
print(f"✅ Gates: DD {gates['dd']['min_prob']*100:.0f}%+ @ {gates['dd']['min_minutes']} min, TD {gates['td']['min_prob']*100:.0f}%+ @ {gates['td']['min_minutes']} min\n")
```

**AFTER**:
```python
print(f"✅ Gates: DD {gates['dd']['min_prob']*100:.0f}%+ @ {gates['dd']['min_minutes']} min")
print(f"   TD Core: {gates['td']['core']['min_prob']*100:.1f}%+, {gates['td']['core']['min_minutes']} min, +{gates['td']['core']['min_odds']} odds")
print(f"   TD Lotto: {gates['td']['lotto']['min_prob']*100:.1f}%+, {gates['td']['lotto']['min_minutes']} min, +{gates['td']['lotto']['min_odds']} odds\n")
```

---

### Change 2: Apply Two-Tier TD Gates

**Location**: Lines ~332-365

**BEFORE**:
```python
# Apply acceptance gates
dd_gate = gates['dd']
td_gate = gates['td']

dd_standard = (pred_df['dd_prob'] >= dd_gate['min_prob']) & \
             (pred_df['avg_minutes'] >= dd_gate['min_minutes']) & \
             (pred_df['dd_odds'].notna())

dd_elite = (pred_df['dd_prob'] >= dd_gate.get('elite_prob', 0.90)) & \
          (pred_df['avg_minutes'] >= dd_gate.get('elite_minutes', 29)) & \
          (pred_df['dd_odds'].notna())

dd_picks = pred_df[dd_standard | dd_elite].copy()

td_standard = (pred_df['td_prob'] >= td_gate['min_prob']) & \
             (pred_df['avg_minutes'] >= td_gate['min_minutes']) & \
             (pred_df['td_odds'].notna())

td_elite = (pred_df['td_prob'] >= td_gate.get('elite_prob', 0.80)) & \
          (pred_df['avg_minutes'] >= td_gate.get('elite_minutes', 33)) & \
          (pred_df['td_odds'].notna())

td_picks = pred_df[td_standard | td_elite].copy()

# Calculate edges
if not dd_picks.empty:
    dd_picks['implied_prob'] = dd_picks['dd_odds'].apply(odds_to_implied_prob)
    dd_picks['edge'] = dd_picks['dd_prob'] - dd_picks['implied_prob']
    dd_picks = dd_picks[dd_picks['edge'] > 0]
    dd_picks = dd_picks.sort_values('edge', ascending=False)

if not td_picks.empty:
    td_picks['implied_prob'] = td_picks['td_odds'].apply(odds_to_implied_prob)
    td_picks['edge'] = td_picks['td_prob'] - td_picks['implied_prob']
    td_picks = td_picks[td_picks['edge'] > 0]
    td_picks = td_picks.sort_values('edge', ascending=False)
```

**AFTER**:
```python
# Apply acceptance gates
dd_gate = gates['dd']
td_core_gate = gates['td']['core']
td_lotto_gate = gates['td']['lotto']

# DD Gates (unchanged)
dd_standard = (pred_df['dd_prob'] >= dd_gate['min_prob']) & \
             (pred_df['avg_minutes'] >= dd_gate['min_minutes']) & \
             (pred_df['dd_odds'].notna())

dd_elite = (pred_df['dd_prob'] >= dd_gate.get('elite_prob', 0.90)) & \
          (pred_df['avg_minutes'] >= dd_gate.get('elite_minutes', 29)) & \
          (pred_df['dd_odds'].notna())

dd_picks = pred_df[dd_standard | dd_elite].copy()

# TD Core Gates: High-confidence plays with sustainable edge
td_core = (pred_df['td_prob'] >= td_core_gate['min_prob']) & \
          (pred_df['avg_minutes'] >= td_core_gate['min_minutes']) & \
          (pred_df['td_odds'].notna()) & \
          (pred_df['td_odds'] >= td_core_gate['min_odds'])

# TD Lotto Gates: Longshot value plays
td_lotto = (pred_df['td_prob'] >= td_lotto_gate['min_prob']) & \
           (pred_df['td_prob'] < td_lotto_gate['max_prob']) & \
           (pred_df['avg_minutes'] >= td_lotto_gate['min_minutes']) & \
           (pred_df['td_odds'].notna()) & \
           (pred_df['td_odds'] >= td_lotto_gate['min_odds'])

td_core_picks = pred_df[td_core].copy()
td_lotto_picks = pred_df[td_lotto].copy()

# Calculate edges for DD
if not dd_picks.empty:
    dd_picks['implied_prob'] = dd_picks['dd_odds'].apply(odds_to_implied_prob)
    dd_picks['edge'] = dd_picks['dd_prob'] - dd_picks['implied_prob']
    dd_picks = dd_picks[dd_picks['edge'] > 0]
    dd_picks = dd_picks.sort_values('edge', ascending=False)

# Calculate edges for TD Core
if not td_core_picks.empty:
    td_core_picks['implied_prob'] = td_core_picks['td_odds'].apply(odds_to_implied_prob)
    td_core_picks['edge'] = td_core_picks['td_prob'] - td_core_picks['implied_prob']
    td_core_picks = td_core_picks[td_core_picks['edge'] >= td_core_gate['min_edge']]
    td_core_picks['profile'] = 'core'
    td_core_picks['stake_size'] = 1.0
    td_core_picks = td_core_picks.sort_values('edge', ascending=False)

# Calculate edges for TD Lotto
if not td_lotto_picks.empty:
    td_lotto_picks['implied_prob'] = td_lotto_picks['td_odds'].apply(odds_to_implied_prob)
    td_lotto_picks['edge'] = td_lotto_picks['td_prob'] - td_lotto_picks['implied_prob']
    td_lotto_picks = td_lotto_picks[td_lotto_picks['edge'] >= td_lotto_gate['min_edge']]
    td_lotto_picks['profile'] = 'lotto'
    td_lotto_picks['stake_size'] = td_lotto_gate['stake_multiplier']
    td_lotto_picks = td_lotto_picks.sort_values('edge', ascending=False)

# Combine TD picks (core first, then lotto)
td_picks = pd.concat([td_core_picks, td_lotto_picks], ignore_index=True) if not td_core_picks.empty or not td_lotto_picks.empty else pd.DataFrame()
```

---

### Change 3: Update TD Output Schema

**Location**: Lines ~395-420

**BEFORE**:
```python
td_picks_list = []
for _, pick in td_picks.iterrows():
    td_picks_list.append({
        'player': pick['player'],
        'model_prob': round(float(pick['td_prob']), 4),
        'best_odds': int(pick['td_odds']),
        'implied_prob': round(float(pick['implied_prob']), 4),
        'edge': round(float(pick['edge']), 4),
        'avg_minutes': round(float(pick['avg_minutes']), 1),
        'l20_td_rate': round(float(pick['l20_td_rate']), 3),
        'game': pick['game']
    })
```

**AFTER**:
```python
td_picks_list = []
for _, pick in td_picks.iterrows():
    td_picks_list.append({
        'player': pick['player'],
        'model_prob': round(float(pick['td_prob']), 4),
        'best_odds': int(pick['td_odds']),
        'implied_prob': round(float(pick['implied_prob']), 4),
        'edge': round(float(pick['edge']), 4),
        'avg_minutes': round(float(pick['avg_minutes']), 1),
        'l20_td_rate': round(float(pick['l20_td_rate']), 3),
        'game': pick['game'],
        'profile': pick['profile'],
        'stake_size': float(pick['stake_size'])
    })

# Count picks by profile
td_core_count = sum(1 for p in td_picks_list if p['profile'] == 'core')
td_lotto_count = sum(1 for p in td_picks_list if p['profile'] == 'lotto')
```

---

### Change 4: Update JSON Output Structure

**Location**: Lines ~425-450

**BEFORE**:
```python
output = {
    'date': today_str,
    'generated_at': generated_at,
    'model_version': 'v3',
    'picks': {
        'dd': dd_picks_list,
        'td': td_picks_list
    },
    'summary': {
        'total_dd': len(dd_picks_list),
        'total_td': len(td_picks_list),
        'avg_edge_dd': round(float(dd_picks['edge'].mean()), 4) if not dd_picks.empty else 0,
        'avg_edge_td': round(float(td_picks['edge'].mean()), 4) if not td_picks.empty else 0
    }
}
```

**AFTER**:
```python
output = {
    'date': today_str,
    'generated_at': generated_at,
    'model_version': 'v3',
    'picks': {
        'dd': dd_picks_list,
        'td': td_picks_list
    },
    'summary': {
        'total_dd': len(dd_picks_list),
        'total_td': len(td_picks_list),
        'td_core': td_core_count,
        'td_lotto': td_lotto_count,
        'avg_edge_dd': round(float(dd_picks['edge'].mean()), 4) if not dd_picks.empty else 0,
        'avg_edge_td': round(float(td_picks['edge'].mean()), 4) if not td_picks.empty else 0
    },
    'gates': {
        'td_core': {
            'min_prob': td_core_gate['min_prob'],
            'min_minutes': td_core_gate['min_minutes'],
            'min_edge': td_core_gate['min_edge'],
            'min_odds': td_core_gate['min_odds'],
            'description': td_core_gate['description']
        },
        'td_lotto': {
            'min_prob': td_lotto_gate['min_prob'],
            'min_minutes': td_lotto_gate['min_minutes'],
            'min_edge': td_lotto_gate['min_edge'],
            'min_odds': td_lotto_gate['min_odds'],
            'description': td_lotto_gate['description'],
            'stake_multiplier': td_lotto_gate['stake_multiplier']
        }
    }
}
```

---

### Change 5: Update Console Output

**Location**: Lines ~468-473

**BEFORE**:
```python
print("=" * 60)
print(f"✅ Generated {len(dd_picks_list)} DD picks, {len(td_picks_list)} TD picks")
print(f"✅ Saved to {output_path}")
print("=" * 60)
```

**AFTER**:
```python
print("=" * 60)
print(f"✅ Generated {len(dd_picks_list)} DD picks, {len(td_picks_list)} TD picks")
if td_core_count > 0:
    print(f"   📊 TD Core: {td_core_count} (high-confidence)")
if td_lotto_count > 0:
    print(f"   🎰 TD Lotto: {td_lotto_count} (longshot value)")
print(f"✅ Saved to {output_path}")
print("=" * 60)
```

---

## Verification & Testing

### Test Results (Nov 17, 2025)

**Before Fixes**:
- DD picks: 7 (1 had wrong odds)
- TD picks: 0
- KAT odds: +280 (NO DD) ❌

**After Fixes**:
- DD picks: 6 (all correct)
- TD picks: 1 (Scottie Barnes - Core)
- KAT odds: -339 (YES DD) ✅

### Example TD Pick Generated

**Scottie Barnes** (CHA @ TOR)
- Profile: **core**
- Model Prob: 23.08%
- Odds: +2700
- Implied Prob: 3.57%
- **Edge: 19.51%** (546% ROI potential)
- Minutes: 33.1
- Stake Size: 1.0

---

## Summary of Changes

### 1. **Critical Bug Fix** (YES/NO odds filtering)
- **Impact**: High - Was showing wrong odds for favorites
- **Files**: 1 (`generate_picks_for_rrmodel.py`)
- **Lines changed**: ~3-4 lines
- **Result**: All odds now correctly show YES outcomes only

### 2. **TD System Redesign** (Two-tier framework)
- **Impact**: High - Enables TD picks to fire while maintaining profitability
- **Files**: 2 (`acceptance_gates_v3.json`, `generate_picks_for_rrmodel.py`)
- **Lines changed**: ~100+ lines
- **Result**: TD picks now generate with clear Core/Lotto profiles

### 3. **Enhanced JSON Output**
- **Impact**: Medium - Better transparency and frontend display
- **New fields**: `profile`, `stake_size`, `td_core`, `td_lotto`, `gates`
- **Result**: Frontend can display TD tiers and recommended stake sizes

---

## Deployment Checklist

- [ ] Update `acceptance_gates_v3.json` in production
- [ ] Update `generate_picks_for_rrmodel.py` in production
- [ ] Test locally with live API
- [ ] Verify JSON output schema matches expectations
- [ ] Update frontend to display TD profile badges
- [ ] Commit and push to GitHub
- [ ] Trigger GitHub Action manually to test
- [ ] Monitor first 7 days for TD pick quality

---

**Last Updated**: November 17, 2025
**Model Version**: v3
**Architecture**: Hybrid (Python generation + JS serving)
