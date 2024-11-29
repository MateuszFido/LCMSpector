# model.py
import sys, logging, traceback, re
import numpy as np
import concurrent.futures
from pathlib import Path
from utils.measurements import LCMeasurement, MSMeasurement, Compound

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
    
    __slots__ = ['ms_measurements', 'lc_measurements', 'annotations', 'controller', 'compounds']

    def __init__(self):
        self.lc_measurements = {}
        self.ms_measurements = {}
        self.annotations = []
        self.compounds = []
        
    def process_data(self):
        # TODO: Implement concurrency
        lc_results = {}
        ms_results = {}
        total_files = len(self.lc_measurements) + len(self.ms_measurements)
        progress = 0

        for lc_file in self.lc_measurements:
            lc_result = LCMeasurement(lc_file)
            progress += 1
            self.controller.view.update_progress_bar(int(progress / total_files * 100))
            lc_results[lc_result.filename] = lc_result

        for ms_file in self.ms_measurements:
            ms_result = MSMeasurement(ms_file, self.compounds, 0.0001)
            progress += 1
            self.controller.view.update_progress_bar(int(progress / total_files * 100))
            ms_results[ms_result.filename] = ms_result

        return lc_results, ms_results

    def get_plots(self, filename):
        # Find the corresponding MS and LC files
        ms_file = self.ms_measurements.get(filename, None)
        lc_file = self.lc_measurements.get(filename, None)
        return lc_file, ms_file

    def calibrate(self, selected_files):
        for file in selected_files:
            concentration = selected_files[file].split(" ")
            try:
                suffix = concentration[1]
            except IndexError:
                continue
            if suffix == "mM":
                concentration = float(concentration[0])*0.001
            elif suffix == "uM":
                concentration = float(concentration[0])*0.000001
            elif suffix == "nM":
                concentration = float(concentration[0])*0.000000001
            elif suffix == "pM":
                concentration = float(concentration[0])*0.000000000001
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
                else:
                    logger.error(f"No xics found for file {file}.")
                    continue
            except Exception as e:
                    logger.error(f"Error calibrating file {file}: {traceback.format_exc()}")

    def save_results(self, lc_file):
        # TODO: Implement
        results = []
        for compound in lc_file.compounds:
            for ion in compound.ions.keys():
                results.append({
                    'File': lc_file.filename,
                    'Ion (m/z)': ion,
                    'Compound': compound.name,
                    'RT (min)': compound.ions[ion]['RT'],
                    'MS Intensity (cps)': compound.ions[ion]['MS Intensity'],
                    'LC Intensity (a.u.)': compound.ions[ion]['LC Intensity']
                })
        df = pd.DataFrame(results)
        df.to_csv('results.csv', index=False)
        
        return
