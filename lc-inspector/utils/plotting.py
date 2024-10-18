import matplotlib.pyplot as plt
from matplotlib import gridspec
import os
from pathlib import Path
import numpy as np
import pandas as pd
from adjustText import adjust_text

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
    # Plot the m/z of the 5 highest peaks in spectrum
    highest_peaks = data_matrix.nlargest(5, 'intensity / a.u.')
    texts=[]
    for index, row in highest_peaks.iterrows():
        texts.append(plt.text(row['m/z'], row['intensity / a.u.'], row['m/z']))
    adjust_text(texts, arrowprops=dict(arrowstyle='->', color='red'))
    plt.title(f'Average MS data of {filename}')
    plt.savefig(os.path.join(plot_path, filename.replace('.mzml', '-avg.png')), dpi=300)
    plt.close('all')

def plot_annotated_LC(path, chromatogram, compounds):
    '''
    Annotate the LC data with the given targeted list of ions and plot the results.

    Parameters
    ----------
    path : str
        The path to the .mzML file.
    
    chromatogram : pd.DataFrame
        The DataFrame containing the LC data.

    Returns
    -------
    None
    '''

    # Prepare the plotting folder
    os.makedirs(Path(path).parents[1] / 'plots' / 'LC chromatograms', exist_ok=True)
    plot_path = Path(path).parents[1] / 'plots' / 'LC chromatograms'
    filename = os.path.basename(path)

    # Plot the LC data
    plt.figure(figsize=(20, 12))
    plt.title(f'{filename}')
    plt.xlabel('Retention time (min)')
    plt.ylabel('Absorbance (mAU)')
    plt.plot(chromatogram['Time (min)'], chromatogram['Value (mAU)'])
    texts=[]
    for compound in compounds:
        for ion in compound.ions.keys():
            if compound.ions[ion]['RT'] is not None:
                plt.plot(compound.ions[ion]['RT'], compound.ions[ion]['Apex'], 'o', markersize=10)
                texts.append(plt.text(compound.ions[ion]['RT'], compound.ions[ion]['Apex']-np.random.random()/100,
                f"{compound.name}\n{ion}", fontsize=5))
    
    adjust_text(texts, avoid_self=False, time_lim=30, max_move=None, arrowprops=dict(arrowstyle='-', color='gray', alpha=.3))
    plt.savefig(os.path.join(plot_path, filename.replace('.txt', '_LC.png')), dpi=300)
    plt.close()

def plot_annotated_XICs(path, xics, compound_list):
    """
    Plot the XICs for the given compounds and annotate them with the respective m/z and scan time.

    Parameters
    ----------
    path : str
        The path to the .mzML file.
    xics : pd.DataFrame
        The DataFrame containing the XICs.
    compound_list : list
        A list of dictionaries containing the targeted ions for each compound.

    Returns
    -------
    None

    """
    # Create the plots folder if it doesn't exist
    os.makedirs(Path(path).parents[1] / 'plots' / 'XICs', exist_ok=True)
    plot_path = Path(path).parents[1] / 'plots' / 'XICs'
    filename = os.path.basename(path)
    # Using gridspec, create a grid of subplots

    # Calculate the number of columns and rows required for the grid
    tot = len(compound_list)
    cols = int(np.ceil(np.sqrt(tot)))
    rows = int(np.ceil(tot / cols))

    # Create the grid of subplots
    gs = gridspec.GridSpec(rows, cols)
    fig = plt.figure(figsize=(30, 20))
    # Adjust the spacing between the subplots
    plt.subplots_adjust(hspace=0.5, wspace=0.5)
    # Add a title to the figure
    fig.suptitle(f'{filename}')
    # Iterate over each compound and create a subplot for it
    for i, compound in enumerate(compound_list):
        texts = []
        ax = fig.add_subplot(gs[i])
        # Iterate over each ion in the compound
        for j, ion in enumerate(compound.ions.keys()):
            # Find the closest m/z to the ion
            if compound.ions[ion]["RT"] is None or compound.ions[ion]["MS Intensity"] is None:
                continue
            closest = np.abs(xics.iloc[0] - ion).idxmin()
            # Find the scan time with the highest intensity
            scan_time = xics['Scan time (min)'].iloc[xics[closest][1:].idxmax()] # Skip the first two rows
            # Plot the XIC and annotate it with the m/z and scan time
            ax.plot(xics['Scan time (min)'][1:], xics[closest][1:])
            ax.plot(scan_time, xics[closest].iloc[xics[closest][1:].idxmax()], "o")
            text = ax.text(x=scan_time-np.random.random()/100, y=xics[closest].iloc[xics[closest][1:].idxmax()], s=f"{ion}\n({closest})", fontsize=5)
            texts.append(text)
        # Add a title to the subplot
        ax.set_title(f"{compound.name}")
        ax.set_xlabel('Scan time (min)')
        ax.set_ylabel('intensity / a.u.')
        # Adjust the spacing between the text labels
        adjust_text(texts, avoid_self=False, time_lim=10, arrowprops=dict(arrowstyle='-', color='gray', alpha=.3))

    # Save in the folder plots/XICs
    plt.savefig(os.path.join(plot_path, filename.replace('.mzml', '_XICs.png')), dpi=300)
    plt.close()
