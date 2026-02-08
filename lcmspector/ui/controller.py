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

logger = logging.getLogger(__name__)


class Controller:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.view.controller = self
        self.model.controller = self

        # Inject controller into tab modules
        self._inject_controller_into_tabs()

        # Connect signals to view widgets
        self._connect_signals()

        self.mode = "LC/GC-MS"
        logger.info("Controller initialized.")
        logger.info("Current thread: %s", threading.current_thread().name)
        logger.info("Current process: %d", os.getpid())

    def _inject_controller_into_tabs(self):
        """Inject controller reference into all tab modules."""
        if hasattr(self.view, "upload_tab"):
            self.view.upload_tab.set_controller(self)
        if hasattr(self.view, "results_tab"):
            self.view.results_tab.set_controller(self)
        if hasattr(self.view, "quantitation_tab"):
            self.view.quantitation_tab.set_controller(self)

    def _connect_signals(self):
        """Connect controller to current view widgets."""
        self.view.processButton.clicked.connect(self.process_data)
        self.view.comboBox_currentfile.currentIndexChanged.connect(
            self.display_selected_plots
        )
        self.view.calibrateButton.clicked.connect(self.calibrate)
        self.view.comboBoxChooseCompound.currentIndexChanged.connect(
            self.view.display_calibration_curve
        )
        self.view.comboBoxChooseCompound.currentIndexChanged.connect(
            self.view.display_concentrations
        )
        self.view.comboBoxChooseCompound.currentIndexChanged.connect(
            self.view.display_compound_integration
        )
        self.view.button_apply_integration.clicked.connect(
            self.model.apply_integration_changes
        )
        self.view.button_recalculate_integration.clicked.connect(
            self.model.recalculate_integration_all_files
        )
        self.view.button_reset_integration.clicked.connect(self.model.reset_integration)

    def _disconnect_signals(self):
        """Disconnect controller from old view widgets."""
        # Disconnect processButton
        try:
            self.view.processButton.clicked.disconnect(self.process_data)
        except (RuntimeError, TypeError):
            pass  # Already disconnected or widget deleted

        # Disconnect comboBox_currentfile
        try:
            self.view.comboBox_currentfile.currentIndexChanged.disconnect(
                self.display_selected_plots
            )
        except (RuntimeError, TypeError):
            pass

        # Disconnect calibrateButton
        try:
            self.view.calibrateButton.clicked.disconnect(self.calibrate)
        except (RuntimeError, TypeError):
            pass

        # Disconnect comboBoxChooseCompound
        try:
            self.view.comboBoxChooseCompound.currentIndexChanged.disconnect(
                self.view.display_calibration_curve
            )
        except (RuntimeError, TypeError):
            pass
        try:
            self.view.comboBoxChooseCompound.currentIndexChanged.disconnect(
                self.view.display_concentrations
            )
        except (RuntimeError, TypeError):
            pass
        try:
            self.view.comboBoxChooseCompound.currentIndexChanged.disconnect(
                self.view.display_compound_integration
            )
        except (RuntimeError, TypeError):
            pass

        # Disconnect integration buttons
        try:
            self.view.button_apply_integration.clicked.disconnect(
                self.model.apply_integration_changes
            )
        except (RuntimeError, TypeError):
            pass
        try:
            self.view.button_recalculate_integration.clicked.disconnect(
                self.model.recalculate_integration_all_files
            )
        except (RuntimeError, TypeError):
            pass
        try:
            self.view.button_reset_integration.clicked.disconnect(
                self.model.reset_integration
            )
        except (RuntimeError, TypeError):
            pass

    def reconnect_signals(self):
        """Reconnect signals after UI rebuild (mode change)."""
        logger.debug("Reconnecting controller signals to new widgets...")
        self._disconnect_signals()
        self._inject_controller_into_tabs()
        self._connect_signals()
        logger.debug("Controller signals reconnected.")

    def load_lc_data(self):
        pass

    def load_ms_data(self):
        pass

    def process_data(self):
        logger.info("Process data button clicked.")
        self.view.statusbar.showMessage(f"Processing data in {self.mode} mode ...")
        self.model.compounds = self.view.ionTable.get_items()
        self.model.mass_accuracy = self.view.mass_accuracy_slider.value()
        if not self.model.compounds:
            self.view.show_critical_error(
                "No compounds found!\n\nPlease define m/z values to trace or choose from the predefined lists before processing."
            )
            return
        if (
            hasattr(self.model, "ms_measurements")
            and hasattr(self.model, "lc_measurements")
        ) or (
            hasattr(self.model, "lc_measurements")
            and hasattr(self.model, "annotations")
        ):
            if self.mode == "LC/GC-MS" and not self.model.lc_measurements:
                self.view.show_critical_error(
                    "No files to process!\n\nPlease load LC files and either corresponding MS files or manual annotations before processing."
                )
                return
            elif self.mode == "LC/GC Only" and not self.model.lc_measurements:
                self.view.show_critical_error(
                    "No files to process!\n\nPlease load LC files before processing."
                )
                return
            elif self.mode == "MS Only" and not self.model.ms_measurements:
                self.view.show_critical_error(
                    "No files to process!\n\nPlease load MS files before processing."
                )
                return
            if not self.model.compounds or not self.model.compounds[0].ions:
                self.view.show_critical_error(
                    "Please define m/z values to trace or choose from the predefined lists before processing."
                )
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
                self.view.show_critical_error(
                    f"Error processing data: {traceback.format_exc()}"
                )
                return
        else:
            self.view.show_critical_error(
                "Nothing to process. Please load LC files and either corresponding MS files or manual annotations before proceeding."
            )
            logger.error(
                "Nothing to process. Please load LC files and either corresponding MS files or manual annotations before proceeding."
            )

    def on_processing_finished(self, compound_results):
        # iterate over the compound results and match them with their respective MS file
        for compound in compound_results:
            self.model.ms_measurements[compound[0].file.split(".")[0]].xics = compound

        self.view.progressBar.setVisible(False)
        self.view.progressLabel.setVisible(False)
        self.view.processButton.setEnabled(True)
        self.view.statusbar.showMessage(
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -- Finished processing, displaying results.",
            5000,
        )

        self.view.tabWidget.setTabEnabled(
            self.view.tabWidget.indexOf(self.view.tabResults), True
        )
        self.view.tabWidget.setCurrentIndex(
            self.view.tabWidget.indexOf(self.view.tabResults)
        )
        self.view.tabWidget.setTabEnabled(
            self.view.tabWidget.indexOf(self.view.tabQuantitation), True
        )
        self.view.setup_dock_area(
            next(iter(self.model.ms_measurements.values())).xics, self.view.canvas_XICs
        )
        self.update_filenames()
        self.view.actionExport.setEnabled(True)

        # Enable compound selection and populate compound list
        self.view.comboBoxChooseCompound.setEnabled(True)
        self.view.update_choose_compound(self.model.compounds)

    def update_filenames(self):
        if self.mode == "LC/GC-MS" or self.mode == "LC/GC Only":
            filenames = list(self.model.lc_measurements.keys())
            # Grab the return values of extract_concentration() for every file in lc_measurements
            concentrations = [
                [file, self.model.lc_measurements[file].extract_concentration()]
                for file in filenames
            ]
            self.view.update_combo_box(filenames)
            self.view.update_table_quantitation(concentrations)
            self.view.quantitation_tab.update_file_combo_box(filenames)
        else:
            filenames = list(self.model.ms_measurements.keys())
            concentrations = [
                [file, self.model.ms_measurements[file].extract_concentration()]
                for file in filenames
            ]
            self.view.update_combo_box(filenames)
            self.view.update_table_quantitation(concentrations)
            self.view.quantitation_tab.update_file_combo_box(filenames)

    def display_selected_plots(self):
        """
        Display plots for the currently selected file.
        """
        selected_file = self.view.comboBox_currentfile.currentText()
        try:
            lc_file, ms_file = self.model.get_plots(selected_file)
            self.view.display_plots(lc_file, ms_file)
        except Exception:
            logger.error(
                "Error getting plots for file %s: %s",
                selected_file,
                traceback.format_exc(),
            )

    def calibrate(self):
        """
        Calibrates the concentrations of the selected MS files using the selected files with annotated concentrations.
        :return: None
        """
        selected_files = self.view.get_calibration_files()
        if not selected_files:
            logger.error("No files selected for calibration.")
            return

        # Validate at least 2 files have concentration values
        valid_count = sum(1 for conc in selected_files.values() if conc and conc.strip())
        if valid_count < 2:
            logger.error(f"Need at least 2 files with concentrations for calibration, got {valid_count}.")
            return

        try:
            self.model.calibrate(selected_files)
        except Exception:
            logger.error(f"Error calibrating files: {traceback.format_exc()}")
            return

        # Display the calibration curve after successful calibration
        self.view.display_calibration_curve()

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

    def on_loading_finished(self, results):
        # Validate this is from current worker (prevents stale callbacks after mode change)
        if hasattr(self.model, "worker") and self.model.worker:
            if hasattr(self.model.worker, "worker_id"):
                if self.model.worker.worker_id != self.model._current_worker_id:
                    logger.warning("Ignoring results from stale worker")
                    return

        # Safeguard to only update what was just loaded
        if results is not None and len(results) > 0:
            try:
                last_loaded_result = list(results.keys())[0]
                logger.debug(
                    f"Received results with file type: {results[last_loaded_result].file_type}"
                )
            except AttributeError:
                logger.error(
                    "Invalid results format received. Setting last_loaded_result to None."
                )
                last_loaded_result = None
            if results[last_loaded_result].file_type == "LC":
                self.model.lc_measurements = results
                self.view.upload_tab.listLC.checkItem(0)
            elif results[last_loaded_result].file_type == "MS":
                self.model.ms_measurements = results
                self.view.upload_tab.listMS.checkItem(0)
            else:
                logger.error("Unknown file type in results.")

        self.view.progressBar.setVisible(False)
        self.view.progressLabel.setVisible(False)
        if len(results) == 0:
            self.view.statusbar.showMessage(
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -- No files loaded.",
                5000,
            )
            return
        else:
            self.view.statusbar.showMessage(
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -- Finished loading {len(results)} files.",
                5000,
            )
            self.view.processButton.setEnabled(True)

            # Re-plot any files that were checked before loading completed
            if hasattr(self.view, "upload_tab"):
                self.view.upload_tab.refresh_checkbox_plots()
