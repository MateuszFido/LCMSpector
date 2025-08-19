"""
Controller module for LC-Inspector application.

This module manages the interaction between the model and view components,
handling data processing, loading, and UI interactions.
"""
import os
import logging
import threading
import traceback
from datetime import datetime

from PySide6.QtCore import Signal
from utils.classes import LCMeasurement, MSMeasurement

logger = logging.getLogger(__name__)
logger.propagate = False

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
        self.view.comboBoxChooseCompound.currentIndexChanged.connect(self.view.display_library_ms2)
        self.mode = "LC/GC-MS"
        logger.info("Controller initialized.")
        logger.info("Current thread: %s", threading.current_thread().name)
        logger.info("Current process: %d", os.getpid())

    def load_lc_data(self):
        pass

    def load_ms_data(self):
        pass
    
    def process_data(self):
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

    def on_processing_finished(self, compound_results):
        # iterate over the compound results and match them with their respective MS file
        for compound_result in compound_results:
            self.model.ms_measurements[compound_result[0].file].xics = compound_result
            print(compound_result, type(compound_result))

        self.view.progressBar.setVisible(False)
        self.view.progressLabel.setVisible(False)
        self.view.processButton.setEnabled(True)
        self.view.statusbar.showMessage(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -- Finished processing, displaying results.", 5000)

        self.view.tabWidget.setTabEnabled(self.view.tabWidget.indexOf(self.view.tabResults), True)
        self.view.tabWidget.setCurrentIndex(self.view.tabWidget.indexOf(self.view.tabResults))
        self.view.tabWidget.setTabEnabled(self.view.tabWidget.indexOf(self.view.tabQuantitation), True)

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
        """
        Display plots for the currently selected file.
        """
        selected_file = self.view.comboBox_currentfile.currentText()
        try:
            lc_file, ms_file = self.model.get_plots(selected_file)
            self.view.display_plots(lc_file, ms_file)
        except Exception as e:
            logger.error("Error getting plots for file %s: %s", selected_file, str(e))

        
    def calibrate(self):
        """
        Calibrates the concentrations of the selected MS files using the selected files with annotated concentrations.
        :return: None
        """
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
            self.view.statusbar.showMessage("Looking for MS2 precursors...", 5000)
            self.model.find_ms2_precursors()
        except Exception:
            logger.error("Error finding MS2 precursors: %s", traceback.format_exc())
            return

    def on_worker_error(self, error_message):
        """
        Handles errors from loading and processing workers.
        
        :param error_message: Error message from the worker
        """
        logger.error(f"Worker error: {error_message}")
        
        # Reset UI elements
        self.view.progressBar.setVisible(False)
        self.view.progressLabel.setVisible(False)
        self.view.processButton.setEnabled(False)
        self.view.statusbar.showMessage(f"Error: {error_message}", 5000)

    def on_loading_finished(self, lc_results, ms_results):
        # Safeguard to only update what was just loaded
        if lc_results:
            self.model.lc_measurements = lc_results
        if ms_results:
            self.model.ms_measurements = ms_results

        self.view.progressBar.setVisible(False)
        self.view.progressLabel.setVisible(False)
        self.view.processButton.setEnabled(True)
        if len(lc_results) == 0 and len(ms_results) == 0:
            self.view.statusbar.showMessage(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -- No files loaded.", 5000)
            return
        elif len(lc_results) == 0:
            self.view.statusbar.showMessage(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -- Finished loading {len(ms_results)} MS files.", 5000)
        elif len(ms_results) == 0:
            self.view.statusbar.showMessage(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -- Finished loading {len(lc_results)} chromatography files.", 5000)
        self.view.processButton.setEnabled(True)
