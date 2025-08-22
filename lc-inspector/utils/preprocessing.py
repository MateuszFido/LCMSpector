import logging
import copy
import numpy as np
import pandas as pd
from pyteomics import auxiliary
import static_frame as sf
logger = logging.getLogger(__name__)
try:
    from utils.peak_integration import safe_peak_integration, \
        integrate_ms_xic_peak, create_fallback_peak_area                 
except ImportError:
    logger.warning("Peak integration module not found, using simple sum.")

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
    logger.info("Baseline corrected chromatogram calculated.")
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


def construct_xics(data, ion_list, mass_accuracy, file_name):
    """
    Creates XICs (extracted ion chromatograms) for a list of ions and Scan objects for a given data file.

    Parameters
    ----------
    data : List of Scan objects
        The list of Scan objects containing the MS data.
    ion_list : List of Compound objects
        The list of Compounds to generate XICs for.
    mass_accuracy : float
        The mass accuracy to use for XIC extraction.
    file_name : str
        The name of the file being processed.

    Returns
    -------
    Tuple of Compound objects
        A tuple of Compound objects with XICs computed.
    """
    # Precompute scan metadata to avoid repeated expensive XML lookups
    scan_times = np.array([auxiliary.cvquery(scan, 'MS:1000016') for scan in data])
    
    compounds = []
    for compound in ion_list:
        new_compound = copy.copy(compound)  # Shallow copy the compound
        new_compound.ions = copy.deepcopy(compound.ions)  # Deep copy the ions dict
        new_compound.file = file_name
        compounds.append(new_compound)
    
    # Group ions by compound
    ion_to_compounds = {}
    for idx, compound in enumerate(compounds):
        for ion in compound.ions.keys():
            if ion not in ion_to_compounds:
                ion_to_compounds[ion] = []
            ion_to_compounds[ion].append((idx, ion))
    
    # Process each unique ion only once
    for ion, compound_refs in ion_to_compounds.items():
        # Find a range around the ion
        mass_range = (ion-3*mass_accuracy, ion+3*mass_accuracy)
        # Safeguard for negative m/z
        if mass_range[0] < 0:
            mass_range = (0, mass_range[1])
            logger.error(f"Mass range for ion {ion} starting at less than 0, setting to 0.")
        
        # Process all scans for this ion at once
        xic_intensities = np.zeros(len(data))
        
        # Use binary search for range finding
        for i, scan in enumerate(data):
            mz_array = scan['m/z array']
            intensity_array = scan['intensity array']
            
            start_idx = np.searchsorted(mz_array, mass_range[0], side='left')
            end_idx = np.searchsorted(mz_array, mass_range[1], side='right')
            
            if start_idx < end_idx:  # Only sum if we have values in range
                xic_intensities[i] = np.sum(intensity_array[start_idx:end_idx])
        
        xic = np.array((scan_times, xic_intensities))
        max_idx = np.argmax(xic_intensities)
        
        # Apply results to all compounds that need this ion
        for comp_idx, ion_key in compound_refs:
            compound = compounds[comp_idx]
            compound.ions[ion_key]['MS Intensity'] = xic
            
            # Get the scan time of the index with the highest intensity
            try:
                compound.ions[ion_key]['RT'] = scan_times[max_idx]
            except Exception as e:
                compound.ions[ion_key]['RT'] = 0
                logger.error(f"Error: {e}")
            
            # Calculate peak area
            try:
                # Get RT of peak maximum for target
                rt_peak = compound.ions[ion_key]['RT']
                if rt_peak == 0:
                    rt_peak = xic[0][np.argmax(xic[1])] if len(xic[1]) > 0 else 0
                
                # Calculate peak area using trapezoidal integration
                peak_area_info = safe_peak_integration(
                    integrate_ms_xic_peak,
                    scan_times=xic[0],
                    intensities=xic[1],
                    rt_target=rt_peak,
                    mass_accuracy=mass_accuracy
                )
                compound.ions[ion_key]['MS Peak Area'] = peak_area_info
            except Exception as e:
                logger.warning(f"Peak area calculation failed for {ion_key} in {compound.name}: {e}")
                compound.ions[ion_key]['MS Peak Area'] = create_fallback_peak_area(xic[0], xic[1])
    
    return tuple(compounds)
