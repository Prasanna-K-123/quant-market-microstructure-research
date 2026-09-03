from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import LinearRegression


@dataclass(frozen=True)
class PredictionMetrics:
    n: int
    pearson_ic: float
    spearman_ic: float
    directional_accuracy: float
    rmse: float
    mae: float


def prediction_metrics(y: np.ndarray, prediction: np.ndarray) -> PredictionMetrics:
    y = np.asarray(y, dtype=float)
    prediction = np.asarray(prediction, dtype=float)
    finite = np.isfinite(y) & np.isfinite(prediction)
    y = y[finite]
    prediction = prediction[finite]
    if len(y) == 0:
        raise ValueError("No finite observations")

    pearson = float(np.corrcoef(y, prediction)[0, 1]) if np.std(y) > 0 and np.std(prediction) > 0 else float("nan")
    spearman = float(spearmanr(y, prediction, nan_policy="omit").statistic) if len(y) > 2 else float("nan")
    nonzero = (y != 0) & (prediction != 0)
    directional = float(np.mean(np.sign(y[nonzero]) == np.sign(prediction[nonzero]))) if nonzero.any() else float("nan")
    rmse = float(np.sqrt(np.mean((y - prediction) ** 2)))
    mae = float(np.mean(np.abs(y - prediction)))
    return PredictionMetrics(len(y), pearson, spearman, directional, rmse, mae)


def baseline_metrics(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
    target_col: str,
) -> pd.DataFrame:
    """
    Evaluate transparent one-feature OLS baselines on the untouched test rows.

    Raw imbalance features are dimensionless while targets are log returns, so using
    the raw feature itself as a return forecast makes RMSE/MAE meaningless. Each
    baseline therefore fits a single-feature linear map on train+validation only,
    then predicts the final test. This preserves interpretability while keeping all
    reported error metrics in target-return units and avoids any test-set fitting.
    """
    development = pd.concat([train, validation], ignore_index=True)
    y_dev = development[target_col].to_numpy(dtype=float)
    y_test = test[target_col].to_numpy(dtype=float)
    baseline_features = {
        "order_imbalance_ols": "imbalance",
        "last_5s_return_ols": "ret_1",
        "rolling_30s_imbalance_ols": "imbalance_6",
    }
    records = []
    for name, feature_col in baseline_features.items():
        x_dev = development[[feature_col]].to_numpy(dtype=float)
        x_test = test[[feature_col]].to_numpy(dtype=float)
        model = LinearRegression(fit_intercept=True)
        model.fit(x_dev, y_dev)
        pred = model.predict(x_test)
        m = prediction_metrics(y_test, pred)
        records.append(
            {
                "model": name,
                "feature": feature_col,
                "fit_scope": "train_plus_validation",
                "coefficient": float(model.coef_[0]),
                "intercept": float(model.intercept_),
                "n": m.n,
                "pearson_ic": m.pearson_ic,
                "spearman_ic": m.spearman_ic,
                "directional_accuracy": m.directional_accuracy,
                "rmse": m.rmse,
                "mae": m.mae,
            }
        )
    return pd.DataFrame(records)


def decile_returns(y: np.ndarray, prediction: np.ndarray, bins: int = 10) -> pd.DataFrame:
    work = pd.DataFrame({"target": np.asarray(y, dtype=float), "prediction": np.asarray(prediction, dtype=float)})
    work = work.replace([np.inf, -np.inf], np.nan).dropna()
    if len(work) < bins * 5:
        raise ValueError("Not enough rows for decile analysis")
    ranks = work["prediction"].rank(method="first")
    work["decile"] = pd.qcut(ranks, q=bins, labels=False) + 1
    result = (
        work.groupby("decile", observed=True)
        .agg(mean_forward_return=("target", "mean"), median_forward_return=("target", "median"), observations=("target", "size"))
        .reset_index()
    )
    return result


def long_short_decile_spread(deciles: pd.DataFrame) -> float:
    low = float(deciles.loc[deciles["decile"] == deciles["decile"].min(), "mean_forward_return"].iloc[0])
    high = float(deciles.loc[deciles["decile"] == deciles["decile"].max(), "mean_forward_return"].iloc[0])
    return high - low


def block_bootstrap_decile_spread(
    y: np.ndarray,
    prediction: np.ndarray,
    block_size: int = 720,
    resamples: int = 1000,
    seed: int = 2027,
) -> tuple[float, float, float]:
    """Moving-block bootstrap for top-minus-bottom predicted-return decile spread."""
    y = np.asarray(y, dtype=float)
    prediction = np.asarray(prediction, dtype=float)
    n = len(y)
    if n < max(100, block_size * 2):
        return float("nan"), float("nan"), float("nan")

    base_deciles = decile_returns(y, prediction)
    point = long_short_decile_spread(base_deciles)
    rng = np.random.default_rng(seed)
    starts = np.arange(0, max(1, n - block_size + 1))
    spreads: list[float] = []
    blocks_needed = int(np.ceil(n / block_size))

    for _ in range(resamples):
        sampled_starts = rng.choice(starts, size=blocks_needed, replace=True)
        idx = np.concatenate([np.arange(s, min(s + block_size, n)) for s in sampled_starts])[:n]
        try:
            spread = long_short_decile_spread(decile_returns(y[idx], prediction[idx]))
            spreads.append(spread)
        except ValueError:
            continue

    if not spreads:
        return point, float("nan"), float("nan")
    low, high = np.quantile(np.asarray(spreads), [0.025, 0.975])
    return point, float(low), float(high)


def strategy_cost_sensitivity(
    test: pd.DataFrame,
    target_col: str,
    prediction: np.ndarray,
    threshold_abs_prediction: float,
    horizon_bars: int,
    one_way_cost_bps: tuple[float, ...] = (0.0, 1.0, 2.0, 5.0, 10.0),
) -> pd.DataFrame:
    """
    Non-overlapping sign strategy using a validation-frozen signal threshold.

    Signal is already paired with an execution-lagged target. We additionally sample
    every `horizon_bars` observation so holding periods do not overlap. Cost is an
    explicitly illustrative per-side bps assumption; round-trip cost is twice that.
    """
    work = test[["timestamp", target_col]].copy().reset_index(drop=True)
    work["prediction"] = np.asarray(prediction, dtype=float)
    work = work.iloc[::max(1, horizon_bars)].copy()
    work["position"] = np.where(
        np.abs(work["prediction"]) >= threshold_abs_prediction,
        np.sign(work["prediction"]),
        0.0,
    )
    work["gross_log_return"] = work["position"] * work[target_col]
    active = work["position"] != 0
    records: list[dict[str, float]] = []

    for cost in one_way_cost_bps:
        round_trip = 2.0 * float(cost) / 1e4
        net = work["gross_log_return"] - active.astype(float) * round_trip
        active_net = net[active]
        active_gross = work.loc[active, "gross_log_return"]
        records.append(
            {
                "one_way_cost_bps": float(cost),
                "round_trip_cost_bps": float(2.0 * cost),
                "candidate_timestamps": int(len(work)),
                "trades": int(active.sum()),
                "participation_rate": float(active.mean()),
                "mean_gross_log_return_per_trade": float(active_gross.mean()) if len(active_gross) else float("nan"),
                "mean_net_log_return_per_trade": float(active_net.mean()) if len(active_net) else float("nan"),
                "median_net_log_return_per_trade": float(active_net.median()) if len(active_net) else float("nan"),
                "net_hit_rate": float((active_net > 0).mean()) if len(active_net) else float("nan"),
                "cumulative_net_log_return": float(active_net.sum()) if len(active_net) else 0.0,
            }
        )
    return pd.DataFrame(records)


def volatility_regime_metrics(test: pd.DataFrame, target_col: str, prediction: np.ndarray) -> pd.DataFrame:
    work = test[[target_col, "rv_6"]].copy().reset_index(drop=True)
    work["prediction"] = np.asarray(prediction, dtype=float)
    median_rv = float(work["rv_6"].median())
    work["regime"] = np.where(work["rv_6"] > median_rv, "high_vol", "low_vol")
    rows = []
    for regime, part in work.groupby("regime"):
        m = prediction_metrics(part[target_col].to_numpy(), part["prediction"].to_numpy())
        rows.append(
            {
                "regime": regime,
                "n": m.n,
                "pearson_ic": m.pearson_ic,
                "spearman_ic": m.spearman_ic,
                "directional_accuracy": m.directional_accuracy,
            }
        )
    return pd.DataFrame(rows)
