# factor_tilt

A long-only ETF portfolio treated as a factor-exposure problem rather than a
ticker-picking one. Each fund is regressed on the Ken French factor set for its
own region — US, Developed, Developed ex-US, Europe, Emerging — to get
empirical loadings on market, size, value, profitability, investment and
momentum, with HAC standard errors and an explicit flag wherever a short UCITS
history has been extended with a US-listed proxy. Those loadings, plus factor
premia and a residual covariance, give the `mu` and `Sigma` behind `b = Σ⁻¹μ`.
The headline return model is market + value + profitability; the question the
repo exists to answer is what happens to the implied weights as the estimates
are shrunk towards a structured target — the shrinkage path, not the point
solution, is the output of interest.

## Layout

```
config.py            universe, factor mapping, frequency, model, shrinkage grid
config_local.py      private overrides, gitignored (see below)
pull/factors.py      Ken French factor sets  -> data/factors/<region>.csv
pull/etfs.py         yfinance prices in USD  -> data/etfs/            [stub]
model/regress.py     loadings table          -> outputs/              [stub]
model/optimize.py    shrinkage path          -> outputs/              [stub]
data/                downloaded, gitignored
outputs/             produced, gitignored
.githooks/pre-commit refuses to commit private or generated files
```

## Running

```sh
python -m venv .venv && .venv/bin/pip install -r requirements.txt
git config core.hooksPath .githooks          # once per clone

python pull/factors.py                       # --regions us,europe  --freq ME
python pull/etfs.py
python model/regress.py
```

Every script also imports cleanly from a console at the repo root, so any step
can be run piecemeal:

```python
>>> from pull.factors import build
>>> native, weekly, freq = build("us")
```

Anything account-specific goes in `config_local.py`, which is gitignored. It is
read at the end of `config.py`, so it only restates what differs:

```python
# config_local.py
BASE_CURRENCY = "EUR"
HOLDINGS = {"AVUV": 0.12, "SWRD.L": 0.40}
```

## Data

- **Factors** — Kenneth R. French's data library: the 5-factor sets plus
  momentum, daily where it exists, compounded to the configured frequency.
  Fetched with `pandas_datareader`, falling back to parsing the published CSV
  zip when the library renames a file.
- **Prices** — Yahoo Finance via `yfinance`, adjusted closes, with `EURUSD=X`
  used to put EUR-quoted lines into USD.
- **Frequency** — weekly, Friday-stamped. LSE and Xetra close hours before
  NYSE, so daily returns across a mixed-venue universe are misaligned by
  construction; a weekly grid absorbs it. Emerging markets is the exception:
  French publishes no daily EM file, so that region is monthly.

Returns are simple, in USD, in excess of the French RF. A proxy-extended series
is a different fund before its inception date, and every table says so.
