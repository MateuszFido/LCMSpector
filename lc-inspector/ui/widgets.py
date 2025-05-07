from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QDialog, QApplication, QDialogButtonBox
from utils.classes import Compound
from datetime import datetime
import json, __main__
import pyqtgraph as pg 

class PlotWindow(QDialog):
    #FIXME: seems to be unused
    def __init__(self):
        super().__init__()
        self.canvas = pg.GraphicsWidget()
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

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
                logger.error(f"Could not find any compounds in the table: {e}")        
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
            config = json.load(open(__main__.__file__.replace("main.py","config.json"), "r+"))
            config[ion_list_name] = ions
            json.dump(config, open(__main__.__file__.replace("main.py","config.json"), "w"), indent=4)
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
            config = json.load(open(__main__.__file__.replace("main.py","config.json"), "r+"))
            config.pop(ion_list_name)
            json.dump(config, open(__main__.__file__.replace("main.py","config.json"), "w"), indent=4)
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

    def redo(self):
        rows = self.clipboard_text.splitlines()
        for row_data in rows:
            columns = row_data.split('\t')
            for col_index, value in enumerate(columns):
                if self.current_row < self.table.rowCount():
                    item = self.table.item(self.current_row, self.current_col)
                    try:
                        item
                    except:
                        item = None
                    if item is None:
                        item = QtWidgets.QTableWidgetItem(value)
                        self.table.setItem(self.current_row, self.current_col, item)
                    else:
                        item.setText(value)
                else:
                    self.table.insertRow(self.current_row)
                    item = QtWidgets.QTableWidgetItem(value)
                    self.table.setItem(self.current_row, col_index, item)
                self.items.append(item)
            self.current_row += 1

    def undo(self):
        for item in self.items:
            self.table.takeItem(self.table.row(item), self.table.column(item))
        self.table.removeRow(self.current_row - len(rows))


class CopyCommand(QtGui.QUndoCommand):
    def __init__(self, table):
        super().__init__()
        self.table = table
        self.clipboard_text = ""
        self.items = table.selectedItems()

    def redo(self):
        self.clipboard_text = "\t".join([item.text() for item in self.items])
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(self.clipboard_text)

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
            item
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

class ChromatogramPlotWidget(pg.PlotWidget):
    sigKeyPressed = QtCore.pyqtSignal(object)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def keyPressEvent(self, ev):
        self.scene().keyPressEvent(ev)
        self.sigKeyPressed.emit(ev)
