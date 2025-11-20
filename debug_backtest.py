"""
Debug version of backtest to see why no results
"""

import sys
import json
import pickle
from pathlib import Path
from datetime import datetime
import pandas as pd

# Load model and data
MODEL_PATH = Path("models/nba/ddtd/ddtd_model_v3.pkl")
DATA_PATH = Path("data/nba/boxscores-raw/2023-24")

print("Loading model...")
with open(MODEL_PATH, 'rb') as f:
    model_data = pickle.load(f)

print(f"Model features: {len(model_data['feature_columns'])}")

# Load some games
print("\nLoading games...")
games = []
for file_path in sorted(list(DATA_PATH.glob('*.json')))[:10]:
    with open(file_path) as f:
        game = json.load(f)
    games.append(game)
    
print(f"Loaded {len(games)} games")

# Extract player records
records = []
for game in games:
    game_date = game.get('gameDate', '')
    for team_key in ['home', 'away']:
        for player in game.get(team_key, {}).get('players', []):
            stats = player.get('stats', {})
            if stats.get('min', 0) > 0:
                pts, reb, ast = stats.get('pts', 0), stats.get('reb', 0), stats.get('ast', 0)
                records.append({
                    'gameDate': game_date,
                    'playerId': player.get('playerId', ''),
                    'playerName': player.get('name', ''),
                    'minutes': stats.get('min', 0),
                    'points': pts,
                    'rebounds': reb,
                    'assists': ast,
                    'dd': int(sum([pts >= 10, reb >= 10, ast >= 10]) >= 2),
                    'td': int(pts >= 10 and reb >= 10 and ast >= 10)
                })

df = pd.DataFrame(records)
print(f"\nExtracted {len(df)} player-games")
print(f"Date range: {df['gameDate'].min()} to {df['gameDate'].max()}")
print(f"Unique players: {df['playerId'].nunique()}")
print(f"DD rate: {df['dd'].mean()*100:.1f}%")
print(f"TD rate: {df['td'].mean()*100:.1f}%")

# Check if we have enough history
print("\nPlayer game counts:")
player_counts = df.groupby('playerId').size().sort_values(ascending=False)
print(player_counts.head(10))

print("\n✅ Data structure looks good!")
print("Issue: Backtest likely needs more historical games before start date")
print("Solution: Start backtest later in season (e.g., 2024-01-01) after players have 45+ games")
