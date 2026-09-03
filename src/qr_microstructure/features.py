from __future__ import annotations

import numpy as np
import pandas as pd


FEATURE_COLUMNS = [
    "imbalance",
    "imbalance_3",
    "imbalance_6",
    "ret_1",
    "ret_3",
    "ret_6",
    "rv_6",
    "log_quote_volume",
    "trade_intensity",
    "volume_z_60",
    "range_bps",
]

HORIZON_BARS = {"5s": 1, "15s": 3, "30s": 6}


def _rolling_zscore(series: pd.Series, window: int) -> pd.Series:
    mean = series.rolling(window, min_periods=window).mean()
    std = series.rolling(window, min_periods=window).std(ddof=0)
    return (series - mean) / std.replace(0.0, np.nan)


def build_features(bars: pd.DataFrame) -> pd.DataFrame:
    """
    Build strictly backward-looking microstructure features and execution-lagged targets.

    Signal time is the close of bar t. Targets assume a conservative one-bar execution
    delay: entry at close(t+1), exit h bars after entry. This avoids claiming fills at
    the same close used to calculate the signal.
    """
    if bars.empty:
        raise ValueError("bars cannot be empty")
    required = {
        "timestamp",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "quote_volume",
        "n_trades",
        "taker_buy_base",
    }
    missing = required.difference(bars.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df = bars.sort_values("timestamp").reset_index(drop=True).copy()
    eps = 1e-12

    # Buyer-maker=False corresponds to buyer-initiated (taker-buy) volume in Binance
    # kline data. The imbalance is bounded [-1, 1] when volumes are internally valid.
    df["imbalance"] = (
        2.0 * df["taker_buy_base"] - df["volume"]
    ) / (df["volume"] + eps)
    df.loc[df["volume"] <= eps, "imbalance"] = 0.0
    df["imbalance"] = df["imbalance"].clip(-1.0, 1.0)

    log_price = np.log(df["close"].astype(float))
    df["ret_1"] = log_price.diff(1)
    df["ret_3"] = log_price.diff(3)
    df["ret_6"] = log_price.diff(6)
    df["imbalance_3"] = df["imbalance"].rolling(3, min_periods=3).mean()
    df["imbalance_6"] = df["imbalance"].rolling(6, min_periods=6).mean()
    df["rv_6"] = df["ret_1"].rolling(6, min_periods=6).std(ddof=0)
    df["log_quote_volume"] = np.log1p(df["quote_volume"].clip(lower=0.0))
    df["trade_intensity"] = np.log1p(df["n_trades"].clip(lower=0.0))
    df["volume_z_60"] = _rolling_zscore(df["log_quote_volume"], 60)
    df["range_bps"] = (
        (df["high"].astype(float) - df["low"].astype(float))
        / df["close"].astype(float).replace(0.0, np.nan)
        * 1e4
    )

    for label, h in HORIZON_BARS.items():
        entry = log_price.shift(-1)
        exit_ = log_price.shift(-(h + 1))
        df[f"target_{label}"] = exit_ - entry
        df[f"entry_time_{label}"] = df["timestamp"].shift(-1)
        df[f"exit_time_{label}"] = df["timestamp"].shift(-(h + 1))

    df["calendar_day"] = pd.to_datetime(df["timestamp"], utc=True).dt.strftime("%Y-%m-%d")
    return df


def usable_rows(feature_frame: pd.DataFrame, horizon: str) -> pd.DataFrame:
    if horizon not in HORIZON_BARS:
        raise ValueError(f"Unknown horizon: {horizon}")
    target = f"target_{horizon}"
    entry_time = f"entry_time_{horizon}"
    exit_time = f"exit_time_{horizon}"
    subset = feature_frame.dropna(subset=FEATURE_COLUMNS + [target, entry_time, exit_time]).copy()
    finite = np.isfinite(subset[FEATURE_COLUMNS + [target]].to_numpy(dtype=float)).all(axis=1)
    return subset.loc[finite].reset_index(drop=True)
