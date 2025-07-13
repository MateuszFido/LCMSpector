#!/usr/bin/env python3
"""
Script to compare the performance of the original and optimized versions of LC-Inspector.

This script runs both versions of the LC-Inspector application with the same input files
and reports performance metrics such as memory usage, processing time, and CPU utilization.
"""

import os
import sys
import time
import argparse
import psutil
import logging
import tempfile
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from concurrent.futures import ThreadPoolExecutor

# Add the LC-Inspector directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def monitor_process(pid, metrics, interval=0.5):
    """Monitor a process and record memory usage and CPU utilization."""
    process = psutil.Process(pid)
    while process.is_running() and psutil.pid_exists(pid):
        try:
            # Get memory info
            mem_info = process.memory_info()
            cpu_percent = process.cpu_percent(interval=0.1)
            
            # Record metrics
            metrics['memory'].append(mem_info.rss / (1024 * 1024))  # MB
            metrics['cpu'].append(cpu_percent)
            
            time.sleep(interval)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            break
    logger.info(f"Monitoring for PID {pid} ended")

def run_and_monitor(command, metrics_key, lc_files, ms_files):
    """Run a command and monitor its performance."""
    metrics = {metrics_key: {'memory': [], 'cpu': [], 'time': 0}}
    
    # Start the process
    logger.info(f"Running {command}...")
    start_time = time.time()
    process = psutil.Popen(command, shell=True)
    
    # Start monitoring in a separate thread
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(monitor_process, process.pid, metrics[metrics_key])
        
        # Wait for the process to complete
        process.wait()
        
    # Calculate the execution time
    end_time = time.time()
    metrics[metrics_key]['time'] = end_time - start_time
    
    # Log performance metrics
    max_memory = max(metrics[metrics_key]['memory']) if metrics[metrics_key]['memory'] else 0
    avg_cpu = sum(metrics[metrics_key]['cpu']) / len(metrics[metrics_key]['cpu']) if metrics[metrics_key]['cpu'] else 0
    
    logger.info(f"{metrics_key} Performance:")
    logger.info(f"  Execution time: {metrics[metrics_key]['time']:.2f} seconds")
    logger.info(f"  Peak memory usage: {max_memory:.2f} MB")
    logger.info(f"  Average CPU utilization: {avg_cpu:.2f}%")
    
    return metrics

def plot_performance_comparison(metrics):
    """Create performance comparison plots."""
    # Set up the plots
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 15))
    
    # Extract the metrics
    original = metrics['Original']
    optimized = metrics['Optimized']
    
    # Plot execution time
    labels = ['Original', 'Optimized']
    times = [original['time'], optimized['time']]
    ax1.bar(labels, times, color=['blue', 'green'])
    ax1.set_ylabel('Execution Time (seconds)')
    ax1.set_title('Execution Time Comparison')
    
    # Add percentage improvement
    if original['time'] > 0:
        improvement = (original['time'] - optimized['time']) / original['time'] * 100
        ax1.text(1, optimized['time'], f"{improvement:.1f}% faster", 
                 ha='center', va='bottom', fontweight='bold')
    
    # Plot memory usage
    max_original_memory = max(original['memory']) if original['memory'] else 0
    max_optimized_memory = max(optimized['memory']) if optimized['memory'] else 0
    memory_values = [max_original_memory, max_optimized_memory]
    
    ax2.bar(labels, memory_values, color=['blue', 'green'])
    ax2.set_ylabel('Peak Memory Usage (MB)')
    ax2.set_title('Memory Usage Comparison')
    
    # Add percentage improvement
    if max_original_memory > 0:
        memory_improvement = (max_original_memory - max_optimized_memory) / max_original_memory * 100
        ax2.text(1, max_optimized_memory, f"{memory_improvement:.1f}% less memory", 
                 ha='center', va='bottom', fontweight='bold')
    
    # Plot CPU utilization over time
    time_points_original = np.arange(len(original['cpu']))
    time_points_optimized = np.arange(len(optimized['cpu']))
    
    ax3.plot(time_points_original, original['cpu'], label='Original', color='blue')
    ax3.plot(time_points_optimized, optimized['cpu'], label='Optimized', color='green')
    ax3.set_xlabel('Time (samples)')
    ax3.set_ylabel('CPU Utilization (%)')
    ax3.set_title('CPU Utilization Over Time')
    ax3.legend()
    
    # Adjust layout and save
    plt.tight_layout()
    output_dir = Path(tempfile.gettempdir()) / "lc_inspector_performance"
    os.makedirs(output_dir, exist_ok=True)
    output_file = output_dir / "performance_comparison.png"
    plt.savefig(output_file)
    logger.info(f"Performance comparison plot saved to {output_file}")
    
    # Show the plot
    plt.show()

def run_performance_comparison(lc_files, ms_files):
    """Run a performance comparison between the original and optimized versions."""
    # Define the commands to run
    original_cmd = f"python main.py --lc-files {' '.join(lc_files)} --ms-files {' '.join(ms_files)} --headless --benchmark"
    optimized_cmd = f"python main_optimized.py --lc-files {' '.join(lc_files)} --ms-files {' '.join(ms_files)} --headless --benchmark"
    
    # Run the original version and monitor performance
    original_metrics = run_and_monitor(original_cmd, 'Original', lc_files, ms_files)
    
    # Run the optimized version and monitor performance
    optimized_metrics = run_and_monitor(optimized_cmd, 'Optimized', lc_files, ms_files)
    
    # Combine metrics
    metrics = {**original_metrics, **optimized_metrics}
    
    # Plot the performance comparison
    plot_performance_comparison(metrics)
    
    return metrics

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Compare performance of LC-Inspector versions')
    parser.add_argument('--lc-files', nargs='+', help='LC data files to process')
    parser.add_argument('--ms-files', nargs='+', help='MS data files to process')
    parser.add_argument('--sample-data', action='store_true', help='Use sample data files for testing')
    return parser.parse_args()

def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Use provided files or sample data
    lc_files = args.lc_files or []
    ms_files = args.ms_files or []
    
    if args.sample_data:
        # TODO: Add sample data files
        logger.info("Using sample data files for testing")
        # This would be implemented with actual sample files
        pass
    
    if not lc_files and not ms_files:
        logger.error("No input files specified. Use --lc-files, --ms-files, or --sample-data")
        sys.exit(1)
    
    # Run the performance comparison
    metrics = run_performance_comparison(lc_files, ms_files)
    
    # Print summary
    logger.info("\nPerformance Comparison Summary:")
    original = metrics['Original']
    optimized = metrics['Optimized']
    
    time_improvement = (original['time'] - optimized['time']) / original['time'] * 100 if original['time'] > 0 else 0
    memory_improvement = (max(original['memory']) - max(optimized['memory'])) / max(original['memory']) * 100 if max(original['memory']) > 0 else 0
    
    logger.info(f"Time: {time_improvement:.1f}% faster with optimized version")
    logger.info(f"Memory: {memory_improvement:.1f}% less memory usage with optimized version")
    
    # Exit with success
    return 0

if __name__ == "__main__":
    sys.exit(main())
