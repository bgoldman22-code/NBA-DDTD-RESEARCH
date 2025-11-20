#!/usr/bin/env python3
"""
Simple Paper Trading Tracker

Usage:
    python3 scripts/simple_paper_tracker.py add "Luka Doncic" "DAL@LAL" 0.65 -180
    python3 scripts/simple_paper_tracker.py settle "Luka Doncic" win
    python3 scripts/simple_paper_tracker.py report
"""

import json
import sys
from datetime import datetime
from pathlib import Path


TRADES_FILE = Path(__file__).parent.parent / 'data' / 'simple_paper_trades.json'


def odds_to_prob(odds):
    """Convert American odds to probability"""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)


def calc_profit(bet_size, odds, won):
    """Calculate profit/loss"""
    if not won:
        return -bet_size
    
    if odds > 0:
        return bet_size * (odds / 100)
    else:
        return bet_size * (100 / abs(odds))


def load_trades():
    """Load existing trades"""
    if TRADES_FILE.exists():
        with open(TRADES_FILE) as f:
            return json.load(f)
    return {'bankroll': 10000, 'trades': []}


def save_trades(data):
    """Save trades to file"""
    TRADES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRADES_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def add_trade(player, game, model_prob, market_odds):
    """Add a new paper trade"""
    data = load_trades()
    
    market_prob = odds_to_prob(market_odds)
    edge = model_prob - market_prob
    
    # Bet size: 1% of bankroll, rounded to nearest $10
    bet_size = round(data['bankroll'] * 0.01 / 10) * 10
    
    trade = {
        'id': len(data['trades']) + 1,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'player': player,
        'game': game,
        'model_prob': model_prob,
        'market_odds': market_odds,
        'market_prob': market_prob,
        'edge': edge,
        'bet_size': bet_size,
        'status': 'pending'
    }
    
    data['trades'].append(trade)
    save_trades(data)
    
    print(f"\n✅ Added paper bet:")
    print(f"   Player: {player}")
    print(f"   Game: {game}")
    print(f"   Model: {model_prob*100:.1f}% | Market: {market_prob*100:.1f}% ({market_odds:+d})")
    print(f"   Edge: {edge*100:.1f}%")
    print(f"   Bet: ${bet_size}")
    
    if edge < 0.05:
        print(f"   ⚠️  WARNING: Edge < 5% - Consider skipping")


def settle_trade(player, result):
    """Settle a trade"""
    data = load_trades()
    
    # Find pending trade for player
    trade = None
    for t in reversed(data['trades']):
        if t['player'] == player and t['status'] == 'pending':
            trade = t
            break
    
    if not trade:
        print(f"❌ No pending trade found for {player}")
        return
    
    won = result.lower() in ['win', 'yes', 'w', 'y', '1', 'true']
    
    profit = calc_profit(trade['bet_size'], trade['market_odds'], won)
    data['bankroll'] += profit
    
    trade['status'] = 'settled'
    trade['result'] = 'win' if won else 'loss'
    trade['profit'] = profit
    trade['settled_date'] = datetime.now().strftime('%Y-%m-%d')
    
    save_trades(data)
    
    emoji = "✅" if won else "❌"
    print(f"\n{emoji} Settled: {player}")
    print(f"   Result: {'WIN' if won else 'LOSS'}")
    print(f"   P&L: ${profit:+.0f}")
    print(f"   New bankroll: ${data['bankroll']:.0f}")


def show_report():
    """Show paper trading report"""
    data = load_trades()
    
    if not data['trades']:
        print("\n📊 No trades yet!")
        print("\nTo add a trade:")
        print('  python3 scripts/simple_paper_tracker.py add "Player Name" "TEAM@TEAM" 0.45 +200')
        return
    
    settled = [t for t in data['trades'] if t['status'] == 'settled']
    pending = [t for t in data['trades'] if t['status'] == 'pending']
    
    print("\n" + "="*80)
    print("📊 PAPER TRADING REPORT")
    print("="*80)
    
    print(f"\n💰 Bankroll: ${data['bankroll']:.0f}")
    print(f"📈 P&L: ${data['bankroll'] - 10000:+.0f}")
    print(f"\n📊 Total Trades: {len(data['trades'])}")
    print(f"   ✅ Settled: {len(settled)}")
    print(f"   ⏳ Pending: {len(pending)}")
    
    if settled:
        wins = [t for t in settled if t['result'] == 'win']
        total_profit = sum(t['profit'] for t in settled)
        total_wagered = sum(t['bet_size'] for t in settled)
        hit_rate = len(wins) / len(settled) * 100
        roi = (total_profit / total_wagered * 100) if total_wagered > 0 else 0
        
        avg_model = sum(t['model_prob'] for t in settled) / len(settled) * 100
        
        print(f"\n📈 Performance:")
        print(f"   Record: {len(wins)}-{len(settled)-len(wins)}")
        print(f"   Hit Rate: {hit_rate:.1f}%")
        print(f"   Avg Model Prob: {avg_model:.1f}%")
        print(f"   Calibration: {abs(hit_rate - avg_model):.1f}% off")
        print(f"   ROI: {roi:+.1f}%")
        
        if len(settled) >= 10:
            recent = settled[-10:]
            recent_wins = sum(1 for t in recent if t['result'] == 'win')
            recent_profit = sum(t['profit'] for t in recent)
            print(f"\n📅 Last 10 Bets:")
            print(f"   Record: {recent_wins}-{10-recent_wins}")
            print(f"   Profit: ${recent_profit:+.0f}")
        
        # Validation status
        print(f"\n🎯 Validation Status:")
        if len(settled) < 20:
            print(f"   ⏳ Need {20-len(settled)} more bets (min 20)")
        elif len(settled) < 50:
            print(f"   ⚠️  Early results ({len(settled)} bets)")
            print(f"   Target: 50-100 bets")
        else:
            print(f"   ✅ Sufficient data ({len(settled)} bets)")
            
            if roi > 5 and abs(hit_rate - avg_model) < 10:
                print(f"   ✅ VALIDATION PASSED - Model works!")
                print(f"   💡 Consider small stakes testing")
            elif roi > 0:
                print(f"   ⚠️  MARGINAL - Profitable but check calibration")
            else:
                print(f"   ❌ VALIDATION FAILED - Negative ROI")
    
    if pending:
        print(f"\n⏳ Pending Bets:")
        for t in pending[-5:]:
            print(f"\n   {t['player']} - {t['game']}")
            print(f"   Model: {t['model_prob']*100:.1f}% | Market: {t['market_prob']*100:.1f}% ({t['market_odds']:+d})")
            print(f"   Bet: ${t['bet_size']:.0f} | Edge: {t['edge']*100:.1f}%")
    
    print("\n" + "="*80)


def main():
    if len(sys.argv) < 2:
        show_report()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'add':
        if len(sys.argv) != 6:
            print("Usage: python3 scripts/simple_paper_tracker.py add PLAYER GAME MODEL_PROB ODDS")
            print('Example: python3 scripts/simple_paper_tracker.py add "Luka Doncic" "DAL@LAL" 0.65 -180')
            return
        
        player = sys.argv[2]
        game = sys.argv[3]
        model_prob = float(sys.argv[4])
        market_odds = int(sys.argv[5])
        
        add_trade(player, game, model_prob, market_odds)
    
    elif command == 'settle':
        if len(sys.argv) != 4:
            print("Usage: python3 scripts/simple_paper_tracker.py settle PLAYER RESULT")
            print('Example: python3 scripts/simple_paper_tracker.py settle "Luka Doncic" win')
            return
        
        player = sys.argv[2]
        result = sys.argv[3]
        
        settle_trade(player, result)
    
    elif command in ['report', 'show', 'status']:
        show_report()
    
    else:
        print(f"Unknown command: {command}")
        print("Available commands: add, settle, report")


if __name__ == '__main__':
    main()
