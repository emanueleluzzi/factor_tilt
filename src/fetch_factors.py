"""Download Ken French factor sets and write them to data/factors/.

For each region in config.factor_sets: pull the 5-factor file and the momentum
file, merge them, convert percent -> decimal, compound up to the configured
frequency, and save. RF travels with the 5-factor file and is kept alongside.

Two wrinkles the script handles rather than hides:

* The Emerging sets exist only at monthly frequency. A set whose native
  frequency is coarser than the target is written at its native frequency and
  loudly flagged - those lines have to be regressed monthly.
* pandas_datareader breaks whenever French renames a file, so every fetch falls
  back to downloading and parsing the published CSV zip directly.

Usage:
    python src/fetch_factors.py                 # every set used by the universe
    python src/fetch_factors.py --sets us,europe
    python src/fetch_factors.py --all --refresh
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import zipfile

import pandas as pd
import requests

from config import load_config, path, regions

FRENCH_ZIP = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/{name}_CSV.zip"
)

# French codes missing data as -99.99 / -999.
MISSING = [-99.99, -999.0, -9999.0]

PERIODS_PER_YEAR = {"D": 252, "W": 52, "M": 12}

# The momentum column is "Mom" in the US file and "WML" everywhere else.
FACTOR_RENAMES = {"Mom": "WML"}


# --------------------------------------------------------------------------- #
# Fetching
# --------------------------------------------------------------------------- #
def _via_datareader(name: str, start, end) -> pd.DataFrame:
    from pandas_datareader import data as web

    raw = web.DataReader(name, "famafrench", start=start, end=end)
    return raw[0]  # [0] is the base table; monthly files put annual data in [1]


def _via_zip(name: str) -> pd.DataFrame:
    """Download and parse the raw CSV zip - the fallback when the reader trips."""
    response = requests.get(FRENCH_ZIP.format(name=name), timeout=60)
    response.raise_for_status()
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    member = next(n for n in archive.namelist() if n.lower().endswith(".csv"))
    return _parse_french_csv(archive.read(member).decode("latin-1"))


def _parse_french_csv(text: str) -> pd.DataFrame:
    """Pull the first date-indexed block out of a French CSV.

    The files carry a paragraph of preamble, then a header row, then rows keyed
    by YYYYMMDD (daily) or YYYYMM (monthly), then sometimes a second block of
    annual data and a copyright line.
    """
    lines = text.splitlines()
    is_data = re.compile(r"^\s*(\d{6}|\d{8})\s*,")

    first = next((i for i, line in enumerate(lines) if is_data.match(line)), None)
    if first is None:
        raise ValueError("no date-keyed rows found in the French CSV")

    last = first
    while last + 1 < len(lines) and is_data.match(lines[last + 1]):
        last += 1

    header = None
    for i in range(first - 1, -1, -1):
        if "," in lines[i] and re.search(r"[A-Za-z]", lines[i]):
            header = [c.strip() for c in lines[i].split(",")]
            break
    if header is None:
        raise ValueError("no header row found in the French CSV")
    header[0] = "date"

    frame = pd.read_csv(
        io.StringIO("\n".join(lines[first : last + 1])),
        names=header,
        index_col=0,
    )
    frame.index = frame.index.astype(str).str.strip()
    return frame.apply(pd.to_numeric, errors="coerce")


def fetch_dataset(name: str, start, end) -> tuple[pd.DataFrame, str]:
    """Return (frame indexed by timestamp, which source served it)."""
    try:
        frame = _via_datareader(name, start, end)
        source = "pandas_datareader"
    except Exception as exc:  # renamed file, reader bug, transient network
        print(f"    reader failed ({type(exc).__name__}: {exc}); falling back to zip")
        frame = _via_zip(name)
        source = "zip"

    frame = frame.rename(columns=lambda c: FACTOR_RENAMES.get(c.strip(), c.strip()))
    frame.index = _to_timestamps(frame.index)
    frame = frame.mask(frame.isin(MISSING))
    return frame.sort_index(), source


def _to_timestamps(index) -> pd.DatetimeIndex:
    """French dates arrive as PeriodIndex, DatetimeIndex, or YYYYMMDD strings."""
    if isinstance(index, pd.PeriodIndex):
        return index.to_timestamp(how="end").normalize()
    if isinstance(index, pd.DatetimeIndex):
        return index
    keys = pd.Index(index).astype(str).str.strip()
    if keys.str.len().max() == 6:
        return pd.PeriodIndex(keys, freq="M").to_timestamp(how="end").normalize()
    return pd.to_datetime(keys, format="%Y%m%d")


# --------------------------------------------------------------------------- #
# Shaping
# --------------------------------------------------------------------------- #
def native_freq(index: pd.DatetimeIndex) -> str:
    """'D' or 'M', inferred from the median spacing of the index."""
    if len(index) < 3:
        return "D"
    gap = pd.Series(index).diff().dt.days.median()
    return "M" if gap > 20 else "D"


def compound(frame: pd.DataFrame, freq: str) -> pd.DataFrame:
    """Compound decimal returns up to `freq`.

    Mkt-RF is rebuilt as (compounded market) - (compounded RF) rather than
    compounded directly: the excess return of a compounded position is not the
    compound of the excess returns. The long-short factors are compounded as
    they stand, which is the usual convention and a mild approximation.
    """
    work = frame.copy()
    has_market = {"Mkt-RF", "RF"}.issubset(work.columns)
    if has_market:
        work["Mkt"] = work["Mkt-RF"] + work["RF"]
        work = work.drop(columns=["Mkt-RF"])

    grouped = work.resample(freq)
    out = grouped.agg(lambda s: (1.0 + s.dropna()).prod() - 1.0 if s.notna().any() else float("nan"))
    out["n_obs"] = grouped.size()

    if has_market:
        out["Mkt-RF"] = out["Mkt"] - out["RF"]
        out = out.drop(columns=["Mkt"])
    return out.dropna(how="all")


def build_set(name: str, spec: dict, start, end, freq: str):
    print(f"  {name}")
    five, src5 = fetch_dataset(spec["five_factor"], start, end)
    print(f"    {spec['five_factor']}: {five.shape[0]} rows via {src5}")
    mom, srcm = fetch_dataset(spec["momentum"], start, end)
    print(f"    {spec['momentum']}: {mom.shape[0]} rows via {srcm}")

    frame = five.join(mom[["WML"]], how="left") / 100.0
    frame = frame.loc[str(start) :] if not end else frame.loc[str(start) : str(end)]

    native = native_freq(frame.index)
    target = freq
    if native == "M" and not freq.upper().startswith("M"):
        print(
            f"    !! {name} is monthly at source - French publishes no daily file. "
            "Writing monthly; these lines cannot be regressed weekly."
        )
        target = "ME"

    resampled = frame if target.upper() == "D" else compound(frame, target)
    return frame, resampled, target


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def summarise(name: str, frame: pd.DataFrame, freq: str) -> pd.DataFrame:
    ppy = PERIODS_PER_YEAR[freq[0].upper()]
    body = frame[[c for c in frame.columns if c != "n_obs"]]
    return pd.DataFrame(
        {
            "set": name,
            "freq": freq,
            "n": body.notna().sum(),
            "start": body.apply(lambda s: s.first_valid_index().date()),
            "end": body.apply(lambda s: s.last_valid_index().date()),
            "ann_mean_%": body.mean() * ppy * 100,
            "ann_vol_%": body.std() * (ppy ** 0.5) * 100,
        }
    )


# --------------------------------------------------------------------------- #
def main() -> None:
    cfg = load_config()
    parser = argparse.ArgumentParser(description="Fetch Ken French factor sets.")
    parser.add_argument("--sets", help="comma-separated sets (default: those the universe uses)")
    parser.add_argument("--all", action="store_true", help="every set in config.factor_sets")
    parser.add_argument("--freq", help="override data.frequency")
    parser.add_argument("--refresh", action="store_true", help="redownload even if cached")
    args = parser.parse_args()

    freq = args.freq or cfg["data"]["frequency"]
    start, end = cfg["data"]["start"], cfg["data"]["end"]

    if args.sets:
        wanted = [s.strip() for s in args.sets.split(",")]
    elif args.all:
        wanted = list(cfg["factor_sets"])
    else:
        wanted = regions(cfg)

    unknown = [s for s in wanted if s not in cfg["factor_sets"]]
    if unknown:
        sys.exit(f"unknown factor set(s): {', '.join(unknown)}")

    out_dir = path(cfg, "factor_dir")
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(exist_ok=True)

    print(f"Ken French factors -> {out_dir}")
    print(f"  window {start} .. {end or 'today'}, target frequency {freq}\n")

    summaries = []
    for name in wanted:
        target_file = out_dir / f"{name}.csv"
        if target_file.exists() and not args.refresh:
            cached = pd.read_csv(target_file, index_col=0, parse_dates=True)
            print(f"  {name}: cached ({len(cached)} rows); --refresh to redownload")
            summaries.append(summarise(name, cached, native_freq(cached.index)))
            continue

        raw, resampled, used = build_set(name, cfg["factor_sets"][name], start, end, freq)
        raw.to_csv(raw_dir / f"{name}_native.csv")
        resampled.to_csv(target_file)
        print(f"    -> {target_file.name}: {len(resampled)} rows at {used}")
        summaries.append(summarise(name, resampled, used))

    print("\nAnnualised, read back from the written files:\n")
    report = pd.concat(summaries)
    with pd.option_context("display.width", 140, "display.float_format", "{:.2f}".format):
        print(report.to_string())


if __name__ == "__main__":
    main()
