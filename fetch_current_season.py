"""
Quick fetch for 2025-26 season only (doesn't re-fetch old seasons)
Automatically fetches from season start through yesterday
"""
import sys
from datetime import datetime, timedelta
sys.path.append('ddtd')
from fetch_historical_data import fetch_season_data
from pathlib import Path

# Calculate date range: season start through yesterday
season_start = '2025-10-22'
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

print(f"🏀 Fetching 2025-26 Season ({season_start} through {yesterday})")
print("=" * 60)

output_dir = Path('data/nba/boxscores-raw/2025-26')
games = fetch_season_data(season_start, yesterday, output_dir)

print()
print(f"✅ Complete: {games} games fetched")
print(f"📁 Saved to: {output_dir}")
