"""
Peak area integration module for LC-Inspector.

This module provides comprehensive peak area calculation functionality
for both MS XIC data and LC chromatogram data using trapezoidal integration
with automatic boundary detection.
"""

import numpy as np
from typing import Dict, Tuple, Union
from scipy.signal import find_peaks

try:
    from scipy.integrate import trapz
except ImportError:
    # For newer scipy versions where trapz has been moved
    from scipy.integrate import trapezoid as trapz
import logging
import copy

logger = logging.getLogger(__name__)


class PeakIntegrationError(Exception):
    """Base exception for peak integration errors."""

    pass


class InsufficientDataError(PeakIntegrationError):
    """Raised when insufficient data points for integration."""

    pass


class PoorPeakQualityError(PeakIntegrationError):
    """Raised when peak quality is below acceptable threshold."""

    pass


class BoundaryDetectionError(PeakIntegrationError):
    """Raised when peak boundaries cannot be reliably detected."""

    pass


def integrate_ms_xic_peak(
    scan_times: np.ndarray,
    intensities: np.ndarray,
    rt_target: float,
    mass_accuracy: float = 0.0001,
    min_peak_width: float = 0.1,  # minimum peak width in minutes
    max_peak_width: float = 5.0,  # maximum peak width in minutes
    noise_threshold: float = 1000.0,  # minimum intensity threshold
    smoothing_window: int = 5,  # smoothing window size
) -> Dict[str, Union[float, int, str]]:
    """
    Integrate MS XIC peak area using trapezoidal integration with automatic boundary detection.

    Parameters
    ----------
    scan_times : np.ndarray
        Array of scan times (retention times) in minutes
    intensities : np.ndarray
        Array of intensity values corresponding to scan times
    rt_target : float
        Target retention time for peak detection
    mass_accuracy : float
        Mass accuracy for peak detection (used for quality assessment)
    min_peak_width : float
        Minimum expected peak width in minutes
    max_peak_width : float
        Maximum expected peak width in minutes
    noise_threshold : float
        Minimum intensity threshold for peak detection
    smoothing_window : int
        Window size for Savitzky-Golay smoothing

    Returns
    -------
    Dict[str, Union[float, int, str]]
        Dictionary containing peak area information matching enhanced data structure

    Raises
    ------
    PeakIntegrationError
        If peak integration fails due to insufficient data or poor peak quality
    """

    # Validate input data
    if len(scan_times) < 5 or len(intensities) < 5:
        raise InsufficientDataError(f"Insufficient data points: {len(scan_times)}")

    if len(scan_times) != len(intensities):
        raise ValueError("scan_times and intensities must have same length")

    # Sort data by retention time
    sorted_indices = np.argsort(scan_times)
    times_sorted = scan_times[sorted_indices]
    intensities_sorted = intensities[sorted_indices]

    # Find peak maximum closest to target RT
    peak_index = find_peak_maximum(times_sorted, intensities_sorted, rt_target)

    # Detect peak boundaries
    try:
        start_idx, end_idx, baseline_start, baseline_end = detect_peak_boundaries(
            times_sorted,
            intensities_sorted,
            peak_index,
            rt_target,
            min_peak_width,
            max_peak_width,
            noise_threshold,
        )
    except BoundaryDetectionError:
        # Use fallback boundary detection
        start_idx, end_idx, baseline_start, baseline_end = fallback_boundary_detection(
            times_sorted, intensities_sorted, peak_index, min_peak_width, max_peak_width
        )

    # Calculate baseline
    baseline = calculate_baseline_linear(intensities_sorted, start_idx, end_idx)

    # Integrate peak area
    total_area, baseline_corrected_area = integrate_peak_area_trapezoidal(
        times_sorted, intensities_sorted, baseline, start_idx, end_idx
    )

    # Calculate quality metrics
    snr, quality_score = calculate_peak_quality_metrics(
        times_sorted, intensities_sorted, baseline, start_idx, end_idx, peak_index
    )

    # Calculate peak height
    peak_height = intensities_sorted[peak_index] - baseline[peak_index - start_idx]

    return {
        "total_area": float(total_area),
        "baseline_corrected_area": float(baseline_corrected_area),
        "start_time": float(times_sorted[start_idx]),
        "end_time": float(times_sorted[end_idx]),
        "start_index": int(start_idx),
        "end_index": int(end_idx),
        "baseline_start": float(baseline_start),
        "baseline_end": float(baseline_end),
        "peak_height": float(peak_height),
        "integration_method": "trapezoidal",
        "snr": float(snr),
        "quality_score": float(quality_score),
    }


def integrate_lc_peak(
    retention_times: np.ndarray,
    absorbances: np.ndarray,
    baseline_corrected: np.ndarray,
    rt_target: float,
    min_peak_width: float = 0.05,
    max_peak_width: float = 2.0,
    noise_threshold: float = 10.0,
    smoothing_window: int = 5,
) -> Dict[str, Union[float, int, str]]:
    """
    Integrate LC chromatogram peak area using trapezoidal integration.

    Parameters
    ----------
    retention_times : np.ndarray
        Array of retention times in minutes
    absorbances : np.ndarray
        Array of uncorrected absorbance values
    baseline_corrected : np.ndarray
        Array of baseline-corrected absorbance values
    rt_target : float
        Target retention time for peak detection
    min_peak_width : float
        Minimum expected peak width in minutes
    max_peak_width : float
        Maximum expected peak width in minutes
    noise_threshold : float
        Minimum absorbance threshold for peak detection
    smoothing_window : int
        Window size for Savitzky-Golay smoothing

    Returns
    -------
    Dict[str, Union[float, int, str]]
        Dictionary containing LC peak area information
    """

    # Validate input data
    if len(retention_times) < 5:
        raise InsufficientDataError(f"Insufficient data points: {len(retention_times)}")

    # Find peak maximum closest to target RT
    peak_index = find_peak_maximum(retention_times, baseline_corrected, rt_target)

    # Detect boundaries using baseline-corrected data
    try:
        start_idx, end_idx, baseline_start, baseline_end = detect_peak_boundaries(
            retention_times,
            baseline_corrected,
            peak_index,
            rt_target,
            min_peak_width,
            max_peak_width,
            noise_threshold,
        )
    except BoundaryDetectionError:
        start_idx, end_idx, baseline_start, baseline_end = fallback_boundary_detection(
            retention_times,
            baseline_corrected,
            peak_index,
            min_peak_width,
            max_peak_width,
        )

    # For LC data, use the already baseline-corrected values
    peak_region_times = retention_times[start_idx : end_idx + 1]
    peak_region_corrected = baseline_corrected[start_idx : end_idx + 1]

    # Calculate areas
    total_area = trapz(peak_region_corrected, peak_region_times)
    baseline_corrected_area = total_area  # Already baseline corrected

    # Calculate quality metrics
    dummy_baseline = np.zeros_like(peak_region_corrected)
    snr, quality_score = calculate_peak_quality_metrics(
        retention_times,
        baseline_corrected,
        dummy_baseline,
        start_idx,
        end_idx,
        peak_index,
    )

    peak_height = baseline_corrected[peak_index]

    return {
        "total_area": float(total_area),
        "baseline_corrected_area": float(baseline_corrected_area),
        "start_time": float(retention_times[start_idx]),
        "end_time": float(retention_times[end_idx]),
        "start_index": int(start_idx),
        "end_index": int(end_idx),
        "baseline_start": 0.0,
        "baseline_end": 0.0,
        "peak_height": float(peak_height),
        "integration_method": "trapezoidal",
        "snr": float(snr),
        "quality_score": float(quality_score),
    }


def find_peak_maximum(
    times: np.ndarray, intensities: np.ndarray, rt_target: float
) -> int:
    """
    Find the peak maximum index closest to the target retention time.

    Parameters
    ----------
    times : np.ndarray
        Array of time values
    intensities : np.ndarray
        Array of intensity values
    rt_target : float
        Target retention time

    Returns
    -------
    int
        Index of peak maximum
    """

    # Enhanced peak detection with adaptive prominence
    signal_std = np.std(intensities)
    signal_max = np.max(intensities)

    # Adaptive prominence: higher for noisy data, lower for clean data
    base_prominence = max(signal_std * 3, signal_max * 0.005)
    peaks, properties = find_peaks(
        intensities,
        prominence=base_prominence,
        distance=3,  # Minimum separation
        height=signal_std * 2,
    )

    if len(peaks) == 0:
        # No peaks found, use maximum intensity point
        return np.argmax(intensities)

    # Find peak closest to target RT
    peak_times = times[peaks]
    closest_peak_idx = np.argmin(np.abs(peak_times - rt_target))

    return peaks[closest_peak_idx]


def detect_peak_boundaries(
    times: np.ndarray,
    intensities: np.ndarray,
    peak_index: int,
    rt_target: float,
    min_width: float,
    max_width: float,
    noise_threshold: float,
) -> Tuple[int, int, float, float]:
    """
    Detect peak start and end boundaries using valley detection and baseline return.

    Parameters
    ----------
    times : np.ndarray
        Array of time values
    intensities : np.ndarray
        Array of intensity values
    peak_index : int
        Index of peak maximum
    rt_target : float
        Target retention time
    min_width : float
        Minimum peak width
    max_width : float
        Maximum peak width
    noise_threshold : float
        Noise threshold for boundary detection

    Returns
    -------
    Tuple[int, int, float, float]
        (start_index, end_index, baseline_start, baseline_end)
    """

    peak_time = times[peak_index]
    peak_intensity = intensities[peak_index]

    # Enhanced minimum intensity calculation for low-concentration samples
    # Use adaptive threshold based on signal statistics
    signal_baseline = np.percentile(
        intensities, 10
    )  # 10th percentile as baseline estimate
    signal_noise = np.std(intensities[intensities <= np.percentile(intensities, 25)])

    # More sensitive threshold for STMIX validation
    adaptive_threshold = signal_baseline + 3 * signal_noise
    min_intensity = max(noise_threshold, peak_intensity * 0.02, adaptive_threshold)

    # Find left boundary
    start_idx = peak_index
    for i in range(peak_index - 1, -1, -1):
        # Check time constraint
        if peak_time - times[i] > max_width:
            break

        # Check if intensity drops below threshold
        if intensities[i] <= min_intensity:
            start_idx = i
            break

        # Check for valley (local minimum)
        if (
            i > 0
            and intensities[i] < intensities[i - 1]
            and intensities[i] < intensities[i + 1]
        ):
            if intensities[i] <= min_intensity * 2:
                start_idx = i
                break

    # Find right boundary
    end_idx = peak_index
    for i in range(peak_index + 1, len(times)):
        # Check time constraint
        if times[i] - peak_time > max_width:
            break

        # Check if intensity drops below threshold
        if intensities[i] <= min_intensity:
            end_idx = i
            break

        # Check for valley (local minimum)
        if (
            i < len(times) - 1
            and intensities[i] < intensities[i - 1]
            and intensities[i] < intensities[i + 1]
        ):
            if intensities[i] <= min_intensity * 2:
                end_idx = i
                break

    # Validate minimum width constraint
    if times[end_idx] - times[start_idx] < min_width:
        # Expand boundaries to meet minimum width
        half_min_width = min_width / 2
        target_start_time = peak_time - half_min_width
        target_end_time = peak_time + half_min_width

        start_idx = np.argmin(np.abs(times - target_start_time))
        end_idx = np.argmin(np.abs(times - target_end_time))

    # Get baseline values at boundaries
    baseline_start = intensities[start_idx]
    baseline_end = intensities[end_idx]

    return start_idx, end_idx, baseline_start, baseline_end


def fallback_boundary_detection(
    times: np.ndarray,
    intensities: np.ndarray,
    peak_index: int,
    min_width: float,
    max_width: float,
) -> Tuple[int, int, float, float]:
    """
    Fallback boundary detection using fixed width around peak maximum.

    Parameters
    ----------
    times : np.ndarray
        Array of time values
    intensities : np.ndarray
        Array of intensity values
    peak_index : int
        Index of peak maximum
    min_width : float
        Minimum peak width
    max_width : float
        Maximum peak width

    Returns
    -------
    Tuple[int, int, float, float]
        (start_index, end_index, baseline_start, baseline_end)
    """

    peak_time = times[peak_index]

    # Use median width between min and max
    width = (min_width + max_width) / 2
    half_width = width / 2

    start_time = peak_time - half_width
    end_time = peak_time + half_width

    start_idx = np.argmin(np.abs(times - start_time))
    end_idx = np.argmin(np.abs(times - end_time))

    # Ensure indices are within bounds
    start_idx = max(0, start_idx)
    end_idx = min(len(times) - 1, end_idx)

    baseline_start = intensities[start_idx]
    baseline_end = intensities[end_idx]

    return start_idx, end_idx, baseline_start, baseline_end


def calculate_baseline_linear(
    intensities: np.ndarray, start_index: int, end_index: int
) -> np.ndarray:
    """
    Calculate linear baseline between peak boundaries.

    Parameters
    ----------
    intensities : np.ndarray
        Array of intensity values
    start_index : int
        Peak start index
    end_index : int
        Peak end index

    Returns
    -------
    np.ndarray
        Linear baseline values across peak region
    """

    start_intensity = intensities[start_index]
    end_intensity = intensities[end_index]

    # Create linear baseline
    n_points = end_index - start_index + 1
    baseline = np.linspace(start_intensity, end_intensity, n_points)

    return baseline


def calculate_peak_quality_metrics(
    times: np.ndarray,
    intensities: np.ndarray,
    baseline: np.ndarray,
    start_index: int,
    end_index: int,
    peak_index: int,
) -> Tuple[float, float]:
    """
    Calculate peak quality metrics including SNR and quality score.

    Parameters
    ----------
    times : np.ndarray
        Array of time values
    intensities : np.ndarray
        Array of intensity values
    baseline : np.ndarray
        Baseline values
    start_index : int
        Peak start index
    end_index : int
        Peak end index
    peak_index : int
        Peak maximum index

    Returns
    -------
    Tuple[float, float]
        (signal_to_noise_ratio, quality_score)
    """

    # Extract peak region
    peak_intensities = intensities[start_index : end_index + 1]

    if len(baseline) == 0:
        baseline = np.zeros_like(peak_intensities)

    # Calculate signal (peak height above baseline)
    baseline_at_peak = (
        baseline[peak_index - start_index]
        if len(baseline) > peak_index - start_index
        else 0
    )
    signal = intensities[peak_index] - baseline_at_peak

    # Estimate noise from surrounding regions
    noise_regions = []

    # Left noise region
    left_start = max(0, start_index - 20)
    left_end = start_index
    if left_end > left_start:
        noise_regions.extend(intensities[left_start:left_end])

    # Right noise region
    right_start = end_index
    right_end = min(len(intensities), end_index + 20)
    if right_end > right_start:
        noise_regions.extend(intensities[right_start:right_end])

    if len(noise_regions) > 0:
        noise = np.std(noise_regions)
        # Ensure noise estimate is reasonable (not too small)
        noise = max(noise, np.mean(noise_regions) * 0.01)
    else:
        # Enhanced fallback: use more sophisticated noise estimation
        # Use lower percentile of all intensities as noise estimate
        all_intensities = intensities[intensities > 0]  # Exclude zeros
        if len(all_intensities) > 10:
            noise = np.std(
                all_intensities[all_intensities <= np.percentile(all_intensities, 20)]
            )
            noise = max(noise, np.percentile(all_intensities, 5) * 0.1)
        else:
            noise = max(1.0, intensities[peak_index] * 0.01)

    # Calculate SNR
    snr = signal / noise if noise > 0 else 0

    # Calculate quality score (0-1) with enhanced metrics for LC-MS
    # Improved SNR normalization for modern instruments
    snr_score = min(
        1.0, snr / 50.0
    )  # Better normalization for LC-MS (SNR can be >1000)

    # Enhanced peak symmetry calculation considering peak tailing
    left_half = peak_index - start_index
    right_half = end_index - peak_index

    # Basic symmetry score
    basic_symmetry = 1.0 - abs(left_half - right_half) / max(left_half + right_half, 1)

    # Tailing factor calculation (USP method adapted)
    peak_region = intensities[start_index : end_index + 1]
    if len(peak_region) > 4:
        # Find 10% height points for tailing assessment
        peak_height = peak_region[peak_index - start_index]
        height_10pct = peak_height * 0.1

        # Find points closest to 10% height
        left_10pct_idx = (
            np.argmin(np.abs(peak_region[: peak_index - start_index] - height_10pct))
            if peak_index > start_index
            else 0
        )
        right_10pct_idx = (
            peak_index
            - start_index
            + np.argmin(np.abs(peak_region[peak_index - start_index :] - height_10pct))
        )

        if right_10pct_idx > left_10pct_idx:
            tailing_factor = (right_10pct_idx - left_10pct_idx) / (
                2 * (peak_index - start_index - left_10pct_idx)
            )
            tailing_score = max(
                0.0, 1.0 - abs(tailing_factor - 1.0)
            )  # Ideal tailing factor is 1.0
            symmetry_score = (basic_symmetry + tailing_score) / 2
        else:
            symmetry_score = basic_symmetry
    else:
        symmetry_score = basic_symmetry

    # Baseline stability (how flat the baseline regions are)
    baseline_score = 1.0
    if len(noise_regions) > 1:
        baseline_stability = np.std(noise_regions) / (np.mean(noise_regions) + 1)
        baseline_score = max(0.0, 1.0 - baseline_stability)

    # Enhanced combined quality score with additional factors
    # Adjust weights for LC-MS applications
    quality_score = snr_score * 0.4 + symmetry_score * 0.35 + baseline_score * 0.25

    # Apply minimum quality threshold for very noisy peaks
    if snr < 3.0:
        quality_score *= 0.5  # Penalize very low SNR peaks

    return snr, quality_score


def integrate_peak_area_trapezoidal(
    times: np.ndarray,
    intensities: np.ndarray,
    baseline: np.ndarray,
    start_index: int,
    end_index: int,
) -> Tuple[float, float]:
    """
    Perform trapezoidal integration of peak area.

    Parameters
    ----------
    times : np.ndarray
        Array of time values
    intensities : np.ndarray
        Array of intensity values
    baseline : np.ndarray
        Baseline values
    start_index : int
        Peak start index
    end_index : int
        Peak end index

    Returns
    -------
    Tuple[float, float]
        (total_area, baseline_corrected_area)
    """

    # Extract peak region
    peak_times = times[start_index : end_index + 1]
    peak_intensities = intensities[start_index : end_index + 1]

    # Calculate total area
    total_area = trapz(peak_intensities, peak_times)

    # Calculate baseline-corrected area
    if len(baseline) > 0 and len(baseline) == len(peak_intensities):
        corrected_intensities = peak_intensities - baseline
        baseline_corrected_area = trapz(corrected_intensities, peak_times)
    else:
        # Fallback: use linear baseline
        baseline_linear = np.linspace(
            peak_intensities[0], peak_intensities[-1], len(peak_intensities)
        )
        corrected_intensities = peak_intensities - baseline_linear
        baseline_corrected_area = trapz(corrected_intensities, peak_times)

    return total_area, baseline_corrected_area


def safe_peak_integration(integration_func, *args, **kwargs):
    """
    Wrapper function for safe peak integration with graceful error handling.

    Returns fallback values if integration fails, ensuring system stability.
    """
    try:
        return integration_func(*args, **kwargs)
    except InsufficientDataError:
        logger.warning("Insufficient data for peak integration, using simple sum")
        return create_fallback_peak_area(*args)
    except PoorPeakQualityError:
        logger.warning("Poor peak quality detected, integration may be unreliable")
        # Try with relaxed quality threshold
        return integration_func(*args, **kwargs)
    except BoundaryDetectionError:
        logger.warning("Boundary detection failed, using fixed width")
        return integration_func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Peak integration failed with unexpected error: {e}")
        return create_fallback_peak_area(*args)


def create_fallback_peak_area(*args) -> Dict[str, Union[float, int, str]]:
    """
    Create fallback peak area data when integration fails.

    Returns
    -------
    Dict[str, Union[float, int, str]]
        Fallback peak area information
    """

    # Try to extract basic information from args
    if len(args) >= 2:
        times = args[0] if isinstance(args[0], np.ndarray) else np.array([0])
        intensities = args[1] if isinstance(args[1], np.ndarray) else np.array([0])

        if len(intensities) > 0:
            total_area = float(np.sum(intensities))
            max_intensity = float(np.max(intensities))
        else:
            total_area = 0.0
            max_intensity = 0.0

        if len(times) > 0:
            start_time = float(np.min(times))
            end_time = float(np.max(times))
        else:
            start_time = 0.0
            end_time = 0.0
    else:
        total_area = 0.0
        max_intensity = 0.0
        start_time = 0.0
        end_time = 0.0

    return {
        "total_area": total_area,
        "baseline_corrected_area": total_area,
        "start_time": start_time,
        "end_time": end_time,
        "start_index": 0,
        "end_index": 0,
        "baseline_start": 0.0,
        "baseline_end": 0.0,
        "peak_height": max_intensity,
        "integration_method": "fallback_sum",
        "snr": 0.0,
        "quality_score": 0.0,
    }


def thread_safe_peak_integration(compounds_data, mass_accuracy, file_name):
    """
    Thread-safe wrapper for peak integration in multiprocessing environment.

    Ensures no shared state between processes and proper error isolation.
    """
    # Deep copy input data to avoid shared references
    safe_compounds = copy.deepcopy(compounds_data)

    # Process each compound independently
    results = []
    for compound in safe_compounds:
        try:
            processed_compound = process_compound_peak_areas(
                compound, mass_accuracy, file_name
            )
            results.append(processed_compound)
        except Exception as e:
            logger.error(f"Peak area processing failed for {compound.name}: {e}")
            results.append(compound)  # Return original compound on failure

    return results


def process_compound_peak_areas(compound, mass_accuracy, file_name):
    """
    Process peak areas for all ions in a compound.

    Parameters
    ----------
    compound : Compound
        Compound object to process
    mass_accuracy : float
        Mass accuracy for peak detection
    file_name : str
        Name of the file being processed

    Returns
    -------
    Compound
        Processed compound with peak area information
    """

    compound.file = file_name

    for ion in compound.ions.keys():
        try:
            # Check if MS Intensity data exists
            if compound.ions[ion]["MS Intensity"] is not None:
                ms_data = compound.ions[ion]["MS Intensity"]

                if len(ms_data) >= 2 and len(ms_data[0]) > 0:
                    scan_times = ms_data[0]
                    intensities = ms_data[1]

                    # Find RT of peak maximum
                    rt_peak = scan_times[np.argmax(intensities)]

                    # Calculate peak area
                    peak_area_info = safe_peak_integration(
                        integrate_ms_xic_peak,
                        scan_times=scan_times,
                        intensities=intensities,
                        rt_target=rt_peak,
                        mass_accuracy=mass_accuracy,
                    )

                    compound.ions[ion]["MS Peak Area"] = peak_area_info
                else:
                    # Insufficient data
                    compound.ions[ion]["MS Peak Area"] = create_fallback_peak_area()
            else:
                # No MS data
                compound.ions[ion]["MS Peak Area"] = create_fallback_peak_area()

        except Exception as e:
            logger.warning(
                f"Peak area calculation failed for ion {ion} in {compound.name}: {e}"
            )
            compound.ions[ion]["MS Peak Area"] = create_fallback_peak_area()

    return compound
