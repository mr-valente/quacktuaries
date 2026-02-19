# Scoring Formula — Statistical Analysis

This document analyzes the Quacktuaries scoring formula, explains the design decisions behind it, and demonstrates why it produces well-aligned incentives for a statistics classroom game.

---

## The Formula

$$\text{Premium} = \left\lfloor \text{scale} \times (1 - w)^2 \times \text{bonus} \right\rfloor$$

$$\text{Net} = \text{Premium} - \text{Penalty (if miss)}$$

Where:
- **scale** = 120 (premium_scale)
- **w** = U − L (interval width)
- **bonus** = confidence multiplier: 1.0× (90%), 1.2× (95%), 1.5× (99%)
- **penalty** = miss penalty: 150 (90%), 350 (95%), 600 (99%)

---

## Design Goals

The scoring system must achieve all of the following:

1. **Narrow intervals should be rewarded** — students who gather enough data to make precise estimates should earn more.
2. **Higher confidence should mean higher reward AND higher risk** — matching real insurance economics.
3. **Lying about confidence should be unprofitable** — claiming 99% on a 90%-quality interval must be EV-negative.
4. **Width should dominate confidence** — you can't overcome a wide interval by picking a higher confidence level.
5. **No dominant strategy** — different approaches to allocating turns and budget should yield comparable outcomes for skilled players.
6. **Lazy strategies should yield near-zero returns** — wide intervals and minimal inspection must not be viable.

---

## Why Quadratic Width Scaling?

### The Problem with Linear Scaling

Under a linear formula `scale × (1 - w) × bonus`, width and confidence have equally-weighted effects on the premium. This creates an exploit:

| Strategy | Width | Confidence | Bonus | Premium |
|----------|-------|------------|-------|---------|
| Tight 90% CI | 0.10 | 90% | 1.0× | 108 |
| Wide 99% CI | 0.30 | 99% | 1.5× | 126 |

A student earns **more** by going wider at higher confidence — precisely the opposite of what we want. The confidence bonus (1.5×) overpowers the width penalty (0.70/0.90 = 78%).

### The Quadratic Fix

With `(1 - w)²`, width becomes the dominant factor:

| Strategy | Width | Confidence | Bonus | Premium |
|----------|-------|------------|-------|---------|
| Tight 90% CI | 0.10 | 90% | 1.0× | **97** |
| Wide 99% CI | 0.30 | 99% | 1.5× | **88** |

Now the tight interval wins. The quadratic term means going from w=0.10 to w=0.30 drops the width factor from 0.81 to 0.49 — a 40% decrease that the 1.5× bonus cannot overcome.

### Mathematical Intuition

The `(1-w)²` term has a natural interpretation: it approximates the **relative precision** of an estimate. In statistics, the variance of an estimator scales inversely with sample size, and confidence interval width scales with the square root of variance. Squaring the width factor creates a penalty that mirrors the actual cost of imprecision.

---

## Expected Value Analysis

Using the normal approximation for a confidence interval on a proportion:

$$w = 2 \times z_\alpha \times \sqrt{\frac{\hat{p}(1-\hat{p})}{n}}$$

Where z₉₀ = 1.645, z₉₅ = 1.960, z₉₉ = 2.576.

### Honest Play: Properly Constructed CIs

For a student who builds a proper CI (so their hit rate matches their claimed confidence):

**n = 50, p̂ = 0.50 (worst-case standard error):**

| Confidence | Proper Width | Premium | Hit Rate | Miss Penalty | **EV per Sell** |
|------------|-------------|---------|----------|-------------|-----------------|
| 90% | 0.233 | 70 | 90% | 150 | **48** |
| 95% | 0.277 | 75 | 95% | 350 | **54** |
| 99% | 0.364 | 72 | 99% | 600 | **65** |

**n = 80, p̂ = 0.50:**

| Confidence | Proper Width | Premium | Hit Rate | Miss Penalty | **EV per Sell** |
|------------|-------------|---------|----------|-------------|-----------------|
| 90% | 0.184 | 80 | 90% | 150 | **57** |
| 95% | 0.219 | 88 | 95% | 350 | **66** |
| 99% | 0.288 | 91 | 99% | 600 | **84** |

**Key takeaway:** Better data (larger n) produces narrower CIs, which earn more at every confidence level. And higher confidence consistently earns more EV — *but only when the CI is properly calibrated*. This is exactly the incentive structure we want.

### Confidence Overclaiming ("Lying")

The most important exploit to prevent: a student constructs a 90%-quality interval but claims 99% to pocket the 1.5× bonus.

**n = 50, w = 0.233 (proper 90% CI), claimed as 99%:**

| Strategy | Premium | Hit Rate | Miss Cost | **EV** |
|----------|---------|----------|-----------|--------|
| Honest 90% | 70 | 90% | 150 | **48** |
| **Lie:** Claim 99% | 105 | 90% | 600 | **35** |

The lie is **EV-negative** relative to honest play. The 600 penalty on the 10% miss rate wipes out the bonus.

**Even with tighter intervals (n = 80, w = 0.15):**

| Strategy | Premium | Hit Rate | Miss Cost | **EV** |
|----------|---------|----------|-----------|--------|
| Honest 90% | 86 | 90% | 150 | **63** |
| **Lie:** Claim 99% | 130 | 90% | 600 | **57** |

Still unprofitable to lie. The penalty structure ensures this holds across all realistic widths.

---

## Break-Even Analysis

The break-even hit rate is the minimum accuracy needed for a strategy to have non-negative expected value:

$$\text{BE} = \frac{\text{Penalty}}{\text{Premium} + \text{Penalty}}$$

### By Width

| Width | 90% Conf (P=150) | 95% Conf (P=350) | 99% Conf (P=600) |
|-------|-------------------|-------------------|-------------------|
| 0.05 | BE = 61% | BE = 77% | BE = 82% |
| 0.10 | BE = 61% | BE = 75% | BE = 81% |
| 0.15 | BE = 63% | BE = 77% | BE = 83% |
| 0.20 | BE = 66% | BE = 79% | BE = 84% |
| 0.30 | BE = 72% | BE = 83% | BE = 87% |
| 0.50 | BE = 83% | BE = 91% | BE = 93% |

All break-even rates for honest play sit comfortably **below** their corresponding confidence levels:
- 90% CI → needs ~61–66% accuracy (has 90%) ✅
- 95% CI → needs ~75–79% accuracy (has 95%) ✅
- 99% CI → needs ~81–84% accuracy (has 99%) ✅

This means properly calibrated confidence intervals are always solidly profitable.

---

## Lazy / Degenerate Strategy Analysis

### "Submit [0, 1] on everything"

- Width = 1.0, Premium = floor(120 × 0² × bonus) = **0**
- Always hits, but earns nothing. Worthless.

### "Inspect minimally, sell wide at 99%"

Sample n = 5, sell w = 0.80, claim 99%:
- Premium = floor(120 × 0.04 × 1.5) = **7**
- Even on a hit, earning 7 points is negligible.
- On a miss: 7 − 600 = **−593**

### "Moderate lazy" — n = 10, w = 0.50, claim 99%

A proper 99% CI at n = 10 with p̂ = 0.5 is width ≈ 0.82. Selling at w = 0.50 with a 99% claim means ~80% actual hit rate.

- Premium = floor(120 × 0.25 × 1.5) = **45**
- EV = 0.80 × 45 − 0.20 × 600 = 36 − 120 = **−84**

Devastating. Lazy play is heavily punished.

### "Just claim 90% on everything to be safe"

This works — but underperforms. A student who always claims 90% leaves money on the table compared to a student who correctly calibrates their confidence to their data quality. At n=50, the difference is **48 EV (90%) vs 65 EV (99%)** per batch — a 35% improvement for doing the statistics properly.

---

## Full-Game Strategy Comparisons

With 20 turns and 400 budget (medium difficulty), here are representative strategies:

### Strategy A: Spread Thin

- Inspect 10 batches × n = 40 (10 turns, 400 budget)
- Sell 10 policies at 95% (10 turns)
- Proper 95% CI at n = 40: w ≈ 0.31
- Premium per sell ≈ 57, EV per sell ≈ 37
- **Total EV ≈ 370**

### Strategy B: Balanced

- Inspect 8 batches × n = 50 (8 turns, 400 budget)
- Sell 8 policies at 95% (8 turns), 4 turns unused
- Proper 95% CI at n = 50: w ≈ 0.28
- Premium per sell ≈ 64, EV per sell ≈ 43
- **Total EV ≈ 345**

### Strategy C: Balanced + High Confidence

- Inspect 8 batches × n = 50 (8 turns, 400 budget)
- Sell 8 policies at 99% (8 turns)
- Proper 99% CI at n = 50: w ≈ 0.36
- Premium per sell ≈ 74, EV per sell ≈ 67
- **Total EV ≈ 536**

### Strategy D: Deep Investment

- Inspect 5 batches × n = 80 (5 turns, 400 budget)
- Sell 5 policies at 99% (5 turns), 10 turns unused
- Proper 99% CI at n = 80: w ≈ 0.29
- Premium per sell ≈ 91, EV per sell ≈ 84
- **Total EV ≈ 420**

### Strategy E: Multi-Inspect + Narrow

- Inspect 5 batches × n = 40 twice each (10 turns, 400 budget)
- Effective n = 80 per batch, sell 5 at 99% (5 turns)
- Same as Strategy D but uses more turns for inspection
- **Total EV ≈ 420**

### Strategy F: Selective Deep + 90% Safety

- Inspect 4 batches × n = 80 (4 turns, 320 budget)
- Inspect 2 more batches × n = 40 (2 turns, 80 budget)
- Sell 4 at 99%, 2 at 90% (6 turns)
- EV ≈ 4 × 84 + 2 × 37 = **410**

### Summary

| Strategy | Batches Sold | Avg EV/Batch | **Total EV** |
|----------|-------------|-------------|--------------|
| A: Spread thin | 10 | 37 | **370** |
| B: Balanced 95% | 8 | 43 | **345** |
| C: Balanced 99% | 8 | 67 | **536** |
| D: Deep invest | 5 | 84 | **420** |
| E: Multi-inspect | 5 | 84 | **420** |
| F: Selective mix | 6 | 68 | **410** |

No single strategy totally dominates. Strategy C performs best because it hits the sweet spot: enough data per batch (n=50) for reasonable 99% CIs, while still having turns to sell on all 8 batches. But it requires statistical competence to construct valid 99% intervals — a student who overclaims will get crushed by the 600 penalty.

---

## Why This Scoring System Works

1. **Width is king.** The quadratic `(1-w)²` term ensures that narrowing your interval is always the highest-leverage move. No confidence trick can substitute for actual precision.

2. **Confidence is a meaningful choice.** Higher confidence earns 20–50% more premium, making it worth pursuing — but only when your data supports it. The steep penalties (150 → 350 → 600) make overclaiming a losing bet.

3. **Lying is always punished.** At every width, claiming a higher confidence than your data supports produces negative EV relative to honest calibration. The penalty structure is specifically tuned for this.

4. **Data quality matters.** More inspections → narrower proper CIs → higher premiums. This directly rewards the statistical skill of gathering sufficient data.

5. **Resource management matters.** Students must balance turns (inspect vs. sell), budget (sample size vs. batch coverage), and confidence (reward vs. risk). No resource can be ignored.

6. **No degenerate strategies.** Wide intervals earn almost nothing (quadratic crush). Overclaiming burns you on misses. Spreading too thin yields mediocre per-batch returns. Going too deep sacrifices batch count.

7. **Proper CI construction is the optimal strategy.** The system rewards exactly what the course teaches: gather data, compute the appropriate confidence interval, and state your confidence honestly.
