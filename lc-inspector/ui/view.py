from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QDialog, QApplication
import pyqtgraph as pg
from utils.plotting import plot_absorbance_data, plot_average_ms_data, \
plot_annotated_LC, plot_annotated_XICs, plot_calibration_curve,  \
plot_total_ion_current, plot_library_ms2, plot_no_ms2_found, plot_ms2_from_file
import os, sys, traceback, logging, json
from pathlib import Path
from datetime import datetime
from pyqtgraph.dockarea import Dock, DockArea
import numpy as np
from scipy.signal import find_peaks
from ui.widgets import DragDropListWidget, IonTable, GenericTable, ChromatogramPlotWidget, UnifiedResultsTable

pg.setConfigOptions(antialias=True)
logger = logging.getLogger(__name__)
logger.propagate = False

class View(QtWidgets.QMainWindow):
    progress_update = QtCore.pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.progress_update.connect(self.update_progress_bar)

    def handle_files_dropped_LC(self, file_paths):
        """
        Slot to handle the dropped files.
        Updates the model with the new file paths and triggers loading.
        """
        count_ok = 0
        error_shown = False # Safeguard to show error message only once
        for file_path in file_paths:
            # Check if the dropped file is a folder; if yes, check if it contains .txt files
            if os.path.isdir(file_path):
                txt_files = [f for f in os.listdir(file_path) if f.lower().endswith(".txt") or f.lower().endswith(".csv")]
                if len(txt_files) > 0:
                    for txt_file in txt_files:
                        count_ok += 1
                        self.listLC.addItem(os.path.join(file_path, txt_file))  # Add each file path to the listLC widget
                else:
                    continue
            if file_path.lower().endswith(".txt") or file_path.lower().endswith(".csv"):
                count_ok += 1
                self.listLC.addItem(file_path)  # Add each file path to the listLC widget
            elif not error_shown:
                self.show_critical_error(f"Invalid file type: {file_path.split('/')[-1]}\nCurrently only .csv and .txt files are supported.")
                logger.error(f"Invalid file type: {file_path.split('/')[-1]}")
                error_shown = True
            else:
                continue
        if count_ok > 0:
            self.statusbar.showMessage(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -- {count_ok} LC files loaded successfully.", 3000)
        self.update_lc_file_list()  # Update the model with the new LC files
        print(self.controller.model.lc_measurements)
        # Trigger loading process
        self.progressBar.setVisible(True)
        self.progressLabel.setVisible(True)
        self.controller.model.load(self.controller.mode)


    def handle_files_dropped_MS(self, file_paths):
        """
        Slot to handle the dropped files.
        Updates the model with the new file paths and triggers loading.
        """
        count_ok = 0
        error_shown = False # Safeguard to show error message only once
        for file_path in file_paths:
            # Check if the dropped file is a folder; if yes, check if it contains .mzML files
            if os.path.isdir(file_path):
                mzml_files = [f for f in os.listdir(file_path) if f.lower().endswith(".mzml")]
                if len(mzml_files) > 0:
                    count_ok += len(mzml_files)
                    for mzml_file in mzml_files:
                        self.listMS.addItem(os.path.join(file_path, mzml_file))  # Add each file path to the listLC widget
                    continue
            if file_path.lower().endswith(".mzml"):
                count_ok += 1
                self.listMS.addItem(file_path)  # Add each file path to the listLC widget
            elif not error_shown:
                self.show_critical_error(f"Invalid file type: {file_path.split('/')[-1]}\nCurrently only .mzML files are supported.")
                logger.error(f"Invalid file type: {file_path.split('/')[-1]}")
                error_shown = True
            else:
                continue
        if count_ok > 0:
            self.statusbar.showMessage(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -- {count_ok} MS files loaded successfully.", 3000)
        self.update_ms_file_list()  # Update the model with the new LC files
        
        # Trigger loading process
        self.progressBar.setVisible(True)
        self.progressLabel.setVisible(True)
        self.controller.model.load(self.controller.mode)

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
                logger.info(f"Added annotation file: {file_path}")
            elif not error_shown:
                self.show_critical_error(f"Invalid file type: {file_path.split('/')[-1]}\nCurrently only .txt files are supported.")
                logger.error(f"Invalid file type: {file_path.split('/')[-1]}")
                error_shown = True
            else:
                continue
        if count_ok > 0:
            self.statusbar.showMessage(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -- {count_ok} annotation files loaded successfully.", 3000)
        self.update_annotation_file()  # Update the model with the new LC files

    def update_ion_list(self):
        config_path = Path(__file__).parent.parent / "config.json"
        with open(config_path, "r") as f:
            lists = json.load(f)
        if self.comboBoxIonLists.currentText() == "Create new ion list..." or self.comboBoxIonLists.currentText() == "":
            self.ionTable.clearContents()
            return
        else:
            try:
                ion_list = lists[self.comboBoxIonLists.currentText()]
            except:
                logger.error(f"Could not find ion list: {self.comboBoxIonLists.currentText()}")
                self.statusbar.showMessage(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -- Could not find ion list: {self.comboBoxIonLists.currentText()}", 3000)
                ion_list = None

            self.ionTable.clearContents()
            if ion_list:
                i=0
                self.ionTable.setRowCount(len(ion_list))
                for compound, keywords in ion_list.items():
                    self.ionTable.set_item(i, 0, QtWidgets.QTableWidgetItem(str(compound)))
                    for key, value in keywords.items():
                        if key == "ions":
                            self.ionTable.set_item(i, 1, QtWidgets.QTableWidgetItem(', '.join(map(str,value))))
                        elif key == "info":
                            self.ionTable.set_item(i, 2, QtWidgets.QTableWidgetItem(', '.join(map(str,value))))
                    i+=1


    def on_browseLC(self):
        """
        Slot for the browseLC button. Opens a file dialog for selecting LC files,
        which are then added to the listLC widget and the model is updated.
        """
        lc_file_paths, _ = QFileDialog.getOpenFileNames(self, "Select LC Files", "", "Text Files (*.txt);;CSV Files (*.csv);;All Files (*)")
        if lc_file_paths:
            self.clear_list_lc()
            for lc_file_path in lc_file_paths:
                self.listLC.addItem(lc_file_path)  # Add each LC file path to the listLC widget
            self.update_lc_file_list()  # Update the model with the new LC files
            
            # Trigger loading process
            self.progressBar.setVisible(True)
            self.progressLabel.setVisible(True)
            self.controller.model.load(self.controller.mode, "LC")

    def on_browseMS(self):
        """
        Slot for the browseMS button. Opens a file dialog for selecting MS files,
        which are then added to the listMS widget and the model is updated.
        """
        ms_file_paths, _ = QFileDialog.getOpenFileNames(self, "Select MS Files", "", "MzML Files (*.mzML);;All Files (*)")
        if ms_file_paths:
            self.clear_list_ms()
            for ms_file_path in ms_file_paths:
                if ms_file_path.lower().endswith(".mzml") and os.path.isfile(ms_file_path):
                    self.listMS.addItem(ms_file_path)  # Add each MS file path to the listMS widget
                else:
                    self.show_critical_error(f"Invalid file type: {ms_file_path.split('/')[-1]}\nCurrently only .mzML files are supported.")
                    logger.error(f"Invalid file type: {ms_file_path.split('/')[-1]}")
                    return
            self.update_ms_file_list()  # Update the model with the new MS files
            
            # Trigger loading process
            self.progressBar.setVisible(True)
            self.progressLabel.setVisible(True)
            self.controller.model.load(self.controller.mode, "MS")

    def on_browseAnnotations(self):
        """
        Slot for the browseAnnotations button. Opens a file dialog for selecting annotation files,
        which are then added to the listAnnotations widget and the model is updated.
        """
        annotation_file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Annotation Files", "", "Text Files (*.txt);;All Files (*)")
        if annotation_file_paths:
            self.clear_list_annotated_lc()
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

    def on_export(self):
        results = self.controller.model.export()
        if not results.empty:
            file_name, _ = QFileDialog.getSaveFileName(self, "Save Results", "", "CSV Files (*.csv);;All Files (*)")
            if file_name:
                f = open(file_name, 'w')
                f.write(results.to_csv(index=False))
                f.close()
                output_folder = os.path.dirname(file_name)
            try:
                self.statusbar.showMessage(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -- Saved results to output folder {output_folder}", 5000)
            except UnboundLocalError:
                return
        else:
            self.show_critical_error("Error: Nothing to export.")
            logger.error("Error: Nothing to export.")

    def update_lc_file_list(self):
        """
        Updates the model with the LC file paths currently in the listLC widget.

        Iterates over the listLC widget, retrieves the text of each item, and stores
        them in a list. This list is then assigned to the `lc_filelist` attribute of
        the model, which is assumed to be accessed through the `controller` attribute.

        This method is called whenever the contents of the listLC widget change,
        such as when new LC files are added or existing ones are removed.
        """
        lc_files = []
        try:
            self.listLC
        except AttributeError:
            logger.error("listLC is not defined!")
            return
        try:
            lc_files = [self.listLC.item(i).text() for i in range(self.listLC.count())]
        except RuntimeError:
            logger.error("listLC has been deleted!")
        finally:
            self.controller.model.lc_measurements = lc_files 

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
        ms_files = []
        try:
            self.listMS
        except AttributeError:
            logger.error("listMS is not defined!")
            return
        try:
            ms_files = [self.listMS.item(i).text() for i in range(self.listMS.count())]
        except RuntimeError:
            logger.error("listMS has been deleted!")
        finally:
            self.controller.model.ms_measurements = ms_files  

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
        annotation_files = []
        try:
            self.listAnnotations
        except AttributeError:
            logger.warning("listAnnotations is not defined!")
            return
        try:
            annotation_files = [self.listAnnotations.item(i).text() for i in range(self.listAnnotations.count())]
        except RuntimeError:
            logger.error("listAnnotations has been deleted!")
        finally:
            self.controller.model.annotations = annotation_files 

    def update_progress_bar(self, value):
        self.progressBar.setValue(value)
        self.progressLabel.setText(f"{value}%")

    def update_statusbar_with_loaded_file(self, progress, message):
        self.statusbar.showMessage(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -- Loaded file {message} ({progress}%)", 1000)


    def show_critical_error(self, message):
        QtWidgets.QMessageBox.critical(self, "Error", message)

    def update_combo_box(self, filenames):
        self.comboBox_currentfile.clear()
        self.comboBox_currentfile.addItems(filenames)

    def update_table_quantitation(self, concentrations):
        """
        Update the unified results table with file concentrations and setup columns.
        This replaces the old separate tableWidget_files functionality.
        """
        # Store concentrations for later use
        self.file_concentrations = concentrations
        
        # Setup columns and populate data based on current compound selection
        self.update_unified_table_for_compound()
    
    def update_unified_table_for_compound(self):
        """
        Update the unified table based on the currently selected compound.
        """
        if not hasattr(self, 'file_concentrations'):
            return
            
        # Get the currently selected compound
        current_compound = None
        if (hasattr(self.controller, 'model') and 
            hasattr(self.controller.model, 'compounds') and 
            self.controller.model.compounds and
            self.comboBoxChooseCompound.currentIndex() >= 0):
            
            current_compound = self.controller.model.compounds[self.comboBoxChooseCompound.currentIndex()]
            
            # Setup columns for the current compound
            self.unifiedResultsTable.setup_columns(current_compound)
            
            # Get MS measurements if available
            ms_measurements = getattr(self.controller.model, 'ms_measurements', {})
            
            # Populate the table with data for the current compound
            self.unifiedResultsTable.populate_data(self.file_concentrations, ms_measurements, current_compound)
        else:
            # Fallback: just setup basic columns without compound data
            self.unifiedResultsTable.setColumnCount(3)
            self.unifiedResultsTable.setHorizontalHeaderLabels(["File", "Calibration", "Concentration"])
            self.unifiedResultsTable.setRowCount(len(self.file_concentrations))
            
            for row, (filename, concentration) in enumerate(self.file_concentrations):
                # File name
                file_item = QtWidgets.QTableWidgetItem(filename)
                file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.unifiedResultsTable.setItem(row, 0, file_item)
                
                # Calibration checkbox
                checkbox_widget = QtWidgets.QWidget()
                checkbox = QtWidgets.QCheckBox()
                checkbox.setChecked(False)
                layout = QtWidgets.QHBoxLayout(checkbox_widget)
                layout.addWidget(checkbox)
                layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.setContentsMargins(0, 0, 0, 0)
                self.unifiedResultsTable.setCellWidget(row, 1, checkbox_widget)
                
                # Concentration
                conc_item = QtWidgets.QTableWidgetItem(concentration or "")
                self.unifiedResultsTable.setItem(row, 2, conc_item)

    def get_calibration_files(self):
        """
        Get calibration files from the unified results table.
        """
        return self.unifiedResultsTable.get_calibration_files()

    def update_choose_compound(self, compounds):
        self.comboBoxChooseCompound.clear()
        for compound in compounds:
            self.comboBoxChooseCompound.addItem(compound.name)

    def display_plots(self, lc_file, ms_file):
        if self.controller.mode == "LC/GC-MS":
            self.canvas_baseline.clear()
            if lc_file:
                try:
                    plot_absorbance_data(lc_file.path, lc_file.baseline_corrected, self.canvas_baseline)
                    self.canvas_baseline.getPlotItem().addItem(self.crosshair_v, ignoreBounds=True)
                    self.canvas_baseline.getPlotItem().addItem(self.crosshair_h, ignoreBounds=True)
                    self.canvas_baseline.getPlotItem().addItem(self.line_marker, ignoreBounds=True)
                    self.crosshair_v_label = pg.InfLineLabel(self.crosshair_v, text="", color='#b8b8b8', rotateAxis=(1, 0))
                    self.crosshair_h_label = pg.InfLineLabel(self.crosshair_h, text="", color='#b8b8b8', rotateAxis=(1, 0))
                except Exception as e: 
                    logger.error(f"No baseline chromatogram found: {traceback.format_exc()}")
            self.canvas_avgMS.clear()
            if ms_file:
                try:
                    plot_average_ms_data(0, ms_file.data, self.canvas_avgMS)
                except AttributeError as e: 
                    logger.error(f"No average MS found: {traceback.format_exc()}")
            self.canvas_XICs.clear()
            if ms_file:
                self.gridLayout_2.removeWidget(self.scrollArea)
                self.gridLayout_2.addWidget(self.scrollArea, 1, 1, 1, 1)
                try:
                    plot_annotated_XICs(ms_file.path, ms_file.xics, self.canvas_XICs)
                except AttributeError as e: 
                    logger.error(f"No XIC plot found: {traceback.format_exc()}")
            if lc_file and ms_file:
                if lc_file.filename == ms_file.filename:
                    try:
                        self.canvas_annotatedLC.clear()
                        self.curve_list = plot_annotated_LC(lc_file.path, lc_file.baseline_corrected, self.canvas_annotatedLC)
                    except RuntimeError:
                        logger.error(f"Canvas was deleted, reacreating canvas_annotatedLC.")
                        self.canvas_annotatedLC = pg.PlotWidget(parent=self.tabResults)
                        self.canvas_annotatedLC.setObjectName("canvas_annotatedLC")
                        self.canvas_annotatedLC.setMouseEnabled(x=True, y=False)
                        self.gridLayout_2.addWidget(self.canvas_annotatedLC, 0, 1, 1, 1)
                        self.curve_list = plot_annotated_LC(lc_file.path, lc_file.baseline_corrected, self.canvas_annotatedLC)
                    for curve in self.curve_list.keys():
                        curve.sigClicked.connect(lambda c: self.highlight_peak(c, ms_file.xics))                
                    
        elif self.controller.mode == "MS Only":
            try:
                self.canvas_baseline.clear()
                self.canvas_avgMS.clear()
                self.canvas_XICs.clear()
                self.gridLayout_5.removeWidget(self.canvas_annotatedLC)
                self.canvas_annotatedLC.deleteLater()
                # Set scrollArea (holds canvasXIC) to span two rows of the grid
                self.gridLayout_2.removeWidget(self.scrollArea)
                self.gridLayout_2.addWidget(self.scrollArea, 0, 1, 2, 1)
                self.browseAnnotations.deleteLater()
            except RuntimeError as e:
                logger.error(f"Widgets not found: {traceback.format_exc()}")
            if ms_file:
                try:
                    plot_total_ion_current(self.canvas_baseline, ms_file.data, ms_file.filename)
                    self.canvas_baseline.getPlotItem().addItem(self.crosshair_v, ignoreBounds=True)
                    self.canvas_baseline.getPlotItem().addItem(self.crosshair_h, ignoreBounds=True)
                    self.canvas_baseline.getPlotItem().addItem(self.line_marker, ignoreBounds=True)
                    self.crosshair_v_label = pg.InfLineLabel(self.crosshair_v, text="", color='#b8b8b8', rotateAxis=(1, 0))
                    self.crosshair_h_label = pg.InfLineLabel(self.crosshair_h, text="", color='#b8b8b8', rotateAxis=(1, 0))
                    plot_average_ms_data(0, ms_file.data, self.canvas_avgMS)
                    plot_annotated_XICs(ms_file.path, ms_file.xics, self.canvas_XICs)
                except AttributeError as e:
                    logger.error(f"No plot found: {traceback.format_exc()}") 

    def display_calibration_curve(self):
        self.canvas_calibration.clear()
        self.canvas_calibration.getPlotItem().vb.enableAutoRange(axis='y', enable=True)
        self.canvas_calibration.getPlotItem().vb.enableAutoRange(axis='x', enable=True)
        self.canvas_calibration.getPlotItem().vb.setAutoVisible(x=True, y=True)
        for compound in self.controller.model.compounds:
            if compound.name == self.comboBoxChooseCompound.currentText():
                try:
                    plot_calibration_curve(compound, self.canvas_calibration)
                except TypeError as e: 
                    logger.error(f"No calibration curve found for {compound.name}: {traceback.format_exc()}")

    def display_concentrations(self):
        """
        This method is now handled by the unified results table.
        The concentration display is automatically updated when the table is populated.
        """
        # The unified table automatically shows concentrations and ion intensities
        # No separate method needed as this is handled in update_table_quantitation
        pass

    def display_library_ms2(self):
        try:
            library_entries = self.controller.model.find_ms2_precursors()
        except Exception as e:
            logger.error(f"Error finding MS2 precursors: {e}")
        self.canvas_library_ms2.clear()
        self.canvas_library_ms2.setBackground("w")
        # Plot the library entry which is currently selected in comboBoxChooseMS2File
        try:
            library_entry = library_entries[self.comboBoxChooseMS2File.currentText()]
            plot_library_ms2(library_entry, self.canvas_library_ms2)
            self.comboBoxChooseMS2File.currentIndexChanged.connect(lambda: plot_library_ms2(library_entries[self.comboBoxChooseMS2File.currentText()], self.canvas_library_ms2))
        except IndexError:
            logger.error(f"No MS2 found for {self.comboBoxChooseMS2File.currentText()}")
            plot_no_ms2_found(self.canvas_library_ms2)
        except KeyError:
            logger.error(f"No MS2 found for {self.comboBoxChooseMS2File.currentText()}")


    def display_ms2(self):
        """
        Display MS2 data for the selected file in the unified results table.
        """
        selected_file = self.unifiedResultsTable.get_selected_file()
        if not selected_file:
            logger.error("No file selected for MS2 display")
            plot_no_ms2_found(self.canvas_ms2)
            return
            
        ms_file = self.controller.model.ms_measurements.get(selected_file)
        if ms_file is None:
            logger.error(f"No MS file found for {selected_file}")
            plot_no_ms2_found(self.canvas_ms2)
            return
            
        try:
            self.controller.model.find_ms2_in_file(ms_file)
            compound = next((xic for xic in ms_file.xics if xic.name == self.comboBoxChooseCompound.currentText()), None)
            precursor = float(self.comboBoxChooseMS2File.currentText().split("m/z ")[1].replace('(', '').replace(')', ''))
            plot_ms2_from_file(ms_file, compound, precursor, self.canvas_ms2)
        except Exception as e:
            logger.error(f"No MS2 found for {self.comboBoxChooseMS2File.currentText()} in {ms_file.filename}: {traceback.format_exc()}")
            plot_no_ms2_found(self.canvas_ms2)
    

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
                    text_item = pg.TextItem(text=f"{compound.name} ({ion})", color='#242526', anchor=(0, 0))
                    text_item.setFont(pg.QtGui.QFont('Helvetica', 10, weight=pg.QtGui.QFont.Weight.ExtraLight))
                    text_items.append(text_item)
                    self.canvas_annotatedLC.addItem(text_item)
        selected_curve.setBrush(pg.mkBrush('#ee6677'))
        selected_curve.setPen(pg.mkPen('#ee6677'))
        positions = np.linspace(np.max(selected_curve.getData()[1])/2, np.max(selected_curve.getData()[1])+400, 20)
        for i, text_item in enumerate(text_items):
            text_item.setPos(float(np.median(selected_curve.getData()[0]+i//20)), float(positions[i%len(positions)]))

    def update_labels_avgMS(self, canvas):
        # Remove all the previous labels
        for item in canvas.items():
            if isinstance(item, pg.TextItem):
                canvas.removeItem(item)
        try:
            data = canvas.getPlotItem().listDataItems()[0].getData()
        except IndexError as e:
            logger.error(f"Error getting data items for MS viewing. {traceback.format_exc()}")
            return
        current_view_range = canvas.getViewBox().viewRange()
        # Get the intensity range within the current view range
        mz_range = data[0][np.logical_and(data[0] >= current_view_range[0][0], data[0] <= current_view_range[0][1])]
        indices = [i for i, x in enumerate(data[0]) if x in mz_range]
        intensity_range = data[1][indices]
        peaks, _ = find_peaks(intensity_range, prominence=10)
        if len(peaks) < 5: 
            peaks, _ = find_peaks(intensity_range)
        # Get the 10 highest peaks within the current view range
        sorted_indices= np.argsort(intensity_range[peaks])[::-1]
        # Get their mz values
        mzs = mz_range[peaks][sorted_indices][0:10]
        intensities = intensity_range[peaks][sorted_indices][0:10]
        for mz, intensity in zip(mzs, intensities):
            text_item = pg.TextItem(text=f"{mz:.4f}", color='#242526', anchor=(0, 0))
            text_item.setFont(pg.QtGui.QFont('Helvetica', 10, weight=pg.QtGui.QFont.Weight.Normal))
            text_item.setPos(mz, intensity)
            canvas.addItem(text_item)

    def update_crosshair(self, e):
        """
        Event handler for when the user moves the mouse over the canvas_baseline widget.
        Updates the position of the vertical and horizontal crosshairs and their labels with the current time (in minutes) and intensity (in a.u.), respectively.
        """
        try:
            self.crosshair_v_label
        except AttributeError:
            return
        pos = e[0]
        if self.canvas_baseline.sceneBoundingRect().contains(pos):
            mousePoint = self.canvas_baseline.getPlotItem().getViewBox().mapSceneToView(pos)
            self.crosshair_v.setPos(mousePoint.x())
            self.crosshair_h.setPos(mousePoint.y())
            self.crosshair_v_label.setText(f"{mousePoint.x():.2f} min")
            self.crosshair_h_label.setText(f"{mousePoint.y():.0f} a.u.")
            
    def update_line_marker(self, event):
        # Update the position of the vertical line marker every time the user clicks on the canvas
        mouse_pos = self.canvas_baseline.getPlotItem().getViewBox().mapSceneToView(event._scenePos)
        self.line_marker.setVisible(True)
        self.line_marker.setPos(mouse_pos.x())

    def update_line_marker_with_key(self, event):
        # Update the position of the vertical line marker every time the user presses either the left or right arrow keys
        self.line_marker.setVisible(True)
        # Change the position by one scan to the left or right
        if event.key() == QtCore.Qt.Key.Key_Left:
            self.line_marker.setPos(self.line_marker.pos() - 0.01)
        elif event.key() == QtCore.Qt.Key.Key_Right:
            self.line_marker.setPos(self.line_marker.pos() + 0.01)

    def clear_list_lc(self):
        self.listLC.clear()
        self.controller.model.lc_measurements = []

    def clear_list_ms(self):
        self.listMS.clear()
        self.controller.model.ms_measurements = []

    def clear_list_annotated_lc(self):
        self.listAnnotatedLC.clear()
        self.controller.model.annotations = []

    def change_mode(self):
        """
        Update the layout of the Upload tab based on the current selection in the combo box.

        When the selection changes, this function will clear the layout of the Upload tab and
        recreate the widgets appropriate for the new selection. The list of MS files is updated
        and the model is updated with the new list of MS files.

        This function does not return anything.

        :param self: The View instance.
        """
        def clear_layout(layout):
            if layout:
                for i in reversed(range(layout.count())):
                    widget = layout.itemAt(i).widget()
                    print(widget)
                    if widget is not None and isinstance(widget, DragDropListWidget):
                        widget.clear()
                        widget.deleteLater()

        if self.comboBox.currentText() == "LC/GC-MS":
            print('switched to LC/GC-MS mode')
            clear_layout(self.gridLayout)
            self.labelAnnotations.setVisible(False)
            self.browseAnnotations.setVisible(False)
            # Replace with LC/GC-MS widgets 
            self.listLC = DragDropListWidget(parent=self.tabUpload)
            self.listLC.setMinimumWidth(500)
            self.gridLayout.addWidget(self.listLC, 2, 0, 1, 2)
            self.labelLCdata.setVisible(True)
            self.browseLC.setVisible(True)
            self.listMS = DragDropListWidget(parent=self.tabUpload)
            self.listMS.setMinimumWidth(500)
            self.gridLayout.addWidget(self.listMS, 2, 2, 1, 2)
            self.labelMSdata.setVisible(True)
            self.browseMS.setVisible(True)
            self.controller.mode = "LC/GC-MS"
            self.listLC.filesDropped.connect(self.handle_files_dropped_LC)
            self.listMS.filesDropped.connect(self.handle_files_dropped_MS)
            self.button_clear_LC.clicked.connect(self.listLC.clear)
            self.button_clear_MS.clicked.connect(self.listMS.clear)
            self.update_ms_file_list()
            self.update_lc_file_list()

        elif self.comboBox.currentText() == "MS Only":
            print('switched to MS Only')
            clear_layout(self.gridLayout)
            self.labelLCdata.setVisible(False)
            self.labelAnnotations.setVisible(False)
            self.labelMSdata.setVisible(True)
            self.browseLC.setVisible(False)
            self.listMS = DragDropListWidget(parent=self.tabUpload)
            self.listMS.setMinimumWidth(1000)
            self.gridLayout.addWidget(self.listMS, 2, 0, 1, 4)
            self.button_clear_LC.setVisible(False)
            self.controller.mode = "MS Only"
            self.listMS.filesDropped.connect(self.handle_files_dropped_MS)
            self.button_clear_MS.clicked.connect(self.listMS.clear)
            self.update_ms_file_list()

        else:
            print('switched to LC Only')
            clear_layout(self.gridLayout)
            # Remove MS widgets
            self.labelMSdata.setVisible(False)
            self.browseMS.setVisible(False)
            # Recreate the LC widgets
            self.listLC = DragDropListWidget(parent=self.tabUpload)
            self.listLC.setMinimumWidth(500)
            self.gridLayout.addWidget(self.listLC, 2, 0, 1, 2)
            # Replace with annotations
            self.listAnnotations = DragDropListWidget(parent=self.tabUpload)
            self.listAnnotations.setMinimumWidth(500)
            self.gridLayout.addWidget(self.listAnnotations, 2, 2, 1, 2)
            self.labelAnnotations.setVisible(True)
            self.browseAnnotations.setVisible(True)
            self.labelLCdata.setVisible(True)
            self.browseLC.setVisible(True)
            self.controller.mode = "LC/GC Only"
            self.listLC.filesDropped.connect(self.handle_files_dropped_LC)
            self.listAnnotations.filesDropped.connect(self.handle_files_dropped_annotations)
            self.update_lc_file_list()
            self.update_annotation_file()

    def show_scan_at_time_x(self, event):
        time_x = float(self.line_marker.pos().x())
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
        MainWindow.setToolTip("")
        MainWindow.setToolTipDuration(-1)
        MainWindow.setTabShape(QtWidgets.QTabWidget.TabShape.Rounded)
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.centralwidget.setMinimumSize(QtCore.QSize(1500, 720))
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
        self.gridLayout = QtWidgets.QGridLayout(self.tabUpload)
        self.gridLayout.setObjectName("gridLayout")
        self.comboBoxIonLists = QtWidgets.QComboBox(parent=self.tabUpload)
        self.comboBoxIonLists.setObjectName("comboBoxIonLists")
        self.comboBoxIonLists.addItem("Create new ion list...")
        try: 
            config_path = Path(__file__).parent.parent / "config.json"
            with open(config_path, "r") as f:
                lists = json.load(f)
            for ionlist in lists:
                self.comboBoxIonLists.addItem(ionlist)
        except Exception as e:
            logger.error(f"Error loading ion lists: {e}")
        self.gridLayout.addWidget(self.comboBoxIonLists, 1, 4, 1, 2)
        self.ionTable = IonTable(view=self, parent=self.tabUpload)
        self.gridLayout.addWidget(self.ionTable, 2, 4, 1, 3)

        self.browseLC = QtWidgets.QPushButton(parent=self.tabUpload)
        self.browseLC.setObjectName("browseLC")
        self.gridLayout.addWidget(self.browseLC, 1, 1, 1, 1)
        self.comboBox = QtWidgets.QComboBox(parent=self.tabUpload)
        self.comboBox.setObjectName("comboBox")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.gridLayout.addWidget(self.comboBox, 0, 0, 1, 2)
        self.browseMS = QtWidgets.QPushButton(parent=self.tabUpload)
        self.browseMS.setObjectName("browseMS")
        self.browseAnnotations = QtWidgets.QPushButton(parent=self.tabUpload)
        self.browseAnnotations.setObjectName("browseAnnotations")
        self.gridLayout.addWidget(self.browseAnnotations, 1, 3, 1, 1)
        self.browseAnnotations.setVisible(False)
        self.gridLayout.addWidget(self.browseMS, 1, 3, 1, 1)
        self.labelLCdata = QtWidgets.QLabel(parent=self.tabUpload)
        self.labelLCdata.setObjectName("labelLCdata")
        self.gridLayout.addWidget(self.labelLCdata, 1, 0, 1, 1)
        self.labelMSdata = QtWidgets.QLabel(parent=self.tabUpload)
        self.labelMSdata.setObjectName("labelMSdata")
        self.labelAnnotations = QtWidgets.QLabel(parent=self.tabUpload)
        self.labelAnnotations.setObjectName("labelAnnotations")
        self.gridLayout.addWidget(self.labelAnnotations, 1, 2, 1, 1)
        self.labelAnnotations.setVisible(False)
        self.gridLayout.addWidget(self.labelMSdata, 1, 2, 1, 1)
        self.listLC = DragDropListWidget(parent=self.tabUpload)
        self.listLC.setObjectName("listLC")
        self.listLC.setMinimumWidth(500)
        self.gridLayout.addWidget(self.listLC, 2, 0, 1, 2)
        self.listMS = DragDropListWidget(parent=self.tabUpload)
        self.listMS.setObjectName("listMS")
        self.listMS.setMinimumWidth(500)
        self.gridLayout.addWidget(self.listMS, 2, 2, 1, 2)
        self.labelIonList = QtWidgets.QLabel(parent=self.tabUpload)
        self.labelIonList.setObjectName("labelIonList")
        self.gridLayout.addWidget(self.labelIonList, 0, 4, 1, 1)
        self.button_clear_LC = QtWidgets.QPushButton(parent=self.tabUpload)
        self.button_clear_LC.setObjectName("button_clear_LC")
        self.gridLayout.addWidget(self.button_clear_LC, 3, 0, 1, 1)
        self.button_clear_MS = QtWidgets.QPushButton(parent=self.tabUpload)
        self.button_clear_MS.setObjectName("button_clear_MS")
        self.gridLayout.addWidget(self.button_clear_MS, 3, 2, 1, 1)
        self.button_clear_ion_list = QtWidgets.QPushButton(parent=self.tabUpload)
        self.button_clear_ion_list.setObjectName("button_clear_ion_list")
        self.gridLayout.addWidget(self.button_clear_ion_list, 3, 4, 1, 1)
        self.button_save_ion_list = QtWidgets.QPushButton(parent=self.tabUpload)
        self.button_save_ion_list.setObjectName("button_save_ion_list")
        self.gridLayout.addWidget(self.button_save_ion_list, 3, 5, 1, 1)
        self.button_delete_ion_list = QtWidgets.QPushButton(parent=self.tabUpload)
        self.button_delete_ion_list.setObjectName("button_delete_ion_list")
        self.gridLayout.addWidget(self.button_delete_ion_list, 3, 6, 1, 1)
        
        self.processButton = QtWidgets.QPushButton(parent=self.tabUpload)
        self.processButton.setObjectName("processButton")
        self.processButton.setDefault(True)
        self.processButton.setEnabled(False)
        self.gridLayout.addWidget(self.processButton, 4, 2, 1, 2)
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
        self.canvas_baseline = ChromatogramPlotWidget(parent=self.tabResults)
        self.canvas_baseline.setObjectName("canvas_baseline")
        self.canvas_baseline.scene().sigMouseClicked.connect(self.show_scan_at_time_x)
        self.canvas_baseline.scene().sigMouseClicked.connect(self.update_line_marker)
        self.canvas_baseline.scene().sigMouseClicked.connect(lambda ev: self.update_labels_avgMS(self.canvas_avgMS))
        self.canvas_baseline.sigKeyPressed.connect(self.update_line_marker_with_key)
        self.canvas_baseline.sigKeyPressed.connect(self.show_scan_at_time_x)
        self.canvas_baseline.sigKeyPressed.connect(lambda ev: self.update_labels_avgMS(self.canvas_avgMS))
        self.crosshair_v = pg.InfiniteLine(angle=90, pen=pg.mkPen(color="#b8b8b8", width=1, style=QtCore.Qt.PenStyle.DashLine), movable=False)
        self.crosshair_h = pg.InfiniteLine(angle=0, pen=pg.mkPen(color="#b8b8b8", style=QtCore.Qt.PenStyle.DashLine, width=1), movable=False)
        self.line_marker = pg.InfiniteLine(angle=90, pen=pg.mkPen(color="#000000", style=QtCore.Qt.PenStyle.SolidLine, width=1), movable=True)

        self.proxy = pg.SignalProxy(self.canvas_baseline.scene().sigMouseMoved, rateLimit=60, slot=self.update_crosshair)
        self.canvas_baseline.setCursor(Qt.CursorShape.CrossCursor)

        self.gridLayout_2.addWidget(self.canvas_baseline, 0, 0, 1, 1)
        self.canvas_avgMS = pg.PlotWidget(parent=self.tabResults)
        self.canvas_avgMS.setObjectName("canvas_avgMS")
        self.canvas_avgMS.setMouseEnabled(x=True, y=False)
        self.canvas_avgMS.getPlotItem().getViewBox().enableAutoRange(axis='y')
        self.canvas_avgMS.getPlotItem().getViewBox().setAutoVisible(y=True)
        self.canvas_avgMS.getPlotItem().getViewBox().sigRangeChangedManually.connect(lambda ev: self.update_labels_avgMS(self.canvas_avgMS))

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
        self.gridLayout_quant.setColumnStretch(0, 1)
        self.gridLayout_quant.setColumnStretch(1, 1)
        self.gridLayout_quant.setRowStretch(0, 1)
        self.gridLayout_quant.setRowStretch(1, 1)
        self.gridLayout_quant.setRowStretch(2, 1)
        self.gridLayout_quant.setRowStretch(3, 1)
        self.gridLayout_top_left = QtWidgets.QGridLayout()
        self.gridLayout_top_left.setObjectName("gridLayout_top_left")
        self.label_calibrate = QtWidgets.QLabel(parent=self.tabQuantitation)
        self.label_calibrate.setWordWrap(True)
        self.label_calibrate.setObjectName("label_calibrate")
        # Set size policy to prevent unnecessary expansion
        self.label_calibrate.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        self.gridLayout_top_left.addWidget(self.label_calibrate, 0, 0, 1, 1)
        self.calibrateButton = QtWidgets.QPushButton(parent=self.tabQuantitation)
        self.calibrateButton.setObjectName("calibrateButton")
        # Set size policy for the button to prevent expansion
        self.calibrateButton.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        self.gridLayout_top_left.addWidget(self.calibrateButton, 0, 1, 1, 1)
        self.gridLayout_quant.addLayout(self.gridLayout_top_left, 0, 0, 4, 1)
        self.unifiedResultsTable = UnifiedResultsTable(parent=self.tabQuantitation)
        self.unifiedResultsTable.setObjectName("unifiedResultsTable")
        self.gridLayout_top_left.addWidget(self.unifiedResultsTable, 1, 0, 3, 2)
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
        self.label_compound.setSizePolicy(sizePolicy)
        self.label_compound.setObjectName("label_compound")
        self.gridLayout_top_right.addWidget(self.label_compound, 0, 0, 1, 1)
        self.comboBoxChooseCompound = QtWidgets.QComboBox(parent=self.tabQuantitation)
        self.comboBoxChooseCompound.setMinimumSize(QtCore.QSize(0, 32))
        self.comboBoxChooseCompound.setObjectName("comboBoxChooseCompound")
        self.comboBoxChooseCompound.setEnabled(False)
        self.gridLayout_top_right.addWidget(self.comboBoxChooseCompound, 0, 1, 1, 1)
        self.canvas_calibration = pg.PlotWidget()
        self.canvas_calibration.setObjectName("canvas_calibration")
        self.gridLayout_top_right.addWidget(self.canvas_calibration, 1, 0, 1, 2)
        self.gridLayout_quant.addLayout(self.gridLayout_top_right, 0, 1, 1, 1)
        self.canvas_ms2 = pg.PlotWidget(parent=self.tabQuantitation)
        self.canvas_ms2.setObjectName("canvas_ms2")
        self.canvas_ms2.setMouseEnabled(x=True, y=False)
        self.canvas_ms2.getPlotItem().getViewBox().enableAutoRange(axis='y')
        self.canvas_ms2.getPlotItem().getViewBox().setAutoVisible(y=True)
        self.canvas_ms2.getPlotItem().getViewBox().sigRangeChangedManually.connect(lambda ev: self.update_labels_avgMS(self.canvas_ms2))

        self.gridLayout_quant.addWidget(self.canvas_ms2, 2, 1, 1, 1)
        self.comboBoxChooseMS2File = QtWidgets.QComboBox(parent=self.tabQuantitation) 
        self.comboBoxChooseMS2File.setObjectName("comboBoxChooseMS2File")
        self.gridLayout_quant.addWidget(self.comboBoxChooseMS2File, 1, 1, 1, 1)  # Above canvas_ms2
        self.canvas_library_ms2 = pg.PlotWidget(parent=self.tabQuantitation)
        self.canvas_library_ms2.setObjectName("canvas_library_ms2")
        self.canvas_library_ms2.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)
        self.canvas_library_ms2.setMouseEnabled(x=True, y=False)
        self.canvas_library_ms2.getPlotItem().getViewBox().enableAutoRange(axis='y')
        self.canvas_library_ms2.getPlotItem().getViewBox().setAutoVisible(y=True)
        self.canvas_library_ms2.getPlotItem().getViewBox().sigRangeChangedManually.connect(lambda ev: self.update_labels_avgMS(self.canvas_library_ms2))
        self.gridLayout_quant.addWidget(self.canvas_library_ms2, 3, 1, 1, 1)  
        self.gridLayout_6.addLayout(self.gridLayout_quant, 0, 0, 1, 1)
        self.tabWidget.addTab(self.tabQuantitation, "")
        self.tabWidget.setTabEnabled(self.tabWidget.indexOf(self.tabQuantitation), False)  # Disable the second tab

        self.gridLayout_4.addWidget(self.tabWidget, 2, 0, 1, 1)
        self.logo = QtWidgets.QLabel(parent=self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        self.logo.setSizePolicy(sizePolicy)
        self.logo.setMaximumSize(QtCore.QSize(1200, 100))
        self.logo.setText("")
        self.logo.setPixmap(QtGui.QPixmap(os.path.join(os.path.dirname(__file__), "logo.png")))
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
        self.actionExport = QtGui.QAction(parent=MainWindow)
        self.actionExport.setObjectName("actionExport")
        self.actionExport.setEnabled(False)
        self.actionOpen = QtGui.QAction(parent=MainWindow)
        self.actionOpen.setObjectName("actionOpen")
        self.actionAbout = QtGui.QAction(parent=MainWindow)
        self.actionAbout.setObjectName("actionAbout")
        self.menuFile.addAction(self.actionOpen)
        self.menuFile.addAction(self.actionSave)
        self.menuFile.addAction(self.actionExport)
        self.menuFile.addAction(self.actionExit)
        self.menuEdit.addAction(self.actionPreferences)
        self.menuHelp.addAction(self.actionReadme)
        self.menuHelp.addAction(self.actionAbout)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuEdit.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        # Connect signals
        #TODO: Implement the rest of the menu items
        #self.actionSave.triggered.connect(self.on_save)
        self.actionExit.triggered.connect(self.on_exit)
        self.actionExport.triggered.connect(self.on_export)
        #self.actionPreferences.triggered.connect(self.on_preferences)
        #self.actionReadme.triggered.connect(self.on_readme)
        self.browseLC.clicked.connect(self.on_browseLC)
        self.browseMS.clicked.connect(self.on_browseMS)
        self.browseAnnotations.clicked.connect(self.on_browseAnnotations)
        # self.processButton.clicked.connect(self.on_process)
        self.listLC.filesDropped.connect(self.handle_files_dropped_LC)
        self.listMS.filesDropped.connect(self.handle_files_dropped_MS)
        self.comboBox.currentIndexChanged.connect(self.change_mode)
        self.comboBoxIonLists.currentIndexChanged.connect(self.update_ion_list)
        self.button_clear_LC.clicked.connect(self.listLC.clear)
        self.button_clear_MS.clicked.connect(self.listMS.clear)
        self.button_clear_ion_list.clicked.connect(self.ionTable.clear)
        self.button_save_ion_list.clicked.connect(self.ionTable.save_ion_list)
        self.button_delete_ion_list.clicked.connect(self.ionTable.delete_ion_list)
        # Connect compound selection change to update the unified table
        self.comboBoxChooseCompound.currentIndexChanged.connect(self.update_unified_table_for_compound)
        # Connect unified table selection change to display MS2 data
        self.unifiedResultsTable.selectionModel().selectionChanged.connect(self.display_ms2)


    def retranslateUi(self, MainWindow):
        """
        Set the text of the UI elements according to the current locale.
        
        Parameters
        ----------
            MainWindow: The main window object for which the UI is being set up.
        """
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "LCMSpector"))
        MainWindow.setWindowIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__), "resources", "icon.icns")))
        self.browseLC.setText(_translate("MainWindow", "Browse"))
        self.comboBox.setItemText(0, _translate("MainWindow", "LC/GC-MS"))
        self.comboBox.setItemText(1, _translate("MainWindow", "MS Only"))
        self.comboBox.setItemText(2, _translate("MainWindow", "LC/GC Only"))
        self.browseMS.setText(_translate("MainWindow", "Browse"))
        self.browseAnnotations.setText(_translate("MainWindow", "Browse"))
        self.labelAnnotations.setText(_translate("MainWindow", "Annotations (.txt)"))
        self.labelLCdata.setText(_translate("MainWindow", "Chromatography data (.txt)"))
        self.labelMSdata.setText(_translate("MainWindow", "MS data (.mzML)"))
        self.labelIonList.setText(_translate("MainWindow", "Targeted m/z values:"))
        self.comboBoxIonLists.setToolTip(_translate("MainWindow", "Choose an ion list from the list of ion lists provided with the software"))
        self.processButton.setText(_translate("MainWindow", "Process"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabUpload), _translate("MainWindow", "Upload"))
        self.label_results_currentfile.setText(_translate("MainWindow", "Current file:"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabResults), _translate("MainWindow", "Results"))
        self.label_curr_compound.setText(_translate("MainWindow", "Compound:"))
        self.label_calibrate.setText(_translate("MainWindow", "Select the files to be used for calibration."))
        self.calibrateButton.setText(_translate("MainWindow", "Calculate"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabQuantitation), _translate("MainWindow", "Quantitation"))
        self.menuFile.setTitle(_translate("MainWindow", "File"))
        self.actionFile.setText(_translate("MainWindow", "File"))
        self.menuEdit.setTitle(_translate("MainWindow", "Edit"))
        self.menuHelp.setTitle(_translate("MainWindow", "Help"))
        self.actionSave.setText(_translate("MainWindow", "Save"))
        self.actionSave.setShortcut(_translate("MainWindow", "Ctrl+S"))
        self.actionExit.setText(_translate("MainWindow", "Exit"))
        self.actionExit.setShortcut(_translate("MainWindow", "Ctrl+W"))
        self.actionExport.setText(_translate("MainWindow", "Export"))
        self.actionExport.setShortcut(_translate("MainWindow", "Ctrl+E"))
        self.actionAbout.setText(_translate("MainWindow", "About"))
        self.actionAbout.setShortcut(_translate("MainWindow", "F1"))
        self.actionPreferences.setText(_translate("MainWindow", "Preferences"))
        self.actionReadme.setText(_translate("MainWindow", "Readme"))
        self.actionReadme.setShortcut(_translate("MainWindow", "F10"))
        self.actionOpen.setText(_translate("MainWindow", "Open"))
        self.actionOpen.setShortcut(_translate("MainWindow", "Ctrl+O"))
        self.button_clear_LC.setText(_translate("MainWindow", "Clear"))
        self.button_clear_MS.setText(_translate("MainWindow", "Clear"))
        self.button_clear_ion_list.setText(_translate("MainWindow", "Clear"))
        self.button_save_ion_list.setText(_translate("MainWindow", "Save"))
        self.button_delete_ion_list.setText(_translate("MainWindow", "Delete"))
        
        self.resize(1500, 900)
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
