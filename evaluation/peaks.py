import numpy as np
from scipy.signal import find_peaks, peak_prominences
import matplotlib.pyplot as plt
import os, re
from pathlib import Path

class Compound:
    def __init__(self, index, name, area, rt, left_base=None, right_base=None):
        self.index = index
        self.name = name
        self.area = area
        self.left_base = left_base
        self.right_base = right_base
        self.rt = rt
        
    def __str__(self):
        return f"Peak {self.name} (index: {self.index}), RT: {round(self.rt, 2)} min, area: {round(self.area, 2)} mAU, left base: {round(self.left_base, 2)}, right base: {round(self.right_base, 2)}."
        

def assign_peaks(baseline_corrected_data, peaks, filename, file_path):
    """
    Assigns peaks to a chromatogram based on annotated peaks data.

    Args:
        baseline_corrected_data (pandas.DataFrame): The baseline corrected data for the chromatogram.
        peaks (pandas.DataFrame): The annotated peaks data.
        file_path (str): The path to the file containing the annotated peaks data.

    Returns:
        compound_list (list): A list of Compound objects representing the assigned peaks.

    This function iterates over the annotated peaks data and assigns peaks to the chromatogram based on the provided data. It skips rows that contain "n.a." values or "UV_VIS" in the peak name. It creates a subfolder called "peaks" in the "plots" directory if it doesn't exist. It then plots the chromatogram and highlights the assigned peaks. It also plots vertical lines for the left and right bases of each peak and fills the area underneath the peak's contour line with a shaded region. The plot is saved as a PNG file in the "peaks" subfolder. The function returns a list of Compound objects representing the assigned peaks.
    """
    #TODO: Delete when MS annotation present? Relegate? 
    compound_list = []
    for index, peak in peaks.iterrows():
        # First, check which naming convention is used by Chromeleon
        try:
            rt = peak['Ret.Time']
            area = peak['Area ']
        except KeyError:
            rt = peak['RetentionTime']
            area = peak['Area']
        finally:
            peakname = peak['Peakname']
            peak_start = peak['Peak Start ']
            peak_stop = peak['Peak Stop ']
        if index == 0:
            continue
        if 'NaN'.casefold() in str(peakname).casefold() or 'UV_VIS'.casefold() in str(peakname).casefold():
            continue
        try: 
            float(rt)
        except(ValueError):
            print(f'[ERROR] Peak {index} contains n.a. values, skipping.')
            continue
        else:    
            print(f"Found peak {peakname}, with area {area} mAU, at retention time {rt} minutes between {peak_start} and {peak_stop} minutes.\n Recalculating area...")
            left_base=np.argmin(np.abs(baseline_corrected_data['Time (min)'] - float(peak_start)))
            right_base=np.argmin(np.abs(baseline_corrected_data['Time (min)'] - float(peak_stop)))
            compound = Compound(index=index, 
                                name=peakname, 
                                left_base=left_base, 
                                right_base=right_base, 
                                area=np.trapz(y=baseline_corrected_data['Value (mAU)'].iloc[left_base:right_base]), 
                                rt=float(rt))
            print(filename, ':', compound, '\n')
            compound_list.append(compound)
        
    # Create "peaks" subfolder in "plots" directory if it doesn't exist
    peaks_plots_dir = Path(file_path / 'plots' / 'peaks')
    os.makedirs(peaks_plots_dir, exist_ok=True)

    # Plotting chromatogram and highlighting peaks
    plt.figure(figsize=(10, 6))
    plt.plot(baseline_corrected_data['Time (min)'], baseline_corrected_data['Value (mAU)'], label='Chromatogram (Baseline Corrected)', color='blue', linewidth=0.5)

    # Highlight peaks
    for compound in compound_list:
        x = baseline_corrected_data['Time (min)'].iloc[(np.argmin(np.abs(baseline_corrected_data['Time (min)'] - float(compound.rt))))]
        y = baseline_corrected_data['Value (mAU)'].iloc[(np.argmin(np.abs(baseline_corrected_data['Time (min)'] - float(compound.rt))))]
        plt.scatter(x, y, color='green', marker='o')
        plt.text(x*(1.01), y*(1.01), compound.name, fontsize=5, rotation=90)
        
    # Plot one vertical line for the left base of each peak, one for the right base of each peak 
    # and fill the area underneath the peak's contour line with a shaded region    
    for i, compound in enumerate(compound_list):
        plt.axvline(x=baseline_corrected_data['Time (min)'].iloc[compound.left_base], color='red', linestyle='--', linewidth=0.1)
        plt.axvline(x=baseline_corrected_data['Time (min)'].iloc[compound.right_base], color='red', linestyle='--', linewidth=0.1)
        x = baseline_corrected_data['Time (min)'].iloc[compound.left_base:compound.right_base]
        y = baseline_corrected_data['Value (mAU)'].iloc[compound.left_base:compound.right_base]
        plt.fill_between(x, y, alpha=0.5, color='gray')
    
    plt.title('Chromatogram with Detected Peaks (Baseline Corrected)')
    plt.xlabel('Time (min)')
    plt.ylabel('Absorbance (mAU)')
    plt.legend()

    # Save the plot as a PNG file
    plt.savefig(os.path.join(peaks_plots_dir, f'peaks_{filename.replace(".txt", ".png")}'), dpi=300)

    # Close the figure
    plt.close()

    return compound_list