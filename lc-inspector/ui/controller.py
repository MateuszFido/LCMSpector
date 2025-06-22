from calculation.workers import Worker, WorkerSignals
from utils.classes import LCMeasurement, MSMeasurement
from PyQt6.QtCore import pyqtSlot
import logging, traceback, threading, os
logger = logging.getLogger(__name__)
from datetime import datetime

class Controller:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.view.controller = self
        self.model.controller = self
        self.view.processButton.clicked.connect(self.process_data)
        self.view.comboBox_currentfile.currentIndexChanged.connect(self.display_selected_plots)
        self.view.calibrateButton.clicked.connect(self.calibrate)
        self.view.calibrateButton.clicked.connect(self.find_ms2_precursors)
        self.view.comboBoxChooseCompound.currentIndexChanged.connect(self.view.display_calibration_curve)
        self.view.comboBoxChooseCompound.currentIndexChanged.connect(self.view.display_concentrations)
        self.view.comboBoxChooseCompound.currentIndexChanged.connect(self.view.display_ms2)
        self.mode = "LC/GC-MS"
        logger.info("Controller initialized.")
        logger.info(f"Current thread: {threading.current_thread().name}")
        logger.info(f"Current process: {os.getpid()}")

    def load_lc_data(self):
        pass

    def load_ms_data(self):
        pass
    
    def process_data(self):
        self.view.update_lc_file_list()
        self.view.update_ms_file_list()
        self.view.update_annotation_file()
        self.view.statusbar.showMessage(f"Processing data in {self.mode} mode ...")
        self.model.compounds = self.view.ionTable.get_items()
        if not self.model.compounds:
            self.view.show_critical_error("No compounds found!\n\nPlease define m/z values to trace or choose from the predefined lists before processing.")
            return
        if (hasattr(self.model, 'ms_measurements') and hasattr(self.model, 'lc_measurements')) or (hasattr(self.model, 'lc_measurements') and hasattr(self.model, 'annotations')):
            if self.mode == "LC/GC-MS" and not self.model.lc_measurements:
                self.view.show_critical_error("No files to process!\n\nPlease load LC files and either corresponding MS files or manual annotations before processing.")
                return
            elif self.mode == "LC/GC Only" and not self.model.lc_measurements:
                self.view.show_critical_error("No files to process!\n\nPlease load LC files before processing.")
                return
            elif self.mode == "MS Only" and not self.model.ms_measurements:
                self.view.show_critical_error("No files to process!\n\nPlease load MS files before processing.")
                return
            if not self.model.compounds or not self.model.compounds[0].ions:
                self.view.show_critical_error("Please define m/z values to trace or choose from the predefined lists before processing.")
                return
            
            logger.info("Starting the processing...")
            # Handle pre-processing UI events
            self.view.processButton.setEnabled(False)
            self.view.progressBar.setVisible(True)
            self.view.progressLabel.setVisible(True)
            self.view.progressLabel.setText("0%")
            self.view.progressBar.setValue(0)
            # Start processing
            try:
                self.model.process(mode=self.mode)
            except Exception:
                logger.error(f"Error processing data: {traceback.format_exc()}")
                self.view.show_critical_error(f"Error processing data: {traceback.format_exc()}")
                return
        else:
            self.view.show_critical_error("Nothing to process. Please load LC files and either corresponding MS files or manual annotations before proceeding.")
            logger.error("Nothing to process. Please load LC files and either corresponding MS files or manual annotations before proceeding.")

    def on_processing_finished(self, lc_results, ms_results):
        self.model.lc_measurements = lc_results
        self.model.ms_measurements = ms_results
        self.view.progressBar.setVisible(False)
        self.view.progressLabel.setVisible(False)
        self.view.processButton.setEnabled(True)
        self.view.statusbar.showMessage(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -- Finished processing, displaying results.", 5000)

        self.view.tabWidget.setTabEnabled(self.view.tabWidget.indexOf(self.view.tabResults), True)
        self.view.tabWidget.setCurrentIndex(self.view.tabWidget.indexOf(self.view.tabResults))
        self.view.tabWidget.setTabEnabled(self.view.tabWidget.indexOf(self.view.tabQuantitation), True)

        # Resize view to fit the screen
        self.update_filenames()
        self.view.actionExport.setEnabled(True)

    
    def update_filenames(self):
        if self.mode == "LC/GC-MS" or self.mode == "LC/GC Only":
            filenames = list(self.model.lc_measurements.keys())
            # Grab the return values of extract_concentration() for every file in lc_measurements
            concentrations = [[file, self.model.lc_measurements[file].extract_concentration()] for file in filenames]
            self.view.update_combo_box(filenames)
            self.view.update_table_quantitation(concentrations)
        else:
            filenames = list(self.model.ms_measurements.keys())
            concentrations = [[file, self.model.ms_measurements[file].extract_concentration()] for file in filenames]
            self.view.update_combo_box(filenames)
            self.view.update_table_quantitation(concentrations)
            
    def display_selected_plots(self):
        selected_file = self.view.comboBox_currentfile.currentText()
        try:
            lc_file, ms_file = self.model.get_plots(selected_file)
        except Exception:
            logger.error(f"Error getting plots for file {selected_file}: {traceback.format_exc()}")
        self.view.display_plots(lc_file, ms_file)  # Update the view with the selected plots
        
    def calibrate(self):
        """
        Calibrates the concentrations of the selected MS files using the selected files with annotated concentrations.
        :return: None
        """
        try: 
            self.model.find_ms2_precursors()
        except Exception:
            logger.error(f"Error finding MS2 precursors: {traceback.format_exc()}")
            return
        selected_files = self.view.get_calibration_files()
        if selected_files:
            try:
                self.model.calibrate(selected_files)
            except Exception:
                logger.error(f"Error calibrating files: {traceback.format_exc()}")
                return
        else:
            logger.error("No files selected for calibration.")
        self.view.comboBoxChooseCompound.setEnabled(True)
        self.view.update_choose_compound(self.model.compounds)

    def find_ms2_precursors(self):
        """
        Finds the MS2 precursors in the library for the currently selected files with annotated concentrations.
        :return: None
        """
        try:
            self.model.find_ms2_precursors()
        except Exception:
            logger.error(f"Error finding MS2 precursors: {traceback.format_exc()}")
            return