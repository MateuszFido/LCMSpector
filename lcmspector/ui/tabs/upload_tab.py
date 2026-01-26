from pathlib import Path
import logging
import json
import os
from PySide6 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

from ui.widgets import (
    DragDropListWidget,
    IonTable,
    ChromatogramPlotWidget,
    LabelledSlider,
)
from ui.plotting import plot_placeholder

logger = logging.getLogger(__name__)

class UploadTab(QtWidgets.QWidget):
    """
    Handles file selection (LC, MS, Annotations) and configuration (Ion Lists, Mass Accuracy).
    """
    # --- Signals ---
    files_loaded = QtCore.Signal(str, list)  # (type, file_paths)
    status_message = QtCore.Signal(str, int) # (message, duration_ms)
    process_requested = QtCore.Signal()
    mode_changed = QtCore.Signal(str)
    
    def __init__(self, parent=None, mode="LC/GC-MS"):
        super().__init__(parent)
        self.mode = mode
        
        # Determine config path relative to the application root
        # Structure: lcmspector/ui/tabs/upload_tab.py -> lcmspector/config.json
        self.config_path = Path(__file__).resolve().parent.parent.parent / "config.json"
        
        self.layout = QtWidgets.QGridLayout(self)
        self.setup_ui()
        
        # Initialize placeholders
        plot_placeholder(self.canvas_baseline, "Welcome to LCMSpector\n← add files to get started")
        
        # Load initial state
        self._load_ion_config_names()
        self.update_ion_list()
        self._update_mode_ui(self.mode)

    def setup_ui(self):
        """Constructs the UI elements."""
        
        # 1. Mode Selection
        self.labelMode = QtWidgets.QLabel("Mode:")
        self.comboBoxChangeMode = QtWidgets.QComboBox()
        self.comboBoxChangeMode.addItems(["LC/GC-MS", "MS Only"])
        self.comboBoxChangeMode.setCurrentText(self.mode)
        self.comboBoxChangeMode.currentTextChanged.connect(self.on_mode_changed)

        self.layout.addWidget(self.labelMode, 0, 0)
        self.layout.addWidget(self.comboBoxChangeMode, 0, 1)

        # 2. File Lists & Browsing
        # LC
        self.labelLC = QtWidgets.QLabel("LC/GC Files:")
        self.browseLC = QtWidgets.QPushButton("Browse")
        self.browseLC.clicked.connect(self.on_browse_lc)
        self.listLC = DragDropListWidget()
        self.listLC.filesDropped.connect(lambda files: self.handle_files_dropped(files, "LC"))
        self.button_clear_LC = QtWidgets.QPushButton("Clear")
        self.button_clear_LC.clicked.connect(self.listLC.clear)

        self.layout.addWidget(self.labelLC, 1, 0, 1, 1)
        self.layout.addWidget(self.browseLC, 1, 1, 1, 1)
        self.layout.addWidget(self.listLC, 2, 0, 1, 2)
        self.layout.addWidget(self.button_clear_LC, 3, 0, 1, 2)

        # MS
        self.labelMS = QtWidgets.QLabel("MS Files:")
        self.browseMS = QtWidgets.QPushButton("Browse")
        self.browseMS.clicked.connect(self.on_browse_ms)
        self.listMS = DragDropListWidget()
        self.listMS.filesDropped.connect(lambda files: self.handle_files_dropped(files, "MS"))
        self.button_clear_MS = QtWidgets.QPushButton("Clear")
        self.button_clear_MS.clicked.connect(self.listMS.clear)

        self.layout.addWidget(self.labelMS, 4, 0, 1, 1)
        self.layout.addWidget(self.browseMS, 4, 1, 1, 1)
        self.layout.addWidget(self.listMS, 5, 0, 1, 2)
        self.layout.addWidget(self.button_clear_MS, 6, 0, 1, 2)

        # 3. Ion Lists
        self.labelIon = QtWidgets.QLabel("Targeted ions (m/z values):")
        self.comboBoxIonLists = QtWidgets.QComboBox()
        self.comboBoxIonLists.addItems(["Create new ion list..."])
        self.comboBoxIonLists.currentTextChanged.connect(self.update_ion_list)
        
        self.ionTable = IonTable(self)
        
        self.ionButtonLayout = QtWidgets.QHBoxLayout()
        
        self.button_save_ion_list = QtWidgets.QPushButton("Save")
        self.button_save_ion_list.clicked.connect(self.save_ion_list)
        
        self.button_delete_ion_list = QtWidgets.QPushButton("Delete")
        self.button_delete_ion_list.clicked.connect(self.delete_ion_list)
        
        self.button_clear_ion_list = QtWidgets.QPushButton("Clear")
        self.button_clear_ion_list.clicked.connect(self.clear_ion_list)

        self.ionButtonLayout.addWidget(self.button_save_ion_list)
        self.ionButtonLayout.addWidget(self.button_delete_ion_list)
        self.ionButtonLayout.addWidget(self.button_clear_ion_list)

        self.layout.addWidget(self.labelIon, 0, 4, 1, 1)
        self.layout.addWidget(self.comboBoxIonLists, 1, 4, 1, 2)
        self.layout.addWidget(self.ionTable, 2, 4, 4, 3)
        self.layout.addLayout(self.ionButtonLayout, 6, 4, 1, 3)

        # 4. Parameters
        self.mass_accuracy_slider = LabelledSlider(
            "Mass accuracy (Da)", [0.1, 0.01, 0.001, 0.0001], 0.001
        )
        
        self.layout.addWidget(self.mass_accuracy_slider, 7, 4, 1, 3)

        # 5. Process Button
        self.processButton = QtWidgets.QPushButton("Process")
        self.processButton.clicked.connect(self.process_requested.emit)
        self.processButton.setStyleSheet("padding: 5px;")
        self.layout.addWidget(self.processButton, 7, 2, 1, 1)

        # 6. Plot widgets
        self.canvas_baseline = ChromatogramPlotWidget()
        self.canvas_avgMS = pg.PlotWidget() # Placeholder for Avg MS
        self.layout.addWidget(self.canvas_baseline, 0, 2, 3, 2)
        self.layout.addWidget(self.canvas_avgMS, 3, 2, 3, 2)

        self.layout.setRowStretch(2, 3)
        self.layout.setRowStretch(5, 3)
        self.layout.setColumnStretch(2, 4)
    
    # --- Mode Handling ---

    def on_mode_changed(self, mode):
        """Emits mode change signal and updates local UI state."""
        self.mode = mode
        self._update_mode_ui(mode)
        self.mode_changed.emit(mode)

    def _update_mode_ui(self, mode):
        """Disables LC widgets if in MS Only mode."""
        is_lc = (mode == "LC/GC-MS" or mode == "LC/GC Only")
        self.listLC.setEnabled(is_lc)
        self.browseLC.setEnabled(is_lc)
        self.button_clear_LC.setEnabled(is_lc)

    # --- File Handling ---
    def handle_files_dropped(self, file_paths, file_type):
        """
        Validates and adds dropped files, then emits signal for Controller.
        """
        valid_extensions = {
            "LC": [".txt", ".csv"],
            "MS": [".mzml"],
            "Annotations": [".txt"]
        }
        
        added_files = []
        for path in file_paths:
            p = Path(path)
            # Simple recursive folder check
            if p.is_dir():
                for f in p.rglob('*'):
                    if f.suffix.lower() in valid_extensions.get(file_type, []):
                        added_files.append(str(f))
            elif p.suffix.lower() in valid_extensions.get(file_type, []):
                added_files.append(str(p))
            else:
                logger.warning(f"Ignored invalid file for {file_type}: {path}")

        if not added_files:
            self.status_message.emit("No valid files found.", 2000)
            return

        # Add to UI List
        target_list = self.listLC if file_type == "LC" else self.listMS
        for f in added_files:
            target_list.addItem(os.path.basename(f))

        self.status_message.emit(f"Added {len(added_files)} {file_type} files.", 3000)

        # Notify Controller to update Model
        self.files_loaded.emit(file_type, added_files)

    def on_browse_lc(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, 
            "Select LC Files", 
            str(QtCore.QDir.homePath()),
            "Text Files (*.txt);;CSV Files (*.csv);;All Files (*)",
        )
        if files:
            self.handle_files_dropped(files, "LC")

    def on_browse_ms(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, 
            "Select MS Files", 
            str(QtCore.QDir.homePath()),
            "MzML Files (*.mzML);;All Files (*)"
        )
        if files:
            self.handle_files_dropped(files, "MS")

    # --- Ion List Management ---

    def _load_ion_config_names(self):
        """Reads config.json to populate the dropdown."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    # Keep "Create new..." at the top, then sorted keys
                    keys = sorted(list(data.keys()))
                    self.comboBoxIonLists.addItems(keys)
            except Exception as e:
                logger.error(f"Failed to load ion config: {e}")
                self.status_message.emit("Error loading ion config.", 3000)

    def update_ion_list(self):
        """Populates the table based on combo selection."""
        selection = self.comboBoxIonLists.currentText()
        
        # Handle "Create new" or empty selection
        if not selection or selection == "Create new ion list...":
            self.ionTable.setRowCount(0)
            return

        if not self.config_path.exists():
            return

        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
            
            ion_data = data.get(selection, {})
            self.ionTable.setRowCount(len(ion_data))
            
            for row, (name, details) in enumerate(ion_data.items()):
                # Name
                self.ionTable.setItem(row, 0, QtWidgets.QTableWidgetItem(str(name)))
                
                # Ions (Handle list or string legacy format)
                ions = details.get("ions", [])
                if isinstance(ions, list):
                    ions_str = ", ".join(map(str, ions))
                else:
                    ions_str = str(ions)
                self.ionTable.setItem(row, 1, QtWidgets.QTableWidgetItem(ions_str))
                
                # Info (Handle list or string legacy format)
                info = details.get("info", [])
                if isinstance(info, list):
                    info_str = ", ".join(map(str, info))
                else:
                    info_str = str(info)
                self.ionTable.setItem(row, 2, QtWidgets.QTableWidgetItem(info_str))
                
        except Exception as e:
            logger.error(f"Error updating ion list: {e}")
            self.status_message.emit(f"Error updating ion list: {e}", 3000)

    def save_ion_list(self):
        """Saves current table content to config.json."""
        current_name = self.comboBoxIonLists.currentText()
        if current_name == "Create new ion list...":
            current_name = ""

        name, ok = QtWidgets.QInputDialog.getText(
            self, "Save Ion List", "Enter name for ion list:", text=current_name
        )
        
        if ok and name:
            new_data = {}
            for row in range(self.ionTable.rowCount()):
                item_name = self.ionTable.item(row, 0)
                item_ions = self.ionTable.item(row, 1)
                item_info = self.ionTable.item(row, 2)
                
                if item_name and item_ions:
                    key = item_name.text()
                    # Parse ions string back to list for storage consistency
                    ions_text = item_ions.text()
                    ions_list = [x.strip() for x in ions_text.split(",") if x.strip()]
                    
                    info_text = item_info.text() if item_info else ""
                    info_list = [x.strip() for x in info_text.split(",") if x.strip()]
                    
                    new_data[key] = {"ions": ions_list, "info": info_list}

            try:
                full_config = {}
                if self.config_path.exists():
                    with open(self.config_path, 'r') as f:
                        full_config = json.load(f)
                
                full_config[name] = new_data
                
                with open(self.config_path, 'w') as f:
                    json.dump(full_config, f, indent=4)
                
                self.status_message.emit(f"Ion list '{name}' saved.", 3000)
                
                # Update combo box if it's a new list
                if self.comboBoxIonLists.findText(name) == -1:
                    self.comboBoxIonLists.addItem(name)
                self.comboBoxIonLists.setCurrentText(name)
                
            except Exception as e:
                logger.error(f"Error saving ion list: {e}")
                QtWidgets.QMessageBox.critical(self, "Error", f"Could not save ion list:\n{e}")

    def delete_ion_list(self):
        """Deletes the currently selected ion list from config."""
        name = self.comboBoxIonLists.currentText()
        if name == "Create new ion list...":
            return

        reply = QtWidgets.QMessageBox.question(
            self, "Delete Ion List", 
            f"Are you sure you want to delete '{name}'?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            try:
                if self.config_path.exists():
                    with open(self.config_path, 'r') as f:
                        full_config = json.load(f)
                    
                    if name in full_config:
                        del full_config[name]
                        
                        with open(self.config_path, 'w') as f:
                            json.dump(full_config, f, indent=4)
                        
                        # Remove from UI
                        idx = self.comboBoxIonLists.findText(name)
                        self.comboBoxIonLists.removeItem(idx)
                        self.comboBoxIonLists.setCurrentIndex(0) # Reset to 'Create new...'
                        self.status_message.emit(f"Ion list '{name}' deleted.", 3000)
            except Exception as e:
                logger.error(f"Error deleting ion list: {e}")
                QtWidgets.QMessageBox.critical(self, "Error", f"Could not delete ion list:\n{e}")

    def clear_ion_list(self):
        """Clears the Ion Table."""
        self.ionTable.setRowCount(0)

    # --- External Access ---
    
    def get_file_list(self, file_type):
        """Helper for Controller to sync state."""
        widget = self.listLC if file_type == "LC" else self.listMS
        return [widget.item(i).text() for i in range(widget.count())]
