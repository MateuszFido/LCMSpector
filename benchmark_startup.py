#!/usr/bin/env python3
"""
Startup time benchmarking script for LC-Inspector Nuitka migration.

This script measures application startup performance and compares
PyInstaller vs Nuitka builds following the migration plan specifications.
"""

import time
import subprocess
import statistics
import json
import sys
import argparse
from pathlib import Path


class StartupBenchmark:
    """Benchmark application startup performance."""
    
    def __init__(self):
        self.results = {}
    
    def measure_startup(self, executable_path, iterations=10):
        """Measure startup time with statistical analysis."""
        times = []
        
        print(f"Measuring startup time for: {executable_path}")
        print(f"Running {iterations} iterations...")
        
        for i in range(iterations):
            # Use a special flag to exit immediately after initialization
            start_time = time.perf_counter()
            
            try:
                result = subprocess.run(
                    [str(executable_path), '--app-info'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                end_time = time.perf_counter()
                
                if result.returncode == 0:
                    startup_time = end_time - start_time
                    times.append(startup_time)
                    print(f"Run {i+1:2d}: {startup_time:6.3f}s")
                else:
                    print(f"Run {i+1:2d}: FAILED - {result.stderr[:100]}")
                    
            except subprocess.TimeoutExpired:
                end_time = time.perf_counter()
                startup_time = end_time - start_time
                print(f"Run {i+1:2d}: TIMEOUT ({startup_time:6.3f}s) - App may have started but didn't exit")
                # Don't include timeout runs in statistics
            except Exception as e:
                print(f"Run {i+1:2d}: ERROR - {e}")
        
        if times:
            return {
                'mean': statistics.mean(times),
                'median': statistics.median(times),
                'stdev': statistics.stdev(times) if len(times) > 1 else 0,
                'min': min(times),
                'max': max(times),
                'count': len(times),
                'raw_times': times
            }
        return None
    
    def compare_builds(self, pyinstaller_exe, nuitka_exe, iterations=10):
        """Compare PyInstaller vs Nuitka performance."""
        print("=" * 60)
        print("LC-INSPECTOR STARTUP BENCHMARK")
        print("=" * 60)
        
        results = {}
        
        # Test PyInstaller build if available
        if pyinstaller_exe and Path(pyinstaller_exe).exists():
            print("\nBenchmarking PyInstaller build...")
            pyinstaller_stats = self.measure_startup(pyinstaller_exe, iterations)
            results['pyinstaller'] = pyinstaller_stats
        else:
            print(f"\nPyInstaller executable not found: {pyinstaller_exe}")
            pyinstaller_stats = None
        
        # Test Nuitka build if available
        if nuitka_exe and Path(nuitka_exe).exists():
            print("\nBenchmarking Nuitka build...")
            nuitka_stats = self.measure_startup(nuitka_exe, iterations)
            results['nuitka'] = nuitka_stats
        else:
            print(f"\nNuitka executable not found: {nuitka_exe}")
            nuitka_stats = None
        
        # Compare results
        if pyinstaller_stats and nuitka_stats:
            improvement = ((pyinstaller_stats['mean'] - nuitka_stats['mean']) 
                          / pyinstaller_stats['mean'] * 100)
            
            print(f"\n{'='*60}")
            print(f"PERFORMANCE COMPARISON")
            print(f"{'='*60}")
            print(f"PyInstaller: {pyinstaller_stats['mean']:.3f}s ± {pyinstaller_stats['stdev']:.3f}s")
            print(f"Nuitka:      {nuitka_stats['mean']:.3f}s ± {nuitka_stats['stdev']:.3f}s")
            print(f"Improvement: {improvement:+.1f}%")
            
            if improvement > 0:
                print("✓ Nuitka is FASTER than PyInstaller")
            elif improvement < -10:
                print("✗ Nuitka is significantly SLOWER than PyInstaller")
            else:
                print("≈ Performance is similar")
            
            results['comparison'] = {
                'improvement_percent': improvement,
                'nuitka_faster': improvement > 0
            }
        
        elif pyinstaller_stats:
            print(f"\nPyInstaller Results:")
            print(f"Mean startup time: {pyinstaller_stats['mean']:.3f}s ± {pyinstaller_stats['stdev']:.3f}s")
            
        elif nuitka_stats:
            print(f"\nNuitka Results:")
            print(f"Mean startup time: {nuitka_stats['mean']:.3f}s ± {nuitka_stats['stdev']:.3f}s")
            
        else:
            print("\nNo executables found to benchmark!")
            return None
        
        return results
    
    def save_results(self, results, output_file="startup_benchmark_results.json"):
        """Save benchmark results to file."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        output_data = {
            'timestamp': timestamp,
            'system_info': {
                'platform': sys.platform,
                'python_version': sys.version,
            },
            'results': results
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\nResults saved to: {output_file}")


def auto_detect_executables():
    """Auto-detect available executables."""
    candidates = {
        'pyinstaller': [
            'lc-inspector/dist/LCMSpector',  # macOS PyInstaller
            'lc-inspector/dist/LCMSpector/LCMSpector.exe',  # Windows PyInstaller
            'lc-inspector/dist/LCMSpector.app/Contents/MacOS/LCMSpector',  # macOS bundle
        ],
        'nuitka': [
            'lc-inspector/dist/main',  # macOS Nuitka
            'lc-inspector/dist/main.exe',  # Windows Nuitka
            'lc-inspector/dist/LCMSpector.app/Contents/MacOS/LCMSpector',  # macOS Nuitka bundle
        ]
    }
    
    found = {}
    for build_type, paths in candidates.items():
        for path in paths:
            if Path(path).exists():
                found[build_type] = path
                break
    
    return found


def main():
    parser = argparse.ArgumentParser(description='Benchmark LC-Inspector startup performance')
    parser.add_argument('--pyinstaller', help='Path to PyInstaller executable')
    parser.add_argument('--nuitka', help='Path to Nuitka executable')
    parser.add_argument('--iterations', type=int, default=10,
                       help='Number of iterations to run (default: 10)')
    parser.add_argument('--auto-detect', action='store_true',
                       help='Auto-detect executables in standard locations')
    parser.add_argument('--output', default='startup_benchmark_results.json',
                       help='Output file for results')
    
    args = parser.parse_args()
    
    benchmark = StartupBenchmark()
    
    if args.auto_detect:
        print("Auto-detecting executables...")
        found = auto_detect_executables()
        pyinstaller_exe = found.get('pyinstaller')
        nuitka_exe = found.get('nuitka')
        
        if pyinstaller_exe:
            print(f"Found PyInstaller build: {pyinstaller_exe}")
        if nuitka_exe:
            print(f"Found Nuitka build: {nuitka_exe}")
        if not found:
            print("No executables found in standard locations")
            return 1
    else:
        pyinstaller_exe = args.pyinstaller
        nuitka_exe = args.nuitka
    
    results = benchmark.compare_builds(
        pyinstaller_exe, 
        nuitka_exe, 
        args.iterations
    )
    
    if results:
        benchmark.save_results(results, args.output)
        return 0
    else:
        print("Benchmark failed - no valid results obtained")
        return 1


if __name__ == "__main__":
    sys.exit(main())