import numpy as np
import pandas as pd
from utils.loading import load_absorbance_data
import logging, copy
from pyteomics import auxiliary
from scipy.signal import find_peaks, peak_widths
import static_frame as sf
from concurrent.futures import ThreadPoolExecutor
import time
import joblib
import os.path

logger = logging.getLogger(__name__)

def get_cache_path(prefix, path):
    """Generate a cache file path for intermediate results"""
    cache_dir = os.path.join(os.path.dirname(path), ".cache")
    os.makedirs(cache_dir, exist_ok=True)
    basename = os.path.basename(path)
    return os.path.join(cache_dir, f"{prefix}_{basename}.joblib")

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
    
    # Determine if we need to shift the baseline
    if (absorbance < 0).any():
        shift = np.median(absorbance[absorbance < 0])
    else:
        shift = 0
        
    # Apply shift and filter negative values
    absorbance -= shift
    absorbance *= np.heaviside(absorbance, 0)
    
    # Compute the LLS operator - using NumPy vectorized operations
    tform = np.log(np.log(np.sqrt(absorbance + 1) + 1) + 1)

    # Compute the number of iterations given the window size.
    n_iter = 20

    # Optimization: Use NumPy's minimum function for faster computation
    for i in range(1, n_iter + 1):
        tform_new = tform.copy()
        for j in range(i, len(tform) - i):
            tform_new[j] = min(tform_new[j], 0.5 * (tform_new[j+i] + tform_new[j-i]))
        tform = tform_new

    # Perform the inverse of the LLS transformation and subtract
    inv_tform = ((np.exp(np.exp(tform) - 1) - 1)**2 - 1)
    baseline_corrected = np.round((absorbance - inv_tform), decimals=9)
    baseline = inv_tform + shift 
        
    normalized = sf.FrameHE.from_dict({
        'Time (min)': retention_time, 
        'Value (mAU)': baseline_corrected, 
        'Baseline': baseline, 
        'Uncorrected': absorbance
    })
    
    logger.info(f"Baseline corrected chromatogram calculated.")
    return normalized

def process_ion_chunk(data_chunk, ions_chunk, mass_accuracy):
    """Process a subset of ions for a subset of scans in parallel"""
    results = {}
    
    for ion in ions_chunk:
        xic = []
        scan_id = []
        # Find a range around the ion (theoretical mass - observed mass)
        mass_range = (ion-3*mass_accuracy, ion+3*mass_accuracy)
        # Safeguard for if mass_range is less than 0
        if mass_range[0] < 0:
            mass_range = (0, mass_range[1])
            logger.error(f"Mass range for ion {ion} starting at less than 0, setting to 0.")
            
        for scan in data_chunk:
            # Use numpy's logical_and and where functions for efficient filtering
            indices = np.where(np.logical_and(scan['m/z array'] >= mass_range[0], 
                                              scan['m/z array'] <= mass_range[1]))
            intensities = scan['intensity array'][indices]
            xic.append(np.sum(intensities))
            scan_id.append(auxiliary.cvquery(scan, 'MS:1000016'))
            
        results[ion] = np.array((scan_id, xic))
        
    return results

def construct_xics(data, ion_list, mass_accuracy):
    """
    Construct extracted ion chromatograms (XICs) with optimizations:
    1. Caching results
    2. Parallel processing using ThreadPoolExecutor
    3. Chunking data for more efficient memory usage
    
    Parameters
    ----------
    data : list
        List of MS scan data.
    ion_list : list
        List of compounds containing ion information.
    mass_accuracy : float
        Mass accuracy to use for m/z filtering.
        
    Returns
    -------
    tuple
        Tuple of compounds with XICs.
    """
    start_time = time.time()
    compounds = copy.deepcopy(ion_list)
    
    # Check if we have a valid path for caching
    if data and len(data) > 0 and isinstance(data[0], dict) and 'id' in data[0]:
        scan_id = data[0]['id']
        if isinstance(scan_id, str) and 'file=' in scan_id:
            # Extract file path from scan ID
            file_path = scan_id.split('file=')[1].split(' ')[0]
            cache_path = get_cache_path('xics', file_path)
            
            # Try to load from cache
            if os.path.exists(cache_path):
                try:
                    cached_results = joblib.load(cache_path)
                    cached_ion_keys = set([ion for compound in cached_results for ion in compound.ions.keys()])
                    current_ion_keys = set([ion for compound in ion_list for ion in compound.ions.keys()])
                    
                    # If all current ions are in the cache, use the cached results
                    if current_ion_keys.issubset(cached_ion_keys):
                        logger.info(f"Loaded XICs from cache in {time.time() - start_time:.2f} seconds.")
                        filtered_results = []
                        for compound in ion_list:
                            # Find matching compound in cache
                            cached_compound = next((c for c in cached_results if c.name == compound.name), None)
                            if cached_compound:
                                # Copy only the requested ions
                                new_compound = copy.deepcopy(compound)
                                for ion in compound.ions.keys():
                                    if ion in cached_compound.ions:
                                        new_compound.ions[ion] = cached_compound.ions[ion]
                                filtered_results.append(new_compound)
                        return tuple(filtered_results)
                except Exception as e:
                    logger.warning(f"Failed to load XICs from cache: {e}")
    
    # If not cached or cache load failed, calculate XICs with optimization
    # Determine optimal chunk size for parallelization
    num_cpus = os.cpu_count() or 4
    
    with ThreadPoolExecutor(max_workers=num_cpus) as executor:
        # Process each compound's ions in parallel
        for compound_idx, compound in enumerate(compounds):
            # Collect all ions for this compound
            all_ions = list(compound.ions.keys())
            
            # Split ions into chunks for parallel processing
            chunk_size = max(1, len(all_ions) // num_cpus)
            ion_chunks = [all_ions[i:i + chunk_size] for i in range(0, len(all_ions), chunk_size)]
            
            # Submit tasks to the executor
            futures = []
            for ions_chunk in ion_chunks:
                future = executor.submit(process_ion_chunk, data, ions_chunk, mass_accuracy)
                futures.append(future)
            
            # Collect results and update compound
            for future in futures:
                chunk_results = future.result()
                for ion, xic_data in chunk_results.items():
                    compound.ions[ion]['MS Intensity'] = xic_data
                    # Get the scan time of the index with the highest intensity
                    try:
                        max_idx = int(np.argmax(xic_data[1]))
                        if 0 <= max_idx < len(data):
                            compound.ions[ion]['RT'] = auxiliary.cvquery(data[max_idx], 'MS:1000016')
                        else:
                            compound.ions[ion]['RT'] = 0
                            logger.warning(f"Index {max_idx} out of range for data with length {len(data)}")
                    except Exception as e:
                        compound.ions[ion]['RT'] = 0
                        logger.error(f"Error setting RT for ion {ion}: {e}")
    
    # Cache results if possible
    if data and len(data) > 0 and isinstance(data[0], dict) and 'id' in data[0]:
        scan_id = data[0]['id']
        if isinstance(scan_id, str) and 'file=' in scan_id:
            # Extract file path from scan ID
            file_path = scan_id.split('file=')[1].split(' ')[0]
            cache_path = get_cache_path('xics', file_path)
            try:
                joblib.dump(compounds, cache_path, compress=3)
                logger.info(f"Cached XICs to {cache_path}")
            except Exception as e:
                logger.warning(f"Failed to cache XICs: {e}")
    
    logger.info(f"Constructed XICs in {time.time() - start_time:.2f} seconds.")
    return tuple(compounds)
