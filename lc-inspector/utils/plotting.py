import matplotlib.pyplot as plt
import os

def plot_absorbance_data(file_path, dataframe):
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

def plot_average_ms_data(file_path, data_matrix):

    plt.plot(data_matrix['m/z'], data_matrix['intensity / a.u.'])
    plt.xlabel('m/z')
    plt.ylabel('average intensity / a.u.')
    plt.savefig(os.path.join(plot_path, filename.replace('.mzml', '-avg.png')), dpi=300)
    plt.close('all')