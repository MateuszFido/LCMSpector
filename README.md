[![License: MIT](https://img.shields.io/badge/License-MIT_License-green)](https://mit-license.org/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.13990448.svg)](https://doi.org/10.5281/zenodo.13990448)
[![Tests](https://github.com/MateuszFido/LC-Inspector/actions/workflows/ci.yml/badge.svg)](https://github.com/MateuszFido/LC-Inspector/actions/workflows/ci.yml)

![LCMSpector Logo](https://github.com/MateuszFido/LC-Inspector/blob/gui-redesign/resources/logo.png?raw=true)


# 🚀 Quickstart

Follow this short guide to get started with LCMSpector:

https://github.com/MateuszFido/LCMSpector/wiki/Quickstart-guide

Or read on for a more detailed explanation:

---
#### Table of Contents

1. [Description](#description)
2. [Features](#features)
3. [Installation](#installation)
   - [Desktop app](#desktop-app)
   - [Running from source](#running-from-source)
4. [Usage](#usage)
5. [Running with Docker](#-running-with-docker)
   - [MacOS](#macos)
   - [Linux](#linux)
   - [Windows](#windows)
6. [Contributing](#contributing)
7. [Licensing](#licensing)


***

<a name="description"/>

# 🔍 Description  
LCMSpector (pronunciation: "el-see-em-spector" or "el-see-inspector") is an open-source application for analyzing targeted mass spectrometry data. 

It allows you to process raw mass spectrometry and/or chromatography files and look for a set of compounds or peaks, trace their intensities, graph and export them (also the raw data), check with databases via MS/MS, and quantify using calibration standards.

For more information, visit the [LCMSpector wiki](https://github.com/MateuszFido/LCMSpector/wiki)!

<a name="features"/>

# ✨ Features

<img width="1503" height="859" alt="LC-Inspector-interface" src="https://github.com/user-attachments/assets/aa162e46-7d8c-4835-8e25-e3ff6b196acd" />

* Trace compounds in raw mass spec data
* Analyze and process LC/GC spectra 
* View the underlying MS spectra, scan by scan
* Graph and export your data in SVG, TIFF, PNG, JPG or CSV formats 
* Calculate concentrations using in-built calibration features 
* Compare with integrated MS/MS libraries 
* Vendor-agnostic, accepts any .mzML and .txt files 
* Process everything on your machine without registration/uploading to external websites or servers
* Easy UI, works on Windows, Mac, and Linux! 
***

<p align="center">
<img src="https://github.com/user-attachments/assets/cdbf9488-a75f-431d-b619-f07b3a8dbe47" width="800" height="525" />
</p>

<a name="installation"/>

# 💽 Installation 

## Desktop app

Executables for Windows, macOS, and Linux are published under [Releases](https://github.com/MateuszFido/LC-Inspector/releases). 

You can now also use the [Docker version of LCMSpector](#-running-with-docker).

*   On Windows, if you encounter a warning, go to `Windows Defender -> Protection history -> LC-Inspector`, find the LC-Inspector entry, and click `Restore`. If the warning "Windows protected your PC" appears, click `More info` and `Run anyway`.
*   On MacOS, you can remove the app from quarantine by running the following command: `xattr -d com.apple.quarantine /path/to/app.app`

If the app has not been quarantined but isn't running, go to `System settings -> Privacy and security -> scroll down -> Open anyway`

If running from source, you only need to execute `python3 main.py`.

## Running from source 

1.  Clone the repository or download the compressed version and unpack
2.  Install Python 3.12 or later
3.  Navigate to the folder containing `main.py` in the terminal
4.  Install dependencies listed in `requirements.txt` using `pip3 install -r requirements.txt`
5.  Prepare the input data
6.  Run the script via `main.py` using `python3 main.py`

<a name="usage"/>

# ⛯ Usage

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

[Here is an overview](https://github.com/MateuszFido/LCMSpector/wiki) of what LCMSpector can do! 

<a name="-running-with-docker"/>

# 🐳 Running with Docker

Docker is a fantastic alternative if you don't want to install the app directly on your system. 

## MacOS

### 1. Install XQuartz (if you don't have it already)

Download and install XQuartz from:  
https://www.xquartz.org/

- After installation, open XQuartz.
- Go to **XQuartz > Preferences > Security** and check:  
  **"Allow connections from network clients"**
- Restart XQuartz if you changed the setting.

---

### 2. Allow Docker to Connect to XQuartz

Open a terminal on your Mac and run:

```bash
xhost + 127.0.0.1
```

---

### 3. Pull the Docker Image

```bash
docker pull mateuszfido/lcmspector:latest
```

---

### 4. Run the Docker Container

In **the same** terminal, run:

```bash
docker run -it \
  -e DISPLAY=host.docker.internal:0 \
  mateuszfido/lcmspector:latest
```
>[!IMPORTANT]
>To be able to analyze files on your local machine, add `-v /path/on/host:/path/in/container` to the Docker command to mount your data folder(s).
---

If you have issues:
- Make sure XQuartz is running and "Allow connections from network clients" is checked.
- Make sure your Mac firewall allows incoming connections for XQuartz.
- Try restarting XQuartz or your terminal session.

---

## Linux

### 1. Prerequisites

Make sure you have Docker installed and an X11 server running (most Linux desktops do this by default).

You may also need to allow clients to connect to your X server:

```bash
xhost +local:docker
```

---

### 2. Pull the Docker Image

```bash
docker pull mateuszfido/lcmspector:latest
```

---

### 3. Run the Docker Container

Run the following command in your terminal:

```bash
docker run -it \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  mateuszfido/lcmspector:latest
```
>[!IMPORTANT]
>To be able to analyze files on your local machine, add `-v /path/on/host:/path/in/container` to the Docker command to mount your data folder(s).

---

If you have issues:
- Make sure you ran `xhost +local:docker` to allow Docker containers to use your X server.
- Check that your DISPLAY variable is set (usually `:0` on most desktop Linux systems).
- Make sure your system firewall is not blocking local X11 connections.

---

## Windows 

### 1. Install an X11 Server (VcXsrv)

- Download [VcXsrv Windows X Server](https://sourceforge.net/projects/vcxsrv/) and install it.
- Launch **XLaunch** (installed with VcXsrv), and configure as follows:
  - Select "Multiple windows"
  - Start no client
  - Extra settings: Check "Disable access control"
  - Finish to start the server

---

### 2. Find Your Host IP Address

Open Command Prompt or PowerShell and run:

```bash
ipconfig
```

Look for your IPv4 address (e.g., `192.168.1.100`).

---

### 3. Pull the Docker Image

```powershell
docker pull mateuszfido/lcmspector:latest
```

---

### 4. Run the Docker Container

In your terminal, run (replace `<YOUR-IP>` with your IPv4 address from step 2):

```powershell
docker run -it ^
  -e DISPLAY=<YOUR-IP>:0.0 ^
  mateuszfido/lcmspector:latest
```

>[!IMPORTANT]
>To be able to analyze files on your local machine, add `-v /path/on/host:/path/in/container` to the Docker command to mount your data folder(s).
---

If you have issues:
- Make sure VcXsrv is running and "Disable access control" is checked.
- Ensure your firewall allows VcXsrv connections.
- Double-check you used the correct IP address.
- Try restarting VcXsrv or your terminal session.

---

<a name="contributing"/>

# 🙋 Contributing

If you have an idea to improve LC-Inspector, don't hesitate to let me know -- any and all contributions are very welcome! 

There are two main ways to contribute: 
* opening an issue: describe feature(s) you would like to see or any bugs or problems you encountered: please enclose your exact system configuration and attach the log file (app.log) 
* opening a pull request with your suggested code changes 

<a name="licensing"/>

# 📋 Licensing 

LC-Inspector is distributed under the MIT license and available free of charge. 

LC-Inspector makes use of the MoNA database libraries for MS/MS spectra comparison, which are distributed under the CC BY 4.0 License <https://creativecommons.org/licenses/by/4.0/>. No changes are made to the content of the libraries.
