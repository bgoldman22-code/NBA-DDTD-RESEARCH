"""
Fetch historical NBA boxscore data from ESPN API
Downloads real game data for training and backtesting
"""

import requests
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import time

def fetch_espn_schedule(date_str):
    """Fetch NBA schedule for a specific date from ESPN API"""
    year, month, day = date_str.split('-')
    formatted_date = f"{year}{month}{day}"
    
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={formatted_date}"
    
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
                'date': date_str,
                'homeTeam': home.get('team', {}).get('abbreviation', ''),
                'awayTeam': away.get('team', {}).get('abbreviation', ''),
                'status': event.get('status', {}).get('type', {}).get('name', ''),
                'homeScore': int(home.get('score', 0)),
                'awayScore': int(away.get('score', 0))
            })
        
        return games
    except Exception as e:
        print(f"  ⚠️  Error fetching schedule for {date_str}: {e}")
        return []

def fetch_espn_boxscore(game_id):
    """Fetch boxscore for a specific game from ESPN API"""
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        boxscore = data.get('boxscore', {})
        players = boxscore.get('players', [])
        
        home_players = []
        away_players = []
        home_team = None
        away_team = None
        
        for team_data in players:
            team_abbr = team_data.get('team', {}).get('abbreviation', '')
            
            # Determine if home or away
            competition = data.get('header', {}).get('competitions', [{}])[0]
            competitors = competition.get('competitors', [])
            is_home = any(c.get('team', {}).get('abbreviation') == team_abbr and c.get('homeAway') == 'home' for c in competitors)
            
            if is_home and not home_team:
                home_team = team_abbr
            elif not is_home and not away_team:
                away_team = team_abbr
            
            for stat_group in team_data.get('statistics', []):
                for athlete in stat_group.get('athletes', []):
                    raw_stats = athlete.get('stats', [])
                    
                    # ESPN stats order: MIN, STL, BLK, AST, REB, FGM, FGA, 3PM, 3PA, FTM, FTA, TO, PTS
                    # Note: Some values may be percentages (e.g., "33.3") - need to handle gracefully
                    if len(raw_stats) >= 13:
                        def safe_int(val):
                            """Safely convert to int, handle percentages and empty values"""
                            if not val:
                                return 0
                            try:
                                # Try direct int conversion first
                                return int(float(val))
                            except (ValueError, TypeError):
                                # If it's a percentage string or invalid, return 0
                                return 0
                        
                        def safe_float(val):
                            """Safely convert to float"""
                            if not val:
                                return 0.0
                            try:
                                return float(val)
                            except (ValueError, TypeError):
                                return 0.0
                        
                        player = {
                            'playerId': athlete.get('athlete', {}).get('id', ''),
                            'name': athlete.get('athlete', {}).get('displayName', ''),
                            'stats': {
                                'min': safe_float(raw_stats[0]),
                                'pts': safe_int(raw_stats[12]),
                                'reb': safe_int(raw_stats[4]),
                                'ast': safe_int(raw_stats[3]),
                                'stl': safe_int(raw_stats[1]),
                                'blk': safe_int(raw_stats[2]),
                                'fgm': safe_int(raw_stats[5]),
                                'fga': safe_int(raw_stats[6]),
                                'fg3m': safe_int(raw_stats[7]),
                                'fg3a': safe_int(raw_stats[8]),
                                'ftm': safe_int(raw_stats[9]),
                                'fta': safe_int(raw_stats[10]),
                                'tov': safe_int(raw_stats[11]),
                                'pf': 0  # Not in ESPN summary stats
                            }
                        }
                        
                        # Add OREB/DREB breakdown (not in basic stats, use total rebounds)
                        player['stats']['oreb'] = int(player['stats']['reb'] * 0.3)  # Approximate
                        player['stats']['dreb'] = player['stats']['reb'] - player['stats']['oreb']
                        
                        if is_home:
                            home_players.append(player)
                        else:
                            away_players.append(player)
        
        # Get game-level info
        competition = data.get('header', {}).get('competitions', [{}])[0]
        competitors = competition.get('competitors', [])
        
        home = next((c for c in competitors if c.get('homeAway') == 'home'), {})
        away = next((c for c in competitors if c.get('homeAway') == 'away'), {})
        
        return {
            'gameId': game_id,
            'gameDate': data.get('header', {}).get('competitions', [{}])[0].get('date', '')[:10],
            'home': {
                'team': home.get('team', {}).get('abbreviation', home_team or ''),
                'score': int(home.get('score', 0)),
                'players': home_players
            },
            'away': {
                'team': away.get('team', {}).get('abbreviation', away_team or ''),
                'score': int(away.get('score', 0)),
                'players': away_players
            },
            'pace': 100  # Default pace, could calculate from possessions if available
        }
    
    except Exception as e:
        print(f"    ⚠️  Error fetching boxscore for game {game_id}: {e}")
        return None

def fetch_season_data(season_start, season_end, output_dir):
    """
    Fetch all games for a season
    
    Args:
        season_start: Start date YYYY-MM-DD (e.g., '2023-10-24')
        season_end: End date YYYY-MM-DD (e.g., '2024-04-14')
        output_dir: Directory to save JSON files
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    start = datetime.strptime(season_start, '%Y-%m-%d')
    end = datetime.strptime(season_end, '%Y-%m-%d')
    
    current = start
    total_games = 0
    total_days = (end - start).days + 1
    
    print(f"\n🏀 Fetching season data: {season_start} to {season_end}")
    print(f"   Output: {output_dir}")
    print(f"   Days to process: {total_days}\n")
    
    day_count = 0
    
    while current <= end:
        day_count += 1
        date_str = current.strftime('%Y-%m-%d')
        
        print(f"[{day_count}/{total_days}] {date_str}...", end=' ')
        
        # Fetch schedule
        games = fetch_espn_schedule(date_str)
        
        if not games:
            print("No games")
            current += timedelta(days=1)
            continue
        
        # Filter for completed games
        completed = [g for g in games if g['status'] in ['STATUS_FINAL', 'Final']]
        
        if not completed:
            print(f"0 completed games (found {len(games)} scheduled)")
            current += timedelta(days=1)
            continue
        
        print(f"{len(completed)} games", end='')
        
        # Fetch boxscores
        games_saved = 0
        for game in completed:
            game_id = game['gameId']
            file_path = output_path / f"{game_id}.json"
            
            # Skip if already exists
            if file_path.exists():
                games_saved += 1
                continue
            
            boxscore = fetch_espn_boxscore(game_id)
            
            if boxscore and boxscore['home']['players'] and boxscore['away']['players']:
                with open(file_path, 'w') as f:
                    json.dump(boxscore, f, indent=2)
                games_saved += 1
                time.sleep(0.5)  # Rate limiting
        
        print(f" → {games_saved} saved")
        total_games += games_saved
        
        current += timedelta(days=1)
        time.sleep(0.2)  # Rate limiting between days
    
    print(f"\n✅ Season complete: {total_games} games saved to {output_dir}\n")
    return total_games

def main():
    """Fetch historical data for multiple seasons"""
    base_dir = Path(__file__).parent.parent / 'data' / 'nba' / 'boxscores-raw'
    
    print("=" * 60)
    print("🏀 NBA HISTORICAL DATA FETCHER")
    print("=" * 60)
    
    seasons = [
        {
            'name': '2023-24',
            'start': '2023-10-24',
            'end': '2024-04-14',  # Regular season only
            'output': base_dir / '2023-24'
        },
        {
            'name': '2024-25',
            'start': '2024-10-22',
            'end': '2025-05-08',  # Full season including playoffs
            'output': base_dir / '2024-25'
        },
        {
            'name': '2025-26',
            'start': '2025-10-22',
            'end': '2025-11-13',  # Current season up to today
            'output': base_dir / '2025-26'
        }
    ]
    
    total_all = 0
    
    for season in seasons:
        games = fetch_season_data(season['start'], season['end'], season['output'])
        total_all += games
    
    print("=" * 60)
    print(f"✅ COMPLETE: {total_all} total games fetched")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Train Model V3: python3 ddtd/train_model_v3.py")
    print("2. Run backtest: python3 ddtd/backtest_v3.py")
    print("=" * 60)

if __name__ == '__main__':
    main()
