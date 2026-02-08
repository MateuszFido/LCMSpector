from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, PrivateAttr
import os
import logging
import re
import numpy as np
from pathlib import Path
from abc import abstractmethod
from utils.loading import load_absorbance_data, load_ms_data, extract_tic_data
from calculation.preprocessing import baseline_correction

logger = logging.getLogger(__name__)
logger.propagate = False


class Measurement:
    """
    Abstract class representing a single measurement. Constructor takes the path to the data file as an argument.
    Upon construction, if the filename contains "STMIX", the calibration flag is set to True.
    Parameters
    ----------
    path : str
        The path to the data file.

    -------
    The class defines the following methods:

    load_data(self) : abstractmethod
        Loads the data from path and stores it in the data attribute.
    plot(self) : abstractmethod
        Plots the data.
    extract_concentration(self) : float
        Extracts the concentration from the filename.

    """

    def __init__(self, path):
        self.path = path
        self.filename = Path(path).stem
        if "STMIX" in self.filename:
            self.calibration = True
        else:
            self.calibration = False

    @abstractmethod
    def load_data(self):
        pass

    @abstractmethod
    def plot(self):
        pass

    def extract_concentration(self):
        # Extract the concentration from the filename, by looking anywhere in the string
        # for a number followed by an optional decimal and followed by mM, uM, nM or pM
        match = re.search(r"(\d+(\.\d+)?).?_*([a-z][A-Z]{1,3})", self.filename)
        if match:
            return str(match.group(1)) + " " + str(match.group(3))
        else:
            return None

    def __str__(self):
        # Return the filename without any extensions
        return os.path.splitext(self.filename)[0]


class LCMeasurement(Measurement):
    """
    Subclass of the abstract Measurement class. Represents a single .mzML LC file.
    """

    def __init__(self, path):
        super().__init__(path)
        self.data = load_absorbance_data(path)
        self.annotations = None
        self.baseline_corrected = baseline_correction(self.data)
        self.file_type = "LC"

        self.peak_areas = self._calculate_lc_peak_areas()
        logger.info(
            f"Loaded LC file {self.filename} with {len(self.peak_areas)} detected peaks."
        )

    def _calculate_lc_peak_areas(self):
        """Calculate peak areas for all detected peaks in LC chromatogram."""
        try:
            from calculation.peak_integration import (
                integrate_lc_peak,
                safe_peak_integration,
            )
            from scipy.signal import find_peaks

            peak_areas = []
            times = self.baseline_corrected["Time (min)"].values
            corrected_values = self.baseline_corrected["Value (mAU)"].values
            uncorrected_values = self.baseline_corrected["Uncorrected"].values

            # Enhanced adaptive prominence threshold for STMIX validation
            signal_max = np.max(corrected_values)
            signal_std = np.std(corrected_values)

            # More sensitive detection for low-concentration samples
            # Use percentile-based noise estimation
            noise_level = np.std(
                corrected_values[
                    corrected_values <= np.percentile(corrected_values, 25)
                ]
            )
            baseline_level = np.percentile(corrected_values, 10)

            # Adaptive prominence: sensitive enough for 0.01 mM STMIX samples
            prominence_threshold = max(
                5.0,  # Absolute minimum
                noise_level * 4,  # 4x noise level
                signal_std * 2,  # 2x standard deviation
                (signal_max - baseline_level) * 0.005,  # 0.5% of signal range
            )

            # Enhanced peak detection parameters
            peaks, properties = find_peaks(
                corrected_values,
                prominence=prominence_threshold,
                distance=3,  # Reduced for dense chromatograms
                height=baseline_level + noise_level * 3,  # 3-sigma above baseline
                width=2,
            )  # Minimum peak width in data points

            logger.info(f"Found {len(peaks)} peaks in LC chromatogram {self.filename}")

            for i, peak_idx in enumerate(peaks):
                rt_target = times[peak_idx]
                try:
                    peak_area_info = safe_peak_integration(
                        integrate_lc_peak,
                        retention_times=times,
                        absorbances=uncorrected_values,
                        baseline_corrected=corrected_values,
                        rt_target=rt_target,
                        min_peak_width=0.05,  # 0.05 minutes minimum
                        max_peak_width=2.0,  # 2.0 minutes maximum
                        noise_threshold=prominence_threshold * 0.5,
                    )
                    peak_area_info["peak_rt"] = rt_target
                    peak_area_info["peak_index"] = i + 1  # 1-based peak numbering
                    peak_areas.append(peak_area_info)

                except Exception as e:
                    logger.warning(
                        f"LC peak area calculation failed at RT {rt_target:.2f}: {e}"
                    )
                    # Add fallback peak area info
                    from utils.peak_integration import create_fallback_peak_area

                    fallback_info = create_fallback_peak_area(times, corrected_values)
                    fallback_info["peak_rt"] = rt_target
                    fallback_info["peak_index"] = i + 1
                    peak_areas.append(fallback_info)

            return peak_areas

        except Exception as e:
            logger.error(f"Failed to calculate LC peak areas for {self.filename}: {e}")
            return []

    def get_peak_at_rt(self, target_rt: float, tolerance: float = 0.1):
        """
        Get peak area information for a peak at a specific retention time.

        Parameters
        ----------
        target_rt : float
            Target retention time in minutes
        tolerance : float
            Tolerance for RT matching in minutes

        Returns
        -------
        dict or None
            Peak area information if found, None otherwise
        """
        for peak_info in self.peak_areas:
            if abs(peak_info["peak_rt"] - target_rt) <= tolerance:
                return peak_info
        return None

    def plot(self, widget):
        """Plot this measurement's baseline-corrected data on the given widget.

        Parameters
        ----------
        widget : pg.PlotWidget
            The plot widget to draw on.

        Returns
        -------
        pg.PlotDataItem
            The created plot item.
        """
        from ui.plotting import plot_absorbance_data

        return plot_absorbance_data(self.path, self.baseline_corrected, widget)



class MSMeasurement(Measurement):
    """
    Subclass of the abstract Measurement class. Represents a single .mzML MS file.

    Attributes
    ----------
    mass_accuracy : float
        The mass accuracy of the m/z axis. Default: 0.0001
    data : tuple(Scan)
        The list of Scan objects containing the MS data.
    xics : tuple(Compound)
        A tuple containing the m/z and intensity values of the XICs.
    ms2_data : set
        A set containing the m/z and intensity values of the MS2 spectra.
    """

    def __init__(self, path, mass_accuracy=0.001):
        super().__init__(path)
        self.mass_accuracy = mass_accuracy
        self.xics = []
        self.file_type = "MS"

        # Extract TIC data first (runs in worker process during loading)
        self.tic_times, self.tic_values = extract_tic_data(path)

        # Keep lazy reader for indexed scan access (used by show_scan_at_time_x)
        self.data = load_ms_data(path)

    def get_compound_by_name(self, name: str):
        """
        Get a compound by its name.

        Parameters
        ----------
        name : str
            The name of the compound.

        Returns
        -------
        Compound or None
            The Compound object if found, None otherwise.
        """
        for compound in self.xics:
            if compound.name == name:
                return compound
        return None


class Compound(BaseModel):
    """
    Pydantic model representing a targeted result for a compound.
    Validates inputs and safely initializes internal state.
    """

    name: str
    target_list: List[float] = Field(..., description="List of expected m/z values")
    ion_info: List[str] = Field(
        default_factory=list, description="Optional list of additional info strings"
    )

    # Internal state attributes (Excluded from __init__ arguments and validation)
    _file: Optional[Any] = PrivateAttr(default=None)
    _ions: Dict = PrivateAttr(default_factory=dict)
    _calibration_curve: Dict = PrivateAttr(default_factory=dict)
    _calibration_parameters: Dict = PrivateAttr(default_factory=dict)
    _concentration: Optional[float] = PrivateAttr(default=None)
    _custom_mz_ranges: Dict = PrivateAttr(default_factory=dict)
    # Structure: {mz_float: (lower_bound, upper_bound)}

    def model_post_init(self, __context):
        """
        Post-initialization hook (Pydantic V2).
        Constructs the internal dictionary structure from the input list.
        """
        self._ions = {
            ion: {"RT": None, "MS Intensity": None, "LC Intensity": None}
            for ion in self.target_list
        }

    @property
    def ions(self) -> Dict:
        """Access the internal dictionary state."""
        return self._ions

    @ions.setter
    def ions(self, value: Dict):
        self._ions = value

    @property
    def file(self):
        return self._file

    @file.setter
    def file(self, value):
        self._file = value

    @property
    def calibration_curve(self):
        return self._calibration_curve

    @property
    def calibration_parameters(self):
        return self._calibration_parameters

    @calibration_parameters.setter
    def calibration_parameters(self, value):
        self._calibration_parameters = value

    @property
    def concentration(self):
        return self._concentration

    @concentration.setter
    def concentration(self, value):
        self._concentration = value

    @property
    def custom_mz_ranges(self):
        return self._custom_mz_ranges

    @custom_mz_ranges.setter
    def custom_mz_ranges(self, value):
        self._custom_mz_ranges = value

    def get_ion_label(self, index: int) -> str:
        """
        Get a label for the ion at the given index.
        Returns ion_info if available, otherwise falls back to m/z value.

        Parameters
        ----------
        index : int
            The index of the ion in target_list/ion_info.

        Returns
        -------
        str
            The ion label (ion_info string or m/z value as string).
        """
        if index < len(self.ion_info) and self.ion_info[index]:
            return self.ion_info[index]
        if index < len(self.target_list):
            return str(self.target_list[index])
        return ""

    def __str__(self):
        return f"Compound: {self.name}, ions: {self.target_list}, ion info: {self.ion_info}"
