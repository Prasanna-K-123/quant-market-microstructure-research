import numpy as np
import pandas as pd

from qr_microstructure.evaluation import decile_returns, strategy_cost_sensitivity
from qr_microstructure.modeling import DaySplit, partition_by_days


def test_cost_sensitivity_is_monotone():
    n = 120
    test = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-01-12", periods=n, freq="5s", tz="UTC"),
            "target_30s": np.full(n, 0.001),
        }
    )
    prediction = np.full(n, 0.002)
    costs = strategy_cost_sensitivity(
        test,
        "target_30s",
        prediction,
        threshold_abs_prediction=0.001,
        horizon_bars=6,
        one_way_cost_bps=(0.0, 1.0, 2.0, 5.0),
    )
    net = costs["mean_net_log_return_per_trade"].to_numpy()
    assert np.all(np.diff(net) < 0)
    assert costs["trades"].nunique() == 1


def test_decile_ordering_on_perfect_signal():
    y = np.linspace(-0.01, 0.01, 1000)
    deciles = decile_returns(y, y)
    means = deciles["mean_forward_return"].to_numpy()
    assert np.all(np.diff(means) > 0)


def test_partition_drops_targets_crossing_split_end():
    timestamps = pd.to_datetime(
        ["2025-01-02T23:59:50Z", "2025-01-03T00:00:00Z", "2025-01-04T00:00:00Z"]
    )
    df = pd.DataFrame(
        {
            "calendar_day": ["2025-01-02", "2025-01-03", "2025-01-04"],
            "exit_time_30s": pd.to_datetime(
                ["2025-01-03T00:00:10Z", "2025-01-03T00:00:30Z", "2025-01-04T00:00:30Z"]
            ),
            "timestamp": timestamps,
        }
    )
    split = DaySplit(("2025-01-02",), ("2025-01-03",), ("2025-01-04",))
    train, validation, test = partition_by_days(df, "30s", split)
    assert len(train) == 0
    assert len(validation) == 1
    assert len(test) == 1
