FROM ubuntu:latest AS build

# Install Python, pip, and dependencies
RUN apt-get update && apt-get install -y python3.12 python3-pip python3-venv python3-numpy-dev x11-xserver-utils build-essential libx11-dev libgl1-mesa-glx libegl1-mesa libglib2.0-0 libxkbcommon-x11-0 libdbus-1-dev libxcb-* qt6-base-dev qt6-tools-dev-tools libqt6gui6 libqt6widgets6 libqt6core6

ENV DEBIAN_FRONTEND=noninteractive
ENV LIBGL_ALWAYS_INDIRECT=1

# Copy your app code
COPY . /lc-inspector

# Create a virtual environment and install dependencies
WORKDIR /lc-inspector
RUN python3 -m venv venv
RUN . venv/bin/activate && pip install numpy
RUN . venv/bin/activate && pip install pandas
RUN . venv/bin/activate && pip install PySide6
RUN . venv/bin/activate && pip install pyqtgraph pyteomics pytest PyYAML scipy static_frame lxml

# Set the PATH environment variable
ENV PATH="/lc-inspector/venv/bin:$PATH"

# Set environment variables for Qt and PySide6
ENV DISPLAY=:99
ENV QT_QPA_PLATFORM=offscreen
ENV QT_API=pyside6

# Run the GUI app
CMD ["python", "lc-inspector/main.py"]
