# CALIBRATION FIX PLAN
**Date:** December 4, 2025

---

## 🔍 ROOT CAUSE IDENTIFIED

**The calibration issue has TWO causes:**

### 1. ✅ Data Corruption (FIXED on Dec 3)
- **When:** ESPN scraper bug from unknown date until Dec 3, 2025
- **What:** Stats mapped to wrong array indices (rebounds, assists wrong)
- **Impact:** All data scraped before Dec 3 was corrupted
- **Status:** ✅ Fixed and re-scraped on Dec 3

### 2. 🚨 Model Trained on OLD Data (NEEDS FIX)
- **Model file:** `models/nba/ddtd/ddtd_model_v3.pkl`
- **Training date:** November 20, 2025 (BEFORE the fix)
- **Data files:** Updated Dec 3, 2025 (AFTER the fix)
- **Problem:** Model was trained on corrupted data!
- **Status:** ❌ Needs retraining

---

## 📊 EVIDENCE

```bash
# Model (OLD - trained on corrupted data)
-rw-r--r--  1.0M Nov 20 15:07 models/nba/ddtd/ddtd_model_v3.pkl

# Data (NEW - re-scraped with fix)
-rw-r--r--  9381 Dec  3 09:46 data/nba/boxscores-raw/2025-26/401810147.json
```

**Calibration Analysis Results:**
- TD Model: When predicting 95% → actual is 12.5% (off by 83%!)
- DD Model: When predicting 78% → actual is 26.3% (off by 52%)

**This is because the model learned from corrupted training data.**

---

## ✅ SOLUTION: RETRAIN WITH FIXED DATA

### Step 1: Backup Current Model
```bash
cp models/nba/ddtd/ddtd_model_v3.pkl models/nba/ddtd/ddtd_model_v3_nov20_corrupted.pkl
cp models/nba/ddtd/acceptance_gates_v3.json models/nba/ddtd/acceptance_gates_v3_nov20.json
```

### Step 2: Retrain Model
```bash
python3 ddtd/train_model_v3.py
```

This will:
- Use the fixed data (re-scraped Dec 3)
- Train new DD and TD models
- Save to `models/nba/ddtd/ddtd_model_v3.pkl`
- Update acceptance gates

### Step 3: Test Calibration
```bash
python3 investigate_calibration.py
```

Expected improvement:
- TD high confidence predictions should be much better
- DD high confidence predictions should be much better
- Julius Randle 83% bug should disappear

### Step 4: Validate with Backtest
```bash
python3 ddtd/backtest_v3.py
```

Compare:
- Old model (Nov 20 - corrupted data)
- New model (Dec 4 - fixed data)

### Step 5: Deploy to Production
```bash
# If calibration improves, commit and push
git add models/nba/ddtd/ddtd_model_v3.pkl
git add models/nba/ddtd/acceptance_gates_v3.json
git commit -m "RETRAIN: Model on fixed ESPN data (Dec 4, 2025)"
git push origin main
```

---

## 🎯 ADDITIONAL CALIBRATION (If Still Needed)

**If retraining doesn't fully fix calibration, add post-processing:**

### Option A: Isotonic Regression (Recommended)
```python
from sklearn.isotonic import IsotonicRegression

# Train calibrator on validation set
iso_dd = IsotonicRegression(out_of_bounds='clip')
iso_td = IsotonicRegression(out_of_bounds='clip')

iso_dd.fit(dd_pred_uncalibrated, dd_actual)
iso_td.fit(td_pred_uncalibrated, td_actual)

# Apply during prediction
dd_pred_calibrated = iso_dd.transform(dd_pred_raw)
td_pred_calibrated = iso_td.transform(td_pred_raw)
```

### Option B: Platt Scaling
```python
from sklearn.linear_model import LogisticRegression

# Train calibrator
platt_dd = LogisticRegression()
platt_td = LogisticRegression()

platt_dd.fit(dd_pred_raw.reshape(-1, 1), dd_actual)
platt_td.fit(td_pred_raw.reshape(-1, 1), td_actual)
```

### Option C: Temperature Scaling (Simple)
```python
# Find temperature T that minimizes calibration error
def apply_temperature(pred, temperature):
    return pred ** (1.0 / temperature)

# Tune temperature on validation set
# T > 1 reduces overconfidence
# T < 1 increases confidence
```

---

## 📋 EXPECTED RESULTS AFTER RETRAINING

**Before (Nov 20 model on corrupted data):**
- TD 95% prediction → 12.5% actual ❌
- DD 78% prediction → 26.3% actual ❌
- Julius Randle: 83% TD (absurd) ❌

**After (Dec 4 model on fixed data):**
- TD 95% prediction → 70-85% actual ✅
- DD 78% prediction → 60-75% actual ✅
- Julius Randle: 5-15% TD (realistic) ✅

---

## ⚠️ IMPORTANT NOTES

1. **Don't Skip Retraining**
   - Adding calibration on top of a corrupted model won't fully fix it
   - The model learned wrong patterns from bad data
   - Must retrain from scratch with fixed data

2. **Validate Before Production**
   - Run calibration analysis after retraining
   - Run backtest to ensure performance maintains/improves
   - Check a few manual examples (like Julius Randle)

3. **Consider Ensemble After Retraining**
   - If still overconfident, add isotonic calibration layer
   - This is common best practice for gradient boosting

4. **Update Documentation**
   - Note retraining date in model metadata
   - Track calibration metrics over time
   - Set alert if calibration drifts >10%

---

## 🚀 QUICK START

```bash
# 1. Backup old model
cp models/nba/ddtd/ddtd_model_v3.pkl models/nba/ddtd/ddtd_model_v3_nov20.pkl

# 2. Retrain with fixed data
python3 ddtd/train_model_v3.py

# 3. Check calibration
python3 investigate_calibration.py

# 4. Compare predictions
python3 run_today.py $(netlify env:get ODDS_API_KEY)

# 5. If good, commit
git add models/nba/ddtd/
git commit -m "RETRAIN: Model on fixed ESPN data"
git push origin main
```

---

**Bottom Line:** The model needs retraining, not just calibration. It learned from corrupted data. Once retrained on the fixed data (re-scraped Dec 3), the calibration should improve dramatically.
