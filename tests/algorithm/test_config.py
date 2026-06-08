import os
import importlib
from unittest.mock import patch
import pytest

from src.algorithm import config

def test_config_negative_perfect_distance():
    with patch.dict(os.environ, {"MATCH_PERFECT_DISTANCE_KM": "-1.0"}):
        importlib.reload(config)
        assert config.PERFECT_DISTANCE_KM == 0.0

def test_config_max_less_than_perfect():
    with patch.dict(os.environ, {"MATCH_MAX_DISTANCE_KM": "1.0", "MATCH_PERFECT_DISTANCE_KM": "2.0"}):
        importlib.reload(config)
        assert config.MAX_DISTANCE_KM == 2.0
        assert config.PERFECT_DISTANCE_KM == 2.0

def test_config_weights_sum_to_zero():
    with patch.dict(os.environ, {"MATCH_WEIGHT_GEO": "0", "MATCH_WEIGHT_TIME": "0", "MATCH_WEIGHT_ADDRESS": "0"}):
        importlib.reload(config)
        assert config.WEIGHT_GEO == 0.40
        assert config.WEIGHT_TIME == 0.40
        assert config.WEIGHT_ADDRESS == 0.20

def test_config_weights_normalized():
    with patch.dict(os.environ, {"MATCH_WEIGHT_GEO": "2.0", "MATCH_WEIGHT_TIME": "2.0", "MATCH_WEIGHT_ADDRESS": "1.0"}):
        importlib.reload(config)
        assert config.WEIGHT_GEO == 0.40
        assert config.WEIGHT_TIME == 0.40
        assert config.WEIGHT_ADDRESS == 0.20
