# Data provenance and evidence boundary

## Primary source

The research pipeline uses the official Binance Public Data archive at `data.binance.vision`.

For each configured symbol/day it downloads Spot **1-second kline** ZIP archives using the documented path pattern:

`data/spot/daily/klines/{SYMBOL}/1s/{SYMBOL}-1s-{YYYY-MM-DD}.zip`

Binance documents Spot kline fields as open time, OHLC prices, volume, close time, quote volume, trade count, taker-buy base volume, taker-buy quote volume and an ignored field. From 2025-01-01 onward, Spot archive timestamps are documented in microseconds.

Reference: `binance/binance-public-data` (MIT licensed), README.

## Integrity control

Every downloaded ZIP is hashed with SHA-256. The observed digest must match the companion `.CHECKSUM` file from the same official archive path. A mismatch is a hard pipeline failure and the local cache copy is removed.

The generated `results/data_manifest.csv` records symbol, date, source URL, observed SHA-256 and parsed row count for every archive used by a successful run.

## Why 1-second klines rather than undocumented order-book snapshots

The project intentionally uses a source with documented provenance and stable fields. The available kline schema contains aggregate taker-buy volume and trade count but **not** full bid/ask depth, queue state or exchange-native order messages. The project therefore does not claim to reconstruct a limit-order book or estimate queue position.

The research label "market microstructure" refers specifically to short-horizon trade-flow/price interaction using taker-flow imbalance, trade intensity, volume, realized volatility and price response.

## Derived 5-second bars

The official 1-second observations are aggregated into 5-second research bars using:

- open = first open
- high = maximum high
- low = minimum low
- close = last close
- total/base/quote/taker-buy volume = sum
- number of trades = sum

A 5-second bucket without an observed close is excluded rather than forward-filled into an artificial executable price.

## Evidence boundary

This is public cryptocurrency-venue data. Findings do not automatically generalize to equities, futures, options, other venues or institutional execution. Fee/slippage scenarios are illustrative research assumptions, not claims about a particular account tier or executable institutional cost schedule.
