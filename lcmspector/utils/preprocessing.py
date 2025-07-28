import numpy as np
import pandas as pd
from lcmspector.utils.loading import load_absorbance_data
import logging, copy
from pyteomics import auxiliary
from scipy.signal import find_peaks, peak_widths
import static_frame as sf
import cython

logger = logging.getLogger(__name__)
def baseline_correction(dataframe: pd.DataFrame) -> sf.FrameHE:    
    """
    Baseline corrects the chromatogram using the LLS algorithm.

    Parameters
    ----------
    dataframe : sf.FrameHE
        The chromatogram data as a static-frame FrameHE object.

    Returns
    -------
    sf.FrameHE
        The baseline corrected chromatogram as a static-frame FrameHE object.

    Notes
    -----
    Baseline correction is a preprocessing step that subtracts the baseline from the chromatogram.
    The baseline is estimated using the LLS algorithm.
    """
    # Extract Time (min) and Value (mAU) columns
    retention_time = dataframe.copy()['Time (min)'].values
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
        
    normalized = sf.FrameHE.from_dict({'Time (min)': retention_time, 'Value (mAU)': baseline_corrected, 'Baseline': baseline, 'Uncorrected': absorbance})
    logger.info(f"Baseline corrected chromatogram calculated.")
    return normalized

# Currently unused 
# def calculate_mz_axis(data: list, mass_accuracy: float) -> np.ndarray:
    
#     """
#     Calculate the m/z axis from a list of Scan objects.

#     Parameters
#     ----------
#     data : List of Scan objects
#         The list of Scan objects containing the MS data.

#     Returns
#     -------
#     mz_axis : np.ndarray
#         The m/z axis for the intensity values.
#     """
    
#     # Look up the necessary fields from the first scan in the file for m/z axis determination

#     low_mass = auxiliary.cvquery(data[0], 'MS:1000501')-10 # +10 m/z for safety in case the MS recorded beyond limit
#     high_mass = auxiliary.cvquery(data[0], 'MS:1000500')+10
#     # Calculate the resolution of the m/z axis
#     resolution = int((high_mass - low_mass) / mass_accuracy) 
#     # Create the m/z axis, rounded appropriately
#     mz_axis = np.round(np.linspace(low_mass, high_mass, resolution, dtype=np.float64), decimals=len(str(mass_accuracy).split('.')[1]))
#     return mz_axis


def construct_xics(data, ion_list, mass_accuracy):
    compounds = copy.deepcopy(ion_list)
    
    # Detect if we're using the new format from Rust
    is_rust_format = data and isinstance(data[0], dict) and 'mzs' in data[0]
    
    for compound in compounds:
        for ion in compound.ions.keys():
            xic = []
            scan_id = []
            # Find a range around the ion (theoretical mass - observed mass)
            mass_range = (float(ion)-3*mass_accuracy, float(ion)+3*mass_accuracy)
            # Safeguard for if mass_range is less than 0
            if mass_range[0] < 0:
                mass_range = (0, mass_range[1])
                logger.error(f"Mass range for ion {ion} starting at less than 0, setting to 0.")
            
            for scan in data:
                if is_rust_format:
                    # New format from Rust
                    mzs = scan.get('mzs', [])
                    intensities_array = scan.get('intensities', [])
                    scan_time = scan.get('scan_time', 0)
                    
                    # Convert to numpy arrays if they aren't already
                    if not isinstance(mzs, np.ndarray):
                        mzs = np.array(mzs)
                    if not isinstance(intensities_array, np.ndarray):
                        intensities_array = np.array(intensities_array)
                    
                    indices = np.where(np.logical_and(mzs >= mass_range[0], mzs <= mass_range[1]))
                    intensities = intensities_array[indices]
                else:
                    # Old format
                    indices = np.where(np.logical_and(scan['m/z array'] >= mass_range[0], scan['m/z array'] <= mass_range[1]))
                    intensities = scan['intensity array'][indices]
                    scan_time = auxiliary.cvquery(scan, 'MS:1000016')
                
                xic.append(np.sum(intensities))
                scan_id.append(scan_time)
            
            xic = np.array((scan_id, xic))
            compound.ions[ion]['MS Intensity'] = xic
            
            # Get the scan time of the index with the highest intensity
            try:
                if xic[1].size > 0:
                    max_index = int(np.argmax(xic[1]))
                    compound.ions[ion]['RT'] = scan_id[max_index]
                else:
                    compound.ions[ion]['RT'] = 0
            except Exception as e:
                compound.ions[ion]['RT'] = 0
                logger.error(f"Error calculating RT for ion {ion}: {e}")
    return tuple(compounds)
