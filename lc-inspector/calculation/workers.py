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
import gc
import time

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

    @staticmethod
    def process_lc_file(lc_file):
        """Process a single LC file"""
        try:
            return LCMeasurement(lc_file)
        except Exception as e:
            logger.error(f"Error processing LC file {lc_file}: {e}")
            return None

    @staticmethod
    def process_ms_file(ms_file, compounds, mass_accuracy):
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
            # Ensure lc_measurements and ms_measurements are properly initialized
            if not hasattr(self.model, 'lc_measurements'):
                self.model.lc_measurements = []
            if not hasattr(self.model, 'ms_measurements'):
                self.model.ms_measurements = []
                
            # Calculate total files to process
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
                # Convert list to dictionary if needed
                if isinstance(self.model.lc_measurements, list):
                    lc_files = {file_path: os.path.basename(file_path) for file_path in self.model.lc_measurements}
                else:
                    lc_files = self.model.lc_measurements
                
                # Create batches from the file paths
                lc_keys = list(lc_files.keys())
                lc_batches = [lc_keys[i:i + self.batch_size] 
                             for i in range(0, len(lc_keys), self.batch_size)]
                
                for batch in lc_batches:
                    with ProcessPoolExecutor(max_workers=self.process_workers) as executor:
                        lc_futures = {executor.submit(OptimizedWorker.process_lc_file, lc_file): lc_file 
                                     for lc_file in batch}
                        
                        for future in as_completed(lc_futures):
                            try:
                                result = future.result()
                                if result:
                                    lc_results[result.filename] = result
                            except Exception as e:
                                logger.error(f"Error processing LC file: {traceback.format_exception(type(err), e, e.__traceback__)}")
                            update_progress()
            
            if self.mode in {"LC/GC-MS", "MS Only"}:
                # Convert list to dictionary if needed
                if isinstance(self.model.ms_measurements, list):
                    ms_files = {file_path: os.path.basename(file_path) for file_path in self.model.ms_measurements}
                else:
                    ms_files = self.model.ms_measurements
                
                # Create batches from the file paths
                ms_keys = list(ms_files.keys())
                ms_batches = [ms_keys[i:i + self.batch_size] 
                             for i in range(0, len(ms_keys), self.batch_size)]
                
                # Process MS files sequentially to avoid serialization issues
                logger.info("Processing MS files sequentially to avoid serialization issues")
                for batch in ms_batches:
                    for ms_file in batch:
                        try:
                            # Process directly without multiprocessing
                            result = OptimizedWorker.process_ms_file(ms_file, self.model.compounds, 0.0001)
                            if result:
                                ms_results[result.filename] = result
                                logger.info(f"Successfully processed MS file: {result.filename}")
                            else:
                                logger.error(f"Failed to process MS file: {ms_file}")
                        except Exception as e:
                            logger.error(f"Error processing MS file {ms_file}: {traceback.format_exception(type(err), e, e.__traceback__)}")
                        update_progress()
                            
        except Exception as e:
            logger.error(f"Error in processing pool: {traceback.format_exc()}")
            # Try to recover by processing remaining files in the main thread
            self.process_remaining_files(lc_results, ms_results)
            
        end_time = time.time()
        processing_time = end_time - st
        logger.info(f"Processed {len(lc_results)} LC files and {len(ms_results)} MS files in {processing_time:.2f} seconds.")
        
        # Important: store results in instance variables that will be accessed directly by the model
        self.lc_results = lc_results
        self.ms_results = ms_results
        
        # Verify MS data is fully loaded before signaling completion
        for filename, ms_file in ms_results.items():
            if ms_file.data is None:
                logger.error(f"MS data is None for {filename}")
            else:
                logger.info(f"MS data for {filename} contains {len(ms_file.data)} scans, memory address: {id(ms_file.data)}")
                # Log first few scan IDs to identify the data
                scan_ids = [scan.get('id', 'No ID') for scan in ms_file.data[:3]]
                logger.info(f"First few scan IDs for {filename}: {scan_ids}")
                
            if ms_file.xics is None:
                logger.error(f"XICs is None for {filename}")
            else:
                logger.info(f"XICs for {filename} contains {len(ms_file.xics)} compounds, memory address: {id(ms_file.xics)}")
                # Log compound names to identify the XICs
                compound_names = [compound.name for compound in ms_file.xics[:3]]
                logger.info(f"First few compound names for {filename}: {compound_names}")
    
        # Log number of objects tracked by garbage collector
        gc_objects_before = len(gc.get_objects())
        logger.info(f"Number of objects tracked by GC before signal emission: {gc_objects_before}")
        
        # Check for gc.garbage collection
        logger.info(f"Current gc.garbage size: {len(gc.garbage)}")
        
        # Hold references to MS data in a way that survives signal/slot transfer
        for filename, ms_file in ms_results.items():
            # Ensure the data field has a strong reference to its data
            if hasattr(ms_file, '_data') and ms_file._data is not None:
                # Reassign to itself to ensure strong reference
                ms_file._data = ms_file._data
                logger.info(f"Strengthened reference to MS data for {filename}, size: {len(ms_file._data)}")
            
            # Ensure the xics field has a strong reference
            if hasattr(ms_file, '_xics') and ms_file._xics is not None:
                # Reassign to itself to ensure strong reference
                ms_file._xics = ms_file._xics
                logger.info(f"Strengthened reference to XICs for {filename}, size: {len(ms_file._xics)}")
        
        # Set these as attributes on the worker itself to maintain references
        # This ensures the data persists until the model can safely store it
        self._persisted_lc_results = lc_results
        self._persisted_ms_results = ms_results
        
        # Signal completion
        logger.info(f"Emitting finished signal with lc_results ({id(lc_results)}) and ms_results ({id(ms_results)})")
        self.finished.emit(lc_results, ms_results)
        
        # Track objects after signal emission to see if anything changed
        time.sleep(0.1)  # Give a small delay to ensure signal processing
        gc_objects_after = len(gc.get_objects())
        logger.info(f"Number of objects tracked by GC after signal emission: {gc_objects_after}")
        logger.info(f"GC objects difference: {gc_objects_after - gc_objects_before}")

    def process_remaining_files(self, lc_results, ms_results):
        """Process any remaining files in the main thread if the parallel processing fails"""
        logger.info("Attempting to process remaining files in the main thread")
        
        if self.mode in {"LC/GC-MS", "LC/GC Only"}:
            # Get the list of file paths
            lc_files = self.model.lc_measurements
            if isinstance(lc_files, dict):
                lc_files = list(lc_files.keys())
                
            for lc_file in lc_files:
                if lc_file not in [result.filename for result in lc_results.values()]:
                    try:
                        result = OptimizedWorker.process_lc_file(lc_file)
                        if result:
                            lc_results[result.filename] = result
                    except Exception as e:
                        logger.error(f"Error processing LC file {lc_file} in main thread: {e}")
        
        if self.mode in {"LC/GC-MS", "MS Only"}:
            # Get the list of file paths
            ms_files = self.model.ms_measurements
            if isinstance(ms_files, dict):
                ms_files = list(ms_files.keys())
                
            for ms_file in ms_files:
                if ms_file not in [result.filename for result in ms_results.values()]:
                    try:
                        result = OptimizedWorker.process_ms_file(ms_file, self.model.compounds, 0.0001)
                        if result:
                            ms_results[result.filename] = result
                    except Exception as e:
                        logger.error(f"Error processing MS file {ms_file} in main thread: {e}")

# For backward compatibility
Worker = OptimizedWorker
