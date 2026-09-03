from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from qr_microstructure.data import aggregate_to_5s, load_symbol_days
from qr_microstructure.evaluation import (
    baseline_metrics,
    block_bootstrap_decile_spread,
    decile_returns,
    prediction_metrics,
    strategy_cost_sensitivity,
    volatility_regime_metrics,
)
from qr_microstructure.features import HORIZON_BARS, build_features, usable_rows
from qr_microstructure.modeling import chronological_day_split, partition_by_days, predict, select_and_fit_ridge
from qr_microstructure.reporting import build_research_report, plot_cost_sensitivity, plot_deciles, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run leakage-controlled market microstructure research")
    parser.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT"])
    parser.add_argument("--start", default="2025-01-02")
    parser.add_argument("--end", default="2025-01-15")
    parser.add_argument("--cache-dir", default="data/raw")
    parser.add_argument("--output-dir", default="results")
    parser.add_argument("--report-dir", default="reports/generated")
    return parser.parse_args()


def as_date(value: str) -> date:
    return date.fromisoformat(value)


def main() -> None:
    args = parse_args()
    start = as_date(args.start)
    end = as_date(args.end)
    cache_dir = Path(args.cache_dir)
    output_dir = Path(args.output_dir)
    report_dir = Path(args.report_dir)
    figures_dir = report_dir / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    all_prediction_rows: list[dict] = []
    all_baseline_rows: list[pd.DataFrame] = []
    all_selection_rows: list[pd.DataFrame] = []
    all_deciles: list[pd.DataFrame] = []
    all_costs: list[pd.DataFrame] = []
    all_regimes: list[pd.DataFrame] = []
    all_downloads: list[dict] = []
    split_records: list[dict] = []

    for symbol in args.symbols:
        raw, download_records = load_symbol_days(symbol, start, end, cache_dir / symbol)
        all_downloads.extend([record.__dict__ for record in download_records])
        bars = aggregate_to_5s(raw)
        feature_frame = build_features(bars)

        for horizon, h_bars in HORIZON_BARS.items():
            usable = usable_rows(feature_frame, horizon)
            split = chronological_day_split(usable, train_days=8, validation_days=3)
            train, validation, test = partition_by_days(usable, horizon, split)
            target_col = f"target_{horizon}"

            if min(len(train), len(validation), len(test)) < 100:
                raise RuntimeError(
                    f"Insufficient split rows for {symbol} {horizon}: "
                    f"train={len(train)}, val={len(validation)}, test={len(test)}"
                )

            fitted, selection = select_and_fit_ridge(train, validation, target_col, split)
            test_prediction = predict(fitted, test)
            metrics = prediction_metrics(test[target_col].to_numpy(), test_prediction)

            all_prediction_rows.append(
                {
                    "symbol": symbol,
                    "horizon": horizon,
                    "model": "ridge_full",
                    "n": metrics.n,
                    "pearson_ic": metrics.pearson_ic,
                    "spearman_ic": metrics.spearman_ic,
                    "directional_accuracy": metrics.directional_accuracy,
                    "rmse": metrics.rmse,
                    "mae": metrics.mae,
                    "selected_alpha": fitted.alpha,
                    "validation_ic": fitted.validation_ic,
                    "validation_abs_prediction_q90": fitted.threshold_abs_prediction,
                }
            )

            baselines = baseline_metrics(train, validation, test, target_col)
            baselines.insert(0, "horizon", horizon)
            baselines.insert(0, "symbol", symbol)
            all_baseline_rows.append(baselines)

            selection.insert(0, "horizon", horizon)
            selection.insert(0, "symbol", symbol)
            all_selection_rows.append(selection)

            deciles = decile_returns(test[target_col].to_numpy(), test_prediction)
            point, ci_low, ci_high = block_bootstrap_decile_spread(
                test[target_col].to_numpy(),
                test_prediction,
                block_size=720,
                resamples=1000,
            )
            deciles.insert(0, "horizon", horizon)
            deciles.insert(0, "symbol", symbol)
            deciles["top_minus_bottom_mean_return"] = point
            deciles["spread_bootstrap_ci_low"] = ci_low
            deciles["spread_bootstrap_ci_high"] = ci_high
            all_deciles.append(deciles)
            plot_deciles(
                deciles,
                figures_dir / f"{symbol}_{horizon}_prediction_deciles.png",
                f"{symbol} {horizon}: final-test prediction deciles",
            )

            regimes = volatility_regime_metrics(test, target_col, test_prediction)
            regimes.insert(0, "horizon", horizon)
            regimes.insert(0, "symbol", symbol)
            all_regimes.append(regimes)

            if horizon == "30s":
                costs = strategy_cost_sensitivity(
                    test,
                    target_col,
                    test_prediction,
                    fitted.threshold_abs_prediction,
                    horizon_bars=h_bars,
                )
                costs.insert(0, "horizon", horizon)
                costs.insert(0, "symbol", symbol)
                all_costs.append(costs)
                plot_cost_sensitivity(
                    costs,
                    figures_dir / f"{symbol}_{horizon}_cost_sensitivity.png",
                    f"{symbol} {horizon}: validation-frozen signal cost sensitivity",
                )

            split_records.append(
                {
                    "symbol": symbol,
                    "horizon": horizon,
                    "train_days": list(split.train_days),
                    "validation_days": list(split.validation_days),
                    "test_days": list(split.test_days),
                    "train_rows": len(train),
                    "validation_rows": len(validation),
                    "test_rows": len(test),
                }
            )

    prediction_df = pd.DataFrame(all_prediction_rows)
    baseline_df = pd.concat(all_baseline_rows, ignore_index=True)
    selection_df = pd.concat(all_selection_rows, ignore_index=True)
    decile_df = pd.concat(all_deciles, ignore_index=True)
    costs_df = pd.concat(all_costs, ignore_index=True)
    regimes_df = pd.concat(all_regimes, ignore_index=True)
    downloads_df = pd.DataFrame(all_downloads)
    splits_df = pd.DataFrame(split_records)

    prediction_df.to_csv(output_dir / "prediction_metrics.csv", index=False)
    baseline_df.to_csv(output_dir / "baseline_metrics.csv", index=False)
    selection_df.to_csv(output_dir / "model_selection.csv", index=False)
    decile_df.to_csv(output_dir / "prediction_deciles.csv", index=False)
    costs_df.to_csv(output_dir / "strategy_cost_sensitivity.csv", index=False)
    regimes_df.to_csv(output_dir / "volatility_regime_metrics.csv", index=False)
    downloads_df.to_csv(output_dir / "data_manifest.csv", index=False)
    splits_df.to_json(output_dir / "chronological_splits.json", orient="records", indent=2)

    summary = {
        "project": "FLAGSHIP-QR-001",
        "symbols": list(args.symbols),
        "start_date": args.start,
        "end_date": args.end,
        "raw_1s_rows": int(downloads_df["rows"].sum()),
        "archives_verified": int(len(downloads_df)),
        "bar_interval_seconds": 5,
        "horizons": list(HORIZON_BARS.keys()),
        "train_days_per_symbol": 8,
        "validation_days_per_symbol": 3,
        "test_days_per_symbol": len(split_records[0]["test_days"]) if split_records else 0,
        "execution_delay_bars": 1,
        "model": "StandardScaler + Ridge; alpha selected on validation Pearson IC",
        "baseline_protocol": "single-feature OLS fit on train+validation; evaluated once on final test",
        "decile_bootstrap": "1-hour moving blocks; 1000 resamples",
        "cost_grid_one_way_bps": [0, 1, 2, 5, 10],
        "headline": {},
    }

    for symbol in args.symbols:
        row = prediction_df[(prediction_df["symbol"] == symbol) & (prediction_df["horizon"] == "30s")].iloc[0]
        spread = decile_df[(decile_df["symbol"] == symbol) & (decile_df["horizon"] == "30s")].iloc[0]
        zero_cost = costs_df[(costs_df["symbol"] == symbol) & (costs_df["one_way_cost_bps"] == 0.0)].iloc[0]
        two_bps = costs_df[(costs_df["symbol"] == symbol) & (costs_df["one_way_cost_bps"] == 2.0)].iloc[0]
        summary["headline"][symbol] = {
            "test_30s_pearson_ic": float(row["pearson_ic"]),
            "test_30s_spearman_ic": float(row["spearman_ic"]),
            "test_30s_directional_accuracy": float(row["directional_accuracy"]),
            "test_30s_top_minus_bottom_return": float(spread["top_minus_bottom_mean_return"]),
            "test_30s_spread_ci_low": float(spread["spread_bootstrap_ci_low"]),
            "test_30s_spread_ci_high": float(spread["spread_bootstrap_ci_high"]),
            "strategy_active_trades": int(zero_cost["trades"]),
            "mean_gross_log_return_per_trade": float(zero_cost["mean_gross_log_return_per_trade"]),
            "mean_net_log_return_per_trade_at_2bps_one_way": float(two_bps["mean_net_log_return_per_trade"]),
        }

    write_json(output_dir / "research_summary.json", summary)
    report = build_research_report(summary, prediction_df, baseline_df, decile_df, costs_df, regimes_df)
    (report_dir / "research_report.md").write_text(report, encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
