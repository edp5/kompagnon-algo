"""
Centralized configuration for the matching algorithm.

All parameters are read from environment variables with sensible defaults.
To override, set the corresponding env var in your .env file or system environment.
"""
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _env_float(key: str, default: float) -> float:
    """Read an env var as float, falling back to *default* on missing / invalid values."""
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning(f"Invalid value for {key}='{raw}', using default {default}")
        return default


def _env_int(key: str, default: int) -> int:
    """Read an env var as int, falling back to *default* on missing / invalid values."""
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning(f"Invalid value for {key}='{raw}', using default {default}")
        return default


# ---------------------------------------------------------------------------
# Geographic matching
# ---------------------------------------------------------------------------

# Maximum distance (km) — beyond this the geo score is 0 → no match possible.
MAX_DISTANCE_KM: float = _env_float("MATCH_MAX_DISTANCE_KM", 5.0)

# Distance (km) below which the geo score is 1.0 (perfect proximity).
PERFECT_DISTANCE_KM: float = _env_float("MATCH_PERFECT_DISTANCE_KM", 0.5)

# ---------------------------------------------------------------------------
# Temporal matching
# ---------------------------------------------------------------------------

# Maximum tolerated departure-time difference in minutes.
TIME_TOLERANCE_MINUTES: int = _env_int("MATCH_TIME_TOLERANCE_MINUTES", 30)

# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

# Minimum combined score (0.0–1.0) to accept a match.
MIN_MATCH_SCORE: float = _env_float("MATCH_MIN_SCORE", 0.5)

# Weights — must sum to 1.0.
WEIGHT_GEO: float = _env_float("MATCH_WEIGHT_GEO", 0.40)
WEIGHT_TIME: float = _env_float("MATCH_WEIGHT_TIME", 0.40)
WEIGHT_ADDRESS: float = _env_float("MATCH_WEIGHT_ADDRESS", 0.20)

# Validate distances
if PERFECT_DISTANCE_KM < 0:
    logger.warning(f"Invalid PERFECT_DISTANCE_KM ({PERFECT_DISTANCE_KM}), resetting to 0.0")
    PERFECT_DISTANCE_KM = 0.0

if MAX_DISTANCE_KM < PERFECT_DISTANCE_KM:
    logger.warning(f"MAX_DISTANCE_KM ({MAX_DISTANCE_KM}) < PERFECT_DISTANCE_KM ({PERFECT_DISTANCE_KM}), overriding MAX_DISTANCE_KM")
    MAX_DISTANCE_KM = PERFECT_DISTANCE_KM

# Validate & normalize weights
total_weight = WEIGHT_GEO + WEIGHT_TIME + WEIGHT_ADDRESS
if total_weight <= 0:
    logger.warning("Weights sum to <= 0. Resetting to defaults.")
    WEIGHT_GEO, WEIGHT_TIME, WEIGHT_ADDRESS = 0.40, 0.40, 0.20
else:
    WEIGHT_GEO /= total_weight
    WEIGHT_TIME /= total_weight
    WEIGHT_ADDRESS /= total_weight
