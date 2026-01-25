import logging
import numpy as np
import pandas as pd
import static_frame as sf
from pathlib import Path
from typing import Tuple
from pyteomics.mzml import MzML

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
    retention_time = dataframe["Time (min)"].values
    absorbance = dataframe["Value (mAU)"].values.copy()
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
            tform_new[j] = min(
                tform_new[j], 0.5 * (tform_new[j + i] + tform_new[j - i])
            )
        tform = tform_new

    # Perform the inverse of the LLS transformation and subtract
    inv_tform = (np.exp(np.exp(tform) - 1) - 1) ** 2 - 1
    baseline_corrected = np.round((absorbance - inv_tform), decimals=9)
    baseline = inv_tform + shift

    normalized = sf.FrameHE.from_dict(
        {
            "Time (min)": retention_time,
            "Value (mAU)": baseline_corrected,
            "Baseline": baseline,
            "Uncorrected": absorbance,
        }
    )
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


def build_xics(
    filepath: str, ion_list: np.typing.NDArray[np.float32], mass_accuracy: np.float64
) -> Tuple[np.typing.NDArray[np.float32], np.typing.NDArray[np.float32]]:
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

    # turn target_mzs into numpy array and pre-allocate result containers
    data = MzML(filepath)

    target_mzs = np.asarray(ion_list, dtype=np.float32)
    xic_intensities = np.zeros((len(data), len(target_mzs)), dtype=np.float32)
    scan_times = np.zeros(len(data), dtype=np.float32)

    # Compute tolerance windows for each target mz
    delta = target_mzs * mass_accuracy * 3
    lower = target_mzs - delta
    upper = target_mzs + delta

    for i, scan in enumerate(data):
        mz_array = scan["m/z array"]
        intensity_array = scan["intensity array"]
        scan_times[i] = scan["scanList"]["scan"][0]["scan start time"]

        # Binary search the arrays for mz ranges to sum in
        left_idx = np.searchsorted(mz_array, lower, side="left")
        right_idx = np.searchsorted(mz_array, upper, side="right")

        for ion_idx, (left, right) in enumerate(zip(left_idx, right_idx)):
            if left < right:  # Only sum if we have values in range
                xic_intensities[i, ion_idx] = np.sum(intensity_array[left:right])

    return xic_intensities, scan_times


def construct_xics(
    filepath: str,
    compounds: tuple,
    mass_accuracy: np.float64 = np.float64(0.0001),
):
    """Wrapper around build_xics for calling from ProcessPoolExecutor.
    Returns a list of *filled* Compound objects."""
    target_mzs = _extract_target_mzs(compounds)
    intensities, rts = build_xics(filepath, target_mzs, mass_accuracy)

    # Map results onto Compound objects
    mz_to_column = {mz: idx for idx, mz in enumerate(target_mzs)}  # lookup index

    for compound in compounds:
        compound.file = Path(filepath).name
        for ion in compound.ions:
            col = mz_to_column[ion]
            xic = np.array((rts, intensities[:, col]), dtype=np.float32)
            compound.ions[ion]["MS Intensity"] = xic
            max_idx = np.argmax(xic[1])
            compound.ions[ion]["RT"] = rts[max_idx]

            # TODO: additional integration logic

    return compounds


def _extract_target_mzs(compounds: tuple) -> np.ndarray:
    """Collect the m/z of every ion that appears in the supplied compounds."""
    mzs = []
    for cmpd in compounds:
        for ion in cmpd.ions:  # ion_info is a list of (ion_name, mz) tuples
            mzs.append(ion)  # info holds the exact m/z value
    return np.unique(np.asarray(mzs, dtype=np.float64))


def integrate_chromatogram(
    xic_data: np.ndarray, start_time: float, end_time: float
) -> float:
    """
    Parameters
    ----------
    xic_data : np.ndarray
        Shape (2, N). Row 0 is Time, Row 1 is Intensity.
    """
    times = xic_data[0]
    intensities = xic_data[1]

    # Boolean mask for the region of interest
    mask = (times >= start_time) & (times <= end_time)

    if not np.any(mask):
        return 0.0

    area = np.trapezoid(intensities[mask], times[mask])

    return float(area)
