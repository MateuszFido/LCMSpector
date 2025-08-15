"""
STMIX Calibration Curve Validation Test

This test creates calibration curves using 5 STMIX concentration levels
and validates interpolation accuracy on the 6th concentration level.
Tests both positive and negative ionization modes.
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock
import sys
import os
from pathlib import Path

# Add the lc-inspector directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lc-inspector'))

from ui.model import Model
from utils.classes import Compound, MSMeasurement
from calculation.calc_conc import calculate_concentration


class TestSTMIXCalibrationValidation:
    """
    STMIX Calibration Curve Validation Test Suite
    
    Tests calibration curve generation using 5 STMIX concentrations and
    validates interpolation accuracy on the 6th concentration.
    """
    
    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.model = Model()
        
        # Define STMIX concentration series (6 levels)
        self.stmix_concentrations = [0.01, 0.1, 0.5, 2.5, 5.0, 10.0]  # mM
        
        # Use first 5 for calibration, last one for validation
        self.calibration_concentrations = self.stmix_concentrations[:5]
        self.validation_concentration = self.stmix_concentrations[5]  # 10.0 mM
        
        # Create test compounds from aminoacids config section
        self.test_compounds = [
            Compound(name="Alanine", ions=[90.0549, 116.0706], ion_info=["Alanine-D", "Alanine-I"]),
            Compound(name="Glycine", ions=[76.0393, 102.0549], ion_info=["Glycine-D", "Glycine-I"]),
            Compound(name="Lysine", ions=[147.1128, 173.1285], ion_info=["Lysine-D", "Lysine-I"]),
            Compound(name="Arginine", ions=[175.1190, 201.1346], ion_info=["Arginine-D", "Arginine-I"]),
            Compound(name="Glutamine", ions=[147.0764, 173.0921], ion_info=["Glutamine-D", "Glutamine-I"])
        ]
        self.model.compounds = self.test_compounds
        
        print(f"\nSTMIX Calibration Validation Setup:")
        print(f"Calibration concentrations: {self.calibration_concentrations} mM")
        print(f"Validation concentration: {self.validation_concentration} mM")
        print(f"Test compounds: {[c.name for c in self.test_compounds]}")
    
    def _create_mock_stmix_measurement(self, concentration, mode="pos"):
        """
        Create a mock MS measurement for STMIX data at given concentration.
        
        Args:
            concentration (float): STMIX concentration in mM
            mode (str): Ionization mode ("pos" or "neg")
        
        Returns:
            Mock MSMeasurement with realistic peak area data
        """
        filename = f"STMIX_BIG_{concentration}mM_{mode}.mzml"
        
        mock_ms = Mock(spec=MSMeasurement)
        mock_ms.filename = filename
        mock_ms.xics = []
        
        # Create XIC data for each compound
        for compound in self.test_compounds:
            mock_xic = Mock()
            mock_xic.name = compound.name
            mock_xic.ions = {}
            
            # Create ion data for each m/z in the compound
            for i, ion_mz in enumerate(compound.ions):
                # Simulate concentration-dependent peak areas with realistic noise
                base_signal = 10000.0  # Base signal at 1 mM
                concentration_factor = concentration  # Linear response
                noise_factor = 1.0 + np.random.normal(0, 0.05)  # ±5% noise
                
                # Mode-dependent signal intensity (pos mode typically stronger)
                mode_factor = 1.0 if mode == "pos" else 0.7
                
                # Ion-specific factors (simulate different ionization efficiencies)
                ion_factors = [1.2, 0.8, 1.5, 0.9, 1.1]  # Different per compound
                ion_factor = ion_factors[self.test_compounds.index(compound)]
                
                baseline_corrected_area = (
                    base_signal * concentration_factor * noise_factor * 
                    mode_factor * ion_factor
                )
                
                mock_xic.ions[ion_mz] = {
                    'RT': [5.0 + i * 0.1],  # Slightly different RTs
                    'MS Intensity': (
                        [4.5, 5.0, 5.5], 
                        [1000, int(baseline_corrected_area * 0.8), 1000]
                    ),
                    'MS Peak Area': {
                        'baseline_corrected_area': baseline_corrected_area,
                        'total_area': baseline_corrected_area * 1.2,
                        'peak_height': baseline_corrected_area * 0.8,
                        'snr': 25.0 + np.random.normal(0, 5),
                        'quality_score': 0.85 + np.random.normal(0, 0.1),
                        'integration_method': 'gaussian_fit'
                    }
                }
            
            mock_ms.xics.append(mock_xic)
        
        return mock_ms
    
    @pytest.mark.stmix
    def test_stmix_calibration_curve_positive_mode(self):
        """
        Test STMIX calibration curve generation and validation in positive mode.
        
        Expected: Accurate concentration interpolation within ±15% relative error
        """
        print(f"\n{'='*60}")
        print(f"STMIX CALIBRATION VALIDATION - POSITIVE MODE")
        print(f"{'='*60}")
        
        # Create calibration data (5 concentrations)
        calibration_files = {}
        for conc in self.calibration_concentrations:
            mock_ms = self._create_mock_stmix_measurement(conc, mode="pos")
            filename = mock_ms.filename
            self.model.ms_measurements[filename] = mock_ms
            calibration_files[filename] = f"{conc} mM"
        
        print(f"\nCalibration files created: {list(calibration_files.keys())}")
        
        # Run calibration
        self.model.calibrate(calibration_files)
        
        # Verify calibration parameters were generated
        calibration_results = []
        for compound in self.test_compounds:
            if hasattr(compound, 'calibration_parameters'):
                params = compound.calibration_parameters
                calibration_results.append({
                    'Compound': compound.name,
                    'Slope': params['slope'],
                    'Intercept': params['intercept'],
                    'R-squared': params['r_value'] ** 2,
                    'P-value': params['p_value']
                })
                
                print(f"\n{compound.name} Calibration:")
                print(f"  Slope: {params['slope']:.1f}")
                print(f"  Intercept: {params['intercept']:.1f}")
                print(f"  R²: {params['r_value']**2:.4f}")
        
        # Create validation sample (6th concentration)
        validation_ms = self._create_mock_stmix_measurement(self.validation_concentration, mode="pos")
        validation_filename = validation_ms.filename
        self.model.ms_measurements[validation_filename] = validation_ms
        
        # Calculate concentrations for validation sample
        self.model.calibrate({})  # Empty dict to skip calibration, just calculate concentrations
        
        # Collect validation results
        validation_results = []
        total_compounds = 0
        accurate_predictions = 0
        
        print(f"\n{'='*60}")
        print(f"INTERPOLATION VALIDATION RESULTS")
        print(f"{'='*60}")
        print(f"True concentration: {self.validation_concentration} mM")
        print(f"{'Compound':<15} {'Predicted':<12} {'Error %':<10} {'Status'}")
        print(f"{'-'*50}")
        
        for i, (xic, compound) in enumerate(zip(validation_ms.xics, self.test_compounds)):
            if hasattr(xic, 'concentration') and hasattr(compound, 'calibration_parameters'):
                predicted_conc = xic.concentration
                relative_error = abs(predicted_conc - self.validation_concentration) / self.validation_concentration
                
                validation_results.append({
                    'Compound': compound.name,
                    'True_Concentration_mM': self.validation_concentration,
                    'Predicted_Concentration_mM': predicted_conc,
                    'Absolute_Error_mM': abs(predicted_conc - self.validation_concentration),
                    'Relative_Error_Percent': relative_error * 100,
                    'Within_15_Percent': relative_error <= 0.15,
                    'Mode': 'positive'
                })
                
                status = " PASS" if relative_error <= 0.15 else " FAIL"
                print(f"{compound.name:<15} {predicted_conc:<12.3f} {relative_error*100:<10.1f} {status}")
                
                total_compounds += 1
                if relative_error <= 0.15:
                    accurate_predictions += 1
        
        # Calculate overall accuracy
        if total_compounds > 0:
            accuracy_rate = accurate_predictions / total_compounds
            mean_relative_error = np.mean([r['Relative_Error_Percent'] for r in validation_results])
            
            print(f"\n{'='*60}")
            print(f"POSITIVE MODE SUMMARY")
            print(f"{'='*60}")
            print(f"Compounds tested: {total_compounds}")
            print(f"Accurate predictions (≤15%): {accurate_predictions}")
            print(f"Accuracy rate: {accuracy_rate:.1%}")
            print(f"Mean relative error: {mean_relative_error:.1f}%")
            
            # Validation assertions
            assert total_compounds >= 3, "Should have at least 3 compounds with calibration data"
            assert accuracy_rate >= 0.60, f"Accuracy rate {accuracy_rate:.1%} below 60% threshold"
            assert mean_relative_error <= 25.0, f"Mean relative error {mean_relative_error:.1f}% too high"
            
            return validation_results
        else:
            pytest.fail("No compounds with calibration data found")
    
    @pytest.mark.stmix
    def test_stmix_calibration_curve_negative_mode(self):
        """
        Test STMIX calibration curve generation and validation in negative mode.
        
        Expected: Accurate concentration interpolation within ±20% relative error (wider tolerance for negative mode)
        """
        print(f"\n{'='*60}")
        print(f"STMIX CALIBRATION VALIDATION - NEGATIVE MODE")
        print(f"{'='*60}")
        
        # Reset model for negative mode test
        self.model = Model()
        self.model.compounds = self.test_compounds
        
        # Create calibration data (5 concentrations)
        calibration_files = {}
        for conc in self.calibration_concentrations:
            mock_ms = self._create_mock_stmix_measurement(conc, mode="neg")
            filename = mock_ms.filename
            self.model.ms_measurements[filename] = mock_ms
            calibration_files[filename] = f"{conc} mM"
        
        print(f"\nCalibration files created: {list(calibration_files.keys())}")
        
        # Run calibration
        self.model.calibrate(calibration_files)
        
        # Verify calibration parameters were generated
        for compound in self.test_compounds:
            if hasattr(compound, 'calibration_parameters'):
                params = compound.calibration_parameters
                print(f"\n{compound.name} Calibration:")
                print(f"  Slope: {params['slope']:.1f}")
                print(f"  Intercept: {params['intercept']:.1f}")
                print(f"  R²: {params['r_value']**2:.4f}")
        
        # Create validation sample (6th concentration)
        validation_ms = self._create_mock_stmix_measurement(self.validation_concentration, mode="neg")
        validation_filename = validation_ms.filename
        self.model.ms_measurements[validation_filename] = validation_ms
        
        # Calculate concentrations for validation sample
        self.model.calibrate({})  # Empty dict to skip calibration, just calculate concentrations
        
        # Collect validation results
        validation_results = []
        total_compounds = 0
        accurate_predictions = 0
        
        print(f"\n{'='*60}")
        print(f"INTERPOLATION VALIDATION RESULTS")
        print(f"{'='*60}")
        print(f"True concentration: {self.validation_concentration} mM")
        print(f"{'Compound':<15} {'Predicted':<12} {'Error %':<10} {'Status'}")
        print(f"{'-'*50}")
        
        for i, (xic, compound) in enumerate(zip(validation_ms.xics, self.test_compounds)):
            if hasattr(xic, 'concentration') and hasattr(compound, 'calibration_parameters'):
                predicted_conc = xic.concentration
                relative_error = abs(predicted_conc - self.validation_concentration) / self.validation_concentration
                
                validation_results.append({
                    'Compound': compound.name,
                    'True_Concentration_mM': self.validation_concentration,
                    'Predicted_Concentration_mM': predicted_conc,
                    'Absolute_Error_mM': abs(predicted_conc - self.validation_concentration),
                    'Relative_Error_Percent': relative_error * 100,
                    'Within_20_Percent': relative_error <= 0.20,  # Wider tolerance for negative mode
                    'Mode': 'negative'
                })
                
                status = " PASS" if relative_error <= 0.20 else " FAIL"
                print(f"{compound.name:<15} {predicted_conc:<12.3f} {relative_error*100:<10.1f} {status}")
                
                total_compounds += 1
                if relative_error <= 0.20:
                    accurate_predictions += 1
        
        # Calculate overall accuracy
        if total_compounds > 0:
            accuracy_rate = accurate_predictions / total_compounds
            mean_relative_error = np.mean([r['Relative_Error_Percent'] for r in validation_results])
            
            print(f"\n{'='*60}")
            print(f"NEGATIVE MODE SUMMARY")
            print(f"{'='*60}")
            print(f"Compounds tested: {total_compounds}")
            print(f"Accurate predictions (≤20%): {accurate_predictions}")
            print(f"Accuracy rate: {accuracy_rate:.1%}")
            print(f"Mean relative error: {mean_relative_error:.1f}%")
            
            # Validation assertions (more lenient for negative mode)
            assert total_compounds >= 3, "Should have at least 3 compounds with calibration data"
            assert accuracy_rate >= 0.50, f"Accuracy rate {accuracy_rate:.1%} below 50% threshold"
            assert mean_relative_error <= 30.0, f"Mean relative error {mean_relative_error:.1f}% too high"
            
            return validation_results
        else:
            pytest.fail("No compounds with calibration data found")
    
    @pytest.mark.stmix
    def test_stmix_calibration_curve_comparison(self):
        """
        Compare positive and negative mode calibration performance.
        
        Expected: Positive mode generally more accurate than negative mode
        """
        print(f"\n{'='*60}")
        print(f"STMIX MODE COMPARISON TEST")
        print(f"{'='*60}")
        
        # Run both mode tests
        pos_results = self.test_stmix_calibration_curve_positive_mode()
        neg_results = self.test_stmix_calibration_curve_negative_mode()
        
        # Compare results
        if pos_results and neg_results:
            pos_errors = [r['Relative_Error_Percent'] for r in pos_results]
            neg_errors = [r['Relative_Error_Percent'] for r in neg_results]
            
            pos_mean_error = np.mean(pos_errors)
            neg_mean_error = np.mean(neg_errors)
            
            print(f"\n{'='*60}")
            print(f"MODE COMPARISON RESULTS")
            print(f"{'='*60}")
            print(f"Positive mode mean error: {pos_mean_error:.1f}%")
            print(f"Negative mode mean error: {neg_mean_error:.1f}%")
            print(f"Performance difference: {abs(pos_mean_error - neg_mean_error):.1f}%")
            
            # Generally expect positive mode to be more accurate (but not strictly required)
            if pos_mean_error < neg_mean_error:
                print(" Positive mode more accurate (expected)")
            else:
                print("⚠ Negative mode more accurate (unexpected but acceptable)")
            
            # Both modes should be reasonably accurate
            assert pos_mean_error <= 25.0, "Positive mode error too high"
            assert neg_mean_error <= 30.0, "Negative mode error too high"
            
            return {'positive': pos_results, 'negative': neg_results}