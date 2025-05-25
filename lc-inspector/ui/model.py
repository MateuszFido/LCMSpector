# model.py
import logging, traceback, multiprocessing, time, sys
import numpy as np
from scipy.stats import linregress
import pandas as pd
from utils.classes import LCMeasurement, MSMeasurement, Compound
from calculation.calc_conc import calculate_concentration
from utils.loading import load_ms2_library, load_ms2_data
from calculation.workers import Worker

logger = logging.getLogger(__name__)
class Model:
    """
    The Model class handles the loading, processing, and annotation of LC and MS measurement files.

    Attributes
    ----------
    ms_measurements : dict
        -- A dictionary to store MSMeasurement objects.
    lc_measurements : dict
        -- A dictionary to store LCMeasurement objects.
    annotations : list
        -- A list to store annotations for the measurements.
    compounds : list
        -- A list of Compound objects representing targeted results.
    library : dict
        -- A dictionary representing the MS2 library loaded from external resources.
    worker : Worker or None
        -- A worker instance for handling concurrent processing tasks.

    Methods
    -------
    - process_data(mode):
        Initiates the data processing workflow.
    - get_plots(filename):
        Retrieves the corresponding LC and MS files for a given filename.
    - calibrate(selected_files):
        Calibrates the concentrations for selected files.
    """
    
    __slots__ = ['ms_measurements', 'lc_measurements', 'annotations', 'controller', 'compounds', 'library', 'worker']

    def __init__(self):
        self.lc_measurements = {}
        self.ms_measurements = {}
        self.annotations = []
        self.compounds = []
        self.library = load_ms2_library()
        self.worker = None
        
    def process_data(self, mode):
        self.worker = Worker(self, mode)
        self.worker.progressUpdated.connect(self.controller.view.update_progress_bar)
        self.worker.finished.connect(self.controller.on_processing_finished)
        self.worker.start()

    def get_plots(self, filename):
        # Find the corresponding MS and LC files
        ms_file = self.ms_measurements.get(filename, None)
        lc_file = self.lc_measurements.get(filename, None)
        return lc_file, ms_file

    def calibrate(self, selected_files):
        for j, (file, concentration) in enumerate(selected_files.items()):
            concentration_value, suffix = (concentration.split(" ") + [None])[:2]
            conversion_factors = {'m': 1e3, 'mm': 1, 'um': 1e-3, 'nm': 1e-6, 'pm': 1e-9}
            concentration = float(concentration_value) * conversion_factors.get(suffix and suffix.lower(), 1)
            
            ms_file = self.ms_measurements.get(file)
            if not ms_file or not ms_file.xics:
                logger.error(f"No xics found for file {file}.")
                continue

            for i, compound in enumerate(self.compounds):
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
                ms_compound.concentration = sum(
                    np.round(np.sum(ms_compound.ions[ion]['MS Intensity'][1]), 0)
                    for ion in ms_compound.ions.keys()
                )
                try:
                    ms_compound.concentration = calculate_concentration(
                        ms_compound.concentration, model_compound.calibration_parameters
                    )
                    ms_compound.calibration_parameters = model_compound.calibration_parameters
                except Exception:
                    logger.error(f"Error calibrating file {file}: {traceback.format_exc()}")

    def find_ms2_precursors(self):
        for ms_file in self.ms_measurements.values():
            ms_file.ms2_data = load_ms2_data(ms_file.path, ms_file.xics, ms_file.mass_accuracy)

    def export(self):
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
        return df
