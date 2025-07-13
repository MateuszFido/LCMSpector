"""
Main model class for the LC-Inspector application.

This module provides the main model class for the LC-Inspector application.
It handles the loading, processing, and annotation of LC and MS measurement files.
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

from model.base import BaseModel
from utils.classes import LCMeasurement, MSMeasurement, Compound
from calculation.calc_conc import calculate_concentration
from utils.loading import load_ms2_library, load_ms2_data
from calculation.workers_refactored import Worker

logger = logging.getLogger(__name__)

class LCInspectorModel(BaseModel):
    """
    The LCInspectorModel class handles the loading, processing, and annotation of LC and MS measurement files.

    This class is responsible for managing the data and business logic of the application.
    It uses an event system to communicate with the controller.

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
    """
    
    __slots__ = ['ms_measurements', 'lc_measurements', 'annotations', 'compounds', 'library', 'worker']

    def __init__(self):
        """Initialize the model with empty data structures and load the MS2 library."""
        super().__init__()
        self.lc_measurements = {}
        self.ms_measurements = {}
        self.annotations = []
        self.compounds = []
        self.library = load_ms2_library()
        if self.library:
            logger.info("MS2 library loaded.")
        else:
            logger.error("No MS2 library found. Please make sure a corresponding library in .msp format is in the 'resources' folder.")
        self.worker = None
        logger.info(f"Current thread: {threading.current_thread().name}")
        logger.info(f"Current process: {os.getpid()}")
        
    def process(self, mode):
        """
        Initiate the data processing workflow.
        
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
        self.worker = Worker(self, mode)
        
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

    def calibrate(self, selected_files):
        """
        Calibrate the concentrations for selected files.
        
        Parameters
        ----------
        selected_files : dict
            A dictionary mapping filenames to concentration values.
        """
        for j, (file, concentration) in enumerate(selected_files.items()):
            if not concentration.strip():
                continue
            concentration_value, suffix = (concentration.split(" ") + [None])[:2]
            conversion_factors = {'m': 1e3, 'mm': 1, 'um': 1e-3, 'nm': 1e-9, 'pm': 1e-12}
            concentration = float(concentration_value) * conversion_factors.get(suffix and suffix.lower(), 1)
            
            ms_file = self.ms_measurements.get(file)
            if not ms_file or not ms_file.xics:
                logger.error(f"No xics found for file {file}.")
                continue

            for i, compound in enumerate(self.compounds):
                if not compound.ions:
                    logger.error(f"No ions found for compound {compound.name}.")
                    continue
                compound_intensity = sum(
                    np.round(np.sum(ms_file.xics[i].ions[ion]['MS Intensity'][1]), 0)
                    for ion in compound.ions.keys()
                )
                compound.calibration_curve[concentration] = compound_intensity
                
                if j == len(selected_files) - 1:
                    slope, intercept, r_value, p_value, std_err = linregress(
                        list(compound.calibration_curve.keys()),
                        list(compound.calibration_curve.values())
                    )
                    compound.calibration_parameters = {
                        'slope': slope, 'intercept': intercept, 'r_value': r_value,
                        'p_value': p_value, 'std_err': std_err
                    }

        for ms_file in self.ms_measurements.values():
            for ms_compound, model_compound in zip(ms_file.xics, self.compounds):
                try:
                    ms_compound.concentration = sum(
                        np.round(np.sum(ms_compound.ions[ion]['MS Intensity'][1]), 0)
                        for ion in ms_compound.ions.keys()
                    )
                    ms_compound.concentration = calculate_concentration(
                        ms_compound.concentration, model_compound.calibration_parameters
                    )
                    ms_compound.calibration_parameters = model_compound.calibration_parameters
                except Exception as e:
                    logger.error(f"Error calibrating file {file}: {traceback.format_exc()}")
        
        # Log the compounds before emitting the event
        logger.info(f"Calibration finished. Emitting event with {len(self.compounds)} compounds.")
        for compound in self.compounds:
            logger.info(f"Compound: {compound.name}")
            
        # Emit an event to indicate that calibration has finished
        self.emit('calibration_finished', self.compounds)

    def find_ms2_precursors(self, compound_index):
        """
        Find MS2 precursors for a compound.
        
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
            
        for ion in compound.ions.keys():
            try:
                library_entry = next((l for l in self.library.values() 
                                    if (precursor_mz := next((line.split(' ')[1] for line in l if 'PrecursorMZ:' in line), None)) is not None 
                                    and np.isclose(float(precursor_mz), float(ion), atol=0.005)), None)
                if library_entry:
                    logger.info(f"Precursor m/z {ion} found for {compound.name} in the library.")
                    library_entries.add(tuple(library_entry))
                else:
                    logger.debug(f"Library entry not found for {compound.name}: {ion}")
            except StopIteration:
                logger.debug(f"Library entry not found for {compound.name}: {ion}")
                break
                
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
        Export the results to a pandas DataFrame.
        
        Returns
        -------
        pd.DataFrame
            A DataFrame containing the results.
        """
        results = []
        for ms_measurement in self.ms_measurements.values():
            for compound in ms_measurement.xics:
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
                    results.append(results_dict)
        df = pd.DataFrame(results)
        
        # Emit an event to indicate that export has finished
        self.emit('export_finished', df)
        
        return df
