
[![License: MIT](https://img.shields.io/badge/License-MIT_License-green)](https://mit-license.org/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.13990448.svg)](https://doi.org/10.5281/zenodo.13990448)

![alt text](https://github.com/MateuszFido/LC-Inspector/blob/gui-redesign/logo.png?raw=true)

# Preface

[WARNING] The graphical user interface (UI) of `LC-Inspector` is currently in early development. A lot of features visible in the UI is not functional yet. Bugs are prevalent and expected.

This package preprocesses, analyzes and annotates LC-MS data. 

It was primarily designed to annotate LC-MS files of derivatized amino acids and polyamines but can be used with any targeted LC-MS workflow.

Input can only be plain text (.txt) files for LC chromatograms and mzML files for the MS data. Alternatively, annotation files (expected .txt) can be used if exact retention times of targeted compounds are known. 

The script starts by parsing and preprocessing the given LC and MS files, interpolating intensity over a linearly-spaced m/z axis, reconstructing extracted ion chromatograms for a given set of peaks and plotting annotated LC spectra. 

# Installation
1. Clone the repository or download the compressed version (Code -> Download ZIP) and unpack
2. Install Python 3.12 or later
3. Navigate to the folder containing ```main.py``` in the terminal (e.g., cmd on Windows or Terminal on MacOS)
3. Install the dependencies listed out in requirements.txt (```$ pip3 install -r requirements.txt```):
    - pandas
    - numpy
    - matplotlib
    - scipy
    - alive_bar
    - pyteomics
    - lxml
    - pyqt6 
4. Prepare the input data:
    - The script expects the LC input data to be in .txt format.
    - The script expects the MS input data to be in .mzml format.
5. (OPTIONAL) Instead of the MS data, pre-annotated .txt files can be supplied if retention times are known (Thermo Chromeleon format).
6. Run the script via the main.py file (```$ python3 main.py```).

# Usage
The graphical user interface version (on branches `main` and `gui-redesign`) allows the user to browse their machine and upload liquid chromatography files (.txt format) and open-format mass spectrometry files (.mzML ). The script preprocesses the data and lets the user display the results in the "Results" tab of the main view. The plots are interactive, allowing the user to inspect the data closely, copy the plots to clipboard or export them in .png, .tif or .svg formats. An unnotated export of the plot data is also possible, although this feature is not well-implemented. 

The script version (branches `cluster`, `ms-integration`) produces results in the form of .csv files in the 'data/results' folder, alongside plots of calibration curves, background corrected chromatograms and recognized peaks in the 'data/plots' folder. 


# References

pyteomics library 

hplc-py package by Griffin Chure from the Cremer lab:

https://cremerlab.github.io/hplc-py/

https://github.com/cremerlab/hplc-py

# Copyright

This project is distributed under the permissive MIT license. Details can be found in `LICENSE.txt`.

Created on 2024-02-29
Copyright (c) Mateusz Fido, ETH Zürich, 2024
mateusz.fido@org.chem.ethz.ch