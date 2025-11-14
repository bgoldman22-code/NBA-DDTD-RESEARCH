#!/usr/bin/env python3
"""
Setup Test Environment for DD/TD Pipeline
==========================================
Creates sample data and model files for testing the pipeline.

Since we don't have actual player-level boxscore data in the expected format,
this script generates:
1. Sample game data (JSON files in data/nba/boxscores-raw/)
2. Mock trained model (ddtd_model_v3.pkl)
3. Acceptance gates configuration

Author: Brent Goldman
Date: November 12, 2025
"""

import json
import pickle
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
import random

# Paths
BASE_PATH = Path(__file__).parent.parent
DATA_PATH = BASE_PATH / "data/nba/boxscores-raw"
MODEL_PATH = BASE_PATH / "models/nba/ddtd"


# Sample player names and IDs
PLAYERS = [
    ("LeBron James", "lebron_james", "LAL", [25, 8, 7, 1.2, 0.6]),  # PTS, REB, AST, STL, BLK
    ("Anthony Davis", "anthony_davis", "LAL", [24, 12, 3, 1.3, 2.3]),
    ("Stephen Curry", "stephen_curry", "GSW", [28, 5, 6, 1.5, 0.2]),
    ("Giannis Antetokounmpo", "giannis", "MIL", [30, 11, 5, 1.2, 1.5]),
    ("Nikola Jokic", "jokic", "DEN", [26, 12, 9, 1.3, 0.9]),
    ("Luka Doncic", "luka", "DAL", [28, 9, 8, 1.4, 0.5]),
    ("Joel Embiid", "embiid", "PHI", [33, 10, 4, 1.0, 1.7]),
    ("Jayson Tatum", "tatum", "BOS", [27, 8, 5, 1.1, 0.7]),
    ("Kevin Durant", "durant", "PHX", [28, 7, 5, 0.9, 1.3]),
    ("Damian Lillard", "lillard", "MIL", [26, 4, 7, 0.9, 0.3]),
    ("Domantas Sabonis", "sabonis", "SAC", [19, 13, 8, 1.0, 0.5]),
    ("Russell Westbrook", "westbrook", "LAC", [15, 5, 7, 1.3, 0.4]),
    ("Julius Randle", "randle", "NYK", [24, 10, 5, 0.7, 0.3]),
    ("Draymond Green", "green", "GSW", [9, 8, 7, 1.2, 0.8]),
    ("Ben Simmons", "simmons", "BKN", [7, 7, 6, 1.5, 0.8]),
]

TEAMS = ["LAL", "GSW", "MIL", "DEN", "DAL", "PHI", "BOS", "PHX", "SAC", "LAC",
         "NYK", "BKN", "MIA", "CLE", "TOR", "ATL", "CHI", "ORL", "IND", "WAS"]


def generate_player_game_stats(base_stats, minutes=32):
    """Generate realistic game stats with variance."""
    pts_mean, reb_mean, ast_mean, stl_mean, blk_mean = base_stats
    
    # Scale by minutes (base is ~32 min)
    scale = minutes / 32.0
    
    # Add variance
    pts = max(0, int(np.random.normal(pts_mean * scale, pts_mean * 0.25)))
    reb = max(0, int(np.random.normal(reb_mean * scale, reb_mean * 0.25)))
    ast = max(0, int(np.random.normal(ast_mean * scale, ast_mean * 0.25)))
    stl = max(0, int(np.random.poisson(stl_mean * scale)))
    blk = max(0, int(np.random.poisson(blk_mean * scale)))
    
    return {
        'min': minutes,
        'pts': pts,
        'reb': reb,
        'ast': ast,
        'stl': stl,
        'blk': blk,
        'fgm': int(pts * 0.35),
        'fga': int(pts * 0.75),
        'fg3m': int(pts * 0.12),
        'fg3a': int(pts * 0.35),
        'ftm': int(pts * 0.20),
        'fta': int(pts * 0.25),
        'oreb': int(reb * 0.3),
        'dreb': int(reb * 0.7),
        'tov': max(0, int(np.random.normal(2.5, 1.2))),
        'pf': max(0, int(np.random.normal(2.0, 1.0))),
    }


def generate_game_data(game_id, game_date, home_team, away_team):
    """Generate a complete game with player stats."""
    home_score = random.randint(95, 125)
    away_score = random.randint(95, 125)
    pace = random.randint(95, 110)
    
    game_data = {
        'gameId': game_id,
        'gameDate': game_date.strftime('%Y-%m-%d'),
        'home': {
            'team': home_team,
            'score': home_score,
            'players': []
        },
        'away': {
            'team': away_team,
            'score': away_score,
            'players': []
        },
        'pace': pace
    }
    
    # Add players from each team
    for team_key in ['home', 'away']:
        team = game_data[team_key]['team']
        
        # Get players from this team
        team_players = [p for p in PLAYERS if p[2] == team]
        
        # If team has no preset players, use random players
        if not team_players:
            team_players = random.sample(PLAYERS, min(5, len(PLAYERS)))
        
        for player_name, player_id, _, base_stats in team_players:
            # Randomize minutes
            minutes = random.randint(20, 38)
            
            stats = generate_player_game_stats(base_stats, minutes)
            
            game_data[team_key]['players'].append({
                'playerId': player_id,
                'name': player_name,
                'stats': stats
            })
        
        # Add a few bench players
        for i in range(3):
            bench_stats = [8, 4, 2, 0.5, 0.3]  # Bench player averages
            minutes = random.randint(10, 25)
            stats = generate_player_game_stats(bench_stats, minutes)
            
            game_data[team_key]['players'].append({
                'playerId': f'{team.lower()}_bench_{i}',
                'name': f'{team} Bench Player {i+1}',
                'stats': stats
            })
    
    return game_data


def create_sample_season_data(season="2023-24", num_games=100):
    """Create sample game data for a season."""
    print(f"Generating {num_games} sample games for {season}...")
    
    season_path = DATA_PATH / season
    season_path.mkdir(parents=True, exist_ok=True)
    
    start_date = datetime(2023, 10, 24) if season == "2023-24" else datetime(2024, 10, 22)
    
    for i in range(num_games):
        game_date = start_date + timedelta(days=i * 2)  # Games every 2 days
        game_id = f"40159{1000 + i}"
        
        home_team = random.choice(TEAMS)
        away_team = random.choice([t for t in TEAMS if t != home_team])
        
        game_data = generate_game_data(game_id, game_date, home_team, away_team)
        
        output_file = season_path / f"{game_id}.json"
        with open(output_file, 'w') as f:
            json.dump(game_data, f, indent=2)
    
    print(f"✅ Created {num_games} games in {season_path}")


def create_mock_model():
    """Create a mock trained model."""
    print("\nCreating mock trained model...")
    
    # Feature columns (38 features from V3)
    feature_columns = [
        'pts_l40', 'reb_l40', 'ast_l40', 'stl_l40', 'blk_l40',
        'minutes_l40', 'dd_rate_l40', 'td_rate_l40',
        'pts_l10', 'reb_l10', 'ast_l10', 'stl_l10', 'blk_l10',
        'minutes_l10', 'dd_rate_l10', 'td_rate_l10',
        'pts_l5', 'reb_l5', 'ast_l5', 'dd_rate_l5', 'td_rate_l5',
        'pts_trend', 'reb_trend', 'ast_trend', 'dd_trend', 'td_trend',
        'pts_std_l40', 'reb_std_l40', 'ast_std_l40',
        'minutes', 'pace', 'is_home', 'score_diff',
        'opp_allows_pts', 'opp_allows_reb', 'opp_allows_ast',
        'opp_allows_dd_rate', 'opp_allows_td_rate'
    ]
    
    # Create simple models
    dd_model = GradientBoostingClassifier(n_estimators=50, max_depth=3, random_state=42)
    td_model = GradientBoostingClassifier(n_estimators=50, max_depth=3, random_state=42)
    
    # Generate synthetic training data
    n_samples = 1000
    X_train = np.random.randn(n_samples, len(feature_columns))
    
    # DD: ~15% positive rate
    y_dd = (X_train[:, 0] + X_train[:, 6] * 2 + np.random.randn(n_samples) * 0.5 > 0.5).astype(int)
    
    # TD: ~0.5% positive rate
    y_td = (X_train[:, 0] + X_train[:, 7] * 5 + np.random.randn(n_samples) * 2 > 2.0).astype(int)
    
    # Train models
    dd_model.fit(X_train, y_dd)
    td_model.fit(X_train, y_td)
    
    # Create calibrators
    dd_calibrator = IsotonicRegression(out_of_bounds='clip')
    td_calibrator = IsotonicRegression(out_of_bounds='clip')
    
    dd_probs = dd_model.predict_proba(X_train)[:, 1]
    td_probs = td_model.predict_proba(X_train)[:, 1]
    
    dd_calibrator.fit(dd_probs, y_dd)
    td_calibrator.fit(td_probs, y_td)
    
    # Save model
    MODEL_PATH.mkdir(parents=True, exist_ok=True)
    
    model_data = {
        'dd_model': dd_model,
        'td_model': td_model,
        'dd_calibrator': dd_calibrator,
        'td_calibrator': td_calibrator,
        'feature_columns': feature_columns,
        'trained_date': datetime.now().isoformat(),
        'note': 'This is a MOCK model for testing purposes only'
    }
    
    model_file = MODEL_PATH / "ddtd_model_v3.pkl"
    with open(model_file, 'wb') as f:
        pickle.dump(model_data, f)
    
    print(f"✅ Mock model saved to {model_file}")


def create_acceptance_gates():
    """Create acceptance gates configuration."""
    print("\nCreating acceptance gates...")
    
    gates = {
        "dd": {
            "min_edge": 0.10,
            "min_prob": 0.20,
            "min_minutes": 28,
            "max_score_diff": 15
        },
        "td": {
            "min_edge": 0.18,
            "min_prob": 0.03,
            "min_minutes": 32,
            "min_pace": 100,
            "min_odds": 800,
            "max_odds": 2000
        }
    }
    
    gates_file = MODEL_PATH / "acceptance_gates_v3.json"
    with open(gates_file, 'w') as f:
        json.dump(gates, f, indent=2)
    
    print(f"✅ Acceptance gates saved to {gates_file}")


def create_readme():
    """Create README for test environment."""
    readme_content = """# Test Environment Setup

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
"""
    
    readme_file = BASE_PATH / "TEST_ENVIRONMENT_README.md"
    with open(readme_file, 'w') as f:
        f.write(readme_content)
    
    print(f"✅ README saved to {readme_file}")


def main():
    """Setup complete test environment."""
    print("\n" + "="*60)
    print("🏀 Setting Up NBA DD/TD Test Environment")
    print("="*60 + "\n")
    
    print("⚠️  This will create SAMPLE/MOCK DATA for testing")
    print("    NOT for production use!\n")
    
    # Create sample data
    create_sample_season_data("2023-24", num_games=100)
    create_sample_season_data("2024-25", num_games=100)
    
    # Create mock model
    create_mock_model()
    
    # Create gates
    create_acceptance_gates()
    
    # Create README
    create_readme()
    
    print("\n" + "="*60)
    print("✅ Test Environment Setup Complete!")
    print("="*60 + "\n")
    
    print("Next steps:")
    print("1. Review TEST_ENVIRONMENT_README.md")
    print("2. Test scripts with: python3 ddtd/backtest_v3.py")
    print("3. Replace with real data for production")
    print()


if __name__ == "__main__":
    main()
