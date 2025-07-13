from utils.loading_optimized import load_absorbance_data, load_ms1_data
from utils.preprocessing_optimized import baseline_correction, construct_xics
from utils.plotting import plot_average_ms_data, plot_absorbance_data, plot_annotated_LC, plot_annotated_XICs
from abc import abstractmethod
import os, logging, re
from pathlib import Path
import numpy as np
import weakref

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

class OptimizedLCMeasurement(Measurement):
    """
    Optimized subclass of the abstract Measurement class. Represents a single .mzML LC file.
    Implements memory-efficient data handling and caching.
    """
    def __init__(self, path):
        super().__init__(path)
        # Use lazy loading pattern - only load data when needed
        self._data = None
        self._baseline_corrected = None
        logger.info(f"Initialized LC file {self.filename}.")

    @property
    def data(self):
        """Lazy-load data only when needed"""
        if self._data is None:
            self._data = load_absorbance_data(self.path)
        return self._data

    @property
    def baseline_corrected(self):
        """Lazy-load baseline correction only when needed"""
        if self._baseline_corrected is None:
            self._baseline_corrected = baseline_correction(self.data)
        return self._baseline_corrected

    def plot(self):
        plot_absorbance_data(self.path, self.baseline_corrected)

    def plot_annotated(self):
        plot_annotated_LC(self.path, self.baseline_corrected, self.compounds)

    def __getstate__(self):
        """Custom serialization to handle weak references"""
        state = self.__dict__.copy()
        # Don't pickle the actual data, just the path
        state['_data'] = None
        state['_baseline_corrected'] = None
        return state

    def __setstate__(self, state):
        """Custom deserialization to handle weak references"""
        self.__dict__.update(state)


class OptimizedMSMeasurement(Measurement):
    """
    Optimized subclass of the abstract Measurement class. Represents a single .mzML MS file.
    Implements memory-efficient data handling, lazy loading, and caching.

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
    def __init__(self, path, ion_list, mass_accuracy=0.0001):
        super().__init__(path)
        self.mass_accuracy = mass_accuracy
        self._data = None
        self._xics = None
        self.ms2_data = None
        self._ion_list = ion_list

    @property
    def data(self):
        """Lazy-load MS data only when needed"""
        if self._data is None:
            self._data = load_ms1_data(self.path)
        return self._data

    @property
    def xics(self):
        """Lazy-load XICs only when needed"""
        if self._xics is None:
            self._xics = construct_xics(self.data, self._ion_list, self.mass_accuracy)
        return self._xics

    def plot(self):
        self.average_plot = plot_average_ms_data(self.path, self.data)

    def plot_annotated(self):
        self.XIC_plot = plot_annotated_XICs(self.path, self.xics, self.compounds)

    def __getstate__(self):
        """Custom serialization to optimize memory usage"""
        state = self.__dict__.copy()
        # Don't pickle the actual data, just the path and parameters
        state['_data'] = None
        # Keep the xics if they've been calculated
        return state

    def __setstate__(self, state):
        """Custom deserialization"""
        self.__dict__.update(state)

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
        self.ms2 = list()
        self.ion_info = ion_info
        self.calibration_curve = {}

    def __str__(self):
        return f"Compound: {self.name}, ions: {self.ions}, ion info: {self.ion_info}"

# Aliases for backward compatibility
LCMeasurement = OptimizedLCMeasurement
MSMeasurement = OptimizedMSMeasurement
