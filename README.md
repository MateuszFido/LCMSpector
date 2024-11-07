Created on 2024-02-29
Copyright (c) Mateusz Fido, ETH Zürich, 2024
mateusz.fido@org.chem.ethz.ch

![alt text](https://github.com/MateuszFido/LC-Inspector/blob/gui-redesign/logo.png?raw=true)

This package preprocesses, analyzes and annotates LC-MS data. 

It was primarily designed to annotate LC-MS files of derivatized amino acids and polyamines but can be used with any targeted LC-MS workflow.

Input can only be plaintext (.txt) files for LC chromatograms and mzML files for the MS data. Alternatively, annotation files (expected .txt) can be used if exact retention times of targeted compounds are known. 

The script starts by parsing and preprocessing the given LC and MS files, interpolating intensity over a linearly-spaced m/z axis, reconstructing extracted ion chromatograms for a given set of peaks and plotting annotated LC spectra. 

# INSTALLATION:
1. Clone the repository or download the compressed version (Code -> Download ZIP) and unpack.
2. Install Python 3.12 or later.
3. Install the dependencies listed out in requirements.txt ($ pip3 install -r requirements.txt):
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
6. Run the script via the main.py file ($ python3 main.py).

The script produces results in the form of .csv files in the 'data/results' folder, alongside plots of calibration curves,
background corrected chromatograms and recognized peaks in the 'data/plots' folder. They can be viewed in the "Results" tab of the graphical user interface.

===========
References: 

pyteomics library 

hplc-py package by Griffin Chure from the Cremer lab:

https://cremerlab.github.io/hplc-py/

https://github.com/cremerlab/hplc-py

