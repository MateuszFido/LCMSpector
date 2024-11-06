from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QApplication
import pyqtgraph as pg
from utils.plotting import plot_absorbance_data, plot_average_ms_data, plot_annotated_LC, plot_annotated_XICs
import sys, traceback

pg.setConfigOptions(antialias=True)

class IonTable(QtWidgets.QTableWidget):
    def __init__(self, parent=None):
        super().__init__(10, 2, parent)
        self.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.horizontalHeader().setStretchLastSection(True)
        self.setHorizontalHeaderLabels(["Compound", "Expected m/z"])
        self.setShowGrid(True)
        self.setGridStyle(QtCore.Qt.PenStyle.SolidLine)
        self.setObjectName("ionTable")
        self.setStyleSheet("gridline-color: #e0e0e0;")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_V and (event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
            self.paste_from_clipboard()
        elif event.key() == Qt.Key.Key_A and (event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier):
            self.select_all()
        elif event.key() == QtCore.Qt.Key.Key_Backspace or event.key() == QtCore.Qt.Key.Key_Delete:
            self.clear_selection()
        else:
            super().keyPressEvent(event)

    def select_all(self):
        self.selectAll()

    def clear_selection(self):
        for item in self.selectedItems():
            item.setText("")  # Clear the text of the selected item

    def paste_from_clipboard(self):
        clipboard = QtWidgets.QApplication.clipboard()
        text = clipboard.text()

        # Split the text into lines and then into cells
        rows = text.splitlines()
        current_row = self.currentRow()

        for row_data in rows:
            # Split the row data into columns (assuming tab-separated values)
            columns = row_data.split('\t')
            for col_index, value in enumerate(columns):
                if current_row < self.rowCount():
                    self.setItem(current_row, col_index, QtWidgets.QTableWidgetItem(value))
                else:
                    # If we exceed the current row count, add a new row
                    self.insertRow(current_row)
                    self.setItem(current_row, col_index, QtWidgets.QTableWidgetItem(value))
            current_row += 1

class DragDropListWidget(QtWidgets.QListWidget):
    filesDropped = QtCore.pyqtSignal(list)  # Define a custom signal
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)  # Enable accepting drops

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

class View(QtWidgets.QMainWindow):
    progress_update = QtCore.pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.progress_update.connect(self.update_progress_bar)

    def handle_files_dropped_LC(self, file_paths):
        """
        Slot to handle the dropped files.
        Updates the model with the new file paths.
        """
        count_ok = 0
        error_shown = False # Safeguard to show error message only once
        for file_path in file_paths:
            if file_path.lower().endswith(".txt"):
                count_ok += 1
                self.listLC.addItem(file_path)  # Add each file path to the listLC widget
            elif not error_shown:
                self.show_critical_error(f"Invalid file type: {file_path.split('/')[-1]}\nCurrently only .txt files are supported.")
                error_shown = True
            else:
                continue
        if count_ok > 0:
            self.statusbar.showMessage(f"Files added, {count_ok} LC files loaded successfully.", 3000)
        self.update_lc_file_list()  # Update the model with the new LC files


    def handle_files_dropped_MS(self, file_paths):
        """
        Slot to handle the dropped files.
        Updates the model with the new file paths.
        """
        count_ok = 0
        error_shown = False # Safeguard to show error message only once
        for file_path in file_paths:
            if file_path.lower().endswith(".mzml"):
                count_ok += 1
                self.listMS.addItem(file_path)  # Add each file path to the listLC widget
            elif not error_shown:
                self.show_critical_error(f"Invalid file type: {file_path.split('/')[-1]}\nCurrently only .mzML files are supported.")
                error_shown = True
            else:
                continue
        if count_ok > 0:
            self.statusbar.showMessage(f"Files added, {count_ok} MS files loaded successfully.", 3000)
        self.update_ms_file_list()  # Update the model with the new LC files

    def handle_files_dropped_annotations(self, file_paths):
        """
        Slot to handle the dropped files.
        Updates the model with the new file paths.
        """
        count_ok = 0
        error_shown = False # Safeguard to show error message only once
        for file_path in file_paths:
            if file_path.lower().endswith(".txt"):
                count_ok += 1
                self.listAnnotations.addItem(file_path)  # Add each file path to the listLC widget
            elif not error_shown:
                self.show_critical_error(f"Invalid file type: {file_path.split('/')[-1]}\nCurrently only .txt files are supported.")
                error_shown = True
            else:
                continue
        if count_ok > 0:
            self.statusbar.showMessage(f"Files added, {count_ok} annotation files loaded successfully.", 3000)
        self.update_annotation_file()  # Update the model with the new LC files


    def on_browseLC(self):
        """
        Slot for the browseLC button. Opens a file dialog for selecting LC files,
        which are then added to the listLC widget and the model is updated.
        """
        lc_file_paths, _ = QFileDialog.getOpenFileNames(self, "Select LC Files", "", "Text Files (*.txt);;All Files (*)")
        if lc_file_paths:
            self.listLC.clear()
            for lc_file_path in lc_file_paths:
                self.listLC.addItem(lc_file_path)  # Add each LC file path to the listLC widget
            self.update_lc_file_list()  # Update the model with the new LC files
            self.statusbar.showMessage(f"Files added, {len(lc_file_paths)} LC files loaded successfully.", 3000)

    def on_browseMS(self):
        """
        Slot for the browseMS button. Opens a file dialog for selecting MS files,
        which are then added to the listMS widget and the model is updated.
        """
        ms_file_paths, _ = QFileDialog.getOpenFileNames(self, "Select MS Files", "", "MzML Files (*.mzML);;All Files (*)")
        if ms_file_paths:
            self.listMS.clear()
            for ms_file_path in ms_file_paths:
                self.listMS.addItem(ms_file_path)  # Add each MS file path to the listMS widget
            self.update_ms_file_list()  # Update the model with the new MS files
            self.statusbar.showMessage(f"Files added, {len(ms_file_paths)} MS files loaded successfully.", 3000)

    def on_browseAnnotations(self):
        """
        Slot for the browseAnnotations button. Opens a file dialog for selecting annotation files,
        which are then added to the listAnnotations widget and the model is updated.
        """
        annotation_file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Annotation Files", "", "Text Files (*.txt);;All Files (*)")
        if annotation_file_paths:
            self.listAnnotations.clear()
            for annotation_file_path in annotation_file_paths:
                self.listAnnotations.addItem(annotation_file_path)  # Add each annotation file path to the listAnnotations widget
            self.update_annotation_file()  # Update the model with the new annotation files
            self.statusbar.showMessage(f"Files added, {len(annotation_file_paths)} annotation files loaded successfully.", 3000)

    def on_process(self):
        # Trigger the processing action in the controller
        """
        Slot for the process button. Triggers the processing action in the controller.
        """
        pass  # This is handled by the controller
    def on_exit(self):
        sys.exit(0)

    def update_lc_file_list(self):
        # Update the model with the LC file paths
        """
        Updates the model with the LC file paths currently in the listLC widget.

        Iterates over the listLC widget, retrieves the text of each item, and stores
        them in a list. This list is then assigned to the `lc_filelist` attribute of
        the model, which is assumed to be accessed through the `controller` attribute.

        This method is called whenever the contents of the listLC widget change,
        such as when new LC files are added or existing ones are removed.
        """
        lc_files = [self.listLC.item(i).text() for i in range(self.listLC.count())]
        self.controller.model.lc_measurements = lc_files  # Assuming you have a reference to the controller

    def update_ms_file_list(self):
        # Update the model with the MS file paths
        """
        Updates the model with the MS file paths currently in the listMS widget.

        Iterates over the listMS widget, retrieves the text of each item, and stores
        them in a list. This list is then assigned to the `ms_filelist` attribute of
        the model, which is assumed to be accessed through the `controller` attribute.

        This method is called whenever the contents of the listMS widget change,
        such as when new MS files are added or existing ones are removed.
        """
        ms_files = [self.listMS.item(i).text() for i in range(self.listMS.count())]
        self.controller.model.ms_measurements = ms_files  # Assuming you have a reference to the controller

    def update_annotation_file(self):
        # Update the model with the annotation file paths
        """
        Updates the model with the annotation file paths currently in the listAnnotations widget.

        Iterates over the listAnnotations widget, retrieves the text of each item, and stores
        them in a list. This list is then assigned to the `annotation_file` attribute of
        the model, which is assumed to be accessed through the `controller` attribute.

        This method is called whenever the contents of the listAnnotations widget change,
        such as when new annotation files are added or existing ones are removed.
        """
        annotation_files = [self.listAnnotations.item(i).text() for i in range(self.listAnnotations.count())]
        self.controller.model.annotations = annotation_files  # Store all annotation files

    def update_progress_bar(self, value):
        self.progressBar.setValue(value)
        self.progressLabel.setText(f"{value}%")

    def show_critical_error(self, message):
        QtWidgets.QMessageBox.critical(self, "Error", message)

    def update_combo_box(self, filenames):
        self.comboBox_currentfile.clear()
        self.comboBox_currentfile.addItems(filenames)

    def display_plots(self, file_lc, file_ms):
        self.canvas_baseline.clear()
        if file_lc:
            try:
                plot_absorbance_data(file_lc.path, file_lc.baseline_corrected, self.canvas_baseline)
            except Exception as e: 
                print(f"No baseline chromatogram found: {e}")
        self.canvas_avgMS.clear()
        if file_ms:
            try:
                plot_average_ms_data(file_ms.path, file_ms.average, self.canvas_avgMS)
            except AttributeError as e: 
                print(f"No average MS found: {e}")
        self.canvas_XICs.clear()
        if file_ms:
            try:
                plot_annotated_XICs(file_ms.path, file_ms.xics, file_ms.compounds, self.canvas_XICs)
            except AttributeError as e: 
                print(f"No XIC plot found: {traceback.format_exc()}")
        self.canvas_annotatedLC.clear()
        if hasattr(file_lc, 'compounds'):
            try:
                plot_annotated_LC(file_lc.path, file_lc.baseline_corrected, file_lc.compounds, self.canvas_annotatedLC)
            except Exception as e: 
                print(f"No annotated LC plot found: {e}")

                
    def update_resolution_label(self, resolution):
        resolutions = [7500, 15000, 30000, 60000, 120000, 240000]
        self.resolutionLabel.setText(f"Mass resolution:\n{resolutions[resolution]}")

    def change_MS_annotations(self):
        if self.comboBox.currentText() == "Use MS-based annotations":
            # Remove annotations widgets
            self.gridLayout_3.removeWidget(self.listAnnotations)
            self.listAnnotations.deleteLater()
            self.labelAnnotations.setVisible(False)
            self.browseAnnotations.setVisible(False)
            # Replace with MS
            self.listMS = DragDropListWidget(parent=self.tabUpload)
            self.gridLayout_3.addWidget(self.listMS, 2, 2, 1, 2)
            self.labelMSdata.setVisible(True)
            self.browseMS.setVisible(True)
        else:
            # Remove MS widgets
            self.gridLayout_3.removeWidget(self.listMS)
            self.listMS.deleteLater()
            self.labelMSdata.setVisible(False)
            self.browseMS.setVisible(False)
            # Replace with annotations
            self.listAnnotations = DragDropListWidget(parent=self.tabUpload)
            self.gridLayout_3.addWidget(self.listAnnotations, 2, 2, 1, 2)
            self.labelAnnotations.setVisible(True)
            self.browseAnnotations.setVisible(True)
        # BUG: lists don't clear properly
        self.listMS.clear()
        self.listAnnotations.clear()
        # Make updates to the model
        self.update_ms_file_list()
        self.update_annotation_file()

    def copy_selection(self):
        """
        Adapted from: https://stackoverflow.com/a/55204654
        """
        selection = self.selectedIndexes()
        if selection:
            rows = sorted(index.row() for index in selection)
            columns = sorted(index.column() for index in selection)
            rowcount = rows[-1] - rows[0] + 1
            colcount = columns[-1] - columns[0] + 1
            table = [[''] * colcount for _ in range(rowcount)]
            for index in selection:
                row = index.row() - rows[0]
                column = index.column() - columns[0]
                table[row][column] = index.data()
            stream = io.StringIO()
            csv.writer(stream, delimiter='\t').writerows(table)
            QtWidgets.qApp.clipboard().setText(stream.getvalue())
        return
            
    def setupUi(self, MainWindow):
        """
        Sets up the UI components for the main window.

        Parameters
        ----------
        MainWindow : QMainWindow
            The main window object for which the UI is being set up.
        
        This method configures the main window, central widget, tab widget, and various
        UI elements such as buttons, labels, combo boxes, and sliders. It applies size
        policies, sets geometries, and associates various UI elements with their respective
        actions. Additionally, it sets up the menu bar with file, edit, and help menus.
        """
        
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(860, 700)
        MainWindow.setToolTip("")
        MainWindow.setToolTipDuration(-1)
        MainWindow.setTabShape(QtWidgets.QTabWidget.TabShape.Rounded)
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.centralwidget.setMinimumSize(QtCore.QSize(850, 640))
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.tabWidget = QtWidgets.QTabWidget(parent=self.centralwidget)
        self.tabWidget.setTabPosition(QtWidgets.QTabWidget.TabPosition.North)
        self.tabWidget.setElideMode(QtCore.Qt.TextElideMode.ElideMiddle)
        self.tabWidget.setUsesScrollButtons(True)
        self.tabWidget.setTabBarAutoHide(False)
        self.tabWidget.setObjectName("tabWidget")
        self.tabUpload = QtWidgets.QWidget()
        self.tabUpload.setObjectName("tabUpload")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.tabUpload)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.ionTable = IonTable(parent=self.tabUpload)
        self.gridLayout_3.addWidget(self.ionTable, 2, 4, 1, 2)
        self.warning = QtWidgets.QLabel(parent=self.tabUpload)
        self.warning.setWordWrap(True)
        self.warning.setObjectName("warning")
        self.gridLayout_3.addWidget(self.warning, 3, 4, 1, 2)
        self.browseLC = QtWidgets.QPushButton(parent=self.tabUpload)
        self.browseLC.setObjectName("browseLC")
        self.gridLayout_3.addWidget(self.browseLC, 1, 1, 1, 1)
        self.comboBox = QtWidgets.QComboBox(parent=self.tabUpload)
        self.comboBox.setObjectName("comboBox")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.gridLayout_3.addWidget(self.comboBox, 0, 0, 1, 2)
        self.browseMS = QtWidgets.QPushButton(parent=self.tabUpload)
        self.browseMS.setObjectName("browseMS")
        self.browseAnnotations = QtWidgets.QPushButton(parent=self.tabUpload)
        self.browseAnnotations.setObjectName("browseAnnotations")
        self.gridLayout_3.addWidget(self.browseAnnotations, 1, 3, 1, 1)
        self.browseAnnotations.setVisible(False)
        self.gridLayout_3.addWidget(self.browseMS, 1, 3, 1, 1)
        self.labelLCdata = QtWidgets.QLabel(parent=self.tabUpload)
        self.labelLCdata.setObjectName("labelLCdata")
        self.gridLayout_3.addWidget(self.labelLCdata, 1, 0, 1, 1)
        self.labelMSdata = QtWidgets.QLabel(parent=self.tabUpload)
        self.labelMSdata.setObjectName("labelMSdata")
        self.labelAnnotations = QtWidgets.QLabel(parent=self.tabUpload)
        self.labelAnnotations.setObjectName("labelAnnotations")
        self.gridLayout_3.addWidget(self.labelAnnotations, 1, 2, 1, 1)
        self.labelAnnotations.setVisible(False)
        self.gridLayout_3.addWidget(self.labelMSdata, 1, 2, 1, 1)
        self.listLC = DragDropListWidget(parent=self.tabUpload)
        self.listLC.setObjectName("listLC")
        self.gridLayout_3.addWidget(self.listLC, 2, 0, 2, 2)
        self.listMS = DragDropListWidget(parent=self.tabUpload)
        self.listMS.setObjectName("listMS")
        self.gridLayout_3.addWidget(self.listMS, 2, 2, 1, 2)
        self.labelIonList = QtWidgets.QLabel(parent=self.tabUpload)
        self.labelIonList.setObjectName("labelIonList")
        self.gridLayout_3.addWidget(self.labelIonList, 1, 4, 1, 1)
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.resSlider = QtWidgets.QSlider(parent=self.tabUpload)
        self.resSlider.setSizeIncrement(QtCore.QSize(0, 0))
        self.resSlider.setMinimum(0)
        self.resSlider.setMaximum(5)
        self.resSlider.setSingleStep(1)
        self.resSlider.setPageStep(1)
        self.resSlider.setProperty("value", 4)
        self.resSlider.setSliderPosition(4)
        self.resSlider.setTracking(True)
        self.resSlider.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.resSlider.setTickPosition(QtWidgets.QSlider.TickPosition.TicksAbove)
        self.resSlider.setTickInterval(1)
        self.resSlider.setObjectName("resSlider")
        self.gridLayout.addWidget(self.resSlider, 0, 1, 2, 1)
        self.resolutionLabel = QtWidgets.QLabel(parent=self.tabUpload)
        self.resolutionLabel.setObjectName("resolutionLabel")
        self.resolutionLabel.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.gridLayout.addWidget(self.resolutionLabel, 0, 0, 1, 1, QtCore.Qt.AlignmentFlag.AlignHCenter|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.gridLayout_3.addLayout(self.gridLayout, 3, 2, 1, 2)
        self.processButton = QtWidgets.QPushButton(parent=self.tabUpload)
        self.processButton.setObjectName("processButton")
        self.gridLayout_3.addWidget(self.processButton, 4, 2, 1, 2)
        self.tabWidget.addTab(self.tabUpload, "")
        self.tabResults = QtWidgets.QWidget()
        self.tabResults.setObjectName("tabResults")

        self.gridLayout_5 = QtWidgets.QGridLayout(self.tabResults)
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.label_results_currentfile = QtWidgets.QLabel(parent=self.tabResults)
        self.label_results_currentfile.setEnabled(True)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_results_currentfile.sizePolicy().hasHeightForWidth())
        self.label_results_currentfile.setSizePolicy(sizePolicy)
        self.label_results_currentfile.setObjectName("label_results_currentfile")
        self.gridLayout_5.addWidget(self.label_results_currentfile, 0, 1, 1, 1)
        self.gridLayout_2 = QtWidgets.QGridLayout()
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.canvas_baseline = pg.PlotWidget(parent=self.tabResults)
        self.canvas_baseline.setObjectName("canvas_baseline")
        self.gridLayout_2.addWidget(self.canvas_baseline, 0, 0, 1, 1)
        self.canvas_avgMS = pg.PlotWidget(parent=self.tabResults)
        self.canvas_avgMS.setObjectName("canvas_avgMS")
        self.gridLayout_2.addWidget(self.canvas_avgMS, 1, 0, 1, 1)
        self.scrollArea = QtWidgets.QScrollArea(parent=self.tabResults)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.canvas_XICs = pg.GraphicsLayoutWidget(parent=self.tabResults)
        self.canvas_XICs.setObjectName("canvas_XICs")
        self.scrollArea.setWidget(self.canvas_XICs)
        self.canvas_XICs.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_2.addWidget(self.scrollArea, 1, 1, 1, 1)
        self.canvas_annotatedLC = pg.PlotWidget(parent=self.tabResults)
        self.canvas_annotatedLC.setObjectName("canvas_annotatedLC")
        self.gridLayout_2.addWidget(self.canvas_annotatedLC, 0, 1, 1, 1)

        self.gridLayout_2.setColumnStretch(0, 2)  # Left column (larger canvases)
        self.gridLayout_2.setColumnStretch(1, 3)  # Right column (smaller canvases)

        self.gridLayout_5.addLayout(self.gridLayout_2, 1, 0, 1, 4)
        self.comboBox_currentfile = QtWidgets.QComboBox(parent=self.tabResults)
        self.comboBox_currentfile.setObjectName("comboBox_currentfile")
        self.gridLayout_5.addWidget(self.comboBox_currentfile, 0, 2, 1, 1)
        self.tabWidget.addTab(self.tabResults, "")
        self.tabWidget.setTabEnabled(self.tabWidget.indexOf(self.tabResults), False)  # Disable the second tab

        self.tabQuantitation = QtWidgets.QWidget()
        self.tabQuantitation.setObjectName("tabQuantitation")
        self.gridLayout_7 = QtWidgets.QGridLayout(self.tabQuantitation)
        self.gridLayout_7.setObjectName("gridLayout_7")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label_3 = QtWidgets.QLabel(parent=self.tabQuantitation)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout_2.addWidget(self.label_3)
        self.comboBox_2 = QtWidgets.QComboBox(parent=self.tabQuantitation)
        self.comboBox_2.setMinimumSize(QtCore.QSize(0, 32))
        self.comboBox_2.setObjectName("comboBox_2")
        self.horizontalLayout_2.addWidget(self.comboBox_2)
        self.gridLayout_7.addLayout(self.horizontalLayout_2, 0, 1, 1, 1)
        self.tableWidget_concentrations = QtWidgets.QTableWidget(parent=self.tabQuantitation)
        self.tableWidget_concentrations.setObjectName("tableWidget_concentrations")
        self.tableWidget_concentrations.setColumnCount(0)
        self.tableWidget_concentrations.setRowCount(0)
        self.gridLayout_7.addWidget(self.tableWidget_concentrations, 2, 1, 1, 1)
        self.gridLayout_6 = QtWidgets.QGridLayout()
        self.gridLayout_6.setObjectName("gridLayout_6")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.quant_label = QtWidgets.QLabel(parent=self.tabQuantitation)
        self.quant_label.setObjectName("quant_label")
        self.horizontalLayout.addWidget(self.quant_label)
        self.pushButton = QtWidgets.QPushButton(parent=self.tabQuantitation)
        self.pushButton.setObjectName("pushButton")
        self.horizontalLayout.addWidget(self.pushButton)
        self.gridLayout_6.addLayout(self.horizontalLayout, 0, 0, 1, 1)
        self.quant_ion_list_view = QtWidgets.QListView(parent=self.tabQuantitation)
        self.quant_ion_list_view.setObjectName("quant_ion_list_view")
        self.gridLayout_6.addWidget(self.quant_ion_list_view, 1, 0, 1, 1)
        self.gridLayout_7.addLayout(self.gridLayout_6, 0, 0, 3, 1)
        self.canvas_calcurve = QtWidgets.QGraphicsView(parent=self.tabQuantitation)
        self.canvas_calcurve.setObjectName("canvas_calcurve")
        self.gridLayout_7.addWidget(self.canvas_calcurve, 1, 1, 1, 1)
        self.tabWidget.addTab(self.tabQuantitation, "")
        self.tabWidget.setTabEnabled(self.tabWidget.indexOf(self.tabQuantitation), False)  # Disable the third tab

        self.gridLayout_4.addWidget(self.tabWidget, 2, 0, 1, 1)
        self.logo = QtWidgets.QLabel(parent=self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.logo.sizePolicy().hasHeightForWidth())
        self.logo.setSizePolicy(sizePolicy)
        self.logo.setMaximumSize(QtCore.QSize(900, 70))
        self.logo.setText("")
        self.logo.setPixmap(QtGui.QPixmap("logo.png"))
        self.logo.setScaledContents(True)
        self.logo.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.logo.setObjectName("logo")
        self.gridLayout_4.addWidget(self.logo, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.progressBar = QtWidgets.QProgressBar()
        self.statusbar.addPermanentWidget(self.progressBar)
        self.progressBar.setVisible(False)  # Initially hidden
        self.progressLabel = QtWidgets.QLabel()
        self.statusbar.addPermanentWidget(self.progressLabel)
        self.progressLabel.setVisible(False)  # Initially hidden

        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 864, 37))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(parent=self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuEdit = QtWidgets.QMenu(parent=self.menubar)
        self.menuEdit.setObjectName("menuEdit")
        self.menuHelp = QtWidgets.QMenu(parent=self.menubar)
        self.menuHelp.setObjectName("menuHelp")
        MainWindow.setMenuBar(self.menubar)
        self.actionSave = QtGui.QAction(parent=MainWindow)
        self.actionSave.setObjectName("actionSave")
        self.actionExit = QtGui.QAction(parent=MainWindow)
        self.actionExit.setObjectName("actionExit")
        self.actionPreferences = QtGui.QAction(parent=MainWindow)
        self.actionPreferences.setObjectName("actionPreferences")
        self.actionReadme = QtGui.QAction(parent=MainWindow)
        self.actionReadme.setObjectName("actionReadme")
        self.actionFile = QtGui.QAction(parent=MainWindow)
        self.actionFile.setObjectName("actionFile")
        self.actionOpen = QtGui.QAction(parent=MainWindow)
        self.actionOpen.setObjectName("actionOpen")
        self.menuFile.addAction(self.actionOpen)
        self.menuFile.addAction(self.actionSave)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionExit)
        self.menuEdit.addAction(self.actionPreferences)
        self.menuHelp.addAction(self.actionReadme)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuEdit.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(0)
        self.resSlider.valueChanged.connect(self.update_resolution_label) 
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        # Connect signals
        #TODO: Implement the rest of the menu items
        #self.actionSave.triggered.connect(self.on_save)
        self.actionExit.triggered.connect(self.on_exit)
        #self.actionPreferences.triggered.connect(self.on_preferences)
        #self.actionReadme.triggered.connect(self.on_readme)
        self.browseLC.clicked.connect(self.on_browseLC)
        self.browseMS.clicked.connect(self.on_browseMS)
        self.browseAnnotations.clicked.connect(self.on_browseAnnotations)
        self.processButton.clicked.connect(self.on_process)
        self.listLC.filesDropped.connect(self.handle_files_dropped_LC)
        self.listMS.filesDropped.connect(self.handle_files_dropped_MS)
        self.comboBox.currentIndexChanged.connect(self.change_MS_annotations)


    def retranslateUi(self, MainWindow):
        """
        Set the text of the UI elements according to the current locale.
        
        Parameters
        ----------
            MainWindow: The main window object for which the UI is being set up.
        """
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "LC-Inspector"))
        self.warning.setText(_translate("MainWindow", "Warning: Mass resolution above 60,000 is CPU-expensive and may take a long time to compute"))
        self.browseLC.setText(_translate("MainWindow", "Browse"))
        self.comboBox.setItemText(0, _translate("MainWindow", "Use MS-based annotations"))
        self.comboBox.setItemText(1, _translate("MainWindow", "Use pre-annotated chromatograms"))
        self.browseMS.setText(_translate("MainWindow", "Browse"))
        self.browseAnnotations.setText(_translate("MainWindow", "Browse"))
        self.labelAnnotations.setText(_translate("MainWindow", "Annotations (.txt)"))
        self.labelLCdata.setText(_translate("MainWindow", "LC data (.txt)"))
        self.labelMSdata.setText(_translate("MainWindow", "MS data (.mzML)"))
        self.labelIonList.setText(_translate("MainWindow", "Targeted m/z values:"))
        self.resSlider.setToolTip(_translate("MainWindow", "Set the resolution with which to interpolate a new m/z axis from the MS data. Default: 120,000"))
        self.resolutionLabel.setToolTip(_translate("MainWindow", "Set the resolution with which to interpolate a new m/z axis from the MS data. Default: 120,000"))
        self.resolutionLabel.setText(_translate("MainWindow", "Mass resolution:\n120,000"))
        self.processButton.setText(_translate("MainWindow", "Process"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabUpload), _translate("MainWindow", "Upload"))
        self.label_results_currentfile.setText(_translate("MainWindow", "Current file:"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabResults), _translate("MainWindow", "Results"))
        self.label_3.setText(_translate("MainWindow", "Compound:"))
        self.quant_label.setText(_translate("MainWindow", "Choose which file(s) to use for calibration:"))
        self.pushButton.setText(_translate("MainWindow", "Calibrate"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabQuantitation), _translate("MainWindow", "Quantitation"))
        self.menuFile.setTitle(_translate("MainWindow", "File"))
        self.menuEdit.setTitle(_translate("MainWindow", "Edit"))
        self.menuHelp.setTitle(_translate("MainWindow", "Help"))
        self.actionSave.setText(_translate("MainWindow", "Save"))
        self.actionSave.setShortcut(_translate("MainWindow", "Ctrl+S"))
        self.actionExit.setText(_translate("MainWindow", "Exit"))
        self.actionExit.setShortcut(_translate("MainWindow", "Ctrl+W"))
        self.actionPreferences.setText(_translate("MainWindow", "Preferences"))
        self.actionReadme.setText(_translate("MainWindow", "Readme"))
        self.actionReadme.setShortcut(_translate("MainWindow", "F10"))
        self.actionFile.setText(_translate("MainWindow", "File"))
        self.actionOpen.setText(_translate("MainWindow", "Open"))
        self.actionOpen.setShortcut(_translate("MainWindow", "Ctrl+O"))
