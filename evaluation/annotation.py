import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import os
import re
from scipy.signal import find_peaks, peak_widths
from pathlib import Path


def annotate_XICs(path, data, compound_list, mass_accuracy):
    """
    Find the XICs for the given compounds and annotate them in the given DataFrame.

    Parameters
    ----------
    path : str
        The path to the .mzML file.
    data : pd.DataFrame
        The DataFrame containing the MS data.
    compound_list : list
        A list of dictionaries containing the targeted ions for each compound.
    mass_accuracy : float
        The mass accuracy of the instrument.

    Returns
    -------
    compounds : list
        A list of dictionaries containing the annotated targeted ions for each compound.

    """

    for compound in compound_list:
        for ion in compound.ions.keys():
            # Look for the closest m/z value in the first row of data 
            closest = np.abs(data.iloc[0] - ion).idxmin()
            # Check if the m/z difference is within the given mass accuracy
            if mass_accuracy <= 0.0001:
                ppm_difference = np.abs((data[closest][0] - ion)) / ion * 1e6
                if ppm_difference > 3:
                    print(f"Skipping {ion} for {compound.name}, as m/z difference is {closest} - {ion} = {round(ppm_difference, 2)} ppm.")
                    continue
            if data[closest].max() < 1e4:
                print(f"Skipping {ion} for {compound.name}, as its intensity is {data[closest].max()}, which is lower than 1e4 cps.")
                continue


            # Get the respective time value for the highest intensity of this m/z
            scan_time = data['Scan time (min)'].iloc[data[closest][1:].idxmax()] # Skip the first two rows
            
            # Annotate the XICs with the respective time value
            compound.ions[ion]['RT'] = round(scan_time, 2)
            compound.ions[ion]['MS Intensity'] = round(data[closest].sum())

            print(f"Highest intensity of m/z={ion} ({compound.name}) was at {round(scan_time, 2)} mins.")
    
    return compound_list



def annotate_LC_data(chromatogram, compounds):
    
    lc_peaks = find_peaks(chromatogram['Value (mAU)'], distance=10, prominence=10)        
    widths, width_heights, left, right = peak_widths(chromatogram['Value (mAU)'], lc_peaks[0], rel_height=0.9)
    lc_peaks_RTs = chromatogram['Time (min)'][lc_peaks[0]]

    for compound in compounds:
        for ion in compound.ions:
            if compound.ions[ion]['RT'] is not None:
                closest = np.abs(lc_peaks_RTs - compound.ions[ion]['RT']).idxmin()
                left_idx = int(np.floor(left[list(lc_peaks[0]).index(closest)]))
                right_idx = int(np.ceil(right[list(lc_peaks[0]).index(closest)]))

                lc_intensity = np.trapz(chromatogram['Value (mAU)'][left_idx:right_idx])
                
                compound.ions[ion]['LC Intensity'] = round(lc_intensity)
                compound.ions[ion]['Apex'] = chromatogram['Value (mAU)'][left_idx:right_idx].max()

        print(compound)
        
    return compounds
