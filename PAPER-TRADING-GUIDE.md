# Paper Trading Guide - DD/TD Model Validation

## What is Paper Trading?

**Paper trading = tracking bets WITHOUT real money to validate your model works.**

You record what bets you WOULD make, track the outcomes, and see if you're actually profitable before risking real cash.

---

## Why Paper Trade?

Our model shows:
- ✅ Test AUC: 0.8772 (good predictive power)
- ⚠️ Test Edge: 28.8% (suspiciously high)
- ❓ **Unknown**: Do real markets offer these edges?

**We need to prove:**
1. Real sportsbooks have beatable odds
2. Hit rates match model predictions
3. Actual ROI is positive over 50-100 bets

---

## Simple Paper Trading Process

### Step 1: Generate Daily Picks (Manual)

Every day around **5 PM** (before games start):

1. **Run the pick generator:**
```bash
cd ~/Desktop/REPO33/NBA-DDTD-RESEARCH
export ODDS_API_KEY="c5d3fe15e6c5be83b2acd8695cff012b"
python3 scripts/generate_picks_for_rrmodel.py
```

2. **For each pick that meets criteria**, open a spreadsheet and record:
   - Date
   - Player name
   - Game (e.g., "LAL @ BOS")
   - Game time
   - Model probability (e.g., 35%)
   - Your bet: "DD Yes" or "DD No"
   - Projected minutes

3. **Look up REAL odds** on a sportsbook:
   - Go to DraftKings, FanDuel, or BetMGM
   - Search for the player
   - Find "Double-Double" prop
   - Record the odds (e.g., +200, -150)

4. **Calculate your paper bet size:**
   - Virtual bankroll: $10,000
   - Bet 1% per pick = $100
   - Record this in your spreadsheet

5. **Calculate implied edge:**
   - If model says 35% and market is +200 (33%), edge = 2%
   - If edge < 5%, skip the bet (too close)

---

### Step 2: Track Results (Next Day)

Every morning:

1. **Check game results** on ESPN or NBA.com

2. **For each player you "bet" on:**
   - Look up their stats
   - Did they get a double-double?
   - Record Win or Loss

3. **Calculate profit/loss:**
   - If bet $100 at +200 and WON: +$200
   - If bet $100 at +200 and LOST: -$100
   - Update your running bankroll

---

## Simple Spreadsheet Template

Create a Google Sheet with these columns:

| Date | Player | Game | Time | Model % | Market Odds | Market % | Edge | Bet $ | Result | P&L | Bankroll |
|------|--------|------|------|---------|-------------|----------|------|-------|--------|-----|----------|
| 11/20 | Jalen Johnson | ATL@BOS | 7:30 PM | 35% | +200 | 33% | +2% | $100 | - | - | $10,000 |
| 11/20 | Domantas Sabonis | SAC@GSW | 10:00 PM | 45% | -150 | 60% | -15% | SKIP | - | - | $10,000 |
| 11/21 | Jalen Johnson | - | - | - | - | - | - | - | WIN | +$200 | $10,200 |

### Key Columns:

**Before Game:**
- **Date**: Game date
- **Player**: Player name
- **Game**: Teams playing
- **Model %**: Your model's predicted probability
- **Market Odds**: Real odds from sportsbook (+200, -150, etc.)
- **Market %**: Implied probability from odds
- **Edge**: Model % - Market %
- **Bet $**: Amount you're "betting" ($100 typically)

**After Game:**
- **Result**: WIN or LOSS
- **P&L**: Profit or loss on this bet
- **Bankroll**: Running total

---

## Formulas to Know

### Convert Odds to Probability

**Positive odds (+200):**
```
Probability = 100 / (odds + 100)
Example: +200 = 100 / (200 + 100) = 33.3%
```

**Negative odds (-150):**
```
Probability = |odds| / (|odds| + 100)
Example: -150 = 150 / (150 + 100) = 60%
```

### Calculate Profit

**Win at positive odds (+200):**
```
Profit = Bet × (odds / 100)
Example: $100 × (200 / 100) = +$200
```

**Win at negative odds (-150):**
```
Profit = Bet × (100 / |odds|)
Example: $100 × (100 / 150) = +$66.67
```

**Loss (any odds):**
```
Profit = -Bet
Example: -$100
```

---

## Daily Workflow

### Monday - Friday (5:00 PM)

1. **Check today's NBA games** (10-15 games per day)

2. **Run pick generator script**
   ```bash
   python3 scripts/generate_picks_for_rrmodel.py
   ```

3. **For each qualifying player:**
   - Record model prediction
   - Look up odds on DraftKings
   - Calculate edge
   - If edge > 5%, record as paper bet

4. **Expected picks per day:** 2-5 bets

### Next Morning (9:00 AM)

1. **Check NBA scores** (espn.com/nba/scoreboard)

2. **For each paper bet from yesterday:**
   - Look up player's box score
   - Check if they got DD (2+ stats with 10+)
   - Record WIN or LOSS
   - Calculate P&L

3. **Update spreadsheet totals**

---

## What to Look For

### ✅ Good Signs (Keep Going)

After 20-30 bets:
- **Positive ROI** (even 5-10% is great!)
- **Hit rate close to predictions** (within 5-10%)
- **Consistent edge** across different players/teams
- **Bankroll trending up**

Example:
```
25 bets tracked
13 wins, 12 losses (52% hit rate)
Avg model prediction: 48%
Total profit: +$450 (+18% ROI)
✅ Model appears calibrated and profitable
```

### ⚠️ Warning Signs

After 20-30 bets:
- **Negative ROI** (-5% or worse)
- **Hit rate much lower than predictions** (10%+ difference)
- **Markets consistently have better odds** than model suggests
- **Bankroll trending down**

Example:
```
25 bets tracked
8 wins, 17 losses (32% hit rate)
Avg model prediction: 45%
Total loss: -$850 (-34% ROI)
❌ Model NOT working - do not bet real money
```

### 🎯 Validation Criteria (After 50+ Bets)

**GREEN LIGHT (Start small stakes):**
- ✅ ROI > +5%
- ✅ Hit rate within 5% of predictions
- ✅ Positive profit over last 20 bets
- ✅ 50+ bets tracked

**YELLOW LIGHT (Keep paper trading):**
- ⚠️ ROI between 0% and +5%
- ⚠️ Hit rate within 10% of predictions
- ⚠️ Need more data (under 50 bets)

**RED LIGHT (Do NOT bet real money):**
- ❌ ROI < 0%
- ❌ Hit rate off by 10%+
- ❌ Consistent losses
- ❌ Model predictions don't match reality

---

## Common Questions

### Q: How long should I paper trade?

**A:** Minimum 4-6 weeks to get 50-100 bets. If results are clearly bad after 25 bets, you can stop early.

### Q: What if I can't find odds for a player?

**A:** Skip that bet. Only track bets where you can find real market odds.

### Q: Should I bet every pick the model generates?

**A:** No! Only bet if:
1. Model probability > 17% (gate threshold)
2. Edge > 5% (model prob - market prob)
3. Projected minutes > 30
4. You can find market odds

### Q: What if my hit rate is lower than predictions?

**A:** This means the model is overconfident. After 30+ bets, if hit rate is 10%+ lower than predictions, the model needs recalibration.

### Q: What's a realistic ROI to expect?

**A:** 
- Excellent: 15-25% annual ROI
- Good: 10-15% annual ROI
- Acceptable: 5-10% annual ROI
- Amazing: 25%+ annual ROI (probably luck)

### Q: Can I just skip paper trading?

**A:** **NO!** Our model shows 28.8% edge which is suspiciously high. Paper trading will reveal if:
- We're overfitting
- Markets are more efficient than we think
- Our predictions are actually calibrated

**Skipping this step = gambling, not investing.**

---

## Example Week of Paper Trading

### Monday Nov 20
```
Generated 4 picks
- Jalen Johnson DD @ +175 (model 40%, market 36%, edge +4%, SKIP - edge too low)
- Domantas Sabonis DD @ -130 (model 60%, market 56%, edge +4%, SKIP)
- Nikola Jokic DD @ -500 (model 85%, market 83%, edge +2%, SKIP)
- Jaren Jackson Jr DD @ +225 (model 35%, market 31%, edge +4%, SKIP)

No bets - all edges < 5%
```

### Tuesday Nov 21
```
Generated 3 picks
- Giannis Antetokounmpo DD @ -200 (model 70%, market 67%, edge +3%, SKIP)
- Luka Doncic DD @ -180 (model 72%, market 64%, edge +8%, BET $100) ✅
- Julius Randle DD @ +180 (model 42%, market 36%, edge +6%, BET $100) ✅

Placed 2 paper bets totaling $200
```

### Wednesday Nov 22 (Morning - Settle)
```
Luka Doncic - 28 pts, 12 reb, 8 ast → DD YES → WIN +$55.56
Julius Randle - 18 pts, 7 reb, 4 ast → DD NO → LOSS -$100

Tuesday results: -$44.44
Bankroll: $9,955.56
```

**Continue this for 4-6 weeks...**

---

## When to Start Real Money Betting

Only after paper trading shows:
1. ✅ 50+ bets tracked
2. ✅ Overall ROI > +5%
3. ✅ Hit rate matches predictions (within 5-10%)
4. ✅ Last 20 bets are profitable
5. ✅ You understand what you're doing

**Then start with SMALL stakes:**
- $500-1,000 bankroll (not $10k)
- $10-20 per bet (not $100)
- Scale up slowly over months

---

## Tools You'll Need

1. **Spreadsheet**: Google Sheets (free) or Excel
2. **Sportsbook** (for odds, no account needed): 
   - DraftKings.com
   - FanDuel.com
   - BetMGM.com
3. **Box scores** (for results):
   - ESPN.com/nba
   - NBA.com
4. **Your model** (already have):
   - `python3 scripts/generate_picks_for_rrmodel.py`

---

## The Honest Truth

**Paper trading will likely show:**
- ❌ Real edges are smaller than 28.8%
- ❌ Many days have no qualifying bets
- ⚠️ ROI is probably 5-15% (not 28%)
- ⚠️ You'll have losing weeks

**But that's GOOD!** Better to learn this now without losing real money.

**If paper trading shows positive ROI > 5% over 50+ bets, you have a real edge.**

Even 8-10% annual ROI would be **phenomenal** for sports betting.

---

## Next Steps

1. **Create spreadsheet** (use template above)
2. **Generate today's picks** (run script)
3. **Look up real odds** (DraftKings/FanDuel)
4. **Record bets** in spreadsheet
5. **Check results tomorrow**
6. **Repeat for 4-6 weeks**
7. **Analyze results**
8. **Decide**: Real money or back to drawing board

**START TODAY!** The sooner you start paper trading, the sooner you'll know if this works.

---

## Need Help?

Common issues:

**"Script doesn't generate picks"**
- Check if there are games today
- Verify API key is set
- Model might not find qualifying bets (normal)

**"Can't find odds for a player"**
- Not all sportsbooks offer DD props
- Some players aren't available
- Skip those bets

**"How do I know if a player got DD?"**
- Go to ESPN.com
- Search player name
- Look at game log
- Need 2+ categories with 10+
  - 20 pts, 12 reb = DD ✅
  - 15 pts, 8 reb, 6 ast = No DD ❌

---

**Remember: Paper trading is FREE. Real losses are NOT. Do this right.**
