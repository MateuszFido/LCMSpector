FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Runtime dependencies for PySide6/Qt GUI via X11 forwarding
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 \
        libopengl0 \
        libegl1 \
        libfontconfig1 \
        libglib2.0-0 \
        libxkbcommon-x11-0 \
        libdbus-1-3 \
        libxcb-cursor0 \
        libxcb-icccm4 \
        libxcb-keysyms1 \
        libxcb-randr0 \
        libxcb-render-util0 \
        libxcb-shape0 \
        libxcb-sync1 \
        libxcb-xfixes0 \
        libxcb-xinerama0 \
        libxcb-xkb1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv (official multi-stage copy)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Install Python 3.13 via uv
RUN uv python install 3.13

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install all dependencies (including dev group for pytest)
RUN uv sync --frozen

# Copy application source and tests
COPY lcmspector/ lcmspector/
COPY tests/ tests/
COPY pytest.ini ./

# Qt binding hint (no QT_QPA_PLATFORM — defaults to xcb for GUI)
ENV QT_API=pyside6

# Default: run the application
CMD ["uv", "run", "python", "lcmspector/main.py"]
