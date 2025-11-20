"""
Quick fetch for 2025-26 season only (doesn't re-fetch old seasons)
"""
import sys
sys.path.append('ddtd')
from fetch_historical_data import fetch_season_data
from pathlib import Path

print("🏀 Fetching 2025-26 Season (Oct 22 - Nov 13)")
print("=" * 60)

output_dir = Path('data/nba/boxscores-raw/2025-26')
games = fetch_season_data('2025-10-22', '2025-11-13', output_dir)

print()
print(f"✅ Complete: {games} games fetched")
print(f"📁 Saved to: {output_dir}")
