import numpy as np
from scipy.signal import find_peaks, peak_widths
import matplotlib.pyplot as plt
import os
from pathlib import Path

class Compound:
    def __init__(self, index, name, area, rt):
        self.index = index
        self.name = name
        self.area = area
        self.rt = rt
        
    def __str__(self):
        return f"Peak: {self.name} (index: {self.index}) with retention time: {self.rt} min, total area: {self.area} mAU."
        

def detect_peaks(time, baseline_corrected_data, theoretical_peaklist, filename, file_path):
    # Find peaks in the baseline-corrected data
    peaks, _ = find_peaks(baseline_corrected_data, prominence=2)
    compound_list = []
    
    # Calculate peak areas using trapezoidal integration within estimated boundaries
    widths, _, left_ips, right_ips = peak_widths(baseline_corrected_data, peaks, rel_height=0.5)
        
    theoretical_index = 0

    for i, peak_index in enumerate(peaks):
        # Define the boundaries of the peak
        left_index = int(left_ips[i])
        right_index = int(right_ips[i])
        
        # Extract the segment of the data that corresponds to the current peak
        peak_data = baseline_corrected_data[left_index:right_index + 1]
        peak_time = time[left_index:right_index + 1]
        
        # Calculate the area under the peak using the trapezoidal rule
        peak_area = np.trapz(peak_data, peak_time)
        
        # Create a compound object with the calculated area and append it to the list
        if theoretical_index < len(theoretical_peaklist):
            
            peak_name = theoretical_peaklist[theoretical_index]
            peak_rt = time[peak_index]
            compound_list.append(Compound(peak_index, peak_name, peak_area, peak_rt))
            theoretical_index += 1


    # Create "peaks" subfolder in "plots" directory if it doesn't exist
    peaks_plots_dir = Path(file_path / 'plots' / 'peaks')
    os.makedirs(peaks_plots_dir, exist_ok=True)

    # Plotting chromatogram and highlighting peaks
    plt.figure(figsize=(10, 6))
    plt.plot(time, baseline_corrected_data, label='Chromatogram (Baseline Corrected)', color='blue', linewidth=0.5)

    # Highlight peaks
    for compound in compound_list:
        x = time[compound.index]
        y = baseline_corrected_data[compound.index]
        plt.scatter(x, y, color='green', marker='o')
        plt.text(x*(1.01), y*(1.01), compound.name, fontsize=8, rotation=90)
        
    # Plot one vertical line for the left base of each peak, one for the right base of each peak 
    # and the area underneath the peak's contour line as a shaded region
    for i, compound in enumerate(compound_list):
        left_base = time[int(left_ips[i])]
        right_base = time[int(right_ips[i])]
        plt.axvline(x=left_base, color='red', linestyle='--', linewidth=0.1)
        plt.axvline(x=right_base, color='red', linestyle='--', linewidth=0.1)
        plt.fill_between(time[int(left_ips[i]):int(right_ips[i]) + 1], 
                         baseline_corrected_data[int(left_ips[i]):int(right_ips[i]) + 1], 
                         color='gray', alpha=0.5)
    
    plt.title('Chromatogram with Detected Peaks (Baseline Corrected)')
    plt.xlabel('Time (min)')
    plt.ylabel('Absorbance (mAU)')
    plt.legend()

    # Save the plot as a PNG file
    plt.savefig(os.path.join(peaks_plots_dir, f'peaks_{os.path.splitext(filename)[0]}.png'), dpi=300)

    # Close the figure
    plt.close()

    return compound_list