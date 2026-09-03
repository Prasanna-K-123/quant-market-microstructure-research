# Methodology

## Research question

Does recent taker-order-flow imbalance and short-horizon market state contain reproducible information about subsequent returns after a conservative execution delay, and does any measured predictability survive explicit cost sensitivity?

The project is designed to make a weak/negative result acceptable. It is not tuned to manufacture a profitable backtest.

## Unit of analysis

Official 1-second Spot klines are aggregated to 5-second bars. Each signal is formed at the **close of bar t**.

### Execution-lagged targets

For horizon `h`, the target is:

`log(close[t + h + 1] / close[t + 1])`

Thus entry is modeled one full 5-second bar after the signal timestamp. This deliberately prevents same-close execution assumptions.

Horizons:

- 5s = 1 holding bar after delayed entry
- 15s = 3 holding bars
- 30s = 6 holding bars

## Features

All features are current or backward-looking at signal time:

- current taker order-flow imbalance: `(2 * taker_buy_base - volume) / volume`
- 15s and 30s rolling mean imbalance
- trailing 5s, 15s and 30s log returns
- trailing 30s realized volatility
- log quote volume
- log trade count / trade intensity
- 5-minute rolling quote-volume z-score
- within-bar high-low range in basis points

No future-derived feature is permitted.

## Split protocol

For the fixed 14-day window used by the reference run, each symbol is split chronologically:

- first 8 days: training
- next 3 days: validation
- remaining 3 days: untouched final test

Targets whose exit timestamp crosses the end of a partition are removed. Historical data prior to a validation/test signal may contribute backward-looking rolling features, which is operationally available information and not target leakage.

## Model and selection

Primary model: standardized Ridge regression.

Ridge alpha is selected **only** on validation-set Pearson information coefficient over a fixed alpha grid. The selected specification is then refit on train + validation and evaluated once on final test.

The absolute prediction threshold used by the trading diagnostic is the 90th percentile of absolute **validation** predictions. It is frozen before final-test strategy evaluation.

## Baselines

The full model must be compared with transparent untuned baselines:

1. contemporaneous order-flow imbalance
2. most recent 5-second return
3. rolling 30-second mean imbalance

The project is not considered informative merely because a flexible model beats zero.

## Final-test diagnostics

For each symbol and horizon:

- Pearson information coefficient
- Spearman information coefficient
- directional accuracy
- RMSE / MAE
- prediction-decile average returns
- top-minus-bottom prediction-decile spread
- moving-block bootstrap 95% interval for the spread
- high- vs low-volatility regime metrics

## Trading diagnostic

Only the 30-second horizon receives a trading-cost diagnostic.

- signals are sampled every six 5-second bars so modeled holding periods do not overlap;
- position is `sign(prediction)` only when absolute prediction exceeds the validation-frozen 90th-percentile threshold;
- gross return uses the same one-bar-delayed 30-second target;
- one-way costs of 0, 1, 2, 5 and 10 bps are tested, producing 0, 2, 4, 10 and 20 bps round-trip assumptions;
- outputs include trade count, participation, gross/net mean return, median net return, hit rate and cumulative net log return.

These are research diagnostics. They omit order-book spread dynamics, market impact, queueing, capacity, latency dispersion, funding and operational constraints.

## Anti-overfitting rules

- Fixed assets/date range in the reference run.
- Fixed feature set before final-test inspection.
- Fixed alpha grid.
- Fixed validation criterion.
- Fixed trading threshold quantile.
- Fixed cost grid.
- Final test is not used to redesign the signal during the reference run.
- Cross-symbol disagreement and negative results are retained.

## Research limitations

The dataset is one cryptocurrency spot venue and uses aggregate 1-second kline fields, not full depth-of-book state. A short sample can capture regime-specific behavior. Even statistically significant predictability may be too small to survive costs. The results must therefore be described as sample-specific evidence rather than durable alpha.
