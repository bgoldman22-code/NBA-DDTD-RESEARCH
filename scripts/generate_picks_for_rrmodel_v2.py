"""
Generate Daily NBA DD/TD Picks for RRMODEL V2
Outputs TWO tables:
1. Recommended Picks (passing gates) with Kelly sizing
2. All players >35% probability

Includes live odds and proper bankroll management
"""

import os
import sys
import json
import pickle
import requests
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Configuration
ODDS_API_KEY = os.environ.get('ODDS_API_KEY')
BANKROLL = 4500  # $4,500 bankroll
UNIT_SIZE = 10   # $10 per unit
MAX_BET_PCT = 0.05  # Max 5% of bankroll per bet
KELLY_FRACTION = 0.25  # Quarter Kelly for safety

if not ODDS_API_KEY:
    print("❌ ERROR: ODDS_API_KEY environment variable not set")
    sys.exit(1)

def american_to_prob(odds):
    """Convert American odds to implied probability"""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def calculate_td_kelly_scale(td_prob, l20_td_rate, edge):
    """
    Calculate scaled Kelly fraction for TD bets based on risk factors.
    TDs are rare/high-variance, so we use conservative sizing with harsh penalties.
    
    Base: 0.25% Kelly (sprinkle) | Max: 5% Kelly | Brutal L20 penalty
    
    Args:
        td_prob: Model probability for TD
        l20_td_rate: Recent TD rate (last 20 games)
        edge: Model edge over implied odds
    
    Returns:
        Kelly fraction to use (0.0025 to 0.05)
    """
    min_kelly = 0.0025   # 0.25% minimum (true sprinkle)
    max_kelly = 0.05     # 5% max (way lower than DD Quarter Kelly)
    
    # Probability multiplier (0.5 to 3.0)
    if td_prob >= 0.70:
        prob_mult = 3.0
    elif td_prob >= 0.60:
        prob_mult = 2.0
    elif td_prob >= 0.50:
        prob_mult = 1.5
    elif td_prob >= 0.40:
        prob_mult = 1.0
    elif td_prob >= 0.30:
        prob_mult = 0.7
    else:
        prob_mult = 0.5
    
    # L20 TD Rate multiplier (0.05 to 3.0) - EXTREMELY HARSH
    if l20_td_rate >= 0.25:
        history_mult = 3.0    # Elite TD consistency
    elif l20_td_rate >= 0.20:
        history_mult = 2.0
    elif l20_td_rate >= 0.15:
        history_mult = 1.5
    elif l20_td_rate >= 0.10:
        history_mult = 1.0
    elif l20_td_rate >= 0.05:
        history_mult = 0.4    # Occasional TDs
    else:
        history_mult = 0.05   # BRUTAL penalty for no recent TDs (1/20th)
    
    # Edge multiplier (0.8 to 2.0)
    if edge >= 0.40:
        edge_mult = 2.0
    elif edge >= 0.30:
        edge_mult = 1.5
    elif edge >= 0.20:
        edge_mult = 1.2
    elif edge >= 0.10:
        edge_mult = 1.0
    else:
        edge_mult = 0.8
    
    # MULTIPLY all factors (compound penalty - one weakness tanks the bet)
    total_mult = prob_mult * history_mult * edge_mult
    
    # Apply to base Kelly, cap at max
    kelly_fraction = min_kelly * total_mult
    kelly_fraction = min(kelly_fraction, max_kelly)
    kelly_fraction = max(kelly_fraction, min_kelly)
    
    return kelly_fraction

def calculate_kelly_bet(edge, odds_american, bankroll=BANKROLL, fraction=KELLY_FRACTION, 
                       is_td=False, td_prob=None, l20_td_rate=None):
    """
    Calculate Kelly criterion bet size
    
    Args:
        edge: Model edge (model_prob - implied_prob)
        odds_american: American odds (e.g., +200, -150)
        bankroll: Total bankroll
        fraction: Kelly fraction (0.25 = quarter Kelly for DD)
        is_td: Whether this is a TD bet (uses scaled Kelly)
        td_prob: Model probability (for TD scaling)
        l20_td_rate: Recent TD rate (for TD scaling)
    
    Returns:
        dict with bet_amount, bet_pct, units
    """
    # Convert American odds to decimal
    if odds_american > 0:
        decimal_odds = (odds_american / 100) + 1
    else:
        decimal_odds = (100 / abs(odds_american)) + 1
    
    # Kelly formula: f = (bp - q) / b
    # where b = decimal_odds - 1, p = model_prob, q = 1 - p
    b = decimal_odds - 1
    p = edge + (1 / decimal_odds)  # Back-calculate model prob from edge
    q = 1 - p
    
    kelly_pct = (b * p - q) / b
    kelly_pct = max(0, kelly_pct)  # No negative bets
    
    # Apply fraction - use scaled fraction for TDs
    if is_td and td_prob is not None and l20_td_rate is not None:
        fraction = calculate_td_kelly_scale(td_prob, l20_td_rate, edge)
    
    kelly_pct *= fraction
    
    # Apply max bet limit
    kelly_pct = min(kelly_pct, MAX_BET_PCT)
    
    bet_amount = bankroll * kelly_pct
    units = bet_amount / UNIT_SIZE
    
    return {
        'bet_amount': round(bet_amount, 2),
        'bet_pct': round(kelly_pct * 100, 2),
        'units': round(units, 2)
    }

def fetch_player_props_odds():
    """Fetch DD/TD odds from The Odds API"""
    events_url = "https://api.the-odds-api.com/v4/sports/basketball_nba/events"
    
    try:
        print("📡 Fetching today's NBA events...")
        events_response = requests.get(events_url, params={'apiKey': ODDS_API_KEY}, timeout=15)
        events_response.raise_for_status()
        events = events_response.json()
        
        remaining = events_response.headers.get('x-requests-remaining', 'unknown')
        print(f"   API requests remaining: {remaining}")
        
        if not events:
            return pd.DataFrame()
        
        odds_data = []
        
        for event in events:
            event_id = event.get('id')
            away_team = event.get('away_team')
            home_team = event.get('home_team')
            
            odds_url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/events/{event_id}/odds"
            odds_params = {
                'apiKey': ODDS_API_KEY,
                'regions': 'us',
                'markets': 'player_double_double,player_triple_double',
                'oddsFormat': 'american'
            }
            
            try:
                odds_response = requests.get(odds_url, params=odds_params, timeout=15)
                odds_response.raise_for_status()
                event_odds = odds_response.json()
                
                for bookmaker in event_odds.get('bookmakers', []):
                    bookmaker_name = bookmaker.get('title', 'Unknown')
                    for market in bookmaker.get('markets', []):
                        market_key = market.get('key')
                        if market_key in ['player_double_double', 'player_triple_double']:
                            # Capture BOTH Yes and No outcomes to detect inversions
                            outcomes_dict = {}
                            for outcome in market.get('outcomes', []):
                                outcome_name = outcome.get('name')
                                if outcome_name in ['Yes', 'No']:
                                    outcomes_dict[outcome_name] = {
                                        'player_name': outcome.get('description'),
                                        'odds': outcome.get('price')
                                    }
                            
                            # Add if we have at least one side (preferably both for validation)
                            if outcomes_dict:
                                # Use the player name from whichever outcome exists
                                player_name_key = 'Yes' if 'Yes' in outcomes_dict else 'No'
                                odds_data.append({
                                    'player_name': outcomes_dict[player_name_key]['player_name'],
                                    'bet_type': 'DD' if market_key == 'player_double_double' else 'TD',
                                    'odds_yes': outcomes_dict.get('Yes', {}).get('odds'),
                                    'odds_no': outcomes_dict.get('No', {}).get('odds'),
                                    'bookmaker': bookmaker_name,
                                    'game': f"{away_team} @ {home_team}"
                                })
            except:
                continue
        
        return pd.DataFrame(odds_data)
    
    except Exception as e:
        print(f"⚠️  Error fetching odds: {e}")
        return pd.DataFrame()

def load_historical_data():
    """Load historical data including current season"""
    data_dir = Path('data/nba/boxscores-raw')
    records = []
    seasons = ['2023-24', '2024-25', '2025-26']  # Include current season
    
    print("📥 Loading historical data...")
    for season in seasons:
        season_dir = data_dir / season
        if season_dir.exists():
            files = list(season_dir.glob('*.json'))
            print(f"   {season}: {len(files)} games")
            
            for file_path in files:
                try:
                    with open(file_path) as f:
                        game = json.load(f)
                    
                    for team_key in ['home', 'away']:
                        for player in game.get(team_key, {}).get('players', []):
                            stats = player.get('stats', {})
                            if stats.get('min', 0) > 0:
                                pts, reb, ast = stats.get('pts', 0), stats.get('reb', 0), stats.get('ast', 0)
                                records.append({
                                    'gameDate': game.get('gameDate', ''),
                                    'playerId': player.get('playerId', ''),
                                    'playerName': player.get('name', ''),
                                    'minutes': stats.get('min', 0),
                                    'points': pts,
                                    'rebounds': reb,
                                    'assists': ast,
                                    'steals': stats.get('stl', 0),
                                    'blocks': stats.get('blk', 0),
                                    'turnovers': stats.get('tov', 0),
                                    'fgm': stats.get('fgm', 0),
                                    'fga': stats.get('fga', 0),
                                    'fg3m': stats.get('fg3m', 0),
                                    'fg3a': stats.get('fg3a', 0),
                                    'ftm': stats.get('ftm', 0),
                                    'fta': stats.get('fta', 0),
                                    'dd': int(sum([pts >= 10, reb >= 10, ast >= 10]) >= 2),
                                    'td': int(pts >= 10 and reb >= 10 and ast >= 10)
                                })
                except:
                    continue
    
    df = pd.DataFrame(records)
    df['gameDate'] = pd.to_datetime(df['gameDate'])
    print(f"✅ Loaded {len(df):,} player-games\n")
    
    return df

def calculate_player_features(df, player_name, lookback=20):
    """Calculate features for a specific player"""
    player_data = df[df['playerName'] == player_name]
    
    if player_data.empty:
        player_data = df[df['playerName'].str.lower() == player_name.lower()]
    
    if player_data.empty:
        player_data = df[df['playerName'].str.contains(player_name.split()[0], case=False, na=False)]
    
    if player_data.empty or len(player_data) < 10:
        return None
    
    player_data = player_data.sort_values('gameDate', ascending=False)
    history = player_data.iloc[:lookback]
    
    features = {
        'playerName': player_name,
        'avg_minutes': history['minutes'].mean(),
        'avg_points': history['points'].mean(),
        'avg_rebounds': history['rebounds'].mean(),
        'avg_assists': history['assists'].mean(),
        'avg_steals': history['steals'].mean(),
        'avg_blocks': history['blocks'].mean(),
        'avg_turnovers': history['turnovers'].mean(),
        'fg_pct': history['fgm'].sum() / max(history['fga'].sum(), 1),
        'fg3_pct': history['fg3m'].sum() / max(history['fg3a'].sum(), 1),
        'ft_pct': history['ftm'].sum() / max(history['fta'].sum(), 1),
        'avg_fga': history['fga'].mean(),
        'avg_fta': history['fta'].mean(),
        'dd_rate': history['dd'].mean(),
        'td_rate': history['td'].mean(),
        'l5_minutes': history.iloc[:5]['minutes'].mean(),
        'l5_points': history.iloc[:5]['points'].mean(),
        'l5_rebounds': history.iloc[:5]['rebounds'].mean(),
        'l5_assists': history.iloc[:5]['assists'].mean(),
        'l5_dd_rate': history.iloc[:5]['dd'].mean(),
        'std_points': history['points'].std(),
        'std_rebounds': history['rebounds'].std(),
        'std_assists': history['assists'].std(),
        'min_games_played': len(history),
        'pts_reb': history['points'].mean() + history['rebounds'].mean(),
        'pts_ast': history['points'].mean() + history['assists'].mean(),
        'reb_ast': history['rebounds'].mean() + history['assists'].mean(),
        'total_production': history['points'].mean() + history['rebounds'].mean() + history['assists'].mean(),
        'per_minute_pts': history['points'].mean() / max(history['minutes'].mean(), 1),
        'per_minute_reb': history['rebounds'].mean() / max(history['minutes'].mean(), 1),
        'per_minute_ast': history['assists'].mean() / max(history['minutes'].mean(), 1),
        'proj_minutes': history['minutes'].mean()
    }
    
    return features

def main():
    print("=" * 60)
    print("🏀 NBA DD/TD PICKS GENERATOR V2")
    print("=" * 60)
    print()
    
    # Load model
    print("🤖 Loading Model V3...")
    with open('models/nba/ddtd/ddtd_model_v3.pkl', 'rb') as f:
        model_data = pickle.load(f)
    
    with open('models/nba/ddtd/acceptance_gates_v3.json') as f:
        gates = json.load(f)
    
    print("✅ Model loaded\n")
    
    # Fetch odds
    odds_df = fetch_player_props_odds()
    
    if odds_df.empty:
        print("❌ No odds data available")
        sys.exit(1)
    
    print(f"✅ Fetched odds for {len(odds_df)} props\n")
    
    # Load historical data
    historical_df = load_historical_data()
    
    # Get unique players
    players_to_predict = odds_df['player_name'].unique()
    print(f"🎯 Generating predictions for {len(players_to_predict)} players...\n")
    
    predictions = []
    
    for player_name in players_to_predict:
        features = calculate_player_features(historical_df, player_name)
        
        if features is None:
            continue
        
        # Create feature vector
        feature_names = model_data['feature_columns']
        X = pd.DataFrame([features])[feature_names].fillna(0)
        
        # Predict
        dd_raw = model_data['dd_model'].predict_proba(X)[0, 1]
        td_raw = model_data['td_model'].predict_proba(X)[0, 1]
        dd_prob = model_data['dd_calibrator'].transform([dd_raw])[0]
        td_prob = model_data['td_calibrator'].transform([td_raw])[0]
        
        # Get odds
        player_odds = odds_df[odds_df['player_name'] == player_name]
        
        def pick_best_odds_side(odds_data, model_prob):
            """
            We ALWAYS bet YES (player will get DD/TD), but need to detect which outcome 
            represents "YES" because some bookmakers invert the labels.
            
            Strategy: Compare implied probabilities of Yes vs No outcomes.
            - If model_prob is HIGH and implied_yes is HIGH → correctly labeled (use Yes odds)
            - If model_prob is HIGH but implied_yes is LOW → inverted (use No odds)
            - If only one side available, use it (can't detect inversion)
            """
            if odds_data.empty:
                return None, None
            
            # For each bookmaker, determine which side represents "will happen"
            best_odds = -999999
            best_bookmaker = None
            
            for idx, row in odds_data.iterrows():
                odds_yes = row['odds_yes']
                odds_no = row['odds_no']
                
                # Handle cases where only one side is available
                if pd.isna(odds_yes) and pd.isna(odds_no):
                    continue
                elif pd.isna(odds_no):
                    # Only Yes side - assume correct labeling
                    selected_odds = odds_yes
                elif pd.isna(odds_yes):
                    # Only No side - assume it means "will happen" (inverted)
                    selected_odds = odds_no
                else:
                    # Both sides available - detect inversion by implied probability
                    implied_yes = american_to_prob(odds_yes)
                    implied_no = american_to_prob(odds_no)
                    
                    # We ALWAYS want to bet YES (will happen)
                    # Determine which outcome actually represents "will happen"
                    if implied_yes > implied_no:
                        # "Yes" is the favorite = correctly labeled as "will happen"
                        selected_odds = odds_yes
                    else:
                        # "No" is the favorite = inverted labeling, "No" means "will happen"
                        selected_odds = odds_no
                
                # Track best odds (most positive for underdogs, least negative for favorites)
                if pd.notna(selected_odds) and selected_odds > best_odds:
                    best_odds = selected_odds
                    best_bookmaker = row['bookmaker']
            
            return (best_odds if best_odds > -999999 else None), best_bookmaker
        
        # Get best odds and bookmaker for DD
        dd_odds_data = player_odds[player_odds['bet_type'] == 'DD']
        dd_best, dd_bookmaker = pick_best_odds_side(dd_odds_data, dd_prob)
        
        # Get best odds and bookmaker for TD
        td_odds_data = player_odds[player_odds['bet_type'] == 'TD']
        td_best, td_bookmaker = pick_best_odds_side(td_odds_data, td_prob)
        
        # Get game info
        game_info = player_odds['game'].iloc[0] if not player_odds.empty else 'Unknown'
        
        predictions.append({
            'player': player_name,
            'dd_prob': dd_prob,
            'td_prob': td_prob,
            'dd_odds': dd_best,
            'td_odds': td_best,
            'dd_bookmaker': dd_bookmaker,
            'td_bookmaker': td_bookmaker,
            'avg_minutes': features['avg_minutes'],
            'l20_dd_rate': features['dd_rate'],
            'l20_td_rate': features['td_rate'],
            'avg_pts': features['avg_points'],
            'avg_reb': features['avg_rebounds'],
            'avg_ast': features['avg_assists'],
            'game': game_info
        })
    
    pred_df = pd.DataFrame(predictions)
    
    # Calculate edges and apply gates
    def odds_to_implied_prob(odds):
        if pd.isna(odds):
            return None
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)
    
    pred_df['dd_implied_prob'] = pred_df['dd_odds'].apply(odds_to_implied_prob)
    pred_df['td_implied_prob'] = pred_df['td_odds'].apply(odds_to_implied_prob)
    pred_df['dd_edge'] = pred_df['dd_prob'] - pred_df['dd_implied_prob']
    pred_df['td_edge'] = pred_df['td_prob'] - pred_df['td_implied_prob']
    
    # Apply acceptance gates for DD
    dd_gate = gates['dd']
    dd_standard = (pred_df['dd_prob'] >= dd_gate['min_prob']) & \
                 (pred_df['avg_minutes'] >= dd_gate['min_minutes']) & \
                 (pred_df['dd_odds'].notna()) & \
                 (pred_df['dd_edge'] > 0)
    
    dd_elite = (pred_df['dd_prob'] >= dd_gate.get('elite_prob', 0.90)) & \
              (pred_df['avg_minutes'] >= dd_gate.get('elite_minutes', 29)) & \
              (pred_df['dd_odds'].notna()) & \
              (pred_df['dd_edge'] > 0)
    
    dd_picks = pred_df[dd_standard | dd_elite].copy()
    
    # Apply acceptance gates for TD
    td_gate = gates['td']
    td_standard = (pred_df['td_prob'] >= td_gate['min_prob']) & \
                 (pred_df['avg_minutes'] >= td_gate['min_minutes']) & \
                 (pred_df['td_odds'].notna()) & \
                 (pred_df['td_edge'] > 0)
    
    td_elite = (pred_df['td_prob'] >= td_gate.get('elite_prob', 0.80)) & \
              (pred_df['avg_minutes'] >= td_gate.get('elite_minutes', 33)) & \
              (pred_df['td_odds'].notna()) & \
              (pred_df['td_edge'] > 0)
    
    td_picks = pred_df[td_standard | td_elite].copy()
    
    # Calculate Kelly sizing for picks
    if not dd_picks.empty:
        dd_picks['kelly_data'] = dd_picks.apply(
            lambda row: calculate_kelly_bet(row['dd_edge'], row['dd_odds']), axis=1
        )
        dd_picks['bet_units'] = dd_picks['kelly_data'].apply(lambda x: x['units'])
        dd_picks['bet_amount'] = dd_picks['kelly_data'].apply(lambda x: x['bet_amount'])
        dd_picks = dd_picks.sort_values('dd_edge', ascending=False)
    
    if not td_picks.empty:
        # Use SCALED Kelly for TDs (accounts for probability, L20 rate, and edge)
        td_picks['kelly_data'] = td_picks.apply(
            lambda row: calculate_kelly_bet(
                row['td_edge'], 
                row['td_odds'],
                is_td=True,
                td_prob=row['td_prob'],
                l20_td_rate=row['l20_td_rate']
            ), axis=1
        )
        td_picks['bet_units'] = td_picks['kelly_data'].apply(lambda x: x['units'])
        td_picks['bet_amount'] = td_picks['kelly_data'].apply(lambda x: x['bet_amount'])
        td_picks = td_picks.sort_values('td_edge', ascending=False)
    
    # Get all >35% probability players
    high_prob_dd = pred_df[pred_df['dd_prob'] >= 0.35].copy()
    high_prob_dd = high_prob_dd.sort_values('dd_prob', ascending=False)
    
    # Build output JSON
    output = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'model_version': 'v3',
        'bankroll': BANKROLL,
        'unit_size': UNIT_SIZE,
        'kelly_fraction': KELLY_FRACTION,
        'recommended_picks': {
            'dd': [],
            'td': []
        },
        'high_probability': []
    }
    
    # Add recommended DD picks
    for _, pick in dd_picks.iterrows():
        output['recommended_picks']['dd'].append({
            'player': pick['player'],
            'game': pick['game'],
            'model_prob': round(pick['dd_prob'], 4),
            'best_odds': int(pick['dd_odds']),
            'bookmaker': pick['dd_bookmaker'],
            'implied_prob': round(pick['dd_implied_prob'], 4),
            'edge': round(pick['dd_edge'], 4),
            'bet_units': round(pick['bet_units'], 2),
            'bet_amount': round(pick['bet_amount'], 2),
            'avg_minutes': round(pick['avg_minutes'], 1),
            'l20_dd_rate': round(pick['l20_dd_rate'], 3),
            'stats': {
                'pts': round(pick['avg_pts'], 1),
                'reb': round(pick['avg_reb'], 1),
                'ast': round(pick['avg_ast'], 1)
            }
        })
    
    # Add recommended TD picks
    for _, pick in td_picks.iterrows():
        output['recommended_picks']['td'].append({
            'player': pick['player'],
            'game': pick['game'],
            'model_prob': round(pick['td_prob'], 4),
            'best_odds': int(pick['td_odds']),
            'bookmaker': pick['td_bookmaker'],
            'implied_prob': round(pick['td_implied_prob'], 4),
            'edge': round(pick['td_edge'], 4),
            'bet_units': round(pick['bet_units'], 2),
            'bet_amount': round(pick['bet_amount'], 2),
            'avg_minutes': round(pick['avg_minutes'], 1),
            'l20_td_rate': round(pick['l20_td_rate'], 3),
            'stats': {
                'pts': round(pick['avg_pts'], 1),
                'reb': round(pick['avg_reb'], 1),
                'ast': round(pick['avg_ast'], 1)
            }
        })
    
    # Add high probability players
    for _, player in high_prob_dd.iterrows():
        has_positive_edge = player['dd_edge'] > 0 if pd.notna(player['dd_edge']) else False
        
        output['high_probability'].append({
            'player': player['player'],
            'game': player['game'],
            'model_prob': round(player['dd_prob'], 4),
            'best_odds': int(player['dd_odds']) if pd.notna(player['dd_odds']) else None,
            'bookmaker': player['dd_bookmaker'],
            'implied_prob': round(player['dd_implied_prob'], 4) if pd.notna(player['dd_implied_prob']) else None,
            'edge': round(player['dd_edge'], 4) if pd.notna(player['dd_edge']) else None,
            'has_positive_edge': has_positive_edge,
            'avg_minutes': round(player['avg_minutes'], 1),
            'l20_dd_rate': round(player['l20_dd_rate'], 3),
            'stats': {
                'pts': round(player['avg_pts'], 1),
                'reb': round(player['avg_reb'], 1),
                'ast': round(player['avg_ast'], 1)
            }
        })
    
    # Add summary
    dd_units = dd_picks['bet_units'].sum() if not dd_picks.empty else 0
    dd_amount = dd_picks['bet_amount'].sum() if not dd_picks.empty else 0
    td_units = td_picks['bet_units'].sum() if not td_picks.empty else 0
    td_amount = td_picks['bet_amount'].sum() if not td_picks.empty else 0
    
    output['summary'] = {
        'total_recommended_dd': len(dd_picks),
        'total_recommended_td': len(td_picks),
        'total_high_probability': len(high_prob_dd),
        'total_recommended_units': round(dd_units + td_units, 2),
        'total_recommended_amount': round(dd_amount + td_amount, 2)
    }
    
    # Save to file
    output_dir = Path('data/nba')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'ddtd_today_picks.json'
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print("=" * 60)
    print("✅ PICKS GENERATED")
    print("=" * 60)
    print(f"Recommended DD: {len(dd_picks)}")
    print(f"Recommended TD: {len(td_picks)}")
    print(f"High Probability (>35%): {len(high_prob_dd)}")
    print(f"Total Units: {output['summary']['total_recommended_units']}")
    print(f"Total Amount: ${output['summary']['total_recommended_amount']}")
    print(f"\n📁 Saved to: {output_file}")
    print("=" * 60)

if __name__ == '__main__':
    main()
