import numpy as np
from utils.load_data import load_absorbance_data
from utils.list_files import list_files
import matplotlib.pyplot as plt

def average_spectrum(directory):
    '''
    Prepares an average spectrum of all the calibration files found via list_files.
    Averages the spectra of the calibration files, then returns the average spectrum.
    '''
    # List all calibration files in the directory
    calibration_files = list_files(directory, file_extension='.txt')
    
    # Initialize a list to store spectra
    spectra = []
    
    # Load and accumulate spectra from each calibration file
    for file in calibration_files:
        data = load_absorbance_data(directory / file)
        spectra.append(data['Value (mAU)'].values)
    
    # Calculate the average spectrum
    average_spectrum = np.mean(spectra, axis=0)
    
    # Plot the average spectrum using matplotlib
    plt.plot(average_spectrum)
    plt.xlabel('Wavelength (nm)')
    plt.ylabel('Absorbance (mAU)')
    plt.title('Average Spectrum')
    plt.show()
    
    return average_spectrum
