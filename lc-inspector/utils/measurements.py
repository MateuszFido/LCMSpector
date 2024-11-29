from utils.loading import load_absorbance_data, load_ms1_data
from utils.preprocessing import baseline_correction, calculate_mz_axis, construct_xics
from utils.preprocessing import baseline_correction, calculate_mz_axis, construct_xics
from utils.plotting import plot_average_ms_data, plot_absorbance_data, plot_annotated_LC, plot_annotated_XICs
from abc import ABC, abstractmethod
import os, logging, re

logger = logging.getLogger(__name__)

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
        # Extract the concentration from the filename, by looking anywhere in the string
        # for a number followed by an optional decimal and followed by mM, uM, nM or pM
        match = re.search(r'([0-9]++)(.?)(uM|mM|nM|pM|mol|mol\/|umol)+', self.filename)
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
        self.data = load_absorbance_data(path)  # Initialize as None
        self.baseline_corrected = baseline_correction(self.data)  # Initialize as None
        logger.info(f"Loaded LC file {self.filename}.")

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
    data : List of Scan objects
        The list of Scan objects containing the MS data.
    mz_axis : np.ndarray
        The m/z axis for the intensity values.
    average : pd.DataFrame
        A DataFrame containing the m/z and intensity values.
    peaks : pd.DataFrame
        A DataFrame containing the m/z and intensity values of the peaks.
    xics : pd.DataFrame
        A DataFrame containing the m/z and intensity values of the XICs.
    """
    def __init__(self, path, ion_list, mass_accuracy=0.0001):
        super().__init__(path)
        self.data = load_ms1_data(path)  # Initialize as None
        self.mass_accuracy = mass_accuracy
        self.xics = construct_xics(self.data, ion_list, self.mass_accuracy)
        logger.info(f"Loaded MS file {self.filename}.")

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
        self.name = str(name)
        self.ions = {ion: {"RT": None, "MS Intensity": None, "LC Intensity": None} for ion in ions}
        self.ion_info = ion_info
        self._calibration_curve = None

    def __str__(self):
        return f"Compound: {self.name}, ions: {self.ions}, ion info: {self.ion_info}"

    @property
    #TODO
    def calibration_curve():
        self.calibration_curve = None
        pass