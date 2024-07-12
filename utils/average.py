import numpy as np
import pandas as pd
from utils.load_data import load_absorbance_data
from utils.preprocessing import baseline_correction
import matplotlib.pyplot as plt

def average_spectrum(file_path, cal_files):
    '''
    Prepares an average spectrum of all the calibration files found via list_files.
    Averages the spectra of the calibration files, then returns the average spectrum.
    '''
    # Initialize a list to store spectra
    spectra = []
    
    # Load and accumulate spectra from each calibration file
    for file in cal_files:
        data = load_absorbance_data(file_path / file)
        spectra.append(data['Value (mAU)'])
            
    # Calculate the average spectrum
    average_spectrum = pd.DataFrame(data={'Time (min)': data['Time (min)'], 'Value (mAU)': np.mean(spectra, axis=0)}) 

    average_spectrum = baseline_correction(average_spectrum)
    
    return average_spectrum
