"""All settings for the project. Plain Python, no parsing step.

Private overrides live in config_local.py (gitignored). If that file exists its
names replace the ones below, so it only has to restate what differs:

    # config_local.py
    BASE_CURRENCY = "EUR"
    HOLDINGS = {"AVUV": 0.12, ...}

Nothing account-specific belongs in this file. The weights here are
illustrative.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUTPUTS = ROOT / "outputs"
FACTOR_DIR = DATA / "factors"
PRICE_DIR = DATA / "etfs"

# --------------------------------------------------------------------------- #
# Sample
# --------------------------------------------------------------------------- #
START = "2015-01-01"
END = None                  # None -> today
FREQUENCY = "W-FRI"         # weekly, Friday-stamped: LSE and Xetra close hours
                            # before NYSE, so daily returns on a mixed-venue
                            # universe are misaligned by construction.
BASE_CURRENCY = "USD"       # everything converted before regression
FX_SYMBOL = "EURUSD=X"      # yfinance line used for EUR-quoted tickers

# --------------------------------------------------------------------------- #
# Ken French factor sets, keyed by the region name used in UNIVERSE below.
# Values are the library's dataset names. Adding a region is one entry here.
#
# Note: emerging exists only at monthly frequency - French publishes no daily
# file for it. Everything else here is daily and gets compounded to FREQUENCY.
# --------------------------------------------------------------------------- #
FACTOR_SETS = {
    "us": {
        "five_factor": "F-F_Research_Data_5_Factors_2x3_daily",
        "momentum": "F-F_Momentum_Factor_daily",
    },
    "developed": {
        "five_factor": "Developed_5_Factors_Daily",
        "momentum": "Developed_Mom_Factor_Daily",
    },
    "developed_ex_us": {
        "five_factor": "Developed_ex_US_5_Factors_Daily",
        "momentum": "Developed_ex_US_Mom_Factor_Daily",
    },
    "europe": {
        "five_factor": "Europe_5_Factors_Daily",
        "momentum": "Europe_Mom_Factor_Daily",
    },
    "emerging": {
        "five_factor": "Emerging_5_Factors",
        "momentum": "Emerging_MOM_Factor",
    },
}

# --------------------------------------------------------------------------- #
# Universe.
#   region  picks the factor set
#   slot    the role the fund plays in the portfolio
#   proxy   weighted basket of long-history US lines used to extend a short
#           UCITS history backwards; always flagged in the loadings table
# --------------------------------------------------------------------------- #
UNIVERSE = [
    {"symbol": "SWRD.L",  "currency": "USD", "region": "developed",       "slot": "core_developed",     "proxy": {"URTH": 1.0},
     "name": "SPDR MSCI World UCITS"},
    {"symbol": "VWCE.DE", "currency": "EUR", "region": "developed",       "slot": "core_global",
     "name": "Vanguard FTSE All-World UCITS",
     "note": "ACWI exposure mapped to Developed factors - French has no ACWI set"},
    {"symbol": "IEVL.L",  "currency": "USD", "region": "europe",          "slot": "value_europe",
     "name": "iShares Edge MSCI Europe Value Factor"},
    {"symbol": "IWVL.L",  "currency": "USD", "region": "developed",       "slot": "value_developed",
     "name": "iShares Edge MSCI World Value Factor"},
    {"symbol": "AVWC.L",  "currency": "USD", "region": "developed",       "slot": "core_global",
     "name": "Avantis Global Equity UCITS",
     "note": "inception 2024 - short window, wide standard errors"},
    {"symbol": "AVWS.L",  "currency": "USD", "region": "developed",       "slot": "smallvalue_global", "proxy": {"AVUV": 0.6, "AVDV": 0.4},
     "name": "Avantis Global Small Cap Value UCITS"},
    {"symbol": "AVUV",    "currency": "USD", "region": "us",              "slot": "smallvalue_us",
     "name": "Avantis US Small Cap Value"},
    {"symbol": "AVDV",    "currency": "USD", "region": "developed_ex_us", "slot": "smallvalue_intl",
     "name": "Avantis International Small Cap Value"},
    {"symbol": "ZPRV.DE", "currency": "EUR", "region": "us",              "slot": "smallvalue_us",
     "name": "SPDR MSCI USA Small Cap Value Weighted"},
    {"symbol": "ZPRX.DE", "currency": "EUR", "region": "europe",          "slot": "smallvalue_europe",
     "name": "SPDR MSCI Europe Small Cap Value Weighted"},
    {"symbol": "VWO",     "currency": "USD", "region": "emerging",        "slot": "core_em",
     "name": "Vanguard FTSE Emerging Markets"},
    {"symbol": "EIMI.L",  "currency": "USD", "region": "emerging",        "slot": "core_em",
     "name": "iShares Core MSCI EM IMI UCITS"},
    {"symbol": "AVEM.L",  "currency": "USD", "region": "emerging",        "slot": "core_em",           "proxy": {"AVEM": 1.0},
     "name": "Avantis Emerging Markets Equity UCITS"},
    {"symbol": "AVES",    "currency": "USD", "region": "emerging",        "slot": "value_em",
     "name": "Avantis Emerging Markets Value"},
]

# --------------------------------------------------------------------------- #
# Return model. The headline model is market + value + profitability; the other
# factors are estimated and reported, but are not part of the model being
# evaluated.
# --------------------------------------------------------------------------- #
MODEL_FACTORS = ["Mkt-RF", "HML", "RMW"]
REPORT_FACTORS = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "WML"]
HAC_LAGS = 6                # Newey-West lags, in units of FREQUENCY
MIN_OBS = 52                # skip a line with fewer usable observations

# --------------------------------------------------------------------------- #
# Portfolio construction. b = Sigma^-1 mu, traced from the sample estimate to a
# structured target.
# --------------------------------------------------------------------------- #
LONG_ONLY = True
SHRINKAGE_GRID = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
COVARIANCE_TARGET = "constant_correlation"   # or "diagonal", "identity"
MEAN_TARGET = "grand_mean"

# Illustrative starting weights, NOT real holdings.
REFERENCE_WEIGHTS = {
    "SWRD.L": 0.50,
    "AVUV": 0.15,
    "AVDV": 0.10,
    "IEVL.L": 0.10,
    "VWO": 0.15,
}


# --------------------------------------------------------------------------- #
def regions():
    """Factor sets the universe actually needs, in FACTOR_SETS order."""
    wanted = {t["region"] for t in UNIVERSE}
    return [r for r in FACTOR_SETS if r in wanted]


def symbols():
    return [t["symbol"] for t in UNIVERSE]


def ticker(symbol):
    """The UNIVERSE entry for one symbol."""
    return next(t for t in UNIVERSE if t["symbol"] == symbol)


# Private overrides, if present. Keep this last: it replaces names defined above.
try:
    from config_local import *  # noqa: F401,F403
except ImportError:
    pass
