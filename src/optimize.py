"""Portfolio construction from estimated loadings — stub.

Planned shape:
  - build expected returns from the factor model: mu = alpha + B @ lambda
  - build Sigma = B Omega B' + D (residual diagonal, or a fuller residual cov)
  - shrink both towards a structured target along `optimize.shrinkage_grid`
  - solve b = Sigma^-1 mu at each shrinkage level, long-only, and report how
    the weights move along the path (the interesting object is the path, not
    the endpoint)
  - optional Black-Litterman variant with the reference weights as the prior
"""

from __future__ import annotations

from config import load_config


def main() -> None:
    cfg = load_config()
    raise NotImplementedError(
        f"optimize.py is a stub; shrinkage grid has "
        f"{len(cfg['optimize']['shrinkage_grid'])} points."
    )


if __name__ == "__main__":
    main()
