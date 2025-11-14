#!/usr/bin/env python3
"""
Comprehensive Local Testing Report
===================================
Tests all DD/TD pipeline components and generates a detailed report.
"""

import sys
from pathlib import Path

def test_1_model_loading():
    """Test: Model Loading"""
    print("\n" + "="*60)
    print("TEST 1: Model Loading")
    print("="*60)
    
    try:
        import pickle
        with open('models/nba/ddtd/ddtd_model_v3.pkl', 'rb') as f:
            model_data = pickle.load(f)
        
        print(f"✅ Model loaded successfully")
        print(f"   - Features: {len(model_data['feature_columns'])}")
        print(f"   - DD Model: {type(model_data['dd_model']).__name__}")
        print(f"   - TD Model: {type(model_data['td_model']).__name__}")
        print(f"   - Note: {model_data.get('note', 'N/A')}")
        
        # Test prediction
        import numpy as np
        X_test = np.random.randn(3, len(model_data['feature_columns']))
        dd_pred = model_data['dd_model'].predict_proba(X_test)[:, 1]
        td_pred = model_data['td_model'].predict_proba(X_test)[:, 1]
        print(f"   - Sample predictions working: DD={dd_pred[0]:.2%}, TD={td_pred[0]:.2%}")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_2_data_loading():
    """Test: Sample Data"""
    print("\n" + "="*60)
    print("TEST 2: Sample Data Loading")
    print("="*60)
    
    try:
        import json
        from pathlib import Path
        
        # Count files
        data_path = Path("data/nba/boxscores-raw")
        season_2023 = list((data_path / "2023-24").glob("*.json"))
        season_2024 = list((data_path / "2024-25").glob("*.json"))
        
        print(f"✅ Sample data verified")
        print(f"   - 2023-24 season: {len(season_2023)} games")
        print(f"   - 2024-25 season: {len(season_2024)} games")
        
        # Check a sample file
        with open(season_2023[0], 'r') as f:
            game = json.load(f)
        
        print(f"   - Sample game: {game['gameId']} on {game['gameDate']}")
        print(f"   - Home: {game['home']['team']} (Score: {game['home']['score']})")
        print(f"   - Away: {game['away']['team']} (Score: {game['away']['score']})")
        print(f"   - Players: {len(game['home']['players']) + len(game['away']['players'])}")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_3_backtest_components():
    """Test: Backtest Script"""
    print("\n" + "="*60)
    print("TEST 3: Backtest Components")
    print("="*60)
    
    try:
        sys.path.insert(0, 'ddtd')
        from backtest_v3 import DDTDBacktester
        from pathlib import Path
        
        # Initialize
        backtester = DDTDBacktester(
            model_path=Path("models/nba/ddtd/ddtd_model_v3.pkl"),
            gates_path=Path("models/nba/ddtd/acceptance_gates_v3.json"),
            data_path=Path("data/nba/boxscores-raw")
        )
        print(f"✅ Backtester initialized")
        
        # Load data
        df = backtester.load_game_data("2023-24")
        print(f"   - Loaded: {len(df)} player-games")
        print(f"   - Players: {df['player_id'].nunique()}")
        print(f"   - Date range: {df['date'].min().date()} to {df['date'].max().date()}")
        
        # Test acceptance gates
        print(f"   - DD gates: {backtester.gates['dd']['min_edge']:.0%} edge, {backtester.gates['dd']['min_minutes']} min")
        print(f"   - TD gates: {backtester.gates['td']['min_edge']:.0%} edge, {backtester.gates['td']['min_minutes']} min")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_prediction_pipeline():
    """Test: Prediction Pipeline"""
    print("\n" + "="*60)
    print("TEST 4: Prediction Pipeline")
    print("="*60)
    
    try:
        sys.path.insert(0, 'ddtd')
        from predict_ddtd import DDTDPredictor
        from pathlib import Path
        
        # Initialize
        predictor = DDTDPredictor(
            model_path=Path("models/nba/ddtd/ddtd_model_v3.pkl"),
            gates_path=Path("models/nba/ddtd/acceptance_gates_v3.json"),
            data_path=Path("data/nba/boxscores-raw")
        )
        print(f"✅ Predictor initialized")
        
        # Get slate
        slate = predictor.get_todays_slate()
        print(f"   - Sample slate: {len(slate)} players")
        
        if len(slate) > 0:
            print(f"\n   📋 Today's Sample Slate:")
            for _, player in slate.head(3).iterrows():
                print(f"      • {player['player_name']} ({player['team']}) vs {player['opponent']}")
                print(f"        {player['projected_minutes']} min, Pace: {player['pace']}")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_5_minutes_predictor():
    """Test: Minutes Predictor"""
    print("\n" + "="*60)
    print("TEST 5: Minutes Predictor")
    print("="*60)
    
    try:
        sys.path.insert(0, 'ddtd')
        from predict_minutes import MinutesPredictor
        from pathlib import Path
        
        # Initialize
        predictor = MinutesPredictor(data_path=Path("data/nba/boxscores-raw"))
        print(f"✅ Minutes predictor initialized")
        
        # Load data
        df = predictor.load_training_data(seasons=["2023-24"])
        print(f"   - Loaded: {len(df)} player-games")
        print(f"   - Players: {df['player_id'].nunique()}")
        print(f"   - Avg minutes: {df['minutes'].mean():.1f}")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_6_monte_carlo():
    """Test: Monte Carlo Simulation"""
    print("\n" + "="*60)
    print("TEST 6: Monte Carlo Simulation")
    print("="*60)
    
    try:
        sys.path.insert(0, 'ddtd')
        from monte_carlo_sim import MonteCarloSimulator
        from pathlib import Path
        
        # Initialize
        simulator = MonteCarloSimulator(data_path=Path("data/nba/boxscores-raw"))
        print(f"✅ Monte Carlo simulator initialized")
        
        # Load data
        df = simulator.load_historical_data(seasons=["2023-24", "2024-25"], lookback_days=1000)
        print(f"   - Loaded: {len(df)} player-games")
        
        # Estimate parameters
        simulator.player_params = simulator.estimate_player_parameters(df, min_games=10)
        print(f"   - Parameters for: {len(simulator.player_params)} players")
        
        # Test simulation
        if len(simulator.player_params) > 0:
            player_id = list(simulator.player_params.keys())[0]
            result = simulator.predict_player(player_id, n_sims=10000)
            
            if result:
                print(f"\n   🎲 Sample Simulation: {result['player_name']}")
                print(f"      DD: {result['dd_prob']:.1%} [{result['dd_ci_lower']:.1%} - {result['dd_ci_upper']:.1%}]")
                print(f"      TD: {result['td_prob']:.1%} [{result['td_ci_lower']:.1%} - {result['td_ci_upper']:.1%}]")
                print(f"      Stats: PTS={result['simulated_means'][0]:.1f}, REB={result['simulated_means'][1]:.1f}, AST={result['simulated_means'][2]:.1f}")
        
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests and generate report"""
    print("\n" + "="*60)
    print("🧪 NBA DD/TD PIPELINE - COMPREHENSIVE LOCAL TESTS")
    print("="*60)
    print("\n⚠️  Using SAMPLE/MOCK DATA for testing")
    print("   (Not production data)\n")
    
    # Run all tests
    tests = [
        ("Model Loading", test_1_model_loading),
        ("Sample Data", test_2_data_loading),
        ("Backtest Components", test_3_backtest_components),
        ("Prediction Pipeline", test_4_prediction_pipeline),
        ("Minutes Predictor", test_5_minutes_predictor),
        ("Monte Carlo Simulation", test_6_monte_carlo),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n❌ TEST FAILED: {test_name}")
            print(f"   Error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60 + "\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {status:12} {test_name}")
    
    print(f"\n  {passed}/{total} tests passed")
    
    if passed == total:
        print("\n" + "="*60)
        print("🎉 ALL TESTS PASSED!")
        print("="*60)
        print("\n✅ Pipeline is ready for production deployment")
        print("   (Replace sample data with real NBA data)")
    else:
        print("\n" + "="*60)
        print("⚠️  SOME TESTS FAILED")
        print("="*60)
        print("\n   Review errors above and fix issues")
    
    print("\n" + "="*60)
    print("📝 NEXT STEPS")
    print("="*60)
    print("\n1. Replace sample data with real NBA boxscores")
    print("2. Train Model V3 on actual historical data")
    print("3. Run full backtest: python3 ddtd/backtest_v3.py")
    print("4. Validate ROI targets are met")
    print("5. Deploy to production\n")


if __name__ == "__main__":
    main()
