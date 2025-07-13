from utils.loading import load_absorbance_data, load_ms1_data
from utils.preprocessing import baseline_correction, construct_xics
from utils.plotting import plot_average_ms_data, plot_absorbance_data, plot_annotated_LC, plot_annotated_XICs
from abc import abstractmethod
import os, logging, re
from pathlib import Path
import numpy as np
import weakref
import copy
import gc
import pickle

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


class MSMeasurement(Measurement):
    """
    Subclass of the abstract Measurement class. Represents a single .mzML MS file.
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
        self.ms2_data = None
        self._ion_list = ion_list
        self._persistent_references = {}  # To maintain strong references
        
        # Log initialization for debugging
        logger.info(f"Initializing MSMeasurement for {self.filename} with ID {id(self)}")
        
        # Load data eagerly instead of lazily to avoid serialization issues
        logger.info(f"Loading MS data for {self.filename}")
        self._data = load_ms1_data(self.path)
        logger.info(f"Loaded {len(self._data)} MS scans for {self.filename}, data ID: {id(self._data)}")
        
        # Store persistent reference to data
        self._persistent_references['_data'] = self._data
        
        # Construct XICs immediately
        logger.info(f"Constructing XICs for {self.filename}")
        self._xics = construct_xics(self._data, self._ion_list, self.mass_accuracy)
        logger.info(f"Constructed XICs for {self.filename}: {len(self._xics) if self._xics else 0} compounds, xics ID: {id(self._xics)}")
        
        # Store persistent reference to XICs
        self._persistent_references['_xics'] = self._xics

    @property
    def data(self):
        """Return the MS data"""
        if self._data is None and hasattr(self, 'path') and hasattr(self, '_persistent_references') and '_data' in self._persistent_references:
            # Try to recover from persistent references
            self._data = self._persistent_references['_data']
            if self._data is None:
                logger.warning(f"Recovering lost data for {self.filename}")
                self._data = load_ms1_data(self.path)
                self._persistent_references['_data'] = self._data
        
        return self._data

    @property
    def xics(self):
        """Return the XICs"""
        if self._xics is None and hasattr(self, '_persistent_references') and '_xics' in self._persistent_references:
            # Try to recover from persistent references
            self._xics = self._persistent_references['_xics']
            if self._xics is None and self._data is not None and hasattr(self, '_ion_list') and self._ion_list:
                logger.warning(f"Recovering lost XICs for {self.filename}")
                self._xics = construct_xics(self._data, self._ion_list, self.mass_accuracy)
                self._persistent_references['_xics'] = self._xics
        
        return self._xics

    def plot(self):
        self.average_plot = plot_average_ms_data(self.path, self.data)

    def plot_annotated(self):
        self.XIC_plot = plot_annotated_XICs(self.path, self.xics, self.compounds)

    def __getstate__(self):
        """Simplified serialization that ensures data persistence"""
        # Create a copy of the object's state
        state = self.__dict__.copy()
        
        # Log serialization process
        logger.info(f"Serializing MSMeasurement {self.filename} with ID {id(self)}")
        
        # Ensure we're including the essential data (the key fix for serialization)
        # By accessing the data through properties, we ensure it's loaded if needed
        if hasattr(self, 'data') and self.data is not None:
            logger.info(f"Ensuring _data is included in serialization, size: {len(self.data)}")
            state['_data'] = self._data  # Explicitly include _data
            
        if hasattr(self, 'xics') and self.xics is not None:
            logger.info(f"Ensuring _xics is included in serialization, size: {len(self.xics)}")
            state['_xics'] = self._xics  # Explicitly include _xics
            
        # Remove _persistent_references as we'll recreate it during deserialization
        if '_persistent_references' in state:
            del state['_persistent_references']
        
        # Log what we're serializing
        if '_data' in state:
            logger.info(f"Serializing _data with ID {id(state['_data'])} containing {len(state['_data'])} scans")
        if '_xics' in state:
            logger.info(f"Serializing _xics with ID {id(state['_xics'])} containing {len(state['_xics']) if state['_xics'] else 0} compounds")
        
        return state

    def __setstate__(self, state):
        """Simplified deserialization with direct data assignment"""
        # First, initialize a persistent references dictionary
        self._persistent_references = {}
        
        # Update state directly
        self.__dict__.update(state)
        
        # Log deserialization process
        logger.info(f"Deserializing MSMeasurement {self.filename if hasattr(self, 'filename') else 'unknown'} with ID {id(self)}")
        
        # Verify and establish strong references to data
        if hasattr(self, '_data') and self._data is not None:
            logger.info(f"Deserialized _data with ID {id(self._data)} containing {len(self._data)} scans")
            # Store in persistent references
            self._persistent_references['_data'] = self._data
            
            # Strengthen the reference by reassigning to itself
            self._data = self._data
        else:
            logger.warning(f"Data was missing after deserialization, will reload on first access")
            self._data = None
            # The data property will handle reloading if accessed
        
        # Verify and establish strong references to XICs
        if hasattr(self, '_xics') and self._xics is not None:
            logger.info(f"Deserialized _xics with ID {id(self._xics)} containing {len(self._xics)} compounds")
            # Store in persistent references
            self._persistent_references['_xics'] = self._xics
            
            # Strengthen the reference by reassigning to itself
            self._xics = self._xics
        else:
            logger.warning(f"XICs were missing after deserialization, will reconstruct on first access")
            self._xics = None
            # The xics property will handle reconstruction if accessed

    def __del__(self):
        """Clean up resources when the object is deleted"""
        logger.info(f"Deleting MSMeasurement {self.filename if hasattr(self, 'filename') else 'unknown'} with ID {id(self)}")
        # Clear references to allow proper garbage collection
        if hasattr(self, '_persistent_references'):
            self._persistent_references.clear()

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
