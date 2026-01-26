from PySide6 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import logging
import traceback
import numpy as np

from ui.widgets import (
    UnifiedResultsTable,
    ChromatogramPlotWidget,
)
from ui.plotting import (
    plot_average_ms_data,
    plot_annotated_LC,
    plot_annotated_XICs,
    plot_ms2_from_file,
    plot_no_ms2_found,
    plot_calibration_curve,
    plot_library_ms2,
)

logger = logging.getLogger(__name__)

class ResultsTab(QtWidgets.QWidget):
    """
    Handles the visualization of results: tables, chromatograms, and MS spectra.
    Reconstructs functionality from the legacy view_original.py module.
    """
    # Signals to communicate back to the controller or other widgets
    file_changed = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QtWidgets.QGridLayout(self)
        
        # Internal State
        self.curve_list = {} 
        
        # State tracking for data
        self.mode = "LC/GC-MS"
        self.current_lc_file = None
        self.current_ms_file = None

        self.setup_ui()

    def setup_ui(self):
        self.control_layout = QtWidgets.QHBoxLayout()
        self.comboBox_currentfile = QtWidgets.QComboBox()
        self.comboBox_currentfile.currentIndexChanged.connect(self._on_file_selected)
        
        self.control_layout.addWidget(QtWidgets.QLabel("Compound:"))
        self.control_layout.addWidget(self.comboBox_currentfile)
        self.control_layout.addStretch()
        
        self.layout.addLayout(self.control_layout, 0, 0, 1, 2)

        self.plot_layout = QtWidgets.QGridLayout()
        self.canvas_annotatedLC = ChromatogramPlotWidget(title="Annotated LC Chromatogram")
        self.plot_layout.addWidget(self.canvas_annotatedLC, 0, 0)
        
        self.canvas_xics = pg.PlotWidget(title="Extracted Ion Chromatograms (XICs)")
        self.plot_layout.addWidget(self.canvas_xics, 1, 0)
        
        # Avg MS
        self.canvas_avg_ms = pg.PlotWidget(title="Average MS Spectrum")
        self.plot_layout.addWidget(self.canvas_avg_ms, 2, 0)
        
        # MS2 or Calibration Curve (Dynamic based on context)
        # In the original, this slot was often used for MS2 or Calibration
        self.canvas_bottom = pg.PlotWidget(title="MS2 / Calibration")
        self.plot_layout.addWidget(self.canvas_bottom, 3, 0)

        # Add plot layout to main grid
        self.layout.addLayout(self.plot_layout, 1, 1, 2, 1)
        
        # Sizing
        self.layout.setColumnStretch(0, 2) # Table
        self.layout.setColumnStretch(1, 3) # Plots

    def _on_file_selected(self, index):
        """Internal handler to emit signal."""
        if index != None:
            self.file_changed.emit(index)

    def display_plots(self, mode, lc_file, ms_file, selected_compound=None):
        """
        Orchestrates plotting logic. Called by Controller after processing.
        Replaces the scattered plot calls in legacy `on_process`.
        """
        self.current_mode = mode
        self.current_lc_file = lc_file
        self.current_ms_file = ms_file
        
        try:
            # 1. Clear old plots
            self.canvas_annotatedLC.clear()
            self.canvas_xics.clear()
            self.canvas_avg_ms.clear()
            self.canvas_bottom.clear()

            # 2. Plot LC Data (Only in LC/GC-MS mode)
            if mode == "LC/GC-MS" and lc_file:
                # We expect lc_file to have .path, .df (dataframe) or .time/.absorbance arrays
                # Adhering to the original signature of plot_annotated_LC
                # Assuming lc_file wrapper exposes these properties
                path_str = str(lc_file.path) if hasattr(lc_file, 'path') else "LC File"
                
                # Check if baseline corrected data exists, otherwise use raw
                # This depends on the specific structure of the 'lc_file' object passed from controller
                data_source = getattr(lc_file, 'baseline_corrected', getattr(lc_file, 'data', None))
                
                if data_source is not None:
                    self.curve_list = plot_annotated_LC(
                        path_str, 
                        data_source, 
                        self.canvas_annotatedLC
                    )
                
                # Re-add crosshairs cleared by .clear()
                self.canvas_annotatedLC.addItem(self.crosshair_v)
                self.canvas_annotatedLC.addItem(self.crosshair_h)

            # 3. Plot MS Data
            if ms_file:
                filename = ms_file.filename if hasattr(ms_file, 'filename') else "MS File"
                
                # Plot Average MS
                # Assuming ms_file has .data (mz, intensity) or similar structure expected by helper
                if hasattr(ms_file, 'data'):
                     # plot_average_ms_data(filename, scan_number/time, data, widget)
                     # Passing 0 as placeholder for scan number if not applicable
                    plot_average_ms_data(filename, 0, ms_file.data, self.canvas_avg_ms)

                # Plot XICs if available
                if hasattr(ms_file, 'xics') and ms_file.xics:
                     plot_annotated_XICs(filename, ms_file.xics, self.canvas_xics)

            # 4. Handle MS2 or Calibration Curve (Context dependent)
            # This logic was typically triggered by selection changes in the original view
            if selected_compound:
                self.update_compound_plots(selected_compound)

        except Exception as e:
            logger.error(f"Error displaying plots: {traceback.format_exc()}")
            QtWidgets.QMessageBox.warning(self, "Plotting Error", f"An error occurred while plotting: {e}")

    def update_unified_table(self, concentrations, ms_measurements, compounds, selected_idx):
        """Updates the UnifiedResultsTable."""
        # Update Compound Combo Box if it's different
        if compounds:
            current_items = [self.combo_compound.itemText(i) for i in range(self.combo_compound.count())]
            if current_items != compounds:
                self.combo_compound.blockSignals(True)
                self.combo_compound.clear()
                self.combo_compound.addItems(compounds)
                if 0 <= selected_idx < len(compounds):
                     self.combo_compound.setCurrentIndex(selected_idx)
                self.combo_compound.blockSignals(False)

        current_compound = None
        if compounds and 0 <= selected_idx < len(compounds):
            current_compound = compounds[selected_idx]
            
        self.unifiedResultsTable.setup_columns(current_compound)
        self.unifiedResultsTable.populate_data(concentrations, ms_measurements, current_compound)

    def update_compound_plots(self, compound_data):
        """
        Updates the specific plots that depend on the selected compound
        (e.g., Calibration Curve or Library MS2).
        """
        self.canvas_bottom.clear()
        
        # Logic derived from legacy view:
        # If calibration data exists, plot it. Else if MS2 exists, plot it.
        
        # Check for calibration data
        if compound_data and "calibration" in compound_data:
             plot_calibration_curve(compound_data["calibration"], self.canvas_bottom)
             self.canvas_bottom.setTitle("Calibration Curve")
             return

        # Check for MS2 Library Match
        if compound_data and "library_ms2" in compound_data:
            plot_library_ms2(compound_data["library_ms2"], self.canvas_bottom)
            self.canvas_bottom.setTitle("Library MS2 Spectrum")
            return
            
        # Fallback
        self.canvas_bottom.setTitle("No details available")

    def clear_all(self):
        """Resets the tab to initial state."""
        self.canvas_annotatedLC.clear()
        self.canvas_xics.clear()
        self.canvas_avg_ms.clear()
        self.canvas_bottom.clear()
        self.unifiedResultsTable.clearContents()
        self.unifiedResultsTable.setRowCount(0)
        self.combo_compound.clear()
        self.curve_list = {}
