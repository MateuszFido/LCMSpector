import matplotlib.pyplot as plt
from matplotlib import gridspec
import os
from pathlib import Path

def plot_absorbance_data(file_path, dataframe):
    # Create and save the plots as PNG files
    plt.figure(figsize=(12, 8))
    gs = gridspec.GridSpec(2, 1, height_ratios=[1, 1])

    # Plotting chromatogram before background correction
    plt.subplot(gs[0])
    plt.plot(dataframe['Time (min)'], dataframe['Uncorrected'], label='Before correction', color='blue')
    plt.plot(dataframe['Time (min)'], dataframe['Baseline'], label='Baseline', color='red', linestyle='--')
    plt.title('Chromatogram Before Background Correction')
    plt.xlabel('Time (min)')
    plt.ylabel('Absorbance (mAU)')
    plt.legend()

    # Plotting chromatogram after background correction
    plt.subplot(gs[1])
    plt.plot(dataframe['Time (min)'], dataframe['Value (mAU)'], label='After correction', color='green')
    plt.title('Chromatogram After Background Correction')
    plt.xlabel('Time (min)')
    plt.ylabel('Absorbance (mAU)')
    plt.legend()

    plt.tight_layout()

    # Create the "plots" directory if it doesn't exist
    plot_path = Path(file_path.parents[1] / 'plots' / 'background correction')
    os.makedirs(plot_path, exist_ok=True)
    # Save the plot as a PNG file
    filename = os.path.basename(file_path)
    plt.savefig(os.path.join(plot_path, filename.replace('.txt', '-bg.png')), dpi=300)
    plt.close('all')

def plot_average_ms_data(file_path, data_matrix):
    plot_path = Path(file_path.parents[1] / 'plots' / 'average MS data')
    os.makedirs(plot_path, exist_ok=True)

    filename = os.path.basename(file_path)
    
    plt.figure(figsize=(12, 8))
    plt.plot(data_matrix['m/z'], data_matrix['intensity / a.u.'])
    plt.xlabel('m/z')
    plt.ylabel('average intensity / a.u.')
    plt.savefig(os.path.join(plot_path, filename.replace('.mzml', '-avg.png')), dpi=300)
    plt.close('all')