import sys
import json
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from PySide6 import QtWidgets, QtCore
from ui.widgets import DragDropListWidget 

from ui.tabs.upload_tab import UploadTab

# --- Fixtures ---

@pytest.fixture
def get_config(tmp_path):
    """Creates a temporary config.json with dummy data for testing."""
    config_file = tmp_path / "config.json"
    initial_data = {
        "Standard Mix": {
            "Compound A": {"ions": ["100.1", "100.2"], "info": ["Info A"]},
            "Compound B": {"ions": [200.1], "info": "Info B"}
        }
    }
    with open(config_file, "w") as f:
        json.dump(initial_data, f)
    return config_file

@pytest.fixture
def upload_tab(qtbot, get_config):
    """
    Initializes UploadTab with mocked custom widgets and a temporary config path.
    """
    # Patch custom widgets to use standard Qt widgets. 
    # This avoids import errors if dependencies are missing and isolates the test.
        
    widget = UploadTab()
    qtbot.addWidget(widget)
    
    # Inject the mock config path
    widget.config_path = get_config
    # Force reload of combo box items since path changed
    widget.comboBoxIonLists.clear()
    widget.comboBoxIonLists.addItem("Create new ion list...")
    widget._load_ion_config_names()
    
    return widget

# --- Tests ---

def test_initial_ui_state(upload_tab):
    """Verify default UI state on load."""
    assert upload_tab.mode == "LC/GC-MS"
    assert upload_tab.listLC.isEnabled() is True
    # Should contain "Create new..." and "Standard Mix" from fixture
    assert upload_tab.comboBoxIonLists.count() == 2 
    assert upload_tab.comboBoxIonLists.findText("Standard Mix") != -1

def test_mode_change_signals_and_ui(upload_tab, qtbot):
    """Test that switching to 'MS Only' disables LC widgets and emits signal."""
    # Listen for the signal
    with qtbot.waitSignal(upload_tab.mode_changed, timeout=1000) as blocker:
        upload_tab.comboBoxChangeMode.setCurrentText("MS Only")
    
    # Check signal payload
    assert blocker.args == ["MS Only"]
    assert upload_tab.mode == "MS Only"
    
    # Check UI state
    assert upload_tab.listLC.isEnabled() is False
    assert upload_tab.browseLC.isEnabled() is False
    assert upload_tab.button_clear_LC.isEnabled() is False

def test_handle_files_dropped_filtering(upload_tab, qtbot, tmp_path):
    """Test that file dropping filters by extension correctly."""
    # Create dummy files
    lc_valid = tmp_path / "data.csv"
    lc_valid.touch()
    ms_valid = tmp_path / "data.mzml"
    ms_valid.touch()
    invalid = tmp_path / "image.png"
    invalid.touch()

    # 1. Drop into LC List
    with qtbot.waitSignal(upload_tab.files_loaded) as blocker:
        files = [str(lc_valid), str(ms_valid), str(invalid)]
        upload_tab.handle_files_dropped(files, "LC")
    
    # Verify signal args: (type, list_of_files)
    assert blocker.args[0] == "LC"
    loaded_files = blocker.args[1]
    
    assert len(loaded_files) == 1
    assert str(lc_valid) in loaded_files
    assert str(ms_valid) not in loaded_files # mzML should be ignored for LC
    assert upload_tab.listLC.count() == 1

def test_handle_files_recursion(upload_tab, qtbot, tmp_path):
    """Test that dropping a folder finds files recursively."""
    folder = tmp_path / "dataset"
    sub = folder / "subdir"
    sub.mkdir(parents=True)
    
    (folder / "file1.mzML").touch()
    (sub / "file2.mzml").touch()
    (folder / "notes.txt").touch() # Should be ignored for MS

    with qtbot.waitSignal(upload_tab.files_loaded) as blocker:
        upload_tab.handle_files_dropped([str(folder)], "MS")
        
    loaded_files = blocker.args[1]
    assert len(loaded_files) == 2
    assert any("file1.mzML" in f for f in loaded_files)
    assert any("file2.mzml" in f for f in loaded_files)

def test_ion_list_loading(upload_tab):
    """Test that selecting a list from combo populates the table."""
    # Select "Standard Mix" (from get_config fixture)
    upload_tab.comboBoxIonLists.setCurrentText("Standard Mix")
    
    # Verify table row count (2 items in fixture)
    assert upload_tab.ionTable.rowCount() == 2
    
    # Verify content of first row (assuming sorted order)
    # Note: Since dicts are unordered in older py, exact row depends on sort.
    # The code sorts keys, so "Compound A" is row 0.
    name_item = upload_tab.ionTable.item(0, 0)
    ion_item = upload_tab.ionTable.item(0, 1)
    
    assert name_item.text() == "Compound A"
    assert "100.1" in ion_item.text()

def test_save_ion_list(upload_tab, qtbot, monkeypatch):
    """Test scraping table data and saving to JSON."""
    # 1. Populate Table manually
    upload_tab.ionTable.setRowCount(1)
    upload_tab.ionTable.setItem(0, 0, QtWidgets.QTableWidgetItem("New Met"))
    upload_tab.ionTable.setItem(0, 1, QtWidgets.QTableWidgetItem("500, 501"))
    upload_tab.ionTable.setItem(0, 2, QtWidgets.QTableWidgetItem("Details"))

    # 2. Mock User Input (QInputDialog)
    # We monkeypatch the static method getText to return ("My New List", True)
    mock_input = MagicMock(return_value=("My New List", True))
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", mock_input)

    # 3. Trigger Save
    upload_tab.save_ion_list()

    # 4. Verify Config File Content
    with open(upload_tab.config_path, "r") as f:
        data = json.load(f)
    
    assert "My New List" in data
    entry = data["My New List"]["New Met"]
    assert entry["ions"] == ["500", "501"]
    
    # 5. Verify UI update
    assert upload_tab.comboBoxIonLists.currentText() == "My New List"

def test_delete_ion_list(upload_tab, monkeypatch):
    """Test deleting an ion list removes it from file and UI."""
    upload_tab.comboBoxIonLists.setCurrentText("Standard Mix")
    
    # Mock Confirmation Dialog (QMessageBox.question -> Yes)
    mock_msg = MagicMock(return_value=QtWidgets.QMessageBox.Yes)
    monkeypatch.setattr(QtWidgets.QMessageBox, "question", mock_msg)
    
    upload_tab.delete_ion_list()
    
    # Verify File
    with open(upload_tab.config_path, "r") as f:
        data = json.load(f)
    assert "Standard Mix" not in data
    
    # Verify UI
    assert upload_tab.comboBoxIonLists.findText("Standard Mix") == -1
    assert upload_tab.comboBoxIonLists.count() == 1 # Only "Create new..." remains

def test_process_button_signal(upload_tab, qtbot):
    """Test that the process button emits the correct signal."""
    with qtbot.waitSignal(upload_tab.process_requested) as blocker:
        upload_tab.processButton.click()
    assert blocker.signal_triggered

def test_get_file_list_helper(upload_tab):
    """Test the external accessor method."""
    upload_tab.listMS.addItem("A.mzML")
    upload_tab.listMS.addItem("B.mzML")
    
    result = upload_tab.get_file_list("MS")
    assert result == ["A.mzML", "B.mzML"]
