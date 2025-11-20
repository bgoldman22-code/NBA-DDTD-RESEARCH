#!/usr/bin/env python3
"""
Show all players with 50%+ DD probability for today
"""

import sys
import pandas as pd
import numpy as np
import pickle
import json
import requests
import os
from datetime import datetime

def fetch_odds(api_key):
    """Fetch player props odds from The Odds API"""
    BASE_URL = 'https://api.the-odds-api.com/v4'
    
    # Get today's events
    events_response = requests.get(
        f'{BASE_URL}/sports/basketball_nba/events',
        params={'apiKey': api_key, 'dateFormat': 'iso'}
    )
    events = events_response.json()
    
    odds_data = []
    for event in events:
        event_id = event['id']
        
        # Fetch player props
        odds_response = requests.get(
            f'{BASE_URL}/sports/basketball_nba/events/{event_id}/odds',
            params={
                'apiKey': api_key,
                'regions': 'us',
                'markets': 'player_double_double,player_triple_double',
                'oddsFormat': 'american'
            }
        )
        
        if odds_response.status_code == 200:
            data = odds_response.json()
            if 'bookmakers' in data:
                for bookmaker in data['bookmakers']:
                    for market in bookmaker['markets']:
                        for outcome in market['outcomes']:
                            odds_data.append({
                                'player_name': outcome['description'],
                                'bet_type': 'DD' if market['key'] == 'player_double_double' else 'TD',
                                'odds': outcome['price']
                            })
    
    return pd.DataFrame(odds_data)

def load_historical_data():
    """Load all historical player stats"""
    seasons = ['2023-24', '2024-25', '2025-26']
    all_stats = []
    
    for season in seasons:
        boxscore_dir = f'data/nba/boxscores-raw/{season}'
        if not os.path.exists(boxscore_dir):
            continue
        
        for fname in os.listdir(boxscore_dir):
            if not fname.endswith('.json'):
                continue
            
            with open(f'{boxscore_dir}/{fname}') as f:
                game_data = json.load(f)
                game_date = game_data['gameDate']
                
                for venue in ['home', 'away']:
                    team = game_data[venue]['team']
                    for player in game_data[venue]['players']:
                        stats = player['stats']
                        
                        # Calculate DD/TD
                        cats = []
                        if stats.get('pts', 0) >= 10: cats.append('pts')
                        if stats.get('reb', 0) >= 10: cats.append('reb')
                        if stats.get('ast', 0) >= 10: cats.append('ast')
                        if stats.get('stl', 0) >= 10: cats.append('stl')
                        if stats.get('blk', 0) >= 10: cats.append('blk')
                        
                        all_stats.append({
                            'playerName': player['name'],
                            'team': team,
                            'gameDate': pd.to_datetime(game_date),
                            'minutes': stats.get('min', 0),
                            'points': stats.get('pts', 0),
                            'rebounds': stats.get('reb', 0),
                            'assists': stats.get('ast', 0),
                            'steals': stats.get('stl', 0),
                            'blocks': stats.get('blk', 0),
                            'turnovers': stats.get('to', 0),
                            'fgm': stats.get('fgm', 0),
                            'fga': stats.get('fga', 0),
                            'fg3m': stats.get('fg3m', 0),
                            'fg3a': stats.get('fg3a', 0),
                            'ftm': stats.get('ftm', 0),
                            'fta': stats.get('fta', 0),
                            'dd': 1 if len(cats) >= 2 else 0,
                            'td': 1 if len(cats) >= 3 else 0
                        })
    
    return pd.DataFrame(all_stats)

def calculate_player_features(df, player_name, lookback=20):
    """Calculate features for a player"""
    player_data = df[df['playerName'].str.contains(player_name.split()[0], case=False, na=False)]
    
    if player_data.empty or len(player_data) < 10:
        return None
    
    player_data = player_data.sort_values('gameDate', ascending=False)
    history = player_data.iloc[:lookback]
    
    features = {
        'playerName': player_name,
        'avg_minutes': history['minutes'].mean(),
        'avg_points': history['points'].mean(),
        'avg_rebounds': history['rebounds'].mean(),
        'avg_assists': history['assists'].mean(),
        'avg_steals': history['steals'].mean(),
        'avg_blocks': history['blocks'].mean(),
        'avg_turnovers': history['turnovers'].mean(),
        'fg_pct': history['fgm'].sum() / max(history['fga'].sum(), 1),
        'fg3_pct': history['fg3m'].sum() / max(history['fg3a'].sum(), 1),
        'ft_pct': history['ftm'].sum() / max(history['fta'].sum(), 1),
        'avg_fga': history['fga'].mean(),
        'avg_fta': history['fta'].mean(),
        'dd_rate': history['dd'].mean(),
        'td_rate': history['td'].mean(),
        'l5_minutes': history.iloc[:5]['minutes'].mean(),
        'l5_points': history.iloc[:5]['points'].mean(),
        'l5_rebounds': history.iloc[:5]['rebounds'].mean(),
        'l5_assists': history.iloc[:5]['assists'].mean(),
        'l5_dd_rate': history.iloc[:5]['dd'].mean(),
        'std_points': history['points'].std(),
        'std_rebounds': history['rebounds'].std(),
        'std_assists': history['assists'].std(),
        'min_games_played': len(history),
        'pts_reb': history['points'].mean() + history['rebounds'].mean(),
        'pts_ast': history['points'].mean() + history['assists'].mean(),
        'reb_ast': history['rebounds'].mean() + history['assists'].mean(),
        'total_production': history['points'].mean() + history['rebounds'].mean() + history['assists'].mean(),
        'per_minute_pts': history['points'].mean() / max(history['minutes'].mean(), 1),
        'per_minute_reb': history['rebounds'].mean() / max(history['minutes'].mean(), 1),
        'per_minute_ast': history['assists'].mean() / max(history['minutes'].mean(), 1),
        'proj_minutes': history['minutes'].mean()
    }
    
    return features

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 show_high_prob_players.py <API_KEY>")
        sys.exit(1)
    
    api_key = sys.argv[1]
    
    # Load model
    print("Loading model...")
    with open('models/nba/ddtd/ddtd_model_v3.pkl', 'rb') as f:
        model_data = pickle.load(f)
    
    # Load historical data
    print("Loading historical data...")
    historical_df = load_historical_data()
    print(f"Loaded {len(historical_df)} player-games")
    
    # Fetch odds
    print("Fetching odds...")
    odds_df = fetch_odds(api_key)
    print(f"Found {len(odds_df)} props for {len(odds_df['player_name'].unique())} players\n")
    
    # Generate predictions
    players_to_predict = odds_df['player_name'].unique()
    predictions = []
    
    for player_name in players_to_predict:
        features = calculate_player_features(historical_df, player_name)
        
        if features is None:
            continue
        
        # Create feature vector
        feature_names = model_data['feature_columns']
        X = pd.DataFrame([features])[feature_names].fillna(0)
        
        # Predict
        dd_raw = model_data['dd_model'].predict_proba(X)[0, 1]
        td_raw = model_data['td_model'].predict_proba(X)[0, 1]
        dd_prob = model_data['dd_calibrator'].transform([dd_raw])[0]
        td_prob = model_data['td_calibrator'].transform([td_raw])[0]
        
        # Get best odds
        player_odds = odds_df[odds_df['player_name'] == player_name]
        dd_odds_list = player_odds[player_odds['bet_type'] == 'DD']['odds'].values
        dd_best = max(dd_odds_list) if len(dd_odds_list) > 0 else None
        
        predictions.append({
            'player': player_name,
            'dd_prob': dd_prob,
            'td_prob': td_prob,
            'dd_odds': dd_best,
            'avg_minutes': features['avg_minutes'],
            'l20_dd_rate': features['dd_rate']
        })
    
    # Filter for 50%+ DD probability
    pred_df = pd.DataFrame(predictions)
    high_prob = pred_df[pred_df['dd_prob'] >= 0.50].sort_values('dd_prob', ascending=False)
    
    print("=" * 70)
    print("PLAYERS WITH 50%+ DD PROBABILITY (November 14, 2025)")
    print("=" * 70)
    print()
    
    if high_prob.empty:
        print("No players with 50%+ DD probability found.")
    else:
        for idx, (_, row) in enumerate(high_prob.iterrows(), 1):
            print(f"{idx}. {row['player']}")
            print(f"   Model Probability: {row['dd_prob']:.1%}")
            if row['dd_odds'] and not pd.isna(row['dd_odds']):
                odds = row['dd_odds']
                implied = abs(odds) / (abs(odds) + 100) if odds < 0 else 100 / (odds + 100)
                edge = row['dd_prob'] - implied
                print(f"   Best Odds: {odds:+d} (implied {implied:.1%})")
                print(f"   Edge: {edge:+.1%}")
            else:
                print(f"   Best Odds: No odds available")
            print(f"   Minutes: {row['avg_minutes']:.1f} avg")
            print(f"   L20 DD Rate: {row['l20_dd_rate']:.0%}")
            print()
    
    print(f"Total: {len(high_prob)} players with 50%+ DD probability")

if __name__ == '__main__':
    main()
