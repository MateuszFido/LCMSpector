from utils.annotation import average_intensity
from utils.load_data import load_absorbance_data, load_ms1_data
from abc import ABC, abstractmethod

class Measurement: 
    def __init__(self, filename):
        self.filename = filename
        if "STMIX" in self.filename:
            self.calibration = True
        else:
            self.calibration = False

    @abstractmethod
    def load_data(self):
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
    def __init__(self, filename):
        super().__init__(filename)

    def load_data(self):
        absorbance_data = load_absorbance_data(self.filename)
        self.data = baseline_correction(absorbance_data)

class MSMeasurement(Measurement):
    def __init__(self, filename):
        super().__init__(filename)

    def load_data(self):
        ms_data = load_ms1_data(self.filename)
        self.average = average_intensity(ms_data)