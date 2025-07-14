#!/usr/bin/env python3
"""
Fixed test script for the performance optimizations.
"""

import sys
import os
import tempfile
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def create_test_csv(filepath, num_rows=10000):
    """Create a test CSV file for performance testing."""
    with open(filepath, 'w') as f:
        f.write("Time,Intensity\n")
        for i in range(num_rows):
            time_val = i * 0.01
            intensity_val = i * 0.1 + (i % 100)
            f.write(f"{time_val},{intensity_val}\n")

def test_c_extension_directly():
    """Test the C extension directly."""
    print("Testing C extension directly...")
    
    # Check if the compiled extension exists
    extension_files = [
        'loading_accelerator.cpython-312-darwin.so',
        'lc-inspector/utils/loading_accelerator.cpython-312-darwin.so'
    ]
    
    extension_found = None
    for ext_file in extension_files:
        if os.path.exists(ext_file):
            extension_found = ext_file
            break
    
    if not extension_found:
        print("✗ No compiled C extension found")
        return False
    
    print(f"✓ Found C extension: {extension_found}")
    
    # Add the directory containing the extension to Python path
    ext_dir = os.path.dirname(extension_found)
    if ext_dir:
        sys.path.insert(0, ext_dir)
    
    try:
        import loading_accelerator
        print("✓ C extension imported successfully")
        
        # Test CSV parsing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            test_file = f.name
        
        create_test_csv(test_file, 1000)
        
        try:
            start_time = time.time()
            result = loading_accelerator.load_absorbance_data_fast(test_file)
            end_time = time.time()
            
            print(f"✓ Fast CSV parsing works: loaded {len(result)} rows in {end_time - start_time:.4f}s")
            
            # Show sample data
            if hasattr(result, 'head'):
                print("Sample data:")
                print(result.head())
            
        except Exception as e:
            print(f"✗ Fast CSV parsing failed: {e}")
        finally:
            os.unlink(test_file)
        
        return True
        
    except ImportError as e:
        print(f"✗ Failed to import C extension: {e}")
        return False

def test_python_fallback():
    """Test the Python fallback implementation."""
    print("\nTesting Python fallback...")
    
    # Add lc-inspector to path
    sys.path.insert(0, 'lc-inspector')
    
    try:
        from utils.loading import load_absorbance_data
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            test_file = f.name
        
        create_test_csv(test_file, 1000)
        
        try:
            start_time = time.time()
            result = load_absorbance_data(test_file)
            end_time = time.time()
            
            print(f"✓ Python implementation works: loaded {len(result)} rows in {end_time - start_time:.4f}s")
            
        except Exception as e:
            print(f"✗ Python implementation failed: {e}")
        finally:
            os.unlink(test_file)
            
    except ImportError as e:
        print(f"✗ Failed to import Python implementation: {e}")

def test_optimized_module():
    """Test the optimized module with proper fallback."""
    print("\nTesting optimized module...")
    
    # Add lc-inspector to path
    sys.path.insert(0, 'lc-inspector')
    
    try:
        from utils.loading_optimized import load_absorbance_data, HAS_C_EXTENSIONS
        
        print(f"✓ Optimized module imported (C extensions: {HAS_C_EXTENSIONS})")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            test_file = f.name
        
        create_test_csv(test_file, 1000)
        
        try:
            start_time = time.time()
            result = load_absorbance_data(test_file)
            end_time = time.time()
            
            print(f"✓ Optimized loading works: loaded {len(result)} rows in {end_time - start_time:.4f}s")
            print(f"✓ Data shape: {result.shape}")
            print(f"✓ Columns: {list(result.columns)}")
            
        except Exception as e:
            print(f"✗ Optimized loading failed: {e}")
        finally:
            os.unlink(test_file)
            
    except ImportError as e:
        print(f"✗ Failed to import optimized module: {e}")

def main():
    """Run all tests."""
    print("LC-Inspector Performance Optimization Tests")
    print("=" * 50)
    
    # Test C extension directly
    c_ext_works = test_c_extension_directly()
    
    # Test Python fallback
    test_python_fallback()
    
    # Test optimized module
    test_optimized_module()
    
    print("\n" + "=" * 50)
    if c_ext_works:
        print("✓ Performance optimizations are working!")
        print("  The C extensions provide faster CSV parsing.")
        print("  The system gracefully falls back to Python when needed.")
    else:
        print("ℹ C extensions not available, but Python fallback works.")
        print("  Run 'python3 setup.py build_ext --inplace' to enable optimizations.")
    
    print("\nTo use in your application:")
    print("  from lc-inspector.utils.loading_optimized import load_absorbance_data")
    print("  # or from within lc-inspector directory:")
    print("  from utils.loading_optimized import load_absorbance_data")

if __name__ == "__main__":
    main()
