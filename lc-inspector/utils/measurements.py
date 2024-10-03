from utils.annotation import average_intensity
from utils.loading import load_absorbance_data, load_ms1_data
from utils.preprocessing import baseline_correction
from utils.plotting import plot_average_ms_data, plot_absorbance_data
from abc import ABC, abstractmethod
import os

class Measurement: 
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
    def __init__(self, path):
        super().__init__(path)

    def load_data(self):
        absorbance_data = load_absorbance_data(self.path)
        self.data = baseline_correction(absorbance_data)
    
    def plot(self):
        plot_absorbance_data(self.path, self.data)

class MSMeasurement(Measurement):
    def __init__(self, path):
        super().__init__(path)

    def load_data(self):
        ms_data = load_ms1_data(self.path)
        self.average = average_intensity(ms_data)

    def plot(self):
        plot_average_ms_data(self.path, self.average)