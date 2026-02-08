"""
Shared fixtures for UI testing suite.

Provides pytest-qt fixtures and mock objects for testing LCMSpector UI components.
"""
import gc
import json
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ============================================================================
# Qt Cleanup Hooks
# ============================================================================


def pytest_configure(config):
    """Disable Python's cyclic garbage collector for the entire test session.

    PySide6/shiboken segfaults when Python's GC collects PySide6 wrapper
    objects whose C++ counterparts have already been destroyed.  Disabling
    automatic GC prevents this race.  Manual gc.collect() is also unsafe
    here, so we rely on reference-counting for Python-side cleanup and
    os._exit(0) to skip atexit handlers that would trigger the same issue.
    """
    gc.disable()


@pytest.fixture(autouse=True)
def _flush_qt_events(qapp):
    """Flush deferred deletions between every test to prevent accumulation."""
    yield
    for _ in range(3):  # handle cascading deletions
        qapp.processEvents()


def pytest_sessionfinish(session, exitstatus):
    """Capture the real exit status before shutdown."""
    session.config._real_exitstatus = exitstatus


def pytest_unconfigure(config):
    """Bypass Python interpreter shutdown when all tests passed.

    Qt's atexit handlers can trigger use-after-free segfaults during
    interpreter shutdown when thousands of deferred deletions accumulate
    in a session-scoped QApplication.  When all tests passed, skip the
    teardown entirely with os._exit(0).
    """
    real_status = getattr(config, "_real_exitstatus", None)
    if real_status is not None and real_status == 0:
        if sys.platform == "win32":
            import ctypes

            kernel32 = ctypes.windll.kernel32
            kernel32.GetCurrentProcess.restype = ctypes.c_void_p
            kernel32.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint]
            kernel32.TerminateProcess.restype = ctypes.c_int

            sys.stdout.flush()
            sys.stderr.flush()

            kernel32.TerminateProcess(kernel32.GetCurrentProcess(), 0)
        else:
            os._exit(0)


# ============================================================================
# Signal Catcher Utility
# ============================================================================


class SignalCatcher:
    """
    Utility class for recording signal emissions.

    Usage:
        catcher = SignalCatcher()
        widget.some_signal.connect(catcher.slot)
        widget.do_something()
        assert catcher.was_called
        assert catcher.call_count == 1
        assert catcher.args == (expected_arg1, expected_arg2)
    """

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all recorded state."""
        self.was_called = False
        self.call_count = 0
        self.args = None
        self.all_args = []

    def slot(self, *args):
        """Slot to connect to signals."""
        self.was_called = True
        self.call_count += 1
        self.args = args
        self.all_args.append(args)


@pytest.fixture
def signal_catcher():
    """Provide a fresh SignalCatcher instance for each test."""
    return SignalCatcher()


# ============================================================================
# Qt Application Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def qapp():
    """
    Session-scoped QApplication instance.

    pytest-qt provides this via qtbot, but we define it explicitly for clarity.
    The QT_QPA_PLATFORM=offscreen environment variable (from pytest.ini)
    ensures headless execution.
    """
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# ============================================================================
# Mock MVC Components
# ============================================================================


@pytest.fixture
def mock_model():
    """
    Mock Model object for testing without full application context.
    """
    model = MagicMock()
    model.lc_measurements = {}
    model.ms_measurements = {}
    model.compounds = []
    return model


@pytest.fixture
def mock_controller(mock_model):
    """
    Mock Controller object for testing without full application context.
    """
    controller = MagicMock()
    controller.model = mock_model
    controller.mode = "LC/GC-MS"
    return controller


# ============================================================================
# Test Config Data
# ============================================================================


@pytest.fixture
def sample_config():
    """Sample ion configuration data for testing."""
    return {
        "Test Compounds": {
            "Caffeine": {
                "ions": [195.0877, 138.0662],
                "info": ["[M+H]+", "[M+H-C2H5NO]+"]
            },
            "Glucose": {
                "ions": [203.0526, 185.042],
                "info": ["[M+Na]+", "[M+Na-H2O]+"]
            }
        },
        "Empty List": {}
    }


@pytest.fixture
def config_file(tmp_path, sample_config):
    """
    Create a temporary config.json file for testing.

    Returns the path to the temporary config file.
    """
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(sample_config, indent=2))
    return config_path


# ============================================================================
# Sample Test Data Files
# ============================================================================


@pytest.fixture
def sample_lc_file(tmp_path):
    """
    Create a sample LC chromatography file for testing.

    Returns the path to the temporary file.
    """
    lc_file = tmp_path / "sample_lc.txt"
    # Simple time,intensity format
    content = """Time\tIntensity
0.0\t100
0.5\t150
1.0\t200
1.5\t180
2.0\t120
"""
    lc_file.write_text(content)
    return lc_file


@pytest.fixture
def sample_ms_file(tmp_path):
    """
    Create a sample MS file path for testing.

    Note: This doesn't create a valid mzML file, just a path for testing
    file handling logic.

    Returns the path to the temporary file.
    """
    ms_file = tmp_path / "sample_ms.mzML"
    ms_file.write_text("<mzML></mzML>")  # Minimal placeholder
    return ms_file


@pytest.fixture
def sample_annotation_file(tmp_path):
    """
    Create a sample annotation file for testing.

    Returns the path to the temporary file.
    """
    annotation_file = tmp_path / "annotations.txt"
    annotation_file.write_text("Compound1\t1.5\nCompound2\t3.2\n")
    return annotation_file


# ============================================================================
# UploadTab Fixtures
# ============================================================================


@pytest.fixture
def upload_tab(qapp, qtbot, config_file):
    """
    Create an isolated UploadTab instance for testing.

    Uses a temporary config file to avoid affecting the real config.
    """
    from ui.tabs.upload_tab import UploadTab

    tab = UploadTab(parent=None, mode="LC/GC-MS")
    tab.config_path = config_file
    qtbot.addWidget(tab)

    # Reload ion config with new path
    tab.comboBoxIonLists.clear()
    tab.comboBoxIonLists.addItem("Create new ion list...")
    tab._load_ion_config_names()

    yield tab

    tab.close()
    tab.deleteLater()


@pytest.fixture
def upload_tab_ms_only(qapp, qtbot, config_file):
    """
    Create an UploadTab instance in MS Only mode.
    """
    from ui.tabs.upload_tab import UploadTab

    tab = UploadTab(parent=None, mode="MS Only")
    tab.config_path = config_file
    qtbot.addWidget(tab)

    # Reload ion config with new path
    tab.comboBoxIonLists.clear()
    tab.comboBoxIonLists.addItem("Create new ion list...")
    tab._load_ion_config_names()

    yield tab

    tab.close()
    tab.deleteLater()


@pytest.fixture
def upload_tab_chrom_only(qapp, qtbot, config_file):
    """
    Create an UploadTab instance in LC/GC Only mode.
    """
    from ui.tabs.upload_tab import UploadTab

    tab = UploadTab(parent=None, mode="LC/GC Only")
    tab.config_path = config_file
    qtbot.addWidget(tab)

    # Reload ion config with new path
    tab.comboBoxIonLists.clear()
    tab.comboBoxIonLists.addItem("Create new ion list...")
    tab._load_ion_config_names()

    yield tab

    tab.close()
    tab.deleteLater()


# ============================================================================
# File Dialog Mock Fixture
# ============================================================================


class MockFileDialog:
    """
    Mock for QFileDialog that allows controlling return values.

    Usage:
        mock_file_dialog.set_return(["/path/to/file.txt"])
        # Now when the browse button is clicked, it will return these files
    """

    def __init__(self):
        self._return_files = []
        self._patches = []

    def set_return(self, files):
        """Set the files to return from getOpenFileNames."""
        self._return_files = files

    def mock_get_open_file_names(self, parent, title, directory, filter_str):
        """Mock implementation of QFileDialog.getOpenFileNames."""
        return (self._return_files, filter_str)

    def start(self):
        """Start patching QFileDialog."""
        from PySide6 import QtWidgets
        patcher = patch.object(
            QtWidgets.QFileDialog,
            'getOpenFileNames',
            side_effect=self.mock_get_open_file_names
        )
        self._patches.append(patcher)
        patcher.start()

    def stop(self):
        """Stop all patches."""
        for patcher in self._patches:
            patcher.stop()
        self._patches.clear()


@pytest.fixture
def mock_file_dialog():
    """
    Provide a controllable mock for QFileDialog.

    Usage in tests:
        def test_browse(upload_tab, mock_file_dialog, qtbot):
            mock_file_dialog.set_return(["/tmp/test.txt"])
            mock_file_dialog.start()
            qtbot.mouseClick(upload_tab.browseLC, Qt.MouseButton.LeftButton)
            mock_file_dialog.stop()
    """
    dialog = MockFileDialog()
    yield dialog
    dialog.stop()  # Ensure cleanup


# ============================================================================
# Custom Widget Fixtures
# ============================================================================


@pytest.fixture
def drag_drop_list(qapp, qtbot):
    """Create an isolated DragDropListWidget for testing."""
    from ui.widgets import DragDropListWidget

    widget = DragDropListWidget(parent=None)
    qtbot.addWidget(widget)
    yield widget

    widget.close()
    widget.deleteLater()


@pytest.fixture
def ion_table(qapp, qtbot, config_file):
    """
    Create an isolated IonTable for testing.

    Requires a mock view with comboBoxIonLists and statusbar.
    """
    from ui.widgets import IonTable
    from unittest.mock import MagicMock

    # Create mock view
    mock_view = MagicMock()
    mock_view.comboBoxIonLists = MagicMock()
    mock_view.statusbar = MagicMock()

    table = IonTable(view=mock_view, parent=None)
    qtbot.addWidget(table)
    yield table

    table._cleanup_lookup()
    table.close()
    table.deleteLater()


@pytest.fixture
def labelled_slider(qapp, qtbot):
    """Create an isolated LabelledSlider for testing."""
    from ui.widgets import LabelledSlider

    values = [0.1, 0.01, 0.001, 0.0001]
    default = 0.001
    widget = LabelledSlider("Test Label", values, default, parent=None)
    qtbot.addWidget(widget)
    yield widget

    widget.close()
    widget.deleteLater()
