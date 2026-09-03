from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .features import FEATURE_COLUMNS


ALPHA_GRID = (0.0, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1.0, 10.0, 100.0)


@dataclass(frozen=True)
class DaySplit:
    train_days: tuple[str, ...]
    validation_days: tuple[str, ...]
    test_days: tuple[str, ...]


@dataclass
class FittedResearchModel:
    model: Pipeline
    alpha: float
    validation_ic: float
    threshold_abs_prediction: float
    split: DaySplit


def chronological_day_split(df: pd.DataFrame, train_days: int = 8, validation_days: int = 3) -> DaySplit:
    days = tuple(sorted(df["calendar_day"].dropna().unique().tolist()))
    minimum = train_days + validation_days + 1
    if len(days) < minimum:
        raise ValueError(f"Need at least {minimum} distinct days, got {len(days)}")
    train = days[:train_days]
    validation = days[train_days : train_days + validation_days]
    test = days[train_days + validation_days :]
    return DaySplit(tuple(train), tuple(validation), tuple(test))


def partition_by_days(df: pd.DataFrame, horizon: str, split: DaySplit) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Partition rows and prevent a target exit from crossing a partition boundary."""
    exit_col = f"exit_time_{horizon}"

    def _part(days: tuple[str, ...]) -> pd.DataFrame:
        part = df[df["calendar_day"].isin(days)].copy()
        if part.empty:
            return part
        end = pd.Timestamp(max(days) + "T23:59:59.999999", tz="UTC")
        part = part[pd.to_datetime(part[exit_col], utc=True) <= end]
        return part.reset_index(drop=True)

    return _part(split.train_days), _part(split.validation_days), _part(split.test_days)


def _pearson_ic(y: np.ndarray, prediction: np.ndarray) -> float:
    if len(y) < 3 or np.std(y) == 0 or np.std(prediction) == 0:
        return float("nan")
    return float(np.corrcoef(y, prediction)[0, 1])


def select_and_fit_ridge(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    target_col: str,
    split: DaySplit,
    alpha_grid: tuple[float, ...] = ALPHA_GRID,
    trade_threshold_quantile: float = 0.90,
) -> tuple[FittedResearchModel, pd.DataFrame]:
    """Select Ridge strength on validation IC, then refit on train+validation."""
    X_train = train[FEATURE_COLUMNS].to_numpy(dtype=float)
    y_train = train[target_col].to_numpy(dtype=float)
    X_val = validation[FEATURE_COLUMNS].to_numpy(dtype=float)
    y_val = validation[target_col].to_numpy(dtype=float)

    records: list[dict[str, float]] = []
    best_alpha: float | None = None
    best_ic = -np.inf
    best_pred: np.ndarray | None = None

    for alpha in alpha_grid:
        pipeline = Pipeline(
            [
                ("scale", StandardScaler()),
                ("ridge", Ridge(alpha=alpha, fit_intercept=True)),
            ]
        )
        pipeline.fit(X_train, y_train)
        pred = pipeline.predict(X_val)
        ic = _pearson_ic(y_val, pred)
        mse = float(np.mean((y_val - pred) ** 2))
        records.append({"alpha": float(alpha), "validation_ic": ic, "validation_mse": mse})
        score = -np.inf if not np.isfinite(ic) else ic
        if score > best_ic:
            best_ic = score
            best_alpha = float(alpha)
            best_pred = pred

    if best_alpha is None or best_pred is None:
        raise RuntimeError("Unable to select a finite Ridge model")

    threshold = float(np.quantile(np.abs(best_pred), trade_threshold_quantile))
    combined = pd.concat([train, validation], ignore_index=True)
    final_model = Pipeline(
        [
            ("scale", StandardScaler()),
            ("ridge", Ridge(alpha=best_alpha, fit_intercept=True)),
        ]
    )
    final_model.fit(
        combined[FEATURE_COLUMNS].to_numpy(dtype=float),
        combined[target_col].to_numpy(dtype=float),
    )

    fitted = FittedResearchModel(
        model=final_model,
        alpha=best_alpha,
        validation_ic=float(best_ic),
        threshold_abs_prediction=threshold,
        split=split,
    )
    return fitted, pd.DataFrame.from_records(records)


def predict(model: FittedResearchModel, df: pd.DataFrame) -> np.ndarray:
    return model.model.predict(df[FEATURE_COLUMNS].to_numpy(dtype=float))
