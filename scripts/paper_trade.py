#!/usr/bin/env python3
"""
Paper Trading System for DD/TD Model Validation

Tracks model predictions vs real market outcomes WITHOUT betting real money.
This validates the model works before risking capital.

Usage:
    python3 scripts/paper_trade.py --generate     # Generate today's paper bets
    python3 scripts/paper_trade.py --settle       # Settle completed games
    python3 scripts/paper_trade.py --report       # View performance report
"""

import sys
import json
import pickle
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ddtd.utils_data import load_games_for_date, fetch_todays_games
from ddtd.utils_odds import OddsAPIClient


class PaperTrader:
    """Manages paper trading to validate model before live betting"""
    
    def __init__(self):
        self.paper_trades_file = project_root / 'data' / 'paper_trades.json'
        self.model_path = project_root / 'models' / 'nba' / 'ddtd' / 'ddtd_model_v3.pkl'
        self.gates_path = project_root / 'models' / 'nba' / 'ddtd' / 'acceptance_gates_v3.json'
        
        # Load model
        with open(self.model_path, 'rb') as f:
            self.model = pickle.load(f)
        
        # Load gates
        with open(self.gates_path) as f:
            self.gates = json.load(f)
        
        # Load existing paper trades
        self.trades = self._load_trades()
    
    def _load_trades(self):
        """Load existing paper trades from disk"""
        if self.paper_trades_file.exists():
            with open(self.paper_trades_file) as f:
                return json.load(f)
        return {
            'trades': [],
            'metadata': {
                'started': str(datetime.now()),
                'model_version': 'v3',
                'bankroll': 10000.0,  # Virtual $10k bankroll
                'bet_unit': 100.0      # $100 per bet (1% Kelly)
            }
        }
    
    def _save_trades(self):
        """Save paper trades to disk"""
        self.paper_trades_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.paper_trades_file, 'w') as f:
            json.dump(self.trades, f, indent=2)
    
    def generate_todays_picks(self):
        """Generate paper trading picks for today's games"""
        print("=" * 80)
        print("📝 GENERATING PAPER TRADING PICKS")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d')}")
        print("=" * 80)
        
        # Fetch today's games and odds
        odds_client = OddsAPIClient()
        games_data = odds_client.fetch_todays_games()
        
        if not games_data or 'games' not in games_data:
            print("❌ No games found for today")
            return
        
        games = games_data['games']
        print(f"✅ Found {len(games)} games today\n")
        
        picks = []
        
        for game in games:
            game_id = game.get('id')
            home_team = game.get('home_team')
            away_team = game.get('away_team')
            game_time = game.get('commence_time')
            
            print(f"\n🏀 {away_team} @ {home_team}")
            print(f"   Time: {game_time}")
            
            # Get player props for this game
            if 'player_props' not in game:
                print("   ⚠️  No player props available")
                continue
            
            for player_prop in game.get('player_props', []):
                player_name = player_prop.get('player_name')
                
                # Check if we have DD odds
                dd_odds = player_prop.get('dd_odds')
                if not dd_odds:
                    continue
                
                # Get model prediction (you'll need to add feature extraction)
                # For now, using placeholder - you'd extract features from player's recent games
                model_prob = self._get_model_prediction(player_name, game_id)
                
                if model_prob is None:
                    continue
                
                # Check if meets acceptance gates
                proj_minutes = player_prop.get('proj_minutes', 0)
                
                if (model_prob >= self.gates['dd']['min_prob'] and 
                    proj_minutes >= self.gates['dd']['min_minutes']):
                    
                    # Calculate edge
                    market_odds = dd_odds.get('price', 100)
                    market_prob = self._odds_to_prob(market_odds)
                    edge = model_prob - market_prob
                    
                    # Calculate Kelly bet size (fractional Kelly for safety)
                    kelly_fraction = 0.25  # Use 25% Kelly (conservative)
                    bet_size = self._calculate_kelly_bet(
                        model_prob, market_prob, kelly_fraction
                    )
                    
                    pick = {
                        'trade_id': len(self.trades['trades']) + len(picks) + 1,
                        'date': str(datetime.now().date()),
                        'game_id': game_id,
                        'game': f"{away_team} @ {home_team}",
                        'game_time': game_time,
                        'player': player_name,
                        'bet_type': 'DD',
                        'model_prob': float(model_prob),
                        'market_odds': market_odds,
                        'market_prob': float(market_prob),
                        'edge': float(edge),
                        'bet_size': float(bet_size),
                        'proj_minutes': proj_minutes,
                        'status': 'pending',
                        'result': None,
                        'profit': None
                    }
                    
                    picks.append(pick)
                    
                    print(f"\n   ✅ PICK: {player_name} DD")
                    print(f"      Model: {model_prob*100:.1f}% | Market: {market_prob*100:.1f}%")
                    print(f"      Edge: {edge*100:.1f}% | Odds: {market_odds:+d}")
                    print(f"      Bet: ${bet_size:.0f}")
        
        # Add picks to trades
        if picks:
            self.trades['trades'].extend(picks)
            self._save_trades()
            
            print("\n" + "=" * 80)
            print(f"✅ Generated {len(picks)} paper trading picks")
            print("=" * 80)
        else:
            print("\n❌ No qualifying picks found today")
    
    def _get_model_prediction(self, player_name, game_id):
        """Get model prediction for a player (placeholder - needs feature extraction)"""
        # TODO: Extract features from player's recent games
        # For now, return None - you'd need to:
        # 1. Load player's last 20 games
        # 2. Calculate rolling features (L20 averages, L5 recent form, etc.)
        # 3. Run through model
        # 4. Return calibrated probability
        return None
    
    def _odds_to_prob(self, odds):
        """Convert American odds to implied probability"""
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)
    
    def _calculate_kelly_bet(self, model_prob, market_prob, fraction=0.25):
        """Calculate Kelly criterion bet size"""
        bankroll = self.trades['metadata']['bankroll']
        
        # Kelly formula: f = (bp - q) / b
        # where b = odds-1, p = win prob, q = 1-p
        
        if model_prob <= market_prob:
            return 0.0
        
        # Convert to decimal odds
        b = (1 / market_prob) - 1
        p = model_prob
        q = 1 - p
        
        kelly = (b * p - q) / b
        kelly = max(0, min(kelly, 0.25))  # Cap at 25% of bankroll
        
        # Apply fractional Kelly
        bet_size = bankroll * kelly * fraction
        
        # Round to nearest $10
        return round(bet_size / 10) * 10
    
    def settle_completed_games(self):
        """Settle paper trades for completed games"""
        print("=" * 80)
        print("🔍 SETTLING COMPLETED GAMES")
        print("=" * 80)
        
        pending_trades = [t for t in self.trades['trades'] if t['status'] == 'pending']
        
        if not pending_trades:
            print("✅ No pending trades to settle")
            return
        
        print(f"Found {len(pending_trades)} pending trades\n")
        
        settled_count = 0
        
        for trade in pending_trades:
            game_date = datetime.strptime(trade['date'], '%Y-%m-%d').date()
            
            # Only settle games from yesterday or earlier
            if game_date >= datetime.now().date():
                continue
            
            # Fetch game result
            result = self._fetch_game_result(trade['game_id'], trade['player'])
            
            if result is None:
                print(f"⏳ {trade['player']} - Game not completed yet")
                continue
            
            # Update trade
            trade['status'] = 'settled'
            trade['result'] = result
            
            # Calculate profit/loss
            if result:  # Win
                # Calculate payout based on odds
                odds = trade['market_odds']
                if odds > 0:
                    payout = trade['bet_size'] * (odds / 100)
                else:
                    payout = trade['bet_size'] * (100 / abs(odds))
                trade['profit'] = payout
            else:  # Loss
                trade['profit'] = -trade['bet_size']
            
            # Update bankroll
            self.trades['metadata']['bankroll'] += trade['profit']
            
            result_emoji = "✅" if result else "❌"
            print(f"{result_emoji} {trade['player']} DD - "
                  f"{'WIN' if result else 'LOSS'} "
                  f"(${trade['profit']:+.0f})")
            
            settled_count += 1
        
        if settled_count > 0:
            self._save_trades()
            print(f"\n✅ Settled {settled_count} trades")
            print(f"💰 New bankroll: ${self.trades['metadata']['bankroll']:.0f}")
        else:
            print("\n⏳ No games ready to settle yet")
    
    def _fetch_game_result(self, game_id, player_name):
        """Fetch actual game result for a player"""
        try:
            # Load game data from ESPN API
            games = load_games_for_date(datetime.now() - timedelta(days=1))
            
            # Find the specific game
            for game in games:
                if game.get('id') == game_id:
                    # Find player stats
                    boxscore = game.get('boxscore', {})
                    
                    for team in boxscore.get('players', []):
                        for stat_group in team.get('statistics', []):
                            for athlete_data in stat_group.get('athletes', []):
                                athlete = athlete_data.get('athlete', {})
                                if athlete.get('displayName') == player_name:
                                    stats = athlete_data.get('stats', [])
                                    
                                    # Parse stats (assuming fixed indices)
                                    points = int(stats[1]) if len(stats) > 1 else 0
                                    rebounds = int(stats[5]) if len(stats) > 5 else 0
                                    assists = int(stats[6]) if len(stats) > 6 else 0
                                    
                                    # Check for double-double
                                    stat_counts = [points >= 10, rebounds >= 10, assists >= 10]
                                    dd = sum(stat_counts) >= 2
                                    
                                    return dd
            
            return None  # Game not found or not completed
            
        except Exception as e:
            print(f"⚠️  Error fetching result: {e}")
            return None
    
    def generate_report(self):
        """Generate paper trading performance report"""
        print("\n" + "=" * 80)
        print("📊 PAPER TRADING PERFORMANCE REPORT")
        print("=" * 80)
        
        trades = self.trades['trades']
        metadata = self.trades['metadata']
        
        if not trades:
            print("\n❌ No trades recorded yet")
            print("\nTo start paper trading:")
            print("  python3 scripts/paper_trade.py --generate")
            return
        
        # Filter settled trades
        settled = [t for t in trades if t['status'] == 'settled']
        pending = [t for t in trades if t['status'] == 'pending']
        
        print(f"\n📅 Started: {metadata['started'][:10]}")
        print(f"💰 Starting Bankroll: $10,000")
        print(f"💰 Current Bankroll: ${metadata['bankroll']:.0f}")
        print(f"📈 Total P&L: ${metadata['bankroll'] - 10000:+.0f}")
        
        if settled:
            # Calculate statistics
            wins = [t for t in settled if t['result']]
            losses = [t for t in settled if not t['result']]
            
            total_profit = sum(t['profit'] for t in settled)
            total_wagered = sum(abs(t['bet_size']) for t in settled)
            roi = (total_profit / total_wagered * 100) if total_wagered > 0 else 0
            
            hit_rate = len(wins) / len(settled) * 100
            avg_model_prob = np.mean([t['model_prob'] for t in settled]) * 100
            
            print(f"\n📊 Settled Bets: {len(settled)}")
            print(f"   ✅ Wins: {len(wins)}")
            print(f"   ❌ Losses: {len(losses)}")
            print(f"   📈 Hit Rate: {hit_rate:.1f}%")
            print(f"   🎯 Avg Model Prob: {avg_model_prob:.1f}%")
            print(f"   💵 Total Wagered: ${total_wagered:.0f}")
            print(f"   💰 Total Profit: ${total_profit:+.0f}")
            print(f"   📊 ROI: {roi:+.1f}%")
            
            # Calibration check
            print(f"\n🎯 Calibration Check:")
            print(f"   Model predicted: {avg_model_prob:.1f}% win rate")
            print(f"   Actual hit rate: {hit_rate:.1f}%")
            diff = abs(hit_rate - avg_model_prob)
            if diff < 5:
                print(f"   ✅ EXCELLENT - Within 5% ({diff:.1f}%)")
            elif diff < 10:
                print(f"   ⚠️  ACCEPTABLE - Within 10% ({diff:.1f}%)")
            else:
                print(f"   ❌ POOR - Off by {diff:.1f}%")
            
            # Edge analysis
            avg_edge = np.mean([t['edge'] for t in settled]) * 100
            print(f"\n📈 Edge Analysis:")
            print(f"   Avg Predicted Edge: {avg_edge:.1f}%")
            print(f"   Actual ROI: {roi:+.1f}%")
            
            # Recent performance (last 10 bets)
            if len(settled) >= 10:
                recent = settled[-10:]
                recent_wins = sum(1 for t in recent if t['result'])
                recent_profit = sum(t['profit'] for t in recent)
                print(f"\n📅 Last 10 Bets:")
                print(f"   Record: {recent_wins}-{10-recent_wins}")
                print(f"   Profit: ${recent_profit:+.0f}")
        
        if pending:
            print(f"\n⏳ Pending Bets: {len(pending)}")
            total_pending = sum(t['bet_size'] for t in pending)
            print(f"   Total at risk: ${total_pending:.0f}")
        
        # Validation status
        print(f"\n🎯 VALIDATION STATUS:")
        if len(settled) < 20:
            print(f"   ⏳ Need {20 - len(settled)} more bets (minimum 20)")
        elif len(settled) < 50:
            print(f"   ⚠️  Early results ({len(settled)} bets)")
            print(f"   📊 Target: 50-100 bets for validation")
        else:
            print(f"   ✅ Sufficient data ({len(settled)} bets)")
            
            if roi > 5 and abs(hit_rate - avg_model_prob) < 10:
                print(f"   ✅ VALIDATION PASSED")
                print(f"   💡 Model appears profitable and calibrated")
                print(f"   ➡️  Consider starting small stakes testing")
            elif roi > 0:
                print(f"   ⚠️  MARGINAL - Profitable but check calibration")
            else:
                print(f"   ❌ VALIDATION FAILED - Negative ROI")
                print(f"   ⚠️  Do NOT bet real money yet")
        
        print("\n" + "=" * 80)
        
        # Show recent picks
        if pending:
            print("\n📋 PENDING PICKS:")
            for trade in pending[-5:]:  # Show last 5 pending
                print(f"\n   {trade['player']} DD - {trade['game']}")
                print(f"   Model: {trade['model_prob']*100:.1f}% | "
                      f"Market: {trade['market_prob']*100:.1f}% | "
                      f"Edge: {trade['edge']*100:.1f}%")
                print(f"   Bet: ${trade['bet_size']:.0f} @ {trade['market_odds']:+d}")


def main():
    parser = argparse.ArgumentParser(
        description='Paper Trading System for DD/TD Model Validation'
    )
    parser.add_argument(
        '--generate', '-g',
        action='store_true',
        help='Generate paper trading picks for today'
    )
    parser.add_argument(
        '--settle', '-s',
        action='store_true',
        help='Settle completed games'
    )
    parser.add_argument(
        '--report', '-r',
        action='store_true',
        help='View performance report'
    )
    
    args = parser.parse_args()
    
    trader = PaperTrader()
    
    if args.generate:
        trader.generate_todays_picks()
    elif args.settle:
        trader.settle_completed_games()
    elif args.report:
        trader.generate_report()
    else:
        # Default: show report
        trader.generate_report()


if __name__ == '__main__':
    main()
