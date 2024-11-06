import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path
from utils.loading import load_absorbance_data
import os, gc
from pyteomics import auxiliary
from scipy.signal import find_peaks, peak_widths

def baseline_correction(dataframe: pd.DataFrame) -> pd.DataFrame:
    
    # Extract Time (min) and Value (mAU) columns
    """
    Baseline corrects the chromatogram using the LLS algorithm.
    
    The algorithm iteratively applies the LLS operator to the data to remove the baseline.
    
    Parameters
    ----------
    dataframe : pd.DataFrame
        The chromatogram data as a pandas DataFrame with columns 'Time (min)' and 'Value (mAU)'.
    
    Returns
    -------
    pd.DataFrame
        The chromatogram data after baseline correction as a pandas DataFrame with columns 'Time (min)' and 'Value (mAU)'.
        
    If the file_path parameter is specified, the function will also create and save plots of the chromatogram before and after background correction as PNG files.
    """
    time = dataframe.copy()['Time (min)'].values
    absorbance = dataframe.copy()['Value (mAU)'].values
    if (absorbance < 0).any():
        shift = np.median(absorbance[absorbance < 0])
    else:
        shift = 0
    absorbance -= shift
    absorbance *= np.heaviside(absorbance, 0)
    # Compute the LLS operator
    tform = np.log(np.log(np.sqrt(absorbance + 1) + 1) + 1)

    # Compute the number of iterations given the window size.
    n_iter = 20

    for i in range(1, n_iter + 1):
        tform_new = tform.copy()
        for j in range(i, len(tform) - i):
            tform_new[j] = min(tform_new[j], 0.5 *
                                (tform_new[j+i] + tform_new[j-i]))
        tform = tform_new

    # Perform the inverse of the LLS transformation and subtract
    inv_tform = ((np.exp(np.exp(tform) - 1) - 1)**2 - 1)
    baseline_corrected = np.round(
        (absorbance - inv_tform), decimals=9)
    baseline = inv_tform + shift 
        
    normalized = pd.DataFrame(data={'Time (min)': time, 'Value (mAU)': baseline_corrected, 'Baseline': baseline, 'Uncorrected': absorbance})
        
    return normalized


def calculate_mz_axis(data: list, mass_accuracy: float) -> np.ndarray:
    """
    Calculate the m/z axis from a list of Scan objects.

    Parameters
    ----------
    data : List of Scan objects
        The list of Scan objects containing the MS data.

    Returns
    -------
    mz_axis : np.ndarray
        The m/z axis for the intensity values.
    """
    # Look up the necessary fields from the first scan in the file for m/z axis determination

    low_mass = auxiliary.cvquery(data[0], 'MS:1000501')
    high_mass = auxiliary.cvquery(data[0], 'MS:1000500')
    # Calculate the resolution of the m/z axis
    resolution = int((high_mass - low_mass) / mass_accuracy)
    # Create the m/z axis
    mz_axis = np.linspace(low_mass, high_mass, resolution, dtype=np.float64)

    return mz_axis



def average_intensity(data: list, mz_axis: np.ndarray) -> pd.DataFrame:
    # Initialize the average intensity array
    avg_int = np.zeros(len(mz_axis), dtype=np.float64)
    
    # Iterate over the scans, calculate the average intensity and store it in avg_int
    for scan in data:
        # Get m/z values and their intensities from the MzML path
        mz_array = scan['m/z array'].astype(np.float64)  # Ensure correct type
        intensity_array = scan['intensity array'].astype(np.float64)  # Ensure correct type
        
        # Interpolate continuous intensity signal from discrete m/z
        int_interp = np.interp(mz_axis, mz_array, intensity_array)
        avg_int += int_interp
        gc.collect()

    avg_int /= len(data)
    
    # Store the averaged intensity values in a DataFrame
    data_matrix = pd.DataFrame({'m/z': np.round(mz_axis, 4), 'intensity / a.u.': avg_int}, dtype=np.float64)
   
    return data_matrix


class Peak():
    '''Support class for Peak objects. \n
    
    Properties:
    -----------
    mz: np.ndarray
        Numpy array of mz values computed from indices of intensity axis, returned by scipy.find_peaks().
    index: int
        Index of the peak centroid. 
    width: list 
        Peak boundaries calculated at 0.9 of peak amplitude.
        '''

    def __init__(self, index: int, mz: np.ndarray, width: list):
        self.index = index # Index of the peak's maximum intensity point
        self.mz = mz       # Numpy array of mz values computed from indices of intensity axis
        self.width = width # The width of the peak from scipy.peak_widths()

    def __str__(self):
        return f"Feature with m/z range: {self.mz} and intensity range: {self.int_range}"

        
def pick_peaks(data, mz_axis):
    '''
    Peak-picking function. Uses SciPy's find_peaks() to perform peak-picking on a given chromatogram. 

    Parameters
    ----------
    path: str
        Path to the .csv file containing the chromatogram data.

    Returns
    -------
    peaklist: list
        List of Peak objects.
    '''

    peaklist = []

    # Find peaks
    peaks = find_peaks(data['intensity / a.u.'], distance=50, height=1000)

    # Calculate peak widths at 0.9 of peak amplitude
    widths, width_heights, left, right = peak_widths(data['intensity / a.u.'], peaks[0], rel_height=0.9)

    # For each peak, extract their properties and append the Peak to peaklist
    counter = 0
    for peak_idx in peaks[0]:
        mz = mz_axis[int(np.floor(left[counter])):int(np.ceil(right[counter]))]   # m/z range
        width = [int(np.floor(left[counter])), int(np.ceil(right[counter]))]      # left and right base, rounded down and up respectively
        counter += 1
        max_int_index = data['intensity / a.u.'].iloc[width[0]:width[1]].idxmax()
        max_int = data['intensity / a.u.'].iloc[max_int_index]
        peak = Peak(max_int_index, mz, width) # create the Peak object
        peaklist.append(peak)    

    '''
    # For debugging purposes, plot the picked peaks
    plt.plot(data['m/z'], data['intensity / a.u.'])
    plt.plot(data['m/z'][peaks[0]], data['intensity / a.u.'][peaks[0]], "x")
    plt.xlabel('m/z')
    plt.ylabel('intensity / a.u.')
    plt.show()
    '''

    return peaklist

import numpy as np
import pandas as pd

def construct_xic(scans, mz_axis, peaks):
    """
    Construct the XICs from the chromatogram data.

    Parameters
    ----------
    path : str
        The path to the .mzML file.

    Returns
    -------
    trc : pd.DataFrame
        The XICs for the given peaks.
    """

    # Initialize empty arrays to store the TIC, scan times, and XICs
    tic = []
    scan_times = []
    data = np.empty((len(peaks)+1, len(scans)), dtype=np.float64)

    # Construct the XICs
    
    for j, scan in enumerate(scans):
        scan_times.append(auxiliary.cvquery(scan, 'MS:1000016'))
        tic.append(scan['total ion current'])
        mz_array = np.ndarray.tolist(scan['m/z array'])
        intensity_array = np.ndarray.tolist(scan['intensity array'])
        # Interpolate intensity linearly for each scan from mz_array and intensity_array onto MZ_AXIS
        int_interp = np.interp(mz_axis, mz_array, intensity_array) 
        data[0][j] = scan['index']
        i = 1
        for peak in peaks:
            if i < len(peaks)+2:
                # TODO: Think about adding p-value comparisons for m/z that falls between two overlapping peaks
                data[i][0] = np.round(mz_axis[peak.index], 4)
            feature_int = int_interp[peak.width[0]:peak.width[1]]
            time_trace = np.round(np.trapz(feature_int))
            data[i][j] = time_trace
            i += 1

    # Add the TIC, scan times, and XICs to the data matrix
    trc = np.ndarray.tolist(data)
    trc.insert(1, scan_times)
    trc.insert(1, tic)

    try:
        ion_mode = auxiliary.cvquery(scans[0], 'MS:1000130')
    except AttributeError:
        ion_mode = 'negative'
    
    if ion_mode and 'positive' in ion_mode:
        mzs = [f'pos{np.round(mz_axis[peak.index], 4)}' for peak in peaks]
    else: 
        mzs = [f'neg{np.round(mz_axis[peak.index], 4)}' for peak in peaks]
    
    columns = ['MS1 scan ID', 'TIC (a.u.)', 'Scan time (min)']
    columns.extend(mzs)

    trc = pd.DataFrame(trc).T
    trc.columns = columns

    return trc