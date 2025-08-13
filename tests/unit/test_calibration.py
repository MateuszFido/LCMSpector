"""
Unit tests for calibration workflow functionality.

This module tests the calibration process in the Model class, including
curve generation, peak area usage, and concentration calculation integration.
"""

import pytest
import numpy as np
from scipy.stats import linregress
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add the lc-inspector directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lc-inspector'))

from ui.model import Model
from utils.classes import Compound, MSMeasurement
from calculation.calc_conc import calculate_concentration


class TestCalibrationWorkflow:
    """Test suite for calibration workflow in Model class."""
    
    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.model = Model()
        
        # Create mock compounds for testing
        self.test_compound = Compound(
            name="TestCompound",
            ions=[100.0, 200.0],
            ion_info=["Ion1", "Ion2"]
        )
        self.model.compounds = [self.test_compound]
        
        # Mock MS measurement data
        self.mock_ms_measurement = Mock(spec=MSMeasurement)
        self.mock_ms_measurement.filename = "test_file.mzml"
        self.mock_ms_measurement.xics = [Mock()]
        
        # Set up mock XIC data structure
        self.mock_xic = self.mock_ms_measurement.xics[0]
        self.mock_xic.name = "TestCompound"
        self.mock_xic.ions = {
            100.0: {
                'RT': [5.0],
                'MS Intensity': ([4.5, 5.0, 5.5], [1000, 5000, 1000]),
                'MS Peak Area': {
                    'baseline_corrected_area': 10000.0,
                    'total_area': 12000.0,
                    'peak_height': 5000.0,
                    'snr': 25.0,
                    'quality_score': 0.85
                }
            },
            200.0: {
                'RT': [5.1],
                'MS Intensity': ([4.6, 5.1, 5.6], [800, 4000, 800]),
                'MS Peak Area': {
                    'baseline_corrected_area': 8000.0,
                    'total_area': 9600.0,
                    'peak_height': 4000.0,
                    'snr': 20.0,
                    'quality_score': 0.80
                }
            }
        }
        
        self.model.ms_measurements = {"test_file.mzml": self.mock_ms_measurement}
    
    def test_calibration_with_peak_areas(self):
        """
        Test calibration workflow using peak areas instead of intensity sums.
        
        Expected: Calibration uses baseline-corrected peak areas when available
        """
        # Define calibration points
        selected_files = {
            "test_file.mzml": "1.0 mM"
        }
        
        # Run calibration
        self.model.calibrate(selected_files)
        
        # Verify calibration curve was created
        assert hasattr(self.test_compound, 'calibration_curve')
        assert 1.0 in self.test_compound.calibration_curve
        
        # Expected signal: sum of baseline-corrected areas (10000 + 8000 = 18000)
        expected_signal = 18000.0
        actual_signal = self.test_compound.calibration_curve[1.0]
        
        assert actual_signal == expected_signal, f"Expected signal {expected_signal}, got {actual_signal}"
    
    def test_calibration_fallback_to_intensity_sums(self):
        """
        Test calibration fallback to intensity sums when peak areas unavailable.
        
        Expected: Uses intensity sum method when peak area data is missing
        """
        # Remove peak area data to force fallback
        for ion_data in self.mock_xic.ions.values():
            del ion_data['MS Peak Area']
        
        selected_files = {
            "test_file.mzml": "1.0 mM"
        }
        
        # Run calibration
        self.model.calibrate(selected_files)
        
        # Verify calibration used intensity sums
        # Expected: sum of ALL intensity arrays (Ion 100.0: 7000 + Ion 200.0: 5600 = 12600)
        expected_signal = 12600.0  # Sum of all intensity values (correct behavior)
        actual_signal = self.test_compound.calibration_curve[1.0]
        
        assert actual_signal == expected_signal, f"Expected signal {expected_signal}, got {actual_signal}"
    
    def test_calibration_curve_generation(self):
        """
        Test generation of linear calibration curve from multiple points.
        
        Expected: Linear regression parameters calculated correctly
        """
        # Create multiple calibration points
        concentrations = [0.5, 1.0, 2.0, 5.0]
        base_area = 10000.0
        slope = 8000.0  # Areas increase linearly with concentration
        
        for i, conc in enumerate(concentrations):
            # Scale peak areas proportionally
            scale_factor = conc / 1.0  # Relative to 1.0 mM baseline
            
            # Create separate XIC object for each concentration to avoid overwriting
            mock_xic = Mock()
            mock_xic.name = "TestCompound"
            mock_xic.ions = {
                100.0: {
                    'RT': [5.0],
                    'MS Intensity': ([4.5, 5.0, 5.5], [1000, 5000, 1000]),
                    'MS Peak Area': {
                        'baseline_corrected_area': base_area * scale_factor,
                        'total_area': base_area * scale_factor * 1.2,
                        'peak_height': 5000.0,
                        'snr': 25.0,
                        'quality_score': 0.85
                    }
                },
                200.0: {
                    'RT': [5.1],
                    'MS Intensity': ([4.6, 5.1, 5.6], [800, 4000, 800]),
                    'MS Peak Area': {
                        'baseline_corrected_area': base_area * scale_factor,
                        'total_area': base_area * scale_factor * 1.2,
                        'peak_height': 4000.0,
                        'snr': 20.0,
                        'quality_score': 0.80
                    }
                }
            }
            
            # Create mock MS measurement for each concentration
            mock_ms = Mock(spec=MSMeasurement)
            mock_ms.filename = f"test_{conc}mM.mzml"
            mock_ms.xics = [mock_xic]
            self.model.ms_measurements[f"test_{conc}mM.mzml"] = mock_ms
        
        # Set up selected files for calibration
        selected_files = {f"test_{conc}mM.mzml": f"{conc} mM" for conc in concentrations}
        
        # Run calibration
        self.model.calibrate(selected_files)
        
        # Verify calibration parameters
        assert hasattr(self.test_compound, 'calibration_parameters')
        params = self.test_compound.calibration_parameters
        
        # Check that slope is reasonable (should be 20000 for 2 ions * 10000 each)
        expected_slope = 20000.0  # 2 ions * 10000 area per mM
        assert abs(params['slope'] - expected_slope) < 1000, f"Slope {params['slope']} differs from expected {expected_slope}"
        
        # Check R-squared is high (perfect linear relationship)
        assert params['r_value'] ** 2 > 0.99, f"R-squared {params['r_value']**2} too low for linear data"
    
    def test_concentration_calculation_after_calibration(self):
        """
        Test concentration calculation for samples after calibration.
        
        Expected: Concentrations calculated using peak areas and calibration parameters
        """
        # Set up calibration with known parameters
        self.test_compound.calibration_parameters = {
            'slope': 10000.0,
            'intercept': 1000.0,
            'r_value': 0.99,
            'p_value': 0.001,
            'std_err': 100.0
        }
        
        # Create sample with known peak area
        sample_area = 21000.0  # Should give (21000-1000)/10000 = 2.0 mM
        for ion_mz in [100.0, 200.0]:
            self.mock_xic.ions[ion_mz]['MS Peak Area']['baseline_corrected_area'] = sample_area / 2
        
        # Run calibration to trigger concentration calculation
        selected_files = {}  # Empty to skip calibration curve generation
        self.model.calibrate(selected_files)
        
        # Verify concentration was calculated
        calculated_conc = self.mock_xic.concentration
        expected_conc = 2.0
        
        assert abs(calculated_conc - expected_conc) < 0.001, f"Expected {expected_conc}, got {calculated_conc}"
    
    def test_concentration_unit_conversion(self):
        """
        Test proper handling of concentration unit conversions.
        
        Expected: Different units (m, mm, um, etc.) converted correctly
        """
        test_cases = [
            ("1.0 mM", 1.0),    # Base unit
            ("1.0 m", 1000.0),  # Molar to millimolar
            ("1000 um", 1.0),   # Micromolar to millimolar
            ("2.5", 2.5),       # No unit (assumed mM)
        ]
        
        for unit_string, expected_conc in test_cases:
            # Reset calibration curve
            self.test_compound.calibration_curve = {}
            
            selected_files = {"test_file.mzml": unit_string}
            self.model.calibrate(selected_files)
            
            # Check that concentration was converted correctly
            assert expected_conc in self.test_compound.calibration_curve, \
                f"Concentration {expected_conc} not found for input '{unit_string}'"
    
    def test_calibration_error_handling(self):
        """
        Test error handling in calibration workflow.
        
        Expected: Graceful handling of missing data and invalid inputs
        """
        # Test with missing XIC data
        self.mock_ms_measurement.xics = None
        
        selected_files = {"test_file.mzml": "1.0 mM"}
        
        # Should not raise exception, but log error
        self.model.calibrate(selected_files)
        
        # Test with empty concentration string
        selected_files = {"test_file.mzml": ""}
        
        # Should skip this file without error
        self.model.calibrate(selected_files)
        
        # Verify no calibration data was added
        assert not hasattr(self.test_compound, 'calibration_curve') or \
               len(self.test_compound.calibration_curve) == 0
    
    def test_calibration_with_missing_ions(self):
        """
        Test calibration behavior when compound has no ions defined.
        
        Expected: Error logged, calibration skipped for compound
        """
        # Create compound with no ions
        empty_compound = Compound(name="EmptyCompound", ions=[], ion_info=[])
        self.model.compounds = [empty_compound]
        
        selected_files = {"test_file.mzml": "1.0 mM"}
        
        # Should not raise exception
        self.model.calibrate(selected_files)
        
        # Verify no calibration curve was created
        assert not hasattr(empty_compound, 'calibration_curve') or \
               len(getattr(empty_compound, 'calibration_curve', {})) == 0


class TestCalibrationValidation:
    """Test calibration validation against expected behavior."""
    
    def test_linear_calibration_accuracy(self):
        """
        Test accuracy of linear calibration with synthetic data.
        
        Expected: Perfect recovery of known calibration parameters
        """
        # Generate synthetic calibration data
        true_slope = 15000.0
        true_intercept = 2000.0
        concentrations = [0.1, 0.5, 1.0, 2.0, 5.0]
        
        # Calculate expected areas
        expected_areas = [true_slope * c + true_intercept for c in concentrations]
        
        # Test calculate_concentration function directly
        calculated_concentrations = []
        curve_params = {'slope': true_slope, 'intercept': true_intercept}
        
        for area in expected_areas:
            calc_conc = calculate_concentration(area, curve_params)
            calculated_concentrations.append(calc_conc)
        
        # Verify perfect recovery
        for original, calculated in zip(concentrations, calculated_concentrations):
            assert abs(calculated - original) < 1e-10, \
                f"Concentration mismatch: {original} vs {calculated}"
    
    def test_calibration_curve_quality_metrics(self):
        """
        Test quality metrics for calibration curves.
        
        Expected: High R-squared for good calibration data
        """
        from tests.fixtures.test_utilities import ConcentrationTestValidator
        
        # Perfect linear data
        x_data = [0.1, 0.5, 1.0, 2.0, 5.0]
        y_data = [1000, 5000, 10000, 20000, 50000]  # Perfect linear
        
        validator = ConcentrationTestValidator()
        result = validator.validate_calibration_curve(x_data, y_data, min_r2=0.95)
        
        assert result['is_valid'], "Perfect linear data should pass validation"
        assert result['r_squared'] > 0.999, f"R-squared {result['r_squared']} too low for perfect data"
        assert abs(result['slope'] - 10000) < 1e-10, f"Slope {result['slope']} incorrect"
        assert abs(result['intercept']) < 1e-10, f"Intercept {result['intercept']} should be ~0"
        
        # Noisy data
        y_noisy = [1050, 4900, 10200, 19800, 50100]  # Small deviations
        
        result_noisy = validator.validate_calibration_curve(x_data, y_noisy, min_r2=0.95)
        
        assert result_noisy['is_valid'], "Slightly noisy data should still pass"
        assert result_noisy['r_squared'] > 0.95, "R-squared should meet minimum threshold"
    
    @pytest.mark.parametrize("slope,intercept,areas,expected_concentrations", [
        (10000.0, 1000.0, [11000, 21000, 51000], [1.0, 2.0, 5.0]),
        (5000.0, 500.0, [5500, 10500, 25500], [1.0, 2.0, 5.0]),
        (1000000.0, 0.0, [100000, 500000, 2000000], [0.1, 0.5, 2.0]),
    ])
    def test_parametrized_calibration_scenarios(self, slope, intercept, areas, expected_concentrations):
        """
        Test calibration with various slope/intercept combinations.
        
        Expected: Accurate concentration calculation across different scales
        """
        curve_params = {'slope': slope, 'intercept': intercept}
        
        for area, expected in zip(areas, expected_concentrations):
            calculated = calculate_concentration(area, curve_params)
            
            # Allow small floating point differences
            assert abs(calculated - expected) < 1e-10, \
                f"Area {area}: expected {expected}, got {calculated}"