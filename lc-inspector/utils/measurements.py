from utils.loading import load_absorbance_data, load_ms1_data
from utils.preprocessing import baseline_correction, calculate_mz_axis, average_intensity, construct_xic, pick_peaks
from utils.plotting import plot_average_ms_data, plot_absorbance_data, plot_annotated_LC, plot_annotated_XICs
from evaluation.annotation import annotate_XICs, annotate_LC_data
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
        print(f"Loading {path}...")
        self.filename = os.path.basename(path).split('.')[0]
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
    Subclass of the abstract Measurement class. Represents a single .mzML LC file.
    """
    def __init__(self, path):
        super().__init__(path)
        self._data = None  # Initialize as None
        self._baseline_corrected = None  # Initialize as None

    @property
    def data(self):
        if self._data is None:  # Load data only if it hasn't been loaded yet
            print(f"Loading data for {self.path}...")
            self._data = load_absorbance_data(self.path)
            print(f"Loaded {self.path} successfully.")
        return self._data

    @property
    def baseline_corrected(self):
        if self._baseline_corrected is None:  # Load baseline corrected data only if it hasn't been loaded yet
            print(f"Performing baseline correction for {self.path}...")
            self._baseline_corrected = baseline_correction(self.data)
        return self._baseline_corrected

    def plot(self):
        self.baseline_plot = plot_absorbance_data(self.path, self.baseline_corrected)

    def annotate(self, compounds):
        self.compounds = annotate_LC_data(self.baseline_corrected, compounds)

    def plot_annotated(self):
        self.annotated_plot = plot_annotated_LC(self.path, self.baseline_corrected, self.compounds)


class MSMeasurement(Measurement):
    """
    Subclass of the abstract Measurement class. Represents a single .mzML MS file.
    """
    def __init__(self, path, mass_accuracy=0.0001):
        super().__init__(path)
        self._data = None  # Initialize as None
        self._mass_accuracy = mass_accuracy
        self._mz_axis = None  # Initialize as None
        self._average = None  # Initialize as None
        self._peaks = None  # Initialize as None
        self._xics = None  # Initialize as None

    @property
    def data(self):
        if self._data is None:  # Load data only if it hasn't been loaded yet
            print(f"Loading data for {self.path}...")
            self._data = load_ms1_data(self.path)
            print(f"Loaded {self.path} successfully.")
        return self._data

    @property
    def mz_axis(self):
        if self._mz_axis is None:  # Calculate m/z axis only if it hasn't been calculated yet
            self._mz_axis = calculate_mz_axis(self.data, self._mass_accuracy)
        return self._mz_axis

    @property
    def average(self):
        if self._average is None:  # Calculate average intensity only if it hasn't been calculated yet
            self._average = average_intensity(self.data, self.mz_axis)
        return self._average

    @property
    def peaks(self):
        if self._peaks is None:  # Pick peaks only if they haven't been picked yet
            self._peaks = pick_peaks(self.average, self.mz_axis)
        return self._peaks

    @property
    def xics(self):
        if self._xics is None:  # Construct XICs only if they haven't been constructed yet
            self._xics = construct_xic(self.data, self.mz_axis, self.peaks)
        return self._xics

    def plot(self):
        self.average_plot = plot_average_ms_data(self.path, self.average)

    def annotate(self, compounds):
        self.compounds = annotate_XICs(self.path, self.xics, compounds, self._mass_accuracy)

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
    def __init__(self, name: str, file: str, ions: dict):
        self.name = name
        self.file = file
        self.ions = {ion: {"RT": None, "MS Intensity": None, "LC Intensity": None} for ion in ions}

    def __str__(self):
        return f"Compound: {self.name}, ions: {self.ions} in file: {self.file}"