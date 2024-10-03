

import sys, os
import unittest
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
print(sys.path)
from utils.annotation import average_intensity, pick_peaks, construct_xic, annotate_XICs, annotate_lc_chromatograms
from utils.preprocessing import baseline_correction
from utils.load_data import load_absorbance_data, load_ms1_data
from pathlib import Path
import utils.Measurement



data = load_ms1_data("/Users/mateuszfido/Library/CloudStorage/OneDrive-ETHZurich/Mice/UPLC code/hplc/data/MS/STMIX5_02.mzml")
average_intensity("/Users/mateuszfido/Library/CloudStorage/OneDrive-ETHZurich/Mice/UPLC code/hplc/data/MS/STMIX5_02.mzml")

ms_path = Path("/Users/mateuszfido/Library/CloudStorage/OneDrive-ETHZurich/Mice/UPLC code/hplc/data/MS")
annotation = "STMIX5_02.mzml"
lc_path = Path("/Users/mateuszfido/Library/CloudStorage/OneDrive-ETHZurich/Mice/UPLC code/hplc/data/LC")
lc_file = "STMIX5_02.txt"
baseline_corrected_data = baseline_correction(lc_path / lc_file)
print(baseline_corrected_data)
annotate_lc_chromatograms((ms_path / annotation), baseline_corrected_data)
