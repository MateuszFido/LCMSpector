import numpy as np
import pandas as pd
import os
import __main__
import time

def find_feature(library, feature_name):
    if feature_name in library:
        return library[feature_name]
    else:
        return None

def parse_feature_name(feature_name: str):
    compound_name = feature_name.split()[0]

def test_library_reading():
    st = time.time()
    library = {}
    with open(os.path.join(os.path.dirname(__main__.__file__), "resources/MoNA-export-All_LC-MS-MS_Orbitrap.msp", "r")) as src:
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