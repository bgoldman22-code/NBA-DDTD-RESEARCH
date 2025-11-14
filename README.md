# NBA Double-Double / Triple-Double Research

**Created:** November 12, 2025  
**Purpose:** Isolated research workspace for NBA DD/TD prediction models

## Overview

This workspace contains research and development code for predicting NBA Double-Doubles and Triple-Doubles. This work has been separated from the main RRMODEL repository to avoid interference with live site deployments on Netlify.

## Contents

### `ddtd/` - DD/TD Scripts
Scripts for building probability models for Double-Doubles and Triple-Doubles:
- `build-marginals.mjs` - Builds marginal probability distributions for each stat
- `estimate-copula.mjs` - Estimates copula dependencies between stats
- `train-calibration.mjs` - Calibrates probability estimates
- `utils-data.mjs` - Data loading and processing utilities
- `utils-distributions.mjs` - Statistical distribution utilities
- `utils-odds.mjs` - Odds conversion and calculation utilities

## Background

The DD/TD prediction system uses a copula-based approach to model the joint distribution of Points, Rebounds, Assists, Steals, and Blocks. This allows us to estimate the probability that a player achieves:
- **Double-Double (DD):** 10+ in two stat categories
- **Triple-Double (TD):** 10+ in three stat categories

## Why Separate from RRMODEL?

The main RRMODEL repository hosts the live RacerRoster.com prediction site, which:
- Deploys automatically to Netlify on every commit
- Serves NFL, NBA, NHL, and MLB predictions to subscribers
- Requires stability and minimal build complexity

This DD/TD research:
- Is experimental and under active development
- Uses different data pipelines and modeling approaches
- Doesn't need to be part of the production build
- Can iterate faster in isolation

## Getting Started

To work on DD/TD models:

1. **Data Requirements:**
   - Historical NBA player game logs with PTS, REB, AST, STL, BLK
   - Recent form data (L5, L10, L40 games)
   - Opponent defensive stats

2. **Dependencies:**
   ```bash
   npm install
   # Main dependencies from the scripts:
   # - jstat (for statistical distributions)
   # - @stdlib/stats (for copula estimation)
   ```

3. **Workflow:**
   ```bash
   # Build marginal distributions
   node ddtd/build-marginals.mjs
   
   # Estimate copula parameters
   node ddtd/estimate-copula.mjs
   
   # Train calibration
   node ddtd/train-calibration.mjs
   ```

## Production Pipeline Suite ✅

**NEW - November 12, 2025:** Complete ML pipeline for DD/TD predictions!

See **[PIPELINE_SUITE_README.md](PIPELINE_SUITE_README.md)** for full documentation.

### Scripts Available:
1. **`backtest_v3.py`** - Walk-forward backtesting with P&L tracking
2. **`predict_ddtd.py`** - Daily prediction pipeline (ranked picks)
3. **`predict_minutes.py`** - Minutes prediction model
4. **`monte_carlo_sim.py`** - Correlated Monte Carlo simulation

### Quick Start:
```bash
# Run backtest on 2023-24 season
python3 ddtd/backtest_v3.py

# Generate today's picks
python3 ddtd/predict_ddtd.py

# Train auxiliary models
python3 ddtd/predict_minutes.py
python3 ddtd/monte_carlo_sim.py
```

## Next Steps

Planned development:
- [x] Build Python-based ML models (Gradient Boosting) for DD/TD predictions ✅
- [x] Implement zero-leakage backtesting framework ✅
- [x] Create prediction pipeline for daily picks ✅
- [ ] Integrate with odds APIs for live betting (API-ready structure in place)
- [ ] Deploy to production if ROI targets are met (pending backtest validation)

## Related Documentation

See `NBA_PLAYER_PROPS_PLAN.md` in the main RRMODEL repo for historical context on the DD/TD feature planning.

## Questions?

This research workspace was created to maintain separation of concerns. All production NBA player props (PTS, REB, AST over/unders) remain in the main RRMODEL repository.
