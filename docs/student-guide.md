# 🦆 Quacktuaries Guide

## What Is This Game?

Quacktuaries is a game about **statistical inference**. You play the role of an insurance underwriter at a rubber duck factory 🏭. The factory produces batches of rubber ducks, and each batch has a hidden true defect rate, *p*, that you don't know. Your job is to **inspect** batches by sampling ducks, **estimate** their defect rates, and then **sell insurance policies** (confidence intervals) for profit.

---

## Getting Started

1. Your instructor will give you a **join code** (e.g., `AB12CD`).
2. Navigate to the game's home page and click **Join**.
3. Enter the join code and your name.
4. Wait in the lobby until your instructor starts the game.

If you get disconnected, just rejoin with the **same name and code** to resume where you left off.

---

## Gameplay

### 📦 Batches

The game presents you with a set of numbered duck batches (by default, 10). Each batch has a hidden defect rate *p* that determines how many ducks in the batch are defective. Your goal is to figure out what *p* is for each batch, or at least narrow it down to a range.

### Turns and Budget

You have a limited number of **turns** and a limited **inspection budget**:

| Resource          | Default |
|-------------------|--------:|
| Turns             | 20      |
| Inspection budget | 400     |

Every action (inspecting or selling) costs **1 turn**. Inspecting also costs *n* points from your budget, where *n* is the number of ducks you sample. Selling a policy does not cost any budget, but it does cost 1 turn. Plan carefully: once you run out of either, you're done.

### Sample Size Limits

When inspecting a batch, you choose a sample size *n* (number of ducks to pull from the batch). It must fall within the allowed range:

| Limit   | Default |
|---------|--------:|
| Minimum | 5       |
| Maximum | 80      |

Larger samples give you more data but consume more of your budget.

---

## Actions

Each turn you choose **one** of two actions:

### 1. 🔍 Inspect a Batch

Pick a batch and a sample size *n*. The game pulls *n* ducks from the batch and tells you how many defective ducks *x* you found out of *n*.

You can inspect the same batch multiple times. Your results accumulate so you can get a clearer picture of *p*.

The sample proportion $\hat{p} = x/n$ is your best point estimate of the defect rate. As you inspect more ducks, your cumulative $\hat{p}$ gets closer to the true value.

### 2. 💰 Sell a Policy

Once you've inspected a batch and have a feel for its defect rate *p*, you can sell an insurance policy on it. To sell, you provide:

- **Batch #**: Which batch you're underwriting
- **Confidence level**: Choose 90%, 95%, or 99%
- **Lower bound (L)** and **Upper bound (U)**: Your estimated interval for *p*

If the batch's true defect rate *p* falls inside your interval [L, U], the policy is a **HIT** ✅ and you earn a premium. If *p* falls outside, it's a **MISS** ❌ and you pay a penalty. You must inspect a batch at least once before selling a policy on it (by default).

---

## Scoring

Your score starts at **0** and changes each time you sell a policy. Inspecting does not directly affect your score.

### Premium (What You Earn)

When you sell a policy, you earn a premium based on how **narrow** your interval is. A narrower interval means you're making a bolder claim, so you earn more:

$$\text{Premium} = \left\lfloor \text{premium\_scale} \times (1 - w) \right\rfloor - \text{confidence\_fee}$$

where $w = U - L$ is the **width** of your interval.

With the default `premium_scale` of **120**:

| Interval Width (*w*) | Confidence | Fee | Raw Premium | **Net Premium** |
|----------------------|------------|-----|-------------|-----------------|
| 0.10                 | 90%        | 0   | 108         | **108**         |
| 0.10                 | 95%        | 10  | 108         | **98**          |
| 0.10                 | 99%        | 25  | 108         | **83**          |
| 0.20                 | 90%        | 0   | 96          | **96**          |
| 0.20                 | 95%        | 10  | 96          | **86**          |
| 0.20                 | 99%        | 25  | 96          | **71**          |
| 0.30                 | 90%        | 0   | 84          | **84**          |
| 0.30                 | 95%        | 10  | 84          | **74**          |
| 0.30                 | 99%        | 25  | 84          | **59**          |
| 0.50                 | 90%        | 0   | 60          | **60**          |
| 0.50                 | 95%        | 10  | 60          | **50**          |
| 0.50                 | 99%        | 25  | 60          | **35**          |
| 0.80                 | 90%        | 0   | 24          | **24**          |
| 0.80                 | 95%        | 10  | 24          | **14**          |
| 0.80                 | 99%        | 25  | 24          | **0**           |

### Penalty (What You Lose on a Miss)

If the true *p* is **not** inside your interval [L, U], you pay a penalty that depends on the confidence level you chose:

| Confidence Level | Confidence Fee | Miss Penalty |
|------------------|----------------|--------------|
| 90%              | 0              | 200          |
| 95%              | 10             | 350          |
| 99%              | 25             | 600          |

Higher confidence levels have steeper penalties (and a small fee that reduces your premium) but they signal that you're very sure about your interval. If you claim 99% confidence and miss, you lose **600 points**.

### Net Score per Policy

$$\text{Net} = \text{Premium} - \text{Penalty}$$

- On a **HIT**: Net = Premium (penalty is 0)
- On a **MISS**: Net = Premium − Penalty (usually very negative)

**Example — HIT:** You sell a policy on Batch 3 with interval [0.30, 0.50] at 95% confidence.
- Width = 0.20, Premium = floor(120 × 0.80) − 10 = 96 − 10 = **86**
- The true defect rate is 0.42 — it's inside your interval. **HIT!** ✅
- Net = 86 − 0 = **+86 points**

**Example — MISS:** Same interval [0.30, 0.50] at 95% confidence.
- Premium = **86** (same as above)
- The true defect rate is 0.55 — outside your interval. **MISS.** ❌
- Net = 86 − 350 = **−264 points**

---

## Strategy Tips

### Balance Inspecting and Selling

If you spend too many turns inspecting, you won't have turns left to sell policies (where you actually score). If you sell too early without enough data, you'll likely miss and take big penalties.

### Match Confidence to Data Quality

- If you have a lot of data on a batch, you can afford narrow intervals at high confidence.
- If you're less sure, use a wider interval or a lower confidence level to reduce penalty risk.
- The 90% confidence level has **no fee** and the lowest penalty (200), making it the safest option for uncertain estimates.

### Watch Your Budget

Each inspection costs *n* from your budget of 400. Example allocation:

| Strategy                       | Inspections | Budget Used | Turns for Selling |
|--------------------------------|-------------|-------------|-------------------|
| Inspect 8 batches × n=50      | 8           | 400         | 12 turns          |
| Inspect 10 batches × n=35     | 10          | 350         | 10 turns          |
| Inspect 6 batches × n=50      | 6           | 300         | 14 turns          |

You don't need to inspect every batch. Focus on gathering enough data to sell confidently on the batches you do inspect.

### Think About Risk vs. Reward

Narrow intervals pay more but fail more easily. Consider this comparison at 95% confidence:

| Width | Premium | Penalty on Miss | Break-Even Accuracy |
|-------|---------|-----------------|---------------------|
| 0.10  | 98      | 350             | 78%                 |
| 0.20  | 86      | 350             | 80%                 |
| 0.30  | 74      | 350             | 83%                 |
| 0.50  | 50      | 350             | 88%                 |

*Break-even accuracy = the hit rate you need for the strategy to have non-negative expected value.*

The narrower the interval, the lower the hit rate you need to break even, but the harder it is to actually hit consistently. Find the sweet spot where your data supports the width you choose.

---

## Quick Reference

| Parameter           | Default Value |
|---------------------|---------------|
| Duck Batches        | 10            |
| Turns               | 20            |
| Inspection budget   | 400           |
| Min sample size     | 5             |
| Max sample size     | 80            |
| Premium scale     | 120           |
| Prior test needed | Yes           |

| Confidence | Fee | Miss Penalty |
|------------|-----|--------------|
| 90%        | 0   | 200          |
| 95%        | 10  | 350          |
| 99%        | 25  | 600          |

---

## FAQ

**Q: Can I sell multiple policies on the same batch?**
A: No. You can only sell one policy per batch. Choose your interval carefully! You can still inspect the same batch multiple times before selling.

**Q: What happens if my interval is [0.00, 1.00]?**
A: It will always hit, but your premium is floor(120 × 0) − fee = 0 (or negative). You'd earn nothing or lose points.

**Q: Can I go negative?**
A: Yes. Missed policies result in large deductions. A bad miss can wipe out several good sells.

**Q: When are the true defect rates revealed?**
A: After the instructor ends the game. Until then, you only see your inspection results.

**Q: Does inspecting count toward my score?**
A: No. Inspecting costs turns and budget but does not change your score directly. Only selling policies changes your score.
