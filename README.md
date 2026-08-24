# factor_tilt

A long-only ETF portfolio, evaluated as a factor-exposure problem rather than a
ticker-picking one. Each fund in the universe is regressed on the Ken French
factor set for its own region — US, Developed, Developed ex-US, Europe, Emerging
— to get empirical loadings on market, size, value, profitability, investment
and momentum, with HAC standard errors and an honest note wherever a short
UCITS history has been extended with a US-listed proxy. Those loadings, plus
factor premia and a residual covariance, give the `mu` and `Sigma` behind
`b = Σ⁻¹μ`. The headline return model is market + value + profitability; the
question the repo exists to answer is what happens to the implied weights as
the estimates are shrunk towards a structured target — the shrinkage path, not
the point solution, is the output of interest.

## Layout

```
config.yaml               universe, factor-set mapping, frequency, shrinkage grid
config.local.yaml         private overrides (gitignored; see .example)
src/config.py             loads both, local wins
src/fetch_factors.py      Ken French daily factors -> weekly -> data/factors/
src/fetch_etfs.py         yfinance closes -> USD -> weekly -> data/etfs/   [stub]
src/regress.py            loadings table with t-stats, R², window, proxy flag [stub]
src/optimize.py           shrunk MV / Black-Litterman along a shrinkage path [stub]
scripts/hooks/pre-commit  blocks private or generated files from being staged
data/                     downloaded inputs (gitignored, rebuilt by the scripts)
outputs/                  tables and figures (gitignored)
```

## Running

```sh
python -m venv .venv && .venv/bin/pip install -r requirements.txt
git config core.hooksPath scripts/hooks     # once, per clone
cp config.local.yaml.example config.local.yaml   # optional, private overrides

python src/fetch_factors.py                 # --sets us,europe to limit
python src/fetch_etfs.py
python src/regress.py
```

Everything under `data/` is downloaded, never committed, and reproducible by
re-running the fetch scripts.

## Data

- **Factors** — Kenneth R. French's data library (5-factor sets plus momentum,
  daily, compounded to the configured frequency). Fetched via
  `pandas_datareader`, falling back to the published CSV zip when the library
  renames a file.
- **Prices** — Yahoo Finance via `yfinance`, adjusted closes, with `EURUSD=X`
  used to put EUR-quoted lines into USD.
- **Frequency** — weekly, Friday-stamped. LSE and Xetra close hours before
  NYSE, so daily returns on a mixed-venue universe are misaligned by
  construction; a weekly grid absorbs it.

Conventions and caveats worth knowing: returns are simple, in USD, in excess of
the French RF; a proxy-extended series is a different fund before its inception
date and every table says so; the Avantis UCITS lines start in 2024 and their
standalone standard errors are wide enough to make the point.
