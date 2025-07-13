"""
Optimized worker module for the LC-Inspector application.

This module provides worker classes for handling concurrent processing tasks.
"""

from PyQt6.QtCore import QThread, QObject, pyqtSignal
import time
import sys
import traceback
import multiprocessing
import logging
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from utils.classes import LCMeasurement, MSMeasurement
import os
import numpy as np
import psutil

logger = logging.getLogger(__name__)

class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        tuple (exctype, value, traceback.format_exc())

    result
        object data returned from processing, anything

    progress
        int indicating % progress
    """
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)

class OptimizedWorker(QThread):
    """
    Optimized worker thread for processing data.
    
    This class handles the concurrent processing of data files with improved performance:
    1. Adaptive worker count based on system resources
    2. Batch processing to manage memory usage
    3. Caching of intermediate results
    4. Better exception handling and recovery
    
    Attributes
    ----------
    progressUpdated : pyqtSignal
        Signal emitted when progress is updated.
    finished : pyqtSignal
        Signal emitted when processing is finished.
    model : LCInspectorModel
        The model instance.
    mode : str
        The processing mode.
    """
    progressUpdated = pyqtSignal(int)
    finished = pyqtSignal(dict, dict)

    def __init__(self, model, mode):
        """
        Initialize the worker with model and mode.
        
        Parameters
        ----------
        model : LCInspectorModel
            The model instance.
        mode : str
            The processing mode.
        """
        super().__init__()
        self.model = model
        self.mode = mode
        
        # Determine optimal number of workers based on system resources
        self.determine_optimal_workers()

    def determine_optimal_workers(self):
        """Determine the optimal number of worker processes based on system resources"""
        cpu_count = os.cpu_count() or 4
        
        # Reserve at least 1 CPU for the main application
        self.process_workers = max(1, cpu_count - 2)
        
        # Check available memory
        mem = psutil.virtual_memory()
        total_mem_gb = mem.total / (1024 ** 3)  # Convert to GB
        
        # Adjust worker count based on available memory
        # Mass spec data can be memory-intensive, so we limit workers if memory is low
        if total_mem_gb < 8:  # Less than 8GB
            self.process_workers = min(self.process_workers, 2)
        elif total_mem_gb < 16:  # Less than 16GB
            self.process_workers = min(self.process_workers, cpu_count - 1)
            
        logger.info(f"Using {self.process_workers} worker processes based on system resources")
        
        # Size of batches to process
        self.batch_size = 5  # Process files in batches of 5

    def process_lc_file(self, lc_file):
        """Process a single LC file"""
        try:
            return LCMeasurement(lc_file)
        except Exception as e:
            logger.error(f"Error processing LC file {lc_file}: {e}")
            return None

    def process_ms_file(self, ms_file, compounds, mass_accuracy):
        """Process a single MS file"""
        try:
            return MSMeasurement(ms_file, compounds, mass_accuracy)
        except Exception as e:
            logger.error(f"Error processing MS file {ms_file}: {e}")
            return None

    def run(self):
        """Run the worker thread with optimized processing."""
        st = time.time()
        lc_results = {}
        ms_results = {}
        
        try:
            total_files = len(self.model.lc_measurements) + len(self.model.ms_measurements)
            if total_files == 0:
                logger.warning("No files to process.")
                return
        except AttributeError:
            logger.error("Model attributes are not properly initialized.")
            return
        
        progress = 0

        def update_progress(increment=1):
            nonlocal progress
            progress += increment
            self.progressUpdated.emit(int(progress / total_files * 100))

        if self.mode not in {"LC/GC-MS", "LC/GC Only", "MS Only"}:
            logger.error(f"ERROR: Invalid argument for process_data(mode): {self.mode}")
            return

        try:
            # Process files in batches to manage memory better
            if self.mode in {"LC/GC-MS", "LC/GC Only"}:
                lc_batches = [list(self.model.lc_measurements.keys())[i:i + self.batch_size] 
                             for i in range(0, len(self.model.lc_measurements), self.batch_size)]
                
                for batch in lc_batches:
                    with ProcessPoolExecutor(max_workers=self.process_workers) as executor:
                        lc_futures = {executor.submit(self.process_lc_file, lc_file): lc_file 
                                     for lc_file in batch}
                        
                        for future in as_completed(lc_futures):
                            try:
                                result = future.result()
                                if result:
                                    lc_results[result.filename] = result
                            except Exception as e:
                                logger.error(f"Error processing LC file: {e}")
                            update_progress()
            
            if self.mode in {"LC/GC-MS", "MS Only"}:
                ms_batches = [list(self.model.ms_measurements.keys())[i:i + self.batch_size] 
                             for i in range(0, len(self.model.ms_measurements), self.batch_size)]
                
                for batch in ms_batches:
                    with ProcessPoolExecutor(max_workers=self.process_workers) as executor:
                        ms_futures = {executor.submit(self.process_ms_file, ms_file, 
                                                     self.model.compounds, 0.0001): ms_file 
                                     for ms_file in batch}
                        
                        for future in as_completed(ms_futures):
                            try:
                                result = future.result()
                                if result:
                                    ms_results[result.filename] = result
                            except Exception as e:
                                logger.error(f"Error processing MS file: {e}")
                            update_progress()
                            
        except Exception as e:
            logger.error(f"Error in processing pool: {e}")
            logger.error(traceback.format_exc())
            # Try to recover by processing remaining files in the main thread
            self.process_remaining_files(lc_results, ms_results)
            
        end_time = time.time()
        processing_time = end_time - st
        logger.info(f"Processed {len(lc_results)} LC files and {len(ms_results)} MS files in {processing_time:.2f} seconds.")
        self.finished.emit(lc_results, ms_results)

    def process_remaining_files(self, lc_results, ms_results):
        """Process any remaining files in the main thread if the parallel processing fails"""
        logger.info("Attempting to process remaining files in the main thread")
        
        if self.mode in {"LC/GC-MS", "LC/GC Only"}:
            for lc_file in self.model.lc_measurements:
                if lc_file not in [result.filename for result in lc_results.values()]:
                    try:
                        result = self.process_lc_file(lc_file)
                        if result:
                            lc_results[result.filename] = result
                    except Exception as e:
                        logger.error(f"Error processing LC file {lc_file} in main thread: {e}")
        
        if self.mode in {"LC/GC-MS", "MS Only"}:
            for ms_file in self.model.ms_measurements:
                if ms_file not in [result.filename for result in ms_results.values()]:
                    try:
                        result = self.process_ms_file(ms_file, self.model.compounds, 0.0001)
                        if result:
                            ms_results[result.filename] = result
                    except Exception as e:
                        logger.error(f"Error processing MS file {ms_file} in main thread: {e}")

# For backward compatibility
Worker = OptimizedWorker
