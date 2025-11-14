"""
Train DD/TD Model V3 on real historical NBA data
Uses Gradient Boosting + Isotonic Calibration
Matches feature engineering from backtest_v3.py
"""

import json
import pickle
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, log_loss, brier_score_loss

class ModelV3Trainer:
    def __init__(self, data_dir='data/nba/boxscores-raw', models_dir='models/nba/ddtd'):
        self.data_dir = Path(data_dir)
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # DD/TD thresholds
        self.dd_threshold = (10, 10)  # (pts, reb) or (pts, ast) or (reb, ast)
        self.td_threshold = (10, 10, 10)  # (pts, reb, ast)
        
    def load_all_games(self, seasons=['2023-24', '2024-25']):
        """Load all historical games"""
        games = []
        
        for season in seasons:
            season_dir = self.data_dir / season
            if not season_dir.exists():
                print(f"  ⚠️  Season directory not found: {season}")
                continue
            
            season_files = list(season_dir.glob('*.json'))
            print(f"  Loading {season}: {len(season_files)} games")
            
            for file_path in season_files:
                try:
                    with open(file_path) as f:
                        game = json.load(f)
                    games.append(game)
                except Exception as e:
                    print(f"    ⚠️  Error loading {file_path.name}: {e}")
        
        return games
    
    def extract_player_games(self, games):
        """Convert games to player-game records"""
        records = []
        
        for game in games:
            game_date = game.get('gameDate', '')
            game_id = game.get('gameId', '')
            
            # Process both teams
            for team_key in ['home', 'away']:
                team_data = game.get(team_key, {})
                team = team_data.get('team', '')
                opp_team = game.get('away' if team_key == 'home' else 'home', {}).get('team', '')
                
                for player in team_data.get('players', []):
                    stats = player.get('stats', {})
                    
                    # Skip DNPs (0 minutes)
                    if stats.get('min', 0) == 0:
                        continue
                    
                    pts = stats.get('pts', 0)
                    reb = stats.get('reb', 0)
                    ast = stats.get('ast', 0)
                    
                    # Calculate DD/TD
                    dd = int(sum([pts >= 10, reb >= 10, ast >= 10]) >= 2)
                    td = int(pts >= 10 and reb >= 10 and ast >= 10)
                    
                    records.append({
                        'gameId': game_id,
                        'gameDate': game_date,
                        'playerId': player.get('playerId', ''),
                        'playerName': player.get('name', ''),
                        'team': team,
                        'opponent': opp_team,
                        'minutes': float(stats.get('min', 0)),
                        'points': int(pts),
                        'rebounds': int(reb),
                        'assists': int(ast),
                        'steals': int(stats.get('stl', 0)),
                        'blocks': int(stats.get('blk', 0)),
                        'turnovers': int(stats.get('tov', 0)),
                        'fgm': int(stats.get('fgm', 0)),
                        'fga': int(stats.get('fga', 0)),
                        'fg3m': int(stats.get('fg3m', 0)),
                        'fg3a': int(stats.get('fg3a', 0)),
                        'ftm': int(stats.get('ftm', 0)),
                        'fta': int(stats.get('fta', 0)),
                        'dd': dd,
                        'td': td
                    })
        
        return pd.DataFrame(records)
    
    def calculate_rolling_features(self, df, lookback_games=20, min_games=10):
        """
        Calculate rolling averages for each player
        Matches backtest_v3.py feature engineering
        """
        df = df.copy()
        df['gameDate'] = pd.to_datetime(df['gameDate'])
        df = df.sort_values(['playerId', 'gameDate'])
        
        features_list = []
        
        for player_id in df['playerId'].unique():
            player_df = df[df['playerId'] == player_id].copy()
            
            if len(player_df) < min_games:
                continue
            
            # For each game, calculate features from previous games only
            for idx in range(min_games, len(player_df)):
                current_row = player_df.iloc[idx]
                history = player_df.iloc[max(0, idx-lookback_games):idx]
                
                if len(history) < min_games:
                    continue
                
                features = {
                    'playerId': player_id,
                    'playerName': current_row['playerName'],
                    'gameDate': current_row['gameDate'],
                    'gameId': current_row['gameId'],
                    'team': current_row['team'],
                    'opponent': current_row['opponent'],
                    
                    # Current game actuals (targets)
                    'minutes': current_row['minutes'],
                    'dd_actual': current_row['dd'],
                    'td_actual': current_row['td'],
                    
                    # Rolling averages (L20 games)
                    'avg_minutes': history['minutes'].mean(),
                    'avg_points': history['points'].mean(),
                    'avg_rebounds': history['rebounds'].mean(),
                    'avg_assists': history['assists'].mean(),
                    'avg_steals': history['steals'].mean(),
                    'avg_blocks': history['blocks'].mean(),
                    'avg_turnovers': history['turnovers'].mean(),
                    
                    # Shooting percentages
                    'fg_pct': history['fgm'].sum() / max(history['fga'].sum(), 1),
                    'fg3_pct': history['fg3m'].sum() / max(history['fg3a'].sum(), 1),
                    'ft_pct': history['ftm'].sum() / max(history['fta'].sum(), 1),
                    
                    # Usage
                    'avg_fga': history['fga'].mean(),
                    'avg_fta': history['fta'].mean(),
                    
                    # DD/TD rates
                    'dd_rate': history['dd'].mean(),
                    'td_rate': history['td'].mean(),
                    
                    # Recent form (L5)
                    'l5_minutes': history.iloc[-5:]['minutes'].mean() if len(history) >= 5 else history['minutes'].mean(),
                    'l5_points': history.iloc[-5:]['points'].mean() if len(history) >= 5 else history['points'].mean(),
                    'l5_rebounds': history.iloc[-5:]['rebounds'].mean() if len(history) >= 5 else history['rebounds'].mean(),
                    'l5_assists': history.iloc[-5:]['assists'].mean() if len(history) >= 5 else history['assists'].mean(),
                    'l5_dd_rate': history.iloc[-5:]['dd'].mean() if len(history) >= 5 else history['dd'].mean(),
                    
                    # Volatility
                    'std_points': history['points'].std(),
                    'std_rebounds': history['rebounds'].std(),
                    'std_assists': history['assists'].std(),
                    
                    # Consistency
                    'min_games_played': len(history),
                    
                    # Composite features
                    'pts_reb': history['points'].mean() + history['rebounds'].mean(),
                    'pts_ast': history['points'].mean() + history['assists'].mean(),
                    'reb_ast': history['rebounds'].mean() + history['assists'].mean(),
                    'total_production': history['points'].mean() + history['rebounds'].mean() + history['assists'].mean(),
                    
                    # Efficiency
                    'per_minute_pts': history['points'].mean() / max(history['minutes'].mean(), 1),
                    'per_minute_reb': history['rebounds'].mean() / max(history['minutes'].mean(), 1),
                    'per_minute_ast': history['assists'].mean() / max(history['minutes'].mean(), 1),
                }
                
                features_list.append(features)
        
        return pd.DataFrame(features_list)
    
    def train_models(self, train_df, test_df):
        """Train DD and TD models with calibration"""
        
        # Define feature columns (38 features)
        feature_cols = [
            'avg_minutes', 'avg_points', 'avg_rebounds', 'avg_assists', 
            'avg_steals', 'avg_blocks', 'avg_turnovers',
            'fg_pct', 'fg3_pct', 'ft_pct', 'avg_fga', 'avg_fta',
            'dd_rate', 'td_rate',
            'l5_minutes', 'l5_points', 'l5_rebounds', 'l5_assists', 'l5_dd_rate',
            'std_points', 'std_rebounds', 'std_assists',
            'min_games_played',
            'pts_reb', 'pts_ast', 'reb_ast', 'total_production',
            'per_minute_pts', 'per_minute_reb', 'per_minute_ast'
        ]
        
        # Add projected minutes as feature
        train_df['proj_minutes'] = train_df['minutes']
        test_df['proj_minutes'] = test_df['minutes']
        feature_cols.append('proj_minutes')
        
        X_train = train_df[feature_cols].fillna(0)
        X_test = test_df[feature_cols].fillna(0)
        
        y_train_dd = train_df['dd_actual']
        y_train_td = train_df['td_actual']
        y_test_dd = test_df['dd_actual']
        y_test_td = test_df['td_actual']
        
        print("\n" + "=" * 60)
        print("Training DD Model...")
        print("=" * 60)
        
        # DD Model
        dd_model = GradientBoostingClassifier(
            n_estimators=200,
            learning_rate=0.1,
            max_depth=5,
            min_samples_split=50,
            min_samples_leaf=20,
            subsample=0.8,
            random_state=42,
            verbose=1
        )
        dd_model.fit(X_train, y_train_dd)
        
        dd_pred_train = dd_model.predict_proba(X_train)[:, 1]
        dd_pred_test = dd_model.predict_proba(X_test)[:, 1]
        
        print(f"\nDD Train AUC: {roc_auc_score(y_train_dd, dd_pred_train):.4f}")
        print(f"DD Test AUC: {roc_auc_score(y_test_dd, dd_pred_test):.4f}")
        print(f"DD Train Brier: {brier_score_loss(y_train_dd, dd_pred_train):.4f}")
        print(f"DD Test Brier: {brier_score_loss(y_test_dd, dd_pred_test):.4f}")
        
        # Isotonic calibration for DD
        print("\nCalibrating DD probabilities...")
        dd_calibrator = IsotonicRegression(out_of_bounds='clip')
        dd_calibrator.fit(dd_pred_train, y_train_dd)
        
        dd_cal_train = dd_calibrator.transform(dd_pred_train)
        dd_cal_test = dd_calibrator.transform(dd_pred_test)
        
        print(f"DD Calibrated Train Brier: {brier_score_loss(y_train_dd, dd_cal_train):.4f}")
        print(f"DD Calibrated Test Brier: {brier_score_loss(y_test_dd, dd_cal_test):.4f}")
        
        print("\n" + "=" * 60)
        print("Training TD Model...")
        print("=" * 60)
        
        # TD Model
        td_model = GradientBoostingClassifier(
            n_estimators=200,
            learning_rate=0.1,
            max_depth=5,
            min_samples_split=50,
            min_samples_leaf=20,
            subsample=0.8,
            random_state=42,
            verbose=1
        )
        td_model.fit(X_train, y_train_td)
        
        td_pred_train = td_model.predict_proba(X_train)[:, 1]
        td_pred_test = td_model.predict_proba(X_test)[:, 1]
        
        print(f"\nTD Train AUC: {roc_auc_score(y_train_td, td_pred_train):.4f}")
        print(f"TD Test AUC: {roc_auc_score(y_test_td, td_pred_test):.4f}")
        print(f"TD Train Brier: {brier_score_loss(y_train_td, td_pred_train):.4f}")
        print(f"TD Test Brier: {brier_score_loss(y_test_td, td_pred_test):.4f}")
        
        # Isotonic calibration for TD
        print("\nCalibrating TD probabilities...")
        td_calibrator = IsotonicRegression(out_of_bounds='clip')
        td_calibrator.fit(td_pred_train, y_train_td)
        
        td_cal_train = td_calibrator.transform(td_pred_train)
        td_cal_test = td_calibrator.transform(td_pred_test)
        
        print(f"TD Calibrated Train Brier: {brier_score_loss(y_train_td, td_cal_train):.4f}")
        print(f"TD Calibrated Test Brier: {brier_score_loss(y_test_td, td_cal_test):.4f}")
        
        return {
            'dd_model': dd_model,
            'td_model': td_model,
            'dd_calibrator': dd_calibrator,
            'td_calibrator': td_calibrator,
            'feature_names': feature_cols,
            'feature_columns': feature_cols  # Compatibility with backtest_v3.py
        }
    
    def calculate_acceptance_gates(self, test_df, models):
        """Calculate acceptance gates from test set performance"""
        feature_cols = models['feature_names']
        X_test = test_df[feature_cols].fillna(0)
        
        # Get calibrated predictions
        dd_raw = models['dd_model'].predict_proba(X_test)[:, 1]
        td_raw = models['td_model'].predict_proba(X_test)[:, 1]
        dd_prob = models['dd_calibrator'].transform(dd_raw)
        td_prob = models['td_calibrator'].transform(td_raw)
        
        test_df = test_df.copy()
        test_df['dd_prob'] = dd_prob
        test_df['td_prob'] = td_prob
        
        # Calculate gates based on profitable thresholds
        print("\n" + "=" * 60)
        print("Calculating Acceptance Gates...")
        print("=" * 60)
        
        # DD gates
        dd_results = []
        for min_prob in np.arange(0.15, 0.50, 0.01):
            for min_minutes in [25, 26, 27, 28, 29, 30]:
                subset = test_df[(test_df['dd_prob'] >= min_prob) & (test_df['minutes'] >= min_minutes)]
                if len(subset) >= 50:
                    hit_rate = subset['dd_actual'].mean()
                    edge = hit_rate - min_prob
                    dd_results.append({
                        'min_prob': min_prob,
                        'min_minutes': min_minutes,
                        'n': len(subset),
                        'hit_rate': hit_rate,
                        'edge': edge
                    })
        
        dd_df = pd.DataFrame(dd_results)
        best_dd = dd_df.nlargest(1, 'edge').iloc[0]
        
        # TD gates
        td_results = []
        for min_prob in np.arange(0.10, 0.40, 0.01):
            for min_minutes in [30, 31, 32, 33, 34, 35]:
                subset = test_df[(test_df['td_prob'] >= min_prob) & (test_df['minutes'] >= min_minutes)]
                if len(subset) >= 20:
                    hit_rate = subset['td_actual'].mean()
                    edge = hit_rate - min_prob
                    td_results.append({
                        'min_prob': min_prob,
                        'min_minutes': min_minutes,
                        'n': len(subset),
                        'hit_rate': hit_rate,
                        'edge': edge
                    })
        
        td_df = pd.DataFrame(td_results)
        best_td = td_df.nlargest(1, 'edge').iloc[0] if len(td_df) > 0 else None
        
        print(f"\n✅ DD Gate: {best_dd['edge']*100:.1f}% edge @ {best_dd['min_prob']*100:.0f}% prob, {best_dd['min_minutes']:.0f} min")
        print(f"   Hit rate: {best_dd['hit_rate']*100:.1f}% on {best_dd['n']:.0f} bets")
        
        if best_td is not None:
            print(f"\n✅ TD Gate: {best_td['edge']*100:.1f}% edge @ {best_td['min_prob']*100:.0f}% prob, {best_td['min_minutes']:.0f} min")
            print(f"   Hit rate: {best_td['hit_rate']*100:.1f}% on {best_td['n']:.0f} bets")
        else:
            best_td = {'min_prob': 0.18, 'min_minutes': 32, 'edge': 0, 'hit_rate': 0, 'n': 0}
            print(f"\n⚠️  TD Gate: No profitable threshold found, using defaults")
        
        gates = {
            'dd': {
                'min_prob': float(best_dd['min_prob']),
                'min_minutes': int(best_dd['min_minutes']),
                'expected_edge': float(best_dd['edge']),
                'hit_rate': float(best_dd['hit_rate'])
            },
            'td': {
                'min_prob': float(best_td['min_prob']),
                'min_minutes': int(best_td['min_minutes']),
                'expected_edge': float(best_td['edge']),
                'hit_rate': float(best_td['hit_rate'])
            }
        }
        
        return gates
    
    def save_model(self, models, gates, version='v3'):
        """Save trained model and gates"""
        model_path = self.models_dir / f'ddtd_model_{version}.pkl'
        gates_path = self.models_dir / f'acceptance_gates_{version}.json'
        
        with open(model_path, 'wb') as f:
            pickle.dump(models, f)
        
        with open(gates_path, 'w') as f:
            json.dump(gates, f, indent=2)
        
        print(f"\n✅ Model saved: {model_path}")
        print(f"✅ Gates saved: {gates_path}")
        
        return model_path, gates_path

def main():
    print("=" * 60)
    print("🏀 TRAINING MODEL V3")
    print("=" * 60)
    
    trainer = ModelV3Trainer()
    
    # Step 1: Load all games
    print("\n📥 Loading historical games...")
    games = trainer.load_all_games(['2023-24', '2024-25'])
    print(f"✅ Loaded {len(games)} games\n")
    
    # Step 2: Extract player-game records
    print("📊 Extracting player-game records...")
    df = trainer.extract_player_games(games)
    print(f"✅ Extracted {len(df)} player-game records")
    print(f"   DD rate: {df['dd'].mean()*100:.1f}%")
    print(f"   TD rate: {df['td'].mean()*100:.1f}%\n")
    
    # Step 3: Calculate rolling features
    print("🔧 Calculating rolling features (L20 with min 10 games history)...")
    features_df = trainer.calculate_rolling_features(df, lookback_games=20, min_games=10)
    print(f"✅ Generated {len(features_df)} training samples")
    print(f"   Unique players: {features_df['playerId'].nunique()}\n")
    
    # Step 4: Train/test split (chronological)
    print("✂️  Splitting train/test (chronological 80/20)...")
    features_df = features_df.sort_values('gameDate')
    split_idx = int(len(features_df) * 0.8)
    train_df = features_df.iloc[:split_idx]
    test_df = features_df.iloc[split_idx:]
    
    print(f"✅ Train: {len(train_df)} samples ({train_df['gameDate'].min()} to {train_df['gameDate'].max()})")
    print(f"✅ Test: {len(test_df)} samples ({test_df['gameDate'].min()} to {test_df['gameDate'].max()})\n")
    
    # Step 5: Train models
    models = trainer.train_models(train_df, test_df)
    
    # Step 6: Calculate acceptance gates
    gates = trainer.calculate_acceptance_gates(test_df, models)
    
    # Step 7: Save everything
    trainer.save_model(models, gates, version='v3')
    
    print("\n" + "=" * 60)
    print("✅ MODEL V3 TRAINING COMPLETE")
    print("=" * 60)
    print("\nNext step: Run backtest")
    print("  python3 ddtd/backtest_v3.py")
    print("=" * 60)

if __name__ == '__main__':
    main()
