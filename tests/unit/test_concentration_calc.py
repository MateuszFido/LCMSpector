import numpy as np
from calculation.calc_conc import calculate_concentration


# ----------------------------------------------------------------------
# Basic functionality
# ----------------------------------------------------------------------
def test_basic_positive_result():
    area = 150.0
    params = {"slope": 2.0, "intercept": 10.0}
    # (150‑10)/2 = 70.0 → rounded to 6 decimals
    assert calculate_concentration(area, params) == 70.0


def test_negative_concentration_returns_zero():
    area = 5.0
    params = {"slope": 2.0, "intercept": 10.0}
    # (5‑10)/2 = -2.5 → should be reported as 0
    assert calculate_concentration(area, params) == 0


def test_zero_slope_returns_zero():
    area = 100.0
    params = {"slope": 0.0, "intercept": 5.0}
    assert calculate_concentration(area, params) == 0


def test_nan_result_returns_zero():
    area = np.nan
    params = {"slope": 1.0, "intercept": 0.0}
    assert calculate_concentration(area, params) == 0


def test_infinite_result_returns_zero():
    area = 1e308
    params = {"slope": 1e-308, "intercept": 0.0}
    # (1e308 - 0) / 1e-308 = inf
    assert calculate_concentration(area, params) == 0


# ----------------------------------------------------------------------
# Edge‑case handling
# ----------------------------------------------------------------------
def test_negative_slope_valid_calculation():
    area = 20.0
    params = {"slope": -2.0, "intercept": 0.0}
    # (20‑0)/‑2 = -10 → negative → returns 0 per function logic
    assert calculate_concentration(area, params) == 0


def test_rounding_to_six_decimals():
    area = 10.123456789
    params = {"slope": 1.0, "intercept": 0.0}
    # Expected: 10.123457 after rounding
    assert calculate_concentration(area, params) == 10.123457
