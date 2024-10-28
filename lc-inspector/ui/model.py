# model.py
import pandas as pd
import concurrent.futures
from pathlib import Path
from alive_progress import alive_bar
from utils.measurements import LCMeasurement, MSMeasurement, Compound
import dill 

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

    def __init__(self):
        self.ms_measurements = []
        self.lc_measurements = []
        self.annotations = []
        self.lc_results = []
        self.ms_results = []

    def process_ms_file(self, ms_file):
        ms_file = MSMeasurement(ms_file, 0.1)
        ms_file.plot()
        return ms_file

    def process_lc_file(self, lc_file):
        lc_file = LCMeasurement(lc_file)
        lc_file.plot()
        return lc_file

    def annotate_ms_file(self, ms_file):
        compound_list = [Compound(name=ion, file=ms_file.filename, ions=ion_list[ion]) for ion in ion_list.keys()]
        ms_file.annotate(compound_list)
        ms_file.plot_annotated()
        return ms_file

    def process_data(self, ms_filelist, lc_filelist):
        
        total_files = len(ms_filelist) + len(lc_filelist)
        self.controller.view.progressBar.setRange(0, total_files)
        self.controller.view.progressBar.setVisible(True)
        self.controller.view.progressBar.setValue(0)

        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures_ms = [executor.submit(self.process_ms_file, ms_file) for ms_file in ms_filelist]
            futures_lc = [executor.submit(self.process_lc_file, lc_file) for lc_file in lc_filelist]
            for future in concurrent.futures.as_completed(futures_ms):
                # BUG: Currently the future.result() raises TypeError: cannot pickle 'View' object 
                # even though View has nothing to do with this? 
                future.result()
            for future in concurrent.futures.as_completed(futures_lc):
                future.result()
            
            self.ms_results = [future.result() for future in futures_ms]
            self.lc_results = [future.result() for future in futures_lc]

        with concurrent.futures.ProcessPoolExecutor() as executor:
                futures = [executor.submit(self.annotate_ms_file, ms_file) for ms_file in self.ms_measurements]
                for future in concurrent.futures.as_completed(futures):
                    future.result()
                
                annotated_ms_measurements = [future.result() for future in futures]

        for lc_file in self.lc_measurements:
            corresponding_ms_file = next((ms_file for ms_file in annotated_ms_measurements if str(ms_file) == str(lc_file)), None)
            if corresponding_ms_file is None:
                print(f"Could not find a matching MS file for {lc_file}. Skipping.")
                continue
            lc_file.annotate(corresponding_ms_file.compounds)
            lc_file.plot_annotated()
            
            for compound in lc_file.compounds:
                for ion in compound.ions.keys():
                    self.results.append({
                        'File': lc_file.filename,
                        'Ion (m/z)': ion,
                        'Compound': compound.name,
                        'RT (min)': compound.ions[ion]['RT'],
                        'MS Intensity (cps)': compound.ions[ion]['MS Intensity'],
                        'LC Intensity (a.u.)': compound.ions[ion]['LC Intensity']
                    })

        df = pd.DataFrame.from_dict(self.results)
        df.to_csv(get_path('results.csv'), index=False)
