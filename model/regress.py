"""Factor loadings per ETF -> outputs/  [not written yet]

Planned shape:
  - load data/etfs/ and the region's file from data/factors/
  - excess return = r_usd - RF on the shared date grid
  - OLS with Newey-West standard errors, config.HAC_LAGS lags
  - one row per ticker: alpha and loadings on config.REPORT_FACTORS, t-stats,
    adjusted R^2, N, window start and end, and a flag wherever the series is
    proxy-extended rather than the fund's own history
  - the headline model is config.MODEL_FACTORS - market, value, profitability
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import config


def main():
    raise NotImplementedError(f"stub - model is {config.MODEL_FACTORS}")


if __name__ == "__main__":
    main()
