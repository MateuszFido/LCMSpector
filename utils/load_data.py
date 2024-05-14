import pandas as pd
import numpy as np

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
        thousands=',',
        names=['Time (min)', 'Step (s)', 'Value (mAU)'],
    )

    # Extract Time (min) and Value (mAU) columns
    chromatogram_data = df[['Time (min)', 'Value (mAU)']][1:].astype(np.float64)

    return chromatogram_data