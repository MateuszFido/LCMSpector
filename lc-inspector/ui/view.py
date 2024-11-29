from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QDialog, QApplication
import pyqtgraph as pg
from utils.plotting import plot_absorbance_data, plot_average_ms_data, plot_annotated_LC, plot_annotated_XICs, plot_calibration_curve
import sys, traceback, logging, json, __main__
from utils.measurements import Compound
from pyqtgraph.dockarea import Dock, DockArea
import numpy as np
from scipy.signal import find_peaks

pg.setConfigOptions(antialias=True)
logger = logging.getLogger(__name__)

class IonTable(QtWidgets.QTableWidget):
    def __init__(self, parent=None):
        super().__init__(50, 3, parent)
        self.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.horizontalHeader().setStretchLastSection(True)
        self.setHorizontalHeaderLabels(["Compound", "Expected m/z", "Add. info"])
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
    
    def get_items(self):
        items = []
        for row in range(self.rowCount()):
            for col in range(2):
                if self.item(row, col) is None:
                    continue
                name = self.item(row, 0).text()
                ions = [float(x) for x in self.item(row, 1).text().split(",")]
                ion_info = self.item(row, 2).text().split(",")
            compound = Compound(name, ions, ion_info)
            items.append(compound)
        if len(items) == 0:
            self.show_critical_error("No ions found in table.")
        return items

class PlotWindow(QDialog):
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

    def update_ion_list(self):
        lists = json.load(open(__main__.__file__.replace("main.py","config.json"), "r"))
        if self.comboBoxIonLists.currentText() == "Amino acids and polyamines (DEEMM)":
            ion_list = lists["aminoacids_and_polyamines"]
        elif self.comboBoxIonLists.currentText() == "Short-chain fatty acids":
            ion_list = lists["scfas"]
        elif self.comboBoxIonLists.currentText() == "Phenolic acids":
            ion_list = lists["phenolic_acids"]
        elif self.comboBoxIonLists.currentText() == "Flavonoids":
            ion_list = lists["flavonoids"]
        elif self.comboBoxIonLists.currentText() == "Fatty acids":
            ion_list = lists["fatty_acids"]
        else:
            ion_list = None

        self.ionTable.clearContents()
        if ion_list:
            i=0
            self.ionTable.setRowCount(len(ion_list))
            for compound, keywords in ion_list.items():
                self.ionTable.setItem(i, 0, QtWidgets.QTableWidgetItem(str(compound)))
                for key, value in keywords.items():
                    if key == "ions":
                        self.ionTable.setItem(i, 1, QtWidgets.QTableWidgetItem(', '.join(map(str,value))))
                    elif key == "info":
                        self.ionTable.setItem(i, 2, QtWidgets.QTableWidgetItem(', '.join(map(str,value))))
                i+=1


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

    def update_table_quantitation(self, concentrations):
        self.tableWidget_files.clear()
        self.tableWidget_files.setColumnCount(3)
        self.tableWidget_files.setShowGrid(True)
        self.tableWidget_files.setStyleSheet("gridline-color: #e0e0e0;")
        for row, item in enumerate(concentrations):
            self.tableWidget_files.insertRow(row)
            self.tableWidget_files.setItem(row, 0, QtWidgets.QTableWidgetItem(item[0]))
            self.tableWidget_files.setItem(row, 1, QtWidgets.QTableWidgetItem(item[1]))
            checkbox = QtWidgets.QTableWidgetItem("")
            checkbox.setCheckState(Qt.CheckState.Unchecked)
            self.tableWidget_files.setItem(row, 2, checkbox)
        self.tableWidget_files.setHorizontalHeaderLabels(["File", "Concentration", "Use for calibration?"])
        self.tableWidget_files.resizeColumnsToContents()

    def get_calibration_files(self):
        selected_files = {}
        for i in range(self.tableWidget_files.rowCount()):
            item = self.tableWidget_files.item(i, 2)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                selected_files[self.tableWidget_files.item(i, 0).text()] = self.tableWidget_files.item(i, 1).text()
        return selected_files

    def update_choose_compound(self, compounds):
        self.comboBoxChooseCompound.clear()
        for compound in compounds:
            self.comboBoxChooseCompound.addItem(compound.name)
        self.tableWidget_concentrations.setColumnCount(len(compounds))
        self.tableWidget_concentrations.setHorizontalHeaderLabels([compound.name for compound in compounds])

    def display_plots(self, file_lc, file_ms):
        self.canvas_baseline.clear()
        if file_lc:
            try:
                plot_absorbance_data(file_lc.path, file_lc.baseline_corrected, self.canvas_baseline)
                self.canvas_baseline.getPlotItem().addItem(self.crosshair_v, ignoreBounds=True)
                self.canvas_baseline.getPlotItem().addItem(self.crosshair_h, ignoreBounds=True)
                self.crosshair_v_label = pg.InfLineLabel(self.crosshair_v, text="0 s", color='#b8b8b8', rotateAxis=(1, 0))
                self.crosshair_h_label = pg.InfLineLabel(self.crosshair_h, text="0 a.u.", color='#b8b8b8', rotateAxis=(1, 0))
            except Exception as e: 
                logger.error(f"No baseline chromatogram found: {traceback.format_exc()}")

        self.canvas_avgMS.clear()
        if file_ms:
            try:
                plot_average_ms_data(0, file_ms.data, self.canvas_avgMS)
            except AttributeError as e: 
                logger.error(f"No average MS found: {traceback.format_exc()}")

        self.canvas_XICs.clear()
        if file_ms:
            try:
                plot_annotated_XICs(file_ms.path, file_ms.xics, self.canvas_XICs)
            except AttributeError as e: 
                logger.error(f"No XIC plot found: {traceback.format_exc()}")

        self.canvas_annotatedLC.clear()
        if file_lc and file_ms:
            if file_lc.filename == file_ms.filename:
                try:
                    self.curve_list = plot_annotated_LC(file_lc.path, file_lc.baseline_corrected, self.canvas_annotatedLC)
                    for curve in self.curve_list.keys():
                        curve.sigClicked.connect(lambda c: self.highlight_peak(c, file_ms.xics))
                except Exception as e: 
                    logger.error(f"No annotated LC plot found: {traceback.format_exc()}")

    def display_calibration_curve(self):
        self.canvas_calibration.clear()
        for compound in self.controller.model.compounds:
            if compound.name == self.comboBoxChooseCompound.currentText():
                try:
                    plot_calibration_curve(compound, self.canvas_calibration)
                except Exception as e: 
                    logger.error(f"No calibration curve found for {compound.name}: {traceback.format_exc()}")

    def highlight_peak(self, selected_curve, xics):
        # Clear previous annotations
        for curve in self.curve_list:
            if curve != selected_curve:
                color = QtGui.QColor(self.curve_list[curve])
                color.setAlpha(50)
                curve.setBrush(color)
                curve.setPen(color)
        for item in self.canvas_annotatedLC.items():
            if isinstance(item, pg.TextItem):
                self.canvas_annotatedLC.removeItem(item)
        # Annotate the selected peak with every compound
        text_items = []
        for compound in xics:
            for j, ion in enumerate(compound.ions.keys()):
                if np.any(np.isclose(compound.ions[ion]['RT'], selected_curve.getData()[0], atol=0.1)): # If the ion's RT overlaps with the RT of selected peak +/- 6 seconds
                    logger.info(f"Compound: {compound.name}, Ion: {ion} at {round(compound.ions[ion]['RT'],2)} mins, overlaps with the time range {selected_curve.getData()[0][0]}-{selected_curve.getData()[0][-1]}.")
                    text_item = pg.TextItem(text=f"{compound.ion_info[j]} ({ion})", color='#232323', anchor=(0, 0))
                    text_item.setFont(pg.QtGui.QFont('Arial', 10, weight=pg.QtGui.QFont.Weight.ExtraLight))
                    text_items.append(text_item)
                    self.canvas_annotatedLC.addItem(text_item)
        selected_curve.setBrush(pg.mkBrush('#ee6677'))
        selected_curve.setPen(pg.mkPen('#ee6677'))
        positions = np.linspace(np.max(selected_curve.getData()[1])/2, np.max(selected_curve.getData()[1])+400, 20)
        for i, text_item in enumerate(text_items):
            text_item.setPos(float(np.median(selected_curve.getData()[0]+i//20)), float(positions[i%len(positions)]))

    def update_labels_avgMS(self):
        # Remove all the previous labels
        for item in self.canvas_avgMS.items():
            if isinstance(item, pg.TextItem):
                self.canvas_avgMS.removeItem(item)
        try:
            data = self.canvas_avgMS.getPlotItem().listDataItems()[0].getData()
        except IndexError as e:
            logger.error(f"Error getting data items for MS viewing. {traceback.format_exc()}")
            return
        current_view_range = self.canvas_avgMS.getViewBox().viewRange()
        # Get the intensity range within the current view range
        mz_range = data[0][np.logical_and(data[0] >= current_view_range[0][0], data[0] <= current_view_range[0][1])]
        indices = [i for i, x in enumerate(data[0]) if x in mz_range]
        intensity_range = data[1][indices]
        peaks, _ = find_peaks(intensity_range, prominence=10)
        # Get the 10 highest peaks within the current view range
        sorted_indices= np.argsort(intensity_range[peaks])[::-1]
        # Get their mz values
        mzs = mz_range[peaks][sorted_indices][0:10]
        intensities = intensity_range[peaks][sorted_indices][0:10]
        for mz, intensity in zip(mzs, intensities):
            text_item = pg.TextItem(text=f"{mz:.4f}", color='#232323', anchor=(0, 0))
            text_item.setFont(pg.QtGui.QFont('Arial', 10, weight=pg.QtGui.QFont.Weight.ExtraLight))
            text_item.setPos(mz, intensity)
            self.canvas_avgMS.addItem(text_item)

    def update_resolution_label(self, resolution):
        resolutions = [7500, 15000, 30000, 60000, 120000, 240000]
        self.resolutionLabel.setText(f"Mass resolution:\n{resolutions[resolution]}")

    def update_crosshair(self, e):
        pos = e[0]
        if self.canvas_baseline.sceneBoundingRect().contains(pos):
            mousePoint = self.canvas_baseline.getPlotItem().getViewBox().mapSceneToView(pos)
            self.crosshair_v.setPos(mousePoint.x())
            self.crosshair_h.setPos(mousePoint.y())
            self.crosshair_v_label.setText(f"{mousePoint.x():.2f} min")
            self.crosshair_h_label.setText(f"{mousePoint.y():.0f} a.u.")

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
    
    def show_scan_at_time_x(self, event):
        mouse_pos = self.canvas_baseline.getPlotItem().getViewBox().mapSceneToView(event._scenePos)
        time_x = float(mouse_pos.x())
        logger.info(f'Clicked the chromatogram at position: {time_x}')
        self.canvas_avgMS.clear()
        file = self.comboBox_currentfile.currentText()
        try:
            plot_average_ms_data(time_x, self.controller.model.ms_measurements[file].data, self.canvas_avgMS)
        except Exception as e:
            logger.error(f"Error displaying average MS for file {file}: {e}")

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
        self.gridLayout_3.addWidget(self.labelIonList, 0, 4, 1, 1)
        
        self.comboBoxIonLists = QtWidgets.QComboBox(parent=self.tabUpload)
        self.comboBoxIonLists.setObjectName("comboBoxIonLists")
        self.comboBoxIonLists.addItem("")
        self.comboBoxIonLists.addItem("Amino acids and polyamines (DEEMM)")
        self.comboBoxIonLists.addItem("Short-chain fatty acids")
        self.comboBoxIonLists.addItem("Fatty acids")
        self.comboBoxIonLists.addItem("Phenolic acids")
        self.comboBoxIonLists.addItem("Flavonoids")
        self.gridLayout_3.addWidget(self.comboBoxIonLists, 1, 4, 1, 2)

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
        self.canvas_baseline.scene().sigMouseClicked.connect(self.show_scan_at_time_x)
        self.crosshair_v = pg.InfiniteLine(angle=90, pen=pg.mkPen(color="#b8b8b8", width=1, style=QtCore.Qt.PenStyle.DashLine), movable=False)
        self.crosshair_h = pg.InfiniteLine(angle=0, pen=pg.mkPen(color="#b8b8b8", style=QtCore.Qt.PenStyle.DashLine, width=1), movable=False)

        self.proxy = pg.SignalProxy(self.canvas_baseline.scene().sigMouseMoved, rateLimit=60, slot=self.update_crosshair)
        self.canvas_baseline.setCursor(Qt.CursorShape.CrossCursor)

        self.gridLayout_2.addWidget(self.canvas_baseline, 0, 0, 1, 1)
        self.canvas_avgMS = pg.PlotWidget(parent=self.tabResults)
        self.canvas_avgMS.setObjectName("canvas_avgMS")
        self.canvas_avgMS.setMouseEnabled(x=True, y=False)
        self.canvas_avgMS.getPlotItem().getViewBox().setAspectLocked(lock=False)            
        self.canvas_avgMS.getPlotItem().getViewBox().setAutoVisible(y=1.0)
        self.canvas_avgMS.getPlotItem().getViewBox().enableAutoRange(axis='y', enable=True)
        self.canvas_avgMS.getPlotItem().getViewBox().sigRangeChangedManually.connect(self.update_labels_avgMS)

        self.gridLayout_2.addWidget(self.canvas_avgMS, 1, 0, 1, 1)
        self.scrollArea = QtWidgets.QScrollArea(parent=self.tabResults)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.canvas_XICs = DockArea(parent=self.tabResults)
        self.canvas_XICs.setObjectName("canvas_XICs")
        self.scrollArea.setWidget(self.canvas_XICs)
        self.canvas_XICs.setContentsMargins(0, 0, 0, 0)
        
        self.gridLayout_2.addWidget(self.scrollArea, 1, 1, 1, 1)
        self.canvas_annotatedLC = pg.PlotWidget(parent=self.tabResults)
        self.canvas_annotatedLC.setObjectName("canvas_annotatedLC")
        self.canvas_annotatedLC.setMouseEnabled(x=True, y=False)
        self.gridLayout_2.addWidget(self.canvas_annotatedLC, 0, 1, 1, 1)

        self.gridLayout_2.setColumnStretch(0, 2)  # Left column
        self.gridLayout_2.setColumnStretch(1, 2)  # Right column 

        self.gridLayout_5.addLayout(self.gridLayout_2, 1, 0, 1, 4)
        self.comboBox_currentfile = QtWidgets.QComboBox(parent=self.tabResults)
        self.comboBox_currentfile.setObjectName("comboBox_currentfile")
        self.gridLayout_5.addWidget(self.comboBox_currentfile, 0, 2, 1, 1)
        self.tabWidget.addTab(self.tabResults, "")
        self.tabWidget.setTabEnabled(self.tabWidget.indexOf(self.tabResults), False)  # Disable the second tab

        self.tabQuantitation = QtWidgets.QWidget()
        self.tabQuantitation.setObjectName("tabQuantitation")
        self.gridLayout_6 = QtWidgets.QGridLayout(self.tabQuantitation)
        self.gridLayout_6.setObjectName("gridLayout_6")
        self.gridLayout_quant = QtWidgets.QGridLayout()
        self.gridLayout_quant.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetDefaultConstraint)
        self.gridLayout_quant.setObjectName("gridLayout_quant")
        self.gridLayout_top_left = QtWidgets.QGridLayout()
        self.gridLayout_top_left.setObjectName("gridLayout_top_left")
        self.label_calibrate = QtWidgets.QLabel(parent=self.tabQuantitation)
        self.label_calibrate.setWordWrap(True)
        self.label_calibrate.setObjectName("label_calibrate")
        self.gridLayout_top_left.addWidget(self.label_calibrate, 0, 0, 1, 1)
        self.calibrateButton = QtWidgets.QPushButton(parent=self.tabQuantitation)
        self.calibrateButton.setObjectName("calibrateButton")
        self.gridLayout_top_left.addWidget(self.calibrateButton, 0, 1, 1, 1)
        self.tableWidget_files = QtWidgets.QTableWidget(parent=self.tabQuantitation)
        self.tableWidget_files.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.tableWidget_files.horizontalHeader().setStretchLastSection(True)
        self.tableWidget_files.setObjectName("tableWidget_files")
        self.tableWidget_files.setColumnCount(3)
        self.tableWidget_files.setRowCount(7)
        self.gridLayout_top_left.addWidget(self.tableWidget_files, 1, 0, 1, 2)
        self.gridLayout_quant.addLayout(self.gridLayout_top_left, 0, 0, 1, 1)
        self.gridLayout_top_right = QtWidgets.QGridLayout()
        self.gridLayout_top_right.setObjectName("gridLayout_top_right")
        self.label_curr_compound = QtWidgets.QLabel(parent=self.tabQuantitation)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_curr_compound.sizePolicy().hasHeightForWidth())
        self.label_curr_compound.setSizePolicy(sizePolicy)
        self.label_curr_compound.setObjectName("label_curr_compound")
        self.gridLayout_top_right.addWidget(self.label_curr_compound, 0, 0, 1, 1)
        self.label_compound = QtWidgets.QLabel(parent=self.tabQuantitation)
        self.label_curr_compound.setSizePolicy(sizePolicy)
        self.label_curr_compound.setObjectName("label_curr_compound")
        self.gridLayout_top_right.addWidget(self.label_curr_compound, 0, 0, 1, 1)
        self.comboBoxChooseCompound = QtWidgets.QComboBox(parent=self.tabQuantitation)
        self.comboBoxChooseCompound.setMinimumSize(QtCore.QSize(0, 32))
        self.comboBoxChooseCompound.setObjectName("comboBoxChooseCompound")
        self.comboBoxChooseCompound.setEnabled(False)
        self.gridLayout_top_right.addWidget(self.comboBoxChooseCompound, 0, 1, 1, 1)
        self.canvas_calibration = pg.PlotWidget()
        self.canvas_calibration.setObjectName("canvas_calibration")
        self.gridLayout_top_right.addWidget(self.canvas_calibration, 1, 0, 1, 2)
        self.gridLayout_quant.addLayout(self.gridLayout_top_right, 0, 1, 1, 1)
        self.tableWidget_concentrations = QtWidgets.QTableWidget(parent=self.tabQuantitation)
        self.tableWidget_concentrations.setObjectName("tableWidget_concentrations")
        self.tableWidget_concentrations.setColumnCount(7)
        self.tableWidget_concentrations.setRowCount(8)
        self.gridLayout_quant.addWidget(self.tableWidget_concentrations, 1, 0, 1, 1)
        self.heatmap = QtWidgets.QGraphicsView(parent=self.tabQuantitation)
        self.heatmap.setObjectName("heatmap")
        self.gridLayout_quant.addWidget(self.heatmap, 1, 1, 1, 1)
        self.gridLayout_6.addLayout(self.gridLayout_quant, 0, 0, 1, 1)
        self.tabWidget.addTab(self.tabQuantitation, "")
        self.tabWidget.setTabEnabled(self.tabWidget.indexOf(self.tabQuantitation), False)  # Disable the second tab

        self.gridLayout_4.addWidget(self.tabWidget, 2, 0, 1, 1)
        self.logo = QtWidgets.QLabel(parent=self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.logo.sizePolicy().hasHeightForWidth())
        self.logo.setSizePolicy(sizePolicy)
        self.logo.setMaximumSize(QtCore.QSize(860, 70))
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
        self.comboBoxIonLists.currentIndexChanged.connect(self.update_ion_list)

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
        self.comboBoxIonLists.setToolTip(_translate("MainWindow", "Choose an ion list from the list of ion lists provided with the software"))
        self.resolutionLabel.setText(_translate("MainWindow", "Mass resolution:\n120,000"))
        self.processButton.setText(_translate("MainWindow", "Process"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabUpload), _translate("MainWindow", "Upload"))
        self.label_results_currentfile.setText(_translate("MainWindow", "Current file:"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabResults), _translate("MainWindow", "Results"))
        self.label_curr_compound.setText(_translate("MainWindow", "Compound:"))
        self.label_calibrate.setText(_translate("MainWindow", "Select the files to be used for calibration."))
        self.calibrateButton.setText(_translate("MainWindow", "Calculate"))
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
