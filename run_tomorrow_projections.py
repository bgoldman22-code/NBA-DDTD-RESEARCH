"""
Generate DD/TD projections for tomorrow (no odds required)
"""
import pickle
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import requests
import sys

def load_historical_data():
    """Load all historical boxscore data with all stats"""
    base_dir = Path('data/nba/boxscores-raw')
    all_data = []
    
    for season_dir in base_dir.iterdir():
        if season_dir.is_dir():
            for game_file in season_dir.glob('*.json'):
                with open(game_file) as f:
                    game = json.load(f)
                    
                    for side in ['home', 'away']:
                        team_data = game.get(side, {})
                        for player in team_data.get('players', []):
                            stats = player.get('stats', {})
                            
                            # Calculate DD/TD
                            stat_cats = [
                                stats.get('pts', 0),
                                stats.get('reb', 0),
                                stats.get('ast', 0),
                                stats.get('stl', 0),
                                stats.get('blk', 0)
                            ]
                            double_digits = sum(1 for x in stat_cats if x >= 10)
                            dd = 1 if double_digits >= 2 else 0
                            td = 1 if double_digits >= 3 else 0
                            
                            all_data.append({
                                'date': game['gameDate'],
                                'player_name': player['name'],
                                'player_id': player['playerId'],
                                'team': team_data['team'],
                                'minutes': stats.get('min', 0),
                                'points': stats.get('pts', 0),
                                'rebounds': stats.get('reb', 0),
                                'assists': stats.get('ast', 0),
                                'steals': stats.get('stl', 0),
                                'blocks': stats.get('blk', 0),
                                'turnovers': stats.get('tov', 0),
                                'fgm': stats.get('fgm', 0),
                                'fga': stats.get('fga', 0),
                                'fg3m': stats.get('fg3m', 0),
                                'fg3a': stats.get('fg3a', 0),
                                'ftm': stats.get('ftm', 0),
                                'fta': stats.get('fta', 0),
                                'double_double': dd,
                                'triple_double': td
                            })
    
    df = pd.DataFrame(all_data)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    return df

def calculate_player_features(historical_df, player_name, as_of_date=None):
    """Calculate rolling features for a player - matches train_model_v3.py"""
    if as_of_date is None:
        as_of_date = datetime.now()
    
    player_data = historical_df[
        (historical_df['player_name'] == player_name) &
        (historical_df['date'] < as_of_date)
    ].copy()
    
    if len(player_data) < 10:
        return None
    
    # Get last 20 games
    history = player_data.tail(20)
    
    # Calculate ALL required features
    features = {
        # Rolling averages (L20 games)
        'avg_minutes': history['minutes'].mean(),
        'avg_points': history['points'].mean(),
        'avg_rebounds': history['rebounds'].mean(),
        'avg_assists': history['assists'].mean(),
        'avg_steals': history['steals'].mean(),
        'avg_blocks': history['blocks'].mean(),
        'avg_turnovers': history['turnovers'].mean(),
        
        # Shooting percentages
        'fg_pct': history['fgm'].sum() / max(history['fga'].sum(), 1),
        'fg3_pct': history['fg3m'].sum() / max(history['fg3a'].sum(), 1),
        'ft_pct': history['ftm'].sum() / max(history['fta'].sum(), 1),
        
        # Usage
        'avg_fga': history['fga'].mean(),
        'avg_fta': history['fta'].mean(),
        
        # DD/TD rates
        'dd_rate': history['double_double'].mean(),
        'td_rate': history['triple_double'].mean(),
        
        # Recent form (L5)
        'l5_minutes': history.iloc[-5:]['minutes'].mean() if len(history) >= 5 else history['minutes'].mean(),
        'l5_points': history.iloc[-5:]['points'].mean() if len(history) >= 5 else history['points'].mean(),
        'l5_rebounds': history.iloc[-5:]['rebounds'].mean() if len(history) >= 5 else history['rebounds'].mean(),
        'l5_assists': history.iloc[-5:]['assists'].mean() if len(history) >= 5 else history['assists'].mean(),
        'l5_dd_rate': history.iloc[-5:]['double_double'].mean() if len(history) >= 5 else history['double_double'].mean(),
        
        # Volatility
        'std_points': history['points'].std(),
        'std_rebounds': history['rebounds'].std(),
        'std_assists': history['assists'].std(),
        
        # Consistency
        'min_games_played': len(history),
        
        # Composite features
        'pts_reb': history['points'].mean() + history['rebounds'].mean(),
        'pts_ast': history['points'].mean() + history['assists'].mean(),
        'reb_ast': history['rebounds'].mean() + history['assists'].mean(),
        'total_production': history['points'].mean() + history['rebounds'].mean() + history['assists'].mean(),
        
        # Efficiency
        'per_minute_pts': history['points'].mean() / max(history['minutes'].mean(), 1),
        'per_minute_reb': history['rebounds'].mean() / max(history['minutes'].mean(), 1),
        'per_minute_ast': history['assists'].mean() / max(history['minutes'].mean(), 1),
        
        # Projected minutes (use average)
        'proj_minutes': history['minutes'].mean()
    }
    
    return features

def fetch_tomorrows_games():
    """Fetch tomorrow's NBA schedule"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y%m%d')
    url = f'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={tomorrow}'
    
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
                'awayTeam': away.get('team', {}).get('abbreviation', ''),
                'homeTeam': home.get('team', {}).get('abbreviation', ''),
                'time': event.get('date', '')
            })
        
        return games
    except Exception as e:
        print(f"Error fetching schedule: {e}")
        return []

def get_recent_starters(historical_df, team_abbrev, as_of_date):
    """Get likely starters based on recent games"""
    team_games = historical_df[
        (historical_df['team'] == team_abbrev) &
        (historical_df['date'] < as_of_date)
    ]
    
    if team_games.empty:
        return []
    
    # Get last 5 games
    recent_dates = team_games['date'].unique()[-5:]
    recent_players = team_games[team_games['date'].isin(recent_dates)]
    
    # Get players by avg minutes in last 5 games
    player_minutes = recent_players.groupby('player_name')['minutes'].mean()
    likely_starters = player_minutes.nlargest(8).index.tolist()
    
    return likely_starters

def main():
    print("=" * 60)
    print("🏀 NBA DD/TD MODEL V3 - TOMORROW'S PROJECTIONS")
    print(f"📅 {(datetime.now() + timedelta(days=1)).strftime('%B %d, %Y')}")
    print("=" * 60)
    print()
    
    # Load model
    print("🤖 Loading Model V3...")
    with open('models/nba/ddtd/ddtd_model_v3.pkl', 'rb') as f:
        model_data = pickle.load(f)
    
    with open('models/nba/ddtd/acceptance_gates_v3.json') as f:
        gates = json.load(f)
    
    print(f"✅ Model loaded")
    print(f"✅ Gates: DD {gates['dd']['min_prob']*100:.0f}%+ @ {gates['dd']['min_minutes']} min, TD {gates['td']['min_prob']*100:.0f}%+ @ {gates['td']['min_minutes']} min\n")
    
    # Fetch tomorrow's games
    games = fetch_tomorrows_games()
    print(f"📅 Tomorrow's Schedule: {len(games)} games")
    for game in games:
        print(f"   • {game['awayTeam']} @ {game['homeTeam']}")
    print()
    
    # Load historical data
    print("📥 Loading historical data...")
    historical_df = load_historical_data()
    print(f"✅ Loaded {len(historical_df)} player-games\n")
    
    # Generate projections for likely starters
    tomorrow = datetime.now() + timedelta(days=1)
    all_projections = []
    
    print("🎯 Generating projections for likely starters...\n")
    
    for game in games:
        for team in [game['awayTeam'], game['homeTeam']]:
            starters = get_recent_starters(historical_df, team, tomorrow)
            
            for player_name in starters:
                features = calculate_player_features(historical_df, player_name, tomorrow)
                
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
                
                all_projections.append({
                    'player': player_name,
                    'team': team,
                    'game': f"{game['awayTeam']} @ {game['homeTeam']}",
                    'dd_prob': dd_prob,
                    'td_prob': td_prob,
                    'avg_minutes': features['avg_minutes'],
                    'l20_dd_rate': features['dd_rate'],
                    'l20_td_rate': features['td_rate'],
                    'avg_points': features['avg_points'],
                    'avg_rebounds': features['avg_rebounds'],
                    'avg_assists': features['avg_assists']
                })
    
    proj_df = pd.DataFrame(all_projections)
    
    # Apply acceptance gates for DD
    dd_gate = gates['dd']
    dd_candidates = proj_df[
        (proj_df['dd_prob'] >= dd_gate['min_prob']) & 
        (proj_df['avg_minutes'] >= dd_gate['min_minutes'])
    ].copy()
    dd_candidates = dd_candidates.sort_values('dd_prob', ascending=False)
    
    # Apply acceptance gates for TD
    td_gate = gates['td']
    td_candidates = proj_df[
        (proj_df['td_prob'] >= td_gate['min_prob']) & 
        (proj_df['avg_minutes'] >= td_gate['min_minutes'])
    ].copy()
    td_candidates = td_candidates.sort_values('td_prob', ascending=False)
    
    # Display results
    print("=" * 60)
    print("🎯 TOMORROW'S PROJECTIONS - PASSING ACCEPTANCE GATES")
    print("=" * 60)
    print()
    
    if not dd_candidates.empty:
        print(f"🔥 DOUBLE-DOUBLE CANDIDATES ({len(dd_candidates)}):")
        print("-" * 60)
        for idx, proj in dd_candidates.iterrows():
            print(f"\n📊 {proj['player']} ({proj['team']})")
            print(f"   Game: {proj['game']}")
            print(f"   DD Probability: {proj['dd_prob']*100:.1f}%")
            print(f"   Recent form: {proj['l20_dd_rate']*100:.0f}% DD rate (L20)")
            print(f"   Minutes: {proj['avg_minutes']:.1f} avg")
            print(f"   Stats: {proj['avg_points']:.1f} pts, {proj['avg_rebounds']:.1f} reb, {proj['avg_assists']:.1f} ast")
    else:
        print("❌ No DD candidates passing acceptance gates tomorrow")
    
    print()
    
    if not td_candidates.empty:
        print(f"⭐ TRIPLE-DOUBLE CANDIDATES ({len(td_candidates)}):")
        print("-" * 60)
        for idx, proj in td_candidates.iterrows():
            print(f"\n📊 {proj['player']} ({proj['team']})")
            print(f"   Game: {proj['game']}")
            print(f"   TD Probability: {proj['td_prob']*100:.1f}%")
            print(f"   Recent form: {proj['l20_td_rate']*100:.0f}% TD rate (L20)")
            print(f"   Minutes: {proj['avg_minutes']:.1f} avg")
            print(f"   Stats: {proj['avg_points']:.1f} pts, {proj['avg_rebounds']:.1f} reb, {proj['avg_assists']:.1f} ast")
    else:
        print("❌ No TD candidates passing acceptance gates tomorrow")
    
    print()
    print("=" * 60)
    print(f"📊 SUMMARY: {len(dd_candidates)} DD candidates, {len(td_candidates)} TD candidates")
    print("=" * 60)
    
    # Save projections
    output_dir = Path('results')
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / f"projections_{(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'date': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
            'dd_candidates': dd_candidates.to_dict('records'),
            'td_candidates': td_candidates.to_dict('records'),
            'all_projections': proj_df.to_dict('records')
        }, f, indent=2)
    
    print(f"\n✅ Projections saved to {output_file}")

if __name__ == '__main__':
    main()
