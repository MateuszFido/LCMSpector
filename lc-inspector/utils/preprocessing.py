import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path
from utils.loading import load_absorbance_data
import os

def baseline_correction(file_path = None):
    
    dataframe = load_absorbance_data(file_path)

    # Extract Time (min) and Value (mAU) columns
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
        
    normalized = pd.DataFrame(data={'Time (min)': time, 'Value (mAU)': baseline_corrected})
        
    if file_path:
        # Create and save the plots as PNG files
        plt.figure(figsize=(12, 8))
        gs = gridspec.GridSpec(2, 1, height_ratios=[1, 1])

        # Plotting chromatogram before background correction
        plt.subplot(gs[0])
        plt.plot(dataframe['Time (min)'], dataframe['Value (mAU)'], label='Before Correction', color='blue')
        plt.plot(dataframe['Time (min)'], baseline, label='Baseline', color='red', linestyle='--')
        plt.title('Chromatogram Before Background Correction')
        plt.xlabel('Time (min)')
        plt.ylabel('Absorbance (mAU)')
        plt.legend()

        # Plotting chromatogram after background correction
        plt.subplot(gs[1])
        plt.plot(dataframe['Time (min)'], baseline_corrected, label='After Correction', color='green')
        plt.title('Chromatogram After Background Correction')
        plt.xlabel('Time (min)')
        plt.ylabel('Absorbance (mAU)')
        plt.legend()

        plt.tight_layout()
    
        # Create the "plots" directory if it doesn't exist
        bg_dir = Path(file_path.parents[1] / 'plots' / 'background_correction')
        os.makedirs(bg_dir, exist_ok=True)
        # Save the plot as a PNG file
        plt.savefig(os.path.join(bg_dir, f'{os.path.basename(file_path)}_background_correction.png'))
        plt.close('all')
        
    return normalized
