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
    plot_ms2_spectrum,
    plot_no_ms2_found,
    plot_no_ms_info,
    update_labels_avgMS,
)
from calculation.workers import MS2LookupWorker

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

    def __init__(self, parent=None, mode="LC/GC-MS"):
        super().__init__(parent)
        self._current_mode = mode

        # State
        self.file_concentrations = None
        self._selected_ion = None  # Track currently selected ion for manual integration
        self._curve_refs = {}  # Store references to curves for click handling
        self._ms2_worker = None  # Current MS2 lookup worker
        self._ms2_lookup_id = 0  # Monotonic counter for stale result rejection

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
        if hasattr(self, "unifiedResultsTable"):
            try:
                self.unifiedResultsTable.clearContents()
                self.unifiedResultsTable.setRowCount(0)
            except RuntimeError:
                pass  # Widget already deleted
        if hasattr(self, "canvas_calibration"):
            try:
                self.canvas_calibration.clear()
            except RuntimeError:
                pass  # Widget already deleted
        if hasattr(self, "canvas_ms2"):
            try:
                self.canvas_ms2.clear()
            except RuntimeError:
                pass  # Widget already deleted
        if hasattr(self, "canvas_library_ms2"):
            try:
                self.canvas_library_ms2.clear()
            except RuntimeError:
                pass  # Widget already deleted
        if hasattr(self, "comboBoxChooseCompound"):
            try:
                self.comboBoxChooseCompound.clear()
                self.comboBoxChooseCompound.setEnabled(False)
            except RuntimeError:
                pass  # Widget already deleted
        if hasattr(self, "comboBoxMS2Ion"):
            try:
                self.comboBoxMS2Ion.clear()
            except RuntimeError:
                pass  # Widget already deleted
        if hasattr(self, "comboBoxChooseFile"):
            try:
                self.comboBoxChooseFile.clear()
            except RuntimeError:
                pass  # Widget already deleted
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
        # Row stretches shifted down by 1 for header row
        self.gridLayout_quant.setRowStretch(1, 1)
        self.gridLayout_quant.setRowStretch(2, 1)
        self.gridLayout_quant.setRowStretch(3, 1)
        self.gridLayout_quant.setRowStretch(4, 1)

        # --- Header layout with prominent file/compound selection (Row 0) ---
        self.header_layout = QtWidgets.QHBoxLayout()

        # File selector
        self.label_file = QtWidgets.QLabel("File:")
        self.label_file.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.comboBoxChooseFile = QtWidgets.QComboBox()
        self.comboBoxChooseFile.setMinimumSize(QtCore.QSize(200, 32))
        self.comboBoxChooseFile.setObjectName("comboBoxChooseFile")

        # Compound selector (prominent in header)
        self.label_compound = QtWidgets.QLabel("Compound:")
        self.label_compound.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.comboBoxChooseCompound = QtWidgets.QComboBox()
        self.comboBoxChooseCompound.setMinimumSize(QtCore.QSize(200, 32))
        self.comboBoxChooseCompound.setObjectName("comboBoxChooseCompound")
        self.comboBoxChooseCompound.setEnabled(False)

        self.header_layout.addWidget(self.label_file)
        self.header_layout.addWidget(self.comboBoxChooseFile)
        self.header_layout.addSpacing(20)
        self.header_layout.addWidget(self.label_compound)
        self.header_layout.addWidget(self.comboBoxChooseCompound)
        self.header_layout.addStretch()

        self.gridLayout_quant.addLayout(self.header_layout, 0, 0, 1, 3)

        # --- Top left layout (calibration controls + results table) (Row 1-3) ---
        self.gridLayout_top_left = QtWidgets.QGridLayout()
        self.gridLayout_top_left.setObjectName("gridLayout_top_left")

        # Calibration setup
        self.label_calibrate = QtWidgets.QLabel(
            "Select files with known concentrations and click Calibrate:"
        )
        self.label_calibrate.setWordWrap(True)
        self.label_calibrate.setObjectName("label_calibrate")
        self.label_calibrate.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed
        )
        self.gridLayout_top_left.addWidget(self.label_calibrate, 0, 0, 1, 1)

        self.calibrateButton = QtWidgets.QPushButton("Calibrate")
        self.calibrateButton.setObjectName("calibrateButton")
        self.calibrateButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed
        )
        self.calibrateButton.setEnabled(False)
        self.calibrateButton.setToolTip("Enter concentrations for at least 2 files (0/2)")
        self.gridLayout_top_left.addWidget(self.calibrateButton, 0, 1, 1, 1)

        # Unified results table
        self.unifiedResultsTable = UnifiedResultsTable(parent=self)
        self.unifiedResultsTable.setObjectName("unifiedResultsTable")
        self.gridLayout_top_left.addWidget(self.unifiedResultsTable, 1, 0, 2, 2)

        self.gridLayout_quant.addLayout(self.gridLayout_top_left, 1, 0, 3, 1)

        # --- Top right layout (calibration curve) (Row 1) ---
        self.gridLayout_top_right = QtWidgets.QGridLayout()
        self.gridLayout_top_right.setObjectName("gridLayout_top_right")

        self.canvas_calibration = pg.PlotWidget()
        self.canvas_calibration.setObjectName("canvas_calibration")
        self.gridLayout_top_right.addWidget(self.canvas_calibration, 0, 0, 1, 3)

        self.gridLayout_quant.addLayout(self.gridLayout_top_right, 1, 1, 1, 2)

        # MS2 ion selection + status label (Row 2)
        self.ms2_header_layout = QtWidgets.QHBoxLayout()
        self.label_ms2_ion = QtWidgets.QLabel("MS2 Ion:")
        self.label_ms2_ion.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.comboBoxMS2Ion = QtWidgets.QComboBox()
        self.comboBoxMS2Ion.setMinimumSize(QtCore.QSize(200, 28))
        self.comboBoxMS2Ion.setObjectName("comboBoxMS2Ion")
        self.label_ms2_status = QtWidgets.QLabel("")
        self.label_ms2_status.setStyleSheet("color: #666666; font-style: italic;")
        self.ms2_header_layout.addWidget(self.label_ms2_ion)
        self.ms2_header_layout.addWidget(self.comboBoxMS2Ion)
        self.ms2_header_layout.addWidget(self.label_ms2_status)
        self.ms2_header_layout.addStretch()
        self.gridLayout_quant.addLayout(self.ms2_header_layout, 2, 1, 1, 2)

        # MS2 canvas (Row 3)
        self.canvas_ms2 = pg.PlotWidget()
        self.canvas_ms2.setObjectName("canvas_ms2")
        self.canvas_ms2.setMouseEnabled(x=True, y=False)
        self.canvas_ms2.getPlotItem().getViewBox().enableAutoRange(axis="y")
        self.canvas_ms2.getPlotItem().getViewBox().setAutoVisible(y=True)
        self.canvas_ms2.getPlotItem().getViewBox().sigRangeChangedManually.connect(
            lambda ev: update_labels_avgMS(self.canvas_ms2)
        )
        self.gridLayout_quant.addWidget(self.canvas_ms2, 3, 1, 1, 2)

        # Library MS2 / Integration canvas (Row 4)
        self.canvas_library_ms2 = pg.PlotWidget()
        self.canvas_library_ms2.setObjectName("canvas_library_ms2")
        self.canvas_library_ms2.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum
        )
        self.canvas_library_ms2.setMouseEnabled(x=True, y=False)
        self.canvas_library_ms2.getPlotItem().getViewBox().enableAutoRange(axis="y")
        self.canvas_library_ms2.getPlotItem().getViewBox().setAutoVisible(y=True)
        self.gridLayout_quant.addWidget(self.canvas_library_ms2, 4, 0, 1, 3)

        # Ion selection for manual integration (Row 5)
        self.ion_selection_layout = QtWidgets.QHBoxLayout()
        self.label_select_ion = QtWidgets.QLabel("Ion to edit:")
        self.label_select_ion.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Preferred
        )
        self.comboBoxSelectIon = QtWidgets.QComboBox()
        self.comboBoxSelectIon.setMinimumSize(QtCore.QSize(250, 32))
        self.comboBoxSelectIon.setSizeAdjustPolicy(
            QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents
        )
        self.comboBoxSelectIon.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed
        )
        self.comboBoxSelectIon.addItem("-- Select ion --")
        self.comboBoxSelectIon.setToolTip(
            "Select an ion to enable manual integration boundary editing"
        )
        self.label_selected_ion_status = QtWidgets.QLabel("No ion selected")
        self.label_selected_ion_status.setStyleSheet(
            "color: #666666; font-style: italic;"
        )

        # Help icon with tooltip explaining integration workflow
        self.help_icon = QtWidgets.QLabel()
        help_pixmap = (
            self.style()
            .standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MessageBoxQuestion)
            .pixmap(QtCore.QSize(30, 30))
        )
        self.help_icon.setPixmap(help_pixmap)
        self.help_icon.setCursor(Qt.CursorShape.WhatsThisCursor)
        self.help_icon.setToolTip(
            "<b>Manual Integration</b><br>"
            "The integration boundaries can be manually adjusted for each ion of the selected compound.<br><br>"
            "1. Select an ion from the dropdown or click on a curve<br>"
            "2. Drag the boundary lines to adjust integration limits<br>"
            "3. Click <b>Apply</b> to save changes for this file<br>"
            "4. Click <b>Recalculate All</b> to apply same boundaries to all files<br>"
            "5. Click <b>Reset</b> to restore automatic integration"
        )

        self.ion_selection_layout.addWidget(self.label_select_ion)
        self.ion_selection_layout.addWidget(self.comboBoxSelectIon)
        self.ion_selection_layout.addWidget(self.label_selected_ion_status)
        self.ion_selection_layout.addWidget(self.help_icon)
        self.ion_selection_layout.addStretch()

        self.gridLayout_quant.addLayout(self.ion_selection_layout, 5, 0, 1, 3)

        # Integration control buttons (Row 6)
        self.button_apply_integration = QtWidgets.QPushButton("Apply changes")
        self.button_recalculate_integration = QtWidgets.QPushButton("Recalculate all")
        self.button_reset_integration = QtWidgets.QPushButton("Reset integration")

        self.gridLayout_quant.addWidget(self.button_apply_integration, 6, 0, 1, 1)
        self.gridLayout_quant.addWidget(self.button_recalculate_integration, 6, 1, 1, 1)
        self.gridLayout_quant.addWidget(self.button_reset_integration, 6, 2, 1, 1)

        # Add quant layout to main layout
        self._main_layout.addLayout(self.gridLayout_quant, 0, 0, 1, 1)

    def _connect_widget_signals(self):
        """Connect widget signals."""
        self.comboBoxChooseCompound.currentIndexChanged.connect(
            self._on_compound_changed
        )
        # Connect compound selection to update the unified table
        self.comboBoxChooseCompound.currentIndexChanged.connect(
            self.update_unified_table_for_compound
        )
        # Monitor concentration inputs for calibrate button state
        self.unifiedResultsTable.itemChanged.connect(self._on_table_item_changed)
        # MS2 ion combo triggers lookup
        self.comboBoxMS2Ion.currentIndexChanged.connect(self._trigger_ms2_lookup)
        # Update MS2 ion combo when compound changes
        self.comboBoxChooseCompound.currentIndexChanged.connect(
            self._update_ms2_ion_combo
        )
        # Update MS2 lookup when table selection (file) changes
        self.unifiedResultsTable.selectionModel().selectionChanged.connect(
            self._trigger_ms2_lookup
        )
        # Connect ion selection combo box
        self.comboBoxSelectIon.currentIndexChanged.connect(
            self._on_ion_selection_changed
        )
        # Update ion combo box when compound changes
        self.comboBoxChooseCompound.currentIndexChanged.connect(
            self._update_ion_combo_box
        )
        # Update ion combo box when file selection changes
        self.unifiedResultsTable.selectionModel().selectionChanged.connect(
            self._update_ion_combo_box
        )
        # File combo box <-> table selection bidirectional sync
        self.comboBoxChooseFile.currentTextChanged.connect(self._on_file_combo_changed)
        self.unifiedResultsTable.selectionModel().selectionChanged.connect(
            self._sync_file_combo_from_table
        )
        # Update integration plot when file selection changes
        self.unifiedResultsTable.selectionModel().selectionChanged.connect(
            self.display_compound_integration
        )

    def _on_compound_changed(self, index):
        """Internal handler for compound selection change."""
        self.compound_changed.emit(index)

    def _on_file_combo_changed(self, filename: str):
        """Handle file selection from combo box - select matching table row."""
        if not filename:
            return
        # Find and select the matching row in the table
        for row in range(self.unifiedResultsTable.rowCount()):
            item = self.unifiedResultsTable.item(row, 0)
            if item and item.text() == filename:
                self.unifiedResultsTable.selectRow(row)
                break

    def _sync_file_combo_from_table(self):
        """Sync file combo box when table selection changes."""
        selected_file = self.unifiedResultsTable.get_selected_file()
        if selected_file:
            self.comboBoxChooseFile.blockSignals(True)
            index = self.comboBoxChooseFile.findText(selected_file)
            if index >= 0:
                self.comboBoxChooseFile.setCurrentIndex(index)
            self.comboBoxChooseFile.blockSignals(False)

    def _on_table_item_changed(self, item):
        """Handle table item changes to monitor concentration inputs."""
        if item.column() == 1:  # Concentration column
            self._update_calibrate_button_state()

    def _update_calibrate_button_state(self):
        """Enable/disable calibrate button based on valid calibration file count."""
        calibration_files = self.unifiedResultsTable.get_calibration_files()
        valid_count = sum(1 for conc in calibration_files.values() if conc and conc.strip())
        self.calibrateButton.setEnabled(valid_count >= 2)
        if valid_count < 2:
            self.calibrateButton.setToolTip(f"Enter concentrations for at least 2 files ({valid_count}/2)")
        else:
            self.calibrateButton.setToolTip(f"Calibrate using {valid_count} files")

    def get_selected_ion(self) -> str | None:
        """
        Get the currently selected ion key for manual integration.

        Returns
        -------
        str or None
            The ion key (e.g., "123.456") or None if no ion is selected.
        """
        return self._selected_ion

    def _update_ion_combo_box(self):
        """Update the ion selection combo box based on current compound and file."""
        self.comboBoxSelectIon.blockSignals(True)
        self.comboBoxSelectIon.clear()
        self.comboBoxSelectIon.addItem("-- Select ion --")

        if not self._controller:
            self.comboBoxSelectIon.blockSignals(False)
            return

        # Get current compound
        compound_idx = self.comboBoxChooseCompound.currentIndex()
        if compound_idx < 0 or not self._controller.model.compounds:
            self.comboBoxSelectIon.blockSignals(False)
            return

        compound = self._controller.model.compounds[compound_idx]

        # Get ion info for display
        ion_keys = list(compound.ions.keys())
        ion_info_list = getattr(compound, "ion_info", [])

        for i, ion_key in enumerate(ion_keys):
            info_str = ion_info_list[i] if i < len(ion_info_list) else ""
            display_text = f"{ion_key}"
            if info_str:
                display_text += f" ({info_str})"
            self.comboBoxSelectIon.addItem(display_text, userData=str(ion_key))

        # Reset selection state
        self._selected_ion = None
        self.label_selected_ion_status.setText("No ion selected")
        self.label_selected_ion_status.setStyleSheet(
            "color: #666666; font-style: italic;"
        )

        self.comboBoxSelectIon.blockSignals(False)

    def _on_ion_selection_changed(self, index):
        """Handle ion selection change from combo box."""
        if index <= 0:
            # "-- Select ion --" or invalid
            self._selected_ion = None
            self.label_selected_ion_status.setText("No ion selected")
            self.label_selected_ion_status.setStyleSheet(
                "color: #666666; font-style: italic;"
            )
        else:
            ion_key = self.comboBoxSelectIon.itemData(index)
            self._selected_ion = ion_key
            self.label_selected_ion_status.setText(f"Editing: {ion_key}")
            self.label_selected_ion_status.setStyleSheet(
                "color: #2EC4B6; font-weight: bold;"
            )

        # Refresh the integration plot with new selection
        self.display_compound_integration()

    def _on_curve_clicked(self, ion_key: str):
        """Handle click on an integration curve to select that ion."""
        # Find the combo box index for this ion
        for i in range(1, self.comboBoxSelectIon.count()):
            if self.comboBoxSelectIon.itemData(i) == ion_key:
                self.comboBoxSelectIon.setCurrentIndex(i)
                break

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
            self.unifiedResultsTable.setColumnCount(2)
            self.unifiedResultsTable.setHorizontalHeaderLabels(["File", "Concentration"])
            self.unifiedResultsTable.setRowCount(len(self.file_concentrations))

            for row, (filename, concentration) in enumerate(self.file_concentrations):
                # File name
                file_item = QtWidgets.QTableWidgetItem(filename)
                file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.unifiedResultsTable.setItem(row, 0, file_item)

                # Concentration
                conc_item = QtWidgets.QTableWidgetItem(concentration or "")
                self.unifiedResultsTable.setItem(row, 1, conc_item)

        self._update_calibrate_button_state()

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

    def update_file_combo_box(self, filenames: list[str]):
        """
        Update the file selection combo box with available files.

        Parameters
        ----------
        filenames : list[str]
            List of filenames to populate the combo box
        """
        self.comboBoxChooseFile.blockSignals(True)
        self.comboBoxChooseFile.clear()
        for filename in filenames:
            self.comboBoxChooseFile.addItem(filename)
        self.comboBoxChooseFile.blockSignals(False)

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

        compound_name = self.comboBoxChooseCompound.currentText()
        # Set dynamic title showing compound name
        self.canvas_calibration.setTitle(
            f"Calibration: {compound_name}",
            color="w",
            size="11pt",
        )

        for compound in self._controller.model.compounds:
            if compound.name == compound_name:
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

        compound_name = self.comboBoxChooseCompound.currentText()
        # Set dynamic title showing file and compound
        self.canvas_library_ms2.setTitle(
            f"Integration profile of {compound_name} in {selected_file}",
            color="w",
            size="12pt",
        )

        ms_file = self._controller.model.ms_measurements.get(selected_file)
        if ms_file is None:
            plot_no_ms_info(self.canvas_library_ms2)
            return

        try:
            ms_compound = next(xic for xic in ms_file.xics if xic.name == compound_name)
            # Pass selected ion to enable selective movability
            self._curve_refs = plot_compound_integration(
                self.canvas_library_ms2, ms_compound, selected_ion=self._selected_ion
            )
            # Connect curve click signals for click-to-select
            self._connect_curve_click_signals()
        except (AttributeError, StopIteration):
            logger.warning(f"No MS data found for {selected_file}.")
            plot_no_ms_info(self.canvas_library_ms2)

    def _connect_curve_click_signals(self):
        """Connect sigClicked signals on curves for click-to-select functionality."""
        for ion_key, curve in self._curve_refs.items():
            try:
                # Disconnect any previous connections
                try:
                    curve.sigClicked.disconnect()
                except (TypeError, RuntimeError):
                    pass  # Not connected or already deleted

                # Connect with a closure to capture ion_key
                def make_handler(key):
                    def handler(curve_item, ev):
                        self._on_curve_clicked(key)

                    return handler

                curve.sigClicked.connect(make_handler(ion_key))
            except Exception as e:
                logger.warning(f"Failed to connect click signal for {ion_key}: {e}")

    def _update_ms2_ion_combo(self):
        """Populate the MS2 ion combo box with ions of the current compound."""
        self.comboBoxMS2Ion.blockSignals(True)
        self.comboBoxMS2Ion.clear()

        if not self._controller:
            self.comboBoxMS2Ion.blockSignals(False)
            return

        compound_idx = self.comboBoxChooseCompound.currentIndex()
        if compound_idx < 0 or not self._controller.model.compounds:
            self.comboBoxMS2Ion.blockSignals(False)
            return

        compound = self._controller.model.compounds[compound_idx]
        ion_keys = list(compound.ions.keys())
        ion_info_list = getattr(compound, "ion_info", [])

        for i, ion_key in enumerate(ion_keys):
            info_str = ion_info_list[i] if i < len(ion_info_list) else ""
            display_text = f"{ion_key}"
            if info_str:
                display_text += f" ({info_str})"
            self.comboBoxMS2Ion.addItem(display_text, userData=float(ion_key))

        self.comboBoxMS2Ion.blockSignals(False)

        # Auto-trigger lookup for the first ion
        if self.comboBoxMS2Ion.count() > 0:
            self._trigger_ms2_lookup()

    def _trigger_ms2_lookup(self):
        """Cancel any pending MS2 worker and start a new lookup."""
        # Cancel previous worker
        if self._ms2_worker is not None:
            self._ms2_worker.cancel()
            self._ms2_worker = None

        if not self._controller:
            return

        selected_file = self.unifiedResultsTable.get_selected_file()
        if not selected_file:
            return

        ms_file = self._controller.model.ms_measurements.get(selected_file)
        if ms_file is None:
            plot_no_ms2_found(self.canvas_ms2)
            return

        if self.comboBoxMS2Ion.currentIndex() < 0:
            return

        precursor_mz = self.comboBoxMS2Ion.currentData()
        if precursor_mz is None:
            return

        # Get target RT from compound XIC data
        compound_name = self.comboBoxChooseCompound.currentText()
        compound = ms_file.get_compound_by_name(compound_name)
        if compound is None:
            plot_no_ms2_found(self.canvas_ms2)
            return

        # Use the ion's RT as target
        ion_data = compound.ions.get(precursor_mz)
        if ion_data is None:
            # Try matching as string
            for key, val in compound.ions.items():
                if str(key) == str(precursor_mz):
                    ion_data = val
                    break
        target_rt = ion_data.get("RT", 0) if ion_data else 0
        if target_rt is None or target_rt == 0:
            # Fallback: use the first scan time
            target_rt = 0

        self._ms2_lookup_id += 1
        lookup_id = self._ms2_lookup_id

        self.label_ms2_status.setText("Searching...")
        self.label_ms2_status.setStyleSheet("color: #0b81a2; font-style: italic;")

        worker = MS2LookupWorker(
            ms_file.path, precursor_mz, target_rt
        )
        worker.finished.connect(lambda result, lid=lookup_id: self._on_ms2_found(result, lid))
        worker.error.connect(lambda msg, lid=lookup_id: self._on_ms2_error(msg, lid))
        self._ms2_worker = worker
        worker.start()

    def _on_ms2_found(self, result, lookup_id):
        """Handle MS2 lookup result. Ignores stale results."""
        if lookup_id != self._ms2_lookup_id:
            return  # Stale result

        if result is None:
            self.label_ms2_status.setText("No MS2 found")
            self.label_ms2_status.setStyleSheet("color: #999999; font-style: italic;")
            plot_no_ms2_found(self.canvas_ms2)
            return

        scan_time, mz_array, intensity_array = result
        self.label_ms2_status.setText(f"Found at RT {scan_time:.2f} min")
        self.label_ms2_status.setStyleSheet("color: #2EC4B6; font-weight: bold;")

        compound_name = self.comboBoxChooseCompound.currentText()
        ion_text = self.comboBoxMS2Ion.currentText()
        title = f"MS2 of {compound_name} ({ion_text}) at RT {scan_time:.2f} min"
        plot_ms2_spectrum(self.canvas_ms2, mz_array, intensity_array, title=title)

    def _on_ms2_error(self, error_msg, lookup_id):
        """Handle MS2 lookup error. Ignores stale results."""
        if lookup_id != self._ms2_lookup_id:
            return
        self.label_ms2_status.setText(f"Error: {error_msg}")
        self.label_ms2_status.setStyleSheet("color: #e25759; font-style: italic;")
        plot_no_ms2_found(self.canvas_ms2)

    def get_integration_bounds(
        self, canvas=None, ion_key: str = None
    ) -> dict[str, tuple[float, float]]:
        """
        Retrieve integration bounds for each ion.

        Parameters
        ----------
        canvas : pg.PlotWidget, optional
            The canvas to get bounds from. Defaults to canvas_library_ms2.
        ion_key : str, optional
            If provided, only return bounds for this specific ion.

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
                    current_ion_key = name[:-5]
                    # Filter by ion_key if provided
                    if ion_key is not None and current_ion_key != ion_key:
                        continue
                    if current_ion_key not in bounds:
                        bounds[current_ion_key] = {}
                    bounds[current_ion_key]["left"] = item.value()
                elif name and name.endswith("_right"):
                    current_ion_key = name[:-6]
                    # Filter by ion_key if provided
                    if ion_key is not None and current_ion_key != ion_key:
                        continue
                    if current_ion_key not in bounds:
                        bounds[current_ion_key] = {}
                    bounds[current_ion_key]["right"] = item.value()

        # Convert to sorted tuples
        result = {}
        for key, b in bounds.items():
            if "left" in b and "right" in b:
                result[key] = (
                    min(b["left"], b["right"]),
                    max(b["left"], b["right"]),
                )
        return result
