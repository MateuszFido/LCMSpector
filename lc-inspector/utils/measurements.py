from utils.loading import load_absorbance_data, load_ms1_data
from utils.preprocessing import baseline_correction, calculate_mz_axis, average_intensity, construct_xic, pick_peaks
from utils.plotting import plot_average_ms_data, plot_absorbance_data
from evaluation.annotation import annotate_lc_chromatograms, annotate_XICs
from abc import ABC, abstractmethod
import os

class Measurement: 
    """
    Abstract class representing a single measurement. Constructor takes the path to the data file as an argument.
    Upon construction, if the filename contains "STMIX", the calibration flag is set to True.
    Parameters
    ----------
    path : str 
        The path to the data file.

    Methods
    -------
    load_data(self) : abstractmethod
        Loads the data from path and stores it in the data attribute.
    plot(self) : abstractmethod
        Plots the data.
    extract_concentration(self) : float
        Extracts the concentration from the filename.

    """
    def __init__(self, path):
        self.path = path
        self.filename = os.path.basename(path)
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
        # First look for STMIX in the filename 
        # If present, return the number(s) in the string as concentration
        match = re.search(r'STMIX', self.filename)
        if match:
            return float(re.findall(r'(\d*[.]?\d+)', self.filename)[0])
        else:
            return None

    def __str__(self):
        # Return the filename without any extensions
        return os.path.splitext(self.filename)[0]

class LCMeasurement(Measurement):
    """
    Subclass of the abstract Measurement class. Represents a single .mzML LC file. Constructor takes the path to the .mzML file as an argument.
    Upon initialization, performs all the necessary preprocessing steps, such as loading the data and baseline correction.
    Parameters
    ----------
    path : str 
        The path to the .mzML file.

    Methods
    -------
    plot(self) : None
        Plots the baseline corrected data.

    """
    def __init__(self, path):
        super().__init__(path)
        self.data = load_absorbance_data(self.path)
        self.baseline_corrected = baseline_correction(self.data)

    def plot(self):
        plot_absorbance_data(self.path, self.baseline_corrected)


class MSMeasurement(Measurement):
    """
    Subclass of the abstract Measurement class. Represents a single .mzML MS file. Constructor takes the path to the .mzML file as an argument, and, optionally, the desired mass accuracy.
    Upon initialization, performs all the necessary preprocessing steps, such as loading the data, calculating the m/z axis, constructing the average spectrum, and rebuilding the XICs.
    
    Parameters
    ----------
    path : str 
        The path to the .mzML file.
    mass_accuracy : float, optional
        The mass accuracy of the instrument, by default 0.0001.
    """
    def __init__(self, path, mass_accuracy = 0.0001):
        super().__init__(path)
        self.data = load_ms1_data(self.path)
        self.mass_accuracy = mass_accuracy
        self.mz_axis = calculate_mz_axis(self.data, self.mass_accuracy)
        self.average = average_intensity(self.data, self.mz_axis)
        self.peaks = pick_peaks(self.average, self.mz_axis)
        self.xics = construct_xic(self.data, self.mz_axis, self.peaks)

    def construct_xics(self):
        construct_xic(self.average, self.mz_axis)

    def plot(self):
        plot_average_ms_data(self.path, self.average)

    def annotate_XICs(self, annotations):
        self.compounds = annotate_XICs(self.path, self.xics, annotations, self.mass_accuracy)

    