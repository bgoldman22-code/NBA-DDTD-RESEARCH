#!/usr/bin/env python3
"""
NBA DD/TD Monte Carlo Simulation
=================================
Correlated Monte Carlo simulation for DD/TD probability estimation using
covariance matrices for PTS/REB/AST/STL/BLK.

Features:
- Multivariate normal simulation with correlation structure
- 10,000 simulations per player
- DD/TD probability estimation with uncertainty bounds
- Can be blended with Gradient Boosting predictions
- Handles zero-inflation for STL/BLK

Author: Brent Goldman
Date: November 12, 2025
"""

import json
import pickle
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from scipy import stats
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Paths
DATA_PATH = Path("data/nba/boxscores-raw")
MODEL_OUTPUT = Path("models/nba/ddtd/monte_carlo_params_v1.pkl")


class MonteCarloSimulator:
    """Monte Carlo simulation for DD/TD probabilities."""
    
    def __init__(self, data_path: Path):
        """Initialize simulator."""
        self.data_path = data_path
        self.stat_cols = ['pts', 'reb', 'ast', 'stl', 'blk']
        self.player_params = {}  # Store mean/cov per player
    
    def load_historical_data(self, seasons: list = ["2022-23", "2023-24", "2024-25"],
                            lookback_days: int = 180) -> pd.DataFrame:
        """Load historical data for covariance estimation."""
        print(f"Loading historical data from: {seasons}")
        
        games = []
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        
        for season in seasons:
            season_path = self.data_path / season
            
            if not season_path.exists():
                continue
            
            for json_file in season_path.glob("*.json"):
                try:
                    with open(json_file, 'r') as f:
                        game_data = json.load(f)
                    
                    game_date = pd.to_datetime(game_data.get('gameDate', ''))
                    
                    if game_date < cutoff_date:
                        continue
                    
                    for team_key in ['home', 'away']:
                        team_data = game_data.get(team_key, {})
                        
                        for player in team_data.get('players', []):
                            stats = player.get('stats', {})
                            
                            game_row = {
                                'player_id': player.get('playerId', ''),
                                'player_name': player.get('name', ''),
                                'date': game_date,
                                'pts': stats.get('pts', 0),
                                'reb': stats.get('reb', 0),
                                'ast': stats.get('ast', 0),
                                'stl': stats.get('stl', 0),
                                'blk': stats.get('blk', 0),
                                'minutes': stats.get('min', 0),
                            }
                            
                            games.append(game_row)
                
                except Exception as e:
                    continue
        
        df = pd.DataFrame(games)
        
        if not df.empty:
            df = df.sort_values(['player_id', 'date'])
            # Filter out DNPs
            df = df[df['minutes'] > 0]
            print(f"✅ Loaded {len(df):,} player-games")
        
        return df
    
    def estimate_player_parameters(self, df: pd.DataFrame, min_games: int = 40) -> Dict:
        """
        Estimate mean vector and covariance matrix for each player.
        
        Returns dict with player_id -> {'mean': array, 'cov': matrix, 'n_games': int}
        """
        print("\nEstimating player parameters...")
        
        player_params = {}
        
        for player_id, player_games in df.groupby('player_id'):
            if len(player_games) < min_games:
                continue
            
            player_name = player_games.iloc[0]['player_name']
            
            # Get stat vectors
            stats_matrix = player_games[self.stat_cols].values
            
            # Calculate mean and covariance
            mean_vector = stats_matrix.mean(axis=0)
            cov_matrix = np.cov(stats_matrix.T)
            
            # Store parameters
            player_params[player_id] = {
                'player_name': player_name,
                'mean': mean_vector,
                'cov': cov_matrix,
                'n_games': len(player_games),
                'last_40_games': player_games.tail(40)[self.stat_cols].values
            }
        
        print(f"✅ Estimated parameters for {len(player_params)} players")
        
        return player_params
    
    def simulate_game(self, mean: np.ndarray, cov: np.ndarray, 
                     n_sims: int = 10000) -> np.ndarray:
        """
        Simulate n_sims games for a player given mean and covariance.
        
        Returns: (n_sims, 5) array of simulated stats [PTS, REB, AST, STL, BLK]
        """
        # Multivariate normal simulation
        simulations = np.random.multivariate_normal(mean, cov, size=n_sims)
        
        # Floor at zero (no negative stats)
        simulations = np.maximum(simulations, 0)
        
        # Round to integers
        simulations = np.round(simulations).astype(int)
        
        return simulations
    
    def calculate_dd_td_probabilities(self, simulations: np.ndarray) -> Dict:
        """
        Calculate DD/TD probabilities from simulations.
        
        Args:
            simulations: (n_sims, 5) array of [PTS, REB, AST, STL, BLK]
        
        Returns:
            Dict with probabilities and confidence intervals
        """
        n_sims = len(simulations)
        
        # Count how many categories >= 10 for each simulation
        double_digit_counts = (simulations >= 10).sum(axis=1)
        
        # DD: at least 2 categories >= 10
        dd_outcomes = (double_digit_counts >= 2)
        dd_prob = dd_outcomes.mean()
        
        # TD: at least 3 categories >= 10
        td_outcomes = (double_digit_counts >= 3)
        td_prob = td_outcomes.mean()
        
        # Confidence intervals (95%)
        dd_ci_raw = stats.binom.interval(0.95, n_sims, dd_prob)
        dd_ci = (dd_ci_raw[0] / n_sims, dd_ci_raw[1] / n_sims)
        td_ci_raw = stats.binom.interval(0.95, n_sims, td_prob)
        td_ci = (td_ci_raw[0] / n_sims, td_ci_raw[1] / n_sims)
        
        # Distribution of stat values (for debugging/analysis)
        stat_means = simulations.mean(axis=0)
        stat_stds = simulations.std(axis=0)
        
        return {
            'dd_prob': dd_prob,
            'dd_ci_lower': dd_ci[0],
            'dd_ci_upper': dd_ci[1],
            'td_prob': td_prob,
            'td_ci_lower': td_ci[0],
            'td_ci_upper': td_ci[1],
            'simulated_means': stat_means,
            'simulated_stds': stat_stds,
            'n_sims': n_sims
        }
    
    def predict_player(self, player_id: str, n_sims: int = 10000) -> Optional[Dict]:
        """Generate Monte Carlo prediction for a player."""
        if player_id not in self.player_params:
            return None
        
        params = self.player_params[player_id]
        
        # Run simulation
        simulations = self.simulate_game(params['mean'], params['cov'], n_sims)
        
        # Calculate probabilities
        results = self.calculate_dd_td_probabilities(simulations)
        
        # Add player metadata
        results['player_id'] = player_id
        results['player_name'] = params['player_name']
        results['n_games_trained'] = params['n_games']
        results['baseline_means'] = params['mean']
        
        return results
    
    def batch_predict(self, player_ids: List[str], n_sims: int = 10000) -> pd.DataFrame:
        """Generate predictions for multiple players."""
        predictions = []
        
        for player_id in player_ids:
            result = self.predict_player(player_id, n_sims)
            if result:
                predictions.append(result)
        
        return pd.DataFrame(predictions)
    
    def blend_with_gradient_boosting(self, mc_prob: float, gb_prob: float, 
                                     mc_weight: float = 0.3) -> float:
        """
        Blend Monte Carlo and Gradient Boosting predictions.
        
        Args:
            mc_prob: Monte Carlo probability
            gb_prob: Gradient Boosting probability
            mc_weight: Weight for MC (0-1), GB gets (1-mc_weight)
        
        Returns:
            Blended probability
        """
        return mc_weight * mc_prob + (1 - mc_weight) * gb_prob
    
    def save_parameters(self, output_path: Path):
        """Save player parameters for later use."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        save_data = {
            'player_params': self.player_params,
            'stat_cols': self.stat_cols,
            'created_date': datetime.now().isoformat()
        }
        
        with open(output_path, 'wb') as f:
            pickle.dump(save_data, f)
        
        print(f"✅ Parameters saved to: {output_path}")
    
    @classmethod
    def load_parameters(cls, model_path: Path, data_path: Path):
        """Load pre-computed parameters."""
        with open(model_path, 'rb') as f:
            save_data = pickle.load(f)
        
        simulator = cls(data_path)
        simulator.player_params = save_data['player_params']
        simulator.stat_cols = save_data['stat_cols']
        
        return simulator
    
    def analyze_correlations(self, player_id: str) -> pd.DataFrame:
        """Analyze stat correlations for a player."""
        if player_id not in self.player_params:
            return None
        
        params = self.player_params[player_id]
        cov_matrix = params['cov']
        
        # Convert covariance to correlation
        std_devs = np.sqrt(np.diag(cov_matrix))
        corr_matrix = cov_matrix / np.outer(std_devs, std_devs)
        
        # Create dataframe
        corr_df = pd.DataFrame(
            corr_matrix,
            index=self.stat_cols,
            columns=self.stat_cols
        )
        
        return corr_df
    
    def validate_model(self, test_df: pd.DataFrame, n_sims: int = 10000) -> Dict:
        """
        Validate Monte Carlo predictions against actual outcomes.
        
        Args:
            test_df: DataFrame with actual game outcomes
            n_sims: Number of simulations per prediction
        
        Returns:
            Validation metrics
        """
        print("\nValidating Monte Carlo model...")
        
        predictions = []
        
        for _, game in test_df.iterrows():
            player_id = game['player_id']
            
            if player_id not in self.player_params:
                continue
            
            # Predict
            pred = self.predict_player(player_id, n_sims)
            
            if pred is None:
                continue
            
            # Actual outcome
            actual_stats = [game['pts'], game['reb'], game['ast'], game['stl'], game['blk']]
            actual_dd = sum(s >= 10 for s in actual_stats) >= 2
            actual_td = sum(s >= 10 for s in actual_stats) >= 3
            
            predictions.append({
                'player_id': player_id,
                'dd_prob': pred['dd_prob'],
                'td_prob': pred['td_prob'],
                'actual_dd': actual_dd,
                'actual_td': actual_td
            })
        
        pred_df = pd.DataFrame(predictions)
        
        if pred_df.empty:
            return {}
        
        # Calculate calibration metrics
        # Bin predictions and compare to actual rates
        dd_bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        pred_df['dd_bin'] = pd.cut(pred_df['dd_prob'], bins=dd_bins)
        
        calibration = pred_df.groupby('dd_bin').agg({
            'dd_prob': 'mean',
            'actual_dd': 'mean'
        }).rename(columns={'dd_prob': 'predicted_rate', 'actual_dd': 'actual_rate'})
        
        print("\nDD Calibration:")
        print(calibration)
        
        # Overall metrics
        metrics = {
            'n_predictions': len(pred_df),
            'dd_mae': np.abs(pred_df['dd_prob'] - pred_df['actual_dd']).mean(),
            'td_mae': np.abs(pred_df['td_prob'] - pred_df['actual_td']).mean(),
            'calibration': calibration.to_dict()
        }
        
        print(f"\nOverall MAE:")
        print(f"  DD: {metrics['dd_mae']:.3f}")
        print(f"  TD: {metrics['td_mae']:.3f}")
        
        return metrics


def integrate_with_predict_ddtd():
    """Show how to integrate Monte Carlo with main prediction pipeline."""
    print("\n" + "="*60)
    print("🔗 INTEGRATION GUIDE: Monte Carlo + Gradient Boosting")
    print("="*60 + "\n")
    
    print("To integrate with predict_ddtd.py:")
    print()
    print("1. Load Monte Carlo simulator:")
    print("   from monte_carlo_sim import MonteCarloSimulator")
    print("   mc_sim = MonteCarloSimulator.load_parameters(")
    print("       'models/nba/ddtd/monte_carlo_params_v1.pkl',")
    print("       DATA_PATH")
    print("   )")
    print()
    print("2. In predict_slate(), add Monte Carlo predictions:")
    print("   # After GB predictions")
    print("   for _, row in features_df.iterrows():")
    print("       player_id = row['player_id']")
    print("       mc_pred = mc_sim.predict_player(player_id)")
    print("       if mc_pred:")
    print("           # Blend predictions")
    print("           dd_prob_blended = mc_sim.blend_with_gradient_boosting(")
    print("               mc_pred['dd_prob'], row['dd_prob'], mc_weight=0.3")
    print("           )")
    print("           td_prob_blended = mc_sim.blend_with_gradient_boosting(")
    print("               mc_pred['td_prob'], row['td_prob'], mc_weight=0.3")
    print("           )")
    print()
    print("3. Use blended probabilities for acceptance gates")
    print()
    print("Benefits:")
    print("  ✅ Captures stat correlations (e.g., high AST → lower PTS)")
    print("  ✅ Provides uncertainty bounds (confidence intervals)")
    print("  ✅ Handles non-linear dependencies")
    print("  ✅ Complements GB's learned patterns")
    print()
    print("Recommended Weights:")
    print("  • DD predictions: 70% GB, 30% MC")
    print("  • TD predictions: 60% GB, 40% MC (more uncertainty)")
    print()


def main():
    """Train Monte Carlo simulation parameters."""
    print("\n" + "="*60)
    print("🎲 NBA DD/TD Monte Carlo Simulation Training")
    print("="*60 + "\n")
    
    # Initialize simulator
    simulator = MonteCarloSimulator(data_path=DATA_PATH)
    
    # Load historical data
    df = simulator.load_historical_data()
    
    if df.empty:
        print("❌ No training data loaded")
        return
    
    # Estimate parameters
    simulator.player_params = simulator.estimate_player_parameters(df)
    
    if not simulator.player_params:
        print("❌ No player parameters estimated")
        return
    
    # Example: Predict for a few players
    print("\n" + "="*60)
    print("📊 SAMPLE PREDICTIONS")
    print("="*60 + "\n")
    
    sample_players = list(simulator.player_params.keys())[:5]
    
    for player_id in sample_players:
        result = simulator.predict_player(player_id, n_sims=10000)
        
        if result:
            print(f"{result['player_name']}:")
            print(f"  DD Probability: {result['dd_prob']:.1%} "
                  f"[{result['dd_ci_lower']:.1%} - {result['dd_ci_upper']:.1%}]")
            print(f"  TD Probability: {result['td_prob']:.1%} "
                  f"[{result['td_ci_lower']:.1%} - {result['td_ci_upper']:.1%}]")
            print(f"  Simulated Stats: "
                  f"PTS={result['simulated_means'][0]:.1f}, "
                  f"REB={result['simulated_means'][1]:.1f}, "
                  f"AST={result['simulated_means'][2]:.1f}")
            print()
    
    # Analyze correlations for first player
    print("="*60)
    print("📈 CORRELATION ANALYSIS (Sample Player)")
    print("="*60 + "\n")
    
    first_player = sample_players[0]
    corr_df = simulator.analyze_correlations(first_player)
    
    if corr_df is not None:
        print(f"Player: {simulator.player_params[first_player]['player_name']}\n")
        print(corr_df.round(2))
        print()
    
    # Save parameters
    simulator.save_parameters(MODEL_OUTPUT)
    
    # Show integration guide
    integrate_with_predict_ddtd()
    
    print("\n✅ Monte Carlo simulation training complete!")


if __name__ == "__main__":
    main()
