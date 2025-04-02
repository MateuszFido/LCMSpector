# model.py
import logging, traceback, multiprocessing, time
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
        if mode == "LC/GC-MS":
            with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()-3) as executor: 
                futures = [executor.submit(LCMeasurement, lc_file) for lc_file in self.lc_measurements] + \
                          [executor.submit(MSMeasurement, ms_file, self.compounds, 0.0001) for ms_file in self.ms_measurements]
                for future in as_completed(futures):
                    result = future.result()
                    if isinstance(result, LCMeasurement):
                        lc_results[result.filename] = result
                    else:
                        ms_results[result.filename] = result
                    progress += 1
                    self.controller.view.update_progress_bar(int(progress / total_files * 100))
            logger.info(f"Processed in {time.time() - st}")
            return lc_results, ms_results
        elif mode == "LC/GC Only":
            with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()-3) as executor: 
                futures = [executor.submit(LCMeasurement, lc_file) for lc_file in self.lc_measurements]
                for future in as_completed(futures):
                    result = future.result()
                    lc_results[result.filename] = result
                    progress += 1
                    self.controller.view.update_progress_bar(int(progress / total_files * 100))
            logger.info(f"Processed in {time.time() - st}")
            return lc_results, ms_results
        elif mode == "MS Only":
            with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()-3) as executor:
                futures = [executor.submit(MSMeasurement, ms_file, self.compounds, 0.0001) for ms_file in self.ms_measurements]
                for future in as_completed(futures):
                    result = future.result()
                    ms_results[result.filename] = result
                    progress += 1
                    self.controller.view.update_progress_bar(int(progress / total_files * 100))
            logger.info(f"Processed in {time.time() - st}")
            return lc_results, ms_results
        else: 
            logger.error("ERROR: Invalid argument for process_data(mode): ", mode)
            return

    def get_plots(self, filename):
        # Find the corresponding MS and LC files
        ms_file = self.ms_measurements.get(filename, None)
        lc_file = self.lc_measurements.get(filename, None)
        return lc_file, ms_file

    def calibrate(self, selected_files):
        j=0
        for file, concentration in selected_files.items(): 
            concentration = concentration.split(" ")
            try:
                suffix = concentration[1].lower()
            except IndexError:
                suffix = None
            if suffix == "m":
                concentration = float(concentration[0])*1e3
            elif suffix == "mm":
                concentration = float(concentration[0]) # Default to mmol/L
            elif suffix == "um":
                concentration = float(concentration[0])*1e-3
            elif suffix == "nm":
                concentration = float(concentration[0])*1e-6
            elif suffix == "pm":
                concentration = float(concentration[0])*1e-9
            else:
                concentration = float(concentration[0])
            try: 
                ms_file = self.ms_measurements.get(file)
                if ms_file.xics:
                    for i, compound in enumerate(self.compounds):
                        compound_intensity = 0
                        for ion in compound.ions.keys():
                            compound_intensity += np.round(np.sum(ms_file.xics[i].ions[ion]['MS Intensity'][1]), 0)
                        compound.calibration_curve[concentration] = compound_intensity
                        if j == len(selected_files)-1:
                            slope, intercept, r_value, p_value, std_err = linregress(list(compound.calibration_curve.keys()), list(compound.calibration_curve.values()))
                            compound.calibration_parameters = {'slope': slope, 'intercept': intercept, 'r_value': r_value, 'p_value': p_value, 'std_err': std_err}
                else:
                    logger.error(f"No xics found for file {file}.")
                    continue
            except Exception:
                    logger.error(f"Error calibrating file {file}: {traceback.format_exc()}")
            j += 1
        for ms_file in self.ms_measurements.values():
            for ms_compound, model_compound in zip(ms_file.xics, self.compounds):
                ms_compound.concentration = 0
                for ion in ms_compound.ions.keys():
                    ion_intensity = np.round(np.sum(ms_compound.ions[ion]['MS Intensity'][1]), 0)
                    ms_compound.concentration += ion_intensity
                try:
                    ms_compound.concentration = calculate_concentration(ms_compound.concentration, model_compound.calibration_parameters)
                    ms_compound.calibration_parameters = model_compound.calibration_parameters
                except Exception:
                    logger.error(f"Error calibrating file {file}: {traceback.format_exc()}")
                    continue

    def export(self):
        results = []
        for ms_measurement in self.ms_measurements.values():
            for compound in ms_measurement.xics:
                for i, ion in enumerate(compound.ions.keys()):
                    results.append({
                        'File': ms_measurement.filename,
                        'Ion (m/z)': ion,
                        'Ion name': compound.ion_info[i],
                        'Compound': compound.name,
                        'RT (min)': np.round(compound.ions[ion]['RT'],3),
                        'MS Intensity (cps)': np.round(np.sum(compound.ions[ion]['MS Intensity']),0),
                        'LC Intensity (a.u.)': compound.ions[ion]['LC Intensity'],
                        'Concentration (mM)': compound.concentration,
                        'Slope': compound.calibration_parameters['slope'],
                        'Intercept': compound.calibration_parameters['intercept'],
                    })
        df = pd.DataFrame(results)
        return df