from __future__ import annotations

import hashlib
import io
import time
import zipfile
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests


KLINE_COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "n_trades",
    "taker_buy_base",
    "taker_buy_quote",
    "ignore",
]

NUMERIC_COLUMNS = [
    "open",
    "high",
    "low",
    "close",
    "volume",
    "quote_volume",
    "n_trades",
    "taker_buy_base",
    "taker_buy_quote",
]


@dataclass(frozen=True)
class DownloadRecord:
    symbol: str
    day: str
    url: str
    sha256: str
    rows: int


def date_range(start: date, end: date) -> Iterable[date]:
    """Yield calendar days inclusively."""
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _binance_daily_1s_url(symbol: str, day: date) -> str:
    ds = day.isoformat()
    return (
        "https://data.binance.vision/data/spot/daily/klines/"
        f"{symbol}/1s/{symbol}-1s-{ds}.zip"
    )


def _download(url: str, timeout: int = 90, attempts: int = 4) -> bytes:
    last_error: Exception | None = None
    headers = {"User-Agent": "qr-microstructure-research/1.0"}
    for attempt in range(attempts):
        try:
            response = requests.get(url, timeout=timeout, headers=headers)
            response.raise_for_status()
            return response.content
        except Exception as exc:  # pragma: no cover - network behavior
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    raise RuntimeError(f"Failed to download {url}") from last_error


def _expected_checksum(checksum_bytes: bytes, filename: str) -> str:
    text = checksum_bytes.decode("utf-8").strip()
    if not text:
        raise ValueError(f"Empty checksum file for {filename}")
    first = text.splitlines()[0].strip().split()[0]
    if len(first) != 64:
        raise ValueError(f"Malformed SHA-256 checksum for {filename}: {text!r}")
    return first.lower()


def _timestamp_unit(values: pd.Series) -> str:
    sample = int(values.dropna().iloc[0])
    # Binance Spot archive uses microseconds from 2025-01-01 onward.
    return "us" if sample >= 10**15 else "ms"


def parse_kline_zip(content: bytes, symbol: str) -> pd.DataFrame:
    """Parse one official Binance 1-second kline ZIP into a validated DataFrame."""
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        csv_names = [name for name in zf.namelist() if name.lower().endswith(".csv")]
        if len(csv_names) != 1:
            raise ValueError(f"Expected one CSV in archive, found {csv_names}")
        with zf.open(csv_names[0]) as handle:
            df = pd.read_csv(handle, header=None, names=KLINE_COLUMNS)

    if df.empty:
        raise ValueError(f"Archive for {symbol} parsed to zero rows")
    if len(df.columns) != len(KLINE_COLUMNS):
        raise ValueError("Unexpected kline schema")

    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="raise")

    unit = _timestamp_unit(df["open_time"])
    df["timestamp"] = pd.to_datetime(df["open_time"], unit=unit, utc=True)
    df["symbol"] = symbol
    df = df.sort_values("timestamp").drop_duplicates("timestamp", keep="last")

    if not df["timestamp"].is_monotonic_increasing:
        raise ValueError("Timestamps are not monotonic")
    if (df["high"] < df["low"]).any():
        raise ValueError("Found high < low")
    if (df[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("Non-positive prices found")
    if (df[["volume", "quote_volume", "n_trades", "taker_buy_base", "taker_buy_quote"]] < 0).any().any():
        raise ValueError("Negative trade/volume field found")
    if (df["taker_buy_base"] - df["volume"] > 1e-9).any():
        raise ValueError("Taker-buy base volume exceeds total volume")

    return df[
        [
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
            "taker_buy_quote",
        ]
    ].reset_index(drop=True)


def load_symbol_days(
    symbol: str,
    start: date,
    end: date,
    cache_dir: Path,
    verify_checksum: bool = True,
) -> tuple[pd.DataFrame, list[DownloadRecord]]:
    """Download/cache official Binance 1-second spot klines and verify SHA-256."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    frames: list[pd.DataFrame] = []
    records: list[DownloadRecord] = []

    for day in date_range(start, end):
        url = _binance_daily_1s_url(symbol, day)
        filename = url.rsplit("/", 1)[-1]
        path = cache_dir / filename

        if path.exists():
            content = path.read_bytes()
        else:
            content = _download(url)
            path.write_bytes(content)

        observed = hashlib.sha256(content).hexdigest()
        if verify_checksum:
            checksum_content = _download(url + ".CHECKSUM")
            expected = _expected_checksum(checksum_content, filename)
            if observed.lower() != expected:
                path.unlink(missing_ok=True)
                raise ValueError(
                    f"Checksum mismatch for {filename}: observed={observed}, expected={expected}"
                )

        day_df = parse_kline_zip(content, symbol)
        frames.append(day_df)
        records.append(
            DownloadRecord(
                symbol=symbol,
                day=day.isoformat(),
                url=url,
                sha256=observed,
                rows=len(day_df),
            )
        )

    data = pd.concat(frames, ignore_index=True)
    data = data.sort_values("timestamp").drop_duplicates("timestamp", keep="last")
    return data.reset_index(drop=True), records


def aggregate_to_5s(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate official 1-second klines into 5-second research bars."""
    if df.empty:
        raise ValueError("Cannot aggregate an empty frame")
    symbol_values = df["symbol"].dropna().unique()
    if len(symbol_values) != 1:
        raise ValueError("aggregate_to_5s expects one symbol")
    symbol = str(symbol_values[0])

    indexed = df.set_index("timestamp")
    agg = indexed.resample("5s", label="right", closed="right").agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
            "quote_volume": "sum",
            "n_trades": "sum",
            "taker_buy_base": "sum",
            "taker_buy_quote": "sum",
        }
    )
    # Binance can emit empty 1-second intervals. A 5-second bucket without any close
    # has no executable price and is therefore excluded rather than forward-filled.
    agg = agg.dropna(subset=["close"]).reset_index()
    agg["symbol"] = symbol
    return agg[
        [
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
            "taker_buy_quote",
        ]
    ]
