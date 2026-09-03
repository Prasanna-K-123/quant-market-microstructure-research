# Reference-results audit

Status: **reference run accepted as research evidence; no trading-alpha or deployability claim.**

This note records the post-run QA interpretation of the frozen 2025-01-02 through 2025-01-15 reference study. It distinguishes what the held-out data support from what they do not support.

## Evidence base

- 2,419,200 official Binance Spot 1-second observations across BTCUSDT and ETHUSDT.
- 28 daily archives, each verified against Binance's companion SHA-256 checksum.
- Signals formed on 5-second research bars.
- One-bar execution delay between signal formation and modeled entry.
- Per symbol: 8 training days, 3 validation days and 3 untouched final-test days.
- Six symbol/horizon final-test combinations: BTCUSDT and ETHUSDT at 5s, 15s and 30s.

## Main statistical finding

The strongest held-out association appears in **BTCUSDT at 5 seconds**:

- Ridge Pearson IC: **0.02064**
- Ridge Spearman IC: **0.04445**
- directional accuracy: **52.68%**
- top-minus-bottom prediction-decile mean-return spread: **1.366e-5 log-return units**, approximately **0.137 bps**
- 1-hour moving-block bootstrap 95% interval for the decile spread: approximately **0.023 to 0.250 bps**

This is evidence of a small short-horizon association in the held-out BTC sample. It is **not evidence of durable or economically executable alpha**.

## Baseline challenge

A recruiter-facing research project should not win by comparing a model against zero or against a metric on the wrong scale. The final audit therefore reports calibrated one-feature OLS baselines fitted only on train+validation and evaluated once on the untouched final test.

For BTCUSDT at 5 seconds:

- full Ridge Pearson IC: **0.02064**
- last-5s-return OLS Pearson IC: **0.02264**
- order-imbalance OLS Pearson IC: **0.02174**

The multivariate Ridge model therefore **does not outperform the strongest simple baseline on Pearson IC**. This is a substantive negative result and is retained explicitly. The project demonstrates research discipline, not model-complexity theater.

## Cross-horizon and cross-asset robustness

The evidence is not uniform:

- BTCUSDT 15s Ridge Pearson IC: **0.00219**
- BTCUSDT 30s Ridge Pearson IC: **-0.00852**
- ETHUSDT 5s Ridge Pearson IC: **0.00441**
- ETHUSDT 15s Ridge Pearson IC: **0.00951**
- ETHUSDT 30s Ridge Pearson IC: **0.00778**

Several validation ICs were negative, including both 30-second specifications. Positive final-test values in those cases are therefore treated as unstable sample evidence, not as validated trading candidates.

The BTC 5-second relationship is also stronger in the low-volatility half of the final test than the high-volatility half, reinforcing that the effect is regime-sensitive rather than universal.

## Economic-significance audit

The 30-second diagnostic uses a validation-frozen absolute-prediction threshold and non-overlapping modeled holding periods.

- BTCUSDT gross mean return per active trade is already negative.
- ETHUSDT gross mean return per active trade is about **0.696 bps**, but becomes negative under a **1 bp one-way / 2 bps round-trip** illustrative cost assumption.
- At 2 bps one-way, both symbols are materially negative.

The statistically positive BTC 5-second decile spread is only about **0.137 bps** before spread, fees, slippage, latency dispersion, market impact, queueing and capacity. It therefore cannot support an executable-strategy claim.

## What the reference run supports

It supports the following claims:

1. A leakage-controlled, checksum-verified high-frequency research pipeline was built and reproduced in CI.
2. Weak short-horizon statistical structure is measurable in parts of the held-out sample.
3. The strongest multivariate result does not clearly beat simple calibrated baselines.
4. Cross-horizon, cross-asset and volatility-regime evidence is mixed.
5. Apparent gross predictability is too small or unstable to justify an executable alpha claim under modest cost assumptions.
6. Negative findings were preserved instead of being tuned away.

## What it does not support

Do **not** claim:

- profitable strategy;
- alpha generation;
- production trading system;
- Sharpe ratio;
- realistic institutional P&L;
- full limit-order-book research;
- queue-position or fill modeling;
- durable market anomaly;
- generalization beyond the studied venue, assets and sample.

## QA corrections after the first reference execution

The first successful end-to-end execution exposed two presentation/inference issues during independent QA. They were corrected without changing the frozen feature set, symbols, dates, targets, Ridge alpha grid, validation-selection rule, model predictions or final-test observations.

1. **Baseline-scale correction.** Raw dimensionless features had initially been passed directly to prediction-error metrics. That made RMSE/MAE units incomparable with return forecasts. The corrected implementation fits transparent one-feature OLS mappings on train+validation and evaluates them on the same untouched test rows.
2. **Dependence robustness.** The decile-spread interval now uses 1-hour moving blocks and 1,000 resamples, a more conservative treatment of high-frequency serial dependence than the initial short-block implementation.

These are QA refinements, not performance-seeking changes. The Git history preserves the sequence.

## Research disposition

**ACCEPTED AS A RESEARCH FLAGSHIP V1.**

The scientifically defensible conclusion is more valuable than a fabricated success story: the frozen specification finds small and regime-sensitive predictive associations, but the evidence is not robust enough or economically large enough to call a deployable trading edge. A future V2 must use a separately preregistered hypothesis and a new untouched evaluation period rather than retroactively redefining this final test.
