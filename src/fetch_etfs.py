"""Download ETF adjusted closes from yfinance, convert to USD, resample.

Not implemented yet. Planned shape:
  - pull adjusted closes for every `universe` symbol plus `data.fx_symbol`
  - convert EUR-quoted lines to USD (price_eur * EURUSD)
  - resample to `data.frequency` (last observation in the period)
  - sanity-check each series (see checks below) before writing data/etfs/
  - write both the price panel and the simple-return panel

Sanity checks worth having, because yfinance returns junk for some LSE lines:
  - no zero / negative prices, no runs of repeated prices longer than a week
  - |weekly return| < 25% flagged for eyeballing
  - series covers a plausible fraction of the requested window
  - currency of the yfinance metadata matches the config'd currency
"""

from __future__ import annotations

from config import load_config


def main() -> None:
    cfg = load_config()
    raise NotImplementedError(
        f"fetch_etfs.py is a stub; {len(cfg['universe'])} symbols configured."
    )


if __name__ == "__main__":
    main()
