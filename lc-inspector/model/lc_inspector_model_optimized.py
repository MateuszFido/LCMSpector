"""
Optimized model class for the LC-Inspector application.

This module provides an optimized model class for the LC-Inspector application.
It handles the loading, processing, and annotation of LC and MS measurement files
with improved performance for large files.
"""

import logging
import traceback
import multiprocessing
import time
import threading
import os
import numpy as np
from scipy.stats import linregress
import pandas as pd
import gc
import joblib
import tempfile
from pathlib import Path

from model.base import BaseModel
from utils.classes_optimized import LCMeasurement, MSMeasurement, Compound
from calculation.calc_conc import calculate_concentration
from utils.loading_optimized import load_ms2_library, load_ms2_data
from calculation.workers_optimized import OptimizedWorker
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class LCInspectorModelOptimized(BaseModel):
    """
    The optimized LCInspectorModel class handles the loading, processing, and annotation 
    of LC and MS measurement files with improved performance.

    This class implements:
    1. Memory-efficient data handling
    2. Parallel processing
    3. Caching of intermediate results
    4. Efficient data structures
    5. Lazy loading of resources

    Attributes
    ----------
    ms_measurements : dict
        A dictionary to store MSMeasurement objects.
    lc_measurements : dict
        A dictionary to store LCMeasurement objects.
    annotations : list
        A list to store annotations for the measurements.
    compounds : list
        A list of Compound objects representing targeted results.
    library : dict
        A dictionary representing the MS2 library loaded from external resources.
    worker : Worker or None
        A worker instance for handling concurrent processing tasks.
    cache_dir : Path
        Directory for caching results
    """
    
    __slots__ = [
        'ms_measurements', 'lc_measurements', 'annotations', 'compounds', 
        'library', 'worker', 'cache_dir', '_library_loaded'
    ]

    def __init__(self):
        """Initialize the model with empty data structures and set up caching."""
        super().__init__()
        self.lc_measurements = {}
        self.ms_measurements = {}
        self.annotations = []
        self.compounds = []
        self._library_loaded = False
        self.library = {}  # Lazy-loaded when needed
        self.worker = None
        self.cache_dir = Path(tempfile.gettempdir()) / "lc_inspector_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        
        logger.info(f"Initialized optimized model with cache directory: {self.cache_dir}")
        logger.info(f"Current thread: {threading.current_thread().name}")
        logger.info(f"Current process: {os.getpid()}")
    
    @property
    def ms2_library(self):
        """Lazy-load the MS2 library only when needed"""
        if not self._library_loaded:
            self.library = load_ms2_library()
            self._library_loaded = True
            if self.library:
                logger.info("MS2 library loaded.")
            else:
                logger.error("No MS2 library found. Please make sure a corresponding library in .msp format is in the 'resources' folder.")
        return self.library
        
    def process(self, mode):
        """
        Initiate the data processing workflow with improved performance.
        
        Parameters
        ----------
        mode : str
            The processing mode to use. Can be "LC/GC-MS", "LC/GC Only", or "MS Only".
        """
        # safety check 
        if self.worker and self.worker.isRunning():
            logger.warning("Worker thread is already running. Aborting.")
            return

        # Create a new worker and connect its signals
        self.worker = OptimizedWorker(self, mode)
        
        # Connect worker signals to model events
        self.worker.progressUpdated.connect(lambda value: self.emit('progress_updated', value))
        self.worker.finished.connect(self._on_processing_finished)
        
        # Start the worker
        self.worker.start()
        
        # Emit an event to indicate that processing has started
        self.emit('processing_started')

    def _on_processing_finished(self, lc_results, ms_results):
        """
        Handle the completion of the processing task.
        
        Parameters
        ----------
        lc_results : dict
            The LC measurement results.
        ms_results : dict
            The MS measurement results.
        """
        self.lc_measurements = lc_results
        self.ms_measurements = ms_results
        
        # Force garbage collection to release memory from processing
        gc.collect()
        
        # Emit an event to indicate that processing has finished
        self.emit('processing_finished', {'lc_results': lc_results, 'ms_results': ms_results})

    def get_plots(self, filename):
        """
        Retrieve the corresponding LC and MS files for a given filename.
        
        Parameters
        ----------
        filename : str
            The filename to look for.
            
        Returns
        -------
        tuple
            A tuple containing the LC and MS files.
        """
        # Find the corresponding MS and LC files
        ms_file = self.ms_measurements.get(filename, None)
        lc_file = self.lc_measurements.get(filename, None)
        return lc_file, ms_file

    def process_calibration_data(self, file, concentration, compound, ms_file):
        """Process calibration data for a single file and compound (for parallel processing)"""
        if not compound.ions:
            logger.error(f"No ions found for compound {compound.name}.")
            return None, None
            
        try:
            compound_intensity = sum(
                np.round(np.sum(ms_file.xics[compound.name].ions[ion]['MS Intensity'][1]), 0)
                for ion in compound.ions.keys()
            )
            return compound, {concentration: compound_intensity}
        except Exception as e:
            logger.error(f"Error processing calibration for {file}, compound {compound.name}: {e}")
            return None, None

    def calibrate(self, selected_files):
        """
        Calibrate the concentrations for selected files using parallel processing.
        
        Parameters
        ----------
        selected_files : dict
            A dictionary mapping filenames to concentration values.
        """
        # Process files in parallel
        with ThreadPoolExecutor(max_workers=min(os.cpu_count(), 4)) as executor:
            futures = []
            
            for j, (file, concentration) in enumerate(selected_files.items()):
                if not concentration.strip():
                    continue
                    
                concentration_value, suffix = (concentration.split(" ") + [None])[:2]
                conversion_factors = {'m': 1e3, 'mm': 1, 'um': 1e-3, 'nm': 1e-9, 'pm': 1e-12}
                conc_value = float(concentration_value) * conversion_factors.get(suffix and suffix.lower(), 1)
                
                ms_file = self.ms_measurements.get(file)
                if not ms_file or not ms_file.xics:
                    logger.error(f"No xics found for file {file}.")
                    continue

                for i, compound in enumerate(self.compounds):
                    futures.append(
                        executor.submit(
                            self.process_calibration_data, 
                            file, conc_value, compound, ms_file
                        )
                    )
            
            # Collect results
            for future in futures:
                compound, result = future.result()
                if compound and result:
                    concentration, intensity = next(iter(result.items()))
                    compound.calibration_curve[concentration] = intensity
        
        # Calculate calibration parameters for each compound
        for compound in self.compounds:
            if compound.calibration_curve:
                try:
                    slope, intercept, r_value, p_value, std_err = linregress(
                        list(compound.calibration_curve.keys()),
                        list(compound.calibration_curve.values())
                    )
                    compound.calibration_parameters = {
                        'slope': slope, 'intercept': intercept, 'r_value': r_value,
                        'p_value': p_value, 'std_err': std_err
                    }
                except Exception as e:
                    logger.error(f"Error calculating calibration parameters for {compound.name}: {e}")
                    compound.calibration_parameters = {
                        'slope': 0, 'intercept': 0, 'r_value': 0,
                        'p_value': 0, 'std_err': 0
                    }
        
        # Apply calibration to all MS files
        with ThreadPoolExecutor(max_workers=min(os.cpu_count(), 4)) as executor:
            futures = []
            
            for ms_file in self.ms_measurements.values():
                for ms_compound, model_compound in zip(ms_file.xics, self.compounds):
                    futures.append(
                        executor.submit(
                            self.apply_calibration,
                            ms_compound, model_compound
                        )
                    )
            
            # Wait for all calibrations to complete
            for future in futures:
                future.result()
        
        # Log the compounds before emitting the event
        logger.info(f"Calibration finished. Emitting event with {len(self.compounds)} compounds.")
        for compound in self.compounds:
            logger.info(f"Compound: {compound.name}")
            
        # Emit an event to indicate that calibration has finished
        self.emit('calibration_finished', self.compounds)

    def apply_calibration(self, ms_compound, model_compound):
        """Apply calibration to a single compound (for parallel processing)"""
        try:
            ms_compound.concentration = sum(
                np.round(np.sum(ms_compound.ions[ion]['MS Intensity'][1]), 0)
                for ion in ms_compound.ions.keys()
            )
            ms_compound.concentration = calculate_concentration(
                ms_compound.concentration, model_compound.calibration_parameters
            )
            ms_compound.calibration_parameters = model_compound.calibration_parameters
            return True
        except Exception as e:
            logger.error(f"Error applying calibration to compound {ms_compound.name}: {e}")
            return False

    def find_ms2_precursors(self, compound_index):
        """
        Find MS2 precursors for a compound with optimized performance.
        
        Parameters
        ----------
        compound_index : int
            The index of the compound to find precursors for.
            
        Returns
        -------
        dict
            A dictionary of library entries.
        """
        compound = self.compounds[compound_index]
        library_entries = set()
        
        # safety check
        if not compound:
            logger.error("No compound selected.")
            return {}

        # Use parallel processing to search library
        with ThreadPoolExecutor(max_workers=min(os.cpu_count(), 4)) as executor:
            futures = []
            
            for ion in compound.ions.keys():
                futures.append(
                    executor.submit(
                        self.search_library_for_ion,
                        ion, compound.name
                    )
                )
            
            # Collect results
            for future in futures:
                result = future.result()
                if result:
                    library_entries.add(result)
                
        # Complex dict comprehension to format the library entries
        library_entries = {entry[0].split("Name: ", 1)[1].partition('\n')[0] \
            + (f"m/z ({round(float(next((line.split(' ')[1] for line in entry \
                if 'PrecursorMZ:' in line), None)), 4)})" if \
                    (precursor_mz := next((line.split(' ')[1] \
                        for line in entry if 'PrecursorMZ:' in line), None)) else "").strip(): \
                            entry for entry in library_entries}
        
        # Emit an event to indicate that MS2 precursors have been found
        self.emit('ms2_precursors_found', {'compound_index': compound_index, 'library_entries': library_entries})
        
        return library_entries

    def search_library_for_ion(self, ion, compound_name):
        """Search the library for a specific ion (for parallel processing)"""
        try:
            library_entry = next((l for l in self.ms2_library.values() 
                                if (precursor_mz := next((line.split(' ')[1] for line in l if 'PrecursorMZ:' in line), None)) is not None 
                                and np.isclose(float(precursor_mz), float(ion), atol=0.005)), None)
            if library_entry:
                logger.info(f"Precursor m/z {ion} found for {compound_name} in the library.")
                return tuple(library_entry)
            else:
                logger.debug(f"Library entry not found for {compound_name}: {ion}")
                return None
        except StopIteration:
            logger.debug(f"Library entry not found for {compound_name}: {ion}")
            return None
        except Exception as e:
            logger.error(f"Error searching library for ion {ion}: {e}")
            return None

    def find_ms2_in_file(self, ms_file, compound_index):
        """
        Find MS2 data in a file for a compound.
        
        Parameters
        ----------
        ms_file : MSMeasurement
            The MS file to search in.
        compound_index : int
            The index of the compound to find MS2 data for.
        """
        current_compound = self.compounds[compound_index]
        current_compound_in_ms_file = next((c for c in ms_file.xics if c.name == current_compound.name), None)
        load_ms2_data(ms_file.path, current_compound_in_ms_file, ms_file.mass_accuracy)
        
        # Emit an event to indicate that MS2 data has been found
        self.emit('ms2_in_file_found', {'ms_file': ms_file, 'compound_index': compound_index})

    def export(self):
        """
        Export the results to a pandas DataFrame with optimized performance.
        
        Returns
        -------
        pd.DataFrame
            A DataFrame containing the results.
        """
        results = []
        
        # Use parallel processing to generate result rows
        with ThreadPoolExecutor(max_workers=min(os.cpu_count(), 4)) as executor:
            futures = []
            
            for ms_measurement in self.ms_measurements.values():
                for compound in ms_measurement.xics:
                    futures.append(
                        executor.submit(
                            self.generate_export_rows,
                            ms_measurement, compound
                        )
                    )
            
            # Collect results
            for future in futures:
                rows = future.result()
                if rows:
                    results.extend(rows)
        
        df = pd.DataFrame(results)
        
        # Emit an event to indicate that export has finished
        self.emit('export_finished', df)
        
        return df

    def generate_export_rows(self, ms_measurement, compound):
        """Generate export data rows for a compound (for parallel processing)"""
        rows = []
        try:
            ion_data = zip(compound.ions.keys(), compound.ions.values(), compound.ion_info)
            for ion, data, ion_name in ion_data:
                results_dict = {
                    'File': ms_measurement.filename,
                    'Ion (m/z)': ion,
                    'Compound': compound.name,
                    'RT (min)': np.round(data['RT'],3),
                    'MS Intensity (cps)': np.round(np.sum(data['MS Intensity']),0),
                    'LC Intensity (a.u.)': data['LC Intensity'],
                    'Ion name': str(ion_name).strip() if ion_name else ion
                    }
                try:
                    results_dict['Concentration (mM)'] = compound.concentration
                    results_dict['Calibration slope'] = compound.calibration_parameters['slope']
                    results_dict['Calibration intercept'] = compound.calibration_parameters['intercept']
                except Exception as e:
                    logger.error(f"Error exporting concentration information for {ms_measurement.filename}: {e}")
                    results_dict['Concentration (mM)'] = 0
                    results_dict['Calibration slope'] = 0
                    results_dict['Calibration intercept'] = 0
                rows.append(results_dict)
            return rows
        except Exception as e:
            logger.error(f"Error generating export rows for {compound.name} in {ms_measurement.filename}: {e}")
            return []

    def __del__(self):
        """Clean up resources when the model is deleted"""
        # Clear any running worker
        if self.worker and self.worker.isRunning():
            try:
                self.worker.terminate()
                self.worker.wait()
            except:
                pass
        
        # Force garbage collection
        gc.collect()

# For backward compatibility
LCInspectorModel = LCInspectorModelOptimized
