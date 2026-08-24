"""Portfolio weights along a shrinkage path -> outputs/  [not written yet]

Planned shape:
  - mu = alpha + B @ lambda from the estimated loadings
  - Sigma = B Omega B' + D, D the residual covariance
  - shrink both towards a structured target across config.SHRINKAGE_GRID
  - solve b = Sigma^-1 mu at each level, long-only, and report how the weights
    move along the path - the path is the object of interest, not the endpoint
  - optional Black-Litterman variant with REFERENCE_WEIGHTS as the prior
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import config


def main():
    raise NotImplementedError(f"stub - {len(config.SHRINKAGE_GRID)} shrinkage levels")


if __name__ == "__main__":
    main()
