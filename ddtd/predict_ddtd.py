#!/usr/bin/env python3
"""
NBA DD/TD Model V3 - Daily Prediction Pipeline
==============================================
Production pipeline for generating daily Double-Double and Triple-Double picks.

Features:
- Load today's NBA slate
- Calculate features from historical data
- Generate calibrated predictions
- Apply acceptance gates
- Calculate edge vs market odds
- Kelly criterion position sizing
- Output ranked picks with confidence scores

Author: Brent Goldman
Date: November 12, 2025
"""

import json
import pickle
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
import warnings
warnings.filterwarnings('ignore')

# Paths
MODEL_PATH = Path("models/nba/ddtd/ddtd_model_v3.pkl")
GATES_PATH = Path("models/nba/ddtd/acceptance_gates_v3.json")
DATA_PATH = Path("data/nba/boxscores-raw")
OUTPUT_PATH = Path("predictions")


class DDTDPredictor:
    """Generate daily DD/TD predictions for NBA slate."""
    
    def __init__(self, model_path: Path, gates_path: Path, data_path: Path):
        """Initialize predictor with model, gates, and historical data."""
        self.model_path = model_path
        self.gates_path = gates_path
        self.data_path = data_path
        
        print("Loading model and gates...")
        
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
        
        print("✅ Model loaded successfully")
        
        # Load historical data
        self.historical_data = self.load_historical_data()
    
    def load_historical_data(self, lookback_days: int = 180) -> pd.DataFrame:
        """Load recent historical data for feature calculation."""
        print(f"Loading historical data (last {lookback_days} days)...")
        
        games = []
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        
        # Load from all available seasons
        for season_dir in self.data_path.glob("*"):
            if not season_dir.is_dir():
                continue
            
            for json_file in season_dir.glob("*.json"):
                try:
                    with open(json_file, 'r') as f:
                        game_data = json.load(f)
                    
                    game_date = pd.to_datetime(game_data.get('gameDate', ''))
                    
                    if game_date < cutoff_date:
                        continue  # Skip old games
                    
                    game_id = json_file.stem
                    
                    # Extract player stats
                    for team_key in ['home', 'away']:
                        team_data = game_data.get(team_key, {})
                        opponent_key = 'away' if team_key == 'home' else 'home'
                        opponent_data = game_data.get(opponent_key, {})
                        
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
                    continue
        
        df = pd.DataFrame(games)
        
        if not df.empty:
            df = df.sort_values(['date', 'game_id', 'player_id'])
            print(f"✅ Loaded {len(df):,} recent player-games")
        else:
            print("⚠️  No historical data loaded")
        
        return df
    
    def get_todays_slate(self, date: Optional[str] = None) -> pd.DataFrame:
        """
        Get today's NBA slate (players expected to play).
        
        In production, this would hit an API (e.g., ESPN, Odds API).
        For now, returns a sample slate structure.
        """
        if date:
            target_date = pd.to_datetime(date)
        else:
            target_date = datetime.now()
        
        print(f"\nFetching slate for: {target_date.date()}")
        
        # TODO: Implement actual API integration
        # For now, return structure that would come from API
        slate = {
            'date': target_date,
            'games': [
                {
                    'game_id': 'sample_game_1',
                    'home_team': 'LAL',
                    'away_team': 'GSW',
                    'time': '19:30',
                    'pace': 102.5,
                    'players': [
                        {'player_id': 'lebron_james', 'player_name': 'LeBron James', 
                         'team': 'LAL', 'opponent': 'GSW', 'is_home': True,
                         'projected_minutes': 35, 'injury_status': 'ACTIVE'},
                        {'player_id': 'anthony_davis', 'player_name': 'Anthony Davis',
                         'team': 'LAL', 'opponent': 'GSW', 'is_home': True,
                         'projected_minutes': 34, 'injury_status': 'ACTIVE'},
                        {'player_id': 'stephen_curry', 'player_name': 'Stephen Curry',
                         'team': 'GSW', 'opponent': 'LAL', 'is_home': False,
                         'projected_minutes': 36, 'injury_status': 'ACTIVE'},
                    ]
                }
            ]
        }
        
        # Flatten to player list
        players = []
        for game in slate['games']:
            for player in game['players']:
                player['game_id'] = game['game_id']
                player['pace'] = game['pace']
                players.append(player)
        
        df = pd.DataFrame(players)
        
        print(f"✅ Found {len(df)} players in today's slate")
        
        return df
    
    def calculate_player_features(self, player_id: str, player_name: str,
                                   opponent: str, is_home: bool,
                                   pace: float, minutes: float) -> Dict:
        """Calculate all features for a single player."""
        # Get player's historical games
        player_games = self.historical_data[
            self.historical_data['player_id'] == player_id
        ].sort_values('date')
        
        if len(player_games) < 45:
            return None  # Not enough data
        
        # Get last 40, 10, 5 games
        last_40 = player_games.tail(40)
        last_10 = player_games.tail(10)
        last_5 = player_games.tail(5)
        
        # Get opponent's historical DD/TD rates allowed
        opp_games = self.historical_data[
            self.historical_data['opponent'] == opponent
        ]
        
        if len(opp_games) > 0:
            opp_allows_dd_rate = opp_games['is_dd'].mean()
            opp_allows_td_rate = opp_games['is_td'].mean()
            opp_allows_pts = opp_games['pts'].mean()
            opp_allows_reb = opp_games['reb'].mean()
            opp_allows_ast = opp_games['ast'].mean()
        else:
            # League average defaults
            opp_allows_dd_rate = 0.15
            opp_allows_td_rate = 0.005
            opp_allows_pts = 110.0
            opp_allows_reb = 45.0
            opp_allows_ast = 25.0
        
        # Calculate features
        features = {
            'player_id': player_id,
            'player_name': player_name,
            
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
            
            # Trends
            'pts_trend': last_10['pts'].mean() - last_40['pts'].mean(),
            'reb_trend': last_10['reb'].mean() - last_40['reb'].mean(),
            'ast_trend': last_10['ast'].mean() - last_40['ast'].mean(),
            'dd_trend': last_10['is_dd'].mean() - last_40['is_dd'].mean(),
            'td_trend': last_10['is_td'].mean() - last_40['is_td'].mean(),
            
            # Variance
            'pts_std_l40': last_40['pts'].std(),
            'reb_std_l40': last_40['reb'].std(),
            'ast_std_l40': last_40['ast'].std(),
            
            # Game context
            'minutes': minutes,
            'pace': pace,
            'is_home': int(is_home),
            'score_diff': 0,  # Unknown before game
            
            # Opponent
            'opp_allows_pts': opp_allows_pts,
            'opp_allows_reb': opp_allows_reb,
            'opp_allows_ast': opp_allows_ast,
            'opp_allows_dd_rate': opp_allows_dd_rate,
            'opp_allows_td_rate': opp_allows_td_rate,
            'opp_allows_is_dd': int(opp_allows_dd_rate > 0.16),  # Above average
            'opp_allows_is_td': int(opp_allows_td_rate > 0.006),  # Above average
        }
        
        return features
    
    def predict_slate(self, slate: pd.DataFrame) -> pd.DataFrame:
        """Generate predictions for entire slate."""
        print("\nCalculating features and predictions...")
        
        predictions = []
        
        for _, player in slate.iterrows():
            features = self.calculate_player_features(
                player_id=player['player_id'],
                player_name=player['player_name'],
                opponent=player['opponent'],
                is_home=player['is_home'],
                pace=player['pace'],
                minutes=player['projected_minutes']
            )
            
            if features is None:
                continue  # Skip players without enough data
            
            predictions.append(features)
        
        if not predictions:
            print("⚠️  No predictions generated")
            return pd.DataFrame()
        
        features_df = pd.DataFrame(predictions)
        
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
        features_df['dd_prob_raw'] = dd_prob_raw
        features_df['td_prob_raw'] = td_prob_raw
        
        print(f"✅ Generated {len(features_df)} predictions")
        
        return features_df
    
    def fetch_market_odds(self, player_name: str, bet_type: str) -> Optional[int]:
        """
        Fetch market odds for a player's DD/TD prop.
        
        In production, this would hit an odds API (e.g., The Odds API, DraftKings API).
        For now, returns None (will use simulated odds).
        """
        # TODO: Implement odds API integration
        # Example structure:
        # response = requests.get(f"https://api.the-odds-api.com/v4/sports/basketball_nba/odds",
        #                         params={'apiKey': API_KEY, 'markets': 'player_double_double'})
        # odds_data = response.json()
        # return odds_data[player_name][bet_type]
        
        return None
    
    def calculate_edge_and_kelly(self, prob: float, odds: int) -> tuple:
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
    
    def apply_acceptance_gates(self, predictions: pd.DataFrame,
                                market_odds: Optional[Dict] = None) -> pd.DataFrame:
        """Apply acceptance gates and rank picks."""
        if predictions.empty:
            return pd.DataFrame()
        
        dd_gates = self.gates['dd']
        td_gates = self.gates['td']
        
        picks = []
        
        for _, pred in predictions.iterrows():
            player_name = pred['player_name']
            
            # Double-Double evaluation
            if (pred['dd_prob'] >= dd_gates['min_prob'] and
                pred['minutes'] >= dd_gates['min_minutes']):
                
                # Get or simulate market odds
                if market_odds and player_name in market_odds:
                    odds = market_odds[player_name]['DD']
                else:
                    # Simulate market odds (market typically underprices DDs)
                    market_prob = pred['dd_prob'] * 0.95
                    if market_prob >= 0.5:
                        odds = int(-100 * market_prob / (1 - market_prob))
                    else:
                        odds = int(100 * (1 - market_prob) / market_prob)
                
                edge, kelly = self.calculate_edge_and_kelly(pred['dd_prob'], odds)
                
                # Apply edge threshold
                if edge >= dd_gates['min_edge']:
                    picks.append({
                        'player': player_name,
                        'bet_type': 'DD',
                        'model_prob': pred['dd_prob'],
                        'raw_prob': pred['dd_prob_raw'],
                        'market_odds': odds,
                        'edge': edge,
                        'kelly_size': kelly,
                        'minutes': pred['minutes'],
                        'dd_rate_l40': pred['dd_rate_l40'],
                        'dd_rate_l10': pred['dd_rate_l10'],
                        'pts_l10': pred['pts_l10'],
                        'reb_l10': pred['reb_l10'],
                        'ast_l10': pred['ast_l10'],
                        'confidence': 'HIGH' if edge > dd_gates['min_edge'] * 2 else 'MEDIUM'
                    })
            
            # Triple-Double evaluation
            if (pred['td_prob'] >= td_gates['min_prob'] and
                pred['minutes'] >= td_gates['min_minutes'] and
                pred['pace'] >= td_gates.get('min_pace', 0)):
                
                # Get or simulate market odds
                if market_odds and player_name in market_odds:
                    odds = market_odds[player_name]['TD']
                else:
                    # Simulate market odds (market significantly underprices TDs)
                    market_prob = pred['td_prob'] * 0.90
                    if market_prob >= 0.5:
                        odds = int(-100 * market_prob / (1 - market_prob))
                    else:
                        odds = int(100 * (1 - market_prob) / market_prob)
                
                edge, kelly = self.calculate_edge_and_kelly(pred['td_prob'], odds)
                
                # Apply edge threshold
                if edge >= td_gates['min_edge']:
                    # Apply odds range filter
                    if td_gates['min_odds'] <= odds <= td_gates['max_odds']:
                        picks.append({
                            'player': player_name,
                            'bet_type': 'TD',
                            'model_prob': pred['td_prob'],
                            'raw_prob': pred['td_prob_raw'],
                            'market_odds': odds,
                            'edge': edge,
                            'kelly_size': kelly,
                            'minutes': pred['minutes'],
                            'td_rate_l40': pred['td_rate_l40'],
                            'td_rate_l10': pred['td_rate_l10'],
                            'pts_l10': pred['pts_l10'],
                            'reb_l10': pred['reb_l10'],
                            'ast_l10': pred['ast_l10'],
                            'pace': pred['pace'],
                            'confidence': 'HIGH' if edge > td_gates['min_edge'] * 2 else 'MEDIUM'
                        })
        
        picks_df = pd.DataFrame(picks)
        
        if not picks_df.empty:
            # Sort by edge (highest edge = best value)
            picks_df = picks_df.sort_values('edge', ascending=False)
            picks_df['rank'] = range(1, len(picks_df) + 1)
        
        return picks_df
    
    def generate_daily_picks(self, date: Optional[str] = None,
                            market_odds: Optional[Dict] = None) -> pd.DataFrame:
        """Main pipeline: generate ranked picks for the day."""
        print("\n" + "="*60)
        print("🏀 NBA DD/TD Daily Prediction Pipeline")
        print("="*60)
        
        # Get today's slate
        slate = self.get_todays_slate(date)
        
        if slate.empty:
            print("❌ No games found for today")
            return pd.DataFrame()
        
        # Generate predictions
        predictions = self.predict_slate(slate)
        
        if predictions.empty:
            print("❌ No predictions generated")
            return pd.DataFrame()
        
        # Apply acceptance gates
        picks = self.apply_acceptance_gates(predictions, market_odds)
        
        if picks.empty:
            print("\n⚠️  No picks passed acceptance gates")
            return pd.DataFrame()
        
        # Display picks
        self.display_picks(picks)
        
        return picks
    
    def display_picks(self, picks: pd.DataFrame):
        """Display formatted picks."""
        print("\n" + "="*60)
        print("🎯 TODAY'S PICKS")
        print("="*60 + "\n")
        
        for _, pick in picks.iterrows():
            print(f"#{pick['rank']} - {pick['player']} - {pick['bet_type']}")
            print(f"  Probability: {pick['model_prob']:.1%} (Raw: {pick['raw_prob']:.1%})")
            print(f"  Market Odds: {pick['market_odds']:+d}")
            print(f"  Edge: {pick['edge']:.1%}")
            print(f"  Kelly Size: {pick['kelly_size']:.1%}")
            print(f"  Confidence: {pick['confidence']}")
            print(f"  Minutes: {pick['minutes']:.1f}")
            
            if pick['bet_type'] == 'DD':
                print(f"  DD Rate: L40={pick['dd_rate_l40']:.1%}, L10={pick['dd_rate_l10']:.1%}")
                print(f"  Recent Stats: {pick['pts_l10']:.1f} PTS, "
                      f"{pick['reb_l10']:.1f} REB, {pick['ast_l10']:.1f} AST")
            else:
                print(f"  TD Rate: L40={pick['td_rate_l40']:.1%}, L10={pick['td_rate_l10']:.1%}")
                print(f"  Recent Stats: {pick['pts_l10']:.1f} PTS, "
                      f"{pick['reb_l10']:.1f} REB, {pick['ast_l10']:.1f} AST")
                print(f"  Pace: {pick['pace']:.1f}")
            
            print()
        
        print("="*60 + "\n")
    
    def save_picks(self, picks: pd.DataFrame, date: Optional[str] = None):
        """Save picks to file."""
        if picks.empty:
            return
        
        if date:
            target_date = pd.to_datetime(date)
        else:
            target_date = datetime.now()
        
        filename = f"picks_{target_date.strftime('%Y%m%d')}.json"
        output_file = OUTPUT_PATH / filename
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to JSON-serializable format
        picks_dict = picks.to_dict('records')
        
        with open(output_file, 'w') as f:
            json.dump({
                'date': target_date.strftime('%Y-%m-%d'),
                'generated_at': datetime.now().isoformat(),
                'num_picks': len(picks),
                'picks': picks_dict
            }, f, indent=2, default=str)
        
        print(f"✅ Picks saved to: {output_file}")


def main():
    """Run daily prediction pipeline."""
    # Initialize predictor
    predictor = DDTDPredictor(
        model_path=MODEL_PATH,
        gates_path=GATES_PATH,
        data_path=DATA_PATH
    )
    
    # Generate picks for today
    picks = predictor.generate_daily_picks()
    
    if not picks.empty:
        # Save picks
        predictor.save_picks(picks)
        
        print(f"\n✅ Pipeline complete! Generated {len(picks)} picks")
    else:
        print("\n⚠️  No picks generated for today")


if __name__ == "__main__":
    main()
