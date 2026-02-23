# 🦆 Quacktuaries Guide

## What Is This Game?

Quacktuaries is a game about **statistical inference**. You play the role of an insurance underwriter at a rubber duck factory. The factory produces batches of rubber ducks, and each batch has a hidden true defect rate, *p*, that you don't know. Your job is to **inspect** batches by sampling ducks, **estimate** their defect rates, and then **sell insurance policies** *(confidence intervals)* for profit.


## Getting Started

1. Your instructor will give you a **join code** (e.g., `AB12CD`).
2. Navigate to the game's home page and click **Join**.
3. Enter the join code and your name.
4. Wait in the lobby until your instructor starts the game.

If you get disconnected, just rejoin with the **same name and code** to resume where you left off.


## Gameplay

### Batches 📦

The game presents you with a set of numbered duck batches (by default, 10). Each batch has a hidden defect rate *p* that determines how many ducks in the batch are defective. Your goal is to figure out what *p* is for each batch, or at least narrow it down to a range.

### Turns and Budget

You have a limited number of **turns** (default: **20**) and a limited **inspection budget** (default: **400**).

Every action (inspecting or selling) costs **1 turn**. Inspecting also costs *n* points from your budget, where *n* is the number of ducks you sample. Selling a policy does not cost any budget, but it does cost 1 turn. Plan carefully: once you run out of either, you're done — unless you buy more.

### Time Limit ⏱

Each game session has a **time limit** (default: **15 minutes**). A live countdown timer is displayed on your dashboard — when it reaches zero, the game ends automatically and no more actions can be taken. Keep an eye on it!

### Purchasing Extra Resources 🪙

Your **score** doubles as currency. You can spend points from your score to buy additional turns or inspection budget during the game:

| Purchase             | Cost     |
|----------------------|----------|
| +1 Turn              | 🪙 40    |
| +50 Inspection Budget| 🪙 20    |

Purchase buttons appear directly below the Turns Left and Budget Left displays on your dashboard. This is a strategic trade-off: spending score now reduces your final standing, but extra resources let you inspect more batches or sell more policies. Use wisely — a purchased turn only pays off if you earn back more than you spent.

### Sample Size Limits

When inspecting a batch, you choose a sample size *n* (number of ducks to pull from the batch). It must fall within the allowed range of **5** to **80** (by default). Larger samples give you more data but consume more of your budget.


## Actions

Each turn you choose **one** of two actions:

### 1. Inspect a Batch 🔍

Pick a batch and a sample size *n*. The game pulls *n* ducks from the batch and tells you how many defective ducks *x* you found out of *n*.

You can inspect the same batch multiple times. Your results accumulate so you can get a clearer picture of *p*.

The sample proportion $\hat{p} = x/n$ is your best point estimate of the defect rate. As you inspect more ducks, your cumulative $\hat{p}$ gets closer to the true value.

### 2. Sell a Policy 💰

Once you've inspected a batch and have a feel for its defect rate *p*, you can sell an insurance policy on it. To sell, you provide:

- **Batch #**: Which batch you're underwriting
- **Confidence level**: Choose 90%, 95%, or 99%
- **Lower bound (L)** and **Upper bound (U)**: Your estimated interval for *p*

If the batch's true defect rate *p* falls inside your interval [L, U], the policy is a **HIT** ✅ and you earn a premium. If *p* falls outside, it's a **MISS** ❌ and you pay a penalty. You must inspect a batch at least once before selling a policy on it (by default).


## Scoring

Your score starts at **0** and changes each time you sell a policy. Inspecting does not directly affect your score.

### Premium (What You Earn)

When you sell a policy, you earn a premium based on how **narrow** your interval is and how **confident** you claim to be. A narrower interval is worth *quadratically* more — halving the width roughly quadruples the premium. Higher confidence multiplies the premium further, but carries a steeper miss penalty:

$$\text{Premium} = \left\lfloor \text{premium\_scale} \times (1 - w)^2 \times \text{confidence\_bonus} \right\rfloor$$

where $w = U - L$ is the **width** of your interval.

With the default `premium_scale` of **120**:

| Interval Width (*w*) | Confidence | Bonus | **Premium** |
|----------------------|------------|-------|-------------|
| 0.10                 | 90%        | 1.0×  | **97**      |
| 0.10                 | 95%        | 1.2×  | **116**     |
| 0.10                 | 99%        | 1.5×  | **145**     |
| 0.20                 | 90%        | 1.0×  | **76**      |
| 0.20                 | 95%        | 1.2×  | **92**      |
| 0.20                 | 99%        | 1.5×  | **115**     |
| 0.30                 | 90%        | 1.0×  | **58**      |
| 0.30                 | 95%        | 1.2×  | **70**      |
| 0.30                 | 99%        | 1.5×  | **88**      |
| 0.50                 | 90%        | 1.0×  | **30**      |
| 0.50                 | 95%        | 1.2×  | **36**      |
| 0.50                 | 99%        | 1.5×  | **45**      |
| 0.80                 | 90%        | 1.0×  | **4**       |
| 0.80                 | 95%        | 1.2×  | **5**       |
| 0.80                 | 99%        | 1.5×  | **7**       |

### Penalty (What You Lose on a Miss)

If the true *p* is **not** inside your interval [L, U], you pay a penalty that depends on the confidence level you chose:

| Confidence Level | Bonus | Miss Penalty |
|------------------|-------|--------------|
| 90%              | 1.0×  | 150          |
| 95%              | 1.2×  | 350          |
| 99%              | 1.5×  | 600          |

Higher confidence levels earn bigger premiums but carry steeper penalties if you miss. Think of it like real insurance: a 99% coverage guarantee is worth more to the buyer, but if you can't deliver, the fallout is severe. If you claim 99% confidence and miss, you lose **600 points**.

### Net Score per Policy

$$\text{Net} = \text{Premium} - \text{Penalty}$$

- On a **HIT**: Net = Premium (penalty is 0)
- On a **MISS**: Net = Premium − Penalty (usually very negative)

**Example — HIT:** You sell a policy on Batch 3 with interval [0.30, 0.50] at 95% confidence.
- Width = 0.20, Premium = floor(120 × 0.80² × 1.2) = floor(120 × 0.64 × 1.2) = **92**
- The true defect rate is 0.42 — it's inside your interval. **HIT!** ✅
- Net = 92 − 0 = **+92 points**

**Example — MISS:** Same interval [0.30, 0.50] at 95% confidence.
- Premium = **92** (same as above)
- The true defect rate is 0.55 — outside your interval. **MISS.** ❌
- Net = 92 − 350 = **−258 points**


## Strategy Tips

### Balance Inspecting and Selling

If you spend too many turns inspecting, you won't have turns left to sell policies (where you actually score). If you sell too early without enough data, you'll likely miss and take big penalties. You don't need to inspect every batch, and you can inspect the same batch more than once, so focus on gathering enough data to sell confidently on the batches you do inspect. 

### Match Confidence to Risk

- If you have a lot of data on a batch, you can afford narrow intervals at high confidence, and you'll earn a bigger premium for doing so.
- If you're less sure, use a wider interval or a lower confidence level to reduce penalty risk.
- Higher confidence pays more per hit but punishes misses severely — only claim 99% when your data truly supports it. If it does, the payoff is significantly higher than playing it safe at 90%.
- Width matters even more than confidence — narrowing your interval gives you *quadratically* increasing returns.

### When to Buy Extra Resources

- **Buy turns** when you've run out but still have unsold batches with good data. A turn costs 🪙40 — if your next sell earns 70+ premium, it's worth it.
- **Buy budget** when you need more inspections but are out of sampling capacity. 50 extra budget costs only 🪙20, enough for several small inspections.
- **Don't buy on speculation.** Only purchase resources when you have a clear plan to earn back more than you spend.


## Quick Reference

| Parameter           | Default Value |
|---------------------|---------------|
| Duck Batches        | 10            |
| Turns               | 20            |
| Inspection budget   | 400           |
| Time limit          | 15 minutes    |
| Min sample size     | 5             |
| Max sample size     | 80            |
| Premium scale       | 120           |
| Prior test needed   | Yes           |
| Buy 1 Turn          | 🪙 40         |
| Buy 50 Budget       | 🪙 20         |

| Confidence | Bonus | Miss Penalty |
|------------|-------|--------------|
| 90%        | 1.0×  | 150          |
| 95%        | 1.2×  | 350          |
| 99%        | 1.5×  | 600          |


## FAQ

**Q: Can I sell multiple policies on the same batch?**
A: No. You can only sell one policy per batch. Choose your interval carefully! You can still inspect the same batch multiple times before selling.

**Q: What happens if my interval is [0.00, 1.00]?**
A: It will always hit, but your premium is floor(120 × 0² × bonus) = 0. You'd earn nothing.

**Q: Can I go negative?**
A: Yes. Missed policies result in large deductions. A bad miss can wipe out several good sales.

**Q: When are the true defect rates revealed?**
A: After the instructor ends the game. Until then, you only see your inspection results.

**Q: Does inspecting count toward my score?**
A: No. Inspecting costs turns and budget but does not change your score directly. Only selling policies changes your score.

**Q: Is buying extra turns or budget worth it?**
A: It depends. A turn costs 🪙40, so you need to earn more than 40 points from that extra action to profit. If you've got data on unsold batches and expect a good premium, buying makes sense. If you're guessing, you'll probably lose money.

**Q: What happens when the timer runs out?**
A: The game ends automatically. Any actions you're in the middle of submitting will be rejected. Watch the countdown!
