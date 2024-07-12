Created on 2024-02-29
Copyright (c) Mateusz Fido, ETH Zürich, 2024
mateusz.fido@org.chem.ethz.ch

This package reads and parses LC data from Thermo Scientific HPLCs/UPLCs. 
It is designed to be run on a series of .txt files containing absorbance and time data from the LC. 
It looks for peak annotations for each calibration/measurement file, and outputs a .csv file with the given compounds names, retention times, and peak areas.
It also outputs a plot of the calibration curve, a plot of the background corrected chromatogram, and a plot of the recognized peaks.
If supplied files with concentrations in the name, the script will also estimate concentrations of the recognized peaks based on the calibration curve.

# INSTALLATION #:
1. Clone the repository. 
2. Install Python 3.12 or later.
3. Install the dependencies listed out in requirements.txt ($ pip3 install -r requirements.txt):
    - pandas
    - numpy
    - matplotlib
    - scipy
    - alive_bar
    - (OPTIONAL, see below) torch
4. Prepare the input data:
    - The script expects the input data to be in the same directory as the script, in the subfolder 'data'.
    - The script expects the input data to be in .txt format.
    - The script expects the input data to be in the same format as the Thermo Scientific UPLC output.
5. (OPTIONAL) Train the peak recognition model by running train_peak_recognition_model.ipynb on your own dataset.
6. Run the script via main.py file ($ python3 main.py).

The script produces results in the form of .csv files in the 'results' folder, alongside plots of calibration curves,
background corrected chromatograms, and recognized peaks in the 'plots' folder.

===========
References: 

hplc-py package by Griffin Chure from the Cremer lab:
https://cremerlab.github.io/hplc-py/
https://github.com/cremerlab/hplc-py

