import pandas as pd
import numpy as np
import csv, re
from pyteomics import mzml
from alive_progress import alive_bar

def load_absorbance_data(file_path):
    # Read the .txt file skipping initial rows until the 'Chromatogram Data' section
    with open(file_path, 'r') as file:
        lines = file.readlines()
        start_index = lines.index('Chromatogram Data:\n') + 2  # Find the start index of data

    # Convert lines into a Pandas DataFrame, skipping the first row as it contains headers
    df = pd.read_csv(
        file_path,
        skiprows=start_index,
        delimiter='\t',
        thousands=",",
        names=['Time (min)', 'Step (s)', 'Value (mAU)'],
    )

    # Look through all the values and replace any apostrophes (thousand's separator) with an empty string
    # Convert to a string first if necessary
    df['Value (mAU)'] = df['Value (mAU)'].apply(lambda x: str(x).replace("’", ""))
        
    # Extract Time (min) and Value (mAU) columns
    chromatogram_data = df[['Time (min)', 'Value (mAU)']][1:].astype(np.float64)

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

    print(df)
    
    return df


def load_ms1_data(path: str) -> tuple[list, np.ndarray, str]:
    #FIXME: Unused
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
    file = mzml.MzML(path)

    # Take only the scans where ms level is 1
    data = [scan for scan in file if scan['ms level'] == 1]

    return data