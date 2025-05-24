import pandas as pd
import numpy as np
import csv, re, os, logging, itertools, time
import __main__
from pyteomics import mzml
from pyteomics.auxiliary import cvquery

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
    start_time = time.time()
    
    ms1_data, ms2_data = [], []
    precursors_set = {round(ion, 4) for precursor in precursors for ion in precursor.ions.keys()}
    ms2_threshold = mass_accuracy * 5

    with mzml.MzML(str(path)) as file:
        for scan in file:
            if scan['ms level'] == 1:
                ms1_data.append(scan)
            elif scan['ms level'] == 2:
                precursor_mz = round(cvquery(scan, 'MS:1000827'), 4)
                if any(abs(precursor_mz - ion) < ms2_threshold for ion in precursors_set):
                    ms2_data.append(scan)

    if not ms1_data:
        logger.warning("No dedicated MS1 scans found, loading all scans.")
        with mzml.MzML(str(path)) as file:
            ms1_data = list(file)

    logger.info(f"Loaded {len(ms1_data)} MS1 scans and {len(ms2_data)} MS2 scans in {time.time() - start_time:.2f} seconds.")
    return tuple(ms1_data), tuple(ms2_data)

def load_ms2_library() -> dict:
    """
    Loads the MS2 library from the MoNA-export-All_LC-MS-MS_Orbitrap.msp file.
    
    Returns
    -------
    library : dict
        The MS2 library as a dictionary where the keys are the feature names and the values are lists of lines from the file.
    """
    library = {}
    with open(os.path.join(os.path.dirname(__main__.__file__), "resources/MoNA-export-All_LC-MS-MS_Orbitrap.msp"), mode="r", encoding="utf-8") as src:
        library = {line.split("Name: ")[1].strip(): [line] + list(itertools.takewhile(lambda x: x.strip() != "", src)) for line in src if line.startswith("Name: ")}
    return library
