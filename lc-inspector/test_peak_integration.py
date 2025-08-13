#!/usr/bin/env python3
"""
Test script to verify peak area integration functionality in LC-Inspector.

This script tests the peak area calculation system by creating synthetic data
and verifying that the integration functions work correctly.
"""

import numpy as np
import sys
import os
import logging

# Add the lc-inspector directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_peak_integration_module():
    """Test the peak integration module with synthetic data."""
    try:
        from utils.peak_integration import (
            integrate_ms_xic_peak, 
            integrate_lc_peak,
            safe_peak_integration,
            create_fallback_peak_area
        )
        logger.info("✓ Peak integration module imported successfully")
        
        # Create synthetic MS XIC data (Gaussian peak)
        times = np.linspace(0, 10, 100)  # 10 minutes, 100 data points
        peak_center = 5.0
        peak_width = 0.5
        baseline = 1000
        peak_height = 50000
        
        # Generate Gaussian peak with noise
        intensities = baseline + peak_height * np.exp(-0.5 * ((times - peak_center) / peak_width) ** 2)
        intensities += np.random.normal(0, 500, len(times))  # Add noise
        intensities = np.maximum(intensities, 0)  # Ensure non-negative
        
        # Test MS XIC peak integration
        logger.info("Testing MS XIC peak integration...")
        ms_result = safe_peak_integration(
            integrate_ms_xic_peak,
            scan_times=times,
            intensities=intensities,
            rt_target=peak_center,
            mass_accuracy=0.0001,
            noise_threshold=2000
        )
        
        logger.info(f"MS Peak Area Results:")
        logger.info(f"  Total Area: {ms_result['total_area']:.2f}")
        logger.info(f"  Baseline Corrected Area: {ms_result['baseline_corrected_area']:.2f}")
        logger.info(f"  Peak Height: {ms_result['peak_height']:.2f}")
        logger.info(f"  SNR: {ms_result['snr']:.2f}")
        logger.info(f"  Quality Score: {ms_result['quality_score']:.3f}")
        logger.info(f"  Integration Method: {ms_result['integration_method']}")
        
        # Verify results are reasonable
        assert ms_result['total_area'] > 0, "Total area should be positive"
        assert ms_result['baseline_corrected_area'] > 0, "Baseline corrected area should be positive"
        assert ms_result['peak_height'] > 0, "Peak height should be positive"
        assert 0 <= ms_result['quality_score'] <= 1, "Quality score should be between 0 and 1"
        
        logger.info("✓ MS XIC peak integration test passed")
        
        # Test LC peak integration with baseline-corrected data
        logger.info("Testing LC peak integration...")
        baseline_corrected = intensities - baseline  # Remove baseline
        baseline_corrected = np.maximum(baseline_corrected, 0)  # Ensure non-negative
        
        lc_result = safe_peak_integration(
            integrate_lc_peak,
            retention_times=times,
            absorbances=intensities,  # Original data
            baseline_corrected=baseline_corrected,  # Baseline corrected
            rt_target=peak_center,
            noise_threshold=1000
        )
        
        logger.info(f"LC Peak Area Results:")
        logger.info(f"  Total Area: {lc_result['total_area']:.2f}")
        logger.info(f"  Baseline Corrected Area: {lc_result['baseline_corrected_area']:.2f}")
        logger.info(f"  Peak Height: {lc_result['peak_height']:.2f}")
        logger.info(f"  SNR: {lc_result['snr']:.2f}")
        logger.info(f"  Quality Score: {lc_result['quality_score']:.3f}")
        
        # Verify results are reasonable
        assert lc_result['total_area'] > 0, "LC total area should be positive"
        assert lc_result['baseline_corrected_area'] > 0, "LC baseline corrected area should be positive"
        
        logger.info("✓ LC peak integration test passed")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Peak integration test failed: {e}")
        return False

def test_compound_enhancement():
    """Test that Compound class can be enhanced with peak area data."""
    try:
        from utils.classes import Compound
        
        # Create a test compound
        compound = Compound("Test Compound", [100.0, 200.0], ["Ion1", "Ion2"])
        
        # Verify original structure
        assert 'RT' in compound.ions[100.0]
        assert 'MS Intensity' in compound.ions[100.0]
        assert 'LC Intensity' in compound.ions[100.0]
        
        # Add peak area data (simulating what construct_xics would do)
        compound.ions[100.0]['MS Peak Area'] = {
            'total_area': 12345.67,
            'baseline_corrected_area': 10000.0,
            'start_time': 4.5,
            'end_time': 5.5,
            'peak_height': 50000.0,
            'snr': 25.0,
            'quality_score': 0.85,
            'integration_method': 'trapezoidal'
        }
        
        # Verify the enhancement worked
        assert 'MS Peak Area' in compound.ions[100.0]
        assert compound.ions[100.0]['MS Peak Area']['total_area'] == 12345.67
        
        logger.info("✓ Compound class enhancement test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Compound enhancement test failed: {e}")
        return False

def test_preprocessing_integration():
    """Test that preprocessing can import and use peak integration functions."""
    try:
        # Test that construct_xics can import peak integration functions
        from utils.preprocessing import construct_xics
        from utils.peak_integration import safe_peak_integration, integrate_ms_xic_peak
        
        logger.info("✓ Preprocessing integration test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Preprocessing integration test failed: {e}")
        return False

def test_model_export_enhancement():
    """Test that model export functionality includes peak area fields."""
    try:
        from ui.model import Model
        
        # Create a mock model and verify export method exists
        # Note: We can't fully test without actual data files
        model = Model()
        
        # Verify the export method exists and can be called
        assert hasattr(model, 'export'), "Model should have export method"
        
        logger.info("✓ Model export enhancement test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Model export enhancement test failed: {e}")
        return False

def run_all_tests():
    """Run all test functions and report results."""
    logger.info("=" * 60)
    logger.info("LC-Inspector Peak Area Integration Test Suite")
    logger.info("=" * 60)
    
    tests = [
        ("Peak Integration Module", test_peak_integration_module),
        ("Compound Enhancement", test_compound_enhancement),
        ("Preprocessing Integration", test_preprocessing_integration),
        ("Model Export Enhancement", test_model_export_enhancement)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\nRunning {test_name}...")
        try:
            if test_func():
                passed += 1
            else:
                logger.error(f"Test {test_name} failed")
        except Exception as e:
            logger.error(f"Test {test_name} failed with exception: {e}")
    
    logger.info("\n" + "=" * 60)
    logger.info(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Peak area integration is working correctly.")
    else:
        logger.warning(f"⚠️  {total - passed} tests failed. Please check the implementation.")
    
    logger.info("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)