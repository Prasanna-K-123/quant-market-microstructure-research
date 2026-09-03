from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def plot_deciles(deciles: pd.DataFrame, path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(deciles["decile"], deciles["mean_forward_return"] * 1e4, marker="o")
    ax.axhline(0.0, linewidth=1)
    ax.set_xlabel("Prediction decile (low to high)")
    ax.set_ylabel("Mean execution-lagged forward return (bps)")
    ax.set_title(title)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_cost_sensitivity(costs: pd.DataFrame, path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(costs["round_trip_cost_bps"], costs["mean_net_log_return_per_trade"] * 1e4, marker="o")
    ax.axhline(0.0, linewidth=1)
    ax.set_xlabel("Illustrative round-trip cost (bps)")
    ax.set_ylabel("Mean net log return / active trade (bps)")
    ax.set_title(title)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def build_research_report(
    summary: dict,
    prediction_metrics: pd.DataFrame,
    baseline_metrics: pd.DataFrame,
    decile_summary: pd.DataFrame,
    strategy_costs: pd.DataFrame,
    regime_metrics: pd.DataFrame,
) -> str:
    symbols = ", ".join(summary["symbols"])
    start = summary["start_date"]
    end = summary["end_date"]
    lines = [
        "# Trade-Flow Microstructure Research Report",
        "",
        "## Scope",
        "",
        f"This report analyzes official Binance Spot 1-second kline data for **{symbols}** from **{start} to {end}**, aggregated to 5-second research bars.",
        "Signals use only information available by the signal-bar close. Every modeled target assumes a **one-bar execution delay**, so the analysis does not claim an impossible fill at the same close used to compute the signal.",
        "",
        "The central research question is whether short-horizon taker-order-flow imbalance and recent market-state variables contain reproducible information about subsequent 5s/15s/30s returns, and whether any statistical predictability survives explicit transaction-cost assumptions.",
        "",
        "## Evidence discipline",
        "",
        "- Data archives are downloaded from Binance's official public-data archive and SHA-256 checked against the archive's checksum files.",
        "- Model selection uses only train + validation periods. Final-test rows are untouched until the selected model is frozen.",
        "- Chronological splits are by calendar day; targets whose exit crosses a split boundary are removed.",
        "- Baselines are reported alongside the full model.",
        "- Trading outputs use non-overlapping holding periods and a validation-frozen signal threshold.",
        "- Cost scenarios are illustrative assumptions, not claims about an executable institutional fee/slippage schedule.",
        "- Negative or economically insignificant findings remain in the report.",
        "",
        "## Final-test predictive results",
        "",
        prediction_metrics.to_markdown(index=False, floatfmt=".6g"),
        "",
        "## Transparent baselines",
        "",
        baseline_metrics.to_markdown(index=False, floatfmt=".6g"),
        "",
        "## Prediction-decile response",
        "",
        decile_summary.to_markdown(index=False, floatfmt=".6g"),
        "",
        "## Cost sensitivity",
        "",
        strategy_costs.to_markdown(index=False, floatfmt=".6g"),
        "",
        "## Volatility-regime robustness",
        "",
        regime_metrics.to_markdown(index=False, floatfmt=".6g"),
        "",
        "## Interpretation guardrails",
        "",
        "A positive information coefficient or decile spread is evidence of statistical association on this held-out sample, not proof of durable alpha. A gross strategy result is not an executable P&L claim. Binance Spot data represent one venue and asset class, and the kline schema provides aggregated taker-buy volume rather than full order-book state. Any signal that disappears under modest costs, changes sign across symbols/horizons, or fails in a volatility regime is treated as a limitation rather than tuned away.",
        "",
        "## Reproduction",
        "",
        "Run `python run_research.py`. The pipeline downloads and checksum-verifies the fixed public data window, rebuilds features, performs chronological model selection, evaluates the untouched final test, regenerates CSV evidence and figures, and rewrites this report.",
        "",
    ]
    return "\n".join(lines)
