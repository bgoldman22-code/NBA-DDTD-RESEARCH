"""
Fix Data Pipeline: Re-scrape all NBA boxscores with corrected parser
Validates data quality and saves only clean games
"""

import requests
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

# Data validation thresholds
MAX_POINTS = 60
MAX_STEALS = 10
MAX_BLOCKS = 10
MAX_FTA = 25
MAX_MINUTES = 48

def fetch_schedule(date_str):
    """Fetch games for a specific date"""
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str.replace('-', '')}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        games = []
        for event in data.get('events', []):
            games.append({
                'gameId': event['id'],
                'date': date_str
            })
        return games
    except Exception as e:
        print(f"Error fetching schedule for {date_str}: {e}")
        return []

def fetch_boxscore(game_id):
    """Fetch boxscore with CORRECTED stat indices"""
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Get game date
        game_date = data.get('header', {}).get('competitions', [{}])[0].get('date', '')
        if game_date:
            game_date = datetime.fromisoformat(game_date.replace('Z', '+00:00')).strftime('%Y-%m-%d')
        
        # Get teams
        competition = data.get('header', {}).get('competitions', [{}])[0]
        competitors = competition.get('competitors', [])
        
        home_team = None
        away_team = None
        home_score = None
        away_score = None
        
        for comp in competitors:
            abbr = comp.get('team', {}).get('abbreviation', '')
            score = int(comp.get('score', 0))
            if comp.get('homeAway') == 'home':
                home_team = abbr
                home_score = score
            else:
                away_team = abbr
                away_score = score
        
        # Parse boxscore
        boxscore = data.get('boxscore', {})
        players_data = boxscore.get('players', [])
        
        home_players = []
        away_players = []
        
        for team_data in players_data:
            team_abbr = team_data.get('team', {}).get('abbreviation', '')
            is_home = team_abbr == home_team
            
            for stat_group in team_data.get('statistics', []):
                for athlete in stat_group.get('athletes', []):
                    raw_stats = athlete.get('stats', [])
                    
                    if len(raw_stats) < 14:
                        continue
                    
                    # CORRECTED indices based on ESPN API:
                    # [0]: MIN, [1]: PTS, [2]: FG, [3]: 3PT, [4]: FT, [5]: REB, [6]: AST,
                    # [7]: TO, [8]: STL, [9]: BLK, [10]: OREB, [11]: DREB, [12]: PF, [13]: +/-
                    
                    # Parse shooting stats
                    fg = raw_stats[2].split('-') if isinstance(raw_stats[2], str) else ['0', '0']
                    fg3 = raw_stats[3].split('-') if isinstance(raw_stats[3], str) else ['0', '0']
                    ft = raw_stats[4].split('-') if isinstance(raw_stats[4], str) else ['0', '0']
                    
                    # Helper function to safely parse stat values (handles both int and "X-Y" formats)
                    def parse_stat(value, default=0):
                        if not value:
                            return default
                        if isinstance(value, (int, float)):
                            return int(value)
                        # If it's a string, try direct conversion first
                        if isinstance(value, str):
                            # If it contains a dash, it's a shooting stat - take first part
                            if '-' in value:
                                parts = value.split('-')
                                return int(parts[0]) if parts[0] else default
                            return int(value) if value else default
                        return default
                    
                    player_stats = {
                        'playerId': athlete.get('athlete', {}).get('id', ''),
                        'name': athlete.get('athlete', {}).get('displayName', ''),
                        'stats': {
                            'min': float(raw_stats[0]) if raw_stats[0] else 0,
                            'pts': parse_stat(raw_stats[1]),
                            'reb': parse_stat(raw_stats[5]),
                            'ast': parse_stat(raw_stats[6]),
                            'stl': parse_stat(raw_stats[8]),
                            'blk': parse_stat(raw_stats[9]),
                            'tov': parse_stat(raw_stats[7]),
                            'fgm': int(fg[0]) if len(fg) > 0 and fg[0] else 0,
                            'fga': int(fg[1]) if len(fg) > 1 and fg[1] else 0,
                            'fg3m': int(fg3[0]) if len(fg3) > 0 and fg3[0] else 0,
                            'fg3a': int(fg3[1]) if len(fg3) > 1 and fg3[1] else 0,
                            'ftm': int(ft[0]) if len(ft) > 0 and ft[0] else 0,
                            'fta': int(ft[1]) if len(ft) > 1 and ft[1] else 0,
                            'oreb': parse_stat(raw_stats[10]),
                            'dreb': parse_stat(raw_stats[11]),
                            'pf': parse_stat(raw_stats[12])
                        }
                    }
                    
                    if is_home:
                        home_players.append(player_stats)
                    else:
                        away_players.append(player_stats)
        
        return {
            'gameId': game_id,
            'gameDate': game_date,
            'home': {
                'team': home_team,
                'score': home_score,
                'players': home_players
            },
            'away': {
                'team': away_team,
                'score': away_score,
                'players': away_players
            },
            'pace': None  # Could calculate from possessions
        }
        
    except Exception as e:
        print(f"Error fetching boxscore {game_id}: {e}")
        return None

def validate_game_data(game_data):
    """Check if game data passes sanity checks"""
    issues = []
    
    for team_key in ['home', 'away']:
        for player in game_data[team_key]['players']:
            stats = player['stats']
            name = player['name']
            
            if stats['pts'] > MAX_POINTS:
                issues.append(f"{name}: {stats['pts']} pts (max {MAX_POINTS})")
            
            if stats['stl'] > MAX_STEALS:
                issues.append(f"{name}: {stats['stl']} stl (max {MAX_STEALS})")
            
            if stats['blk'] > MAX_BLOCKS:
                issues.append(f"{name}: {stats['blk']} blk (max {MAX_BLOCKS})")
            
            if stats['fta'] > MAX_FTA:
                issues.append(f"{name}: {stats['fta']} fta (max {MAX_FTA})")
            
            if stats['min'] > MAX_MINUTES:
                issues.append(f"{name}: {stats['min']} min (max {MAX_MINUTES})")
            
            if stats['fgm'] > stats['fga'] and stats['fga'] > 0:
                issues.append(f"{name}: fgm ({stats['fgm']}) > fga ({stats['fga']})")
            
            if stats['fg3m'] > stats['fg3a'] and stats['fg3a'] > 0:
                issues.append(f"{name}: fg3m > fg3a")
            
            if stats['ftm'] > stats['fta'] and stats['fta'] > 0:
                issues.append(f"{name}: ftm > fta")
    
    return issues

def scrape_season(start_date, end_date, season_name):
    """Scrape all games in a date range"""
    print(f"\n{'='*80}")
    print(f"Scraping {season_name}")
    print(f"Date range: {start_date} to {end_date}")
    print(f"{'='*80}\n")
    
    output_dir = Path(f'data/nba/boxscores-raw/{season_name}')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    current_date = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    total_games = 0
    valid_games = 0
    invalid_games = 0
    
    while current_date <= end:
        date_str = current_date.strftime('%Y-%m-%d')
        
        games = fetch_schedule(date_str)
        
        if games:
            print(f"📅 {date_str}: {len(games)} games")
            
            for game in games:
                game_id = game['gameId']
                output_file = output_dir / f"{game_id}.json"
                
                # Skip if already exists and valid
                if output_file.exists():
                    try:
                        with open(output_file) as f:
                            existing = json.load(f)
                        validation_issues = validate_game_data(existing)
                        if not validation_issues:
                            print(f"  ✅ {game_id} (cached, valid)")
                            valid_games += 1
                            total_games += 1
                            continue
                        else:
                            print(f"  ⚠️  {game_id} (cached but invalid, re-fetching)")
                    except:
                        print(f"  ⚠️  {game_id} (cached but corrupt, re-fetching)")
                
                # Fetch fresh data
                game_data = fetch_boxscore(game_id)
                
                if game_data:
                    # Validate
                    validation_issues = validate_game_data(game_data)
                    
                    if not validation_issues:
                        # Save valid game
                        with open(output_file, 'w') as f:
                            json.dump(game_data, f, indent=2)
                        print(f"  ✅ {game_id} (fetched, valid)")
                        valid_games += 1
                    else:
                        print(f"  ❌ {game_id} (fetched but INVALID):")
                        for issue in validation_issues[:3]:  # Show first 3 issues
                            print(f"     - {issue}")
                        invalid_games += 1
                    
                    total_games += 1
                else:
                    print(f"  ❌ {game_id} (fetch failed)")
                    invalid_games += 1
                    total_games += 1
                
                # Rate limiting
                time.sleep(0.5)
        
        current_date += timedelta(days=1)
    
    print(f"\n{'='*80}")
    print(f"{season_name} Summary:")
    print(f"  Total games: {total_games}")
    print(f"  Valid: {valid_games} ({valid_games/total_games*100:.1f}%)")
    print(f"  Invalid: {invalid_games} ({invalid_games/total_games*100:.1f}%)")
    print(f"{'='*80}\n")
    
    return valid_games, invalid_games

def main():
    print("="*80)
    print("🔧 NBA DATA FIX & RE-SCRAPE PIPELINE")
    print("="*80)
    print("\nThis will:")
    print("  1. Re-fetch all games with CORRECTED stat indices")
    print("  2. Validate each game for data quality")
    print("  3. Only save games that pass validation")
    print("  4. Skip existing valid games to save time")
    print()
    
    input("Press Enter to continue...")
    
    # Scrape 2023-24 season (October to April)
    valid_2023, invalid_2023 = scrape_season(
        '2023-10-24',
        '2024-04-14',
        '2023-24'
    )
    
    # Scrape 2024-25 season (October to today)
    today = datetime.now().strftime('%Y-%m-%d')
    valid_2024, invalid_2024 = scrape_season(
        '2024-10-22',
        today,
        '2024-25'
    )
    
    print("\n" + "="*80)
    print("🎉 DATA FIX COMPLETE!")
    print("="*80)
    print(f"\n2023-24: {valid_2023} valid, {invalid_2023} invalid")
    print(f"2024-25: {valid_2024} valid, {invalid_2024} invalid")
    print(f"\nTotal: {valid_2023 + valid_2024} valid games")
    print(f"\n✅ All valid games saved to data/nba/boxscores-raw/")
    print("\nNext steps:")
    print("  1. Delete old model: rm models/nba/ddtd/ddtd_model_v3.pkl")
    print("  2. Retrain model with clean data")
    print("  3. Generate new picks")

if __name__ == '__main__':
    main()
