FROM ubuntu:latest AS build

# Install Python, pip, and dependencies
RUN apt-get update && apt-get install -y python3.12 python3-pip python3-venv python3-numpy-dev x11-xserver-utils build-essential libx11-dev libgl1 libegl1-mesa-dev libglib2.0-0 libxkbcommon-x11-0 libdbus-1-dev libxcb-*

ENV DEBIAN_FRONTEND=noninteractive
ENV LIBGL_ALWAYS_INDIRECT=1

# Copy your app code
COPY . /lc-inspector

# Create a virtual environment and install dependencies
WORKDIR /lc-inspector
RUN python3 -m venv venv
RUN . venv/bin/activate && pip install numpy
RUN . venv/bin/activate && pip install pandas
RUN . venv/bin/activate && pip install PyQt6 PyQt6_sip
RUN . venv/bin/activate && pip install pyqtgraph pyteomics pytest PyYAML scipy static_frame lxml

# Set the PATH environment variable
ENV PATH="/lc-inspector/venv/bin:$PATH"

# Set the DISPLAY environment variable
ENV DISPLAY=:99

# Run the GUI app
CMD ["python", "lc-inspector/main.py"]
