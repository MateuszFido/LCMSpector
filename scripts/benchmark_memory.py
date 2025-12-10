#!/usr/bin/env python3
"""
Memory usage benchmarking script for LC-Inspector Nuitka migration.

This script monitors memory usage during application lifecycle and compares
PyInstaller vs Nuitka builds following the migration plan specifications.
"""

import psutil
import time
import subprocess
import threading
import sys
import json
import argparse
from pathlib import Path
from collections import defaultdict


class MemoryBenchmark:
    """Monitor memory usage during application lifecycle."""
    
    def __init__(self):
        self.samples = []
        self.monitoring = False
    
    def monitor_process(self, pid, duration=60):
        """Monitor memory usage of a process."""
        try:
            process = psutil.Process(pid)
            start_time = time.time()
            
            print(f"Monitoring process {pid} for {duration} seconds...")
            
            while self.monitoring and (time.time() - start_time) < duration:
                try:
                    memory_info = process.memory_info()
                    cpu_percent = process.cpu_percent()
                    
                    sample = {
                        'timestamp': time.time() - start_time,
                        'rss_mb': memory_info.rss / 1024 / 1024,
                        'vms_mb': memory_info.vms / 1024 / 1024,
                        'cpu_percent': cpu_percent
                    }
                    
                    # Add platform-specific memory info if available
                    if hasattr(memory_info, 'peak_wset'):  # Windows
                        sample['peak_wset_mb'] = memory_info.peak_wset / 1024 / 1024
                    if hasattr(memory_info, 'peak_pagefile'):  # Windows
                        sample['peak_pagefile_mb'] = memory_info.peak_pagefile / 1024 / 1024
                    
                    self.samples.append(sample)
                    
                    # Print progress every 10 seconds
                    if len(self.samples) % 20 == 0:  # Every 10 seconds (0.5s intervals)
                        print(f"  {sample['timestamp']:.1f}s: {sample['rss_mb']:.1f}MB RSS, {sample['cpu_percent']:.1f}% CPU")
                    
                    time.sleep(0.5)  # Sample every 500ms
                    
                except psutil.NoSuchProcess:
                    print("Process terminated")
                    break
                    
        except psutil.NoSuchProcess:
            print("Process not found")
    
    def benchmark_memory_usage(self, executable_path, duration=60):
        """Benchmark memory usage during typical operation."""
        self.samples = []
        self.monitoring = True
        
        print(f"Starting memory benchmark for: {executable_path}")
        
        try:
            # Start the application
            process = subprocess.Popen([str(executable_path)])
            
            # Give the process a moment to start
            time.sleep(2)
            
            # Start monitoring in a separate thread
            monitor_thread = threading.Thread(
                target=self.monitor_process,
                args=(process.pid, duration)
            )
            monitor_thread.start()
            
            # Wait for monitoring to complete
            monitor_thread.join()
            self.monitoring = False
            
            # Terminate the application
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        
        except Exception as e:
            print(f"Error during memory benchmark: {e}")
            self.monitoring = False
            return None
        
        return self.analyze_samples()
    
    def analyze_samples(self):
        """Analyze memory usage samples."""
        if not self.samples:
            return None
        
        rss_values = [s['rss_mb'] for s in self.samples]
        vms_values = [s['vms_mb'] for s in self.samples]
        cpu_values = [s['cpu_percent'] for s in self.samples]
        
        # Calculate memory growth rate
        if len(rss_values) > 1:
            initial_rss = rss_values[0]
            final_rss = rss_values[-1]
            duration = self.samples[-1]['timestamp'] - self.samples[0]['timestamp']
            growth_rate = (final_rss - initial_rss) / duration if duration > 0 else 0
        else:
            growth_rate = 0
        
        analysis = {
            'peak_memory_mb': max(rss_values),
            'avg_memory_mb': sum(rss_values) / len(rss_values),
            'startup_memory_mb': rss_values[0] if rss_values else 0,
            'final_memory_mb': rss_values[-1] if rss_values else 0,
            'memory_growth_mb_per_sec': growth_rate,
            'peak_vms_mb': max(vms_values),
            'avg_cpu_percent': sum(cpu_values) / len(cpu_values),
            'sample_count': len(self.samples),
            'duration_seconds': self.samples[-1]['timestamp'] if self.samples else 0
        }
        
        # Add percentile analysis
        rss_sorted = sorted(rss_values)
        n = len(rss_sorted)
        if n > 0:
            analysis.update({
                'memory_p50_mb': rss_sorted[n//2],
                'memory_p90_mb': rss_sorted[int(n*0.9)],
                'memory_p95_mb': rss_sorted[int(n*0.95)],
                'memory_p99_mb': rss_sorted[int(n*0.99)]
            })
        
        return analysis
    
    def compare_memory_usage(self, pyinstaller_exe, nuitka_exe, duration=60):
        """Compare memory usage between PyInstaller and Nuitka builds."""
        print("=" * 60)
        print("LC-INSPECTOR MEMORY BENCHMARK")
        print("=" * 60)
        
        results = {}
        
        # Test PyInstaller build if available
        if pyinstaller_exe and Path(pyinstaller_exe).exists():
            print(f"\nBenchmarking PyInstaller memory usage...")
            pyinstaller_stats = self.benchmark_memory_usage(pyinstaller_exe, duration)
            results['pyinstaller'] = pyinstaller_stats
        else:
            print(f"\nPyInstaller executable not found: {pyinstaller_exe}")
            pyinstaller_stats = None
        
        # Test Nuitka build if available
        if nuitka_exe and Path(nuitka_exe).exists():
            print(f"\nBenchmarking Nuitka memory usage...")
            nuitka_stats = self.benchmark_memory_usage(nuitka_exe, duration)
            results['nuitka'] = nuitka_stats
        else:
            print(f"\nNuitka executable not found: {nuitka_exe}")
            nuitka_stats = None
        
        # Compare results
        if pyinstaller_stats and nuitka_stats:
            memory_diff = ((nuitka_stats['peak_memory_mb'] - pyinstaller_stats['peak_memory_mb']) 
                          / pyinstaller_stats['peak_memory_mb'] * 100)
            
            print(f"\n{'='*60}")
            print(f"MEMORY USAGE COMPARISON")
            print(f"{'='*60}")
            print(f"PyInstaller Peak:    {pyinstaller_stats['peak_memory_mb']:.1f}MB")
            print(f"PyInstaller Average: {pyinstaller_stats['avg_memory_mb']:.1f}MB")
            print(f"Nuitka Peak:         {nuitka_stats['peak_memory_mb']:.1f}MB")
            print(f"Nuitka Average:      {nuitka_stats['avg_memory_mb']:.1f}MB")
            print(f"Memory Difference:   {memory_diff:+.1f}%")
            
            startup_diff = ((nuitka_stats['startup_memory_mb'] - pyinstaller_stats['startup_memory_mb'])
                           / pyinstaller_stats['startup_memory_mb'] * 100)
            print(f"Startup Difference:  {startup_diff:+.1f}%")
            
            if abs(memory_diff) < 10:
                print("≈ Memory usage is similar")
            elif memory_diff < 0:
                print("✓ Nuitka uses LESS memory than PyInstaller")
            else:
                print("⚠ Nuitka uses MORE memory than PyInstaller")
            
            results['comparison'] = {
                'memory_difference_percent': memory_diff,
                'startup_difference_percent': startup_diff,
                'nuitka_more_efficient': memory_diff < 0
            }
        
        elif pyinstaller_stats:
            print(f"\nPyInstaller Memory Results:")
            self._print_memory_stats(pyinstaller_stats)
            
        elif nuitka_stats:
            print(f"\nNuitka Memory Results:")
            self._print_memory_stats(nuitka_stats)
            
        else:
            print("\nNo executables found to benchmark!")
            return None
        
        return results
    
    def _print_memory_stats(self, stats):
        """Print memory statistics in a formatted way."""
        print(f"Peak memory:    {stats['peak_memory_mb']:.1f}MB")
        print(f"Average memory: {stats['avg_memory_mb']:.1f}MB")
        print(f"Startup memory: {stats['startup_memory_mb']:.1f}MB")
        print(f"Memory growth:  {stats['memory_growth_mb_per_sec']:.2f}MB/sec")
        print(f"Average CPU:    {stats['avg_cpu_percent']:.1f}%")
        print(f"Duration:       {stats['duration_seconds']:.1f}s")
    
    def save_results(self, results, output_file="memory_benchmark_results.json"):
        """Save benchmark results to file."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        output_data = {
            'timestamp': timestamp,
            'system_info': {
                'platform': sys.platform,
                'total_memory_gb': psutil.virtual_memory().total / (1024**3),
                'available_memory_gb': psutil.virtual_memory().available / (1024**3),
                'cpu_count': psutil.cpu_count(),
                'python_version': sys.version,
            },
            'results': results,
            'raw_samples': self.samples[-100:]  # Keep last 100 samples
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\nResults saved to: {output_file}")


def auto_detect_executables():
    """Auto-detect available executables."""
    candidates = {
        'pyinstaller': [
            'lc-inspector/dist/LCMSpector',
            'lc-inspector/dist/LCMSpector/LCMSpector.exe',
            'lc-inspector/dist/LCMSpector.app/Contents/MacOS/LCMSpector',
        ],
        'nuitka': [
            'lc-inspector/dist/main',
            'lc-inspector/dist/main.exe',
            'lc-inspector/dist/LCMSpector.app/Contents/MacOS/LCMSpector',
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
    parser = argparse.ArgumentParser(description='Benchmark LC-Inspector memory usage')
    parser.add_argument('--pyinstaller', help='Path to PyInstaller executable')
    parser.add_argument('--nuitka', help='Path to Nuitka executable')
    parser.add_argument('--duration', type=int, default=60,
                       help='Monitoring duration in seconds (default: 60)')
    parser.add_argument('--auto-detect', action='store_true',
                       help='Auto-detect executables in standard locations')
    parser.add_argument('--output', default='memory_benchmark_results.json',
                       help='Output file for results')
    
    args = parser.parse_args()
    
    benchmark = MemoryBenchmark()
    
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
    
    results = benchmark.compare_memory_usage(
        pyinstaller_exe, 
        nuitka_exe, 
        args.duration
    )
    
    if results:
        benchmark.save_results(results, args.output)
        return 0
    else:
        print("Benchmark failed - no valid results obtained")
        return 1


if __name__ == "__main__":
    sys.exit(main())