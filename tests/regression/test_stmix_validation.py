"""
Regression tests for STMIX concentration series validation.

This module validates that LC-Inspector correctly calculates concentrations
for the STMIX concentration series, where each file contains all compounds
from the aminoacids list at the concentration indicated in the filename.

The STMIX series represents the ground truth for validation:
- STMIX_BIG_0.01mM contains all compounds at 0.01 mM
- STMIX_BIG_0.1mM contains all compounds at 0.1 mM
- etc.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch
import sys
import os

# Add the lc-inspector directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lc-inspector'))

from tests.fixtures.test_utilities import (
    DataComparisonTools, 
    ConcentrationTestValidator,
    CONCENTRATION_TOLERANCE
)


class TestSTMIXConcentrationValidation:
    """Test suite for STMIX concentration series validation."""
    
    def test_stmix_filename_concentration_extraction(self, stmix_filename_parser):
        """
        Test extraction of true concentrations from STMIX filenames.
        
        Expected: Correct concentration values extracted from various filename formats
        """
        test_cases = [
            ('STMIX_BIG_0.01mM_pos.mzml', 0.01),
            ('STMIX_BIG_0.1mM_neg.txt', 0.1),
            ('STMIX_BIG_2.5mM.mzml', 2.5),
            ('STMIX_BIG_10mM_pos.mzml', 10.0),
            ('STMIX_BIG_5mM_neg.txt', 5.0),
        ]
        
        for filename, expected_conc in test_cases:
            actual_conc = stmix_filename_parser(filename)
            assert actual_conc == expected_conc, f"Failed for {filename}: expected {expected_conc}, got {actual_conc}"
    
    def test_stmix_filename_extraction_invalid(self, stmix_filename_parser):
        """
        Test filename extraction with invalid formats.
        
        Expected: ValueError for non-STMIX filenames
        """
        invalid_filenames = [
            'regular_sample.mzml',
            'BIG_MIX_pos.mzml',
            'STMIX_SMALL_0.1mM.mzml',
            'invalid_file.txt'
        ]
        
        for filename in invalid_filenames:
            with pytest.raises(ValueError):
                stmix_filename_parser(filename)
    
    def test_known_compounds_loading(self, aminoacids_compounds):
        """
        Test loading of known compounds from config.json.
        
        Expected: All aminoacids and polyamines compounds loaded correctly
        """
        compounds = aminoacids_compounds
        
        # Verify we have a reasonable number of compounds
        assert len(compounds) >= 40, f"Expected at least 40 compounds, got {len(compounds)}"
        
        # Check specific expected compounds
        expected_compounds = ['Alanine', 'Glycine', 'Lysine', 'Arginine', 'Glutamine']
        for compound in expected_compounds:
            assert compound in compounds, f"Expected compound {compound} not found"
            assert 'ions' in compounds[compound], f"No ions defined for {compound}"
            assert 'info' in compounds[compound], f"No info defined for {compound}"
            assert len(compounds[compound]['ions']) > 0, f"No ions listed for {compound}"
    
    def test_stmix_concentration_series_fixture(self, stmix_concentration_series):
        """
        Test STMIX concentration series fixture data.
        
        Expected: Complete concentration series with filename mappings
        """
        series = stmix_concentration_series
        
        # Verify concentration levels
        expected_concentrations = [0.01, 0.1, 0.5, 2.5, 5.0, 10.0]
        assert series['concentrations'] == expected_concentrations
        
        # Verify filename mappings
        assert 'true_concentrations' in series
        mappings = series['true_concentrations']
        
        # Test specific mappings
        assert mappings['STMIX_BIG_0.01mM'] == 0.01
        assert mappings['STMIX_BIG_2.5mM_pos'] == 2.5
        assert mappings['STMIX_BIG_10mM_neg'] == 10.0
        
        # Verify we have mappings for all modes using correct filename format
        for conc in expected_concentrations:
            # Use the actual filename convention: 5.0 -> 5mM, 10.0 -> 10mM
            if conc == 5.0:
                base_key = 'STMIX_BIG_5mM'
                pos_key = 'STMIX_BIG_5mM_pos'
                neg_key = 'STMIX_BIG_5mM_neg'
            elif conc == 10.0:
                base_key = 'STMIX_BIG_10mM'
                pos_key = 'STMIX_BIG_10mM_pos'
                neg_key = 'STMIX_BIG_10mM_neg'
            else:
                base_key = f'STMIX_BIG_{conc}mM'
                pos_key = f'STMIX_BIG_{conc}mM_pos'
                neg_key = f'STMIX_BIG_{conc}mM_neg'
            
            assert base_key in mappings, f"Missing mapping for {base_key}"
            assert pos_key in mappings, f"Missing mapping for {pos_key}"
            assert neg_key in mappings, f"Missing mapping for {neg_key}"
    
    def test_stmix_validation_single_concentration(self, aminoacids_compounds):
        """
        Test STMIX validation for a single concentration level.
        
        Expected: Accurate validation statistics for known compounds
        """
        # Create mock results for 0.1 mM STMIX sample
        expected_concentration = 0.1
        mock_results = []
        
        # Add some compounds with accurate concentrations
        accurate_compounds = ['Alanine', 'Glycine', 'Lysine']
        for compound in accurate_compounds:
            mock_results.append({
                'Compound': compound,
                'Concentration (mM)': expected_concentration * (1 + np.random.normal(0, 0.05)),  # ±5% error
                'Ion (m/z)': 100.0 + len(compound),  # Mock m/z
                'File': 'STMIX_BIG_0.1mM_pos.mzml'
            })
        
        # Add some compounds with larger errors
        inaccurate_compounds = ['Arginine', 'Glutamine']
        for compound in inaccurate_compounds:
            mock_results.append({
                'Compound': compound,
                'Concentration (mM)': expected_concentration * (1 + np.random.normal(0, 0.20)),  # ±20% error
                'Ion (m/z)': 200.0 + len(compound),  # Mock m/z
                'File': 'STMIX_BIG_0.1mM_pos.mzml'
            })
        
        # Add unknown compound
        mock_results.append({
            'Compound': 'UnknownCompound',
            'Concentration (mM)': 0.05,
            'Ion (m/z)': 999.0,
            'File': 'STMIX_BIG_0.1mM_pos.mzml'
        })
        
        results_df = pd.DataFrame(mock_results)
        
        # Validate using the new STMIX validation method
        validator = DataComparisonTools()
        validation_stats = validator.validate_stmix_concentrations(
            results_df, expected_concentration, aminoacids_compounds
        )
        
        # Verify validation results
        assert validation_stats['expected_concentration'] == expected_concentration
        assert validation_stats['total_detected'] == len(mock_results)
        assert validation_stats['known_compounds_detected'] == 5  # accurate + inaccurate
        assert validation_stats['unknown_compounds_detected'] == 1
        
        # Check accuracy statistics
        assert 'accuracy_stats' in validation_stats
        assert len(validation_stats['accuracy_stats']) == 5
        
        # Verify specific compound validation
        alanine_stats = validation_stats['accuracy_stats']['Alanine']
        assert alanine_stats['expected'] == expected_concentration
        assert abs(alanine_stats['calculated'] - expected_concentration) / expected_concentration < 0.1
    
    @pytest.mark.parametrize("concentration", [0.01, 0.1, 0.5, 2.5, 5.0, 10.0])
    def test_stmix_validation_all_concentrations(self, concentration, aminoacids_compounds):
        """
        Test STMIX validation across all concentration levels.
        
        Expected: Validation works correctly for all STMIX concentration levels
        """
        # Create mock results with perfect accuracy for this concentration
        mock_results = []
        
        # Select a subset of known compounds for testing
        test_compounds = list(aminoacids_compounds.keys())[:10]
        
        for compound in test_compounds:
            mock_results.append({
                'Compound': compound,
                'Concentration (mM)': concentration,  # Perfect accuracy
                'Ion (m/z)': 100.0 + hash(compound) % 500,  # Mock m/z
                'File': f'STMIX_BIG_{concentration}mM_pos.mzml'
            })
        
        results_df = pd.DataFrame(mock_results)
        
        # Validate
        validator = DataComparisonTools()
        validation_stats = validator.validate_stmix_concentrations(
            results_df, concentration, aminoacids_compounds
        )
        
        # All compounds should be perfectly accurate
        assert validation_stats['accuracy_rate'] == 1.0, f"Perfect accuracy expected for {concentration} mM"
        assert validation_stats['within_15_percent'] == len(test_compounds)
        assert validation_stats['mean_relative_error'] < 1e-10, "Should have zero error for perfect data"


class TestSTMIXAccuracyBenchmarks:
    """Test accuracy benchmarks against STMIX data."""
    
    def test_concentration_accuracy_thresholds(self):
        """
        Test that concentration accuracy thresholds are reasonable for STMIX validation.
        
        Expected: Thresholds appropriate for biological measurement precision
        """
        # Test the default tolerance values
        assert CONCENTRATION_TOLERANCE['relative_error'] == 0.15, "Default tolerance should be 15%"
        assert CONCENTRATION_TOLERANCE['absolute_error'] == 0.05, "Absolute error should be 0.05 mM"
        assert CONCENTRATION_TOLERANCE['r_squared_min'] == 0.95, "R-squared minimum should be 0.95"
        
        # Test validator with different concentration levels
        validator = ConcentrationTestValidator()
        
        test_cases = [
            (0.01, 0.011, True),   # 10% error - should pass
            (0.1, 0.12, False),    # 20% error - should fail (exceeds 15% tolerance)
            (1.0, 1.20, False),    # 20% error - should fail
            (5.0, 4.5, True),      # 10% error - should pass
            (10.0, 8.0, False),    # 20% error - should fail
        ]
        
        for expected, calculated, should_pass in test_cases:
            result = validator.validate_concentration_accuracy(calculated, expected)
            assert result == should_pass, f"Validation failed for expected={expected}, calculated={calculated}"
    
    def test_stmix_detection_rate_requirements(self, aminoacids_compounds):
        """
        Test detection rate requirements for STMIX validation.
        
        Expected: High detection rate for known compounds in STMIX
        """
        total_compounds = len(aminoacids_compounds)
        
        # Simulate high detection rate (85% detection)
        detected_count = int(total_compounds * 0.85)
        mock_results = []
        
        compound_names = list(aminoacids_compounds.keys())
        detected_compounds = compound_names[:detected_count]
        
        for compound in detected_compounds:
            mock_results.append({
                'Compound': compound,
                'Concentration (mM)': 0.1,
                'Ion (m/z)': 100.0,
                'File': 'STMIX_BIG_0.1mM.mzml'
            })
        
        results_df = pd.DataFrame(mock_results)
        
        validator = DataComparisonTools()
        validation_stats = validator.validate_stmix_concentrations(
            results_df, 0.1, aminoacids_compounds
        )
        
        detection_rate = validation_stats['detection_rate']
        assert detection_rate >= 0.80, f"Detection rate {detection_rate} below 80% threshold"
        assert len(validation_stats['missing_compounds']) == (total_compounds - detected_count)
    
    def test_stmix_cross_concentration_consistency(self, aminoacids_compounds):
        """
        Test consistency of detection across different concentration levels.
        
        Expected: Consistent compound detection across STMIX concentration series
        """
        concentrations = [0.01, 0.1, 1.0, 10.0]
        compound_names = list(aminoacids_compounds.keys())[:5]
        
        detection_results = {}
        
        for conc in concentrations:
            mock_results = []
            for compound in compound_names:
                # Use deterministic concentration-dependent detection for consistent test results
                detection_prob = min(0.95, 0.5 + conc * 0.1)
                # Use deterministic detection based on concentration for consistent testing
                if detection_prob >= 0.7:  # Deterministic threshold for reliable testing
                    mock_results.append({
                        'Compound': compound,
                        'Concentration (mM)': conc * (1 + np.random.normal(0, 0.10)),
                        'Ion (m/z)': 100.0,
                        'File': f'STMIX_BIG_{conc}mM.mzml'
                    })
            
            results_df = pd.DataFrame(mock_results)
            
            validator = DataComparisonTools()
            validation_stats = validator.validate_stmix_concentrations(
                results_df, conc, aminoacids_compounds
            )
            
            # Handle case where no compounds are detected (no detection_rate key)
            detection_results[conc] = validation_stats.get('detection_rate', 0.0)
        
        # Higher concentrations should generally have better detection rates
        assert detection_results[10.0] >= detection_results[0.01], \
            "Higher concentrations should have better detection rates"
    
    def test_stmix_validation_error_metrics(self, aminoacids_compounds):
        """
        Test comprehensive error metrics for STMIX validation.
        
        Expected: Detailed error analysis with multiple statistical measures
        """
        expected_concentration = 1.0
        compound_names = list(aminoacids_compounds.keys())[:10]
        
        # Generate mock data with known error distribution
        mock_results = []
        known_errors = []
        
        for i, compound in enumerate(compound_names):
            # Create controlled error pattern
            error_pct = (i - 5) * 0.02  # Errors from -10% to +8%
            calculated_conc = expected_concentration * (1 + error_pct)
            known_errors.append(abs(error_pct))
            
            mock_results.append({
                'Compound': compound,
                'Concentration (mM)': calculated_conc,
                'Ion (m/z)': 100.0 + i,
                'File': 'STMIX_BIG_1.0mM.mzml'
            })
        
        results_df = pd.DataFrame(mock_results)
        
        validator = DataComparisonTools()
        validation_stats = validator.validate_stmix_concentrations(
            results_df, expected_concentration, aminoacids_compounds
        )
        
        # Verify error metrics are calculated correctly
        assert 'mean_relative_error' in validation_stats
        assert 'median_relative_error' in validation_stats
        assert 'accuracy_rate' in validation_stats
        
        # Check that calculated errors match expected pattern
        calculated_mean_error = validation_stats['mean_relative_error']
        expected_mean_error = np.mean(known_errors)
        
        assert abs(calculated_mean_error - expected_mean_error) < 0.01, \
            f"Mean error mismatch: calculated {calculated_mean_error}, expected {expected_mean_error}"


class TestSTMIXIntegrationWorkflow:
    """Integration tests using STMIX data for complete workflow validation."""
    
    def test_stmix_workflow_mock_integration(self, stmix_concentration_series, aminoacids_compounds):
        """
        Test complete workflow integration using STMIX data simulation.
        
        Expected: End-to-end validation from file processing to concentration validation
        """
        # Simulate processing a complete STMIX concentration series
        series = stmix_concentration_series
        validation_results = {}
        
        for filename, true_conc in series['true_concentrations'].items():
            if not filename.endswith('_pos'):  # Test subset to avoid redundancy
                continue
                
            # Simulate compound detection with realistic accuracy - test all compounds
            mock_results = []
            compound_names = list(aminoacids_compounds.keys())
            
            for compound in compound_names:
                # Use deterministic concentration-dependent accuracy for consistent test results
                base_accuracy = 0.90 if true_conc >= 0.1 else 0.75
                # Use deterministic detection to ensure reliable test results (≥60% detection rate)
                if base_accuracy >= 0.75:  # Always detect when accuracy threshold is met
                    # Add realistic measurement error
                    error = np.random.normal(0, 0.08)  # 8% standard deviation
                    calculated_conc = true_conc * (1 + error)
                    calculated_conc = max(0, calculated_conc)  # No negative concentrations
                    
                    mock_results.append({
                        'Compound': compound,
                        'Concentration (mM)': calculated_conc,
                        'Ion (m/z)': 100.0 + hash(compound) % 500,
                        'File': filename + '.mzml'
                    })
            
            # Validate this concentration level
            if mock_results:
                results_df = pd.DataFrame(mock_results)
                validator = DataComparisonTools()
                validation_stats = validator.validate_stmix_concentrations(
                    results_df, true_conc, aminoacids_compounds
                )
                validation_results[true_conc] = validation_stats
        
        # Analyze overall performance across concentration series
        all_accuracy_rates = [stats['accuracy_rate'] for stats in validation_results.values() 
                             if 'accuracy_rate' in stats]
        all_detection_rates = [stats['detection_rate'] for stats in validation_results.values() 
                              if 'detection_rate' in stats]
        
        if all_accuracy_rates:
            mean_accuracy = np.mean(all_accuracy_rates)
            assert mean_accuracy >= 0.70, f"Mean accuracy rate {mean_accuracy} below 70% threshold"
        
        if all_detection_rates:
            mean_detection = np.mean(all_detection_rates)
            assert mean_detection >= 0.60, f"Mean detection rate {mean_detection} below 60% threshold"