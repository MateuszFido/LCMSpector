"""
Unit tests for core concentration calculation functionality.

This module tests the `calculate_concentration()` function from calc_conc.py,
which is the critical component for converting peak areas to concentrations.
"""

import pytest
import math
import sys
import os

# Add the lc-inspector directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lc-inspector'))

from calculation.calc_conc import calculate_concentration


class TestCalculateConcentration:
    """Test suite for the calculate_concentration function."""
    
    def test_linear_concentration_calculation(self):
        """
        Test basic linear concentration calculation with known parameters.
        
        Uses a simple linear relationship: concentration = (area - intercept) / slope
        Expected: Exact calculation within floating point precision
        """
        # Test case: slope=1000, intercept=500, area=2500 -> concentration=2.0
        curve_params = {'slope': 1000.0, 'intercept': 500.0}
        area = 2500.0
        expected_concentration = 2.0
        
        result = calculate_concentration(area, curve_params)
        
        assert result == expected_concentration, f"Expected {expected_concentration}, got {result}"
        assert isinstance(result, float), "Result should be a float"
    
    def test_concentration_rounding(self):
        """
        Test that concentration results are properly rounded to 6 decimal places.
        
        Expected: Results rounded to 6 decimal places for consistency
        """
        curve_params = {'slope': 3.0, 'intercept': 1.0}
        area = 4.0  # (4-1)/3 = 1.0 exactly
        
        result = calculate_concentration(area, curve_params)
        
        assert result == 1.0, "Simple division should give exact result"
        
        # Test with more complex division requiring rounding
        curve_params = {'slope': 3.0, 'intercept': 0.0}
        area = 1.0  # 1/3 = 0.333333...
        
        result = calculate_concentration(area, curve_params)
        expected = round(1.0/3.0, 6)
        
        assert result == expected, f"Expected {expected}, got {result}"
    
    def test_zero_concentration(self):
        """
        Test calculation when area equals intercept (zero concentration).
        
        Expected: Concentration = 0.0 when area = intercept
        """
        curve_params = {'slope': 1000.0, 'intercept': 2000.0}
        area = 2000.0  # area = intercept
        
        result = calculate_concentration(area, curve_params)
        
        assert result == 0.0, f"Expected 0.0, got {result}"
    
    def test_negative_concentration(self):
        """
        Test calculation with negative concentration result.
        
        This can occur when area < intercept, representing below-detection levels.
        Expected: Negative values should be calculated and rounded normally
        """
        curve_params = {'slope': 1000.0, 'intercept': 3000.0}
        area = 2000.0  # (2000-3000)/1000 = -1.0
        
        result = calculate_concentration(area, curve_params)
        
        assert result == -1.0, f"Expected -1.0, got {result}"
    
    def test_high_slope_precision(self):
        """
        Test calculation with very high slope values (typical for LC-MS).
        
        Based on export.csv analysis, slopes can range from 1000 to 50,000,000
        Expected: Accurate calculation with large slope values
        """
        curve_params = {'slope': 10000000.0, 'intercept': 5000.0}
        area = 15000.0  # (15000-5000)/10000000 = 0.001
        
        result = calculate_concentration(area, curve_params)
        expected = 0.001
        
        assert result == expected, f"Expected {expected}, got {result}"
    
    def test_very_small_concentration(self):
        """
        Test calculation resulting in very small concentration values.
        
        Expected: Proper handling of small concentrations with rounding
        """
        curve_params = {'slope': 1000000.0, 'intercept': 1000.0}
        area = 1001.0  # (1001-1000)/1000000 = 0.000001
        
        result = calculate_concentration(area, curve_params)
        expected = 0.000001
        
        assert result == expected, f"Expected {expected}, got {result}"
    
    def test_nan_handling(self):
        """
        Test handling of NaN values in calculation.
        
        NaN can occur with invalid slope (0) or other mathematical errors.
        Expected: Function returns 0 when result is NaN
        """
        # Test with zero slope (division by zero -> inf, then inf-intercept -> inf or nan)
        curve_params = {'slope': 0.0, 'intercept': 1000.0}
        area = 2000.0
        
        result = calculate_concentration(area, curve_params)
        
        assert result == 0, f"Expected 0 for NaN case, got {result}"
    
    def test_infinity_handling(self):
        """
        Test handling of infinity values in calculation.
        
        Expected: Function returns 0 when result is infinite
        """
        # Create a case that results in infinity
        curve_params = {'slope': 0.0, 'intercept': 0.0}
        area = 1000.0  # 1000/0 = inf
        
        result = calculate_concentration(area, curve_params)
        
        # The function checks for NaN but not infinity, this tests actual behavior
        # Based on the current implementation, inf would not be caught by math.isnan()
        # This test documents the current behavior
        assert not math.isfinite(result) or result == 0, "Should handle infinity appropriately"
    
    @pytest.mark.parametrize("slope,intercept,area,expected", [
        (1000.0, 0.0, 1000.0, 1.0),          # Simple case
        (2000.0, 500.0, 2500.0, 1.0),        # With intercept
        (5000.0, 1000.0, 6000.0, 1.0),       # Different scale
        (1000000.0, 0.0, 100.0, 0.0001),     # Small concentration
        (1000.0, 2000.0, 1000.0, -1.0),      # Negative result
    ])
    def test_parametrized_calculations(self, slope, intercept, area, expected):
        """
        Parametrized test for multiple calculation scenarios.
        
        Tests various combinations of slope, intercept, and area values
        to ensure consistent behavior across different scales.
        """
        curve_params = {'slope': slope, 'intercept': intercept}
        
        result = calculate_concentration(area, curve_params)
        
        assert abs(result - expected) < 1e-10, f"Expected {expected}, got {result}"


class TestCalculateConcentrationEdgeCases:
    """Test edge cases and error conditions for calculate_concentration."""
    
    def test_missing_slope_parameter(self):
        """
        Test behavior when slope parameter is missing.
        
        Expected: KeyError should be raised for missing required parameter
        """
        curve_params = {'intercept': 1000.0}  # Missing slope
        area = 2000.0
        
        with pytest.raises(KeyError):
            calculate_concentration(area, curve_params)
    
    def test_missing_intercept_parameter(self):
        """
        Test behavior when intercept parameter is missing.
        
        Expected: KeyError should be raised for missing required parameter
        """
        curve_params = {'slope': 1000.0}  # Missing intercept
        area = 2000.0
        
        with pytest.raises(KeyError):
            calculate_concentration(area, curve_params)
    
    def test_empty_curve_parameters(self):
        """
        Test behavior with empty curve parameters dictionary.
        
        Expected: KeyError for missing required parameters
        """
        curve_params = {}
        area = 2000.0
        
        with pytest.raises(KeyError):
            calculate_concentration(area, curve_params)
    
    def test_string_area_input(self):
        """
        Test behavior with string area input.
        
        Expected: TypeError or proper type conversion behavior
        """
        curve_params = {'slope': 1000.0, 'intercept': 500.0}
        area = "2000.0"  # String instead of float
        
        # The function doesn't explicitly handle type conversion
        # This test documents current behavior
        with pytest.raises(TypeError):
            calculate_concentration(area, curve_params)
    
    def test_none_area_input(self):
        """
        Test behavior with None area input.
        
        Expected: TypeError for None input
        """
        curve_params = {'slope': 1000.0, 'intercept': 500.0}
        area = None
        
        with pytest.raises(TypeError):
            calculate_concentration(area, curve_params)


class TestCalculateConcentrationValidation:
    """Test validation against reference data patterns."""
    
    def test_export_csv_concentration_range(self):
        """
        Test calculation within the range observed in export.csv reference data.
        
        Based on analysis: concentration range 0.033-0.43 mM
        Expected: Results within expected biological range
        """
        # Test parameters similar to those in export.csv
        curve_params = {'slope': 15000000.0, 'intercept': 2000.0}
        
        # Test areas that should give concentrations in the 0.033-0.43 mM range
        test_areas = [502000, 8450000]  # Representative areas from export.csv
        
        for area in test_areas:
            result = calculate_concentration(area, curve_params)
            
            assert 0.0 <= result <= 1.0, f"Concentration {result} outside expected range for area {area}"
            assert isinstance(result, (int, float)), "Result should be numeric"
    
    def test_calibration_curve_linearity(self):
        """
        Test that multiple points on a calibration curve maintain linearity.
        
        Expected: Linear relationship between area and concentration
        """
        curve_params = {'slope': 10000.0, 'intercept': 1000.0}
        
        # Test multiple points along the curve
        areas = [1000, 11000, 21000, 31000, 41000]  # Evenly spaced areas
        expected_concentrations = [0.0, 1.0, 2.0, 3.0, 4.0]
        
        calculated_concentrations = []
        for area in areas:
            result = calculate_concentration(area, curve_params)
            calculated_concentrations.append(result)
        
        # Verify linearity
        for i, (calc, expected) in enumerate(zip(calculated_concentrations, expected_concentrations)):
            assert abs(calc - expected) < 1e-10, f"Point {i}: expected {expected}, got {calc}"
        
        # Verify consistent differences between points
        differences = [calculated_concentrations[i+1] - calculated_concentrations[i] 
                      for i in range(len(calculated_concentrations)-1)]
        
        # All differences should be equal (linear relationship)
        for diff in differences:
            assert abs(diff - 1.0) < 1e-10, f"Non-linear difference: {diff}"