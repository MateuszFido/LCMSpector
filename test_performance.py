#!/usr/bin/env python3
"""
Performance test script for the optimized loading module.
"""

import time
import sys
import os
import tempfile
import pandas as pd
import numpy as np
from pathlib import Path

# Add the current directory to the path for package imports
sys.path.insert(0, '.')

def create_test_csv(filepath, num_rows=10000):
    """Create a test CSV file for performance testing."""
    with open(filepath, 'w') as f:
        f.write("Time,Intensity\n")
        for i in range(num_rows):
            time_val = i * 0.01
            intensity_val = np.random.random() * 1000
            f.write(f"{time_val},{intensity_val}\n")

def benchmark_function(func, *args, **kwargs):
    """Benchmark a function and return execution time."""
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    return result, end_time - start_time

def test_csv_loading():
    """Test CSV loading performance."""
    print("Testing CSV loading performance...")
    
    # Create test data
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        test_file = f.name
    
    create_test_csv(test_file, 50000)
    
    try:
        # Test original implementation
        from utils.loading import load_absorbance_data as load_original
        result_orig, time_orig = benchmark_function(load_original, test_file)
        print(f"Original implementation: {time_orig:.4f} seconds")
        
        # Test optimized implementation
        from utils.loading_optimized import load_absorbance_data as load_optimized
        result_opt, time_opt = benchmark_function(load_optimized, test_file)
        print(f"Optimized implementation: {time_opt:.4f} seconds")
        
        # Calculate speedup
        if time_opt > 0:
            speedup = time_orig / time_opt
            print(f"Speedup: {speedup:.2f}x")
        
        # Verify results are equivalent
        if len(result_orig) == len(result_opt):
            print("✓ Results are equivalent in size")
        else:
            print("✗ Results differ in size")
            
    finally:
        os.unlink(test_file)

def test_ms2_library_loading():
    """Test MS2 library loading if library file exists."""
    print("\nTesting MS2 library loading...")
    
    library_path = Path("lc-inspector/resources/MoNA-export-All_LC-MS-MS_Orbitrap.msp")
    if not library_path.exists():
        print("MS2 library file not found, skipping test")
        return
    
    try:
        # Test original implementation
        from utils.loading import load_ms2_library as load_ms2_original
        result_orig, time_orig = benchmark_function(load_ms2_original)
        print(f"Original implementation: {time_orig:.4f} seconds")
        
        # Test optimized implementation
        from utils.loading_optimized import load_ms2_library as load_ms2_optimized
        result_opt, time_opt = benchmark_function(load_ms2_optimized)
        print(f"Optimized implementation: {time_opt:.4f} seconds")
        
        # Calculate speedup
        if time_opt > 0:
            speedup = time_orig / time_opt
            print(f"Speedup: {speedup:.2f}x")
        
        # Verify results
        if len(result_orig) == len(result_opt):
            print("✓ Results are equivalent in size")
        else:
            print("✗ Results differ in size")
            
    except Exception as e:
        print(f"Error testing MS2 library loading: {e}")

def test_c_extensions():
    """Test if C extensions are working."""
    print("Testing C extensions...")
    
    try:
        import loading_accelerator
        print("✓ C extensions loaded successfully")
        
        # Test fast CSV parsing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            test_file = f.name
        
        create_test_csv(test_file, 1000)
        
        try:
            result = loading_accelerator.load_absorbance_data_fast(test_file)
            print("✓ Fast CSV parsing works")
            print(f"  Loaded {len(result)} rows")
        except Exception as e:
            print(f"✗ Fast CSV parsing failed: {e}")
        finally:
            os.unlink(test_file)
            
        # Test MSP line processing
        test_line = "Name: Test Compound\n"
        result = loading_accelerator.process_msp_line_fast(test_line)
        if result == "Test Compound":
            print("✓ MSP line processing works")
        else:
            print(f"✗ MSP line processing failed: got '{result}'")
            
    except ImportError:
        print("✗ C extensions not available")

def main():
    """Run all performance tests."""
    print("LC-Inspector Loading Module Performance Tests")
    print("=" * 50)
    
    test_c_extensions()
    test_csv_loading()
    test_ms2_library_loading()
    
    print("\nPerformance testing complete!")

if __name__ == "__main__":
    main()
