LC-Inspector
================

[![License: MIT](https://img.shields.io/badge/License-MIT_License-green)](https://mit-license.org/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.13990448.svg)](https://doi.org/10.5281/zenodo.13990448)
[![Tests](https://github.com/MateuszFido/LC-Inspector/actions/workflows/ci.yml/badge.svg)](https://github.com/MateuszFido/LC-Inspector/actions/workflows/ci.yml)

![LC-Inspector Logo](https://github.com/MateuszFido/LC-Inspector/blob/gui-redesign/resources/logo.png?raw=true)

Introduction
------------

LC-Inspector is a free, local, and open-source software for preprocessing, analyzing, and annotating LC-MS data. It was primarily designed for annotating LC-MS files of derivatized amino acids and polyamines but can be used with any targeted LC-MS workflow.

Getting Started
---------------

### Installation

Pre-release binaries for LC-Inspector are available for Windows (64-bit) and MacOS (arm64) under the "Releases" section of the GitHub page. Please note that the binaries are not signed, which may cause antivirus software to flag them as malware.

*   On Windows, if you encounter a warning, go to `Windows Defender -> Protection history -> LC-Inspector`, find the LC-Inspector entry, and click `Restore`. If the warning "Windows protected your PC" appears, click `More info` and `Run anyway`.
*   On MacOS, you can remove the app from quarantine by running the following command: `xattr -d com.apple.quarantine /path/to/app.app`

### Warning

The graphical user interface (UI) of LC-Inspector is currently in early development. Some features may not be functional, and bugs are expected.

Usage
-----

### Input Requirements

*   LC input data: plain text (.txt) files
*   MS input data: open-format mass spectrometry files (.mzML)
*   Alternatively, annotation files (.txt) can be used if exact retention times of targeted compounds are known

### Running from Source

1.  Clone the repository or download the compressed version and unpack
2.  Install Python 3.12 or later
3.  Navigate to the folder containing `main.py` in the terminal
4.  Install dependencies listed in `requirements.txt` using `pip3 install -r requirements.txt`
5.  Prepare the input data
6.  Run the script via `main.py` using `python3 main.py`

### Graphical User Interface

The GUI version allows you to:

*   Browse and upload LC files (.txt format) and MS files (.mzML)
*   Preprocess the data and display results in the "Results" tab
*   Interact with plots, copy them to clipboard, or export them in .png, .tif, or .svg formats

### Script Version

The script version produces results in the form of .csv files in the 'data/results' folder, alongside plots of calibration curves, background-corrected chromatograms, and recognized peaks in the 'data/plots' folder.

References
----------

*   pyteomics library
*   hplc-py package by Griffin Chure from the Cremer lab: <https://cremerlab.github.io/hplc-py/> and <https://github.com/cremerlab/hplc-py>

License
-------

This project is distributed under the permissive MIT license. Details can be found in `LICENSE.txt`.

LC-Inspector makes use of the MoNA database libraries for MS/MS spectra comparison, which are distributed under the CC BY 4.0 License <https://creativecommons.org/licenses/by/4.0/>. No changes are made to the content of the libraries.

Copyright
---------

Created on 2024-02-29
Copyright (c) Mateusz Fido, ETH Zürich, 2024
mateusz.fido@org.chem.ethz.ch
