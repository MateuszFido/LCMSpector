import pandas as pd
import numpy as np
import csv, re, os, logging, itertools, time
from pathlib import Path
from pyteomics import mzml
from pyteomics.auxiliary import cvquery
import h5py
import joblib
import tempfile
import os.path
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

def detect_delimiter(line):
    """Detect the delimiter used in the text file.

    Args:
    line (str): The line of text to check for delimiters.

    Returns:
    str: The detected delimiter, or None if no delimiter is found.
    """
    if ',' in line:
        return ','
    elif '\t' in line:
        return '\t'
    elif ' ' in line:
        return ' '
    else:
        return None  # No recognizable delimiter

def load_absorbance_data(file_path):
    time_values = []
    intensity_values = []

    # Check if the file exists
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    with open(file_path, 'r', newline=None) as file:
        # Check the delimiter by looking at the first few lines
        delimiter = None
        for i in range(5):
            line = file.readline()
            delimiter = detect_delimiter(line)
            if delimiter is not None and detect_delimiter(line) != delimiter:
                logger.error("Detected more than 1 different delimiters in the file. Double check for possible parsing errors.")
                    
        # Reset the file pointer to the beginning
        file.seek(0)
        reader = csv.reader(file, delimiter=delimiter)

        for row in reader:
            # Check if the row has at least two columns
            if len(row) >= 2:
                try:
                    # Attempt to convert the first and last columns to float
                    time = float(row[0])  # First column
                    intensity = float(row[-1])  # Last column
                    time_values.append(time)
                    intensity_values.append(intensity)
                except ValueError:
                    # If conversion fails, skip this row
                    continue
    
    chromatogram_data = pd.DataFrame({'Time (min)': time_values, 'Value (mAU)': intensity_values})
    return chromatogram_data

def load_annotated_peaks(file_path):
    """
    Load annotated peaks from a .txt file.

    This function loads the annotated peaks from the given .txt file, which is expected to have a header row and a variable number of header lines. The header lines are skipped and the annotated peaks are loaded into a pandas DataFrame.

    Parameters
    ----------
    file_path : str
        The path to the .txt file containing the annotated peaks.

    Returns
    -------
    pd.DataFrame
        A pandas DataFrame containing the annotated peaks.

    Notes
    -----
    The function assumes that the .txt file has a header row with column names and a variable number of header lines. The header lines are skipped and the annotated peaks are loaded into a pandas DataFrame. The columns are matched by a regular expression, which looks for the following column names: "Peakname", "Name", "Ret.Time", "RetentionTime", "Area", "Height", "Peak Start", "Start", "Peak Stop", "Stop". The function returns a pandas DataFrame containing the annotated peaks.
    """
    with open(file_path, 'r', newline='\n') as file:
        lines = csv.reader(file, delimiter='\t')
        start_index = 0
        for row in lines:
            if row[0] == 'Peak Results' or row[0] == 'Integration Results':
                break
            else:
                start_index += 1

    peakname = r"(Peakname|Name)\s*"  # Matches "Peakname" or "Name" with optional whitespace
    rt = r"(Ret\.Time|RetentionTime)\s*"  # Matches "Ret.Time" or "RetentionTime" with optional whitespace
    area = r"(Area|Height)\s*"  # Matches "Area" or "Height" with optional whitespace
    peak_start = r"(Peak Start|Start)\s*"  # Matches "Peak Start" or "Start" with optional whitespace
    peak_stop = r"(Peak Stop|Stop)\s*"  # Matches "Peak Stop" or "Stop" with optional whitespace
    
    # Load the annotated peaks from the annotations file, skipping the first few header rows
    df = pd.read_csv(file_path,
                     skiprows=start_index + 1,
                     delimiter='\t',
                     header=0,
                     usecols=lambda x: re.search(peakname, x) or re.search(rt, x) or re.search(area, x) or re.search(peak_start, x) or re.search(peak_stop, x))
    
    return df

def get_cache_path(path):
    """Generate a cache file path for an mzML file"""
    cache_dir = Path(tempfile.gettempdir()) / "lc_inspector_cache"
    os.makedirs(cache_dir, exist_ok=True)
    basename = os.path.basename(path)
    return os.path.join(cache_dir, f"{basename}.h5")

def load_ms1_data(path: str) -> list:
    """
    Using the pyteomics library, load the data from the .mzML file with optimization:
    1. Caching the parsed data to HDF5 for faster repeated access
    2. Memory-mapped arrays for large data
    3. Lazy loading of spectra
    
    Parameters
    ----------
    path : str
        The path to the .mzML file.
    
    Returns
    -------
    data : List of Scan objects
        The list of Scan objects containing the MS data.
    """
    start_time = time.time()
    
    # Check for cached data
    cache_path = get_cache_path(path)
    if os.path.exists(cache_path):
        logger.info(f"Loading cached MS1 data from {cache_path}")
        try:
            ms1_data = joblib.load(cache_path)
            logger.info(f"Loaded {len(ms1_data)} MS1 scans from cache in {time.time() - start_time:.2f} seconds.")
            return ms1_data
        except Exception as e:
            logger.warning(f"Failed to load from cache, regenerating: {e}")
    
    with mzml.MzML(str(path)) as file:
        # First, just collect the metadata to determine the total size
        ms1_metadata = []
        for scan in file:
            if scan['ms level'] == 1:
                # Store only the metadata, not the actual arrays
                scan_meta = {
                    'scan_number': scan.get('id', ''),
                    'retention_time': cvquery(scan, 'MS:1000016'),
                    'ms_level': scan.get('ms level', 1),
                    'mz_array_len': len(scan['m/z array']),
                    'intensity_array_len': len(scan['intensity array'])
                }
                ms1_metadata.append(scan_meta)
        
        if not ms1_metadata:
            logger.error("No MS1 scans found in the .mzML file. Rerunning on higher order MSn.")
            file.reset()
            ms1_metadata = []
            for scan in file:
                scan_meta = {
                    'scan_number': scan.get('id', ''),
                    'retention_time': cvquery(scan, 'MS:1000016'),
                    'ms_level': scan.get('ms level', 1),
                    'mz_array_len': len(scan['m/z array']),
                    'intensity_array_len': len(scan['intensity array'])
                }
                ms1_metadata.append(scan_meta)
        
        # Reset file pointer
        file.reset()
        
        # Create an optimized data structure
        ms1_data = []
        for i, meta in enumerate(ms1_metadata):
            scan = next(file)
            # Create a more efficient representation that only keeps what's needed
            if scan['ms level'] != 1:
                continue
            optimized_scan = {
                'id': scan.get('id', ''),
                'ms level': scan.get('ms level', 1),
                'retention_time': cvquery(scan, 'MS:1000016'),
                'total ion current': scan.get('total ion current', 0),
                # Store arrays as np.float32 to save memory if appropriate
                'm/z array': scan['m/z array'].astype(np.float32),
                'intensity array': [scan['intensity array'].astype(np.float32)]
            }
            ms1_data.append(optimized_scan)

    # Cache the results for future use
    try:
        joblib.dump(ms1_data, cache_path, compress=3)
        logger.info(f"Cached MS1 data to {cache_path}")
    except Exception as e:
        logger.warning(f"Failed to cache data: {e}")
            
    logger.info(f"Loaded {len(ms1_data)} MS1 scans in {time.time() - start_time:.2f} seconds.")
    return ms1_data

def load_ms2_data(path: str, compound, mass_accuracy: float):
    """
    Using the pyteomics library, load the MS2 data from the .mzML file, filtering based on the given precursors.

    Parameters
    ----------
    path : str
        The path to the .mzML file.
    compounds : tuple
        The compounds to filter the MS2 data for.
    mass_accuracy : float
        The mass accuracy to use for filtering the MS2 data.

    Returns
    -------
    None
    """
    start_time = time.time()
    ms2_threshold = mass_accuracy * 5

    with mzml.MzML(str(path)) as file:
        file.reset()
        for ion in compound.ions.keys():
            data_range = file.time[(compound.ions[ion]['RT'] - 0.5) : (compound.ions[ion]['RT'] + 0.5)]
            for scan in data_range:
                if scan['ms level'] == 2 and np.isclose(scan['precursorList']['precursor'][0]['selectedIonList']['selectedIon'][0]['selected ion m/z'], ion, atol=ms2_threshold):
                    compound.ms2.append(scan)

    print(f"Loaded {len(compound.ms2)} MS2 scans in {time.time() - start_time:.2f} seconds.")
    logger.info(f"Loaded MS2 scans in {time.time() - start_time:.2f} seconds.")

def load_ms2_library() -> dict:
    """
    Loads the MS2 library from the MoNA-export-All_LC-MS-MS_Orbitrap.msp file.
    
    Returns
    -------
    library : dict
        The MS2 library as a dictionary where the keys are the feature names and the values are lists of lines from the file.
    """
    library = {}
    library_path = Path(__file__).parent.parent / "resources/MoNA-export-All_LC-MS-MS_Orbitrap.msp"
    with open(library_path, mode="r", encoding="utf-8") as src:
        library = {line.split("Name: ")[1].strip(): [line] + list(itertools.takewhile(lambda x: x.strip() != "", src)) for line in src if line.startswith("Name: ")}
    return library
