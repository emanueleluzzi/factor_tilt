"""Regress each ETF's excess return on its region's factor set.

Not implemented yet. Planned shape:
  - load data/etfs/ returns and data/factors/ for each region
  - excess return = r_usd - RF, aligned on the weekly grid
  - OLS with Newey-West (HAC) standard errors, `regression.hac_lags` lags
  - one row per ticker: alpha and loadings on `regression.report_factors`,
    t-stats, R-bar^2, N, window start/end, and a flag when the series is
    proxy-extended rather than the fund's own history
  - the headline model is `regression.model_factors` (market + value +
    profitability); the remaining factors are reported alongside for context
"""

from __future__ import annotations

from config import load_config


def main() -> None:
    cfg = load_config()
    raise NotImplementedError(
        f"regress.py is a stub; model = {cfg['regression']['model_factors']}."
    )


if __name__ == "__main__":
    main()
