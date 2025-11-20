# Test Environment Setup

This directory contains **SAMPLE/MOCK DATA** for testing the DD/TD pipeline.

## ⚠️ IMPORTANT: This is NOT real data!

The data in this environment was generated for testing purposes only:
- Player stats are synthetic (based on realistic averages)
- Game dates and IDs are fabricated
- Model is a simple mock (not trained on real data)

## What Was Created

1. **Sample Game Data** (`data/nba/boxscores-raw/`)
   - 100 games for 2023-24 season
   - 100 games for 2024-25 season
   - Realistic player stats with variance
   - Proper JSON structure

2. **Mock Model** (`models/nba/ddtd/ddtd_model_v3.pkl`)
   - Simple Gradient Boosting model
   - Trained on synthetic data
   - For testing pipeline only

3. **Acceptance Gates** (`models/nba/ddtd/acceptance_gates_v3.json`)
   - Production-ready configuration
   - DD: 10% edge, 28+ min
   - TD: 18% edge, 32+ min, 100+ pace

## Running Tests

```bash
# Test backtest (will use sample data)
python3 ddtd/backtest_v3.py

# Test predictions (will use sample data)
python3 ddtd/predict_ddtd.py

# Test minutes predictor (will train on sample data)
python3 ddtd/predict_minutes.py

# Test Monte Carlo (will estimate from sample data)
python3 ddtd/monte_carlo_sim.py
```

## For Production

To use with REAL data:
1. Collect actual NBA boxscore data in the JSON format
2. Train Model V3 on real historical data (see RRMODEL/scripts/nba/ddtd/)
3. Replace mock model with real trained model
4. Validate backtest performance meets ROI targets

## Data Format

Sample game JSON structure:
```json
{
  "gameId": "401591869",
  "gameDate": "2023-10-24",
  "home": {
    "team": "LAL",
    "score": 115,
    "players": [
      {
        "playerId": "lebron_james",
        "name": "LeBron James",
        "stats": {
          "min": 35,
          "pts": 25,
          "reb": 8,
          "ast": 7,
          "stl": 1,
          "blk": 1
        }
      }
    ]
  },
  "away": {
    "team": "GSW",
    "score": 112,
    "players": [...]
  }
}
```
