"""
Main View module for LC-Inspector application.

This module provides the main application window and orchestrates the tab modules.
It handles global UI elements (menu bar, status bar, progress bar) and delegates
tab-specific functionality to the respective tab modules.
"""

import os
import subprocess
import tempfile
import traceback
import logging
from pathlib import Path
from datetime import datetime

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMessageBox,
)
import pyqtgraph as pg
from pyqtgraph.dockarea import DockArea

from ui.widgets import ReadmeDialog
from ui.tabs.upload_tab import UploadTab
from ui.tabs.results_tab import ResultsTab
from ui.tabs.quantitation_tab import QuantitationTab
from ui.retranslate_ui import retranslateUi


pg.setConfigOptions(antialias=True)
logger = logging.getLogger(__name__)


class View(QtWidgets.QMainWindow):
    """
    Main application window.

    Orchestrates the tab modules and handles global UI elements like
    the menu bar, status bar, and progress bar.
    """

    progress_update = QtCore.Signal(int)

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.progress_update.connect(self.update_progressBar)
        self.resize(1500, 900)
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    # =========================================================================
    # Widget Delegation Properties for Controller Access
    # =========================================================================
    # These properties provide backward-compatible access to widgets that
    # are now managed by the tab modules.

    # --- UploadTab Widgets ---
    @property
    def processButton(self):
        """Access process button from UploadTab."""
        return self.upload_tab.processButton

    @property
    def ionTable(self):
        """Access ion table from UploadTab."""
        return self.upload_tab.ionTable

    @property
    def mass_accuracy_slider(self):
        """Access mass accuracy slider from UploadTab."""
        return self.upload_tab.mass_accuracy_slider

    @property
    def canvas_baseline(self):
        """Access baseline canvas from UploadTab."""
        return self.upload_tab.canvas_baseline

    @property
    def canvas_avgMS(self):
        """Access average MS canvas from UploadTab."""
        return self.upload_tab.canvas_avgMS

    @property
    def listLC(self):
        """Access LC file list from UploadTab."""
        return getattr(self.upload_tab, "listLC", None)

    @property
    def listMS(self):
        """Access MS file list from UploadTab."""
        return getattr(self.upload_tab, "listMS", None)

    @property
    def listAnnotations(self):
        """Access annotations list from UploadTab."""
        return getattr(self.upload_tab, "listAnnotations", None)

    @property
    def comboBoxIonLists(self):
        """Access ion lists combo box from UploadTab."""
        return self.upload_tab.comboBoxIonLists

    @property
    def crosshair_v(self):
        """Access vertical crosshair from UploadTab."""
        return self.upload_tab.crosshair_v

    @property
    def crosshair_h(self):
        """Access horizontal crosshair from UploadTab."""
        return self.upload_tab.crosshair_h

    @property
    def line_marker(self):
        """Access line marker from UploadTab."""
        return self.upload_tab.line_marker

    # --- QuantitationTab Widgets ---
    @property
    def calibrateButton(self):
        """Access calibrate button from QuantitationTab."""
        return self.quantitation_tab.calibrateButton

    @property
    def comboBoxChooseCompound(self):
        """Access compound combo box from QuantitationTab."""
        return self.quantitation_tab.comboBoxChooseCompound

    @property
    def comboBoxChooseMS2File(self):
        """Access MS2 file combo box from QuantitationTab."""
        return self.quantitation_tab.comboBoxChooseMS2File

    @property
    def unifiedResultsTable(self):
        """Access unified results table from QuantitationTab."""
        return self.quantitation_tab.unifiedResultsTable

    @property
    def canvas_calibration(self):
        """Access calibration canvas from QuantitationTab."""
        return self.quantitation_tab.canvas_calibration

    @property
    def canvas_ms2(self):
        """Access MS2 canvas from QuantitationTab."""
        return self.quantitation_tab.canvas_ms2

    @property
    def canvas_library_ms2(self):
        """Access library MS2 canvas from QuantitationTab."""
        return self.quantitation_tab.canvas_library_ms2

    @property
    def button_apply_integration(self):
        """Access apply integration button from QuantitationTab."""
        return self.quantitation_tab.button_apply_integration

    @property
    def button_recalculate_integration(self):
        """Access recalculate integration button from QuantitationTab."""
        return self.quantitation_tab.button_recalculate_integration

    @property
    def button_reset_integration(self):
        """Access reset integration button from QuantitationTab."""
        return self.quantitation_tab.button_reset_integration

    # --- ResultsTab Widgets ---
    @property
    def comboBox_currentfile(self):
        """Access current file combo box from ResultsTab."""
        return self.results_tab.comboBox_currentfile

    @property
    def canvas_XICs(self):
        """Access XICs dock area from ResultsTab."""
        return self.results_tab.canvas_XICs

    @property
    def canvas_annotatedLC(self):
        """Access annotated LC canvas from ResultsTab."""
        return self.results_tab.canvas_annotatedLC

    @property
    def scrollArea(self):
        """Access scroll area from ResultsTab."""
        return self.results_tab.scrollArea

    # =========================================================================
    # Download Dialog Methods (MS2 Library)
    # =========================================================================

    def show_download_confirmation(self):
        """Displays a confirmation dialog for downloading the MS2 library."""
        reply = QMessageBox.question(
            self,
            "MS2 Library Not Found",
            "The MS2 library is missing. Would you like to download it now? (approx. 400 MB)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return reply == QMessageBox.Yes

    def show_download_progressBar(self):
        """Shows the main window's progress bar for the download."""
        self.progressBar.setVisible(True)
        self.progressLabel.setVisible(True)
        self.statusbar.showMessage("Downloading MS2 Library...")

    def update_download_progressBar(self, value):
        """Updates the main window's progress bar."""
        self.progressBar.setValue(value)
        self.progressLabel.setText(f"{value}%")

    def hide_download_progressBar(self):
        """Hides the main window's progress bar."""
        self.progressBar.setVisible(False)
        self.progressLabel.setVisible(False)
        self.statusbar.clearMessage()

    def show_download_success(self):
        """Shows a success message after the download is complete."""
        QMessageBox.information(
            self, "Download Complete", "MS2 library downloaded successfully."
        )

    def show_download_failure(self, error_message):
        """Shows a failure message if the download fails."""
        QMessageBox.critical(
            self, "Download Failed", f"Failed to download MS2 library:\n{error_message}"
        )

    # =========================================================================
    # Progress and Status Methods
    # =========================================================================

    def update_progressBar(self, value):
        """Update the progress bar value."""
        try:
            self.progressBar.setValue(value)
            self.progressLabel.setText(f"{value}%")
        except AttributeError:
            logger.error("Progress bar not found in the view.")

    def update_statusbar_with_loaded_file(self, progress, message):
        """Update status bar with loading progress."""
        try:
            self.statusbar.showMessage(
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -- Loaded file {message} ({progress}%)",
                1000,
            )
        except AttributeError:
            logger.error("Status bar not found in the view.")

    def show_critical_error(self, message):
        """Show a critical error message box."""
        QtWidgets.QMessageBox.critical(self, "Error", message)

    # =========================================================================
    # Menu Action Handlers
    # =========================================================================

    def on_exit(self):
        """Exit the application."""
        QApplication.instance().quit()

    def on_export(self):
        """Export results to CSV."""
        logger.info("Export action triggered.")
        results = self.controller.model.export()
        if not results.empty:
            file_name, _ = QFileDialog.getSaveFileName(
                self, "Save Results", "", "CSV Files (*.csv);;All Files (*)"
            )
            if file_name:
                with open(file_name, "w") as f:
                    f.write(results.to_csv(index=False))
                output_folder = os.path.dirname(file_name)
                self.statusbar.showMessage(
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -- Saved results to {output_folder}",
                    5000,
                )
                logger.info(f"Exported results to {output_folder}.")
        else:
            self.show_critical_error("Error: Nothing to export.")
            logger.error("Nothing to export.")

    def on_logs(self):
        """Open the log file."""
        logger.info("Log file action triggered.")
        log_file = Path(tempfile.gettempdir()) / "lcmspector/lcmspector.log"
        if os.sys.platform.startswith("win"):
            try:
                os.startfile(log_file)
            except Exception:
                logger.error(f"Could not open log file: {traceback.format_exc()}.")
        elif os.sys.platform == "darwin":
            try:
                subprocess.run(["open", log_file])
            except Exception:
                logger.error(f"Could not open log file: {traceback.format_exc()}.")
        else:
            try:
                subprocess.run(["xdg-open", log_file])
            except Exception:
                logger.error(f"Could not open log file: {traceback.format_exc()}.")

    def on_readme(self):
        """Open the Readme dialog."""
        readme = ReadmeDialog(self)
        readme.show()

    # =========================================================================
    # Delegation Methods for Controller
    # =========================================================================
    # These methods delegate to the appropriate tab for backward compatibility
    # with the controller.

    def update_combo_box(self, filenames):
        """Update the file selection combo box in the results tab."""
        self.results_tab.update_combo_box(filenames)

    def update_table_quantitation(self, concentrations):
        """Update the unified results table. Delegates to QuantitationTab."""
        self.quantitation_tab.update_table_quantitation(concentrations)

    def update_unified_table_for_compound(self):
        """Update the unified table for selected compound. Delegates to QuantitationTab."""
        self.quantitation_tab.update_unified_table_for_compound()

    def get_calibration_files(self):
        """Get calibration files. Delegates to QuantitationTab."""
        return self.quantitation_tab.get_calibration_files()

    def update_choose_compound(self, compounds):
        """Update compound selection combo box. Delegates to QuantitationTab."""
        self.quantitation_tab.update_choose_compound(compounds)

    def display_calibration_curve(self):
        """Display calibration curve. Delegates to QuantitationTab."""
        self.quantitation_tab.display_calibration_curve()

    def display_concentrations(self):
        """Display concentrations. Delegates to QuantitationTab."""
        self.quantitation_tab.display_concentrations()

    def display_compound_integration(self):
        """Display compound integration. Delegates to QuantitationTab."""
        self.quantitation_tab.display_compound_integration()

    def display_ms2(self):
        """Display MS2 data. Delegates to QuantitationTab."""
        self.quantitation_tab.display_ms2()

    def get_integration_bounds(self, canvas=None, ion_key: str = None):
        """Get integration bounds. Delegates to QuantitationTab."""
        return self.quantitation_tab.get_integration_bounds(canvas, ion_key)

    def setup_dock_area(self, xics, widget=None):
        """Setup dock area with XICs. Delegates to ResultsTab."""
        if widget is None:
            widget = self.results_tab.canvas_XICs
        self.results_tab.setup_dock_area(xics, widget)

    def plot_raw_chromatography(self, lc_file):
        """Plot raw chromatography data. Delegates to UploadTab."""
        self.upload_tab._plot_raw_chromatography(lc_file)

    def plot_raw_MS(self, ms_file):
        """Plot raw MS data. Delegates to UploadTab."""
        self.upload_tab._plot_raw_ms(ms_file)

    def display_plots(self, lc_file, ms_file):
        """Display plots for given files. Delegates to ResultsTab only."""
        # Only update results tab - upload tab has its own checkbox system
        self.results_tab.display_plots(lc_file, ms_file)

    # =========================================================================
    # Mode Change Handling
    # =========================================================================

    def change_mode(self):
        """
        Handle mode change from the combo box.

        This method:
        1. Asks for confirmation if data is loaded
        2. Clears all loaded data
        3. Updates all tabs for the new mode
        4. Resets tab enable states
        """
        new_mode = self.comboBoxChangeMode.currentText()

        # Check if we need to confirm mode change
        if self._has_loaded_data():
            reply = QMessageBox.question(
                self,
                "Confirm Mode Change",
                "Changing mode will clear all loaded data and results. Do you want to proceed?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.No:
                self._restore_mode_combo()
                return

        # Clear all data
        self._clear_all_data()

        # Update controller mode
        if hasattr(self, "controller"):
            self.controller.mode = new_mode

        # Update all tabs for the new mode
        self.upload_tab.setup_layout(new_mode)
        self.results_tab.setup_layout(new_mode)
        self.quantitation_tab.setup_layout(new_mode)

        # CRITICAL: Reconnect controller signals to new widgets
        # After setup_layout(), all widgets are new instances, so old signal
        # connections are stale. We must reconnect the controller to the new widgets.
        if hasattr(self, "controller"):
            self.controller.reconnect_signals()

        # Disable results and quantitation tabs
        self.tabWidget.setTabEnabled(self.tabWidget.indexOf(self.results_tab), False)
        self.tabWidget.setTabEnabled(
            self.tabWidget.indexOf(self.quantitation_tab), False
        )

        # Switch to upload tab
        self.tabWidget.setCurrentIndex(0)

        # Update status bar
        self.statusbar.showMessage(f"Switched to {new_mode} mode.", 3000)

        # Retranslate UI for the new mode
        retranslateUi(self)

    def _has_loaded_data(self):
        """Check if any data is currently loaded."""
        if not hasattr(self, "controller") or not hasattr(self.controller, "model"):
            return False
        model = self.controller.model
        has_lc = hasattr(model, "lc_measurements") and model.lc_measurements
        has_ms = hasattr(model, "ms_measurements") and model.ms_measurements
        has_compounds = hasattr(model, "compounds") and model.compounds
        return has_lc or has_ms or has_compounds

    def _restore_mode_combo(self):
        """Restore combo box to the current mode without triggering change."""
        if not hasattr(self, "controller"):
            return
        mode = self.controller.mode
        self.comboBoxChangeMode.blockSignals(True)
        index = self.comboBoxChangeMode.findText(mode)
        if index >= 0:
            self.comboBoxChangeMode.setCurrentIndex(index)
        self.comboBoxChangeMode.blockSignals(False)

    def _clear_all_data(self):
        """Clear all loaded data from the model and view."""
        if hasattr(self, "controller") and hasattr(self.controller, "model"):
            model = self.controller.model

            # IMPORTANT: Stop workers FIRST before clearing any data
            # This prevents workers from accessing cleared data
            if hasattr(model, "shutdown"):
                model.shutdown()

            # Now safely clear measurements with proper resource cleanup
            if hasattr(model, "clear_measurements"):
                model.clear_measurements()
            else:
                # Fallback for older model versions
                if hasattr(model, "lc_measurements"):
                    model.lc_measurements = {}
                if hasattr(model, "ms_measurements"):
                    model.ms_measurements = {}
                if hasattr(model, "annotations"):
                    model.annotations = {}
                if hasattr(model, "compounds"):
                    model.compounds = []

        # Clear all tabs
        self.upload_tab.clear()
        self.results_tab.clear()
        self.quantitation_tab.clear()

        # Disable export action
        self.actionExport.setEnabled(False)

    # =========================================================================
    # Main UI Setup
    # =========================================================================

    def setupUi(self, MainWindow):
        """Setup the main user interface."""
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1200, 800)

        # Central widget and main layout
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayoutOuter = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayoutOuter.setObjectName("gridLayoutOuter")

        # Tab widget
        self.tabWidget = QtWidgets.QTabWidget(parent=self.centralwidget)
        self.tabWidget.setObjectName("tabWidget")

        # =====================================================================
        # Create Tab Instances
        # =====================================================================

        # Upload Tab
        self.upload_tab = UploadTab(parent=self.tabWidget, mode="LC/GC-MS")
        self.tabUpload = self.upload_tab  # Alias for backward compatibility

        # Results Tab
        self.results_tab = ResultsTab(parent=self.tabWidget, mode="LC/GC-MS")
        self.tabResults = self.results_tab  # Alias for backward compatibility

        # Quantitation Tab
        self.quantitation_tab = QuantitationTab(parent=self.tabWidget, mode="LC/GC-MS")
        self.tabQuantitation = self.quantitation_tab  # Alias for backward compatibility

        # Add tabs to tab widget
        self.tabWidget.addTab(self.upload_tab, "Upload")
        self.tabWidget.addTab(self.results_tab, "Results")
        self.tabWidget.setTabEnabled(self.tabWidget.indexOf(self.results_tab), False)
        self.tabWidget.addTab(self.quantitation_tab, "Quantitation")
        self.tabWidget.setTabEnabled(
            self.tabWidget.indexOf(self.quantitation_tab), False
        )

        # =====================================================================
        # Mode Selection Combo Box
        # =====================================================================

        self.comboBoxChangeMode = QtWidgets.QComboBox(parent=self.centralwidget)
        self.comboBoxChangeMode.addItem("LC/GC-MS")
        self.comboBoxChangeMode.addItem("MS Only")
        self.comboBoxChangeMode.addItem("Chromatography Only")
        self.gridLayoutOuter.addWidget(self.comboBoxChangeMode, 2, 0, 1, 1)

        # =====================================================================
        # Logo
        # =====================================================================

        self.logo = QtWidgets.QLabel(parent=self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed
        )
        self.logo.setSizePolicy(sizePolicy)
        self.logo.setMaximumSize(QtCore.QSize(1200, 100))
        self.logo.setText("")
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        if os.path.exists(logo_path):
            self.logo.setPixmap(QtGui.QPixmap(logo_path))
        self.logo.setScaledContents(True)
        self.logo.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.gridLayoutOuter.addWidget(self.logo, 0, 0, 2, 4)

        # Add tab widget to layout
        self.gridLayoutOuter.addWidget(self.tabWidget, 3, 0, 1, 4)

        MainWindow.setCentralWidget(self.centralwidget)

        # =====================================================================
        # Status Bar and Progress Bar
        # =====================================================================

        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.progressBar = QtWidgets.QProgressBar()
        self.statusbar.addPermanentWidget(self.progressBar)
        self.progressBar.setVisible(False)

        self.progressLabel = QtWidgets.QLabel()
        self.statusbar.addPermanentWidget(self.progressLabel)
        self.progressLabel.setVisible(False)

        # =====================================================================
        # Menu Bar
        # =====================================================================

        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 860, 40))

        self.menuFile = QtWidgets.QMenu(parent=self.menubar)
        self.menuEdit = QtWidgets.QMenu(parent=self.menubar)
        self.menuHelp = QtWidgets.QMenu(parent=self.menubar)

        # Actions
        self.actionSave = QtGui.QAction(parent=MainWindow)
        self.actionExit = QtGui.QAction(parent=MainWindow)
        self.actionPreferences = QtGui.QAction(parent=MainWindow)
        self.actionReadme = QtGui.QAction(parent=MainWindow)
        self.actionFile = QtGui.QAction(parent=MainWindow)
        self.actionExport = QtGui.QAction(parent=MainWindow)
        self.actionExport.setEnabled(False)
        self.actionOpen = QtGui.QAction(parent=MainWindow)
        self.actionAbout = QtGui.QAction(parent=MainWindow)
        self.actionLogs = QtGui.QAction(parent=MainWindow)

        # Add actions to menus
        self.menuFile.addAction(self.actionOpen)
        self.menuFile.addAction(self.actionSave)
        self.menuFile.addAction(self.actionExport)
        self.menuFile.addAction(self.actionExit)
        self.menuEdit.addAction(self.actionPreferences)
        self.menuHelp.addAction(self.actionReadme)
        self.menuHelp.addAction(self.actionAbout)
        self.menuHelp.addAction(self.actionLogs)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuEdit.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())

        MainWindow.setMenuBar(self.menubar)

        # =====================================================================
        # Signal Connections
        # =====================================================================

        self.tabWidget.setCurrentIndex(0)

        # Menu actions
        self.actionExit.triggered.connect(self.on_exit)
        self.actionExport.triggered.connect(self.on_export)
        self.actionLogs.triggered.connect(self.on_logs)
        self.actionReadme.triggered.connect(self.on_readme)

        # Mode change
        self.comboBoxChangeMode.currentIndexChanged.connect(self.change_mode)

        # Connect upload tab signals
        self.upload_tab.files_loaded.connect(self._on_files_loaded)
        self.upload_tab.status_message.connect(
            lambda msg, timeout: self.statusbar.showMessage(msg, timeout)
        )

        # Retranslate UI
        retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def _on_files_loaded(self, file_type, file_paths):
        """Handle files loaded from UploadTab."""
        if not hasattr(self, "controller"):
            return

        # Show progress bar
        self.progressBar.setVisible(True)
        self.progressLabel.setVisible(True)
        self.progressBar.setValue(0)

        # Trigger loading in model
        logger.debug(f"Loading {file_type} files: {file_paths}")
        self.controller.model.load(self.controller.mode, file_paths, file_type)

    def retranslateUi(self, MainWindow):
        """Retranslate UI elements. Delegates to retranslate_ui module."""
        retranslateUi(MainWindow)
