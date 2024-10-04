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


def annotate_XICs(path, data, compounds, mass_accuracy):
    """
    Annotate the LC data with the given targeted list of ions.
    """
    os.makedirs(Path(path).parents[1] / 'plots' / 'XICs', exist_ok=True)
    plot_path = Path(path).parents[1] / 'plots' / 'XICs'
    filename = os.path.basename(path)
    fig, axes = plt.subplots(nrows=len(compounds), ncols=1, figsize=(8, int(2*len(compounds))))
    fig.suptitle(f'{filename}')
    for i, (compound, ions) in enumerate(compounds.items()):
        for j, ion in enumerate(ions.keys()):
            # Look for the closest m/z value in the first row of data 
            closest = np.abs(data.iloc[0] - ion).idxmin()

            # Calculate ppm error
            decimals = len(str(mass_accuracy).split(".")[1])
            ppm_difference = np.abs((data[closest][0] - np.round(ion, decimals)) / np.round(ion, decimals)) * 1e6
            if ppm_difference > 5:
                print(f"Skipping {ion} for {compound}, as m/z difference is {closest} - {ion} = {round(ppm_difference, 2)} ppm.")
                continue

            # Get the respective time value for the highest intensity of this m/z
            scan_time = data['Scan time (min)'].iloc[data[closest][1:].idxmax()] # Skip the first two rows

            print(f"Highest intensity of m/z={ion} ({compound}) was at {round(scan_time, 2)} mins.")

            compounds[compound][ion] = scan_time

            axes[i].plot(data['Scan time (min)'][1:], data[closest][1:])
            axes[i].plot(scan_time, data[closest].iloc[data[closest][1:].idxmax()], "o")
            axes[i].text(x=scan_time, y=data[closest].iloc[data[closest][1:].idxmax()], s=f"{compound}, {closest}")
            axes[i].set_xlabel('Scan time (min)')
            axes[i].set_ylabel('intensity / a.u.')

        # Save in the folder plots/XICs
    plt.savefig(os.path.join(plot_path, filename.replace('.mzml', '_XICs.png')), dpi=300)
    plt.close()

    return compounds


def annotate_lc_chromatograms(path, chromatogram):

    # Prepare the plotting folder
    os.makedirs(Path(path).parents[1] / 'plots' / 'lc_chromatograms', exist_ok=True)
    plot_path = Path(path).parents[1] / 'plots' / 'lc_chromatograms'
    filename = os.path.basename(path)
        
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