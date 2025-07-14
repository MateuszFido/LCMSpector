#!/usr/bin/env python3
"""
Demonstration script showing the performance optimizations in action.
"""

import sys
import os
import tempfile
import time
import logging

# Add the current directory to the path for package imports
sys.path.insert(0, '.')

# Configure logging to see the optimization messages
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def create_sample_data():
    """Create sample CSV data for demonstration."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("Time,Intensity\n")
        for i in range(10000):
            f.write(f"{i * 0.01},{i * 0.1 + (i % 100)}\n")
        return f.name

def demonstrate_loading():
    """Demonstrate the optimized loading functionality."""
    print("LC-Inspector Loading Module Optimization Demo")
    print("=" * 50)
    
    # Create sample data
    print("Creating sample data...")
    csv_file = create_sample_data()
    
    try:
        # Import the optimized loading module
        print("\nImporting optimized loading module...")
        from lc_inspector.utils.loading_optimized import load_absorbance_data
        
        # Load data and time it
        print("Loading absorbance data...")
        start_time = time.time()
        data = load_absorbance_data(csv_file)
        end_time = time.time()
        
        print(f"✓ Loaded {len(data)} rows in {end_time - start_time:.4f} seconds")
        print(f"✓ Data shape: {data.shape}")
        print(f"✓ Columns: {list(data.columns)}")
        
        # Show first few rows
        print("\nFirst 5 rows of loaded data:")
        print(data.head())
        
        # Test MS2 library loading if available
        print("\nTesting MS2 library loading...")
        from lc_inspector.utils.loading_optimized import load_ms2_library
        
        start_time = time.time()
        library = load_ms2_library()
        end_time = time.time()
        
        if library:
            print(f"✓ Loaded MS2 library with {len(library)} entries in {end_time - start_time:.4f} seconds")
            print(f"✓ Sample entries: {list(library.keys())[:3]}")
        else:
            print("ℹ MS2 library file not found (this is normal for demo)")
        
        # Test classes integration
        print("\nTesting integration with measurement classes...")
        from lc_inspector.utils.classes import LCMeasurement
        
        start_time = time.time()
        measurement = LCMeasurement(csv_file)
        end_time = time.time()
        
        print(f"✓ Created LCMeasurement object in {end_time - start_time:.4f} seconds")
        print(f"✓ Measurement filename: {measurement.filename}")
        print(f"✓ Data shape: {measurement.data.shape}")
        
    except Exception as e:
        print(f"✗ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if os.path.exists(csv_file):
            os.unlink(csv_file)
    
    print("\nDemo complete!")

def show_optimization_status():
    """Show the status of optimizations."""
    print("\nOptimization Status:")
    print("-" * 20)
    
    try:
        import loading_accelerator
        print("✓ C extensions loaded successfully")
        
        # Test each function
        functions = [
            'load_absorbance_data_fast',
            'process_msp_line_fast', 
            'parse_numeric_fast'
        ]
        
        for func_name in functions:
            if hasattr(loading_accelerator, func_name):
                print(f"  ✓ {func_name} available")
            else:
                print(f"  ✗ {func_name} not available")
                
    except ImportError:
        print("✗ C extensions not available")
        print("  Run: python3 setup.py build_ext --inplace")
    
    # Check optimized module
    try:
        from lc_inspector.utils.loading_optimized import HAS_C_EXTENSIONS
        if HAS_C_EXTENSIONS:
            print("✓ Optimized loading module using C extensions")
        else:
            print("ℹ Optimized loading module using Python fallback")
    except ImportError:
        print("✗ Optimized loading module not found")

if __name__ == "__main__":
    show_optimization_status()
    demonstrate_loading()
