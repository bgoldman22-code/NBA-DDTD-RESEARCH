"""
Comprehensive Probability Analysis
Shows ALL player DD/TD probabilities regardless of odds/edge
Used for model calibration validation
"""

import os
import sys
import json
import pickle
import requests
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# API Key
ODDS_API_KEY = os.environ.get('ODDS_API_KEY')
if not ODDS_API_KEY:
    print("❌ ERROR: ODDS_API_KEY environment variable not set")
    sys.exit(1)

def fetch_player_props_odds():
    """Fetch DD/TD odds from The Odds API"""
    events_url = "https://api.the-odds-api.com/v4/sports/basketball_nba/events"
    
    try:
        print("📡 Fetching today's NBA events...")
        events_response = requests.get(events_url, params={'apiKey': ODDS_API_KEY}, timeout=15)
        events_response.raise_for_status()
        events = events_response.json()
        
        # Filter for today
        today = datetime.now().date()
        todays_events = []
        for event in events:
            event_time = datetime.fromisoformat(event['commence_time'].replace('Z', '+00:00'))
            if event_time.date() == today:
                todays_events.append(event)
        
        print(f"   Found {len(todays_events)} events today\n")
        
        all_odds = {'dd': [], 'td': []}
        
        for event in todays_events:
            event_id = event['id']
            home_team = event['home_team']
            away_team = event['away_team']
            game_str = f"{away_team} @ {home_team}"
            
            # Fetch DD props
            try:
                dd_url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/events/{event_id}/odds"
                dd_response = requests.get(dd_url, params={
                    'apiKey': ODDS_API_KEY,
                    'regions': 'us',
                    'markets': 'player_double_double',
                    'oddsFormat': 'american'
                }, timeout=15)
                
                if dd_response.status_code == 200:
                    dd_data = dd_response.json()
                    for bookmaker in dd_data.get('bookmakers', []):
                        for market in bookmaker.get('markets', []):
                            if market['key'] == 'player_double_double':
                                for outcome in market.get('outcomes', []):
                                    # Only collect YES outcomes
                                    if outcome.get('name') != 'Yes':
                                        continue
                                    
                                    all_odds['dd'].append({
                                        'player': outcome['description'],
                                        'dd_odds': outcome['price'],
                                        'game': game_str
                                    })
            except:
                pass
            
            # Fetch TD props
            try:
                td_url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/events/{event_id}/odds"
                td_response = requests.get(td_url, params={
                    'apiKey': ODDS_API_KEY,
                    'regions': 'us',
                    'markets': 'player_triple_double',
                    'oddsFormat': 'american'
                }, timeout=15)
                
                if td_response.status_code == 200:
                    td_data = td_response.json()
                    for bookmaker in td_data.get('bookmakers', []):
                        for market in bookmaker.get('markets', []):
                            if market['key'] == 'player_triple_double':
                                for outcome in market.get('outcomes', []):
                                    # Only collect YES outcomes
                                    if outcome.get('name') != 'Yes':
                                        continue
                                    
                                    all_odds['td'].append({
                                        'player': outcome['description'],
                                        'td_odds': outcome['price'],
                                        'game': game_str
                                    })
            except:
                pass
        
        print(f"✅ Fetched odds for {len(all_odds['dd'])} DD props, {len(all_odds['td'])} TD props\n")
        return all_odds
        
    except Exception as e:
        print(f"❌ Error fetching odds: {e}")
        return {'dd': [], 'td': []}

def parse_boxscores_dir(root_dir):
    """Parse all boxscore JSON files"""
    all_games = []
    
    for season_dir in sorted(root_dir.glob('*')):
        if not season_dir.is_dir():
            continue
        
        for game_file in sorted(season_dir.glob('*.json')):
            try:
                with open(game_file) as f:
                    game_data = json.load(f)
                
                # Skip if missing required keys
                if 'gameId' not in game_data or 'gameDate' not in game_data:
                    continue
                
                game_id = game_data['gameId']
                game_date = game_data['gameDate']
                
                # Process home team players
                if 'home' in game_data and 'players' in game_data['home']:
                    for player in game_data['home']['players']:
                        stats = player['stats']
                        all_games.append({
                            'gameId': game_id,
                            'gameDate': game_date,
                            'player': player['name'],
                            'playerId': player['playerId'],
                            'team': game_data['home']['team'],
                            **stats
                        })
                
                # Process away team players
                if 'away' in game_data and 'players' in game_data['away']:
                    for player in game_data['away']['players']:
                        stats = player['stats']
                        all_games.append({
                            'gameId': game_id,
                            'gameDate': game_date,
                            'player': player['name'],
                            'playerId': player['playerId'],
                            'team': game_data['away']['team'],
                            **stats
                        })
            except Exception as e:
                # Skip problematic files
                continue
    
    return pd.DataFrame(all_games)

def detect_dd(df):
    """Detect double-doubles"""
    if len(df) == 0:
        return pd.Series(dtype=bool)
    
    categories = ['pts', 'reb', 'ast', 'stl', 'blk']
    dd_counts = sum(df[cat] >= 10 for cat in categories)
    return dd_counts >= 2

def detect_td(df):
    """Detect triple-doubles"""
    if len(df) == 0:
        return pd.Series(dtype=bool)
    
    categories = ['pts', 'reb', 'ast', 'stl', 'blk']
    td_counts = sum(df[cat] >= 10 for cat in categories)
    return td_counts >= 3

def calculate_player_features(historical_df, player_name):
    """Calculate features for a single player"""
    player_games = historical_df[historical_df['player'] == player_name].copy()
    
    if len(player_games) == 0:
        return None
    
    player_games = player_games.sort_values('gameDate', ascending=False)
    
    # Season averages
    avg_minutes = player_games['min'].mean()
    avg_points = player_games['pts'].mean()
    avg_rebounds = player_games['reb'].mean()
    avg_assists = player_games['ast'].mean()
    avg_steals = player_games['stl'].mean()
    avg_blocks = player_games['blk'].mean()
    
    # Per-minute rates
    total_minutes = player_games['min'].sum()
    if total_minutes > 0:
        pts_per_min = player_games['pts'].sum() / total_minutes
        reb_per_min = player_games['reb'].sum() / total_minutes
        ast_per_min = player_games['ast'].sum() / total_minutes
        stl_per_min = player_games['stl'].sum() / total_minutes
        blk_per_min = player_games['blk'].sum() / total_minutes
    else:
        pts_per_min = reb_per_min = ast_per_min = stl_per_min = blk_per_min = 0
    
    # Recent form
    l5 = player_games.head(5)
    l10 = player_games.head(10)
    l20 = player_games.head(20)
    
    features = {
        'avg_minutes': avg_minutes,
        'avg_points': avg_points,
        'avg_rebounds': avg_rebounds,
        'avg_assists': avg_assists,
        'avg_steals': avg_steals,
        'avg_blocks': avg_blocks,
        'pts_per_min': pts_per_min,
        'reb_per_min': reb_per_min,
        'ast_per_min': ast_per_min,
        'stl_per_min': stl_per_min,
        'blk_per_min': blk_per_min,
        'l5_dd_rate': detect_dd(l5).mean() if len(l5) > 0 else 0,
        'l10_dd_rate': detect_dd(l10).mean() if len(l10) > 0 else 0,
        'l20_dd_rate': detect_dd(l20).mean() if len(l20) > 0 else 0,
        'l5_td_rate': detect_td(l5).mean() if len(l5) > 0 else 0,
        'l10_td_rate': detect_td(l10).mean() if len(l10) > 0 else 0,
        'l20_td_rate': detect_td(l20).mean() if len(l20) > 0 else 0,
        'games_played': len(player_games),
        'l5_avg_pts': l5['pts'].mean() if len(l5) > 0 else 0,
        'l5_avg_reb': l5['reb'].mean() if len(l5) > 0 else 0,
        'l5_avg_ast': l5['ast'].mean() if len(l5) > 0 else 0,
        'l10_avg_pts': l10['pts'].mean() if len(l10) > 0 else 0,
        'l10_avg_reb': l10['reb'].mean() if len(l10) > 0 else 0,
        'l10_avg_ast': l10['ast'].mean() if len(l10) > 0 else 0,
        'l20_avg_pts': l20['pts'].mean() if len(l20) > 0 else 0,
        'l20_avg_reb': l20['reb'].mean() if len(l20) > 0 else 0,
        'l20_avg_ast': l20['ast'].mean() if len(l20) > 0 else 0,
        'l5_avg_stl': l5['stl'].mean() if len(l5) > 0 else 0,
        'l10_avg_stl': l10['stl'].mean() if len(l10) > 0 else 0,
        'l5_avg_blk': l5['blk'].mean() if len(l5) > 0 else 0,
        'l10_avg_blk': l10['blk'].mean() if len(l10) > 0 else 0,
    }
    
    return features

def main():
    print("="*80)
    print("🔍 COMPREHENSIVE PROBABILITY ANALYSIS")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d')}")
    print("="*80 + "\n")
    
    # Load model
    print("🤖 Loading Model...")
    model_path = Path('models/nba/ddtd/ddtd_model_v3.pkl')
    with open(model_path, 'rb') as f:
        model_dict = pickle.load(f)
    
    dd_model = model_dict['dd_model']
    dd_calibrator = model_dict['dd_calibrator']
    td_model = model_dict['td_model']
    td_calibrator = model_dict['td_calibrator']
    print("✅ Model loaded\n")
    
    # Load historical data
    print("📥 Loading historical data...")
    historical_df = parse_boxscores_dir(Path('data/nba/boxscores-raw'))
    print(f"✅ Loaded {len(historical_df)} player-games\n")
    
    # Fetch odds
    odds_data = fetch_player_props_odds()
    
    # Merge DD and TD odds
    dd_df = pd.DataFrame(odds_data['dd'])
    td_df = pd.DataFrame(odds_data['td'])
    
    # Get all unique players
    all_players = set()
    if len(dd_df) > 0:
        all_players.update(dd_df['player'].unique())
    if len(td_df) > 0:
        all_players.update(td_df['player'].unique())
    
    print(f"🎯 Generating predictions for {len(all_players)} players...\n")
    
    # Generate predictions
    all_predictions = []
    
    for player_name in all_players:
        features = calculate_player_features(historical_df, player_name)
        if features is None:
            continue
        
        # Feature array
        feature_cols = [
            'avg_minutes', 'avg_points', 'avg_rebounds', 'avg_assists', 'avg_steals', 'avg_blocks',
            'pts_per_min', 'reb_per_min', 'ast_per_min', 'stl_per_min', 'blk_per_min',
            'l5_dd_rate', 'l10_dd_rate', 'l20_dd_rate',
            'l5_td_rate', 'l10_td_rate', 'l20_td_rate',
            'games_played',
            'l5_avg_pts', 'l5_avg_reb', 'l5_avg_ast',
            'l10_avg_pts', 'l10_avg_reb', 'l10_avg_ast',
            'l20_avg_pts', 'l20_avg_reb', 'l20_avg_ast',
            'l5_avg_stl', 'l10_avg_stl', 'l5_avg_blk', 'l10_avg_blk'
        ]
        
        X = np.array([[features[col] for col in feature_cols]])
        
        # Predict
        dd_raw = dd_model.predict_proba(X)[0, 1]
        dd_prob = dd_calibrator.predict(np.array([dd_raw]).reshape(-1, 1))[0]
        
        td_raw = td_model.predict_proba(X)[0, 1]
        td_prob = td_calibrator.predict(np.array([td_raw]).reshape(-1, 1))[0]
        
        # Get odds
        player_dd = dd_df[dd_df['player'] == player_name]
        player_td = td_df[td_df['player'] == player_name]
        
        all_predictions.append({
            'player': player_name,
            'dd_prob': dd_prob,
            'td_prob': td_prob,
            'dd_odds': player_dd['dd_odds'].max() if len(player_dd) > 0 else None,
            'td_odds': player_td['td_odds'].max() if len(player_td) > 0 else None,
            'game': player_dd['game'].iloc[0] if len(player_dd) > 0 else player_td['game'].iloc[0] if len(player_td) > 0 else 'Unknown',
            'avg_minutes': features['avg_minutes'],
            'l20_dd_rate': features['l20_dd_rate'],
            'l20_td_rate': features['l20_td_rate']
        })
    
    pred_df = pd.DataFrame(all_predictions)
    
    # Show high DD probabilities
    print("\n" + "="*80)
    print("🎯 ALL PLAYERS WITH >40% DD PROBABILITY")
    print("="*80)
    
    high_dd = pred_df[pred_df['dd_prob'] >= 0.40].copy()
    high_dd = high_dd.sort_values('dd_prob', ascending=False)
    
    for _, row in high_dd.iterrows():
        if pd.notna(row['dd_odds']):
            if row['dd_odds'] > 0:
                implied = 1 / (row['dd_odds']/100 + 1)
            else:
                implied = abs(row['dd_odds'])/100 / (abs(row['dd_odds'])/100 + 1)
            edge = row['dd_prob'] - implied
        else:
            implied = None
            edge = None
        
        print(f"\n{row['player']}")
        print(f"  Model Prob: {row['dd_prob']*100:.1f}%")
        print(f"  Best Odds: {int(row['dd_odds']) if pd.notna(row['dd_odds']) else 'N/A'}")
        if implied is not None:
            print(f"  Implied Prob: {implied*100:.1f}%")
            print(f"  Edge: {edge*100:.1f}%")
        print(f"  Avg Minutes: {row['avg_minutes']:.1f}")
        print(f"  L20 DD Rate: {row['l20_dd_rate']*100:.1f}%")
        print(f"  Game: {row['game']}")
    
    print(f"\n{'='*80}")
    print(f"Total: {len(high_dd)} players")
    print(f"{'='*80}")
    
    # Show high TD probabilities
    print("\n" + "="*80)
    print("🎰 ALL PLAYERS WITH >20% TD PROBABILITY")
    print("="*80)
    
    high_td = pred_df[pred_df['td_prob'] >= 0.20].copy()
    high_td = high_td.sort_values('td_prob', ascending=False)
    
    for _, row in high_td.iterrows():
        if pd.notna(row['td_odds']):
            if row['td_odds'] > 0:
                implied = 1 / (row['td_odds']/100 + 1)
            else:
                implied = abs(row['td_odds'])/100 / (abs(row['td_odds'])/100 + 1)
            edge = row['td_prob'] - implied
        else:
            implied = None
            edge = None
        
        print(f"\n{row['player']}")
        print(f"  Model Prob: {row['td_prob']*100:.1f}%")
        print(f"  Best Odds: {int(row['td_odds']) if pd.notna(row['td_odds']) else 'N/A'}")
        if implied is not None:
            print(f"  Implied Prob: {implied*100:.1f}%")
            print(f"  Edge: {edge*100:.1f}%")
        print(f"  Avg Minutes: {row['avg_minutes']:.1f}")
        print(f"  L20 TD Rate: {row['l20_td_rate']*100:.1f}%")
        print(f"  Game: {row['game']}")
    
    print(f"\n{'='*80}")
    print(f"Total: {len(high_td)} players")
    print(f"{'='*80}")
    
    # Calibration analysis
    print("\n" + "="*80)
    print("📊 CALIBRATION ANALYSIS")
    print("="*80)
    
    dd_with_odds = pred_df[pred_df['dd_odds'].notna()].copy()
    dd_with_odds['implied'] = dd_with_odds['dd_odds'].apply(
        lambda x: (1 / (x/100 + 1)) if x > 0 else (abs(x)/100) / (abs(x)/100 + 1)
    )
    dd_with_odds['diff'] = dd_with_odds['dd_prob'] - dd_with_odds['implied']
    
    print(f"\nDD Predictions (n={len(dd_with_odds)}):")
    print(f"  Mean model prob: {dd_with_odds['dd_prob'].mean()*100:.1f}%")
    print(f"  Mean implied prob: {dd_with_odds['implied'].mean()*100:.1f}%")
    print(f"  Mean difference: {dd_with_odds['diff'].mean()*100:.1f}%")
    print(f"  Median difference: {dd_with_odds['diff'].median()*100:.1f}%")
    print(f"  Std dev difference: {dd_with_odds['diff'].std()*100:.1f}%")
    
    td_with_odds = pred_df[pred_df['td_odds'].notna()].copy()
    if len(td_with_odds) > 0:
        td_with_odds['implied'] = td_with_odds['td_odds'].apply(
            lambda x: (1 / (x/100 + 1)) if x > 0 else (abs(x)/100) / (abs(x)/100 + 1)
        )
        td_with_odds['diff'] = td_with_odds['td_prob'] - td_with_odds['implied']
        
        print(f"\nTD Predictions (n={len(td_with_odds)}):")
        print(f"  Mean model prob: {td_with_odds['td_prob'].mean()*100:.1f}%")
        print(f"  Mean implied prob: {td_with_odds['implied'].mean()*100:.1f}%")
        print(f"  Mean difference: {td_with_odds['diff'].mean()*100:.1f}%")
        print(f"  Median difference: {td_with_odds['diff'].median()*100:.1f}%")
        print(f"  Std dev difference: {td_with_odds['diff'].std()*100:.1f}%")
    
    print("\n" + "="*80)

if __name__ == '__main__':
    main()
