"""
Test TD Kelly Scaling Formula
Designed to give "sprinkle" bets on high-variance TD plays
"""

def calculate_td_kelly_scale(td_prob, l20_td_rate, edge, max_kelly_td=0.05):
    """
    Ultra-conservative TD Kelly with HARSH L20 penalty
    Base: 0.25% Kelly minimum (true sprinkle)
    Max: 5% Kelly (default, configurable) - way lower than DD Quarter Kelly
    
    Uses MULTIPLICATIVE penalty - one weak factor tanks the bet
    """
    min_kelly = 0.0025   # 0.25% minimum (true sprinkle)
    max_kelly = max_kelly_td  # Default 5%
    
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
    
    # MULTIPLY all factors (compound penalty)
    total_mult = prob_mult * history_mult * edge_mult
    
    # Apply to base Kelly, cap at max
    kelly_fraction = min_kelly * total_mult
    kelly_fraction = min(kelly_fraction, max_kelly)
    kelly_fraction = max(kelly_fraction, min_kelly)
    
    return {
        'kelly_fraction': kelly_fraction,
        'prob_mult': prob_mult,
        'hist_mult': history_mult,
        'edge_mult': edge_mult,
        'total_mult': total_mult
    }

if __name__ == '__main__':
    print('🎯 SPRINKLE-FOCUSED TD Kelly Scaling')
    print('Base: 0.25% Kelly | Max: 5% Kelly | Brutal Penalties for No L20 TDs')
    print('=' * 75)
    print()
    
    scenarios = [
        ('Nikola Jokic (30% L20 TD)', 0.75, 0.30, 0.40),
        ('Luka Doncic (20% L20 TD)', 0.60, 0.20, 0.30),
        ('Domantas Sabonis (15% L20)', 0.50, 0.15, 0.25),
        ('Good player (10% L20)', 0.45, 0.10, 0.25),
        ('🔥 SENGUN TODAY (0% L20)', 0.455, 0.00, 0.301),
        ('Speculative (5% L20)', 0.35, 0.05, 0.20),
    ]
    
    print(f'{"Player":<30} {"Prob":>6} {"L20":>6} {"Edge":>6} | {"Kelly":>7} | {"Units":>7} | Potential Win')
    print('-' * 75)
    
    for name, prob, l20, edge in scenarios:
        result = calculate_td_kelly_scale(prob, l20, edge)
        units = (4500 * result['kelly_fraction']) / 10
        potential = units * 10 * 5.5  # Assuming +550 odds
        
        marker = '🔥' if '0% L20' in name else '  '
        print(f'{marker} {name:<28} {prob:>5.1%} {l20:>5.1%} {edge:>5.1%} | {result["kelly_fraction"]:>6.2%} | {units:>6.1f}U | ${potential:>5.0f}')
    
    print()
    print('=' * 75)
    print('🔥 Sengun Detailed Breakdown:')
    sengun = calculate_td_kelly_scale(0.455, 0.0, 0.301)
    print(f'  Probability: 45.5% → x{sengun["prob_mult"]:.2f} multiplier')
    print(f'  L20 TD Rate: 0.0%  → x{sengun["hist_mult"]:.2f} multiplier (OUCH!)')
    print(f'  Edge: 30.1%        → x{sengun["edge_mult"]:.2f} multiplier')
    print(f'  Total Multiplier:  → x{sengun["total_mult"]:.2f}')
    print()
    print(f'  1% base Kelly × {sengun["total_mult"]:.2f} = {sengun["kelly_fraction"]:.2%}')
    sengun_units = (4500 * sengun['kelly_fraction']) / 10
    print(f'  Bet: ${4500 * sengun["kelly_fraction"]:.0f} = {sengun_units:.1f} units')
    print()
    print(f'  💰 If Sengun hits TD at +550: Win ${sengun_units * 10 * 5.5:.0f}')
    print(f'  📊 Your "vibe" was 0.5-1.5U ($5-$15)')
    print(f'  ✅ This formula gives {sengun_units:.1f}U - {"Perfect sprinkle!" if 0.5 <= sengun_units <= 1.5 else "Needs adjustment"}')
