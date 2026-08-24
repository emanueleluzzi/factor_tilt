"""Config loading: public config.yaml, optionally overridden by config.local.yaml.

Every script starts with `cfg = load_config()`. The local file is gitignored and
holds anything account-specific; it is merged recursively over the public one,
so it only needs to restate what differs.
"""

from __future__ import annotations

import copy
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "config.yaml"
LOCAL = ROOT / "config.local.yaml"


def _merge(base: dict, over: dict) -> dict:
    """Recursive dict merge; `over` wins on scalars and lists."""
    out = copy.deepcopy(base)
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(public: Path = PUBLIC, local: Path = LOCAL) -> dict:
    cfg = yaml.safe_load(public.read_text(encoding="utf-8"))
    if local.exists():
        cfg = _merge(cfg, yaml.safe_load(local.read_text(encoding="utf-8")) or {})
    return cfg


def path(cfg: dict, key: str) -> Path:
    """Resolve a config'd directory (e.g. 'factor_dir') against the repo root."""
    p = ROOT / cfg["data"][key]
    p.mkdir(parents=True, exist_ok=True)
    return p


def regions(cfg: dict) -> list[str]:
    """Factor sets actually needed by the universe, in config order."""
    wanted = {t["region"] for t in cfg["universe"]}
    return [r for r in cfg["factor_sets"] if r in wanted]
