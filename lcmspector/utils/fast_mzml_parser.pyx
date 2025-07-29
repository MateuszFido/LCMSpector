# fast_mzml_parser.pyx
# High-performance mzML parser using Cython
# FIXME: Unused 
import numpy as np
cimport numpy as cnp
from libc.stdlib cimport malloc, free
from libc.string cimport strcmp
import xml.etree.ElementTree as ET
import base64
import struct
import zlib
import logging
import time
import os

logger = logging.getLogger(__name__)

# Type definitions for better performance
ctypedef cnp.float64_t DTYPE_t
DTYPE = np.float64

cdef class FastMS1Scan:
    """Fast MS1 scan data structure."""
    cdef public double scan_time
    cdef public cnp.ndarray mz_array
    cdef public cnp.ndarray intensity_array
    cdef public int ms_level
    cdef public double total_ion_current
    
    def __init__(self, double scan_time, cnp.ndarray mz_array, cnp.ndarray intensity_array, 
                 int ms_level=1, double total_ion_current=0.0):
        self.scan_time = scan_time
        self.mz_array = mz_array
        self.intensity_array = intensity_array
        self.ms_level = ms_level
        self.total_ion_current = total_ion_current
    
    def __getitem__(self, key):
        """Dictionary-like access for compatibility with pyteomics."""
        if key == 'ms level':
            return self.ms_level
        elif key == 'm/z array':
            return self.mz_array
        elif key == 'intensity array':
            return self.intensity_array
        elif key == 'scan time':
            return self.scan_time
        elif key == 'total ion current':
            return self.total_ion_current
        else:
            raise KeyError(f"Key '{key}' not found")
    
    def get(self, key, default=None):
        """Dictionary-like get method."""
        try:
            return self[key]
        except KeyError:
            return default

cdef cnp.ndarray decode_binary_data(str binary_data, str precision, str compression):
    """
    Fast binary data decoding for mzML files.
    
    Parameters:
    -----------
    binary_data : str
        Base64 encoded binary data
    precision : str
        '32' or '64' for float precision
    compression : str
        'none', 'zlib', or 'gzip'
    """
    cdef bytes decoded_data = base64.b64decode(binary_data)
    
    # Handle compression
    if compression == 'zlib':
        decoded_data = zlib.decompress(decoded_data)
    elif compression == 'gzip':
        import gzip
        decoded_data = gzip.decompress(decoded_data)
    
    # Convert to numpy array based on precision
    if precision == '32':
        return np.frombuffer(decoded_data, dtype=np.float32).astype(np.float64)
    else:
        return np.frombuffer(decoded_data, dtype=np.float64)

def parse_ms1_fast(str file_path):
    """
    Fast MS1 data parsing from mzML files.
    
    This function provides significant performance improvements over pyteomics
    by using optimized XML parsing and binary data decoding.
    
    Parameters:
    -----------
    file_path : str
        Path to the mzML file
        
    Returns:
    --------
    list
        List of FastMS1Scan objects compatible with pyteomics API
    """
    cdef list ms1_scans = []
    cdef double scan_time
    cdef int ms_level
    cdef cnp.ndarray mz_array, intensity_array
    cdef str precision, compression
    cdef double file_size_mb
    
    # Get file size for optimizing strategy
    file_size = os.path.getsize(file_path)
    file_size_mb = file_size / (1024 * 1024)
    
    logger.info(f"Fast parsing mzML file: {file_path} ({file_size_mb:.1f} MB)")
    start_time = time.time()
    
    try:
        # Parse XML with iterparse for memory efficiency
        context = ET.iterparse(file_path, events=('start', 'end'))
        context = iter(context)
        event, root = next(context)
        
        cdef int scan_count = 0
        cdef int ms1_count = 0
        cdef int batch_size = max(10, min(100, int(file_size_mb / 10)))  # Adjust batch size based on file size
        cdef list current_batch = []
        
        for event, elem in context:
            if event == 'end' and elem.tag.endswith('spectrum'):
                scan_count += 1
                
                # Extract MS level
                ms_level = 1  # default
                for param in elem.findall('.//{*}cvParam'):
                    if param.get('accession') == 'MS:1000511':  # MS level
                        ms_level = int(param.get('value', '1'))
                        break
                
                # Only process MS1 scans
                if ms_level == 1:
                    # Extract scan time
                    scan_time = 0.0
                    for param in elem.findall('.//{*}cvParam'):
                        if param.get('accession') == 'MS:1000016':  # scan start time
                            scan_time = float(param.get('value', '0'))
                            break
                    
                    # Extract binary data arrays
                    mz_array = None
                    intensity_array = None
                    
                    for binary_data_array in elem.findall('.//{*}binaryDataArray'):
                        # Determine array type (m/z or intensity)
                        array_type = None
                        precision = '64'
                        compression = 'none'
                        
                        for param in binary_data_array.findall('.//{*}cvParam'):
                            accession = param.get('accession')
                            if accession == 'MS:1000514':  # m/z array
                                array_type = 'mz'
                            elif accession == 'MS:1000515':  # intensity array
                                array_type = 'intensity'
                            elif accession == 'MS:1000521':  # 32-bit float
                                precision = '32'
                            elif accession == 'MS:1000523':  # 64-bit float
                                precision = '64'
                            elif accession == 'MS:1000574':  # zlib compression
                                compression = 'zlib'
                        
                        # Decode binary data
                        binary_elem = binary_data_array.find('.//{*}binary')
                        if binary_elem is not None and binary_elem.text:
                            try:
                                decoded_array = decode_binary_data(binary_elem.text.strip(), 
                                                                 precision, compression)
                                
                                if array_type == 'mz':
                                    mz_array = decoded_array
                                elif array_type == 'intensity':
                                    intensity_array = decoded_array
                            except Exception as decode_error:
                                logger.warning(f"Failed to decode binary data: {decode_error}")
                    
                    # Create scan object if we have both arrays
                    if mz_array is not None and intensity_array is not None:
                        # Make arrays the same size if they differ (happens in some files)
                        if len(mz_array) != len(intensity_array):
                            min_len = min(len(mz_array), len(intensity_array))
                            mz_array = mz_array[:min_len]
                            intensity_array = intensity_array[:min_len]
                            
                        # Sort by m/z if needed (not always ordered in files)
                        if not np.all(np.diff(mz_array) >= 0):
                            sort_idx = np.argsort(mz_array)
                            mz_array = mz_array[sort_idx]
                            intensity_array = intensity_array[sort_idx]
                            
                        # Calculate total ion current
                        total_ion_current = np.sum(intensity_array)
                        
                        # Create scan with dictionary-like API for compatibility
                        scan = FastMS1Scan(scan_time, mz_array, intensity_array, 
                                         ms_level, total_ion_current)
                        ms1_scans.append(scan)
                        ms1_count += 1
                
                # Clear element to save memory
                elem.clear()
                root.clear()
                
                # Progress logging for large files
                if scan_count % batch_size == 0:
                    parse_speed = scan_count / (time.time() - start_time)
                    logger.debug(f"Processed {scan_count} scans ({parse_speed:.0f} scans/sec), found {ms1_count} MS1 scans")
                    
                    # Memory optimization for very large files
                    if file_size_mb > 500 and scan_count % (batch_size * 10) == 0:
                        import gc
                        gc.collect()
        
        parse_time = time.time() - start_time
        parse_speed = scan_count / parse_time if parse_time > 0 else 0
        logger.info(f"Fast parsed {ms1_count} MS1 scans from {scan_count} total scans in {parse_time:.2f} seconds ({parse_speed:.0f} scans/sec)")
        
        return ms1_scans
        
    except Exception as e:
        logger.error(f"Fast mzML parsing failed: {e}")
        # Return an empty list instead of raising to ensure fallback works
        return []

def parse_ms1_with_xic_optimization(str file_path, list target_masses, double mass_accuracy):
    """
    Parse MS1 data with XIC optimization - only extract data for target masses.
    
    This provides even better performance when you know the target masses in advance.
    
    Parameters:
    -----------
    file_path : str
        Path to the mzML file
    target_masses : list
        List of target m/z values
    mass_accuracy : float
        Mass accuracy for m/z matching
        
    Returns:
    --------
    tuple
        (ms1_scans, xic_data) where xic_data is pre-computed XIC intensities
    """
    cdef list ms1_scans = []
    cdef cnp.ndarray target_array = np.array(target_masses, dtype=np.float64)
    cdef double mass_tolerance = 3 * mass_accuracy
    cdef cnp.ndarray xic_intensities = np.zeros((len(target_masses), 0), dtype=np.float64)
    cdef list scan_times = []
    
    logger.info(f"Fast parsing with XIC optimization for {len(target_masses)} targets")
    
    try:
        context = ET.iterparse(file_path, events=('start', 'end'))
        context = iter(context)
        event, root = next(context)
        
        cdef int scan_count = 0
        cdef int ms1_count = 0
        
        for event, elem in context:
            if event == 'end' and elem.tag.endswith('spectrum'):
                # Extract MS level
                ms_level = 1
                for param in elem.findall('.//{*}cvParam'):
                    if param.get('accession') == 'MS:1000511':
                        ms_level = int(param.get('value', '1'))
                        break
                
                scan_count += 1
                
                if ms_level == 1:
                    # Extract scan time
                    scan_time = 0.0
                    for param in elem.findall('.//{*}cvParam'):
                        if param.get('accession') == 'MS:1000016':
                            scan_time = float(param.get('value', '0'))
                            break
                    
                    # Extract and process binary data
                    mz_array = None
                    intensity_array = None
                    
                    for binary_data_array in elem.findall('.//{*}binaryDataArray'):
                        array_type = None
                        precision = '64'
                        compression = 'none'
                        
                        for param in binary_data_array.findall('.//{*}cvParam'):
                            accession = param.get('accession')
                            if accession == 'MS:1000514':
                                array_type = 'mz'
                            elif accession == 'MS:1000515':
                                array_type = 'intensity'
                            elif accession == 'MS:1000521':
                                precision = '32'
                            elif accession == 'MS:1000523':
                                precision = '64'
                            elif accession == 'MS:1000574':
                                compression = 'zlib'
                        
                        binary_elem = binary_data_array.find('.//{*}binary')
                        if binary_elem is not None and binary_elem.text:
                            decoded_array = decode_binary_data(binary_elem.text.strip(), 
                                                             precision, compression)
                            
                            if array_type == 'mz':
                                mz_array = decoded_array
                            elif array_type == 'intensity':
                                intensity_array = decoded_array
                    
                    if mz_array is not None and intensity_array is not None:
                        # Calculate XIC intensities for target masses
                        cdef cnp.ndarray current_xic = np.zeros(len(target_masses), dtype=np.float64)
                        
                        for i, target_mass in enumerate(target_masses):
                            # Find mass range indices using binary search
                            low_mass = target_mass - mass_tolerance
                            high_mass = target_mass + mass_tolerance
                            
                            start_idx = np.searchsorted(mz_array, low_mass, side='left')
                            end_idx = np.searchsorted(mz_array, high_mass, side='right')
                            
                            if start_idx < end_idx:
                                current_xic[i] = np.sum(intensity_array[start_idx:end_idx])
                        
                        # Append to XIC data
                        if xic_intensities.shape[1] == 0:
                            xic_intensities = current_xic.reshape(-1, 1)
                        else:
                            xic_intensities = np.column_stack([xic_intensities, current_xic])
                        
                        scan_times.append(scan_time)
                        
                        # Create scan object
                        total_ion_current = np.sum(intensity_array)
                        scan = FastMS1Scan(scan_time, mz_array, intensity_array, 
                                         ms_level, total_ion_current)
                        ms1_scans.append(scan)
                        ms1_count += 1
                
                elem.clear()
                root.clear()
        
        logger.info(f"Fast parsed with XIC optimization: {ms1_count} MS1 scans")
        
        # Return both scans and pre-computed XIC data
        return ms1_scans, {
            'xic_intensities': xic_intensities,
            'scan_times': np.array(scan_times),
            'target_masses': target_array
        }
        
    except Exception as e:
        logger.error(f"Fast mzML parsing with XIC optimization failed: {e}")
        raise
