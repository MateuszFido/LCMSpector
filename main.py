from evaluation.cal_curves import calibrate
from evaluation.calc_conc import calculate_concentration
from evaluation.find_peaks import detect_peaks
from training import *
from utils.list_files import read_files
from utils.load_data import load_absorbance_data
from utils.normalize import background_correction, normalize_data
import time, csv, re
from pathlib import Path


def run():
    
    # Path to the directory where the script is located
    file_path = Path(__file__).parent / 'data'
    
    # Supply the expected peak list, in order of elution
    
    peaks = ['aspartic acid', 
            'glutamic acid', 
            'internal standard',
            'asparagine',
            'serine',
            'glutamine',
            'histidine',
            'glycine',
            'citrulline',
            'threonine',
            'arginine',
            'GABA',
            'alanine',
            'proline',
            'NH4Cl',
            'agmatine',
            'histamine',
            'valine',
            'methionine',
            'tryptophan',
            'isoleucine',
            'leucine-phenylalanine',
            'ornithine',
            'dopamine',
            'spermidine',
            'lysine',
            'putrescine',
            'cadaverine']
    
    # Grab the calibration files and measurement files
    cal_files, res_files = read_files(file_path)

    print('Found calibration files:', cal_files, '\n')
    print('Creating an average spectrum...')
    print('Found measurement files:', res_files, '\n') 
    
    # Grab the concenctrations of calibration files
    def extract_concentration(filename):
        match = re.search(r'(\d+(\.\d+)?)mM', filename)
        if match:
            return float(match.group(1))
        else:
            return None

    all_compounds = []
    # Calculate the calibration curves
    for cal_file in cal_files:
        print(f'Analyzing {cal_file}...')
        # Step 1: Load the .txt data into a pd.DataFrame (load_absorbance_data.py)
        dataframe = load_absorbance_data(file_path / cal_file)
        # Step 2: Perform background correction (bg_corr.py)
        baseline_corrected_data = background_correction(dataframe, cal_file, file_path)
        # Step 3: Detect peaks (find_peaks.py)  
        compounds = detect_peaks(dataframe['Time (min)'], baseline_corrected_data, peaks, cal_file, file_path)
        # Step 4: Assign the concentration values from the current file to the compounds  
        concentration = extract_concentration(cal_file)
        for compound in compounds:
            compound.concentration = concentration
        all_compounds.extend(compounds)

    # Step 5: Graph and return the curve parameters 
    curve_params = calibrate(all_compounds, file_path)
    print(curve_params)
    concentrations = {}

    # Repeat the same process for the measurement files
    for res_file in res_files:
        print(f'Analyzing {res_file}...')
        dataframe = load_absorbance_data(file_path / res_file)
        baseline_corrected_data = background_correction(dataframe, res_file, file_path)
        compounds = detect_peaks(dataframe['Time (min)'], baseline_corrected_data, peaks, res_file, file_path)
        compounds_in_file = {}
        for compound in compounds:
            concentration = calculate_concentration(compound.area, curve_params[compound.name])
            print(f"{compound.name} in file {res_file} has a concentration of {concentration} mM." )
            compounds_in_file[compound.name] = [f'{concentration} mM', 
                                                curve_params[compound.name]['Slope'], 
                                                curve_params[compound.name]['Intercept'],
                                                curve_params[compound.name]['R-squared']]
        concentrations[res_file] = compounds_in_file

        with open(file_path / 'results.csv', 'w', newline='') as csv_file:
            writer = csv.writer(csv_file)

            # Write header row
            header_row = ['File']
            writer.writerow(header_row)

            # Write data rows
            for outer_key, inner_dict in concentrations.items():
                writer.writerow([outer_key, 'Compound', 'Concentration', 'Slope', 'Intercept', 'R-squared'])
                for compound_name, compound_values in inner_dict.items():
                    data_row = ['', compound_name] + compound_values
                    writer.writerow(data_row)
                
                writer.writerow([])

if __name__ == "__main__":
    # Log script run-time 
    st = time.time()           
    run()
    # Report the run-time
    et = time.time()
    elapsed_time = et - st
    print("Execution time: ", round(elapsed_time, 2), " seconds.")
    
