import numpy as np
import pandas as pd

def feature_ms2(feature: str):
    library_entry = {}
    info = []
    mzs = []
    intensities = []
    with open(__main__.__file__.replace("main.py","") + "/resources/MoNA-export-All_LC-MS-MS_Orbitrap.msp", "r") as library:
        for line in library:
            if line.startswith("Name: " + feature):
                library_entry["Name"] = feature
                while not line.startswith("Num Peaks:"):
                    info.append(line)
                    line = next(library)
                info.append(line)
                while not line.split() == []:
                    try: 
                        line = next(library)
                        try:
                            mzs.append(float(line.split()[0]))
                            intensities.append(float(line.split()[1]))
                        except IndexError:
                            break
                    except StopIteration:
                        break
                library_entry["Info"] = info
                library_entry["m/z"] = np.array(mzs)
                library_entry["Intensity"] = np.array(intensities)
                break
    return library_entry