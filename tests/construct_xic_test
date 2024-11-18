import unittest
import numpy as np
import pandas as pd
from pyteomics import auxiliary
import static_frame as sf
lc_inspector = __import__('lc-inspector')
from lc_inspector.utils.preprocessing import construct_xic

class TestConstructXIC(unittest.TestCase):

    def setUp(self):        
        self.scans = [{'index': i, 
                       'total ion current': np.random.random(), 
                       'm/z array': np.linspace(100, 1000, 100), 
                       'intensity array': np.random.random(100)} for i in range(5)]
        
        self.mz_axis = np.linspace(100, 1000, 100)
        self.peaks = [Peak(index=50, mz=np.array([400]), width=[45, 55])]

    def test_construct_xic(self):
        xic_frame = construct_xic(self.scans, self.mz_axis, self.peaks)

        # Check the type of the returned object
        self.assertIsInstance(xic_frame, sf.FrameHE)

        # Check the shape of the DataFrame
        self.assertEqual(xic_frame.shape[1], len(self.peaks) + 3)  # MS1 scan ID, TIC, Scan time, and peaks
        self.assertEqual(xic_frame.shape[0], len(self.scans))

        # Check if the columns contain expected names
        expected_columns = ['MS1 scan ID', 'TIC (a.u.)', 'Scan time (min)']
        expected_columns.extend([f'neg{np.round(self.mz_axis[peak.index], 4)}' for peak in self.peaks])
        self.assertListEqual(list(xic_frame.columns), expected_columns)

if __name__ == '__main__':
    unittest.main()
