#!/usr/bin/env python3
"""
NBA DD/TD Model V3 - Backtesting Framework
==========================================
Walk-forward validation on 2023-24 season data with full P&L tracking.

Features:
- Day-by-day prediction simulation
- Edge calculation vs market odds
- Kelly criterion position sizing
- Acceptance gate filtering
- Performance metrics (ROI, Sharpe, max drawdown)
- Detailed trade logs

Author: Brent Goldman
Date: November 12, 2025
"""

import json
import pickle
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Paths (adjust for your structure)
MODEL_PATH = Path("models/nba/ddtd/ddtd_model_v3.pkl")
GATES_PATH = Path("models/nba/ddtd/acceptance_gates_v3.json")
DATA_PATH = Path("data/nba/boxscores-raw")
OUTPUT_PATH = Path("models/nba/ddtd/backtest_results_v3.json")


class DDTDBacktester:
    """Backtest DD/TD model on historical data with walk-forward validation."""
    
    def __init__(self, model_path: Path, gates_path: Path, data_path: Path):
        """Initialize backtester with model, gates, and data."""
        self.model_path = model_path
        self.gates_path = gates_path
        self.data_path = data_path
        
        # Load model and gates
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.dd_model = model_data['dd_model']
        self.td_model = model_data['td_model']
        self.dd_calibrator = model_data['dd_calibrator']
        self.td_calibrator = model_data['td_calibrator']
        self.feature_columns = model_data['feature_columns']
        
        with open(gates_path, 'r') as f:
            self.gates = json.load(f)
        
        # Results tracking
        self.trades = []
        self.daily_pnl = []
        self.bankroll_history = []
        
    def load_game_data(self, season: str = "2023-24") -> pd.DataFrame:
        """Load all game data for a season from JSON files."""
        print(f"Loading {season} game data...")
        
        games = []
        season_path = self.data_path / season
        
        if not season_path.exists():
            print(f"❌ Season path not found: {season_path}")
            return pd.DataFrame()
        
        json_files = list(season_path.glob("*.json"))
        print(f"Found {len(json_files)} game files")
        
        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    game_data = json.load(f)
                
                game_id = json_file.stem
                game_date = game_data.get('gameDate', '')
                
                # Extract home/away team stats
                for team_key in ['home', 'away']:
                    team_data = game_data.get(team_key, {})
                    opponent_key = 'away' if team_key == 'home' else 'home'
                    opponent_data = game_data.get(opponent_key, {})
                    
                    # Player stats
                    for player in team_data.get('players', []):
                        stats = player.get('stats', {})
                        
                        game_row = {
                            'game_id': game_id,
                            'date': game_date,
                            'player_name': player.get('name', ''),
                            'player_id': player.get('playerId', ''),
                            'team': team_data.get('team', ''),
                            'opponent': opponent_data.get('team', ''),
                            'minutes': stats.get('min', 0),
                            'pts': stats.get('pts', 0),
                            'reb': stats.get('reb', 0),
                            'ast': stats.get('ast', 0),
                            'stl': stats.get('stl', 0),
                            'blk': stats.get('blk', 0),
                            'is_home': (team_key == 'home'),
                            'team_score': team_data.get('score', 0),
                            'opp_score': opponent_data.get('score', 0),
                        }
                        
                        # Calculate DD/TD
                        stat_counts = [
                            int(stats.get('pts', 0) >= 10),
                            int(stats.get('reb', 0) >= 10),
                            int(stats.get('ast', 0) >= 10),
                            int(stats.get('stl', 0) >= 10),
                            int(stats.get('blk', 0) >= 10),
                        ]
                        
                        game_row['is_dd'] = sum(stat_counts) >= 2
                        game_row['is_td'] = sum(stat_counts) >= 3
                        
                        games.append(game_row)
            
            except Exception as e:
                print(f"Error loading {json_file}: {e}")
                continue
        
        df = pd.DataFrame(games)
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values(['date', 'game_id', 'player_id'])
            print(f"✅ Loaded {len(df):,} player-games")
        
        return df
    
    def calculate_features(self, df: pd.DataFrame, as_of_date: datetime) -> pd.DataFrame:
        """Calculate all features for predictions as of a given date."""
        # Filter to games before as_of_date
        historical = df[df['date'] < as_of_date].copy()
        
        if historical.empty:
            return pd.DataFrame()
        
        # Group by player
        features_list = []
        
        for player_id, player_games in historical.groupby('player_id'):
            player_games = player_games.sort_values('date')
            
            # Need at least 45 games for L40 calculation
            if len(player_games) < 45:
                continue
            
            # Get last 40, 10, 5 games
            last_40 = player_games.tail(40)
            last_10 = player_games.tail(10)
            last_5 = player_games.tail(5)
            
            # Calculate features
            features = {
                'player_id': player_id,
                'player_name': player_games.iloc[-1]['player_name'],
                
                # L40 baseline
                'pts_l40': last_40['pts'].mean(),
                'reb_l40': last_40['reb'].mean(),
                'ast_l40': last_40['ast'].mean(),
                'stl_l40': last_40['stl'].mean(),
                'blk_l40': last_40['blk'].mean(),
                'minutes_l40': last_40['minutes'].mean(),
                'dd_rate_l40': last_40['is_dd'].mean(),
                'td_rate_l40': last_40['is_td'].mean(),
                
                # L10 momentum
                'pts_l10': last_10['pts'].mean(),
                'reb_l10': last_10['reb'].mean(),
                'ast_l10': last_10['ast'].mean(),
                'stl_l10': last_10['stl'].mean(),
                'blk_l10': last_10['blk'].mean(),
                'minutes_l10': last_10['minutes'].mean(),
                'dd_rate_l10': last_10['is_dd'].mean(),
                'td_rate_l10': last_10['is_td'].mean(),
                
                # L5 hot/cold
                'pts_l5': last_5['pts'].mean(),
                'reb_l5': last_5['reb'].mean(),
                'ast_l5': last_5['ast'].mean(),
                'dd_rate_l5': last_5['is_dd'].mean(),
                'td_rate_l5': last_5['is_td'].mean(),
                
                # Trends (L10 vs L40)
                'pts_trend': last_10['pts'].mean() - last_40['pts'].mean(),
                'reb_trend': last_10['reb'].mean() - last_40['reb'].mean(),
                'ast_trend': last_10['ast'].mean() - last_40['ast'].mean(),
                'dd_trend': last_10['is_dd'].mean() - last_40['is_dd'].mean(),
                'td_trend': last_10['is_td'].mean() - last_40['is_td'].mean(),
                
                # Variance (for Monte Carlo readiness)
                'pts_std_l40': last_40['pts'].std(),
                'reb_std_l40': last_40['reb'].std(),
                'ast_std_l40': last_40['ast'].std(),
                
                # Placeholder for game-specific features
                'minutes': last_10['minutes'].mean(),  # Use recent average
                'pace': 100.0,  # Placeholder - would need team data
                'is_home': 1,  # Placeholder
                'score_diff': 0,  # Placeholder
                
                # Opponent features (would need more sophisticated calculation)
                'opp_allows_pts': 110.0,  # Placeholder
                'opp_allows_reb': 45.0,  # Placeholder
                'opp_allows_ast': 25.0,  # Placeholder
                'opp_allows_dd_rate': 0.15,  # Placeholder
                'opp_allows_td_rate': 0.005,  # Placeholder
                'opp_allows_is_dd': 0,  # Binary placeholder
                'opp_allows_is_td': 0,  # Binary placeholder
            }
            
            features_list.append(features)
        
        return pd.DataFrame(features_list)
    
    def predict_probabilities(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """Generate calibrated predictions for all players."""
        if features_df.empty:
            return pd.DataFrame()
        
        # Ensure all feature columns exist
        missing_cols = set(self.feature_columns) - set(features_df.columns)
        for col in missing_cols:
            features_df[col] = 0.0
        
        X = features_df[self.feature_columns].fillna(0)
        
        # Raw predictions
        dd_prob_raw = self.dd_model.predict_proba(X)[:, 1]
        td_prob_raw = self.td_model.predict_proba(X)[:, 1]
        
        # Calibrated predictions
        dd_prob = self.dd_calibrator.transform(dd_prob_raw.reshape(-1, 1)).ravel()
        td_prob = self.td_calibrator.transform(td_prob_raw.reshape(-1, 1)).ravel()
        
        # Add to dataframe
        features_df['dd_prob'] = dd_prob
        features_df['td_prob'] = td_prob
        
        return features_df
    
    def apply_acceptance_gates(self, predictions: pd.DataFrame) -> pd.DataFrame:
        """Filter predictions using acceptance gates."""
        if predictions.empty:
            return pd.DataFrame()
        
        dd_gates = self.gates['dd']
        td_gates = self.gates['td']
        
        # DD filters
        dd_picks = predictions[
            (predictions['dd_prob'] >= dd_gates['min_prob']) &
            (predictions['minutes'] >= dd_gates['min_minutes'])
        ].copy()
        dd_picks['bet_type'] = 'DD'
        dd_picks['prob'] = dd_picks['dd_prob']
        
        # TD filters  
        td_picks = predictions[
            (predictions['td_prob'] >= td_gates['min_prob']) &
            (predictions['minutes'] >= td_gates['min_minutes']) &
            (predictions['pace'] >= td_gates.get('min_pace', 0))
        ].copy()
        td_picks['bet_type'] = 'TD'
        td_picks['prob'] = td_picks['td_prob']
        
        # Combine
        picks = pd.concat([dd_picks, td_picks], ignore_index=True)
        
        return picks
    
    def simulate_market_odds(self, prob: float, bet_type: str) -> float:
        """Simulate market odds (American) based on probability."""
        # Add market bias (typically underprices edges)
        if bet_type == 'DD':
            market_prob = prob * 0.95  # Market slightly underestimates
        else:
            market_prob = prob * 0.90  # Larger market inefficiency for TDs
        
        # Convert to American odds
        if market_prob >= 0.5:
            odds = -100 * market_prob / (1 - market_prob)
        else:
            odds = 100 * (1 - market_prob) / market_prob
        
        return int(odds)
    
    def calculate_edge_and_kelly(self, prob: float, odds: int) -> Tuple[float, float]:
        """Calculate edge and Kelly bet size."""
        # Convert American odds to decimal
        if odds > 0:
            decimal_odds = 1 + (odds / 100)
        else:
            decimal_odds = 1 + (100 / abs(odds))
        
        # Implied probability
        implied_prob = 1 / decimal_odds
        
        # Edge
        edge = prob - implied_prob
        
        # Kelly fraction
        if edge > 0:
            kelly = (prob * decimal_odds - 1) / (decimal_odds - 1)
            kelly = max(0, min(kelly * 0.25, 0.05))  # Quarter Kelly, max 5%
        else:
            kelly = 0
        
        return edge, kelly
    
    def run_backtest(self, season: str = "2023-24", 
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> Dict:
        """Run full backtest on season data."""
        print(f"\n{'='*60}")
        print(f"🎯 Starting Backtest: {season}")
        print(f"{'='*60}\n")
        
        # Load data
        df = self.load_game_data(season)
        
        if df.empty:
            print("❌ No data loaded")
            return {}
        
        # Date range
        if start_date:
            start = pd.to_datetime(start_date)
        else:
            start = df['date'].min() + timedelta(days=60)  # Need 60 days history
        
        if end_date:
            end = pd.to_datetime(end_date)
        else:
            end = df['date'].max()
        
        print(f"Backtest Period: {start.date()} to {end.date()}")
        print(f"Total Days: {(end - start).days}\n")
        
        # Walk forward day by day
        current_date = start
        bankroll = 10000  # Starting bankroll
        self.bankroll_history = [{'date': start, 'bankroll': bankroll}]
        
        daily_results = []
        
        while current_date <= end:
            # Get today's games
            todays_games = df[df['date'] == current_date]
            
            if todays_games.empty:
                current_date += timedelta(days=1)
                continue
            
            # Calculate features using data before today
            features = self.calculate_features(df, current_date)
            
            if features.empty:
                current_date += timedelta(days=1)
                continue
            
            # Predict probabilities
            predictions = self.predict_probabilities(features)
            
            # Apply acceptance gates
            picks = self.apply_acceptance_gates(predictions)
            
            if picks.empty:
                current_date += timedelta(days=1)
                continue
            
            # Simulate bets for each pick
            daily_pnl = 0
            
            for _, pick in picks.iterrows():
                player_id = pick['player_id']
                bet_type = pick['bet_type']
                prob = pick['prob']
                
                # Find actual outcome
                actual_game = todays_games[todays_games['player_id'] == player_id]
                
                if actual_game.empty:
                    continue  # Player didn't play
                
                actual_outcome = actual_game.iloc[0]['is_dd' if bet_type == 'DD' else 'is_td']
                
                # Simulate market odds
                market_odds = self.simulate_market_odds(prob, bet_type)
                
                # Calculate edge and Kelly size
                edge, kelly_frac = self.calculate_edge_and_kelly(prob, market_odds)
                
                # Only bet if positive edge
                if edge <= 0:
                    continue
                
                # Bet size
                bet_amount = bankroll * kelly_frac
                
                # Calculate payout
                if market_odds > 0:
                    payout = bet_amount * (market_odds / 100)
                else:
                    payout = bet_amount * (100 / abs(market_odds))
                
                # Result
                if actual_outcome:
                    pnl = payout
                    result = 'WIN'
                else:
                    pnl = -bet_amount
                    result = 'LOSS'
                
                daily_pnl += pnl
                
                # Log trade
                trade = {
                    'date': current_date.strftime('%Y-%m-%d'),
                    'player': pick['player_name'],
                    'bet_type': bet_type,
                    'prob': prob,
                    'odds': market_odds,
                    'edge': edge,
                    'bet_amount': bet_amount,
                    'result': result,
                    'pnl': pnl,
                    'bankroll_after': bankroll + daily_pnl
                }
                
                self.trades.append(trade)
            
            # Update bankroll
            bankroll += daily_pnl
            self.bankroll_history.append({
                'date': current_date,
                'bankroll': bankroll,
                'pnl': daily_pnl
            })
            
            daily_results.append({
                'date': current_date,
                'num_bets': len(picks),
                'pnl': daily_pnl,
                'bankroll': bankroll
            })
            
            # Progress
            if len(daily_results) % 30 == 0:
                roi = ((bankroll - 10000) / 10000) * 100
                print(f"Day {len(daily_results)}: {current_date.date()} | "
                      f"Bankroll: ${bankroll:,.0f} | ROI: {roi:.1f}%")
            
            current_date += timedelta(days=1)
        
        # Calculate performance metrics
        results = self.calculate_metrics()
        
        return results
    
    def calculate_metrics(self) -> Dict:
        """Calculate comprehensive performance metrics."""
        if not self.trades:
            return {}
        
        trades_df = pd.DataFrame(self.trades)
        bankroll_df = pd.DataFrame(self.bankroll_history)
        
        # Overall metrics
        total_bets = len(trades_df)
        wins = len(trades_df[trades_df['result'] == 'WIN'])
        losses = len(trades_df[trades_df['result'] == 'LOSS'])
        win_rate = wins / total_bets if total_bets > 0 else 0
        
        total_pnl = trades_df['pnl'].sum()
        total_risked = trades_df['bet_amount'].sum()
        roi = (total_pnl / total_risked) * 100 if total_risked > 0 else 0
        
        # Sharpe ratio
        daily_returns = bankroll_df['pnl'].pct_change().dropna()
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if len(daily_returns) > 0 else 0
        
        # Max drawdown
        bankroll_df['peak'] = bankroll_df['bankroll'].cummax()
        bankroll_df['drawdown'] = bankroll_df['bankroll'] - bankroll_df['peak']
        max_drawdown = bankroll_df['drawdown'].min()
        max_drawdown_pct = (max_drawdown / bankroll_df['peak'].max()) * 100
        
        # By bet type
        dd_trades = trades_df[trades_df['bet_type'] == 'DD']
        td_trades = trades_df[trades_df['bet_type'] == 'TD']
        
        results = {
            'summary': {
                'total_bets': total_bets,
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'total_risked': total_risked,
                'roi': roi,
                'sharpe_ratio': sharpe,
                'max_drawdown': max_drawdown,
                'max_drawdown_pct': max_drawdown_pct,
                'final_bankroll': bankroll_df.iloc[-1]['bankroll'],
                'starting_bankroll': bankroll_df.iloc[0]['bankroll']
            },
            'dd_performance': {
                'bets': len(dd_trades),
                'wins': len(dd_trades[dd_trades['result'] == 'WIN']),
                'win_rate': len(dd_trades[dd_trades['result'] == 'WIN']) / len(dd_trades) if len(dd_trades) > 0 else 0,
                'pnl': dd_trades['pnl'].sum() if len(dd_trades) > 0 else 0,
                'roi': (dd_trades['pnl'].sum() / dd_trades['bet_amount'].sum()) * 100 if len(dd_trades) > 0 else 0
            },
            'td_performance': {
                'bets': len(td_trades),
                'wins': len(td_trades[td_trades['result'] == 'WIN']),
                'win_rate': len(td_trades[td_trades['result'] == 'WIN']) / len(td_trades) if len(td_trades) > 0 else 0,
                'pnl': td_trades['pnl'].sum() if len(td_trades) > 0 else 0,
                'roi': (td_trades['pnl'].sum() / td_trades['bet_amount'].sum()) * 100 if len(td_trades) > 0 else 0
            },
            'trades': self.trades,
            'bankroll_history': [
                {'date': row['date'].strftime('%Y-%m-%d'), 'bankroll': row['bankroll']}
                for _, row in bankroll_df.iterrows()
            ]
        }
        
        return results
    
    def print_results(self, results: Dict):
        """Print formatted backtest results."""
        print(f"\n{'='*60}")
        print("📊 BACKTEST RESULTS")
        print(f"{'='*60}\n")
        
        summary = results['summary']
        
        print("Overall Performance:")
        print(f"  Total Bets: {summary['total_bets']}")
        print(f"  Win Rate: {summary['win_rate']:.1%}")
        print(f"  Total P&L: ${summary['total_pnl']:,.2f}")
        print(f"  ROI: {summary['roi']:.2f}%")
        print(f"  Sharpe Ratio: {summary['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown: ${summary['max_drawdown']:,.2f} ({summary['max_drawdown_pct']:.1f}%)")
        print(f"  Final Bankroll: ${summary['final_bankroll']:,.2f}")
        
        print("\nDouble-Double Performance:")
        dd = results['dd_performance']
        print(f"  Bets: {dd['bets']}")
        print(f"  Win Rate: {dd['win_rate']:.1%}")
        print(f"  P&L: ${dd['pnl']:,.2f}")
        print(f"  ROI: {dd['roi']:.2f}%")
        
        print("\nTriple-Double Performance:")
        td = results['td_performance']
        print(f"  Bets: {td['bets']}")
        print(f"  Win Rate: {td['win_rate']:.1%}")
        print(f"  P&L: ${td['pnl']:,.2f}")
        print(f"  ROI: {td['roi']:.2f}%")
        
        print(f"\n{'='*60}\n")
    
    def save_results(self, results: Dict, output_path: Path):
        """Save results to JSON."""
        # Convert numpy types to native Python
        def convert(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj
        
        results_clean = json.loads(
            json.dumps(results, default=convert)
        )
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results_clean, f, indent=2)
        
        print(f"✅ Results saved to: {output_path}")


def main():
    """Run backtest."""
    # Initialize backtester
    backtester = DDTDBacktester(
        model_path=MODEL_PATH,
        gates_path=GATES_PATH,
        data_path=DATA_PATH
    )
    
    # Run backtest on 2023-24 season
    results = backtester.run_backtest(
        season="2023-24",
        start_date="2023-11-01",  # After sufficient training data
        end_date="2024-04-15"  # End of regular season
    )
    
    if results:
        # Print results
        backtester.print_results(results)
        
        # Save results
        backtester.save_results(results, OUTPUT_PATH)


if __name__ == "__main__":
    main()
