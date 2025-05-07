import pandas as pd
import numpy as np
import csv, re, os, logging
import __main__
from pyteomics import mzml
from pyteomics.auxiliary import cvquery
from calculation.wrappers import freezeargs
from functools import lru_cache

logger = logging.getLogger(__name__)
def detect_delimiter(line):
    """Detect the delimiter used in the line."""
    if ',' in line:
        return ','
    elif '\t' in line:
        return '\t'
    elif ' ' in line:
        return ' '
    else:
        return None  # No recognizable delimiter

def load_absorbance_data(file_path):
    time_values = []
    intensity_values = []

    # Check if the file exists
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    with open(file_path, 'r') as file:
        # Check the delimiter by looking at the first few lines
        delimiter = None
        for i in range(5):
            line = file.readline()
            delimiter = detect_delimiter(line)
            if delimiter is not None and detect_delimiter(line) != delimiter:
                logger.error("Detected more than 1 different delimiters in the file. Double check for possible parsing errors.")
                    

        # Reset the file pointer to the beginning
        file.seek(0)
        reader = csv.reader(file, delimiter=delimiter)

        for row in reader:
            # Check if the row has at least two columns
            if len(row) >= 2:
                try:
                    # Attempt to convert the first and last columns to float
                    time = float(row[0])  # First column
                    intensity = float(row[-1])  # Last column
                    time_values.append(time)
                    intensity_values.append(intensity)
                except ValueError:
                    # If conversion fails, skip this row
                    continue
    
    chromatogram_data = pd.DataFrame({'Time (min)': time_values, 'Value (mAU)': intensity_values})
    return chromatogram_data

def load_annotated_peaks(file_path):
    
    with open(file_path, 'r', newline='\n') as file:
        lines = csv.reader(file, delimiter='\t')
        start_index = 0
        for row in lines:
            if row[0] == 'Peak Results' or row[0] == 'Integration Results':
                break
            else:
                start_index += 1

    peakname = r"(Peakname|Name)\s*"  # Matches "Peakname" or "Name" with optional whitespace
    rt = r"(Ret\.Time|RetentionTime)\s*"  # Matches "Ret.Time" or "RetentionTime" with optional whitespace
    area = r"(Area|Height)\s*"  # Matches "Area" or "Height" with optional whitespace
    peak_start = r"(Peak Start|Start)\s*"  # Matches "Peak Start" or "Start" with optional whitespace
    peak_stop = r"(Peak Stop|Stop)\s*"  # Matches "Peak Stop" or "Stop" with optional whitespace
    
    # Load the annotated peaks from the annotations file, skipping the first few header rows
    df = pd.read_csv(file_path,
                     skiprows=start_index + 1,
                     delimiter='\t',
                     header=0,
                     usecols=lambda x: re.search(peakname, x) or re.search(rt, x) or re.search(area, x) or re.search(peak_start, x) or re.search(peak_stop, x))
    
    return df

@lru_cache
def load_ms_data(path: str, precursors: tuple, mass_accuracy: float) -> tuple:
    """
    Using the pyteomics library, load the data from the .mzML file into a pandas DataFrame.
    
    Parameters
    ----------
    path : str
        The path to the .mzML file.
    
    Returns
    -------
    data : List of Scan objects
        The list of Scan objects containing the MS data.
    """
    # Load the data
    file = mzml.MzML(str(path))

    # Take only the scans where ms level is 1
    ms1_data = []
    ms2_data = []
    for scan in file:
        if scan['ms level'] == 1:
            ms1_data.append(scan)
        elif scan['ms level'] == 2:
            for precursor in precursors:
                for ion in precursor.ions.keys():
                    if cvquery(scan, 'MS:1000827') is not None:
                        if np.abs(cvquery(scan, 'MS:1000827') - ion) <= (mass_accuracy * 3):
                            ms2_data.append(scan)
        else:
            # Skip the scan, MSn higher than 2 not supported
            continue 
    # Wrong format safeguard: if there are no MS1 scans, restart the iteration with only MS2 scans
    if len(ms1_data) == 0:
        logger.warning("No MS1 scans found, rerunning with higher MSn order scans.")
        file = mzml.MzML(str(path))
        for scan in file:
            ms1_data.append(scan)
    return tuple(ms1_data), tuple(ms2_data)

@lru_cache
def load_ms2_library() -> dict:
    """
    Loads the MS2 library from the MoNA-export-All_LC-MS-MS_Orbitrap.msp file.
    
    Returns
    -------
    library : dict
        The MS2 library as a dictionary where the keys are the feature names and the values are lists of lines from the file.
    """
    library = {}
    with open(os.path.join(os.path.dirname(__main__.__file__), os.pardir, os.path.join("resources/MoNA-export-All_LC-MS-MS_Orbitrap.msp")), "r") as src:
        for line in src:
            if line.startswith("Name: "):
                # The key is the feature name, the value is all the following lines until an empty line
                feature_name = line.split("Name: ")[1].strip()
                library[feature_name] = []
                while True:
                    line = next(src)
                    if line.strip() == "":
                        break
                    library[feature_name].append(line)
    return library