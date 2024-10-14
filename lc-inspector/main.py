from evaluation.calibration_curves import calibrate
from evaluation.calc_conc import calculate_concentration
from evaluation.peaks import assign_peaks
from utils.loading import load_absorbance_data, load_annotated_peaks
from utils.preprocessing import baseline_correction
import time, csv, re, sys, os
from pathlib import Path
from alive_progress import alive_bar
from evaluation.annotation import annotate_XICs
from utils.sorting import get_path, check_data
from utils.measurements import LCMeasurement, MSMeasurement, Compound
import pandas as pd
from settings import BASE_PATH
import multiprocessing

def run():
    """
    Runs the main analysis pipeline for HPLC/UPLC data.
    
    This function performs the following steps:
    1. Determines the file path to the directory where the script is located.
    2. Supplies the expected peak list, in order of elution.
    3. Grabs the calibration files and measurement files from the specified directory.
    4. Prints the found calibration files and creates an average spectrum.
    5. Grabs the concentrations of the calibration files.
    6. Performs the analysis for each calibration file:
        - Loads the .txt data into a pd.DataFrame.
        - Performs background correction.
        - Detects peaks.
        - Assigns the concentration values from the current file to the compounds.
        - Calculates the calibration curves.
    7. Graphs and returns the curve parameters.
    8. Repeats the same process for the measurement files:
        - Loads the .txt data into a pd.DataFrame.
        - Performs background correction.
        - Detects peaks.
        - Assigns the concentration values from the current file to the compounds.
        - Calculates the concentration of each compound using the curve parameters.
        - Prints the concentration of each compound in the measurement file.
        - Writes the results to a CSV file.
    
    Parameters:
    ----------
    None
    
    Returns:
    --------
    None
    """
    

    # TODO: Add all the ions and the possible neutral losses 
    ion_list = {
        'Asp': [304.1024, 258.0606],
        'Glu': [318.1180, 272.0763], 
        'IntStd': [332.1337, 286.0919],
        'Asn': [303.1183, 257.0766],
        'Ser': [276.1075, 230.0658],
        'Gln': [317.1340, 271.0923],
        'Ala': [260.1129, 216.0867],
        'GABA': [274.1286, 230.1023]
    }

    
    # Set up filepaths
    annotation_path =  get_path('annotations/')
    ms_path =  get_path('MS/')
    lc_path =  get_path('LC/')

    print("\nAnnotation path:", annotation_path, "\nMS path:", ms_path, "\nLC path:", lc_path)

    # Perform a check on the data
    check_data()

    lc_filelist = [file for file in os.listdir(lc_path) if file.endswith('.txt')]
    ms_filelist = [file for file in os.listdir(ms_path) if file.endswith('.mzml')]

    # Create the Measurement objects and perform preprocessing
    lc_measurements = []
    with alive_bar(len(lc_filelist), title="Preprocessing LC data...", spinner="dots", bar="filling", calibrate=2) as bar:
        for lc_file in lc_filelist:
            print(f"Preprocessing {lc_file}...")
            lc_file = LCMeasurement(Path(lc_path) / lc_file)
            lc_file.plot()
            lc_measurements.append(lc_file)
            bar()
    print("Done.")

    with alive_bar(len(ms_filelist), title="Preprocessing MS data...", spinner="dots", bar="filling", calibrate=2) as bar:
        for ms_file in ms_filelist:
            print(f"Preprocessing {ms_file}...")
            ms_file = MSMeasurement(Path(ms_path) / ms_file, 0.1)
            ms_file.plot()
            ms_measurements.append(ms_file)
            bar()
    print("Done.")

#FIXME: NEW 

def process_ms_file(ms_file):
    ms_file = MSMeasurement(Path(ms_path) / ms_file, 0.1)
    ms_file.plot()
    return ms_file




    # Perform annotation 
    for ms_file in ms_measurements:
        compound_list = [Compound(name=ion, file=ms_file.filename, ions=ion_list[ion]) for ion in ion_list.keys()]
        ms_file.annotate(compound_list)
        ms_file.plot_annotated()

    for lc_file in lc_measurements:
        corresponding_ms_file = next((ms_file for ms_file in ms_measurements if str(ms_file) == str(lc_file)), None)
        if corresponding_ms_file is None:
            print(f"Could not find a matching MS file for {lc_file}. Skipping.")
            continue
        lc_file.annotate(corresponding_ms_file.compounds)
        lc_file.plot_annotated()


    #TODO: Calculate calibration curves and concentrations
    


    # Direct the output back to the log file

    all_compounds = []
    # Track progress with alive_bar
    with alive_bar(len(cal_files), title='Analyzing calibration files...', calibrate=2) as bar:
        for cal_file in cal_files:
            sys.stdout = log_file
            print(f'Analyzing {cal_file}...')
            # Step 1: Load the .txt data into a pd.DataFrame (load_absorbance_data.py)
            dataframe = load_absorbance_data(data_path / cal_file)
            # Step 2: Load the annotated peaks (load_annotated_peaks.py)
            print(f'Looking for annotations in {annotation_path / cal_file}...')
            try:
                peaks = load_annotated_peaks(annotation_path / cal_file)
            except(FileNotFoundError):
                print(f'[WARNING] Did not find \'annotations\'/{cal_file}!')
                peaks = None
            # Step 3: Perform background correction (bg_corr.py)
            baseline_corrected_data = baseline_correction(dataframe, cal_file, data_path)
            # Step 4: Assign peaks (peaks.py)  
            compounds = assign_peaks(baseline_corrected_data, peaks, cal_file, data_path)
            # Step 5: Assign the concentration values from the current file to the compounds  
            concentration = extract_concentration(cal_file)
            for compound in compounds:
                compound.concentration = concentration
            sys.stdout = stdout
            all_compounds.extend(compounds)
            bar()

    # Step 6: Graph and return the curve parameters 
    print('Calculating calibration curves...')
    curve_params = calibrate(all_compounds, data_path)
    concentrations = {}
    
    # Step 7: Repeat the same process for the measurement files
    with alive_bar(len(res_files), title='Analyzing measurement files...', calibrate=2) as bar:
        for res_file in res_files:
            sys.stdout = log_file
            print(f'Analyzing {res_file}...')
            dataframe = load_absorbance_data(data_path / res_file)
            try:
                peaks = load_annotated_peaks(annotation_path / res_file)
            except(FileNotFoundError):
                print(f'[WARNING] Did not find \'annotations\'/{res_file}!')
                peaks = None
                continue
            baseline_corrected_data = baseline_correction(dataframe, res_file, data_path)
            compounds = assign_peaks(baseline_corrected_data, peaks, res_file, data_path)
            compounds_in_file = {}
            for compound in compounds:
                try:
                    concentration = calculate_concentration(compound.area, curve_params[compound.name])
                except(KeyError):
                    print(f'[WARNING] No calibration curve found for {compound.name}.')
                    continue
                print(f" {res_file}: {compound.name} has a concentration of {concentration} mM." )
                compounds_in_file[compound.name] = concentration
            concentrations[res_file] = compounds_in_file
            sys.stdout = stdout
            bar()
    
    results = pd.DataFrame(data=concentrations, columns = concentrations.keys())

    # Rename all the columns so that they don't contain the .txt extension
    results = results.rename(columns = lambda x: x[:-4])

    results.to_csv('data/results.csv')



def main():
    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        with alive_bar(len(ms_filelist), title="Preprocessing MS data...", spinner="dots", bar="filling", calibrate=2) as bar:
            results = []
            for ms_file in ms_filelist:
                results.append(pool.apply_async(process_ms_file, args=(ms_file,)))
                bar()
            ms_measurements = [result.get() for result in results]
    print("Done.")







if __name__ == "__main__":
    # Log script run-time 
    st = time.time()
    # Sets up a log file to record the print stream during runtime
    stdout = sys.stdout
    log_file = open('data/debug.log', 'w+')
    main()
    # Report the run-time
    et = time.time()
    elapsed_time = et - st
    print("Execution time: ", round(elapsed_time, 2), " seconds.")
    log_file.close()
