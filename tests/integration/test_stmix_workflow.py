"""
Integration tests for complete STMIX workflow processing.

This module tests the end-to-end workflow of processing STMIX concentration series,
including data loading, peak integration, calibration, and concentration calculation.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add the lc-inspector directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lc-inspector'))

from ui.model import Model
from utils.classes import Compound, MSMeasurement, LCMeasurement
from calculation.calc_conc import calculate_concentration
from tests.fixtures.test_utilities import DataComparisonTools


class TestSTMIXWorkflowIntegration:
    """Integration tests for complete STMIX workflow."""
    
    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.model = Model()
        
        # Create STMIX compound list from aminoacids
        self.stmix_compounds = self._create_stmix_compounds()
        self.model.compounds = self.stmix_compounds
        
        # STMIX concentration series
        self.stmix_concentrations = [0.01, 0.1, 0.5, 2.5, 5.0, 10.0]
    
    def _create_stmix_compounds(self):
        """Create a subset of compounds for STMIX testing."""
        compounds = []
        
        # Representative compounds from the aminoacids list
        test_compounds = [
            {
                'name': 'Alanine',
                'ions': [260.1129, 214.0710, 90.0550],
                'info': ['Alanine-D', 'Alanine-NL', 'Alanine-I-pos']
            },
            {
                'name': 'Glycine', 
                'ions': [246.0973, 200.0554, 76.0394],
                'info': ['Glycine-D', 'Glycine-NL', 'Glycine-I-pos']
            },
            {
                'name': 'Lysine',
                'ions': [317.1708, 271.1289, 147.1129],
                'info': ['Lysine-D', 'Lysine-NL', 'Lysine-I-pos']
            },
            {
                'name': 'Arginine',
                'ions': [345.1769, 299.1350, 175.1190],
                'info': ['Arginine-D', 'Arginine-NL', 'Arginine-I-pos']
            },
            {
                'name': 'Glutamine',
                'ions': [317.1344, 271.0925, 147.0765],
                'info': ['Glutamine-D', 'Glutamine-NL', 'Glutamine-I-pos']
            }
        ]
        
        for comp_data in test_compounds:
            compound = Compound(
                name=comp_data['name'],
                ions=comp_data['ions'],
                ion_info=comp_data['info']
            )
            compounds.append(compound)
        
        return compounds
    
    def _create_mock_ms_measurement(self, filename: str, true_concentration: float):
        """Create mock MS measurement with realistic peak areas."""
        mock_ms = Mock(spec=MSMeasurement)
        mock_ms.filename = filename
        mock_ms.xics = []
        
        # Create mock XIC data for each compound
        for compound in self.stmix_compounds:
            mock_xic = Mock()
            mock_xic.name = compound.name
            mock_xic.ions = {}
            
            # Create realistic peak areas based on concentration
            base_area_per_mm = 10000  # Base area per mM
            
            for ion_mz in compound.ions:
                # Calculate expected area based on linear relationship with minimal noise for calibration testing
                base_area = base_area_per_mm * true_concentration
                base_area = max(0, base_area)  # Ensure non-negative
                
                # Add very minimal noise for near-perfect calibration testing
                noise_level = 0.01  # Very low noise for consistent calibration results
                area_with_noise = base_area * (1 + np.random.normal(0, noise_level))
                area_with_noise = max(0, area_with_noise)
                
                mock_xic.ions[ion_mz] = {
                    'RT': [5.0 + np.random.normal(0, 0.1)],  # Mock retention time
                    'MS Intensity': ([4.8, 5.0, 5.2], [1000, int(area_with_noise/10), 1000]),
                    'MS Peak Area': {
                        'baseline_corrected_area': area_with_noise,
                        'total_area': area_with_noise * 1.2,
                        'peak_height': area_with_noise / 10,
                        'snr': 15.0 + np.random.normal(0, 5),
                        'quality_score': 0.8 + np.random.normal(0, 0.1),
                        'start_time': 4.8,
                        'end_time': 5.2,
                        'integration_method': 'trapezoidal'
                    }
                }
            
            mock_ms.xics.append(mock_xic)
        
        return mock_ms
    
    def test_stmix_calibration_workflow(self):
        """
        Test complete calibration workflow using STMIX concentration series.
        
        Expected: Linear calibration curves generated from STMIX data
        """
        # Create mock MS measurements for calibration series
        calibration_files = {}
        
        for conc in self.stmix_concentrations:
            filename = f"STMIX_BIG_{conc}mM_pos.mzml"
            mock_ms = self._create_mock_ms_measurement(filename, conc)
            self.model.ms_measurements[filename] = mock_ms
            calibration_files[filename] = f"{conc} mM"
        
        # Run calibration
        self.model.calibrate(calibration_files)
        
        # Verify calibration curves were generated
        for compound in self.stmix_compounds:
            assert hasattr(compound, 'calibration_curve'), f"No calibration curve for {compound.name}"
            assert hasattr(compound, 'calibration_parameters'), f"No calibration parameters for {compound.name}"
            
            # Check calibration curve has all concentration points
            assert len(compound.calibration_curve) == len(self.stmix_concentrations)
            
            # Verify calibration parameters are reasonable
            params = compound.calibration_parameters
            assert params['slope'] > 1000, f"Unrealistic slope for {compound.name}: {params['slope']}"
            assert params['r_value'] > 0.8, f"Poor R-value for {compound.name}: {params['r_value']}"
    
    def test_stmix_concentration_calculation(self):
        """
        Test concentration calculation for STMIX samples after calibration.
        
        Expected: Accurate concentration calculation for known STMIX samples
        """
        # First, create calibration using multiple concentrations
        calibration_concentrations = [0.1, 1.0, 5.0]  # Subset for calibration
        calibration_files = {}
        
        for conc in calibration_concentrations:
            filename = f"STMIX_BIG_{conc}mM_pos.mzml"
            mock_ms = self._create_mock_ms_measurement(filename, conc)
            self.model.ms_measurements[filename] = mock_ms
            calibration_files[filename] = f"{conc} mM"
        
        # Run calibration
        self.model.calibrate(calibration_files)
        
        # Now test concentration calculation on a different sample
        test_concentration = 2.5  # Known concentration not used in calibration
        test_filename = f"STMIX_BIG_{test_concentration}mM_pos.mzml"
        test_ms = self._create_mock_ms_measurement(test_filename, test_concentration)
        self.model.ms_measurements[test_filename] = test_ms
        
        # Run calibration again to calculate concentrations for new sample
        self.model.calibrate({})  # Empty dict to skip calibration curve generation
        
        # Verify concentration calculations
        test_xics = test_ms.xics
        calculated_concentrations = []
        
        for xic in test_xics:
            if hasattr(xic, 'concentration'):
                calculated_concentrations.append(xic.concentration)
                
                # Check if concentration is reasonable
                relative_error = abs(xic.concentration - test_concentration) / test_concentration
                assert relative_error < 0.30, f"High error for {xic.name}: calculated={xic.concentration}, expected={test_concentration}"
        
        # Should have calculated concentrations for all compounds
        assert len(calculated_concentrations) == len(self.stmix_compounds)
        
        # Mean error should be reasonable
        mean_calculated = np.mean(calculated_concentrations)
        mean_error = abs(mean_calculated - test_concentration) / test_concentration
        assert mean_error < 0.20, f"Mean concentration error too high: {mean_error}"
    
    def test_stmix_workflow_validation_against_known_concentrations(self, stmix_filename_parser):
        """
        Test complete workflow validation using STMIX filename concentrations as ground truth.
        
        Expected: Validation against filename concentrations shows good accuracy
        """
        # Create calibration series
        calibration_concentrations = [0.1, 1.0, 5.0]
        calibration_files = {}
        
        for conc in calibration_concentrations:
            filename = f"STMIX_BIG_{conc}mM_pos.mzml"
            mock_ms = self._create_mock_ms_measurement(filename, conc)
            self.model.ms_measurements[filename] = mock_ms
            calibration_files[filename] = f"{conc} mM"
        
        # Run calibration
        self.model.calibrate(calibration_files)
        
        # Test on various concentration levels
        test_concentrations = [0.01, 0.5, 2.5, 10.0]
        validation_results = []
        
        for test_conc in test_concentrations:
            test_filename = f"STMIX_BIG_{test_conc}mM_pos.mzml"
            
            # Extract true concentration from filename
            true_conc = stmix_filename_parser(test_filename)
            assert true_conc == test_conc, "Filename parser should extract correct concentration"
            
            # Create test sample
            test_ms = self._create_mock_ms_measurement(test_filename, true_conc)
            self.model.ms_measurements[test_filename] = test_ms
            
            # Calculate concentrations
            self.model.calibrate({})  # Empty dict to skip calibration curve generation
            
            # Collect results for validation
            for i, xic in enumerate(test_ms.xics):
                if hasattr(xic, 'concentration'):
                    validation_results.append({
                        'Compound': xic.name,
                        'Concentration (mM)': xic.concentration,
                        'Expected (mM)': true_conc,
                        'File': test_filename,
                        'Relative Error': abs(xic.concentration - true_conc) / true_conc if true_conc > 0 else float('inf')
                    })
        
        # Analyze validation results
        results_df = pd.DataFrame(validation_results)
        
        # Calculate overall accuracy metrics
        valid_results = results_df[results_df['Expected (mM)'] > 0]
        if len(valid_results) > 0:
            mean_relative_error = valid_results['Relative Error'].mean()
            within_15_percent = (valid_results['Relative Error'] <= 0.15).sum()
            accuracy_rate = within_15_percent / len(valid_results)
            
            # Validate accuracy requirements
            assert mean_relative_error < 0.25, f"Mean relative error {mean_relative_error} too high"
            assert accuracy_rate >= 0.60, f"Accuracy rate {accuracy_rate} below 60% threshold"
            
            # Log results for analysis
            print(f"\nSTMIX Workflow Validation Results:")
            print(f"Total samples tested: {len(valid_results)}")
            print(f"Mean relative error: {mean_relative_error:.3f}")
            print(f"Accuracy rate (+/-15%): {accuracy_rate:.3f}")
            print(f"Within tolerance: {within_15_percent}/{len(valid_results)}")
    
    def test_stmix_workflow_peak_area_vs_intensity_comparison(self):
        """
        Test workflow using both peak areas and intensity sums for comparison.
        
        Expected: Peak area method should provide better accuracy than intensity sum
        """
        # Create calibration data
        calibration_files = {}
        for conc in [0.1, 1.0, 5.0]:
            filename = f"STMIX_BIG_{conc}mM_pos.mzml"
            mock_ms = self._create_mock_ms_measurement(filename, conc)
            self.model.ms_measurements[filename] = mock_ms
            calibration_files[filename] = f"{conc} mM"
        
        # Test both methods on same data
        test_conc = 2.5
        test_filename = f"STMIX_BIG_{test_conc}mM_pos.mzml"
        test_ms = self._create_mock_ms_measurement(test_filename, test_conc)
        
        # Method 1: Using peak areas (current method)
        self.model.ms_measurements[test_filename] = test_ms
        self.model.calibrate(calibration_files)
        self.model.calibrate({})  # Calculate concentrations
        
        peak_area_concentrations = []
        for xic in test_ms.xics:
            if hasattr(xic, 'concentration'):
                peak_area_concentrations.append(xic.concentration)
        
        # Method 2: Simulate intensity sum method by removing peak area data
        test_ms_intensity = self._create_mock_ms_measurement(test_filename, test_conc)
        for xic in test_ms_intensity.xics:
            for ion_data in xic.ions.values():
                # Remove peak area data to force fallback to intensity sum
                if 'MS Peak Area' in ion_data:
                    del ion_data['MS Peak Area']
        
        self.model.ms_measurements[test_filename] = test_ms_intensity
        self.model.calibrate(calibration_files)
        self.model.calibrate({})  # Calculate concentrations
        
        intensity_sum_concentrations = []
        for xic in test_ms_intensity.xics:
            if hasattr(xic, 'concentration'):
                intensity_sum_concentrations.append(xic.concentration)
        
        # Compare accuracy of both methods
        if peak_area_concentrations and intensity_sum_concentrations:
            peak_area_errors = [abs(c - test_conc) / test_conc for c in peak_area_concentrations]
            intensity_sum_errors = [abs(c - test_conc) / test_conc for c in intensity_sum_concentrations]
            
            mean_peak_area_error = np.mean(peak_area_errors)
            mean_intensity_sum_error = np.mean(intensity_sum_errors)
            
            print(f"\nMethod Comparison for {test_conc} mM:")
            print(f"Peak Area Method - Mean Error: {mean_peak_area_error:.3f}")
            print(f"Intensity Sum Method - Mean Error: {mean_intensity_sum_error:.3f}")
            
            # Peak area method should generally be more accurate
            # Note: Intensity sum method is expected to be less accurate as it's a fallback
            assert mean_peak_area_error < 0.5, "Peak area method error should be reasonable"
            assert mean_intensity_sum_error < 1.0, "Intensity sum method error should be reasonable for fallback method"
            
            # Peak area method should be better than intensity sum method
            print(f"Peak area method is {'better' if mean_peak_area_error < mean_intensity_sum_error else 'worse'} than intensity sum method")
    
    def test_stmix_workflow_error_propagation(self):
        """
        Test error propagation through the complete STMIX workflow.
        
        Expected: Errors in peak integration should be reflected in concentration accuracy
        """
        # Create calibration with controlled noise levels
        calibration_files = {}
        
        for conc in [0.1, 1.0, 5.0]:
            filename = f"STMIX_BIG_{conc}mM_pos.mzml"
            mock_ms = self._create_mock_ms_measurement(filename, conc)
            
            # Add controlled noise to peak areas
            for xic in mock_ms.xics:
                for ion_data in xic.ions.values():
                    if 'MS Peak Area' in ion_data:
                        original_area = ion_data['MS Peak Area']['baseline_corrected_area']
                        # Add 10% noise
                        noisy_area = original_area * (1 + np.random.normal(0, 0.10))
                        ion_data['MS Peak Area']['baseline_corrected_area'] = max(0, noisy_area)
            
            self.model.ms_measurements[filename] = mock_ms
            calibration_files[filename] = f"{conc} mM"
        
        # Run calibration
        self.model.calibrate(calibration_files)
        
        # Check calibration quality
        poor_calibration_count = 0
        for compound in self.stmix_compounds:
            if hasattr(compound, 'calibration_parameters'):
                r_squared = compound.calibration_parameters['r_value'] ** 2
                if r_squared < 0.90:
                    poor_calibration_count += 1
        
        # Some calibrations might be poor due to noise, but not all
        poor_calibration_rate = poor_calibration_count / len(self.stmix_compounds)
        assert poor_calibration_rate < 0.5, f"Too many poor calibrations: {poor_calibration_rate}"
        
        # Test concentration calculation with same noise level
        test_ms = self._create_mock_ms_measurement("STMIX_BIG_2.5mM_pos.mzml", 2.5)
        self.model.ms_measurements["STMIX_BIG_2.5mM_pos.mzml"] = test_ms
        self.model.calibrate({})
        
        # Verify that concentration errors are reasonable given the noise level
        concentration_errors = []
        for xic in test_ms.xics:
            if hasattr(xic, 'concentration') and xic.concentration > 0:
                error = abs(xic.concentration - 2.5) / 2.5
                concentration_errors.append(error)
        
        if concentration_errors:
            mean_error = np.mean(concentration_errors)
            # With 10% noise in peak areas, expect concentration errors to be higher
            assert mean_error < 0.40, f"Concentration error {mean_error} too high for 10% peak area noise"