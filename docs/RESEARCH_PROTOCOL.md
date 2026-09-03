# Pre-results research protocol

This file records the reference-run hypotheses and success/failure interpretation **before** the untouched final-test results are inspected.

## H1 — short-horizon information

Recent taker-flow imbalance and market-state features may contain positive information about execution-lagged forward returns.

Evidence in favor requires positive final-test Pearson/Spearman information coefficient that is not confined to only one isolated horizon with contradictory neighboring horizons.

A small positive IC is not automatically economically meaningful.

## H2 — ordered response

If model predictions contain useful information, mean forward returns should generally increase across prediction deciles. The top-minus-bottom spread should be positive, and its moving-block bootstrap interval should be reported rather than suppressing uncertainty.

Failure of monotonicity or an interval spanning zero is retained as a negative/ambiguous finding.

## H3 — cross-asset robustness

The primary feature architecture is applied unchanged to BTCUSDT and ETHUSDT. A finding that appears only in one symbol is treated as venue/asset-specific evidence, not a universal microstructure result.

## H4 — regime robustness

The final test is split at the median trailing-realized-volatility level. A signal that reverses sign between high- and low-volatility regimes is treated as unstable unless there is a defensible mechanism and sufficient evidence.

## H5 — economic attenuation under costs

Any gross 30-second trading diagnostic is expected to weaken as explicit transaction costs increase. Net results are shown at 0/1/2/5/10 bps one-way cost assumptions.

The project will not describe a statistical signal as an executable strategy if modest costs eliminate its mean return.

## What will not be done after observing final test

The reference run will not:

- change symbols or dates to obtain a nicer result;
- drop an unfavorable horizon;
- change feature definitions to fit test outcomes;
- alter Ridge alpha based on test results;
- alter the 90th-percentile validation signal threshold based on test P&L;
- alter the cost grid to hide breakeven;
- relabel gross returns as net returns;
- claim Sharpe, alpha or profitability without the required economic controls.

A subsequent research iteration may test a new hypothesis, but it must be versioned separately and must not retroactively redefine the reference final test.
