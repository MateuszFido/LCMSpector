# model.py
import logging, traceback, multiprocessing, time, sys
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
from scipy.stats import linregress
import pandas as pd
from utils.classes import LCMeasurement, MSMeasurement, Compound
from calculation.calc_conc import calculate_concentration
from utils.loading import load_ms2_library

logger = logging.getLogger(__name__)
class Model:
    """
    The Model class handles the loading, processing, and annotation of LC and MS measurement files.

    Attributes
    ----------
    ms_measurements : list
        A list to store MSMeasurement objects.  
    lc_measurements : list
        A list to store LCMeasurement objects.
    annotations : list
        A list to store annotations for the measurements.
    lc_results : list
        A list to store results from processing LC files.
    ms_results : list
        A list to store results from processing MS files.

    Methods
    -------
    process_ms_file(ms_file)
        Processes and plots an MS file.
    process_lc_file(lc_file)
        Processes and plots an LC file.
    annotate_ms_file(ms_file)
        Annotates and plots an MS file with compounds.
    preprocess_data(ms_filelist, lc_filelist)
        Preprocesses and annotates LC and MS files concurrently.
    """
    
    __slots__ = ['ms_measurements', 'lc_measurements', 'annotations', 'controller', 'compounds', 'library']

    def __init__(self):
        self.lc_measurements = {}
        self.ms_measurements = {}
        self.annotations = []
        self.compounds = []
        self.library = load_ms2_library()
        
    def process_data(self, mode):
        st = time.time()
        lc_results = {}
        ms_results = {}
        total_files = len(self.lc_measurements) + len(self.ms_measurements)
        progress = 0

        def update_progress():
            nonlocal progress
            progress += 1
            self.controller.view.update_progress_bar(int(progress / total_files * 100))

        if mode not in {"LC/GC-MS", "LC/GC Only", "MS Only"}:
            logger.error("ERROR: Invalid argument for process_data(mode): ", mode)
            return

        with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count() - 3) as executor:
            if mode in {"LC/GC-MS", "LC/GC Only"}:
                lc_futures = {executor.submit(LCMeasurement, lc_file): lc_file for lc_file in self.lc_measurements}
            else:
                lc_futures = {}

            if mode in {"LC/GC-MS", "MS Only"}:
                ms_futures = {executor.submit(MSMeasurement, ms_file, self.compounds, 0.0001): ms_file for ms_file in self.ms_measurements}
            else:
                ms_futures = {}

            for future in as_completed(list(lc_futures) + list(ms_futures)):
                result = future.result()
                if future in lc_futures:
                    lc_results[result.filename] = result
                else:
                    ms_results[result.filename] = result
                update_progress()

        logger.info(f"Processed in {time.time() - st}")
        logger.info(f"Size in memory is LC: {sys.getsizeof(lc_results) / (1024 * 1024)} MB, MS: {sys.getsizeof(ms_results) / (1024 * 1024)} MB.")
        return lc_results, ms_results


    def get_plots(self, filename):
        # Find the corresponding MS and LC files
        ms_file = self.ms_measurements.get(filename, None)
        lc_file = self.lc_measurements.get(filename, None)
        return lc_file, ms_file

    def calibrate(self, selected_files):
        for j, (file, concentration) in enumerate(selected_files.items()):
            concentration_value, suffix = (concentration.split(" ") + [None])[:2]
            conversion_factors = {'m': 1e3, 'mm': 1, 'um': 1e-3, 'nm': 1e-6, 'pm': 1e-9}
            concentration = float(concentration_value) * conversion_factors.get(suffix.lower(), 1)
            
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

    def export(self):
        results = []
        for ms_measurement in self.ms_measurements.values():
            for compound in ms_measurement.xics:
                ion_data = zip(compound.ions.keys(), compound.ions.values())
                for ion, data in ion_data:
                    results_dict = {
                        'File': ms_measurement.filename,
                        'Ion (m/z)': ion,
                        'Compound': compound.name,
                        'RT (min)': np.round(data['RT'],3),
                        'MS Intensity (cps)': np.round(np.sum(data['MS Intensity']),0),
                        'LC Intensity (a.u.)': data['LC Intensity']
                        }
                    try:
                        results_dict['Ion name'] = compound.ion_info[ion_data.index((ion, data))]
                    except IndexError:
                        results_dict['Ion name'] = ion
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
