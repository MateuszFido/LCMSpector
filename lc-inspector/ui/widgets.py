from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QDialog, QApplication
from utils.measurements import Compound

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
        self.customContextMenuRequested.connect(self.contextMenuEvent)

    def contextMenuEvent(self, event):
        self.menu = QtWidgets.QMenu(self)
        
        copy_action = QtGui.QAction(QtGui.QIcon.fromTheme("edit-copy"), "(⌘+C) Copy", self)
        copy_action.triggered.connect(self.copy)
        self.menu.addAction(copy_action)

        paste_action = QtGui.QAction(QtGui.QIcon.fromTheme("edit-paste"), "(⌘+V) Paste", self)
        paste_action.triggered.connect(self.paste_from_clipboard)
        self.menu.addAction(paste_action)

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
        else:
            super().keyPressEvent(event)

    def select_all(self):
        self.selectAll()

    def clear_selection(self):
        for item in self.selectedItems():
            item.setText("")  # Clear the text of the selected item

    def copy(self):
        selection = self.selectedItems()
        if selection:
            text = "\t".join([item.text() for item in selection])
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.setText(text)
        
    def paste_from_clipboard(self):
        clipboard = QtWidgets.QApplication.clipboard()
        text = clipboard.text()

        # Split the text into lines and then into cells
        rows = text.splitlines()
        current_row = self.currentRow()
        current_col = self.currentColumn()
        for row_data in rows:
            # Split the row data into columns (assuming tab-separated values)
            columns = row_data.split('\t')
            for col_index, value in enumerate(columns):
                if current_row < self.rowCount():
                    self.setItem(current_row, current_col, QtWidgets.QTableWidgetItem(value))
                else:
                    # If we exceed the current row count, add a new row
                    self.insertRow(current_row)
                    self.setItem(current_row, col_index, QtWidgets.QTableWidgetItem(value))
            current_row += 1

class IonTable(GenericTable):
    def __init__(self, parent=None):
        super().__init__(50, 3, parent)
        self.setHorizontalHeaderLabels(["Compound", "Expected m/z", "Add. info"])
        self.setObjectName("ionTable")
        self.setStyleSheet("gridline-color: #e0e0e0;")
    
    def get_items(self):
        items = []
        for row in range(self.rowCount()):
            for col in range(2):
                if self.item(row, col) is None:
                    continue
                name = self.item(row, 0).text()
                ions = [float(x) for x in self.item(row, 1).text().split(",")]
                ion_info = self.item(row, 2).text().split(",")
            try:
                compound = Compound(name, ions, ion_info)
                items.append(compound)
            except UnboundLocalError as e:
                logger.error(f"Could not find any compounds in the table: {e}")        
        return items