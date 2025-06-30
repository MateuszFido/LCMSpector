[![License: MIT](https://img.shields.io/badge/License-MIT_License-green)](https://mit-license.org/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.13990448.svg)](https://doi.org/10.5281/zenodo.13990448)
[![Tests](https://github.com/MateuszFido/LC-Inspector/actions/workflows/ci.yml/badge.svg)](https://github.com/MateuszFido/LC-Inspector/actions/workflows/ci.yml)

![LC-Inspector Logo](https://github.com/MateuszFido/LC-Inspector/blob/gui-redesign/resources/logo.png?raw=true)


##### Table of Contents  
[1. Description](#description)  
[2. Features](#features)   
[3. Usage](#usage)  
    * [User-interface](#user-interface)  
    * [Running from source](#running-from-source)  
[4. Installation](#installation)  
[5. Contributing](#contributing)  
[6. Licensing](#licensing)


***

<a name="description"/>

## 🔍 Description  
LC-Inspector is an open-source application for analyzing targeted mass spectrometry data. 

It allows you to process raw mass spectrometry and/or chromatography files and look for a set of compounds or peaks, trace their intensities, graph and export them (also the raw data), check with databases via MS/MS, and quantify using calibration standards.

<a name="features"/>

## ✨ Features
* Trace compounds in raw mass spec data
* Analyze and process LC/GC spectra 
* View the underlying MS spectra, scan by scan
* Graph and export your data in SVG, TIFF, PNG, JPG or CSV formats 
* Calculate concentrations using in-built calibration features 
* Compare with integrated MS/MS libraries 
* Vendor-agnostic, accepts any .mzML and .txt files 
* Process everything on your machine without registration/uploading to external websites or servers
* Easy UI, works on Windows and macOS > 
***

![LC-Inspector-demo](https://github.com/user-attachments/assets/c17d30d3-6bea-4692-ad7d-6d9d82322201)

<a name="usage"/>

## ⛯ Usage

### User-interface

LC-Inspector simplifies the MS analysis process to only a few steps: 

1. Drag and drop your mass spectrometry files into the main window 
2. Choose a list of metabolites to look for in the MS data or define your own 
3. Click **Process** 
4. View the results: 
* raw data, scan by scan;
* extracted ion chromatograms (XICs) of your compounds;
* total ion current (TIC);
* chromatograms labelled with your compounds' retention times;
* (optional) ion mobility data

5. Verify the structure of your compounds with MS/MS database matching
6. Quantify based on MS and/or chromatography data

The user can upload and process the data entirely locally on their machine. No need to register an account anywhere or upload to external websites or web servers.

### Running from source 

1.  Clone the repository or download the compressed version and unpack
2.  Install Python 3.12 or later
3.  Navigate to the folder containing `main.py` in the terminal
4.  Install dependencies listed in `requirements.txt` using `pip3 install -r requirements.txt`
5.  Prepare the input data
6.  Run the script via `main.py` using `python3 main.py`

<a name="installation"/>

## 💽 Installation 

Binaries are distributed for Windows and macOS, published under [Releases](https://github.com/MateuszFido/LC-Inspector/releases).

*   On Windows, if you encounter a warning, go to `Windows Defender -> Protection history -> LC-Inspector`, find the LC-Inspector entry, and click `Restore`. If the warning "Windows protected your PC" appears, click `More info` and `Run anyway`.
*   On MacOS, you can remove the app from quarantine by running the following command: `xattr -d com.apple.quarantine /path/to/app.app`

<a name="contributing"/>

## 🙋 Contributing

If you have an idea to improve LC-Inspector, don't hesitate to let me know -- any and all contributions are very welcome! 

There are two main ways to contribute: 
* opening an issue: describe feature(s) you would like to see or any bugs or problems you encountered: please enclose your exact system configuration and attach the log file (app.log) 
* opening a pull request with your suggested code changes 

<a name="licensing"/>

## 📋 Licensing 

LC-Inspector is distributed under the MIT license and available free of charge. 

LC-Inspector makes use of the MoNA database libraries for MS/MS spectra comparison, which are distributed under the CC BY 4.0 License <https://creativecommons.org/licenses/by/4.0/>. No changes are made to the content of the libraries.
