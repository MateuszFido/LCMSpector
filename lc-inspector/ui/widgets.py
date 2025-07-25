from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QDialog, QApplication, QDialogButtonBox
from utils.classes import Compound
from datetime import datetime
import json
from pathlib import Path
import pyqtgraph as pg 

class DragDropListWidget(QtWidgets.QListWidget):
    filesDropped = QtCore.pyqtSignal(list)  # Define a custom signal
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)  # Enable accepting drops
        self.setWordWrap(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.contextMenuEvent)

    def contextMenuEvent(self, pos):
        item = self.itemAt(pos)
        if item is not None:
            menu = QtWidgets.QMenu()
            deleteAction = menu.addAction("(⌫/Del) Delete")
            action = menu.exec(self.mapToGlobal(pos))
            if action == deleteAction:
                self.takeItem(self.row(item))
    
    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key.Key_Backspace or event.key() == QtCore.Qt.Key.Key_Delete:
            item = self.currentItem()
            self.takeItem(self.row(item))

    def dragEnterEvent(self, event):
        # Check if the dragged item is a file
        if event.mimeData().hasUrls():
            event.acceptProposedAction()  # Accept the drag event

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)  # Set the drop action to copy
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)  # Set the drop action to copy
            event.accept()
            file_paths = []
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                file_paths.append(file_path)
            self.filesDropped.emit(file_paths) 
        else:
            event.ignore()

class GenericTable(QtWidgets.QTableWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.setShowGrid(True)
        self.setGridStyle(QtCore.Qt.PenStyle.SolidLine)
        self.setStyleSheet("gridline-color: #e0e0e0;")
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.undoStack = QtGui.QUndoStack(self)
        self.undoStack.setUndoLimit(100)
        self.customContextMenuRequested.connect(self.contextMenuEvent)

    def contextMenuEvent(self, event):
        self.menu = QtWidgets.QMenu(self)

        add_row_action = QtGui.QAction(QtGui.QIcon.fromTheme("document-new"), "(⌘+N) Add Row", self)
        add_row_action.triggered.connect(self.append_row)
        self.menu.addAction(add_row_action)

        remove_row_action = QtGui.QAction(QtGui.QIcon.fromTheme("edit-delete"), "(⌫) Remove Row", self)
        remove_row_action.triggered.connect(self.clear_selection)
        self.menu.addAction(remove_row_action)

        select_all_action = QtGui.QAction(QtGui.QIcon.fromTheme("edit-select-all"), "(⌘+A) Select All", self)
        select_all_action.triggered.connect(self.select_all)
        self.menu.addAction(select_all_action)
        
        copy_action = QtGui.QAction(QtGui.QIcon.fromTheme("edit-copy"), "(⌘+C) Copy", self)
        copy_action.triggered.connect(self.copy)
        self.menu.addAction(copy_action)

        paste_action = QtGui.QAction(QtGui.QIcon.fromTheme("edit-paste"), "(⌘+V) Paste", self)
        paste_action.triggered.connect(self.paste_from_clipboard)
        self.menu.addAction(paste_action)

        undo_action = QtGui.QAction(QtGui.QIcon.fromTheme("edit-undo"), "(⌘+Z) Undo", self)
        undo_action.triggered.connect(self.undoStack.undo)
        self.menu.addAction(undo_action)

        redo_action = QtGui.QAction(QtGui.QIcon.fromTheme("edit-redo"), "(⌘+U) Redo", self)
        redo_action.triggered.connect(self.undoStack.redo)
        self.menu.addAction(redo_action)

        self.menu.popup(QtGui.QCursor.pos())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_V and (event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
            self.paste_from_clipboard()
        elif event.key() == Qt.Key.Key_A and (event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
            self.select_all()
        elif event.key() == QtCore.Qt.Key.Key_Backspace or event.key() == QtCore.Qt.Key.Key_Delete:
            self.clear_selection()
        elif event.key() == Qt.Key.Key_C and (event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
            self.copy()
        elif event.key() == Qt.Key.Key_Z and (event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
            self.undoStack.undo()
        elif event.key() == Qt.Key.Key_U and (event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
            self.undoStack.redo()
        elif event.key() == Qt.Key.Key_N and (event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
            self.append_row(self.rowCount())
        else:
            super().keyPressEvent(event)

    def select_all(self):
        self.selectAll()

    def clear_selection(self):
        command = ClearSelectionCommand(self)
        self.undoStack.push(command)

    def paste_from_clipboard(self):
        command = PasteFromClipboardCommand(self)
        self.undoStack.push(command)

    def copy(self):
        command = CopyCommand(self)
        self.undoStack.push(command)

    def insert_row(self, row):
        command = InsertRowCommand(self, row)
        self.undoStack.push(command)
        super().insertRow(row)

    def append_row(self, row):
        # Append row to the end of the table
        self.insert_row(self.rowCount())


    def set_item(self, row, col, item):
        if self.item(row, col) is None or self.item(row, col).text() != item.text():
            command = SetItemCommand(self, row, col, item.text())
            self.undoStack.push(command)
        super().setItem(row, col, item)

class IonTable(GenericTable):
    def __init__(self, view, parent=None):
        super().__init__(50, 3, parent)
        self.setHorizontalHeaderLabels(["Compound", "Expected m/z", "Add. info"])
        self.setObjectName("ionTable")
        self.setStyleSheet("gridline-color: #e0e0e0;")
        self.view = view
    
    def get_items(self):
        items = []
        for row in range(self.rowCount()):
            if self.item(row, 0) is None: continue
            name = self.item(row, 0).text()
            if name == "": continue
            try: 
                ions = [float(x) for x in self.item(row, 1).text().split(",")]
            except ValueError:
                ions = []
            try:
                ion_info = self.item(row, 2).text().split(",")
            except AttributeError:
                ion_info = []
            try:
                compound = Compound(name, ions, ion_info)
                items.append(compound)
            except UnboundLocalError as e:
                #HACK: for now fails silently
                continue        
        return items

    def save_ion_list(self):
        # Prompt the user how they want to name the list
        ion_list_name, okPressed = QtWidgets.QInputDialog.getText(self, "New ion list", "Name the new ion list:")
        if not okPressed: return
        ions = {}
        for row in range(self.rowCount()):
            if self.item(row, 0) is None: continue
            name = self.item(row, 0).text()
            if name == "": continue
            else:
                ions[name] = {}
            try: 
                ions[name]['ions'] = [float(x) for x in self.item(row, 1).text().split(",")]
            except ValueError:
                continue
            try:
                ions[name]['info'] = self.item(row, 2).text().split(",")
            except AttributeError:
                continue
        # Save locally in config.json
        try:
            config_path = Path(__file__).parent.parent / "config.json"
            with open(config_path, "r") as f:
                config = json.load(f)
            config[ion_list_name] = {name: ions[name] for name in ions}
            with open(config_path, "w") as f:
                json.dump(config, f, indent=4)
            self.view.comboBoxIonLists.clear()
            self.view.comboBoxIonLists.addItem("Create new ion list...")
            self.view.comboBoxIonLists.addItems(config.keys())
            self.view.statusbar.showMessage(f"{datetime.now().strftime("%d/%m/%Y %H:%M:%S")} -- Saved new ion list: \"{ion_list_name}\".", 5000)
        except Exception as e:
            print(f"Could not save ions to config.json: {e}")

    def delete_ion_list(self):
        # Slot for the delete button, prompt the user and if they confirm, delete the currently selected ion list
        ion_list_name = self.view.comboBoxIonLists.currentText()
        msgBox = QtWidgets.QMessageBox()
        msgBox.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        msgBox.setText(f"Are you sure you want to delete the ion list \"{ion_list_name}\"? This cannot be undone.")
        msgBox.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
        msgBox.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
        if msgBox.exec() == QtWidgets.QMessageBox.StandardButton.Yes:
            config_path = Path(__file__).parent.parent / "config.json"
            with open(config_path, "r+") as f:
                config = json.load(f)
                config.pop(ion_list_name)
                f.seek(0)
                json.dump(config, f, indent=4)
                f.truncate()
            self.view.comboBoxIonLists.clear()
            self.view.comboBoxIonLists.addItem("Create new ion list...")
            self.view.comboBoxIonLists.addItems(config.keys())
            self.view.statusbar.showMessage(f"{datetime.now().strftime("%d/%m/%Y %H:%M:%S")} -- Deleted ion list: \"{ion_list_name}\".", 5000)

class ClearSelectionCommand(QtGui.QUndoCommand):
    def __init__(self, table):
        super().__init__()
        self.table = table
        self.items = table.selectedItems()
        self.texts = [item.text() for item in self.items]

    def redo(self):
        for item in self.items:
            item.setText("")

    def undo(self):
        for item, text in zip(self.items, self.texts):
            item.setText(text)


class PasteFromClipboardCommand(QtGui.QUndoCommand):
    def __init__(self, table):
        super().__init__()
        self.table = table
        self.clipboard_text = QtWidgets.QApplication.clipboard().text()
        self.current_row = table.currentRow()
        self.current_col = table.currentColumn()
        self.items = []
        self.redo()

    def redo(self):
        rows = self.clipboard_text.splitlines()
        row_index = self.current_row
        col_index = self.current_col
        for row_data in rows:
            columns = row_data.split('\t')
            col_index = self.current_col
            for value in columns:
                item = QtWidgets.QTableWidgetItem(value)
                self.table.setItem(row_index, col_index, item)
                self.items.append(item)
                col_index += 1
            row_index += 1

    def undo(self):
        for item in reversed(self.items):
            self.table.takeItem(self.table.row(item), self.table.column(item))


class CopyCommand(QtGui.QUndoCommand):
    def __init__(self, table):
        super().__init__()
        self.table = table
        self.clipboard_text = ""
        self.items = table.selectedIndexes()
        self.redo()

    def redo(self):
        try:
            self.clipboard_text = "\t".join([str(item.data()) for item in self.items])
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.setText(self.clipboard_text)
        except TypeError:
            pass

    def undo(self):
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText("")


class InsertRowCommand(QtGui.QUndoCommand):
    def __init__(self, table, row):
        super().__init__()
        self.table = table
        self.row = row

    def redo(self):
        self.table.insertRow(self.row)

    def undo(self):
        self.table.removeRow(self.row)


class SetItemCommand(QtGui.QUndoCommand):
    def __init__(self, table, row, col, value):
        super().__init__()
        self.table = table
        self.row = row
        self.col = col
        self.value = value
        self.old_value = table.item(row, col).text() if table.item(row, col) else ""

    def redo(self):
        try:
            item = QtWidgets.QTableWidgetItem(self.value)
        except:
            item = None
        if item is None:
            item = QtWidgets.QTableWidgetItem(self.value)
            self.table.setItem(self.row, self.col, item)
        else:
            item.setText(self.value)

    def undo(self):
        item = self.table.item(self.row, self.col)
        if item is None:
            self.table.takeItem(self.row, self.col)
        else:
            item.setText(self.old_value)

class UnifiedResultsTable(GenericTable):
    """
    Unified table widget that combines the functionality of tableWidget_files and tableWidget_concentrations.
    Shows file names, calibration options, concentrations, and ion intensities in a single scrollable table.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("unifiedResultsTable")
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        
        # Enable horizontal scrolling
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setStretchLastSection(False)
        
        # Store compound information for dynamic column generation
        self.compounds = []
        self.file_data = {}
        
    def contextMenuEvent(self, event):
        """
        Override context menu to disable row deletion while preserving other functionality.
        """
        self.menu = QtWidgets.QMenu(self)

        # Keep useful actions but remove row deletion
        select_all_action = QtGui.QAction(QtGui.QIcon.fromTheme("edit-select-all"), "(⌘+A) Select All", self)
        select_all_action.triggered.connect(self.select_all)
        self.menu.addAction(select_all_action)
        
        copy_action = QtGui.QAction(QtGui.QIcon.fromTheme("edit-copy"), "(⌘+C) Copy", self)
        copy_action.triggered.connect(self.copy)
        self.menu.addAction(copy_action)

        paste_action = QtGui.QAction(QtGui.QIcon.fromTheme("edit-paste"), "(⌘+V) Paste", self)
        paste_action.triggered.connect(self.paste_from_clipboard)
        self.menu.addAction(paste_action)

        undo_action = QtGui.QAction(QtGui.QIcon.fromTheme("edit-undo"), "(⌘+Z) Undo", self)
        undo_action.triggered.connect(self.undoStack.undo)
        self.menu.addAction(undo_action)

        redo_action = QtGui.QAction(QtGui.QIcon.fromTheme("edit-redo"), "(⌘+U) Redo", self)
        redo_action.triggered.connect(self.undoStack.redo)
        self.menu.addAction(redo_action)

        self.menu.popup(QtGui.QCursor.pos())

    def keyPressEvent(self, event):
        """
        Override key press events to disable row deletion while preserving other shortcuts.
        """
        if event.key() == Qt.Key.Key_V and (event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
            self.paste_from_clipboard()
        elif event.key() == Qt.Key.Key_A and (event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
            self.select_all()
        elif event.key() == Qt.Key.Key_C and (event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
            self.copy()
        elif event.key() == Qt.Key.Key_Z and (event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
            self.undoStack.undo()
        elif event.key() == Qt.Key.Key_U and (event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
            self.undoStack.redo()
        # Note: Deliberately NOT handling Delete/Backspace keys to prevent row deletion
        else:
            # Call QTableWidget's keyPressEvent directly to skip GenericTable's row deletion
            QtWidgets.QTableWidget.keyPressEvent(self, event)
        
    def setup_columns(self, compound):
        """
        Set up the table columns based on a single compound and its ions.
        
        Parameters:
        -----------
        compound : Compound
            Single Compound object containing ion information
        """
        self.current_compound = compound
        
        # Base columns: File, Calibration checkbox, Concentration
        base_headers = ["File", "Calibration?", "Concentration"]
        
        # Dynamic columns for the current compound's ions
        ion_headers = []
        if compound and compound.ion_info:
            for ion_info in compound.ion_info:
                # Add MS intensity column for each ion
                ion_headers.append(f"{ion_info} (MS)")
                # Add LC intensity column for each ion if available
                ion_headers.append(f"{ion_info} (LC)")
        
        all_headers = base_headers + ion_headers
        
        self.setColumnCount(len(all_headers))
        self.setHorizontalHeaderLabels(all_headers)
        
        # Set appropriate column widths
        self.setColumnWidth(0, 200)  # File column
        self.setColumnWidth(1, 150)  # Calibration checkbox column
        self.setColumnWidth(2, 150)  # Concentration column
        
        # Set ion columns to reasonable width
        for i in range(3, len(all_headers)):
            self.setColumnWidth(i, 120)
    
    def populate_data(self, file_concentrations, ms_measurements, current_compound):
        """
        Populate the table with file data, concentrations, and ion intensities for the current compound.
        
        Parameters:
        -----------
        file_concentrations : list
            List of [filename, concentration] pairs
        ms_measurements : dict
            Dictionary of MS measurement objects
        current_compound : Compound
            The currently selected compound to display data for
        """
        self.file_data = {}
        
        # Clear existing data but preserve row count and basic structure
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                if col >= 3:  # Only clear ion data columns, preserve file/calibration/concentration
                    self.setItem(row, col, None)
        
        # If no rows exist yet, set them up
        if self.rowCount() != len(file_concentrations):
            self.setRowCount(len(file_concentrations))
        
        for row, (filename, concentration) in enumerate(file_concentrations):
            # Store file data for later retrieval
            self.file_data[row] = filename
            
            # Column 0: File name (only set if not already set)
            if not self.item(row, 0):
                file_item = QtWidgets.QTableWidgetItem(filename)
                file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.setItem(row, 0, file_item)
            
            # Column 1: Calibration checkbox (only set if not already set)
            if not self.cellWidget(row, 1):
                checkbox_widget = QtWidgets.QWidget()
                checkbox = QtWidgets.QCheckBox()
                checkbox.setChecked(False)
                layout = QtWidgets.QHBoxLayout(checkbox_widget)
                layout.addWidget(checkbox)
                layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.setContentsMargins(0, 0, 0, 0)
                self.setCellWidget(row, 1, checkbox_widget)
            
            # Column 2: Concentration (editable) - update if changed
            if not self.item(row, 2) or self.item(row, 2).text() != (concentration or ""):
                conc_item = QtWidgets.QTableWidgetItem(concentration or "")
                self.setItem(row, 2, conc_item)
            
            # Dynamic columns: Ion intensities for current compound only
            if current_compound and hasattr(current_compound, 'ions'):
                col_index = 3
                ms_file = ms_measurements.get(filename)
                
                if ms_file and ms_file.xics:
                    # Find the matching compound in the MS file
                    ms_compound = None
                    for xic_compound in ms_file.xics:
                        if xic_compound.name == current_compound.name:
                            ms_compound = xic_compound
                            break
                    
                    if ms_compound:
                        for ion_idx, ion in enumerate(current_compound.ions.keys()):
                            # MS Intensity column
                            if ion in ms_compound.ions:
                                ms_intensity = ms_compound.ions[ion]['MS Intensity']
                                if ms_intensity is not None:
                                    import numpy as np
                                    ms_value = f"{np.format_float_scientific(np.round(np.sum(ms_intensity), 0), precision=2)}"
                                else:
                                    ms_value = "N/A"
                            else:
                                ms_value = "N/A"
                            
                            ms_item = QtWidgets.QTableWidgetItem(ms_value)
                            ms_item.setFlags(ms_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                            self.setItem(row, col_index, ms_item)
                            col_index += 1
                            
                            # LC Intensity column
                            if ion in ms_compound.ions:
                                lc_intensity = ms_compound.ions[ion]['LC Intensity']
                                lc_value = str(lc_intensity) if lc_intensity is not None else "N/A"
                            else:
                                lc_value = "N/A"
                            
                            lc_item = QtWidgets.QTableWidgetItem(lc_value)
                            lc_item.setFlags(lc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                            self.setItem(row, col_index, lc_item)
                            col_index += 1
                    else:
                        # Fill with N/A if compound not found in MS file
                        for ion in current_compound.ions.keys():
                            for _ in range(2):  # MS and LC columns
                                na_item = QtWidgets.QTableWidgetItem("N/A")
                                na_item.setFlags(na_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                                self.setItem(row, col_index, na_item)
                                col_index += 1
                else:
                    # Fill with N/A if no MS file found
                    for ion in current_compound.ions.keys():
                        for _ in range(2):  # MS and LC columns
                            na_item = QtWidgets.QTableWidgetItem("N/A")
                            na_item.setFlags(na_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                            self.setItem(row, col_index, na_item)
                            col_index += 1
    
    def get_calibration_files(self):
        """
        Get the files selected for calibration and their concentrations.
        
        Returns:
        --------
        dict : Dictionary mapping filename to concentration for selected calibration files
        """
        selected_files = {}
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, 1)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QtWidgets.QCheckBox)
                if checkbox and checkbox.isChecked():
                    filename = self.item(row, 0).text()
                    concentration = self.item(row, 2).text()
                    selected_files[filename] = concentration
        return selected_files
    
    def get_selected_file(self):
        """
        Get the currently selected file for MS2 display.
        
        Returns:
        --------
        str : Filename of the selected row, or None if no selection
        """
        selected_rows = self.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            return self.item(row, 0).text()
        elif self.rowCount() > 0:
            return self.item(0, 0).text()
        return None
    
    def update_concentrations(self, compounds):
        """
        Update the concentration display after calibration.
        
        Parameters:
        -----------
        compounds : list
            List of Compound objects with updated concentration information
        """
        # This method can be called to refresh concentration displays
        # after calibration calculations are complete
        pass

class ChromatogramPlotWidget(pg.PlotWidget):
    sigKeyPressed = QtCore.pyqtSignal(object)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def keyPressEvent(self, ev):
        self.scene().keyPressEvent(ev)
        self.sigKeyPressed.emit(ev)
