# Reference validation evidence

The recruiter-facing V1 result is frozen to the documented BTCUSDT/ETHUSDT 1-second Binance Public Data window from 2025-01-02 through 2025-01-15.

## Accepted validation

- accepted analytical code lineage: `c1fb9b0aa0d506e52a4cdd3fcb863a6d09c73297`
- standalone release-stage validation run: `33628144185`
- accepted release artifact SHA-256: `009a2aa04483eba721e9e3d0720f379babd8fc1403a86cdcc6e3bcfdfeec407d`
- that CI run independently downloaded the same 28 official Binance daily archives, verified companion SHA-256 checksums, ran the unit/leakage/accounting tests, and regenerated the frozen reference outputs

## Reproducibility boundary

Raw Binance archives are intentionally not committed because they are public, checksum-addressed, and reproducibly downloaded by the pipeline. The accepted analytical outputs are preserved as validation evidence rather than substituted with a different date window or data source if upstream archives become unavailable.

The project makes no trading-alpha, profitability, Sharpe, or executable-P&L claim. See `RESULTS_AUDIT.md` for the adversarial interpretation of the weak/mixed held-out evidence.
