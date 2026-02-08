"""
Lightweight mzML reader using lxml iterparse.

Provides streaming access to mzML spectra without the overhead of pyteomics'
CV term resolution, unit conversion, and full dict construction. Designed for
performance-critical paths like TIC extraction and XIC building.
"""

import base64
import logging
import zlib

import numpy as np
from lxml.etree import iterparse

logger = logging.getLogger(__name__)

_NS = "http://psi.hupo.org/ms/mzml"
_SPECTRUM_TAG = f"{{{_NS}}}spectrum"
_CVPARAM_TAG = f"{{{_NS}}}cvParam"
_BINARY_DATA_ARRAY_TAG = f"{{{_NS}}}binaryDataArray"
_BINARY_TAG = f"{{{_NS}}}binary"
_SCAN_TAG = f"{{{_NS}}}scan"
_CHROMATOGRAM_TAG = f"{{{_NS}}}chromatogram"
_PRECURSOR_LIST_TAG = f"{{{_NS}}}precursorList"
_PRECURSOR_TAG = f"{{{_NS}}}precursor"
_SELECTED_ION_LIST_TAG = f"{{{_NS}}}selectedIonList"
_SELECTED_ION_TAG = f"{{{_NS}}}selectedIon"

# Accession constants
_MS_LEVEL = "MS:1000511"
_SCAN_START_TIME = "MS:1000016"
_TIC_ACC = "MS:1000285"
_MZ_ARRAY = "MS:1000514"
_INTENSITY_ARRAY = "MS:1000515"
_TIME_ARRAY = "MS:1000595"
_FLOAT_64 = "MS:1000523"
_FLOAT_32 = "MS:1000521"
_ZLIB = "MS:1000574"
_TIC_CHROMATOGRAM = "MS:1000235"
_SELECTED_ION_MZ = "MS:1000744"


def _decode_binary(raw_base64: str, is_zlib: bool, dtype: np.dtype) -> np.ndarray:
    """Decode base64 (+ optional zlib) binary data to numpy array."""
    decoded = base64.b64decode(raw_base64)
    if is_zlib:
        decoded = zlib.decompress(decoded)
    return np.frombuffer(decoded, dtype=dtype)


def _parse_binary_arrays(elem):
    """Extract binary data arrays from an element (spectrum or chromatogram).

    Returns a dict mapping array type ('mz', 'intensity', 'time') to numpy arrays.
    """
    arrays = {}
    for bda in elem.iter(_BINARY_DATA_ARRAY_TAG):
        is_zlib = False
        dtype = np.float64
        array_type = None

        for cv in bda.iterchildren(_CVPARAM_TAG):
            acc = cv.get("accession")
            if acc == _ZLIB:
                is_zlib = True
            elif acc == _FLOAT_64:
                dtype = np.float64
            elif acc == _FLOAT_32:
                dtype = np.float32
            elif acc == _MZ_ARRAY:
                array_type = "mz"
            elif acc == _INTENSITY_ARRAY:
                array_type = "intensity"
            elif acc == _TIME_ARRAY:
                array_type = "time"

        binary_elem = bda.find(_BINARY_TAG)
        if binary_elem is not None and binary_elem.text and array_type:
            arrays[array_type] = _decode_binary(
                binary_elem.text.strip(), is_zlib, dtype
            )

    return arrays


def extract_tic_chromatogram(filepath: str):
    """Try to extract pre-computed TIC from chromatogramList.

    Returns (times, intensities) as numpy arrays, or None if not found.
    """
    for event, elem in iterparse(filepath, tag=_CHROMATOGRAM_TAG):
        # Check if this chromatogram is a TIC
        is_tic = False
        for cv in elem.iterchildren(_CVPARAM_TAG):
            if cv.get("accession") == _TIC_CHROMATOGRAM:
                is_tic = True
                break

        if not is_tic:
            # Also check by id attribute
            if elem.get("id") == "TIC":
                is_tic = True

        if is_tic:
            arrays = _parse_binary_arrays(elem)
            elem.clear()
            if "time" in arrays and "intensity" in arrays:
                logger.info(
                    "TIC extracted from chromatogram element "
                    f"({len(arrays['time'])} points)"
                )
                return (
                    arrays["time"].astype(np.float64),
                    arrays["intensity"].astype(np.float64),
                )

        elem.clear()

    return None


def iter_scans(filepath: str):
    """Yield (scan_time, tic, ms_level, mz_array, intensity_array) per spectrum.

    Uses lxml iterparse for streaming — constant memory regardless of file size.
    Skips CV term resolution, unit conversion, and full dict construction.
    """
    for event, spectrum_elem in iterparse(filepath, tag=_SPECTRUM_TAG):
        scan_time = 0.0
        tic = 0.0
        ms_level = 1

        # Extract spectrum-level cvParams (ms level, TIC)
        for cv in spectrum_elem.iterchildren(_CVPARAM_TAG):
            acc = cv.get("accession")
            if acc == _MS_LEVEL:
                ms_level = int(cv.get("value"))
            elif acc == _TIC_ACC:
                tic = float(cv.get("value"))

        # Extract scan start time from <scan> element
        for scan_elem in spectrum_elem.iter(_SCAN_TAG):
            for cv in scan_elem.iterchildren(_CVPARAM_TAG):
                if cv.get("accession") == _SCAN_START_TIME:
                    scan_time = float(cv.get("value"))
            break  # Only need first scan element

        # Extract binary arrays
        arrays = _parse_binary_arrays(spectrum_elem)
        spectrum_elem.clear()  # Free memory

        mz_array = arrays.get("mz")
        intensity_array = arrays.get("intensity")

        if mz_array is not None and intensity_array is not None:
            yield scan_time, tic, ms_level, mz_array, intensity_array


def find_nearest_ms2(
    filepath: str,
    precursor_mz: float,
    target_rt: float,
    mz_tolerance: float = 0.5,
    rt_window: float = 2.0,
):
    """Find MS2 scan nearest to target_rt whose precursor matches precursor_mz.

    Streams all spectra, filtering by ms_level==2, RT window, and precursor m/z.
    Only decodes binary arrays for matching candidates to minimise overhead.

    Parameters
    ----------
    filepath : str
        Path to the mzML file.
    precursor_mz : float
        Target precursor m/z value to match.
    target_rt : float
        Target retention time in minutes.
    mz_tolerance : float
        Maximum allowed difference in m/z (Da). Default 0.5.
    rt_window : float
        Maximum allowed RT difference in minutes. Default 2.0.

    Returns
    -------
    tuple or None
        (scan_time, mz_array, intensity_array) of the best match, or None.
    """
    best = None
    best_rt_delta = float("inf")

    for event, spectrum_elem in iterparse(filepath, tag=_SPECTRUM_TAG):
        ms_level = 1
        scan_time = 0.0

        # Extract ms_level from spectrum-level cvParams
        for cv in spectrum_elem.iterchildren(_CVPARAM_TAG):
            acc = cv.get("accession")
            if acc == _MS_LEVEL:
                ms_level = int(cv.get("value"))
                break

        # Skip MS1 scans immediately
        if ms_level != 2:
            spectrum_elem.clear()
            continue

        # Extract scan start time
        for scan_elem in spectrum_elem.iter(_SCAN_TAG):
            for cv in scan_elem.iterchildren(_CVPARAM_TAG):
                if cv.get("accession") == _SCAN_START_TIME:
                    scan_time = float(cv.get("value"))
            break

        # Skip if outside RT window
        rt_delta = abs(scan_time - target_rt)
        if rt_delta > rt_window:
            spectrum_elem.clear()
            continue

        # Parse precursor m/z from <precursorList>
        precursor_match = False
        for precursor_list in spectrum_elem.iter(_PRECURSOR_LIST_TAG):
            for precursor_elem in precursor_list.iter(_SELECTED_ION_TAG):
                for cv in precursor_elem.iterchildren(_CVPARAM_TAG):
                    if cv.get("accession") == _SELECTED_ION_MZ:
                        found_mz = float(cv.get("value"))
                        if abs(found_mz - precursor_mz) <= mz_tolerance:
                            precursor_match = True
                        break
                if precursor_match:
                    break
            break

        if not precursor_match:
            spectrum_elem.clear()
            continue

        # Only decode binary for matching candidates
        if rt_delta < best_rt_delta:
            arrays = _parse_binary_arrays(spectrum_elem)
            mz_array = arrays.get("mz")
            intensity_array = arrays.get("intensity")
            if mz_array is not None and intensity_array is not None:
                best = (scan_time, mz_array, intensity_array)
                best_rt_delta = rt_delta

        spectrum_elem.clear()

    return best
