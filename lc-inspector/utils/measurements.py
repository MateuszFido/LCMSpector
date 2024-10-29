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
    Subclass of the abstract Measurement class. Represents a single .mzML LC file. Constructor takes the path to the .mzML file as an argument.
    Upon initialization, performs all the necessary preprocessing steps, such as loading the data and baseline correction.
    Parameters
    ----------
    path : str 
        The path to the .mzML file.

    -------
    This subclass defines the following methods:
    
    plot(self) : None
        Plots the baseline corrected data.

    """
    def __init__(self, path):
        super().__init__(path)
        self.data = load_absorbance_data(self.path)
        self.baseline_corrected = baseline_correction(self.data)
        print(f"Loaded {self.path} successfully.")


    def plot(self):
        self.plot = plot_absorbance_data(self.path, self.baseline_corrected)

    def annotate(self, compounds):
        self.compounds = annotate_LC_data(self.baseline_corrected, compounds)

    def plot_annotated(self):
        self.annotated_plot = plot_annotated_LC(self.path, self.baseline_corrected, self.compounds)


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

    -------
    This subclass defines the following methods:
    construct_xics(self) : None
        Constructs the XICs.
    plot(self) : None
        Plots the average spectrum.
    annotate_XICs(self, annotations) : None
        Annotates the XICs with annotations.
    """
    def __init__(self, path, mass_accuracy = 0.0001):
        super().__init__(path)
        self.data = load_ms1_data(self.path)
        self.mass_accuracy = mass_accuracy
        self.mz_axis = calculate_mz_axis(self.data, self.mass_accuracy)
        self.average = average_intensity(self.data, self.mz_axis)
        self.peaks = pick_peaks(self.average, self.mz_axis)
        self.xics = construct_xic(self.data, self.mz_axis, self.peaks)
        print(f"Loaded {self.path} successfully.")


    def construct_xics(self):
        construct_xic(self.average, self.mz_axis)

    def plot(self):
        self.plot = plot_average_ms_data(self.path, self.average)

    def annotate(self, compounds):
        self.compounds = annotate_XICs(self.path, self.xics, compounds, self.mass_accuracy)

    def plot_annotated(self):
        self.annotated_plot = plot_annotated_XICs(self.path, self.xics, self.compounds)


class Compound():
    '''
    Class representing a targeted results for a single measurement pair (LC + MS).
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