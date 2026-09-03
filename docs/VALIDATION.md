# Reference validation evidence

The recruiter-facing V1 result is frozen to the documented BTCUSDT/ETHUSDT 1-second Binance Public Data window from 2025-01-02 through 2025-01-15.

## Accepted validation

- accepted analytical code lineage: `c1fb9b0aa0d506e52a4cdd3fcb863a6d09c73297`
- standalone release-stage validation run: `33628144185`
- accepted release artifact SHA-256: `009a2aa04483eba721e9e3d0720f379babd8fc1403a86cdcc6e3bcfdfeec407d`
- standalone repository validation run `33767389469` independently re-ran the fixed reference pipeline successfully before the durable evidence hardening
- `reference/accepted_v1.json` records the accepted headline metrics and SHA-256 for every committed durable result table
- `results/` contains the exact text outputs from the accepted release-stage artifact
- `verify_reference.py` fails if any accepted result file is missing or its SHA-256 differs from the accepted manifest

## Reproducibility boundary

Raw Binance archives are intentionally not committed because they are public, checksum-addressed, and reproducibly downloaded by the pipeline. `results/data_manifest.csv` preserves the 28 accepted archive identities, hashes and row counts. If upstream archives become unavailable, the committed outputs remain the historical accepted V1 evidence; the reference window or data source must not be silently substituted.

The accepted byte-level evidence and a fresh pipeline rerun serve different purposes: the committed files preserve the historical accepted result exactly, while CI independently exercises the fixed-data research pipeline on the current toolchain. Exact floating-point serialization from future dependency versions is not retroactively used to redefine the accepted V1 evidence.

The project makes no trading-alpha, profitability, Sharpe, or executable-P&L claim. See `RESULTS_AUDIT.md` for the adversarial interpretation of the weak/mixed held-out evidence.
