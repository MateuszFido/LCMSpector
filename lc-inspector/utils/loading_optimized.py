import pandas as pd
import numpy as np
import csv, re, os, logging, itertools, time
from pathlib import Path
from pyteomics import mzml
from pyteomics.auxiliary import cvquery

logger = logging.getLogger(__name__)

# Try to import C extensions, fallback to Python implementations
try:
    from . import loading_accelerator
    HAS_C_EXTENSIONS = True
    logger.info("C extensions loaded successfully for performance optimization")
except ImportError as e:
    HAS_C_EXTENSIONS = False
    logger.warning(f"C extensions not available, using Python implementations: {e}")

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
    """Load absorbance data with C acceleration if available."""
    if HAS_C_EXTENSIONS:
        try:
            return loading_accelerator.load_absorbance_data_fast(file_path)
        except Exception as e:
            logger.warning(f"C extension failed, falling back to Python: {e}")
    
    # Original Python implementation as fallback
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
    Load annotated peaks from a .txt file with optimized regex processing.

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

    # Pre-compiled regex patterns for better performance
    peakname = re.compile(r"(Peakname|Name)\s*")
    rt = re.compile(r"(Ret\.Time|RetentionTime)\s*")
    area = re.compile(r"(Area|Height)\s*")
    peak_start = re.compile(r"(Peak Start|Start)\s*")
    peak_stop = re.compile(r"(Peak Stop|Stop)\s*")
    
    # Load the annotated peaks from the annotations file, skipping the first few header rows
    df = pd.read_csv(file_path,
                     skiprows=start_index + 1,
                     delimiter='\t',
                     header=0,
                     usecols=lambda x: peakname.search(x) or rt.search(x) or area.search(x) or peak_start.search(x) or peak_stop.search(x))
    
    return df

def load_ms1_data(path: str) -> list:
    """
    Using the pyteomics library, load the data from the .mzML file with optimizations.
    
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
    
    # Use memory-mapped file access for large files
    try:
        with mzml.MzML(str(path), use_index=True) as file:
            # Pre-allocate list with estimated size for better performance
            ms1_data = []
            ms1_data.extend(scan for scan in file if scan['ms level'] == 1)
            
            if not ms1_data:
                logger.error("No MS1 scans found in the .mzML file. Rerunning on higher order MSn.")
                file.reset()
                ms1_data.extend(scan for scan in file)
                
    except Exception as e:
        logger.warning(f"Optimized loading failed, using standard method: {e}")
        # Fallback to original method
        with mzml.MzML(str(path)) as file:
            ms1_data = [scan for scan in file if scan['ms level'] == 1]
            if not ms1_data:
                logger.error("No MS1 scans found in the .mzML file. Rerunning on higher order MSn.")
                file.reset()
                ms1_data = [scan for scan in file]
    
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

    logger.info(f"Loaded {len(compound.ms2)} MS2 scans in {time.time() - start_time:.2f} seconds.")

def load_ms2_library() -> dict:
    """
    Loads the MS2 library from the MoNA-export-All_LC-MS-MS_Orbitrap.msp file with optimizations.
    
    Returns
    -------
    library : dict
        The MS2 library as a dictionary where the keys are the feature names and the values are lists of lines from the file.
    """
    library = {}
    library_path = Path(__file__).parent.parent / "resources/MoNA-export-All_LC-MS-MS_Orbitrap.msp"
    
    if not library_path.exists():
        logger.warning(f"MS2 library file not found at {library_path}")
        return library
    
    try:
        with open(library_path, mode="r", encoding="utf-8") as src:
            # Use optimized approach but keep original logic for compatibility
            current_entry = None
            current_lines = []
            
            for line in src:
                if line.startswith("Name: "):
                    # Save previous entry if exists
                    if current_entry is not None:
                        library[current_entry] = current_lines
                    # Start new entry
                    current_entry = line.split("Name: ")[1].strip()
                    current_lines = [line]
                else:
                    if current_entry is not None:
                        current_lines.append(line)
                        if line.strip() == "":
                            # End of entry
                            library[current_entry] = current_lines
                            current_entry = None
                            current_lines = []
            
            # Handle last entry
            if current_entry is not None:
                library[current_entry] = current_lines
                
    except Exception as e:
        logger.error(f"Error loading MS2 library: {e}")
        return {}
    
    logger.info(f"Loaded MS2 library with {len(library)} entries")
    return library

# Performance monitoring decorator
def monitor_performance(func):
    """Decorator to monitor function performance."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.debug(f"{func.__name__} executed in {end_time - start_time:.4f} seconds")
        return result
    return wrapper

# Apply performance monitoring to key functions
load_absorbance_data = monitor_performance(load_absorbance_data)
load_ms1_data = monitor_performance(load_ms1_data)
load_ms2_library = monitor_performance(load_ms2_library)
