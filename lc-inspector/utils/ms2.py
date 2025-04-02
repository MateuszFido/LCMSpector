import numpy as np
import pandas as pd
import os
import __main__
import time

def feature_ms2(feature):
    library_entry = {}
    info = []
    mzs = []
    intensities = []
    # Open the MoNa library file by going into the parent folder and then into resources/MoNA-export-All_LC-MS-MS_Orbitrap.msp
    with open(os.path.join(os.path.dirname(__main__.__file__), os.pardir, os.path.join("resources/MoNA-export-All_LC-MS-MS_Orbitrap.msp")), "r") as library:
        for line in library:
            if line.startswith("Name: " + feature.name):
                library_entry["Name"] = feature.name
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

def parse_feature_name(feature_name: str):
    compound_name = feature_name.split()[0]

def test_library_reading():
    st = time.time()
    library = {}
    with open("/Users/mateuszfido/Library/CloudStorage/OneDrive-ETHZurich/LC-Inspector/resources/MoNA-export-All_LC-MS-MS_Orbitrap.msp", "r") as src:
        for line in src:
            if line.startswith("Name: "):
                # The key is the feature name, the value is all the following lines until an empty line
                feature_name = line.split("Name: ")[1].strip()
                library[feature_name] = []
                while True:
                    line = next(src)
                    if line.strip() == "":
                        break
                    library[feature_name].append(line)


    time.sleep(30)

    print("Loading took", time.time() - st, "seconds.")
    st = time.time()
    print(library["Propionic acid"])
    print("Lookup took", time.time() - st, "seconds.")