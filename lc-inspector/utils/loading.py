import pandas as pd
import numpy as np
import csv, re, os
from pyteomics import mzml
from calculation.wrappers import freezeargs
from functools import lru_cache

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
        # Read the first line to detect the delimiter
        first_line = file.readline()
        delimiter = detect_delimiter(first_line)

        if delimiter is None:
            raise ValueError("No recognizable delimiter found in the file.")

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
def load_ms1_data(path: str) -> tuple:
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
    data = [scan for scan in file if scan['ms level'] == 1]
    return tuple(data)