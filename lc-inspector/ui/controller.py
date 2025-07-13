"""
Controller module for the LC-Inspector application.

This module provides the controller class for the LC-Inspector application.
The controller mediates between the model and view, handling user actions and updating the view.
"""

from PyQt6.QtCore import pyqtSlot
import logging
import traceback
import threading
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class Controller:
    """
    The Controller class mediates between the model and view.
    
    This class handles user actions and updates the view based on model changes.
    It subscribes to model events and updates the view accordingly.
    
    Attributes
    ----------
    model : LCInspectorModel
        The model instance.
    view : View
        The view instance.
    mode : str
        The current processing mode.
    """
    
    def __init__(self, model, view):
        """
        Initialize the controller with model and view instances.
        
        Parameters
        ----------
        model : LCInspectorModel
            The model instance.
        view : View
            The view instance.
        """
        self.model = model
        self.view = view
        self.view.controller = self
        self.mode = "LC/GC-MS"
        
        # Connect view signals to controller methods
        self.view.processButton.clicked.connect(self.process_data)
        self.view.comboBox_currentfile.currentIndexChanged.connect(self.display_selected_plots)
        self.view.calibrateButton.clicked.connect(self.calibrate)
        self.view.calibrateButton.clicked.connect(self.find_ms2_precursors)
        self.view.comboBoxChooseCompound.currentIndexChanged.connect(self.view.display_calibration_curve)
        self.view.comboBoxChooseCompound.currentIndexChanged.connect(self.view.display_concentrations)
        self.view.comboBoxChooseCompound.currentIndexChanged.connect(self.view.display_ms2)
        self.view.comboBoxChooseCompound.currentIndexChanged.connect(self.view.display_library_ms2)
        
        # Subscribe to model events
        self.model.on('processing_started', self._on_processing_started)
        self.model.on('processing_finished', self._on_processing_finished)
        self.model.on('progress_updated', self._on_progress_updated)
        self.model.on('calibration_finished', self._on_calibration_finished)
        self.model.on('ms2_precursors_found', self._on_ms2_precursors_found)
        self.model.on('ms2_in_file_found', self._on_ms2_in_file_found)
        self.model.on('export_finished', self._on_export_finished)
        
        logger.info("Controller initialized.")
        logger.info(f"Current thread: {threading.current_thread().name}")
        logger.info(f"Current process: {os.getpid()}")
    
    def process_data(self):
        """Process the data using the current mode."""
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
    
    def _on_processing_started(self, _):
        """Handle the processing started event."""
        logger.info("Processing started.")
    
    def _on_processing_finished(self, data):
        """
        Handle the processing finished event.
        
        Parameters
        ----------
        data : dict
            A dictionary containing the LC and MS results.
        """
        lc_results = data['lc_results']
        ms_results = data['ms_results']
        
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
    
    def _on_progress_updated(self, value):
        """
        Handle the progress updated event.
        
        Parameters
        ----------
        value : int
            The progress value (0-100).
        """
        self.view.update_progress_bar(value)
    
    def _on_calibration_finished(self, compounds):
        """
        Handle the calibration finished event.
        
        Parameters
        ----------
        compounds : list
            The list of calibrated compounds.
        """
        logger.info(f"Received calibration_finished event with {len(compounds) if compounds else 'no'} compounds")
        if compounds:
            for compound in compounds:
                logger.info(f"Event compound: {compound.name}")
        logger.info(f"Model has {len(self.model.compounds)} compounds")
        for compound in self.model.compounds:
            logger.info(f"Model compound: {compound.name}")
            
        self.view.comboBoxChooseCompound.setEnabled(True)
        self.view.update_choose_compound(self.model.compounds)
        logger.info(f"comboBoxChooseCompound has {self.view.comboBoxChooseCompound.count()} items")
    
    def _on_ms2_precursors_found(self, data):
        """
        Handle the MS2 precursors found event.
        
        Parameters
        ----------
        data : dict
            A dictionary containing the compound index and library entries.
        """
        compound_index = data['compound_index']
        library_entries = data['library_entries']
        
        self.view.comboBoxChooseMS2File.clear()
        self.view.comboBoxChooseMS2File.addItems(library_entries.keys())
    
    def _on_ms2_in_file_found(self, data):
        """
        Handle the MS2 in file found event.
        
        Parameters
        ----------
        data : dict
            A dictionary containing the MS file and compound index.
        """
        pass  # This event is currently not used
    
    def _on_export_finished(self, df):
        """
        Handle the export finished event.
        
        Parameters
        ----------
        df : pd.DataFrame
            The exported data.
        """
        pass  # This event is currently not used
    
    def display_selected_plots(self):
        """Display the plots for the selected file."""
        selected_file = self.view.comboBox_currentfile.currentText()
        try:
            lc_file, ms_file = self.model.get_plots(selected_file)
        except Exception:
            logger.error(f"Error getting plots for file {selected_file}: {traceback.format_exc()}")
            return
        self.view.display_plots(lc_file, ms_file)
    
    def calibrate(self):
        """Calibrate the concentrations of the selected MS files."""
        selected_files = self.view.get_calibration_files()
        
        # Always enable the combobox and update with compounds, even if no files are selected
        self.view.comboBoxChooseCompound.setEnabled(True)
        
        if not self.model.compounds:
            logger.error("No compounds found for calibration")
            return
            
        logger.info(f"Updating comboBoxChooseCompound with {len(self.model.compounds)} compounds before calibration")
        self.view.update_choose_compound(self.model.compounds)
        
        if selected_files:
            try:
                self.model.calibrate(selected_files)
                # The event system should handle the update after calibration
            except Exception:
                logger.error(f"Error calibrating files: {traceback.format_exc()}")
        else:
            logger.info("No files selected for calibration. Skipping calibration but still showing compounds.")
    
    def find_ms2_precursors(self):
        """Find MS2 precursors for the currently selected compound."""
        try:
            self.view.statusbar.showMessage(f"Looking for MS2 precursors...", 5000)
            compound_index = self.view.comboBoxChooseCompound.currentIndex()
            self.model.find_ms2_precursors(compound_index)
        except Exception:
            logger.error(f"Error finding MS2 precursors: {traceback.format_exc()}")
            return
    
    def update_filenames(self):
        """Update the filenames in the view."""
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
