"""
Quick backtest runner for Model V3 with progress output
"""

import sys
sys.stdout.reconfigure(line_buffering=True)  # Force line buffering

from pathlib import Path
from ddtd.backtest_v3 import DDTDBacktester

def main():
    """Run backtest with progress"""
    print("=" * 60)
    print("🎯 BACKTEST MODEL V3 - HISTORICAL VALIDATION")
    print("=" * 60)
    print()
    
    MODEL_PATH = Path("models/nba/ddtd/ddtd_model_v3.pkl")
    GATES_PATH = Path("models/nba/ddtd/acceptance_gates_v3.json")
    DATA_PATH = Path("data/nba/boxscores-raw")
    
    # Initialize backtester
    print("Loading model and data...")
    backtester = DDTDBacktester(
        model_path=MODEL_PATH,
        gates_path=GATES_PATH,
        data_path=DATA_PATH
    )
    print()
    
    # Run backtest
    print("Running backtest...")
    print("(This will take a few minutes - processing 166 days)")
    print()
    
    results = backtester.run_backtest(
        season="2023-24",
        start_date="2023-11-01",
        end_date="2024-04-15"
    )
    
    if results:
        print("\n")
        backtester.print_results(results)
        
        # Save
        output_path = "results/backtest_v3_results.json"
        backtester.save_results(results, output_path)
    else:
        print("\n⚠️  No results generated")

if __name__ == '__main__':
    main()
