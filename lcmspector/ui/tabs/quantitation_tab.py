"""
Quantitation Tab for calibration and concentration analysis.
"""
from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt
import pyqtgraph as pg
import logging
import traceback

from ui.tabs.base_tab import TabBase
from ui.widgets import UnifiedResultsTable
from ui.plotting import (
    plot_calibration_curve,
    plot_compound_integration,
    plot_ms2_from_file,
    plot_no_ms2_found,
    update_labels_avgMS,
)

logger = logging.getLogger(__name__)


class QuantitationTab(TabBase):
    """
    Handles calibration, quantitation, and MS2 analysis.

    Displays calibration curves, concentration tables, MS2 spectra,
    and integration controls.
    """

    # Signals to communicate with controller
    calibration_requested = QtCore.Signal()
    compound_changed = QtCore.Signal(int)
    ms2_file_changed = QtCore.Signal(int)

    def __init__(self, parent=None, mode="LC/GC-MS"):
        super().__init__(parent)
        self._current_mode = mode

        # State
        self.file_concentrations = None

        # Initialize the main layout
        self._main_layout = QtWidgets.QGridLayout(self)

        # Setup initial UI
        self.setup_layout(mode)

    @property
    def mode(self):
        """Current mode."""
        return self._current_mode

    # --- TabBase Implementation ---

    def _connect_controller_signals(self):
        """Connect signals to controller after injection."""
        if self._controller is None:
            return
        # Signals are connected externally by controller

    def clear(self):
        """Clear all data from the tab."""
        if hasattr(self, 'unifiedResultsTable'):
            self.unifiedResultsTable.clearContents()
            self.unifiedResultsTable.setRowCount(0)
        if hasattr(self, 'canvas_calibration'):
            self.canvas_calibration.clear()
        if hasattr(self, 'canvas_ms2'):
            self.canvas_ms2.clear()
        if hasattr(self, 'canvas_library_ms2'):
            self.canvas_library_ms2.clear()
        if hasattr(self, 'comboBoxChooseCompound'):
            self.comboBoxChooseCompound.clear()
            self.comboBoxChooseCompound.setEnabled(False)
        if hasattr(self, 'comboBoxChooseMS2File'):
            self.comboBoxChooseMS2File.clear()
        self.file_concentrations = None

    def setup_layout(self, mode: str = None):
        """
        Build or rebuild the layout for the given mode.

        Parameters
        ----------
        mode : str, optional
            The application mode (e.g., "LC/GC-MS", "MS Only", "LC/GC Only")
        """
        if mode is not None:
            self._current_mode = mode

        # Clear existing layout
        self._clear_layout()

        # Build the UI
        self._build_ui()

        # Connect widget signals
        self._connect_widget_signals()

    def _clear_layout(self):
        """Clear all widgets from the layout."""
        for i in reversed(range(self._main_layout.count())):
            item = self._main_layout.itemAt(i)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                nested_layout = item.layout()
                if nested_layout is not None:
                    self._clear_nested_layout(nested_layout)

    def _clear_nested_layout(self, layout):
        """Recursively clear a nested layout."""
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                nested = item.layout()
                if nested is not None:
                    self._clear_nested_layout(nested)

    def _build_ui(self):
        """Build the quantitation tab UI."""
        # Main quant layout
        self.gridLayout_quant = QtWidgets.QGridLayout()
        self.gridLayout_quant.setSizeConstraint(
            QtWidgets.QLayout.SizeConstraint.SetDefaultConstraint
        )
        self.gridLayout_quant.setObjectName("gridLayout_quant")
        self.gridLayout_quant.setColumnStretch(0, 1)
        self.gridLayout_quant.setColumnStretch(1, 1)
        self.gridLayout_quant.setRowStretch(0, 1)
        self.gridLayout_quant.setRowStretch(1, 1)
        self.gridLayout_quant.setRowStretch(2, 1)
        self.gridLayout_quant.setRowStretch(3, 1)

        # Top left layout (calibration controls + results table)
        self.gridLayout_top_left = QtWidgets.QGridLayout()
        self.gridLayout_top_left.setObjectName("gridLayout_top_left")

        # Calibration setup
        self.label_calibrate = QtWidgets.QLabel(
            "Select files with known concentrations and click Calibrate:"
        )
        self.label_calibrate.setWordWrap(True)
        self.label_calibrate.setObjectName("label_calibrate")
        self.label_calibrate.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Fixed
        )
        self.gridLayout_top_left.addWidget(self.label_calibrate, 0, 0, 1, 1)

        self.calibrateButton = QtWidgets.QPushButton("Calibrate")
        self.calibrateButton.setObjectName("calibrateButton")
        self.calibrateButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Fixed
        )
        self.gridLayout_top_left.addWidget(self.calibrateButton, 0, 1, 1, 1)

        # Unified results table
        self.unifiedResultsTable = UnifiedResultsTable(parent=self)
        self.unifiedResultsTable.setObjectName("unifiedResultsTable")
        self.gridLayout_top_left.addWidget(self.unifiedResultsTable, 1, 0, 2, 2)

        self.gridLayout_quant.addLayout(self.gridLayout_top_left, 0, 0, 3, 1)

        # Top right layout (compound selection + calibration curve)
        self.gridLayout_top_right = QtWidgets.QGridLayout()
        self.gridLayout_top_right.setObjectName("gridLayout_top_right")

        self.label_compound = QtWidgets.QLabel("Compound:")
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Preferred
        )
        self.label_compound.setSizePolicy(sizePolicy)
        self.label_compound.setObjectName("label_compound")
        self.gridLayout_top_right.addWidget(self.label_compound, 0, 0, 1, 1)

        self.comboBoxChooseCompound = QtWidgets.QComboBox()
        self.comboBoxChooseCompound.setMinimumSize(QtCore.QSize(0, 32))
        self.comboBoxChooseCompound.setObjectName("comboBoxChooseCompound")
        self.comboBoxChooseCompound.setEnabled(False)
        self.gridLayout_top_right.addWidget(self.comboBoxChooseCompound, 0, 1, 1, 2)

        self.canvas_calibration = pg.PlotWidget()
        self.canvas_calibration.setObjectName("canvas_calibration")
        self.gridLayout_top_right.addWidget(self.canvas_calibration, 1, 0, 1, 3)

        self.gridLayout_quant.addLayout(self.gridLayout_top_right, 0, 1, 1, 2)

        # MS2 file selection
        self.comboBoxChooseMS2File = QtWidgets.QComboBox()
        self.comboBoxChooseMS2File.setObjectName("comboBoxChooseMS2File")
        self.gridLayout_quant.addWidget(self.comboBoxChooseMS2File, 1, 1, 1, 2)

        # MS2 canvas
        self.canvas_ms2 = pg.PlotWidget()
        self.canvas_ms2.setObjectName("canvas_ms2")
        self.canvas_ms2.setMouseEnabled(x=True, y=False)
        self.canvas_ms2.getPlotItem().getViewBox().enableAutoRange(axis="y")
        self.canvas_ms2.getPlotItem().getViewBox().setAutoVisible(y=True)
        self.canvas_ms2.getPlotItem().getViewBox().sigRangeChangedManually.connect(
            lambda ev: update_labels_avgMS(self.canvas_ms2)
        )
        self.gridLayout_quant.addWidget(self.canvas_ms2, 2, 1, 1, 2)

        # Library MS2 / Integration canvas
        self.canvas_library_ms2 = pg.PlotWidget()
        self.canvas_library_ms2.setObjectName("canvas_library_ms2")
        self.canvas_library_ms2.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum
        )
        self.canvas_library_ms2.setMouseEnabled(x=True, y=False)
        self.canvas_library_ms2.getPlotItem().getViewBox().enableAutoRange(axis="y")
        self.canvas_library_ms2.getPlotItem().getViewBox().setAutoVisible(y=True)
        self.gridLayout_quant.addWidget(self.canvas_library_ms2, 3, 0, 1, 3)

        # Integration control buttons
        self.button_apply_integration = QtWidgets.QPushButton("Apply Integration Changes")
        self.button_recalculate_integration = QtWidgets.QPushButton("Recalculate All")
        self.button_reset_integration = QtWidgets.QPushButton("Reset Integration")

        self.gridLayout_quant.addWidget(self.button_apply_integration, 4, 0, 1, 1)
        self.gridLayout_quant.addWidget(self.button_recalculate_integration, 4, 1, 1, 1)
        self.gridLayout_quant.addWidget(self.button_reset_integration, 4, 2, 1, 1)

        # Add quant layout to main layout
        self._main_layout.addLayout(self.gridLayout_quant, 0, 0, 1, 1)

    def _connect_widget_signals(self):
        """Connect widget signals."""
        self.comboBoxChooseCompound.currentIndexChanged.connect(
            self._on_compound_changed
        )
        self.comboBoxChooseMS2File.currentIndexChanged.connect(
            self._on_ms2_file_changed
        )
        # Connect compound selection to update the unified table
        self.comboBoxChooseCompound.currentIndexChanged.connect(
            self.update_unified_table_for_compound
        )
        # Connect unified table selection to display MS2 data
        self.unifiedResultsTable.selectionModel().selectionChanged.connect(
            self.display_ms2
        )

    def _on_compound_changed(self, index):
        """Internal handler for compound selection change."""
        self.compound_changed.emit(index)

    def _on_ms2_file_changed(self, index):
        """Internal handler for MS2 file selection change."""
        self.ms2_file_changed.emit(index)

    # --- Data Display Methods ---

    def update_table_quantitation(self, concentrations):
        """
        Update the unified results table with file concentrations.

        Parameters
        ----------
        concentrations : list
            List of [filename, concentration] pairs
        """
        self.file_concentrations = concentrations
        self.update_unified_table_for_compound()

    def update_unified_table_for_compound(self):
        """Update the unified table based on the currently selected compound."""
        if not self.file_concentrations:
            return

        # Get the currently selected compound
        current_compound = None
        if (
            self._controller
            and hasattr(self._controller, "model")
            and hasattr(self._controller.model, "compounds")
            and self._controller.model.compounds
            and self.comboBoxChooseCompound.currentIndex() >= 0
        ):
            current_compound = self._controller.model.compounds[
                self.comboBoxChooseCompound.currentIndex()
            ]

            # Setup columns for the current compound
            self.unifiedResultsTable.setup_columns(current_compound)

            # Get MS measurements if available
            ms_measurements = getattr(self._controller.model, "ms_measurements", {})

            # Populate the table with data for the current compound
            self.unifiedResultsTable.populate_data(
                self.file_concentrations, ms_measurements, current_compound
            )
        else:
            # Fallback: just setup basic columns without compound data
            self.unifiedResultsTable.setColumnCount(3)
            self.unifiedResultsTable.setHorizontalHeaderLabels(
                ["File", "Calibration", "Concentration"]
            )
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

    def update_choose_compound(self, compounds):
        """
        Update the compound selection combo box.

        Parameters
        ----------
        compounds : list
            List of Compound objects
        """
        self.comboBoxChooseCompound.clear()
        for compound in compounds:
            self.comboBoxChooseCompound.addItem(compound.name)

    def get_calibration_files(self):
        """
        Get calibration files from the unified results table.

        Returns
        -------
        list
            List of selected calibration files
        """
        return self.unifiedResultsTable.get_calibration_files()

    def display_calibration_curve(self):
        """Display the calibration curve for the selected compound."""
        self.canvas_calibration.clear()
        self.canvas_calibration.getPlotItem().vb.enableAutoRange(axis="y", enable=True)
        self.canvas_calibration.getPlotItem().vb.enableAutoRange(axis="x", enable=True)
        self.canvas_calibration.getPlotItem().vb.setAutoVisible(x=True, y=True)

        if not self._controller:
            return

        for compound in self._controller.model.compounds:
            if compound.name == self.comboBoxChooseCompound.currentText():
                try:
                    plot_calibration_curve(compound, self.canvas_calibration)
                except TypeError:
                    logger.error(
                        f"No calibration curve found for {compound.name}: {traceback.format_exc()}"
                    )

    def display_concentrations(self):
        """
        Display concentrations. Handled by the unified results table.
        """
        # The unified table automatically shows concentrations
        pass

    def display_compound_integration(self):
        """Display compound integration boundaries."""
        selected_file = self.unifiedResultsTable.get_selected_file()
        if not selected_file:
            try:
                selected_file = self.unifiedResultsTable.itemAt(0, 0)
            except Exception as e:
                logger.error(e)
                return

        if not self._controller:
            return

        ms_file = self._controller.model.ms_measurements.get(selected_file)
        try:
            ms_compound = next(
                xic
                for xic in ms_file.xics
                if xic.name == self.comboBoxChooseCompound.currentText()
            )
            plot_compound_integration(self.canvas_library_ms2, ms_compound)
        except (AttributeError, StopIteration):
            logger.warning(f"No MS data found for {selected_file}.")

    def display_ms2(self):
        """Display MS2 data for the selected file."""
        selected_file = self.unifiedResultsTable.get_selected_file()
        if not selected_file:
            logger.error("No file selected for MS2 display")
            plot_no_ms2_found(self.canvas_ms2)
            return

        if not self._controller:
            return

        ms_file = self._controller.model.ms_measurements.get(selected_file)
        if ms_file is None:
            logger.error(f"No MS file found for {selected_file}")
            plot_no_ms2_found(self.canvas_ms2)
            return

        try:
            self._controller.model.find_ms2_in_file(ms_file)
            compound = next(
                (
                    xic
                    for xic in ms_file.xics
                    if xic.name == self.comboBoxChooseCompound.currentText()
                ),
                None,
            )
            precursor = float(
                self.comboBoxChooseMS2File.currentText()
                .split("m/z ")[1]
                .replace("(", "")
                .replace(")", "")
            )
            plot_ms2_from_file(ms_file, compound, precursor, self.canvas_ms2)
        except Exception:
            logger.error(
                f"No MS2 found for {self.comboBoxChooseMS2File.currentText()}: "
                f"{traceback.format_exc()}"
            )
            plot_no_ms2_found(self.canvas_ms2)

    def get_integration_bounds(self, canvas=None) -> dict[str, tuple[float, float]]:
        """
        Retrieve integration bounds for each ion.

        Parameters
        ----------
        canvas : pg.PlotWidget, optional
            The canvas to get bounds from. Defaults to canvas_library_ms2.

        Returns
        -------
        dict
            Dictionary mapping ion_key to (left, right) bounds tuple.
        """
        if canvas is None:
            canvas = self.canvas_library_ms2

        plot_item = canvas.getPlotItem()
        bounds = {}

        for item in plot_item.items:
            if isinstance(item, pg.InfiniteLine):
                name = item.name()
                if name and name.endswith("_left"):
                    ion_key = name[:-5]
                    if ion_key not in bounds:
                        bounds[ion_key] = {}
                    bounds[ion_key]["left"] = item.value()
                elif name and name.endswith("_right"):
                    ion_key = name[:-6]
                    if ion_key not in bounds:
                        bounds[ion_key] = {}
                    bounds[ion_key]["right"] = item.value()

        # Convert to sorted tuples
        result = {}
        for ion_key, b in bounds.items():
            if "left" in b and "right" in b:
                result[ion_key] = (
                    min(b["left"], b["right"]),
                    max(b["left"], b["right"]),
                )
        return result
