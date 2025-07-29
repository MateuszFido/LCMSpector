# mzml_loader.pyx
import cython
from libc.stdlib cimport malloc, free
import numpy as np
cimport numpy as np
# FIXME: Unused

cdef class ScanLoader:
    cdef:
        object file_path
        list ms1_scans
    
    def __init__(self, str file_path):
        self.file_path = file_path
        self.ms1_scans = []
    
    def load_ms1_scans(self):
        """
        Efficiently load MS1 scans using Cython
        """
        cdef:
            list scans = []
            dict scan
        
        with mzml.MzML(self.file_path) as file:
            for scan in file:
                if scan['ms level'] == 1:
                    # Efficient numpy array conversion
                    mz_array = np.array(scan.get('m/z array', []), dtype=np.float64)
                    intensity_array = np.array(scan.get('intensity array', []), dtype=np.float64)
                    
                    scans.append({
                        'scan_time': scan.get('scan time', 0.0),
                        'mz_array': mz_array,
                        'intensity_array': intensity_array
                    })
        
        self.ms1_scans = scans
        return self.ms1_scans

# Compilation setup (setup.py)
from setuptools import setup
from Cython.Build import cythonize
import numpy

setup(
    ext_modules=cythonize("mzml_loader.pyx"),
    include_dirs=[numpy.get_include()]
)
