"""
Test utilities and fixtures for LC-Inspector test suite.

This module provides common fixtures, validation utilities, and data loading
functions for testing concentration calculations and calibration workflows.
"""

import pytest
import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Union, Optional
import tempfile
import logging
from scipy import stats

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants based on architecture design
CONCENTRATION_TOLERANCE = {
    'relative_error': 0.15,      # +/-15% for biological measurements
    'absolute_error': 0.05,      # +/-0.05 mM for low concentrations
    'r_squared_min': 0.95,       # Calibration curve quality
    'slope_range': (1000, 50000000),  # Valid slope bounds
}

INTEGRATION_CRITERIA = {
    'snr_minimum': 3.0,          # Signal-to-noise ratio
    'quality_score_min': 0.2,    # Peak quality threshold
    'area_cv_max': 0.20,         # Coefficient of variation
    'retention_time_window': 0.1, # RT tolerance (minutes)
}

STATISTICAL_THRESHOLDS = {
    'calibration_r2': 0.95,      # Minimum R-squared
    'residual_max': 0.1,         # Maximum residual error
    'outlier_threshold': 2.0,    # Z-score for outlier detection
    'replicate_cv': 0.15,        # Replicate precision
}


class ConcentrationTestValidator:
    """Validation utilities for concentration calculations."""
    
    @staticmethod
    def validate_concentration_accuracy(calculated: float, expected: float, 
                                      tolerance: float = 0.15) -> bool:
        """
        Validate calculated concentration against expected value.
        
        Args:
            calculated: Calculated concentration value
            expected: Expected concentration value
            tolerance: Relative error tolerance (default 15%)
            
        Returns:
            bool: True if within tolerance
        """
        if expected == 0:
            return abs(calculated) <= CONCENTRATION_TOLERANCE['absolute_error']
        
        relative_error = abs((calculated - expected) / expected)
        return relative_error <= tolerance
    
    @staticmethod
    def validate_calibration_curve(x_data: List[float], y_data: List[float], 
                                 min_r2: float = 0.95) -> Dict[str, float]:
        """
        Validate calibration curve quality using linear regression.
        
        Args:
            x_data: Concentration values
            y_data: Area/intensity values
            min_r2: Minimum acceptable R-squared value
            
        Returns:
            dict: Regression statistics and validation result
        """
        from scipy.stats import linregress
        
        slope, intercept, r_value, p_value, std_err = linregress(x_data, y_data)
        r_squared = r_value ** 2
        
        return {
            'slope': slope,
            'intercept': intercept,
            'r_squared': r_squared,
            'p_value': p_value,
            'std_err': std_err,
            'is_valid': r_squared >= min_r2
        }
    
    @staticmethod
    def validate_peak_integration(peak_data: Dict, quality_criteria: Dict = None) -> bool:
        """
        Validate peak integration quality metrics.
        
        Args:
            peak_data: Peak integration results dictionary
            quality_criteria: Quality thresholds (uses defaults if None)
            
        Returns:
            bool: True if peak meets quality criteria
        """
        criteria = quality_criteria or INTEGRATION_CRITERIA
        
        snr = peak_data.get('snr', 0)
        quality_score = peak_data.get('quality_score', 0)
        
        return (snr >= criteria['snr_minimum'] and 
                quality_score >= criteria['quality_score_min'])
    
    @staticmethod
    def generate_test_report(results: List[Dict], output_path: str = None) -> Dict:
        """
        Generate comprehensive test validation report.
        
        Args:
            results: List of test result dictionaries
            output_path: Optional path to save report
            
        Returns:
            dict: Summary statistics and validation metrics
        """
        if not results:
            return {'error': 'No results provided'}
        
        df = pd.DataFrame(results)
        
        report = {
            'total_tests': len(results),
            'passed_tests': sum(1 for r in results if r.get('passed', False)),
            'failed_tests': sum(1 for r in results if not r.get('passed', False)),
            'pass_rate': sum(1 for r in results if r.get('passed', False)) / len(results),
            'summary_statistics': {}
        }
        
        # Add concentration accuracy statistics if available
        if 'concentration_error' in df.columns:
            report['summary_statistics']['concentration'] = {
                'mean_error': df['concentration_error'].mean(),
                'std_error': df['concentration_error'].std(),
                'max_error': df['concentration_error'].max(),
                'within_tolerance': (df['concentration_error'] <= 0.15).sum()
            }
        
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
        
        return report


class DataComparisonTools:
    """Tools for comparing test results with reference data."""
    
    @staticmethod
    def validate_stmix_concentrations(results: pd.DataFrame, 
                                    expected_concentration: float,
                                    known_compounds: Dict) -> Dict:
        """
        Validate STMIX concentration results against known filename concentration.
        
        Args:
            results: Test results DataFrame
            expected_concentration: Expected concentration from filename (e.g., 0.01 from STMIX_BIG_0.01mM)
            known_compounds: Dictionary of known compounds from config.json
            
        Returns:
            dict: Validation statistics
        """
        validation = {
            'expected_concentration': expected_concentration,
            'total_detected': 0,
            'known_compounds_detected': 0,
            'unknown_compounds_detected': 0,
            'accuracy_stats': {},
            'detected_compounds': [],
            'missing_compounds': [],
            'concentration_errors': []
        }
        
        # Get list of known compound names
        known_compound_names = set(known_compounds.keys())
        detected_compound_names = set()
        
        for _, result_row in results.iterrows():
            compound = result_row.get('Compound', '')
            calculated_conc = result_row.get('Concentration (mM)', 0)
            
            validation['total_detected'] += 1
            validation['detected_compounds'].append(compound)
            detected_compound_names.add(compound)
            
            # Check if compound is in known list
            if compound in known_compound_names:
                validation['known_compounds_detected'] += 1
                
                # Calculate concentration accuracy
                if expected_concentration > 0 and calculated_conc > 0:
                    relative_error = abs((calculated_conc - expected_concentration) / expected_concentration)
                    validation['accuracy_stats'][compound] = {
                        'calculated': calculated_conc,
                        'expected': expected_concentration,
                        'relative_error': relative_error,
                        'within_tolerance': relative_error <= 0.15
                    }
                    validation['concentration_errors'].append(relative_error)
            else:
                validation['unknown_compounds_detected'] += 1
        
        # Find missing compounds
        validation['missing_compounds'] = list(known_compound_names - detected_compound_names)
        
        # Calculate summary statistics
        if validation['concentration_errors']:
            errors = validation['concentration_errors']
            validation['mean_relative_error'] = np.mean(errors)
            validation['median_relative_error'] = np.median(errors)
            validation['within_15_percent'] = sum(1 for e in errors if e <= 0.15)
            validation['accuracy_rate'] = validation['within_15_percent'] / len(errors)
            validation['detection_rate'] = validation['known_compounds_detected'] / len(known_compound_names)
        
        return validation
    
    @staticmethod
    def statistical_comparison(data1: np.ndarray, data2: np.ndarray, 
                             test_type: str = 't-test') -> Dict:
        """
        Perform statistical comparison between two datasets.
        
        Args:
            data1: First dataset
            data2: Second dataset
            test_type: Type of statistical test ('t-test', 'ks-test')
            
        Returns:
            dict: Statistical test results
        """
        if test_type == 't-test':
            statistic, p_value = stats.ttest_ind(data1, data2)
            test_name = "Independent t-test"
        elif test_type == 'ks-test':
            statistic, p_value = stats.ks_2samp(data1, data2)
            test_name = "Kolmogorov-Smirnov test"
        else:
            raise ValueError(f"Unknown test type: {test_type}")
        
        return {
            'test_name': test_name,
            'statistic': statistic,
            'p_value': p_value,
            'significant': p_value < 0.05,
            'data1_mean': np.mean(data1),
            'data2_mean': np.mean(data2),
            'data1_std': np.std(data1),
            'data2_std': np.std(data2)
        }
    
    @staticmethod
    def generate_accuracy_metrics(calculated: np.ndarray, 
                                reference: np.ndarray) -> Dict:
        """
        Generate comprehensive accuracy metrics.
        
        Args:
            calculated: Calculated values
            reference: Reference values
            
        Returns:
            dict: Accuracy metrics
        """
        # Remove any NaN or zero reference values
        valid_mask = ~(np.isnan(calculated) | np.isnan(reference) | (reference == 0))
        calc_valid = calculated[valid_mask]
        ref_valid = reference[valid_mask]
        
        if len(calc_valid) == 0:
            return {'error': 'No valid data points for comparison'}
        
        # Calculate various error metrics
        absolute_errors = np.abs(calc_valid - ref_valid)
        relative_errors = np.abs((calc_valid - ref_valid) / ref_valid)
        
        return {
            'n_points': len(calc_valid),
            'mae': np.mean(absolute_errors),  # Mean Absolute Error
            'rmse': np.sqrt(np.mean((calc_valid - ref_valid) ** 2)),  # Root Mean Square Error
            'mape': np.mean(relative_errors) * 100,  # Mean Absolute Percentage Error
            'median_ape': np.median(relative_errors) * 100,  # Median Absolute Percentage Error
            'r_squared': stats.pearsonr(calc_valid, ref_valid)[0] ** 2,
            'within_5_percent': np.sum(relative_errors <= 0.05),
            'within_10_percent': np.sum(relative_errors <= 0.10),
            'within_15_percent': np.sum(relative_errors <= 0.15),
            'accuracy_rate_15pct': np.sum(relative_errors <= 0.15) / len(relative_errors)
        }


class SyntheticDataGenerator:
    """Generate synthetic test data for controlled testing."""
    
    @staticmethod
    def generate_synthetic_peaks(snr_range: Tuple[float, float] = (5, 50), 
                                peak_count: int = 10,
                                time_range: Tuple[float, float] = (0, 10)) -> List[Dict]:
        """
        Generate synthetic Gaussian peaks for controlled testing.
        
        Args:
            snr_range: Range of signal-to-noise ratios
            peak_count: Number of peaks to generate
            time_range: Time range for peak generation (minutes)
            
        Returns:
            list: List of synthetic peak data dictionaries
        """
        peaks = []
        
        for i in range(peak_count):
            # Random peak parameters
            peak_center = np.random.uniform(time_range[0], time_range[1])
            peak_width = np.random.uniform(0.1, 0.5)
            snr = np.random.uniform(snr_range[0], snr_range[1])
            baseline = np.random.uniform(500, 2000)
            peak_height = baseline * snr
            
            # Generate time points
            time_points = np.linspace(peak_center - 2*peak_width, 
                                    peak_center + 2*peak_width, 100)
            
            # Generate Gaussian peak
            intensities = baseline + peak_height * np.exp(
                -0.5 * ((time_points - peak_center) / peak_width) ** 2
            )
            
            # Add noise
            noise_level = peak_height / snr
            intensities += np.random.normal(0, noise_level, len(time_points))
            intensities = np.maximum(intensities, 0)  # Ensure non-negative
            
            peaks.append({
                'peak_id': i,
                'time_points': time_points,
                'intensities': intensities,
                'true_center': peak_center,
                'true_width': peak_width,
                'true_height': peak_height,
                'true_snr': snr,
                'baseline': baseline
            })
        
        return peaks
    
    @staticmethod
    def generate_concentration_series(concentrations: List[float],
                                    slope: float = 10000.0,
                                    intercept: float = 1000.0,
                                    noise_level: float = 0.05) -> Dict:
        """
        Generate synthetic concentration calibration series.
        
        Args:
            concentrations: List of concentration values
            slope: Calibration curve slope
            intercept: Calibration curve intercept
            noise_level: Relative noise level (0-1)
            
        Returns:
            dict: Synthetic calibration data
        """
        areas = []
        
        for conc in concentrations:
            # True area from linear relationship
            true_area = slope * conc + intercept
            
            # Add noise
            noise = np.random.normal(0, true_area * noise_level)
            observed_area = max(0, true_area + noise)  # Ensure non-negative
            
            areas.append(observed_area)
        
        return {
            'concentrations': concentrations,
            'areas': areas,
            'true_slope': slope,
            'true_intercept': intercept,
            'noise_level': noise_level
        }


# Test Fixtures
@pytest.fixture(scope="session")
def stmix_concentration_series():
    """Load STMIX concentration series data for testing."""
    # STMIX concentration levels based on available sample data
    concentrations = [0.01, 0.1, 0.5, 2.5, 5.0, 10.0]  # mM
    
    series_data = {
        'concentrations': concentrations,
        'files': {
            'positive': [f"STMIX_BIG_{conc}mM_pos.mzml" for conc in concentrations],
            'negative': [f"STMIX_BIG_{conc}mM_neg.mzml" for conc in concentrations]
        },
        'expected_rt_range': (2.0, 8.0),  # Expected retention time range
        'compound_list': 'aminoacids_and_polyamines',  # Reference to config.json section
        'true_concentrations': {  # Filename -> true concentration mapping
            'STMIX_BIG_0.01mM': 0.01,
            'STMIX_BIG_0.1mM': 0.1, 
            'STMIX_BIG_0.5mM': 0.5,
            'STMIX_BIG_2.5mM': 2.5,
            'STMIX_BIG_5mM': 5.0,
            'STMIX_BIG_10mM': 10.0,
            'STMIX_BIG_0.01mM_pos': 0.01,
            'STMIX_BIG_0.1mM_pos': 0.1,
            'STMIX_BIG_0.5mM_pos': 0.5,
            'STMIX_BIG_2.5mM_pos': 2.5,
            'STMIX_BIG_5mM_pos': 5.0,
            'STMIX_BIG_10mM_pos': 10.0,
            'STMIX_BIG_0.01mM_neg': 0.01,
            'STMIX_BIG_0.1mM_neg': 0.1,
            'STMIX_BIG_0.5mM_neg': 0.5,
            'STMIX_BIG_2.5mM_neg': 2.5,
            'STMIX_BIG_5mM_neg': 5.0,
            'STMIX_BIG_10mM_neg': 10.0
        }
    }
    
    logger.info(f"Loaded STMIX concentration series: {concentrations} mM")
    return series_data


@pytest.fixture(scope="session")
def aminoacids_compounds():
    """Load aminoacids and polyamines compound list from config.json."""
    config_path = Path("lc-inspector/config.json")
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        compounds_data = config.get("Amino acids and polyamines (DEEMM)", {})
        logger.info(f"Loaded {len(compounds_data)} compounds from aminoacids and polyamines")
        return compounds_data
    else:
        logger.warning("config.json not found - using mock compounds")
        # Minimal mock for testing
        return {
            "Alanine": {
                "ions": [260.1129, 214.0710, 258.0983, 90.0550, 88.0404],
                "info": ["Alanine-D", "Alanine-NL", "Alanine-D-neg", "Alanine-I-pos", "Alanine-I-neg"]
            },
            "Glycine": {
                "ions": [246.0973, 200.0554, 244.0826, 76.0394, 74.0247],
                "info": ["Glycine-D", "Glycine-NL", "Glycine-D-neg", "Glycine-I-pos", "Glycine-I-neg"]
            }
        }


@pytest.fixture
def stmix_filename_parser():
    """Utility to extract true concentration from STMIX filenames."""
    def parse_concentration(filename: str) -> float:
        """
        Extract concentration from STMIX filename.
        
        Examples:
            'STMIX_BIG_0.01mM_pos.mzml' -> 0.01
            'STMIX_BIG_2.5mM_neg.txt' -> 2.5
            'STMIX_BIG_10mM.mzml' -> 10.0
        """
        import re
        
        # Pattern to match concentration in filename
        pattern = r'STMIX_BIG_(\d+\.?\d*)mM'
        match = re.search(pattern, filename)
        
        if match:
            return float(match.group(1))
        else:
            raise ValueError(f"Could not extract concentration from filename: {filename}")
    
    return parse_concentration


@pytest.fixture
def synthetic_peak_data():
    """Generate synthetic Gaussian peaks for controlled testing."""
    generator = SyntheticDataGenerator()
    peaks = generator.generate_synthetic_peaks(
        snr_range=(5, 50),
        peak_count=5,
        time_range=(2.0, 8.0)
    )
    return peaks


@pytest.fixture
def validation_utilities():
    """Provide validation utility instances for tests."""
    return {
        'concentration_validator': ConcentrationTestValidator(),
        'data_comparator': DataComparisonTools(),
        'data_generator': SyntheticDataGenerator()
    }


@pytest.fixture
def test_tolerances():
    """Provide test tolerance values."""
    return {
        'concentration': CONCENTRATION_TOLERANCE,
        'integration': INTEGRATION_CRITERIA,
        'statistical': STATISTICAL_THRESHOLDS
    }


@pytest.fixture
def temp_test_directory():
    """Create temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)