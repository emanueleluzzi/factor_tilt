"""Download ETF prices -> data/etfs/  [not written yet]

Planned shape:
  - yfinance adjusted closes for every config.UNIVERSE symbol, plus the proxy
    symbols and config.FX_SYMBOL
  - EUR-quoted lines converted to USD (price_eur * EURUSD)
  - resampled to config.FREQUENCY, last observation in the period
  - sanity checks before anything is written, because yfinance returns junk for
    some LSE lines: no zero or negative prices, no repeated-price runs longer
    than a week, |weekly return| > 25% flagged, coverage a plausible fraction of
    the requested window, and the reported currency matching config
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import config


def main():
    raise NotImplementedError(f"stub - {len(config.UNIVERSE)} symbols configured")


if __name__ == "__main__":
    main()
