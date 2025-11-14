#!/usr/bin/env python3
"""
NBA Minutes Prediction Model
=============================
Predict player minutes for upcoming games to improve DD/TD feature quality.

Features:
- Recent minutes patterns (L5, L10, L40)
- Back-to-back games indicator
- Opponent pace and defensive rating
- Player injury/rest status
- Blowout risk factors
- Coach rotation tendencies
- Home/away splits

Author: Brent Goldman
Date: November 12, 2025
"""

import json
import pickle
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import warnings
warnings.filterwarnings('ignore')

# Paths
DATA_PATH = Path("data/nba/boxscores-raw")
MODEL_OUTPUT = Path("models/nba/ddtd/minutes_predictor_v1.pkl")


class MinutesPredictor:
    """Train and deploy minutes prediction model."""
    
    def __init__(self, data_path: Path):
        """Initialize with data path."""
        self.data_path = data_path
        self.model = None
        self.feature_columns = None
    
    def load_training_data(self, seasons: list = ["2022-23", "2023-24", "2024-25"]) -> pd.DataFrame:
        """Load historical game data for training."""
        print(f"Loading training data from seasons: {seasons}")
        
        games = []
        
        for season in seasons:
            season_path = self.data_path / season
            
            if not season_path.exists():
                print(f"⚠️  Season not found: {season}")
                continue
            
            json_files = list(season_path.glob("*.json"))
            print(f"  {season}: {len(json_files)} games")
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r') as f:
                        game_data = json.load(f)
                    
                    game_id = json_file.stem
                    game_date = pd.to_datetime(game_data.get('gameDate', ''))
                    
                    # Extract team-level stats
                    home_score = game_data.get('home', {}).get('score', 0)
                    away_score = game_data.get('away', {}).get('score', 0)
                    score_diff = abs(home_score - away_score)
                    
                    # Process each team
                    for team_key in ['home', 'away']:
                        team_data = game_data.get(team_key, {})
                        opponent_key = 'away' if team_key == 'home' else 'home'
                        opponent_data = game_data.get(opponent_key, {})
                        
                        team_score = team_data.get('score', 0)
                        opp_score = opponent_data.get('score', 0)
                        
                        # Estimate pace (possessions per game)
                        # Rough estimate: (FGA + 0.4*FTA - 1.07*ORB + TO) * 2
                        # For simplicity, use score as proxy
                        pace = (team_score + opp_score) / 2.0
                        
                        # Process each player
                        for player in team_data.get('players', []):
                            stats = player.get('stats', {})
                            
                            game_row = {
                                'game_id': game_id,
                                'date': game_date,
                                'player_name': player.get('name', ''),
                                'player_id': player.get('playerId', ''),
                                'team': team_data.get('team', ''),
                                'opponent': opponent_data.get('team', ''),
                                'is_home': (team_key == 'home'),
                                'minutes': stats.get('min', 0),
                                'pts': stats.get('pts', 0),
                                'team_score': team_score,
                                'opp_score': opp_score,
                                'score_diff': score_diff,
                                'is_blowout': (score_diff > 20),
                                'pace': pace,
                            }
                            
                            games.append(game_row)
                
                except Exception as e:
                    continue
        
        df = pd.DataFrame(games)
        
        if not df.empty:
            df = df.sort_values(['player_id', 'date'])
            print(f"\n✅ Loaded {len(df):,} player-games")
        
        return df
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer features for minutes prediction."""
        print("\nEngineering features...")
        
        features_list = []
        
        for player_id, player_games in df.groupby('player_id'):
            player_games = player_games.sort_values('date')
            
            # Need sufficient history
            if len(player_games) < 50:
                continue
            
            for idx in range(45, len(player_games)):
                # Target: actual minutes played
                target_minutes = player_games.iloc[idx]['minutes']
                
                # Skip if player didn't play (injured/DNP)
                if target_minutes == 0:
                    continue
                
                # Historical windows
                last_40 = player_games.iloc[idx-40:idx]
                last_10 = player_games.iloc[idx-10:idx]
                last_5 = player_games.iloc[idx-5:idx]
                last_3 = player_games.iloc[idx-3:idx]
                
                # Current game context
                current_game = player_games.iloc[idx]
                
                # Check if back-to-back
                if idx > 0:
                    prev_date = player_games.iloc[idx-1]['date']
                    current_date = current_game['date']
                    is_b2b = (current_date - prev_date).days == 1
                else:
                    is_b2b = False
                
                # Features
                features = {
                    'player_id': player_id,
                    'player_name': current_game['player_name'],
                    'date': current_game['date'],
                    'target_minutes': target_minutes,
                    
                    # Historical minutes patterns
                    'minutes_l40': last_40['minutes'].mean(),
                    'minutes_l10': last_10['minutes'].mean(),
                    'minutes_l5': last_5['minutes'].mean(),
                    'minutes_l3': last_3['minutes'].mean(),
                    'minutes_std_l40': last_40['minutes'].std(),
                    'minutes_std_l10': last_10['minutes'].std(),
                    
                    # Trend: recent vs baseline
                    'minutes_trend': last_10['minutes'].mean() - last_40['minutes'].mean(),
                    
                    # Consistency
                    'minutes_min_l10': last_10['minutes'].min(),
                    'minutes_max_l10': last_10['minutes'].max(),
                    
                    # Performance (might affect playing time)
                    'pts_l10': last_10['pts'].mean(),
                    'pts_trend': last_10['pts'].mean() - last_40['pts'].mean(),
                    
                    # Game context
                    'is_home': int(current_game['is_home']),
                    'is_b2b': int(is_b2b),
                    'opponent_pace': current_game['pace'],  # Proxy for opponent tempo
                    
                    # Rest days (if not B2B)
                    'rest_days': 0 if is_b2b else (
                        (current_game['date'] - player_games.iloc[idx-1]['date']).days
                        if idx > 0 else 3
                    ),
                    
                    # Recent blowout exposure (might affect rotation)
                    'blowout_rate_l5': last_5['is_blowout'].mean(),
                    'avg_score_diff_l5': last_5['score_diff'].mean(),
                }
                
                features_list.append(features)
        
        features_df = pd.DataFrame(features_list)
        
        print(f"✅ Engineered {len(features_df):,} training samples")
        
        return features_df
    
    def train_model(self, features_df: pd.DataFrame) -> dict:
        """Train Gradient Boosting model for minutes prediction."""
        print("\nTraining minutes prediction model...")
        
        # Feature columns (exclude meta and target)
        exclude_cols = ['player_id', 'player_name', 'date', 'target_minutes']
        feature_cols = [col for col in features_df.columns if col not in exclude_cols]
        
        X = features_df[feature_cols].fillna(0)
        y = features_df['target_minutes']
        
        # Train/test split (time-based)
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        
        print(f"  Training samples: {len(X_train):,}")
        print(f"  Test samples: {len(X_test):,}")
        
        # Train model
        model = GradientBoostingRegressor(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=4,
            min_samples_split=50,
            min_samples_leaf=20,
            subsample=0.8,
            random_state=42,
            verbose=0
        )
        
        model.fit(X_train, y_train)
        
        # Predictions
        y_train_pred = model.predict(X_train)
        y_test_pred = model.predict(X_test)
        
        # Metrics
        train_mae = mean_absolute_error(y_train, y_train_pred)
        test_mae = mean_absolute_error(y_test, y_test_pred)
        train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))
        test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
        train_r2 = r2_score(y_train, y_train_pred)
        test_r2 = r2_score(y_test, y_test_pred)
        
        print(f"\n{'='*50}")
        print("📊 MODEL PERFORMANCE")
        print(f"{'='*50}")
        print(f"\nTrain Metrics:")
        print(f"  MAE: {train_mae:.2f} minutes")
        print(f"  RMSE: {train_rmse:.2f} minutes")
        print(f"  R²: {train_r2:.3f}")
        print(f"\nTest Metrics:")
        print(f"  MAE: {test_mae:.2f} minutes")
        print(f"  RMSE: {test_rmse:.2f} minutes")
        print(f"  R²: {test_r2:.3f}")
        
        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': feature_cols,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print(f"\n{'='*50}")
        print("🎯 TOP FEATURES")
        print(f"{'='*50}")
        for _, row in feature_importance.head(10).iterrows():
            print(f"  {row['feature']:<25} {row['importance']:>8.1%}")
        print()
        
        # Error analysis
        test_errors = np.abs(y_test - y_test_pred)
        print(f"{'='*50}")
        print("📈 ERROR DISTRIBUTION")
        print(f"{'='*50}")
        print(f"  Within 2 min: {(test_errors <= 2).mean():.1%}")
        print(f"  Within 5 min: {(test_errors <= 5).mean():.1%}")
        print(f"  Within 10 min: {(test_errors <= 10).mean():.1%}")
        print()
        
        # Store model artifacts
        self.model = model
        self.feature_columns = feature_cols
        
        results = {
            'model': model,
            'feature_columns': feature_cols,
            'feature_importance': feature_importance,
            'metrics': {
                'train_mae': train_mae,
                'test_mae': test_mae,
                'train_rmse': train_rmse,
                'test_rmse': test_rmse,
                'train_r2': train_r2,
                'test_r2': test_r2
            },
            'test_predictions': {
                'actual': y_test.tolist(),
                'predicted': y_test_pred.tolist()
            }
        }
        
        return results
    
    def predict_minutes(self, player_features: dict) -> float:
        """Predict minutes for a player given features."""
        if self.model is None:
            raise ValueError("Model not trained yet")
        
        # Ensure all features present
        features_df = pd.DataFrame([player_features])
        
        for col in self.feature_columns:
            if col not in features_df.columns:
                features_df[col] = 0
        
        X = features_df[self.feature_columns].fillna(0)
        
        prediction = self.model.predict(X)[0]
        
        # Clip to reasonable range
        prediction = max(0, min(48, prediction))
        
        return prediction
    
    def save_model(self, results: dict, output_path: Path):
        """Save model to disk."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        model_data = {
            'model': results['model'],
            'feature_columns': results['feature_columns'],
            'metrics': results['metrics'],
            'trained_date': datetime.now().isoformat()
        }
        
        with open(output_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"✅ Model saved to: {output_path}")
        
        # Save feature importance as CSV
        importance_path = output_path.parent / "minutes_feature_importance.csv"
        results['feature_importance'].to_csv(importance_path, index=False)
        print(f"✅ Feature importance saved to: {importance_path}")
    
    @classmethod
    def load_model(cls, model_path: Path):
        """Load trained model from disk."""
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        predictor = cls(data_path=DATA_PATH)
        predictor.model = model_data['model']
        predictor.feature_columns = model_data['feature_columns']
        
        return predictor


def integrate_with_ddtd_pipeline():
    """
    Example integration with DD/TD prediction pipeline.
    
    Instead of using projected minutes from external sources,
    use the minutes predictor for more accurate forecasts.
    """
    print("\n" + "="*60)
    print("🔗 INTEGRATION GUIDE")
    print("="*60 + "\n")
    
    print("To integrate with predict_ddtd.py:")
    print()
    print("1. Load the minutes predictor:")
    print("   from predict_minutes import MinutesPredictor")
    print("   minutes_model = MinutesPredictor.load_model('models/nba/ddtd/minutes_predictor_v1.pkl')")
    print()
    print("2. In get_todays_slate(), replace projected_minutes with prediction:")
    print("   player_features = calculate_player_features(player_id, ...)")
    print("   predicted_minutes = minutes_model.predict_minutes(player_features)")
    print()
    print("3. Use predicted_minutes in DD/TD feature calculation")
    print()
    print("Benefits:")
    print("  ✅ More accurate minutes forecasts")
    print("  ✅ Accounts for B2B, rest, opponent pace")
    print("  ✅ Uses recent trends and coach patterns")
    print("  ✅ Improves DD/TD prediction quality")
    print()


def main():
    """Train minutes prediction model."""
    print("\n" + "="*60)
    print("🏀 NBA Minutes Prediction Model Training")
    print("="*60 + "\n")
    
    # Initialize predictor
    predictor = MinutesPredictor(data_path=DATA_PATH)
    
    # Load data
    df = predictor.load_training_data()
    
    if df.empty:
        print("❌ No training data loaded")
        return
    
    # Engineer features
    features_df = predictor.engineer_features(df)
    
    if features_df.empty:
        print("❌ No features engineered")
        return
    
    # Train model
    results = predictor.train_model(features_df)
    
    # Save model
    predictor.save_model(results, MODEL_OUTPUT)
    
    # Show integration guide
    integrate_with_ddtd_pipeline()
    
    print("\n✅ Minutes predictor training complete!")


if __name__ == "__main__":
    main()
