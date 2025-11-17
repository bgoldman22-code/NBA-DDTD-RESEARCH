"""
Generate Daily NBA DD/TD Picks for RRMODEL
Reuses run_today.py logic but outputs to JSON format for web consumption
Designed to run via GitHub Actions daily at 10 AM
"""

import os
import sys
import json
import pickle
import requests
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta, timezone

# API Key - provided via environment variable
ODDS_API_KEY = os.environ.get('ODDS_API_KEY')
if not ODDS_API_KEY:
    print("❌ ERROR: ODDS_API_KEY environment variable not set")
    sys.exit(1)

def fetch_todays_games():
    """Fetch today's NBA schedule from ESPN"""
    date_str = datetime.now().strftime('%Y%m%d')
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        games = []
        for event in data.get('events', []):
            competition = event.get('competitions', [{}])[0]
            competitors = competition.get('competitors', [])
            
            home = next((c for c in competitors if c.get('homeAway') == 'home'), {})
            away = next((c for c in competitors if c.get('homeAway') == 'away'), {})
            
            games.append({
                'gameId': event.get('id'),
                'homeTeam': home.get('team', {}).get('abbreviation', ''),
                'awayTeam': away.get('team', {}).get('abbreviation', ''),
                'time': event.get('date', '')
            })
        
        return games
    except Exception as e:
        print(f"⚠️  Error fetching schedule: {e}")
        return []

def fetch_player_props_odds():
    """Fetch DD/TD odds from The Odds API"""
    events_url = "https://api.the-odds-api.com/v4/sports/basketball_nba/events"
    
    try:
        print("📡 Fetching today's NBA events...")
        events_response = requests.get(events_url, params={'apiKey': ODDS_API_KEY}, timeout=15)
        events_response.raise_for_status()
        events = events_response.json()
        
        remaining = events_response.headers.get('x-requests-remaining', 'unknown')
        print(f"   API requests remaining: {remaining}")
        print(f"   Found {len(events)} events today\n")
        
        if not events:
            print("⚠️  No events found for today")
            return pd.DataFrame()
        
        odds_data = []
        
        for event in events:
            event_id = event.get('id')
            away_team = event.get('away_team')
            home_team = event.get('home_team')
            
            print(f"   Fetching props for {away_team} @ {home_team}...")
            
            odds_url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/events/{event_id}/odds"
            odds_params = {
                'apiKey': ODDS_API_KEY,
                'regions': 'us',
                'markets': 'player_double_double,player_triple_double',
                'oddsFormat': 'american'
            }
            
            try:
                odds_response = requests.get(odds_url, params=odds_params, timeout=15)
                odds_response.raise_for_status()
                event_odds = odds_response.json()
                
                for bookmaker in event_odds.get('bookmakers', []):
                    for market in bookmaker.get('markets', []):
                        market_key = market.get('key')
                        if market_key in ['player_double_double', 'player_triple_double']:
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
            except Exception as e:
                print(f"      ⚠️  Error fetching odds for event {event_id}: {e}")
                continue
        
        return pd.DataFrame(odds_data)
    
    except Exception as e:
        print(f"⚠️  Error fetching events: {e}")
        return pd.DataFrame()

def load_historical_data():
    """Load historical data for feature calculation"""
    data_dir = Path('data/nba/boxscores-raw')
    
    records = []
    seasons = ['2023-24', '2024-25']
    
    print("📥 Loading historical data...")
    for season in seasons:
        season_dir = data_dir / season
        if season_dir.exists():
            files = list(season_dir.glob('*.json'))
            print(f"   {season}: {len(files)} games")
            
            for file_path in files:
                try:
                    with open(file_path) as f:
                        game = json.load(f)
                    
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
                                    'steals': stats.get('stl', 0),
                                    'blocks': stats.get('blk', 0),
                                    'turnovers': stats.get('tov', 0),
                                    'fgm': stats.get('fgm', 0),
                                    'fga': stats.get('fga', 0),
                                    'fg3m': stats.get('fg3m', 0),
                                    'fg3a': stats.get('fg3a', 0),
                                    'ftm': stats.get('ftm', 0),
                                    'fta': stats.get('fta', 0),
                                    'dd': int(sum([pts >= 10, reb >= 10, ast >= 10]) >= 2),
                                    'td': int(pts >= 10 and reb >= 10 and ast >= 10)
                                })
                except:
                    continue
    
    df = pd.DataFrame(records)
    df['gameDate'] = pd.to_datetime(df['gameDate'])
    print(f"✅ Loaded {len(df)} player-games, {df['playerId'].nunique()} players\n")
    
    return df

def calculate_player_features(df, player_name, lookback=20):
    """Calculate features for a specific player"""
    player_data = df[df['playerName'] == player_name]
    
    if player_data.empty:
        player_data = df[df['playerName'].str.lower() == player_name.lower()]
    
    if player_data.empty:
        player_data = df[df['playerName'].str.contains(player_name.split()[0], case=False, na=False)]
    
    if player_data.empty:
        return None
    
    player_data = player_data.sort_values('gameDate', ascending=False)
    
    if len(player_data) < 10:
        return None
    
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

def odds_to_implied_prob(odds):
    """Convert American odds to implied probability"""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def main():
    """Generate picks and save to JSON"""
    today_str = datetime.now().strftime('%Y-%m-%d')
    generated_at = datetime.now(timezone.utc).isoformat()
    
    print("=" * 60)
    print("🏀 NBA DD/TD PICKS GENERATOR FOR RRMODEL")
    print(f"📅 {today_str}")
    print("=" * 60)
    print()
    
    # Load model
    print("🤖 Loading Model V3...")
    with open('models/nba/ddtd/ddtd_model_v3.pkl', 'rb') as f:
        model_data = pickle.load(f)
    
    with open('models/nba/ddtd/acceptance_gates_v3.json') as f:
        gates = json.load(f)
    
    print(f"✅ Model loaded")
    print(f"✅ Gates: DD {gates['dd']['min_prob']*100:.0f}%+ @ {gates['dd']['min_minutes']} min")
    print(f"   TD Core: {gates['td']['core']['min_prob']*100:.1f}%+, {gates['td']['core']['min_minutes']} min, +{gates['td']['core']['min_odds']} odds")
    print(f"   TD Lotto: {gates['td']['lotto']['min_prob']*100:.1f}%+, {gates['td']['lotto']['min_minutes']} min, +{gates['td']['lotto']['min_odds']} odds\n")
    
    # Fetch odds
    odds_df = fetch_player_props_odds()
    
    if odds_df.empty:
        print("⚠️  No odds data available. Exiting.")
        # Create empty output (ensures JSON always exists, even with no picks)
        output = {
            'date': today_str,
            'generated_at': generated_at,
            'model_version': 'v3',
            'picks': {'dd': [], 'td': []},
            'summary': {
                'total_dd': 0,
                'total_td': 0,
                'avg_edge_dd': 0,
                'avg_edge_td': 0
            },
            'error': 'No odds data available for today'
        }
        
        output_path = Path('data/nba/ddtd_today_picks.json')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"✅ Empty picks file saved to {output_path}")
        return
    
    print(f"✅ Fetched odds for {len(odds_df)} props\n")
    
    # Load historical data
    historical_df = load_historical_data()
    
    # Generate predictions
    players_to_predict = odds_df['player_name'].unique()
    print(f"🎯 Generating predictions for {len(players_to_predict)} players...\n")
    
    predictions = []
    
    for player_name in players_to_predict:
        features = calculate_player_features(historical_df, player_name)
        
        if features is None:
            continue
        
        feature_names = model_data['feature_columns']
        X = pd.DataFrame([features])[feature_names].fillna(0)
        
        dd_raw = model_data['dd_model'].predict_proba(X)[0, 1]
        td_raw = model_data['td_model'].predict_proba(X)[0, 1]
        dd_prob = model_data['dd_calibrator'].transform([dd_raw])[0]
        td_prob = model_data['td_calibrator'].transform([td_raw])[0]
        
        player_odds = odds_df[odds_df['player_name'] == player_name]
        dd_odds_list = player_odds[player_odds['bet_type'] == 'DD']['odds'].values
        td_odds_list = player_odds[player_odds['bet_type'] == 'TD']['odds'].values
        
        dd_best = max(dd_odds_list) if len(dd_odds_list) > 0 else None
        td_best = max(td_odds_list) if len(td_odds_list) > 0 else None
        
        # Get game info
        game_info = player_odds.iloc[0]['game'] if not player_odds.empty else ''
        
        predictions.append({
            'player': player_name,
            'dd_prob': dd_prob,
            'td_prob': td_prob,
            'dd_odds': dd_best,
            'td_odds': td_best,
            'avg_minutes': features['avg_minutes'],
            'l20_dd_rate': features['dd_rate'],
            'l20_td_rate': features['td_rate'],
            'game': game_info
        })
    
    pred_df = pd.DataFrame(predictions)
    
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
    
    # Format output for web consumption
    dd_picks_list = []
    for _, pick in dd_picks.iterrows():
        dd_picks_list.append({
            'player': pick['player'],
            'model_prob': round(float(pick['dd_prob']), 4),
            'best_odds': int(pick['dd_odds']),
            'implied_prob': round(float(pick['implied_prob']), 4),
            'edge': round(float(pick['edge']), 4),
            'avg_minutes': round(float(pick['avg_minutes']), 1),
            'l20_dd_rate': round(float(pick['l20_dd_rate']), 3),
            'game': pick['game']
        })
    
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
    
    # Create output JSON
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
    
    # Save to file (always writes JSON, even if empty picks)
    output_path = Path('data/nba/ddtd_today_picks.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print("=" * 60)
    print(f"✅ Generated {len(dd_picks_list)} DD picks, {len(td_picks_list)} TD picks")
    if td_core_count > 0:
        print(f"   📊 TD Core: {td_core_count} (high-confidence)")
    if td_lotto_count > 0:
        print(f"   🎰 TD Lotto: {td_lotto_count} (longshot value)")
    print(f"✅ Saved to {output_path}")
    print("=" * 60)

if __name__ == '__main__':
    main()
