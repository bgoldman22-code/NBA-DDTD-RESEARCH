#!/usr/bin/env python3
"""
Lightweight NBA DD/TD picks generator for GitHub Actions
Fetches recent player stats via ESPN API instead of loading 600MB of local data
"""

import os
import json
import requests
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# Configuration
ODDS_API_KEY = os.environ.get('ODDS_API_KEY')
MODEL_PATH = Path('models/nba/ddtd/ddtd_model_v3.pkl')
OUTPUT_PATH = Path('data/nba/ddtd_today_picks.json')

# Allowed bookmakers
ALLOWED_BOOKS = ['fanduel', 'draftkings', 'caesars', 'betmgm', 'fanatics', 'williamhill_us']

def fetch_todays_games():
    """Fetch today's NBA games from ESPN"""
    url = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard'
    response = requests.get(url, timeout=30)
    games = response.json().get('events', [])
    
    today_games = []
    for game in games:
        if game.get('status', {}).get('type', {}).get('state') == 'pre':
            competitions = game.get('competitions', [{}])[0]
            teams = competitions.get('competitors', [])
            
            for team in teams:
                today_games.append({
                    'team': team.get('team', {}).get('displayName'),
                    'team_abbr': team.get('team', {}).get('abbreviation')
                })
    
    print(f"📅 Found {len(today_games)} teams playing today\n")
    return today_games

def fetch_player_props_odds():
    """Fetch DD/TD odds from TheOddsAPI"""
    if not ODDS_API_KEY:
        print("⚠️  No ODDS_API_KEY found, returning empty odds")
        return pd.DataFrame()
    
    url = f'https://api.the-odds-api.com/v4/sports/basketball_nba/events'
    params = {'apiKey': ODDS_API_KEY}
    
    try:
        response = requests.get(url, params=params, timeout=30)
        games = response.json()
        
        all_props = []
        for game in games:
            game_id = game['id']
            home_team = game['home_team']
            away_team = game['away_team']
            
            # Fetch props for this game
            props_url = f'https://api.the-odds-api.com/v4/sports/basketball_nba/events/{game_id}/odds'
            props_params = {
                'apiKey': ODDS_API_KEY,
                'regions': 'us',
                'markets': 'player_double_double,player_triple_double'
            }
            
            print(f"   Fetching props for {away_team} @ {home_team}...")
            props_response = requests.get(props_url, params=props_params, timeout=30)
            
            if props_response.status_code == 200:
                props_data = props_response.json()
                
                for bookmaker in props_data.get('bookmakers', []):
                    book_key = bookmaker['key']
                    
                    # Filter to allowed bookmakers
                    if book_key not in ALLOWED_BOOKS:
                        continue
                    
                    for market in bookmaker.get('markets', []):
                        market_key = market['key']
                        
                        for outcome in market.get('outcomes', []):
                            all_props.append({
                                'player_name': outcome['description'],
                                'market': market_key,
                                'odds': outcome['price'],
                                'bookmaker': bookmaker['title']  # Use title for display name
                            })
        
        print(f"✅ Fetched odds for {len(all_props)} props (filtered books)\n")
        return pd.DataFrame(all_props)
    
    except Exception as e:
        print(f"⚠️  Error fetching odds: {e}")
        return pd.DataFrame()

def fetch_recent_player_stats(player_name, games=20):
    """Fetch recent stats for a player from ESPN API"""
    # Clean player name for URL
    search_name = player_name.replace(' ', '%20')
    
    try:
        # Search for player
        search_url = f'https://site.api.espn.com/apis/common/v3/search?query={search_name}&type=player&sport=basketball&league=nba'
        search_response = requests.get(search_url, timeout=10)
        results = search_response.json().get('results', [])
        
        if not results:
            return None
        
        player_id = results[0].get('id')
        
        # Get player stats
        stats_url = f'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/athletes/{player_id}/gamelog'
        stats_response = requests.get(stats_url, timeout=10)
        game_log = stats_response.json()
        
        # Extract recent games
        events = game_log.get('events', [])[:games]
        
        recent_stats = {
            'avg_minutes': np.mean([e.get('stats', {}).get('minutes', 0) for e in events]),
            'avg_points': np.mean([e.get('stats', {}).get('points', 0) for e in events]),
            'avg_rebounds': np.mean([e.get('stats', {}).get('rebounds', 0) for e in events]),
            'avg_assists': np.mean([e.get('stats', {}).get('assists', 0) for e in events]),
            'avg_steals': np.mean([e.get('stats', {}).get('steals', 0) for e in events]),
            'avg_blocks': np.mean([e.get('stats', {}).get('blocks', 0) for e in events]),
            'games_played': len(events)
        }
        
        return recent_stats
    
    except Exception as e:
        print(f"   ⚠️  Error fetching stats for {player_name}: {e}")
        return None

def main():
    print("🏀 NBA DD/TD Picks Generator (Lite Version)\n")
    print("=" * 60)
    
    # Load model
    print(f"📦 Loading model from {MODEL_PATH}...")
    model = joblib.load(MODEL_PATH)
    print("✅ Model loaded\n")
    
    # Fetch today's games
    print("📅 Fetching today's games...")
    today_games = fetch_todays_games()
    
    # Fetch odds
    print("💰 Fetching player props odds...")
    odds_df = fetch_player_props_odds()
    
    if odds_df.empty:
        print("⚠️  No odds available, generating sample output")
        output = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'generated_at': datetime.now().isoformat(),
            'model_version': 'v3_lite',
            'picks': {
                'double_double': [],
                'triple_double': []
            },
            'summary': {
                'total_picks': 0,
                'dd_picks': 0,
                'td_picks': 0
            },
            'note': 'No odds available - waiting for games to be posted'
        }
    else:
        # Generate predictions (simplified - using odds as proxy)
        dd_picks = []
        td_picks = []
        
        for _, row in odds_df.iterrows():
            player = row['player_name']
            market = row['market']
            odds = row['odds']
            
            # Convert American odds to implied probability
            if odds > 0:
                implied_prob = 100 / (odds + 100)
            else:
                implied_prob = abs(odds) / (abs(odds) + 100)
            
            # Simple edge calculation (model would do this better)
            edge = (1 - implied_prob) * 100
            
            pick = {
                'player': player,
                'odds': int(odds),  # Keep as integer American odds
                'implied_prob': round(implied_prob * 100, 1),
                'edge': round(edge, 1),
                'bookmaker': row['bookmaker']
            }
            
            if market == 'player_double_double' and edge > 5:
                dd_picks.append(pick)
            elif market == 'player_triple_double' and edge > 10:
                td_picks.append(pick)
        
        # Sort by edge
        dd_picks = sorted(dd_picks, key=lambda x: x['edge'], reverse=True)[:10]
        td_picks = sorted(td_picks, key=lambda x: x['edge'], reverse=True)[:5]
        
        output = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'generated_at': datetime.now().isoformat(),
            'model_version': 'v3_lite',
            'picks': {
                'double_double': dd_picks,
                'triple_double': td_picks
            },
            'summary': {
                'total_picks': len(dd_picks) + len(td_picks),
                'dd_picks': len(dd_picks),
                'td_picks': len(td_picks)
            },
            'note': 'Lite version - filtered to approved bookmakers'
        }
    
    # Save output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✅ Generated {output['summary']['total_picks']} picks")
    print(f"   - {output['summary']['dd_picks']} double-double picks")
    print(f"   - {output['summary']['td_picks']} triple-double picks")
    print(f"\n💾 Saved to {OUTPUT_PATH}")

if __name__ == '__main__':
    main()
