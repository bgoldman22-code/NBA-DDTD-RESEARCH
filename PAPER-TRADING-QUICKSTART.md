# Paper Trading Quick Start

## Daily Routine (5 minutes/day)

### Every Evening (5 PM before games)

```bash
# 1. Generate picks
cd ~/Desktop/REPO33/NBA-DDTD-RESEARCH
export ODDS_API_KEY="c5d3fe15e6c5be83b2acd8695cff012b"
python3 scripts/generate_picks_for_rrmodel.py

# 2. For each pick:
#    - Open DraftKings.com
#    - Search player name
#    - Find "Double-Double" prop
#    - Record odds in spreadsheet
#    - Calculate edge: Model % - Market %
#    - If edge > 5%, record as paper bet ($100)
```

### Every Morning (5 minutes)

```
# 1. Check results
#    - Go to ESPN.com/nba/scoreboard
#    - Click on each game
#    - Find your players' stats
#    - Did they get DD? (2+ stats with 10+)

# 2. Update spreadsheet
#    - Record WIN or LOSS
#    - Calculate profit/loss
#    - Update running bankroll
```

---

## Odds Conversion Cheat Sheet

| Odds | Probability | $100 Bet Wins |
|------|-------------|---------------|
| +100 | 50% | $100 |
| +150 | 40% | $150 |
| +200 | 33% | $200 |
| +250 | 29% | $250 |
| +300 | 25% | $300 |
| -110 | 52% | $91 |
| -125 | 56% | $80 |
| -150 | 60% | $67 |
| -200 | 67% | $50 |
| -300 | 75% | $33 |

---

## When to Bet (Paper or Real)

✅ **BET IF:**
- Model probability > 17%
- Edge > 5% (Model % - Market %)
- Projected minutes > 30
- Can find market odds

❌ **SKIP IF:**
- Edge < 5% (too close)
- Can't find market odds
- Player questionable/injured
- Late scratch risk

---

## Validation Milestones

| Bets | Milestone | Action |
|------|-----------|--------|
| 10 | Early check | Look for obvious issues |
| 25 | First review | Check hit rate vs predictions |
| 50 | Validation | Decide if model works |
| 100 | Confidence | Ready for real money (if positive) |

---

## Red Flags 🚩

**STOP if you see:**
- Negative ROI after 30+ bets
- Hit rate 10%+ below predictions
- Losing 60%+ of last 20 bets
- Can't find market odds consistently
- Model predictions way off reality

---

## Success Criteria ✅

**After 50+ paper bets, proceed to real money IF:**
1. Overall ROI > 5%
2. Hit rate within 5-10% of predictions
3. Last 20 bets are profitable
4. You understand the process
5. You're comfortable with variance

**Start with:**
- $500 bankroll (not $10k)
- $10-20 bets (not $100)
- 1-2 bets/day max
- Scale slowly over 3-6 months

---

## Expected Reality Check

**What paper trading will likely show:**
- Real edges: 5-12% (not 28.8%)
- Hit rate: 45-55% on DD bets
- Some days: No qualifying bets
- Variance: Will have losing weeks
- ROI: 8-15% if model works (still great!)

**This is NORMAL and GOOD.**

Sports betting is **hard**. Even 8% ROI is **phenomenal**.

If you see these results, the model works!

---

## Resources

**Odds lookup (free, no account):**
- https://sportsbook.draftkings.com/
- https://sportsbook.fanduel.com/
- https://sports.betmgm.com/

**Box scores (free):**
- https://www.espn.com/nba/scoreboard
- https://www.nba.com/stats

**Your tools:**
- Spreadsheet: `paper_trading_tracker.csv`
- Pick generator: `scripts/generate_picks_for_rrmodel.py`
- This guide: `PAPER-TRADING-GUIDE.md`

---

## FAQ

**Q: How many bets per day?**
A: Usually 0-5. Some days none qualify.

**Q: What if I miss a day?**
A: No problem. Just continue next day.

**Q: Should I bet player props or team totals?**
A: Only DD/TD props (what model is trained for).

**Q: What if odds change after I record them?**
A: Use odds at time of recording. Track line movement if curious.

**Q: Can I paper trade in bulk (look back historically)?**
A: No - you'd know the outcomes. Must be forward-looking.

---

**START TODAY!** 

The sooner you start paper trading, the sooner you'll know if this works.

**Remember: Paper losses teach you. Real losses hurt you. Be patient.**
