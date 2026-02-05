[![License: MIT](https://img.shields.io/badge/License-MIT_License-green)](https://mit-license.org/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.13990448.svg)](https://doi.org/10.5281/zenodo.13990448)
[![Tests](https://github.com/MateuszFido/LC-Inspector/actions/workflows/ci.yml/badge.svg)](https://github.com/MateuszFido/LC-Inspector/actions/workflows/ci-nodata.yml)

![LCMSpector Logo](https://github.com/MateuszFido/LC-Inspector/blob/main/lcmspector/resources/logo.png?raw=true)

# LCMSpector

An open-source desktop application for analyzing targeted mass spectrometry (LC/GC-MS) data. Process raw files, trace compounds, compare spectra, and quantify — all locally on your machine. See the [wiki](https://github.com/MateuszFido/LCMSpector/wiki) for full documentation.

<img width="1503" height="859" alt="LCMSpector interface" src="https://github.com/user-attachments/assets/aa162e46-7d8c-4835-8e25-e3ff6b196acd" />

## Features

- Trace compounds in raw mass spectrometry data via extracted ion chromatograms (XICs)
- Analyze and process LC/GC chromatograms with automatic baseline correction and peak detection
- View MS spectra scan-by-scan at any retention time
- Overlay and compare multiple files simultaneously on the same plot
- Look up compound m/z values from PubChem by name
- Quantify concentrations using built-in linear regression calibration
- Match compounds against integrated MS/MS libraries (MoNA format)
- Export plots (SVG, TIFF, PNG, JPG) and data (CSV)
- High-performance mzML parsing via a custom lxml-based reader
- Vendor-agnostic: accepts `.mzML`, `.txt`, and `.csv` files
- Runs on Windows, macOS, and Linux

## Installation

### Desktop app

Pre-built executables for Windows, macOS, and Linux are available under [Releases](https://github.com/MateuszFido/LC-Inspector/releases).

- **Windows:** If Windows Defender blocks the app, go to *Protection history*, find the LC-Inspector entry, and click *Restore*. If "Windows protected your PC" appears, click *More info* then *Run anyway*.
- **macOS:** Remove the app from quarantine: `xattr -d com.apple.quarantine /path/to/app.app`. Alternatively, go to *System Settings > Privacy & Security* and click *Open Anyway*.

### From source

1. Clone the repository
2. Install [Python 3.13+](https://www.python.org/) and [uv](https://docs.astral.sh/uv/)
3. Install dependencies:

   ```bash
   uv sync --frozen
   ```

4. Run the application:

   ```bash
   python lcmspector/main.py
   ```

## Usage

1. Drag and drop your mass spectrometry and/or chromatography files into the main window
2. Choose a compound list or define your own (compound names are automatically looked up on PubChem)
3. Click **Process**
4. View results: TIC, XICs, labelled chromatograms, and raw MS scans
5. Verify compound structures with MS/MS database matching
6. Quantify using calibration standards

<p align="center">
<img src="https://github.com/user-attachments/assets/cdbf9488-a75f-431d-b619-f07b3a8dbe47" width="800" height="525" />
</p>

## Docker

Docker is an alternative if you prefer not to install the app directly. Currently Linux-only (requires X11).

You need [Podman](https://podman.io/) or [Docker Engine](https://docs.docker.com/engine/install/) (not Docker Desktop — it cannot forward X11 from its VM).

```bash
# Build
podman build -t lcmspector .

# Run (Podman)
xhost +local:
podman run --rm --security-opt label=disable \
  -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix lcmspector
xhost -local:

# Run (Docker Engine) — no --security-opt needed
xhost +local:
docker run --rm -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix lcmspector
xhost -local:
```

To access local files, mount your data directory: `-v /path/on/host:/data`.

## Contributing

Contributions are welcome. Open an [issue](https://github.com/MateuszFido/LC-Inspector/issues) to report bugs or suggest features (please attach logs for bug reports), or submit a pull request with your changes.

## License

LCMSpector is distributed under the [MIT License](https://mit-license.org/).

It includes MS/MS libraries from the MoNA database, distributed under the [CC BY 4.0 License](https://creativecommons.org/licenses/by/4.0/). No changes are made to the library content.
