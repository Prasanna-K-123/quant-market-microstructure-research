# Quant Market Microstructure & Execution Research

[![Validation](https://github.com/Prasanna-K-123/quant-market-microstructure-research/actions/workflows/validation.yml/badge.svg?branch=main)](https://github.com/Prasanna-K-123/quant-market-microstructure-research/actions/workflows/validation.yml)

A reproducible short-horizon quantitative-research project testing whether taker-order-flow imbalance and recent market state contain out-of-sample information about subsequent returns after an explicit execution delay, and whether any measured predictability survives baseline challenge, regime checks and transaction-cost sensitivity.

**Reference V1 conclusion:** small, sample-specific short-horizon associations are detectable, but the multivariate model does not clearly dominate simple calibrated baselines and the measured effects are too small or unstable to support a deployable trading-alpha claim.

## Recruiter snapshot

| Signal | Verified evidence |
|---|---|
| Data integrity | **2,419,200** official Binance 1-second observations across **28** SHA-256-verified daily archives |
| Leakage control | chronological **8 train / 3 validation / 3 untouched final-test days** per symbol; signal at `t`, modeled entry at `t+1` |
| Strongest held-out result | BTCUSDT 5s Ridge Pearson IC **0.02064**, Spearman IC **0.04445**, directional accuracy **52.68%** |
| Baseline challenge | simple last-5s-return OLS Pearson IC **0.02264** beats the multivariate Ridge **0.02064** |
| Economic reality | strongest decile spread is only about **0.137 bps** before friction; ETH 30s turns negative at **1 bp one-way** illustrative cost |

**Direct evidence:** [`accepted V1 manifest`](reference/accepted_v1.json) · [`prediction metrics`](results/prediction_metrics.csv) · [`baseline metrics`](results/baseline_metrics.csv) · [`cost sensitivity`](results/strategy_cost_sensitivity.csv) · [`adversarial results audit`](docs/RESULTS_AUDIT.md)

## Reference research design

- **Source:** official Binance Public Data Spot 1-second klines
- **Assets:** BTCUSDT and ETHUSDT
- **Fixed reference window:** 2025-01-02 through 2025-01-15
- **Integrity:** every daily archive SHA-256 checked against the official companion checksum
- **Raw observations:** 2,419,200 across 28 verified daily archives
- **Research bars:** 5 seconds
- **Features:** taker-flow imbalance, lagged returns, rolling imbalance, realized volatility, quote volume, trade intensity, volume surprise and intrabar range
- **Targets:** 5s / 15s / 30s execution-lagged forward log returns
- **Execution control:** signal at bar `t`; modeled entry at bar `t+1`
- **Split:** 8 training days / 3 validation days / 3 untouched final-test days per symbol
- **Model:** StandardScaler + Ridge; regularization selected only on validation information coefficient
- **Baselines:** one-feature OLS models for order-flow imbalance, latest 5s return and 30s rolling imbalance; fit on train+validation and evaluated on the same untouched final test
- **Robustness:** cross-symbol, horizon, prediction-decile, block-bootstrap and volatility-regime checks
- **Economic diagnostic:** non-overlapping 30s positions with 0/1/2/5/10 bps one-way illustrative cost sensitivity

## Held-out findings

### Strongest statistical association: BTCUSDT, 5 seconds

- Ridge Pearson IC: **0.02064**
- Ridge Spearman IC: **0.04445**
- Directional accuracy: **52.68%**
- Top-minus-bottom prediction-decile mean-return spread: approximately **0.137 bps**
- 1-hour moving-block bootstrap 95% interval: approximately **0.023 to 0.250 bps**

The effect is small. More importantly, the full Ridge model does **not** beat the strongest simple baseline on Pearson IC:

- last-5s-return OLS: **0.02264**
- order-imbalance OLS: **0.02174**
- multivariate Ridge: **0.02064**

That negative model-complexity result is retained rather than hidden.

### Robustness is mixed

Ridge Pearson IC across the remaining final-test combinations:

| Symbol | 15s | 30s |
|---|---:|---:|
| BTCUSDT | 0.00219 | -0.00852 |
| ETHUSDT | 0.00951 | 0.00778 |

ETHUSDT 5s Pearson IC is **0.00441**. Several corresponding validation ICs were negative, so positive final-test values in those cases are treated as unstable sample evidence rather than validated trading candidates.

### Economic significance is weak

For the validation-frozen 30-second diagnostic:

- BTCUSDT gross mean return per active trade is negative.
- ETHUSDT gross mean return per active trade is about **0.696 bps**, but turns negative under a **1 bp one-way / 2 bps round-trip** illustrative cost assumption.
- The positive BTC 5-second decile spread is only about **0.137 bps before any trading frictions**.

The project therefore makes **no profitability, alpha, Sharpe or executable-P&L claim**.

## Why the negative evidence matters

The research was designed so a weak result remains useful evidence of scientific discipline:

- the final-test period was frozen before inspection;
- unfavorable horizons were not dropped;
- negative validation ICs remain visible;
- simple baselines are allowed to beat the full model;
- adverse regime behavior remains visible;
- cost sensitivity is reported even when it destroys gross performance;
- no result is relabeled as “alpha” merely because an association is statistically positive.

The full adversarial interpretation is in [`docs/RESULTS_AUDIT.md`](docs/RESULTS_AUDIT.md).

## Anti-overfitting controls

The feature set, assets, date window, split rule, alpha grid, selection criterion, trading threshold and cost grid were documented before final-test inspection in [`docs/RESEARCH_PROTOCOL.md`](docs/RESEARCH_PROTOCOL.md).

A future V2 must use a separately documented hypothesis and a new untouched evaluation period. V1 will not be retroactively redefined to manufacture a cleaner result.

## Evidence boundary

The Binance archive provides aggregate 1-second kline fields, including total volume, trade count and taker-buy volume. It does **not** provide a full limit-order-book event stream. This project therefore studies short-horizon **trade-flow/price interaction** and does not claim queue-position, spread-reconstruction or full-depth order-book results.

Cost scenarios are illustrative assumptions and are not presented as an executable fee/slippage schedule.

See:

- [`docs/DATA_PROVENANCE.md`](docs/DATA_PROVENANCE.md)
- [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md)
- [`docs/RESEARCH_PROTOCOL.md`](docs/RESEARCH_PROTOCOL.md)
- [`docs/RESULTS_AUDIT.md`](docs/RESULTS_AUDIT.md)

## Repository structure

```text
src/qr_microstructure/
  data.py          official archive download, checksum validation, 5s aggregation
  features.py      backward-looking features + execution-lagged targets
  modeling.py      chronological partitioning + validation-selected Ridge model
  evaluation.py    calibrated baselines, IC, deciles, bootstrap, regime and cost diagnostics
  reporting.py     evidence tables, figures and generated research report

tests/             leakage, split and strategy-accounting tests
docs/              provenance, methodology, frozen protocol and adversarial results audit
run_research.py     end-to-end reference pipeline
```

## Reproduce

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
python -m pytest
python run_research.py
```

The validated CI run downloads and checksum-verifies the fixed public-data window, executes the tests and research pipeline, and generates split metadata, model-selection tables, final-test metrics, baseline comparisons, decile evidence, regime diagnostics, cost sensitivity, figures and a research report.

## Evidence status

**REFERENCE V1 ACCEPTED AS RESEARCH EVIDENCE.**

The accepted result is intentionally narrower than a trading-success story: weak and regime-sensitive predictive structure exists in parts of the sample, but there is insufficient evidence for a durable or economically executable edge.
