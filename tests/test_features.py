import numpy as np
import pandas as pd

from qr_microstructure.features import HORIZON_BARS, build_features


def synthetic_bars(n: int = 120) -> pd.DataFrame:
    ts = pd.date_range("2025-01-02", periods=n, freq="5s", tz="UTC")
    close = 100.0 * np.exp(np.arange(n) * 0.001)
    return pd.DataFrame(
        {
            "timestamp": ts,
            "symbol": "TEST",
            "open": close * 0.999,
            "high": close * 1.001,
            "low": close * 0.998,
            "close": close,
            "volume": np.full(n, 10.0),
            "quote_volume": close * 10.0,
            "n_trades": np.full(n, 20),
            "taker_buy_base": np.full(n, 7.5),
            "taker_buy_quote": close * 7.5,
        }
    )


def test_imbalance_is_bounded_and_correct():
    featured = build_features(synthetic_bars())
    assert np.allclose(featured["imbalance"], 0.5)
    assert featured["imbalance"].between(-1, 1).all()


def test_execution_lagged_target_uses_next_bar_entry():
    bars = synthetic_bars()
    featured = build_features(bars)
    # With a constant 0.001 log return per 5-second bar, a horizon h should
    # produce h * 0.001 even though entry is delayed by one full bar.
    for label, h in HORIZON_BARS.items():
        observed = featured[f"target_{label}"].dropna().iloc[0]
        assert np.isclose(observed, h * 0.001, atol=1e-12)
        first_idx = featured[f"target_{label}"].first_valid_index()
        assert featured.loc[first_idx, f"entry_time_{label}"] == featured.loc[first_idx + 1, "timestamp"]
        assert featured.loc[first_idx, f"exit_time_{label}"] == featured.loc[first_idx + h + 1, "timestamp"]


def test_features_are_backward_looking():
    bars = synthetic_bars()
    base = build_features(bars)
    mutated = bars.copy()
    mutated.loc[100:, "close"] *= 2.0
    changed = build_features(mutated)
    # Changing future prices must not alter features at earlier timestamps.
    cols = ["imbalance", "imbalance_3", "imbalance_6", "ret_1", "ret_3", "ret_6", "rv_6"]
    pd.testing.assert_frame_equal(base.loc[:90, cols], changed.loc[:90, cols])
