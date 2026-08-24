"""Download Ken French factor sets -> data/factors/<region>.csv

One file per region: Mkt-RF, SMB, HML, RMW, CMA, WML, RF, n_obs. Returns are
decimals, not percent. Daily sets are compounded up to config.FREQUENCY;
emerging has no daily file at source and is written monthly, flagged loudly.

    python pull/factors.py                  # every region the universe uses
    python pull/factors.py --regions us,europe
    python pull/factors.py --freq ME

Or, from a console at the repo root:

    >>> from pull.factors import build, fetch
    >>> raw, weekly = build("us")
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import io
import re
import zipfile

import pandas as pd
import requests

import config

# pandas_datareader points at http, not https; matching it keeps the fallback
# working when the reader itself does.
FRENCH_ZIP = "http://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/{name}_CSV.zip"

MISSING = [-99.99, -999.0, -9999.0]           # French's missing-data codes
PERIODS_PER_YEAR = {"D": 252, "W": 52, "M": 12}
RENAMES = {"Mom": "WML"}                      # "Mom" in the US file, "WML" elsewhere


# --------------------------------------------------------------------------- #
# Fetching
# --------------------------------------------------------------------------- #
def fetch(name, start=None, end=None):
    """One French dataset as a DataFrame indexed by timestamp, in percent.

    Tries pandas_datareader first and falls back to parsing the published CSV
    zip, which is what saves us when French renames a file and the reader's
    hard-coded name goes stale.
    """
    start = start or config.START
    end = end or config.END
    try:
        from pandas_datareader import data as web

        frame = web.DataReader(name, "famafrench", start=start, end=end)[0]
        source = "pandas_datareader"
    except Exception as exc:
        print(f"    reader failed ({type(exc).__name__}: {exc})")
        print("    falling back to the CSV zip")
        frame = _from_zip(name)
        source = "zip"

    frame = frame.rename(columns=lambda c: RENAMES.get(c.strip(), c.strip()))
    frame.index = _timestamps(frame.index)
    frame = frame.mask(frame.isin(MISSING)).sort_index()
    return frame, source


def _from_zip(name):
    response = requests.get(
        FRENCH_ZIP.format(name=name),
        timeout=60,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    member = next(n for n in archive.namelist() if n.lower().endswith(".csv"))
    return parse_csv(archive.read(member).decode("latin-1"))


def parse_csv(text):
    """First date-keyed block of a French CSV.

    The files open with a paragraph of preamble, then a header row, then rows
    keyed by YYYYMMDD (daily) or YYYYMM (monthly), then sometimes a second block
    of annual data and a copyright line. We want the first block only.
    """
    lines = text.splitlines()
    is_data = re.compile(r"^\s*(\d{6}|\d{8})\s*,")

    first = next((i for i, line in enumerate(lines) if is_data.match(line)), None)
    if first is None:
        raise ValueError("no date-keyed rows in the French CSV")
    last = first
    while last + 1 < len(lines) and is_data.match(lines[last + 1]):
        last += 1

    header = None
    for i in range(first - 1, -1, -1):
        if "," in lines[i] and re.search(r"[A-Za-z]", lines[i]):
            header = [c.strip() for c in lines[i].split(",")]
            break
    if header is None:
        raise ValueError("no header row in the French CSV")
    header[0] = "date"

    frame = pd.read_csv(
        io.StringIO("\n".join(lines[first : last + 1])), names=header, index_col=0
    )
    frame.index = frame.index.astype(str).str.strip()
    return frame.apply(pd.to_numeric, errors="coerce")


def _timestamps(index):
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
def native_freq(index):
    """'D' or 'M', from the median spacing of the index."""
    if len(index) < 3:
        return "D"
    return "M" if pd.Series(index).diff().dt.days.median() > 20 else "D"


def compound(frame, freq):
    """Compound decimal returns up to `freq`.

    Mkt-RF is rebuilt as compound(Mkt) - compound(RF) rather than compounded
    directly: the excess return of a compounded position is not the compound of
    the excess returns. The long-short factors are compounded as they stand,
    which is the usual convention and a mild approximation.
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


def build(region, freq=None):
    """Fetch, merge and resample one region. Returns (native, resampled, freq)."""
    freq = freq or config.FREQUENCY
    spec = config.FACTOR_SETS[region]

    five, src = fetch(spec["five_factor"])
    print(f"    {spec['five_factor']}: {len(five)} rows via {src}")
    mom, src = fetch(spec["momentum"])
    print(f"    {spec['momentum']}: {len(mom)} rows via {src}")

    frame = five.join(mom[["WML"]], how="left") / 100.0
    frame = frame.loc[config.START : config.END] if config.END else frame.loc[config.START :]

    if native_freq(frame.index) == "M" and not freq.upper().startswith("M"):
        print(f"    !! {region} is monthly at source - French publishes no daily")
        print(f"       file for it. Writing monthly; it cannot be regressed at {freq}.")
        freq = "ME"

    return frame, (frame if freq.upper() == "D" else compound(frame, freq)), freq


def summarise(region, frame, freq):
    """Annualised mean and vol per factor, for eyeballing what came back."""
    ppy = PERIODS_PER_YEAR[freq[0].upper()]
    body = frame[[c for c in frame.columns if c != "n_obs"]]
    return pd.DataFrame(
        {
            "region": region,
            "freq": freq,
            "n": body.notna().sum(),
            "start": body.apply(lambda s: s.first_valid_index().date()),
            "end": body.apply(lambda s: s.last_valid_index().date()),
            "ann_mean_%": body.mean() * ppy * 100,
            "ann_vol_%": body.std() * (ppy ** 0.5) * 100,
        }
    )


# --------------------------------------------------------------------------- #
def main(argv=None):
    parser = argparse.ArgumentParser(description="Download Ken French factor sets.")
    parser.add_argument("--regions", help="comma-separated (default: those the universe uses)")
    parser.add_argument("--freq", help=f"override config.FREQUENCY (currently {config.FREQUENCY})")
    args = parser.parse_args(argv)

    wanted = [r.strip() for r in args.regions.split(",")] if args.regions else config.regions()
    unknown = [r for r in wanted if r not in config.FACTOR_SETS]
    if unknown:
        raise SystemExit(f"unknown region(s): {', '.join(unknown)}")

    config.FACTOR_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ken French factors -> {config.FACTOR_DIR}")
    print(f"  {config.START} .. {config.END or 'today'}, target {args.freq or config.FREQUENCY}\n")

    summaries = []
    for region in wanted:
        print(f"  {region}")
        _, frame, freq = build(region, args.freq)
        out = config.FACTOR_DIR / f"{region}.csv"
        frame.to_csv(out)
        print(f"    -> {out.name}: {len(frame)} rows at {freq}\n")
        summaries.append(summarise(region, frame, freq))

    report = pd.concat(summaries)
    print("Annualised:\n")
    with pd.option_context("display.width", 140, "display.float_format", "{:.2f}".format):
        print(report.to_string())
    return report


if __name__ == "__main__":
    main()
