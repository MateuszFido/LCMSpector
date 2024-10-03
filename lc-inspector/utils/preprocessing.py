import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path
from utils.loading import load_absorbance_data
import os

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
        
    normalized = pd.DataFrame(data={'Time (min)': time, 'Value (mAU)': baseline_corrected})
        
    return normalized
