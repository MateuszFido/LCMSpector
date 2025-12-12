from pyteomics.mzml import chain, MzML
import numpy as np
from pathlib import Path

paths = [
    "/home/user/Documents/data/BIG_MIX_neg.mzml",
    "/home/user/Documents/data/H2O_neg.mzml",
    "/home/user/Documents/data/MIX_1_neg.mzml",
]

predefined_mz = 143.1224
for path in paths:
    with MzML(path, use_index=True) as reader:
        for spectrum in reader:
            # get the m/z array and find in it the value closest to predefined_mz
            mass_range = (predefined_mz - 0.003, predefined_mz + 0.003)
            mzs = spectrum["m/z array"][mass_range][0]
