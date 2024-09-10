from evaluation.calibration_curves import calibrate
from evaluation.calc_conc import calculate_concentration
from evaluation.peaks import assign_peaks
from training import *
from utils.list_files import read_files
from utils.load_data import load_absorbance_data, load_annotated_peaks
from utils.preprocessing import baseline_correction
import time, csv, re, sys, os
from pathlib import Path
from alive_progress import alive_bar
import pandas as pd

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
    
    # Redirect output to a log file
    sys.stdout = log_file
    # Path to the directory where the script is located
    file_path = Path(__file__).parent / 'data'
    annotation_path = Path(__file__).parent / 'data' / 'annotations'
    # Grab the calibration files and measurement files
    cal_files, res_files = read_files(file_path)

    print('Found calibration files:', cal_files, '\n')
    print('Found measurement files:', res_files, '\n') 
    
    # Direct the output back to regular stdout
    sys.stdout = stdout
    
    # Grab the concenctrations of calibration files
    def extract_concentration(filename):
        # First look for STMIX in the filename 
        # If present, return the number(s) in the string as concentration
        match = re.search(r'STMIX', filename)
        if match:
            return float(re.findall(r'(\d*[.]?\d+)', filename)[0])
        else:
            return None
    
    all_compounds = []
    # Track progress with alive_bar
    with alive_bar(len(cal_files), title='Analyzing calibration files...', calibrate=2) as bar:
        for cal_file in cal_files:
            sys.stdout = log_file
            print(f'Analyzing {cal_file}...')
            # Step 1: Load the .txt data into a pd.DataFrame (load_absorbance_data.py)
            dataframe = load_absorbance_data(file_path / cal_file)
            # Step 2: Load the annotated peaks (load_annotated_peaks.py)
            print(f'Looking for annotations in {annotation_path / cal_file}...')
            try:
                peaks = load_annotated_peaks(annotation_path / cal_file)
            except(FileNotFoundError):
                print(f'[WARNING] Did not find \'annotations\'/{cal_file}!')
                peaks = None
            # Step 3: Perform background correction (bg_corr.py)
            baseline_corrected_data = baseline_correction(dataframe, cal_file, file_path)
            # Step 4: Assign peaks (peaks.py)  
            compounds = assign_peaks(baseline_corrected_data, peaks, cal_file, file_path)
            # Step 5: Assign the concentration values from the current file to the compounds  
            concentration = extract_concentration(cal_file)
            for compound in compounds:
                compound.concentration = concentration
            sys.stdout = stdout
            all_compounds.extend(compounds)
            bar()

    # Step 6: Graph and return the curve parameters 
    print('Calculating calibration curves...')
    curve_params = calibrate(all_compounds, file_path)
    concentrations = {}
    
    # Step 7: Repeat the same process for the measurement files
    with alive_bar(len(res_files), title='Analyzing measurement files...', calibrate=2) as bar:
        for res_file in res_files:
            sys.stdout = log_file
            print(f'Analyzing {res_file}...')
            dataframe = load_absorbance_data(file_path / res_file)
            try:
                peaks = load_annotated_peaks(annotation_path / res_file)
            except(FileNotFoundError):
                print(f'[WARNING] Did not find \'annotations\'/{res_file}!')
                peaks = None
                continue
            baseline_corrected_data = baseline_correction(dataframe, res_file, file_path)
            compounds = assign_peaks(baseline_corrected_data, peaks, res_file, file_path)
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

if __name__ == "__main__":
    # Log script run-time 
    st = time.time()
    # Sets up a log file to record the print stream during runtime
    stdout = sys.stdout
    log_file = open('data/debug.log', 'w+')
    run()
    # Report the run-time
    et = time.time()
    elapsed_time = et - st
    print("Execution time: ", round(elapsed_time, 2), " seconds.")
    log_file.close()
