import pandas as pd
import numpy as np
import csv

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
            if row[0] == 'Peak Results':
                break
            else:
                start_index += 1

    # Load the annotated peaks from the annotations file, skipping the first few header rows
    df = pd.read_csv(file_path,
                     skiprows=start_index + 1,
                     delimiter='\t',
                     header=0,
                     usecols=['Peakname', 'Ret.Time', 'Area ', 'Peak Start ', 'Peak Stop '])

    return df