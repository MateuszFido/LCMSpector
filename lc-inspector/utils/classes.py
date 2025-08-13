from utils.loading import load_absorbance_data, load_ms1_data
from utils.preprocessing import baseline_correction, construct_xics
from utils.plotting import plot_average_ms_data, plot_absorbance_data, plot_annotated_LC, plot_annotated_XICs
from abc import abstractmethod
import os, logging, re
import numpy as np
from pathlib import Path

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
        match = re.search(r'(\d+(\.\d+)?).?_*([a-z][A-Z]{1,3})', self.filename)
        if match:
            return str(match.group(1)) + ' ' + str(match.group(3))
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
        
        # NEW: Calculate peak areas for detected peaks in LC chromatogram
        self.peak_areas = self._calculate_lc_peak_areas()
        logger.info(f"Loaded LC file {self.filename} with {len(self.peak_areas)} detected peaks.")

    def _calculate_lc_peak_areas(self):
        """Calculate peak areas for all detected peaks in LC chromatogram."""
        try:
            from utils.peak_integration import integrate_lc_peak, safe_peak_integration
            from scipy.signal import find_peaks
            
            peak_areas = []
            times = self.baseline_corrected['Time (min)'].values
            corrected_values = self.baseline_corrected['Value (mAU)'].values
            uncorrected_values = self.baseline_corrected['Uncorrected'].values
            
            # Enhanced adaptive prominence threshold for STMIX validation
            signal_max = np.max(corrected_values)
            signal_std = np.std(corrected_values)
            signal_median = np.median(corrected_values)
            
            # More sensitive detection for low-concentration samples
            # Use percentile-based noise estimation
            noise_level = np.std(corrected_values[corrected_values <= np.percentile(corrected_values, 25)])
            baseline_level = np.percentile(corrected_values, 10)
            
            # Adaptive prominence: sensitive enough for 0.01 mM STMIX samples
            prominence_threshold = max(
                5.0,  # Absolute minimum
                noise_level * 4,  # 4x noise level
                signal_std * 2,   # 2x standard deviation
                (signal_max - baseline_level) * 0.005  # 0.5% of signal range
            )
            
            # Enhanced peak detection parameters
            peaks, properties = find_peaks(corrected_values,
                                         prominence=prominence_threshold,
                                         distance=3,  # Reduced for dense chromatograms
                                         height=baseline_level + noise_level * 3,  # 3-sigma above baseline
                                         width=2)  # Minimum peak width in data points
            
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
                        max_peak_width=2.0,   # 2.0 minutes maximum
                        noise_threshold=prominence_threshold * 0.5
                    )
                    peak_area_info['peak_rt'] = rt_target
                    peak_area_info['peak_index'] = i + 1  # 1-based peak numbering
                    peak_areas.append(peak_area_info)
                    
                except Exception as e:
                    logger.warning(f"LC peak area calculation failed at RT {rt_target:.2f}: {e}")
                    # Add fallback peak area info
                    from utils.peak_integration import create_fallback_peak_area
                    fallback_info = create_fallback_peak_area(times, corrected_values)
                    fallback_info['peak_rt'] = rt_target
                    fallback_info['peak_index'] = i + 1
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
            if abs(peak_info['peak_rt'] - target_rt) <= tolerance:
                return peak_info
        return None

    def plot(self):
        plot_absorbance_data(self.path, self.baseline_corrected)

    def plot_annotated(self):
        plot_annotated_LC(self.path, self.baseline_corrected, self.compounds)


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
    def __init__(self, path, mass_accuracy=0.0001):
        super().__init__(path)
        self.mass_accuracy = mass_accuracy
        self.data = load_ms1_data(path)
        self.xics = []
        self.ms2_data = None

    def plot(self):
        self.average_plot = plot_average_ms_data(self.path, self.data)

    def plot_annotated(self):
        self.XIC_plot = plot_annotated_XICs(self.path, self.xics, self.compounds)

class Compound():
    '''
    Class representing a targeted result for a single measurement pair (LC + MS).
    Parameters
    ----------
    name : str
        The name of the compound.
    ions : list
        A list of ion types.
    ms_area : float
        The MS area of the compound.
    lc_area : float
        The LC area of the compound.
    rt : float
        The retention time of the compound.
    '''
    def __init__(self, name: str, ions: list, ion_info: list):
        self.file = None
        self.name = str(name)
        self.ions = {ion: {"RT": None, "MS Intensity": None, "LC Intensity": None} for ion in ions}
        self.ms2 = list()
        self.ion_info = ion_info
        self.calibration_curve = {}

    def __str__(self):
        return f"Compound: {self.name}, ions: {self.ions}, ion info: {self.ion_info}"
