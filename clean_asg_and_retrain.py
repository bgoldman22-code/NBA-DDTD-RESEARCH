"""
Clean All-Star Games from data and retrain model with improvements:
1. Filter All-Star games
2. Add recency weighting
3. Adaptive lookback window (L20 early season, L30+ mid/late)
4. Current team verification for predictions
"""
import json
from pathlib import Path
import shutil
from datetime import datetime

def remove_allstar_games():
    """Remove All-Star games from historical data"""
    base_dir = Path('data/nba/boxscores-raw')
    asg_teams = {'EAST', 'WEST', 'All-Star', 'ASG'}
    
    removed = []
    
    for season_dir in base_dir.iterdir():
        if season_dir.is_dir():
            for game_file in season_dir.glob('*.json'):
                with open(game_file) as f:
                    game = json.load(f)
                
                home_team = game['home']['team']
                away_team = game['away']['team']
                
                if home_team in asg_teams or away_team in asg_teams:
                    removed.append(str(game_file))
                    print(f"🗑️  Removing: {game['gameDate']} - {away_team} @ {home_team}")
                    game_file.unlink()  # Delete the file
    
    print(f"\n✅ Removed {len(removed)} All-Star game(s)")
    return removed

def get_current_team_mapping():
    """Get current team for each player from 2025-26 season"""
    season_dir = Path('data/nba/boxscores-raw/2025-26')
    
    if not season_dir.exists():
        print("⚠️  No 2025-26 season data found")
        return {}
    
    player_teams = {}
    
    for game_file in season_dir.glob('*.json'):
        with open(game_file) as f:
            game = json.load(f)
            
            for side in ['home', 'away']:
                team = game[side]['team']
                for player in game[side]['players']:
                    player_name = player['name']
                    # Update with latest team (most recent game)
                    player_teams[player_name] = team
    
    print(f"✅ Found current teams for {len(player_teams)} players")
    return player_teams

def main():
    print("=" * 60)
    print("🏀 CLEANING DATA & RETRAINING MODEL V3")
    print("=" * 60)
    print()
    
    # Step 1: Remove All-Star games
    print("Step 1: Removing All-Star games...")
    removed = remove_allstar_games()
    print()
    
    # Step 2: Get current team mappings
    print("Step 2: Building current team mapping...")
    current_teams = get_current_team_mapping()
    
    # Save current teams for use in predictions
    output_dir = Path('models/nba/ddtd')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / 'current_teams.json', 'w') as f:
        json.dump(current_teams, f, indent=2)
    
    print(f"✅ Saved current team mapping to {output_dir / 'current_teams.json'}")
    print()
    
    # Step 3: Show lookback window recommendations
    print("Step 3: Lookback Window Recommendations...")
    today = datetime.now()
    season_start = datetime(2025, 10, 22)
    days_into_season = (today - season_start).days
    
    if days_into_season < 60:  # < 2 months
        recommended_lookback = 20
        reason = "Early season - use L20 for responsiveness"
    elif days_into_season < 120:  # 2-4 months
        recommended_lookback = 30
        reason = "Mid season - use L30 for balance"
    else:  # 4+ months
        recommended_lookback = 40
        reason = "Late season - use L40 for stability"
    
    print(f"  Days into 2025-26 season: {days_into_season}")
    print(f"  Recommended lookback: L{recommended_lookback}")
    print(f"  Reason: {reason}")
    print()
    
    print("=" * 60)
    print("✅ DATA CLEANING COMPLETE")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Update train_model_v3.py to use adaptive lookback")
    print("2. Add recency weighting to features")
    print("3. Retrain model: python3 ddtd/train_model_v3.py")
    print("4. Update run_today.py to use current_teams.json")
    print("5. Test predictions: python3 run_today.py <API_KEY>")

if __name__ == '__main__':
    main()
