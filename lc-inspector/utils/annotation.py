from pyteomics import mzml, auxiliary
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import os
import re
import sys
from alive_progress import alive_bar
from scipy.signal import find_peaks, peak_widths
from pathlib import Path
from scipy.stats import mode
import json


def calculate_mz_axis(data):
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
    resolution = int((high_mass - low_mass) / 0.0001)
    # Create the m/z axis
    mz_axis = np.linspace(low_mass, high_mass, resolution, dtype=np.float64)

    return mz_axis


def average_intensity(path: str) -> pd.DataFrame:
    """
    Averages the intensity across all scans.

    Parameters
    ----------
    path : str
        The path to the .mzML file.

    Returns
    -------
    data_matrix : pd.DataFrame
        A DataFrame containing the m/z and intensity values.
    """
    
    # Prepare paths
    os.makedirs(Path(path).parents[2] / 'plots' / 'ms_spectra', exist_ok=True)
    plot_path = Path(path).parents[2] / 'plots' / 'ms_spectra'
    results_path = Path(path).parents[2] / 'results'
    filename = os.path.basename(path)

    # Load the data
    print(f"Loading {filename} into memory...")
    data = mzml.MzML(str(path))
    
    # Take only the scans where ms level is 1
    data = [scan for scan in data if scan['ms level'] == 1]
    
    # Calculate the m/z axis
    mz_axis = calculate_mz_axis(data)
    
    # Initialize the average intensity array
    avg_int = np.zeros(len(mz_axis))
    
    # Grab the filename from the first scan 
    bar_title = f"Averaging MS1 spectra for {os.path.basename(path).replace('.mzml', '')}."
    
    csv_data = np.empty((len(mz_axis), len(data)+1), dtype=np.float64)
    # Iterate over the scans, calculate the average intensity and store it in avg_int
    with alive_bar(len(data), title=bar_title, calibrate=2) as bar:
        for scan in data:
            # Get m/z values and their intensities from the MzML path
            mz_array = np.ndarray.transpose(scan['m/z array'])
            intensity_array = np.ndarray.transpose(scan['intensity array'])
            # Interpolate continuous intensity signal from discrete m/z
            int_interp = np.interp(mz_axis, mz_array, intensity_array)
            avg_int += int_interp 
            bar()

    avg_int /= len(data)
    
    # Store the averaged intensity values in a DataFrame
    data_matrix = pd.DataFrame({'m/z': np.round(mz_axis, 4), 'intensity / a.u.': avg_int }, dtype=np.float64)
    
    plt.plot(data_matrix['m/z'], data_matrix['intensity / a.u.'])
    plt.xlabel('m/z')
    plt.ylabel('average intensity / a.u.')
    plt.savefig(os.path.join(plot_path, filename.replace('.mzml', '.png')), dpi=300)

    # Save to a separate .csv file
    data_matrix.to_csv(results_path / filename.replace('.mzml', '.csv'), index=False)
   
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

        
def pick_peaks(path, mz_axis):
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
    filename = os.path.basename(path)
    data = pd.read_csv(Path(path).parents[2] / 'results' / filename.replace('.mzml', '.csv'))
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

def construct_xic(path):
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
    results_path = Path(path).parents[2] / 'results'
    filename = os.path.basename(path)
    
    print(f"Loading {filename} into memory...")
    file = mzml.MzML(str(path)) # Get the MzML
    scans = [scan for scan in file if scan['ms level'] == 1]

    mz_axis = calculate_mz_axis(scans)

    peaks = pick_peaks(path, mz_axis)

    # Initialize empty arrays to store the TIC, scan times, and XICs
    tic = []
    scan_times = []
    data = np.empty((len(peaks)+1, len(scans)))

    # Construct the XICs
    bar_title = f"Constructing XICs for {os.path.basename(path).replace('.mzml', '')}"
    with alive_bar(len(scans), title=bar_title, calibrate=2) as bar:
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
            bar()

    # Add the TIC, scan times, and XICs to the data matrix
    trc = np.ndarray.tolist(data)
    trc.insert(1, scan_times)
    trc.insert(1, tic)
        # Write the XICs to a .csv file
    # Use list comprehension for column titles
    if 'positive' in auxiliary.cvquery(scans[0], 'MS:1000130'):
        mzs = [f'pos{np.round(mz_axis[peak.index], 4)}' for peak in peaks]  
    else: 
        mzs = [f'neg{np.round(mz_axis[peak.index], 4)}' for peak in peaks]

    columns = ['MS1 scan ID', 'TIC (a.u.)', 'Scan time (min)']
    columns.extend(mzs)

    trc = pd.DataFrame(trc).T
    trc.to_csv(results_path / filename.replace('.mzml', '_XIC.csv'), header=columns, index=False)

    return trc
  

def annotate_XICs(path, compounds):
    
    # Load the XIC data, skip MS1 scan index and TIC rows
    """
    Annotate the LC data with the given targeted list of ions.

    Parameters
    ----------
    path : str
        The path to the .mzML file.
    compounds : dict
        A dictionary of targeted compounds with their respective m/z values
        as the keys and the ion names as the values.

    Returns
    -------
    None
    """
    filename = os.path.basename(path)
    data = pd.read_csv(Path(path).parents[2] / 'results' / filename.replace('.mzml', '_XIC.csv'), header=0)

    # Prepare the plotting folder
    os.makedirs(Path(path).parents[2] / 'plots' / 'XICs', exist_ok=True)
    plot_path = Path(path).parents[2] / 'plots' / 'XICs'

    fig, axes = plt.subplots(nrows=len(compounds), ncols=1, figsize=(8, int(2*len(compounds))))
    fig.suptitle(f'{os.path.basename(path)}')
    print(type(compounds))
    for i, (compound, ions) in enumerate(compounds.items()):
        for j, ion in enumerate(ions.keys()):
            # Look for the closest m/z value in the first row of data 
            closest = np.abs(data.iloc[0] - ion).idxmin()

            # Calculate ppm error
            ppm_difference = np.abs((data[closest][0] - ion) / ion) * 1e6
            if ppm_difference > 5:
                print(f"Skipping {ion} for {compound}, as m/z difference is {closest} - {ion} = {round(ppm_difference, 2)} ppm.")
                continue

            # Get the respective time value for the highest intensity of this m/z
            scan_time = data['Scan time (min)'].iloc[data[closest][1:].idxmax()] # Skip the first two rows

            print(f"Highest intensity of m/z={ion} ({compound}) was at {round(scan_time, 2)} mins.")

            compounds[compound][ion] = scan_time

            # Plot every XIC as a separate graph
            axes[i].plot(data['Scan time (min)'][1:], data[closest][1:])
            axes[i].plot(scan_time, data[closest].iloc[data[closest][1:].idxmax()], "o")
            axes[i].text(x=scan_time, y=data[closest].iloc[data[closest][1:].idxmax()], s=f"{compound}, {closest}")
            axes[i].set_xlabel('Scan time (min)')
            axes[i].set_ylabel('intensity / a.u.')

    # Save in the folder plots/XICs
    plt.savefig(os.path.join(plot_path, filename.replace('.mzml', '_XICs.png')), dpi=300)
    plt.close()

    print(compounds)

    # Dump the compounds dict into a .json file
    with open(os.path.join(Path(path).parents[2] / 'results', filename.replace('.mzml', '_compounds.json')), 'w') as f:
        json.dump(compounds, f)

    return compounds


def annotate_lc_chromatograms(path, chromatogram):

    # Prepare the plotting folder
    os.makedirs(Path(path).parents[2] / 'plots' / 'lc_chromatograms', exist_ok=True)
    plot_path = Path(path).parents[2] / 'plots' / 'lc_chromatograms'
    filename = os.path.basename(path)

    compounds = json.load(open(os.path.join(Path(path).parents[2] / 'results', filename.replace('.mzml', '_compounds.json')), 'r'))
    
    lc_peaks = find_peaks(chromatogram['Value (mAU)'], distance=10, height=100)        
    widths, width_heights, left, right = peak_widths(chromatogram['Value (mAU)'], lc_peaks[0], rel_height=0.9)

    lc_peaks_RTs = chromatogram['Time (min)'][lc_peaks[0]]

    plt.plot(chromatogram['Time (min)'], chromatogram['Value (mAU)'])
    plt.plot(chromatogram['Time (min)'][lc_peaks[0]], chromatogram['Value (mAU)'][lc_peaks[0]], 'o')
    plt.ylabel('Absorbance (mAU)')
    plt.xlabel('Retention time (min)')

    for compound, ions in compounds.items():
        # Find the peak with the closest retention time to the value of the first ion in the list of ions
        closest = np.abs(lc_peaks_RTs - ions[list(ions.keys())[0]]).idxmin()
        plt.text(x=chromatogram['Time (min)'][closest], y=chromatogram['Value (mAU)'][closest], s=compound, fontsize=10, rotation=90)
        
    plt.savefig(os.path.join(plot_path, filename.replace('.mzml', '_LC.png')), dpi=300)
    plt.close()




    # FIXME: unfinished
    # Integrate every peak's area
    for i, peak_idx in enumerate(lc_peaks[0]):
        peak_area = np.trapz(chromatogram['Value (mAU)'][int(np.floor(left[i])):int(np.ceil(right[i]))],
         x=chromatogram['Time (min)'][int(np.floor(left[i])):int(np.ceil(right[i]))])
        # compounds['LC'][chromatogram['Name'][peak_idx]] = peak_area



path = '/Users/mateuszfido/Library/CloudStorage/OneDrive-ETHZurich/Mice/UPLC code/hplc/data/ms/STMIX5_02.mzml'
# chromatogram = load_absorbance_data('/Users/mateuszfido/Library/CloudStorage/OneDrive-ETHZurich/Mice/UPLC code/hplc/data/lc/STMIX5_02_UV_VIS_1.txt')


# average_intensity(path)
# construct_xic(path)
# annotate_XICs(path, compounds)
# annotate_lc_chromatograms(path, chromatogram)