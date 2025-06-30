FROM ubuntu:latest AS build

# Install Python, pip, and dependencies
RUN apt-get update && apt-get install -y python3 python3-pip python3-venv x11-xserver-utils

# Copy your app code
COPY . /lc-inspector

# Create a virtual environment and install dependencies
WORKDIR /lc-inspector
RUN python3 -m venv venv
RUN . venv/bin/activate && pip install -r requirements.txt && deactivate

# Copy the virtual environment to the final image
FROM ubuntu:latest
COPY --from=build /lc-inspector/venv /lc-inspector/venv

# Set the PATH environment variable
ENV PATH="/app/venv/bin:$PATH"

# Copy the app code
COPY --from=build /lc-inspector /lc-inspector

# Set the DISPLAY environment variable
ENV DISPLAY=:99

# Run the GUI app
CMD ["/lc-inspector/venv/bin/python", "main.py"]
