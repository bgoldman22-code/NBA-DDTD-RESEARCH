"""
Run Model V3 predictions for today (November 13, 2025)
Fetch real odds from The Odds API and generate picks
"""

import os
import json
import pickle
import requests
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# API Key - REMOVED AFTER USE
# Get from: netlify env:get ODDS_API_KEY
import sys
if len(sys.argv) > 1:
    ODDS_API_KEY = sys.argv[1]
else:
    print("❌ Please provide API key as argument")
    print("   Usage: python3 run_today.py $(netlify env:get ODDS_API_KEY)")
    sys.exit(1)

def fetch_todays_games():
    """Fetch today's NBA schedule from ESPN"""
    from datetime import datetime
    date_str = datetime.now().strftime('%Y%m%d')  # Today's date
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
    # First, get list of today's events
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
        
        # Now fetch odds for each event (player props endpoint)
        odds_data = []
        
        for event in events:  # Fetch ALL games (not just first 3)
            event_id = event.get('id')
            away_team = event.get('away_team')
            home_team = event.get('home_team')
            
            print(f"   Fetching props for {away_team} @ {home_team}...")
            
            # Use per-event odds endpoint with player props markets
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
                
                # Parse player props
                for bookmaker in event_odds.get('bookmakers', []):
                    for market in bookmaker.get('markets', []):
                        market_key = market.get('key')
                        if market_key in ['player_double_double', 'player_triple_double']:
                            for outcome in market.get('outcomes', []):
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
    # First try exact name match
    player_data = df[df['playerName'] == player_name]
    
    # If no exact match, try case-insensitive match
    if player_data.empty:
        player_data = df[df['playerName'].str.lower() == player_name.lower()]
    
    # If still no match, try contains first name (fallback)
    if player_data.empty:
        player_data = df[df['playerName'].str.contains(player_name.split()[0], case=False, na=False)]
    
    if player_data.empty:
        return None
    
    # Use most recent player ID if multiple matches
    player_data = player_data.sort_values('gameDate', ascending=False)
    
    if len(player_data) < 10:
        return None
    
    # Take last N games
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
        'proj_minutes': history['minutes'].mean()  # Use average minutes as projection
    }
    
    return features

def main():
    from datetime import datetime
    today_str = datetime.now().strftime('%B %d, %Y')
    
    print("=" * 60)
    print("🏀 NBA DD/TD MODEL V3 - TODAY'S PREDICTIONS")
    print(f"📅 {today_str}")
    print("=" * 60)
    print()
    
    # Load model
    print("🤖 Loading Model V3...")
    with open('models/nba/ddtd/ddtd_model_v3.pkl', 'rb') as f:
        model_data = pickle.load(f)
    
    with open('models/nba/ddtd/acceptance_gates_v3.json') as f:
        gates = json.load(f)
    
    print(f"✅ Model loaded (38 features)")
    print(f"✅ Gates: DD {gates['dd']['min_prob']*100:.0f}%+ @ {gates['dd']['min_minutes']} min, TD {gates['td']['min_prob']*100:.0f}%+ @ {gates['td']['min_minutes']} min")
    
    # Load current team mapping for verification
    try:
        with open('models/nba/ddtd/current_teams.json') as f:
            current_teams = json.load(f)
        print(f"✅ Current rosters: {len(current_teams)} players mapped to 2025-26 teams\n")
    except:
        current_teams = {}
        print("⚠️  No current team mapping found\n")
    
    # Fetch today's games
    games = fetch_todays_games()
    print(f"📅 Today's Schedule: {len(games)} games")
    for game in games:
        print(f"   • {game['awayTeam']} @ {game['homeTeam']}")
    print()
    
    # Fetch odds (using API key once)
    odds_df = fetch_player_props_odds()
    
    if odds_df.empty:
        print("⚠️  No odds data available. Proceeding with model predictions only.\n")
    else:
        print(f"✅ Fetched odds for {len(odds_df)} props")
        print(f"   DD props: {len(odds_df[odds_df['bet_type']=='DD'])}")
        print(f"   TD props: {len(odds_df[odds_df['bet_type']=='TD'])}\n")
    
    # Load historical data
    historical_df = load_historical_data()
    
    # Get unique players from odds
    if not odds_df.empty:
        players_to_predict = odds_df['player_name'].unique()
        print(f"🎯 Generating predictions for {len(players_to_predict)} players...\n")
        
        predictions = []
        
        for player_name in players_to_predict:
            # Calculate features
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
            
            # Data quality check: Flag suspicious predictions
            if features['dd_rate'] > 0.60 and dd_prob < 0.20:
                print(f"   ⚠️  Data quality warning: {player_name} has {features['dd_rate']:.0%} DD rate but only {dd_prob:.1%} model prob")
            if features['avg_minutes'] > 32 and features['avg_minutes'] < 25:
                print(f"   ⚠️  Data quality warning: {player_name} minutes seem unusual: {features['avg_minutes']:.1f}")
            
            # Get odds for this player (use BEST odds for betting)
            player_odds = odds_df[odds_df['player_name'] == player_name]
            dd_odds_list = player_odds[player_odds['bet_type'] == 'DD']['odds'].values
            td_odds_list = player_odds[player_odds['bet_type'] == 'TD']['odds'].values
            
            # Select best odds (highest value = most favorable for bettor)
            dd_best = max(dd_odds_list) if len(dd_odds_list) > 0 else None
            td_best = max(td_odds_list) if len(td_odds_list) > 0 else None
            
            predictions.append({
                'player': player_name,
                'dd_prob': dd_prob,
                'td_prob': td_prob,
                'dd_odds': dd_best,
                'td_odds': td_best,
                'avg_minutes': features['avg_minutes'],
                'l20_dd_rate': features['dd_rate'],
                'l20_td_rate': features['td_rate']
            })
        
        pred_df = pd.DataFrame(predictions)
        
        # DEBUG: Check elite players and high probability players
        elite_check = ['Luka Doncic', 'Giannis Antetokounmpo', 'Victor Wembanyama', 'Kevin Durant', 
                       'Domantas Sabonis', 'Ivica Zubac']
        elite_found = pred_df[pred_df['player'].isin(elite_check)]
        if not elite_found.empty:
            print(f"\n🔍 DEBUG - Elite Players:")
            for _, row in elite_found.iterrows():
                # Calculate edge
                dd_odds = row['dd_odds']
                if dd_odds and not pd.isna(dd_odds):
                    implied = abs(dd_odds) / (abs(dd_odds) + 100) if dd_odds < 0 else 100 / (dd_odds + 100)
                    edge = row['dd_prob'] - implied
                    edge_str = f"Edge: {edge:+.1%}"
                else:
                    edge_str = "No odds"
                print(f"   {row['player']:25} DD: {row['dd_prob']:.1%} ({edge_str}) | Min: {row['avg_minutes']:.1f} | L20 DD: {row['l20_dd_rate']:.0%}")
        
        # Apply acceptance gates with adaptive logic
        dd_gate = gates['dd']
        td_gate = gates['td']
        
        # Standard gate logic
        dd_standard = (pred_df['dd_prob'] >= dd_gate['min_prob']) & \
                     (pred_df['avg_minutes'] >= dd_gate['min_minutes']) & \
                     (pred_df['dd_odds'].notna())
        
        # Elite exception: very high probability, slightly lower minutes OK
        dd_elite = (pred_df['dd_prob'] >= dd_gate.get('elite_prob', 0.90)) & \
                  (pred_df['avg_minutes'] >= dd_gate.get('elite_minutes', 29)) & \
                  (pred_df['dd_odds'].notna())
        
        # Combine: pass either standard OR elite gates
        dd_picks = pred_df[dd_standard | dd_elite].copy()
        
        # Same for TD
        td_standard = (pred_df['td_prob'] >= td_gate['min_prob']) & \
                     (pred_df['avg_minutes'] >= td_gate['min_minutes']) & \
                     (pred_df['td_odds'].notna())
        
        td_elite = (pred_df['td_prob'] >= td_gate.get('elite_prob', 0.80)) & \
                  (pred_df['avg_minutes'] >= td_gate.get('elite_minutes', 33)) & \
                  (pred_df['td_odds'].notna())
        
        td_picks = pred_df[td_standard | td_elite].copy()
        
        # Track near-misses for analysis
        dd_near_miss = pred_df[
            ~(dd_standard | dd_elite) &  # Didn't pass gates
            (
                ((pred_df['dd_prob'] >= dd_gate.get('near_miss_prob', 0.13)) & 
                 (pred_df['avg_minutes'] >= dd_gate['min_minutes'])) |  # Close on prob
                ((pred_df['dd_prob'] >= dd_gate['min_prob']) & 
                 (pred_df['avg_minutes'] >= dd_gate.get('near_miss_minutes', 28)))  # Close on minutes
            ) &
            (pred_df['dd_odds'].notna())
        ].copy()
        
        # Calculate edges
        def odds_to_implied_prob(odds):
            if odds > 0:
                return 100 / (odds + 100)
            else:
                return abs(odds) / (abs(odds) + 100)
        
        if not dd_picks.empty:
            dd_picks['implied_prob'] = dd_picks['dd_odds'].apply(odds_to_implied_prob)
            dd_picks['edge'] = dd_picks['dd_prob'] - dd_picks['implied_prob']
            # CRITICAL: Only keep positive edge bets
            dd_picks = dd_picks[dd_picks['edge'] > 0]
            dd_picks = dd_picks.sort_values('edge', ascending=False)
        
        if not td_picks.empty:
            td_picks['implied_prob'] = td_picks['td_odds'].apply(odds_to_implied_prob)
            td_picks['edge'] = td_picks['td_prob'] - td_picks['implied_prob']
            # CRITICAL: Only keep positive edge bets
            td_picks = td_picks[td_picks['edge'] > 0]
            td_picks = td_picks.sort_values('edge', ascending=False)
        
        # Display results
        print("=" * 60)
        print("🎯 TODAY'S PICKS - PASSING ACCEPTANCE GATES")
        print("=" * 60)
        print()
        
        if not dd_picks.empty:
            print("🔥 DOUBLE-DOUBLE PICKS:")
            print("-" * 60)
            for idx, pick in dd_picks.iterrows():
                # Flag elite exceptions
                is_elite = pick['dd_prob'] >= dd_gate.get('elite_prob', 0.90) and \
                          pick['avg_minutes'] < dd_gate['min_minutes']
                elite_flag = " 🌟 ELITE EXCEPTION" if is_elite else ""
                
                print(f"\n📊 {pick['player']}{elite_flag}")
                print(f"   Model Prob: {pick['dd_prob']*100:.1f}%")
                print(f"   Market Odds: {pick['dd_odds']:+d} (implied {pick['implied_prob']*100:.1f}%)")
                print(f"   EDGE: {pick['edge']*100:+.1f}%")
                print(f"   Recent form: {pick['l20_dd_rate']*100:.0f}% DD rate (L20)")
                print(f"   Minutes: {pick['avg_minutes']:.1f} avg")
        else:
            print("❌ No DD picks passing acceptance gates today")
        
        print()
        
        if not td_picks.empty:
            print("⭐ TRIPLE-DOUBLE PICKS:")
            print("-" * 60)
            for idx, pick in td_picks.iterrows():
                is_elite = pick['td_prob'] >= td_gate.get('elite_prob', 0.80) and \
                          pick['avg_minutes'] < td_gate['min_minutes']
                elite_flag = " 🌟 ELITE EXCEPTION" if is_elite else ""
                
                print(f"\n📊 {pick['player']}{elite_flag}")
                print(f"   Model Prob: {pick['td_prob']*100:.1f}%")
                print(f"   Market Odds: {pick['td_odds']:+d} (implied {pick['implied_prob']*100:.1f}%)")
                print(f"   EDGE: {pick['edge']*100:+.1f}%")
                print(f"   Recent form: {pick['l20_td_rate']*100:.0f}% TD rate (L20)")
                print(f"   Minutes: {pick['avg_minutes']:.1f} avg")
        else:
            print("❌ No TD picks passing acceptance gates today")
        
        # Report near-misses
        if not dd_near_miss.empty:
            dd_near_miss['implied_prob'] = dd_near_miss['dd_odds'].apply(odds_to_implied_prob)
            dd_near_miss['edge'] = dd_near_miss['dd_prob'] - dd_near_miss['implied_prob']
            dd_near_miss = dd_near_miss[dd_near_miss['edge'] > 0].sort_values('dd_prob', ascending=False)
            
            if not dd_near_miss.empty:
                print()
                print("=" * 60)
                print("⚠️  NEAR-MISS DD CANDIDATES (For Manual Review)")
                print("=" * 60)
                for idx, pick in dd_near_miss.head(5).iterrows():
                    reason = []
                    if pick['dd_prob'] < dd_gate['min_prob']:
                        reason.append(f"prob {pick['dd_prob']*100:.1f}% < {dd_gate['min_prob']*100:.0f}%")
                    if pick['avg_minutes'] < dd_gate['min_minutes']:
                        reason.append(f"min {pick['avg_minutes']:.1f} < {dd_gate['min_minutes']}")
                    
                    print(f"\n📋 {pick['player']}")
                    print(f"   Model: {pick['dd_prob']*100:.1f}% | Edge: {pick['edge']*100:+.1f}% | Minutes: {pick['avg_minutes']:.1f}")
                    print(f"   ⚠️  Missed by: {', '.join(reason)}")
        
        print()
        print("=" * 60)
        print(f"📊 SUMMARY: {len(dd_picks)} DD picks, {len(td_picks)} TD picks")
        print("=" * 60)
        
        # Save to file
        output_dir = Path('results')
        output_dir.mkdir(exist_ok=True)
        
        today_filename = datetime.now().strftime('%Y-%m-%d')
        output = {
            'date': today_filename,
            'dd_picks': dd_picks.to_dict('records') if not dd_picks.empty else [],
            'td_picks': td_picks.to_dict('records') if not td_picks.empty else [],
            'total_picks': len(dd_picks) + len(td_picks)
        }
        
        with open(output_dir / f'picks_{today_filename}.json', 'w') as f:
            json.dump(output, f, indent=2, default=str)
        
        print(f"\n✅ Picks saved to results/picks_{today_filename}.json")
    
    else:
        print("⚠️  No player props available to analyze")
    
    print("\n🔒 Deleting API key from script...")
    # The key will be removed manually after this run

if __name__ == '__main__':
    main()
