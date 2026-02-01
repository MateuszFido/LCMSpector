"""
Upload Tab for file selection and configuration.
"""

from pathlib import Path
import logging
import json
import os
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt
import pyqtgraph as pg

from ui.tabs.base_tab import TabBase
from ui.widgets import (
    DragDropListWidget,
    CheckableDragDropListWidget,
    IonTable,
    ChromatogramPlotWidget,
    LabelledSlider,
)
from ui.plotting import plot_placeholder, update_labels_avgMS
from ui.utils import clear_layout, create_crosshair_lines, create_crosshair_proxy

logger = logging.getLogger(__name__)


class UploadTab(TabBase):
    """
    Handles file selection (LC, MS, Annotations) and configuration (Ion Lists, Mass Accuracy).

    Supports full layout rebuilding for mode switching between LC/GC-MS, MS Only, and LC/GC Only.
    """

    # --- Signals ---
    files_loaded = QtCore.Signal(str, list)  # (type, file_paths)
    process_requested = QtCore.Signal()
    mode_changed = QtCore.Signal(str)

    def __init__(self, parent=None, mode="LC/GC-MS"):
        super().__init__(parent)
        self._current_mode = mode

        # Determine config path relative to the application root
        # Structure: lcmspector/ui/tabs/upload_tab.py -> lcmspector/config.json
        self.config_path = Path(__file__).resolve().parent.parent.parent / "config.json"

        # Initialize the main layout
        self._main_layout = QtWidgets.QGridLayout(self)

        # Crosshair elements (created once, reused across rebuilds)
        self.crosshair_v, self.crosshair_h, self.line_marker = create_crosshair_lines()
        self.crosshair_v_label = None
        self.crosshair_h_label = None
        self.proxy = None

        # Plot tracking for checkbox plotting feature
        self._lc_active_plots = {}  # {filename: PlotDataItem}
        self._ms_active_plots = {}  # {filename: PlotDataItem}
        self._tic_active_plots = {}  # {filename: PlotDataItem} - TIC plots in MS Only mode
        self._color_index_lc = 0
        self._color_index_ms = 0
        self._selected_lc_file = None  # Currently selected LC filename
        self._selected_ms_file = None  # Currently selected MS filename

        # Track main view plots separately (for selective clearing)
        self._main_view_plots = []  # PlotDataItems from click-to-view actions

        # Setup initial UI
        self.setup_layout(mode)

    @property
    def mode(self):
        """Current mode."""
        return self._current_mode

    # --- Public Accessors for Controller/View ---
    @property
    def process_button(self):
        """Access the process button widget."""
        return self.processButton

    @property
    def ion_table(self):
        """Access the ion table widget."""
        return self.ionTable

    @property
    def mass_accuracy(self):
        """Get the current mass accuracy value."""
        return self.mass_accuracy_slider.value()

    # --- TabBase Implementation ---

    def _connect_controller_signals(self):
        """Connect signals to controller after injection."""
        if self._controller is None:
            return

        # Connect process button to controller's process_data
        # Note: We don't disconnect existing connections as we rebuild layout
        pass  # Signals are connected in _connect_widget_signals during layout build

    def clear(self):
        """Clear all data from the tab."""
        if hasattr(self, "listLC"):
            try:
                self.listLC.clear()
            except RuntimeError:
                pass  # Widget already deleted
        if hasattr(self, "listMS"):
            try:
                self.listMS.clear()
            except RuntimeError:
                pass  # Widget already deleted
        if hasattr(self, "listAnnotations"):
            try:
                self.listAnnotations.clear()
            except RuntimeError:
                pass  # Widget already deleted
        if hasattr(self, "ionTable"):
            try:
                self.ionTable.clearContents()
                self.ionTable.setRowCount(0)
            except RuntimeError:
                pass  # Widget already deleted

        # Remove tracked plot items BEFORE clearing canvases
        # This ensures proper cleanup of any references
        if hasattr(self, "canvas_baseline"):
            try:
                # Remove LC overlay plots
                for filename, plot_item in list(self._lc_active_plots.items()):
                    try:
                        self.canvas_baseline.removeItem(plot_item)
                    except Exception:
                        pass  # Item may already be removed

                # Remove main view plots
                for plot_item in self._main_view_plots:
                    try:
                        self.canvas_baseline.removeItem(plot_item)
                    except Exception:
                        pass

                self.canvas_baseline.clear()
                plot_placeholder(
                    self.canvas_baseline,
                    '<p style="color: #c5c5c5">\n\u2190 Add files to get started</p>',
                )
            except RuntimeError:
                pass  # Widget already deleted

        if hasattr(self, "canvas_avgMS"):
            try:
                # Remove MS overlay plots
                for filename, (plot_item, _) in list(self._ms_active_plots.items()):
                    try:
                        if plot_item is not None:
                            self.canvas_avgMS.removeItem(plot_item)
                    except Exception:
                        pass  # Item may already be removed

                self.canvas_avgMS.clear()
                plot_placeholder(self.canvas_avgMS, "")
            except RuntimeError:
                pass  # Widget already deleted

        # Reset plot tracking state
        self._lc_active_plots.clear()
        self._ms_active_plots.clear()
        self._tic_active_plots.clear()
        self._color_index_lc = 0
        self._color_index_ms = 0
        self._selected_lc_file = None
        self._selected_ms_file = None
        self._main_view_plots = []

    def setup_layout(self, mode: str = None):
        """
        Completely rebuild layout for the given mode.

        This clears the existing layout and creates all widgets fresh,
        ensuring proper mode-specific UI configuration.

        Parameters
        ----------
        mode : str, optional
            The mode to build for. If None, uses current mode.
        """
        if mode is not None:
            self._current_mode = mode

        # Clear existing layout
        clear_layout(self._main_layout)

        # Clear stale widget references before building new layout
        # This prevents RuntimeError when accessing deleted C++ objects
        self._clear_stale_widget_refs()

        # Build mode-specific layout
        if self._current_mode == "LC/GC-MS":
            self._build_lcms_layout()
        elif self._current_mode == "MS Only":
            self._build_ms_only_layout()
        else:  # "LC/GC Only"
            self._build_chrom_only_layout()

        # Connect widget signals
        self._connect_widget_signals()

        # Load ion config and update list
        self._load_ion_config_names()
        self.update_ion_list()

    # --- Mode Handling ---

    def on_mode_changed(self, mode):
        """Handle mode change from combo box."""
        if mode == self._current_mode:
            return

        logger.info(f"Switching to {mode} mode.")
        self.setup_layout(mode)
        self.mode_changed.emit(mode)

        # Update controller mode if available
        if self._controller:
            self._controller.mode = mode

    def _clear_stale_widget_refs(self):
        """Remove stale widget attribute references to prevent RuntimeError.

        After clear_layout() deletes widgets via deleteLater(), the Python
        attributes still exist but point to deleted C++ objects. This causes
        RuntimeError when hasattr() returns True but the widget is unusable.
        """
        stale_attrs = [
            "listLC",
            "listMS",
            "listAnnotations",
            "browseLC",
            "browseMS",
            "browseAnnotations",
            "button_clear_LC",
            "button_clear_MS",
            "labelLCdata",
            "labelMSdata",
            "labelAnnotations",
            "canvas_baseline",
            "canvas_avgMS",
            "resultsPane",
            "help_icon_lc",
            "help_icon_ms",
        ]
        for attr in stale_attrs:
            if hasattr(self, attr):
                delattr(self, attr)

        # Clear TIC plot tracking on mode change
        self._tic_active_plots = {}

    # --- Layout Builders ---

    def _create_help_icon(self, tooltip_text: str) -> QtWidgets.QLabel:
        """Create a help icon with tooltip."""
        help_icon = QtWidgets.QLabel()
        help_pixmap = (
            self.style()
            .standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MessageBoxQuestion)
            .pixmap(QtCore.QSize(20, 20))
        )
        help_icon.setPixmap(help_pixmap)
        help_icon.setCursor(Qt.CursorShape.WhatsThisCursor)
        help_icon.setToolTip(tooltip_text)
        return help_icon

    def _build_common_widgets(self):
        """Create widgets common to all modes."""
        # Mode selection (added to outer layout by View, not here)
        # We create these widgets but View positions them

        # Ion table and controls
        self.labelIonList = QtWidgets.QLabel("Targeted ions (m/z values):")
        self.comboBoxIonLists = QtWidgets.QComboBox()
        self.comboBoxIonLists.addItem("Create new ion list...")

        self.ionTable = IonTable(view=self, parent=self)

        self.button_clear_ion_list = QtWidgets.QPushButton("Clear")
        self.button_save_ion_list = QtWidgets.QPushButton("Save")
        self.button_delete_ion_list = QtWidgets.QPushButton("Delete")

        # Mass accuracy slider
        self.mass_accuracy_slider = LabelledSlider(
            "Mass accuracy", [0.1, 0.01, 0.001, 0.0001], 0.0001
        )

        # Process button
        self.processButton = QtWidgets.QPushButton("Process")
        self.processButton.setObjectName("processButton")
        self.processButton.setDefault(True)
        self.processButton.setEnabled(False)

    def _build_canvas_widgets(self):
        """Create canvas widgets for plotting."""
        from ui.plotting import PlotStyle

        # Baseline/TIC canvas
        self.canvas_baseline = ChromatogramPlotWidget(parent=self)
        self.canvas_baseline.setObjectName("canvas_baseline")
        self.canvas_baseline.setCursor(Qt.CursorShape.CrossCursor)
        PlotStyle.apply_standard_style(
            self.canvas_baseline,
            title="Chromatography Data",
            x_label="Time (min)",
            y_label="Absorbance (mAU)",
        )
        self.canvas_baseline.addLegend(labelTextSize="12pt")

        # Average MS canvas
        self.canvas_avgMS = pg.PlotWidget(parent=self)
        self.canvas_avgMS.setObjectName("canvas_avgMS")
        self.canvas_avgMS.setMouseEnabled(x=True, y=False)
        PlotStyle.apply_standard_style(
            self.canvas_avgMS,
            title="Mass Spectrometry Data",
            x_label="m/z",
            y_label="Intensity (a.u.)",
        )
        self.canvas_avgMS.addLegend(labelTextSize="12pt")

        # Setup auto Y-range on X-range change
        def setYRange(vb):
            vb.enableAutoRange(axis="y")
            vb.setAutoVisible(y=True)

        self.canvas_avgMS.getPlotItem().getViewBox().sigXRangeChanged.connect(setYRange)
        self.canvas_avgMS.getPlotItem().setDownsampling(ds=20)
        self.canvas_avgMS.getPlotItem().getViewBox().sigRangeChangedManually.connect(
            lambda ev: update_labels_avgMS(self.canvas_avgMS)
        )

        # Initialize placeholders
        plot_placeholder(
            self.canvas_baseline,
            '<p style="color: #c5c5c5">\n\u2190 Add files to get started</p>',
        )
        plot_placeholder(
            self.canvas_avgMS,
            '<p style="color: #c5c5c5">\n\u2190 Add files to get started</p>',
        )

        # Setup crosshair proxy
        self.crosshair_v, self.crosshair_h, self.line_marker = create_crosshair_lines()
        self.proxy = create_crosshair_proxy(
            self.canvas_baseline, self._update_crosshair
        )

    def _build_lcms_layout(self):
        """Build layout for LC/GC-MS mode."""
        logger.debug("Building LC/GC-MS layout")

        # Create common widgets
        self._build_common_widgets()
        self._build_canvas_widgets()

        # Create file list widgets
        self.labelLCdata = QtWidgets.QLabel("LC/GC Files:")
        self.browseLC = QtWidgets.QPushButton("Browse")
        self.help_icon_lc = self._create_help_icon(
            "<b>Add Chromatography Files</b><br>"
            "Supported formats: .txt, .csv<br><br>"
            "<b>How to add files:</b><br>"
            "- Click Browse to select files<br>"
            "- Drag & drop files directly<br>"
            "- Drag & drop folders to add all valid files recursively"
        )
        self.listLC = CheckableDragDropListWidget(parent=self)
        self.listLC.setObjectName("listLC")
        self.button_clear_LC = QtWidgets.QPushButton("Clear")

        self.labelMSdata = QtWidgets.QLabel("MS Files:")
        self.browseMS = QtWidgets.QPushButton("Browse")
        self.help_icon_ms = self._create_help_icon(
            "<b>Add Mass Spectrometry Files</b><br>"
            "Supported formats: .mzML<br><br>"
            "<b>How to add files:</b><br>"
            "- Click Browse to select files<br>"
            "- Drag & drop files directly<br>"
            "- Drag & drop folders to add all valid files recursively"
        )
        self.listMS = CheckableDragDropListWidget(parent=self)
        self.listMS.setObjectName("listMS")
        self.button_clear_MS = QtWidgets.QPushButton("Clear")

        # Annotations (hidden by default in LC/GC-MS mode)
        self.browseAnnotations = QtWidgets.QPushButton("Browse Annotations")
        self.browseAnnotations.setVisible(False)
        self.labelAnnotations = QtWidgets.QLabel("Annotations:")
        self.labelAnnotations.setVisible(False)

        # --- Layout placement ---
        # Row 0: Labels and browse buttons with help icons (icon on left of button)
        lc_label_layout = QtWidgets.QHBoxLayout()
        lc_label_layout.addWidget(self.labelLCdata)
        lc_label_layout.addWidget(self.help_icon_lc)
        lc_label_layout.addStretch()
        self._main_layout.addLayout(lc_label_layout, 1, 0, 1, 1)
        self._main_layout.addWidget(self.browseLC, 1, 1, 1, 1)
        self._main_layout.addWidget(self.labelAnnotations, 1, 2, 1, 1)
        self._main_layout.addWidget(self.browseAnnotations, 1, 3, 1, 1)

        # Row 1-2: LC file list
        self._main_layout.addWidget(self.listLC, 2, 0, 1, 2)
        self._main_layout.addWidget(self.button_clear_LC, 3, 0, 1, 1)

        # Row 3: MS label and browse with help icon (icon on left of button)
        ms_label_layout = QtWidgets.QHBoxLayout()
        ms_label_layout.addWidget(self.labelMSdata)
        ms_label_layout.addWidget(self.help_icon_ms)
        ms_label_layout.addStretch()
        self._main_layout.addLayout(ms_label_layout, 4, 0, 1, 1)
        self._main_layout.addWidget(self.browseMS, 4, 1, 1, 1)

        # Row 4-5: MS file list
        self._main_layout.addWidget(self.listMS, 5, 0, 1, 2)
        self._main_layout.addWidget(self.button_clear_MS, 6, 0, 1, 1)

        # Ion list controls (right column)
        self._main_layout.addWidget(self.labelIonList, 0, 4, 1, 1)
        self._main_layout.addWidget(self.comboBoxIonLists, 1, 4, 1, 2)
        self._main_layout.addWidget(self.ionTable, 2, 4, 4, 3)
        self._main_layout.addWidget(self.button_clear_ion_list, 6, 4, 1, 1)
        self._main_layout.addWidget(self.button_save_ion_list, 6, 5, 1, 1)
        self._main_layout.addWidget(self.button_delete_ion_list, 6, 6, 1, 1)

        # Processing row
        self._main_layout.addWidget(self.mass_accuracy_slider, 7, 4, 1, 3)
        self._main_layout.addWidget(self.processButton, 7, 2, 1, 2)

        # Canvas pane (middle)
        self.resultsPane = QtWidgets.QWidget(parent=self)
        self.resultsPaneLayout = QtWidgets.QVBoxLayout(self.resultsPane)
        self.resultsPaneLayout.addWidget(self.canvas_baseline)
        self.resultsPaneLayout.addWidget(self.canvas_avgMS)
        self._main_layout.addWidget(self.resultsPane, 2, 2, 4, 2)

        # Stretch settings
        self._main_layout.setRowStretch(2, 3)
        self._main_layout.setRowStretch(5, 3)
        self._main_layout.setColumnStretch(2, 4)

    def _build_ms_only_layout(self):
        """Build layout for MS Only mode."""
        logger.debug("Building MS Only layout")

        # Create common widgets
        self._build_common_widgets()
        self._build_canvas_widgets()

        # Create file list widgets (MS only)
        self.labelMSdata = QtWidgets.QLabel("MS Files:")
        self.browseMS = QtWidgets.QPushButton("Browse")
        self.help_icon_ms = self._create_help_icon(
            "<b>Add Mass Spectrometry Files</b><br>"
            "Supported formats: .mzML<br><br>"
            "<b>How to add files:</b><br>"
            "- Click Browse to select files<br>"
            "- Drag & drop files directly<br>"
            "- Drag & drop folders to add all valid files recursively"
        )
        self.listMS = CheckableDragDropListWidget(parent=self)
        self.listMS.setObjectName("listMS")
        self.button_clear_MS = QtWidgets.QPushButton("Clear")

        # Hidden widgets (for compatibility)
        self.browseAnnotations = QtWidgets.QPushButton("Browse Annotations")
        self.browseAnnotations.setVisible(False)
        self.labelAnnotations = QtWidgets.QLabel("Annotations:")
        self.labelAnnotations.setVisible(False)

        # --- Layout placement ---
        # MS file list (spans more rows since LC is omitted)
        ms_label_layout = QtWidgets.QHBoxLayout()
        ms_label_layout.addWidget(self.labelMSdata)
        ms_label_layout.addWidget(self.help_icon_ms)
        ms_label_layout.addStretch()
        self._main_layout.addLayout(ms_label_layout, 0, 0, 1, 1)
        self._main_layout.addWidget(self.browseMS, 0, 1, 1, 1)
        self._main_layout.addWidget(self.listMS, 2, 0, 5, 2)
        self._main_layout.addWidget(self.button_clear_MS, 7, 0, 1, 1)

        # Ion list controls (right column)
        self._main_layout.addWidget(self.labelIonList, 0, 4, 1, 1)
        self._main_layout.addWidget(self.comboBoxIonLists, 1, 4, 1, 2)
        self._main_layout.addWidget(self.ionTable, 2, 4, 4, 3)
        self._main_layout.addWidget(self.button_clear_ion_list, 6, 4, 1, 1)
        self._main_layout.addWidget(self.button_save_ion_list, 6, 5, 1, 1)
        self._main_layout.addWidget(self.button_delete_ion_list, 6, 6, 1, 1)

        # Processing row
        self._main_layout.addWidget(self.mass_accuracy_slider, 7, 4, 1, 3)
        self._main_layout.addWidget(self.processButton, 7, 2, 1, 2)

        # Canvas pane (middle)
        self.resultsPane = QtWidgets.QWidget(parent=self)
        self.resultsPaneLayout = QtWidgets.QVBoxLayout(self.resultsPane)
        self.resultsPaneLayout.addWidget(self.canvas_baseline)
        self.resultsPaneLayout.addWidget(self.canvas_avgMS)
        self._main_layout.addWidget(self.resultsPane, 2, 2, 4, 2)

        # Stretch settings
        self._main_layout.setRowStretch(2, 3)
        self._main_layout.setColumnStretch(2, 4)

    def _build_chrom_only_layout(self):
        """Build layout for LC/GC Only (chromatography only) mode."""
        logger.debug("Building LC/GC Only layout")

        # Create common widgets
        self._build_common_widgets()

        # Note: No canvas widgets in chromatography-only mode
        # (annotations replace MS data)

        # Create file list widgets
        self.labelLCdata = QtWidgets.QLabel("LC/GC Files:")
        self.browseLC = QtWidgets.QPushButton("Browse")
        self.help_icon_lc = self._create_help_icon(
            "<b>Add Chromatography Files</b><br>"
            "Supported formats: .txt, .csv<br><br>"
            "<b>How to add files:</b><br>"
            "- Click Browse to select files<br>"
            "- Drag & drop files directly<br>"
            "- Drag & drop folders to add all valid files recursively"
        )
        self.listLC = CheckableDragDropListWidget(parent=self)
        self.listLC.setObjectName("listLC")
        self.button_clear_LC = QtWidgets.QPushButton("Clear")

        self.labelAnnotations = QtWidgets.QLabel("Annotation Files:")
        self.browseAnnotations = QtWidgets.QPushButton("Browse")
        self.listAnnotations = DragDropListWidget(parent=self)
        self.listAnnotations.setObjectName("listAnnotations")

        # --- Layout placement ---
        # LC file list with help icon (icon on left of button)
        lc_label_layout = QtWidgets.QHBoxLayout()
        lc_label_layout.addWidget(self.labelLCdata)
        lc_label_layout.addWidget(self.help_icon_lc)
        lc_label_layout.addStretch()
        self._main_layout.addLayout(lc_label_layout, 1, 0, 1, 1)
        self._main_layout.addWidget(self.browseLC, 1, 1, 1, 1)
        self._main_layout.addWidget(self.listLC, 2, 0, 1, 2)
        self._main_layout.addWidget(self.button_clear_LC, 3, 0, 1, 1)

        # Annotations list (where MS would be in LC/GC-MS mode)
        self._main_layout.addWidget(self.labelAnnotations, 1, 2, 1, 1)
        self._main_layout.addWidget(self.browseAnnotations, 1, 3, 1, 1)
        self._main_layout.addWidget(self.listAnnotations, 2, 2, 1, 2)

        # Ion list controls (right column)
        self._main_layout.addWidget(self.labelIonList, 0, 4, 1, 1)
        self._main_layout.addWidget(self.comboBoxIonLists, 1, 4, 1, 2)
        self._main_layout.addWidget(self.ionTable, 2, 4, 4, 3)
        self._main_layout.addWidget(self.button_clear_ion_list, 6, 4, 1, 1)
        self._main_layout.addWidget(self.button_save_ion_list, 6, 5, 1, 1)
        self._main_layout.addWidget(self.button_delete_ion_list, 6, 6, 1, 1)

        # Processing row
        self._main_layout.addWidget(self.mass_accuracy_slider, 7, 4, 1, 3)
        self._main_layout.addWidget(self.processButton, 7, 2, 1, 2)

        # Stretch settings
        self._main_layout.setRowStretch(2, 3)
        self._main_layout.setColumnStretch(2, 4)

    def _connect_widget_signals(self):
        """Connect signals for all widgets after layout build."""
        # File list signals
        if hasattr(self, "listLC"):
            self.listLC.filesDropped.connect(
                lambda files: self.handle_files_dropped(files, "LC")
            )
            self.listLC.itemClicked.connect(self._handle_lc_clicked)
            if hasattr(self.listLC, "itemCheckStateChanged"):
                self.listLC.itemCheckStateChanged.connect(self._on_lc_checkbox_changed)

        if hasattr(self, "listMS"):
            self.listMS.filesDropped.connect(
                lambda files: self.handle_files_dropped(files, "MS")
            )
            self.listMS.itemClicked.connect(self._handle_ms_clicked)
            if hasattr(self.listMS, "itemCheckStateChanged"):
                self.listMS.itemCheckStateChanged.connect(self._on_ms_checkbox_changed)

        if hasattr(self, "listAnnotations"):
            self.listAnnotations.filesDropped.connect(
                lambda files: self.handle_files_dropped(files, "Annotations")
            )

        # Browse buttons
        if hasattr(self, "browseLC"):
            self.browseLC.clicked.connect(self.on_browse_lc)

        if hasattr(self, "browseMS"):
            self.browseMS.clicked.connect(self.on_browse_ms)

        if hasattr(self, "browseAnnotations"):
            self.browseAnnotations.clicked.connect(self.on_browse_annotations)

        # Clear buttons
        if hasattr(self, "button_clear_LC"):
            self.button_clear_LC.clicked.connect(self.listLC.clear)

        if hasattr(self, "button_clear_MS"):
            self.button_clear_MS.clicked.connect(self.listMS.clear)

        # Ion table controls
        self.button_clear_ion_list.clicked.connect(self.ionTable.clear)
        self.button_save_ion_list.clicked.connect(self.ionTable.save_ion_list)
        self.button_delete_ion_list.clicked.connect(self.ionTable.delete_ion_list)
        self.comboBoxIonLists.currentIndexChanged.connect(self.update_ion_list)

        # Connect IonTable PubChem lookup status to status bar
        self.ionTable.lookup_status.connect(self._on_lookup_status)

        # Process button
        self.processButton.clicked.connect(self.process_requested.emit)

        # Canvas signals (if available)
        if hasattr(self, "canvas_baseline"):
            self.canvas_baseline.scene().sigMouseClicked.connect(
                self._update_line_marker
            )
            self.canvas_baseline.sigKeyPressed.connect(
                self._update_line_marker_with_key
            )

            if hasattr(self, "canvas_avgMS"):
                self.canvas_baseline.scene().sigMouseClicked.connect(
                    self._show_scan_at_time_x
                )
                self.canvas_baseline.scene().sigMouseClicked.connect(
                    lambda ev: update_labels_avgMS(self.canvas_avgMS)
                )
                self.canvas_baseline.sigKeyPressed.connect(self._show_scan_at_time_x)
                self.canvas_baseline.sigKeyPressed.connect(
                    lambda ev: update_labels_avgMS(self.canvas_avgMS)
                )

    # --- File Handling ---

    def handle_files_dropped(self, file_paths, file_type):
        """
        Validates and adds dropped files, then emits signal for Controller.
        """
        valid_extensions = {
            "LC": [".txt", ".csv"],
            "MS": [".mzml"],
            "Annotations": [".txt"],
        }

        added_files = []
        for path in file_paths:
            p = Path(path)
            # Handle directories recursively
            if p.is_dir():
                for f in p.rglob("*"):
                    if f.suffix.lower() in valid_extensions.get(file_type, []):
                        added_files.append(str(f))
            elif p.suffix.lower() in valid_extensions.get(file_type, []):
                added_files.append(str(p))
            else:
                logger.warning(f"Ignored invalid file for {file_type}: {path}")

        if not added_files:
            self.status_message.emit("No valid files found.", 2000)
            return

        # Add to UI List
        target_list = self._get_list_for_type(file_type)
        if target_list:
            for f in added_files:
                target_list.addItem(os.path.basename(f))

        self.status_message.emit(f"Added {len(added_files)} {file_type} files.", 3000)

        # Notify Controller to update Model
        self.files_loaded.emit(file_type, added_files)

    def _get_list_for_type(self, file_type):
        """Get the list widget for a given file type."""
        if file_type == "LC" and hasattr(self, "listLC"):
            return self.listLC
        elif file_type == "MS" and hasattr(self, "listMS"):
            return self.listMS
        elif file_type == "Annotations" and hasattr(self, "listAnnotations"):
            return self.listAnnotations
        return None

    def on_browse_lc(self):
        """Open file dialog for LC files."""
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Select LC Files",
            str(QtCore.QDir.homePath()),
            "Text Files (*.txt);;CSV Files (*.csv);;All Files (*)",
        )
        if files:
            self.handle_files_dropped(files, "LC")

    def on_browse_ms(self):
        """Open file dialog for MS files."""
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Select MS Files",
            str(QtCore.QDir.homePath()),
            "MzML Files (*.mzML);;All Files (*)",
        )
        if files:
            self.handle_files_dropped(files, "MS")

    def on_browse_annotations(self):
        """Open file dialog for annotation files."""
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Select Annotation Files",
            str(QtCore.QDir.homePath()),
            "Text Files (*.txt);;All Files (*)",
        )
        if files:
            self.handle_files_dropped(files, "Annotations")

    def _handle_lc_clicked(self, item):
        """Handle click on LC file list item - highlights the plot if checked."""
        # Skip if this was a checkbox click (checkbox handler already ran)
        if (
            hasattr(self.listLC, "was_checkbox_click")
            and self.listLC.was_checkbox_click()
        ):
            return

        filename = item.text()

        # Unhighlight previous selection
        if self._selected_lc_file and self._selected_lc_file in self._lc_active_plots:
            self._set_plot_pen_width(self._lc_active_plots[self._selected_lc_file], 1)

        # Update selection and highlight new (if plotted)
        self._selected_lc_file = filename
        if filename in self._lc_active_plots:
            self._set_plot_pen_width(self._lc_active_plots[filename], 2)

    def _handle_ms_clicked(self, item):
        """Handle click on MS file list item - highlights the plot if checked."""
        # Skip if this was a checkbox click (checkbox handler already ran)
        if (
            hasattr(self.listMS, "was_checkbox_click")
            and self.listMS.was_checkbox_click()
        ):
            return

        filename = item.text()

        # Unhighlight previous selection
        if self._selected_ms_file and self._selected_ms_file in self._ms_active_plots:
            plot_item, _ = self._ms_active_plots[self._selected_ms_file]
            if plot_item is not None:
                self._set_plot_pen_width(plot_item, 1)

        # Update selection and highlight new (if plotted)
        self._selected_ms_file = filename
        if filename in self._ms_active_plots:
            plot_item, _ = self._ms_active_plots[filename]
            if plot_item is not None:
                self._set_plot_pen_width(plot_item, 2)

    # --- Checkbox Plotting Handlers ---

    def _set_plot_pen_width(self, plot_item, width: int):
        """Set the pen width of a plot item, preserving color."""
        from pyqtgraph import mkPen

        current_pen = plot_item.opts.get("pen")
        if current_pen:
            color = current_pen.color()
            plot_item.setPen(mkPen(color, width=width))

    def _get_next_color(self, plot_type: str) -> str:
        """Get next color from palette for overlay plots."""
        from ui.plotting import PlotStyle

        if plot_type == "LC":
            color = PlotStyle.PALETTE[self._color_index_lc % len(PlotStyle.PALETTE)]
            self._color_index_lc += 1
        else:
            color = PlotStyle.PALETTE[self._color_index_ms % len(PlotStyle.PALETTE)]
            self._color_index_ms += 1
        return color

    def _on_lc_checkbox_changed(self, filename: str, is_checked: bool):
        """Handle LC file checkbox state change."""
        from ui.plotting import plot_absorbance_data

        logger.debug(f"LC checkbox changed: {filename} -> {is_checked}")

        if not hasattr(self, "canvas_baseline") or self.canvas_baseline is None:
            logger.debug("No canvas_baseline, skipping")
            return

        stem_filename = Path(filename).stem

        if is_checked:
            if self._controller and hasattr(self._controller.model, "lc_measurements"):
                lc_data = self._controller.model.lc_measurements.get(stem_filename)
                if lc_data:
                    logger.debug(f"Found LC data for {stem_filename}, plotting")

                    # If this is the first plot, clear placeholder and restore axes
                    should_clear = len(self._lc_active_plots) == 0
                    if should_clear:
                        self.canvas_baseline.clear()
                        self.canvas_baseline.addLegend(labelTextSize="12pt")
                        self._add_crosshairs_to_canvas(self.canvas_baseline)

                    color = self._get_next_color("LC")
                    # Set pen width to 2 if this file is currently selected, else 1
                    pen_width = 2 if filename == self._selected_lc_file else 1

                    plot_item = plot_absorbance_data(
                        lc_data.path,
                        lc_data.baseline_corrected,
                        self.canvas_baseline,
                        color=color,
                        pen_width=pen_width,
                        name=filename,
                        clear=should_clear,
                    )
                    self._lc_active_plots[filename] = plot_item
        else:
            if filename in self._lc_active_plots:
                plot_item = self._lc_active_plots.pop(filename)
                self.canvas_baseline.removeItem(plot_item)

                # If no more plots, restore placeholder
                if not self._lc_active_plots:
                    plot_placeholder(
                        self.canvas_baseline,
                        '<p style="color: #c5c5c5">\n\u2190 Add files to get started</p>',
                    )
                    # Reset label references since canvas was cleared
                    self.crosshair_v_label = None
                    self.crosshair_h_label = None

            # Clear selection if this was the selected file
            if filename == self._selected_lc_file:
                self._selected_lc_file = None

    def _on_ms_checkbox_changed(self, filename: str, is_checked: bool):
        """Handle MS file checkbox state change."""
        from ui.plotting import plot_average_ms_data

        logger.debug(f"MS checkbox changed: {filename} -> {is_checked}")

        if not hasattr(self, "canvas_avgMS") or self.canvas_avgMS is None:
            logger.debug("No canvas_avgMS, skipping")
            return

        stem_filename = Path(filename).stem

        if is_checked:
            if self._controller and hasattr(self._controller.model, "ms_measurements"):
                ms_data = self._controller.model.ms_measurements.get(stem_filename)
                if ms_data is not None:
                    logger.debug(
                        f"Found MS data for {stem_filename}, plotting mass spectrum"
                    )
                    color = self._get_next_color("MS")

                    # Get retention time from line_marker (default 0)
                    time_x = 0.0
                    if hasattr(self, "line_marker") and self.line_marker.isVisible():
                        time_x = float(self.line_marker.pos().x())

                    # Only clear canvas on first plot
                    should_clear = len(self._ms_active_plots) == 0

                    plot_item = plot_average_ms_data(
                        stem_filename,
                        time_x,
                        ms_data.data,
                        self.canvas_avgMS,
                        color=color,
                        name=filename,
                        clear=should_clear,
                    )
                    # Store tuple of (plot_item, color) to preserve color for time updates
                    self._ms_active_plots[filename] = (plot_item, color)

                    # In MS Only mode, also plot TIC to canvas_baseline
                    if self._current_mode == "MS Only":
                        from ui.plotting import PlotStyle
                        from pyqtgraph import mkPen

                        # First TIC plot: clear and setup canvas
                        if not self._tic_active_plots:
                            self.canvas_baseline.clear()
                            PlotStyle.apply_standard_style(
                                self.canvas_baseline,
                                title="Total Ion Current (TIC)",
                                x_label="Time (min)",
                                y_label="Intensity (cps)",
                            )
                            self.canvas_baseline.addLegend(labelTextSize="12pt")
                            self._add_crosshairs_to_canvas(self.canvas_baseline)

                        # Plot TIC with overlay support
                        tic_color = self._get_next_color("LC")  # Reuse LC color cycling
                        if ms_data.tic_times is not None and len(ms_data.tic_times) > 0:
                            tic_plot_item = self.canvas_baseline.plot(
                                ms_data.tic_times,
                                ms_data.tic_values,
                                pen=mkPen(tic_color, width=1),
                                name=filename,
                            )
                            self._tic_active_plots[filename] = tic_plot_item
        else:
            if filename in self._ms_active_plots:
                plot_item, _ = self._ms_active_plots.pop(filename)
                if plot_item is not None:
                    self.canvas_avgMS.removeItem(plot_item)
                # Clear orphaned TextItem labels when no MS plots remain
                if len(self._ms_active_plots) == 0:
                    for item in list(self.canvas_avgMS.items()):
                        if isinstance(item, pg.TextItem):
                            self.canvas_avgMS.removeItem(item)

            # In MS Only mode, also remove TIC from canvas_baseline
            if self._current_mode == "MS Only" and filename in self._tic_active_plots:
                tic_plot_item = self._tic_active_plots.pop(filename)
                self.canvas_baseline.removeItem(tic_plot_item)

                # Restore placeholder if no TIC plots remain
                if not self._tic_active_plots:
                    plot_placeholder(
                        self.canvas_baseline,
                        '<p style="color: #c5c5c5">\n\u2190 Add files to get started</p>',
                    )
                    self.crosshair_v_label = None
                    self.crosshair_h_label = None

            # Clear selection if this was the selected file
            if filename == self._selected_ms_file:
                self._selected_ms_file = None

    def refresh_checkbox_plots(self):
        """
        Re-trigger plots for already-checked files after data loads.

        This method handles the race condition where users check files before
        the data has finished loading. Should be called after loading completes.
        """
        # Re-plot checked LC files
        if hasattr(self, "listLC"):
            for i in range(self.listLC.count()):
                item = self.listLC.item(i)
                if item and item.checkState() == Qt.CheckState.Checked:
                    filename = item.text()
                    # Only plot if not already plotted
                    if filename not in self._lc_active_plots:
                        self._on_lc_checkbox_changed(filename, True)

        # Re-plot checked MS files
        if hasattr(self, "listMS"):
            for i in range(self.listMS.count()):
                item = self.listMS.item(i)
                if item and item.checkState() == Qt.CheckState.Checked:
                    filename = item.text()
                    # Only plot if not already plotted
                    if filename not in self._ms_active_plots:
                        self._on_ms_checkbox_changed(filename, True)

    # --- Ion List Management ---

    def _on_lookup_status(self, message: str, duration_ms: int):
        """Forward PubChem lookup status to status bar."""
        if self.statusbar:
            self.statusbar.showMessage(message, duration_ms)
        else:
            # Fallback to status_message signal if statusbar not available
            self.status_message.emit(message, duration_ms)

    def _load_ion_config_names(self):
        """Reads config.json to populate the dropdown."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                    keys = sorted(list(data.keys()))
                    for key in keys:
                        if self.comboBoxIonLists.findText(key) == -1:
                            self.comboBoxIonLists.addItem(key)
            except Exception as e:
                logger.error(f"Failed to load ion config: {e}")
                self.status_message.emit("Error loading ion config.", 3000)

    def update_ion_list(self):
        """Populates the table based on combo selection."""
        selection = self.comboBoxIonLists.currentText()

        # Handle "Create new" or empty selection
        if not selection or selection == "Create new ion list...":
            self.ionTable.setRowCount(0)
            return

        if not self.config_path.exists():
            return

        try:
            with open(self.config_path, "r") as f:
                data = json.load(f)

            ion_data = data.get(selection, {})

            # Block signals to prevent triggering PubChem lookups during programmatic updates
            self.ionTable.blockSignals(True)
            try:
                self.ionTable.setRowCount(len(ion_data))

                for row, (name, details) in enumerate(ion_data.items()):
                    # Name
                    self.ionTable.setItem(row, 0, QtWidgets.QTableWidgetItem(str(name)))

                    # Ions (Handle list or string legacy format)
                    ions = details.get("ions", [])
                    if isinstance(ions, list):
                        ions_str = ", ".join(map(str, ions))
                    else:
                        ions_str = str(ions)
                    self.ionTable.setItem(row, 1, QtWidgets.QTableWidgetItem(ions_str))

                    # Info (Handle list or string legacy format)
                    info = details.get("info", [])
                    if isinstance(info, list):
                        info_str = ", ".join(map(str, info))
                    else:
                        info_str = str(info)
                    self.ionTable.setItem(row, 2, QtWidgets.QTableWidgetItem(info_str))
            finally:
                self.ionTable.blockSignals(False)

        except Exception as e:
            logger.error(f"Error updating ion list: {e}")
            self.status_message.emit(f"Error updating ion list: {e}", 3000)

    # --- Plotting Methods ---

    def _plot_raw_chromatography(self, lc_file):
        """Plot raw chromatography data (used by view.py for loading feedback)."""
        from ui.plotting import plot_absorbance_data

        if not hasattr(self, "canvas_baseline"):
            return

        try:
            # Remove only previous main view plots (preserve checkbox overlays)
            for plot_item in self._main_view_plots:
                try:
                    self.canvas_baseline.removeItem(plot_item)
                except Exception:
                    pass  # Item may already be removed
            self._main_view_plots.clear()

            logger.debug(
                f"Plotting chromatography for {lc_file.path}, preserving checkbox plots"
            )
            # Call plot_absorbance_data and capture returned plot item
            plot_item = plot_absorbance_data(
                lc_file.path,
                lc_file.baseline_corrected,
                self.canvas_baseline,
                color="#2EC4B6",
                pen_width=1,
            )

            # Track the new main view plot using the returned item
            self._main_view_plots = [plot_item]

            self._add_crosshairs_to_canvas(self.canvas_baseline)
        except Exception as e:
            logger.error(f"Error plotting chromatography: {e}")

    def _plot_raw_ms(self, ms_file):
        """Plot raw MS data (TIC and average MS)."""
        from ui.plotting import plot_total_ion_current, plot_average_ms_data

        if not hasattr(self, "canvas_baseline") or not hasattr(self, "canvas_avgMS"):
            return

        try:
            if ms_file:
                # ONLY plot TIC in MS Only mode - don't replace LC data in LC/GC-MS mode
                if self._current_mode == "MS Only":
                    logger.debug(f"Plotting TIC for {ms_file.filename} (MS Only mode)")
                    plot_total_ion_current(
                        self.canvas_baseline, ms_file, ms_file.filename, clear=False
                    )
                    self._add_crosshairs_to_canvas(self.canvas_baseline)

                # Plot average MS (always, in all modes with MS data)
                plot_average_ms_data(
                    ms_file.filename, 0, ms_file.data, self.canvas_avgMS
                )
        except Exception as e:
            logger.error(f"Error plotting MS data: {e}")

    def _add_crosshairs_to_canvas(self, canvas):
        """Add crosshair lines to a canvas."""
        canvas.getPlotItem().addItem(self.crosshair_v, ignoreBounds=True)
        canvas.getPlotItem().addItem(self.crosshair_h, ignoreBounds=True)
        canvas.getPlotItem().addItem(self.line_marker, ignoreBounds=True)

        # Only create labels if they don't exist
        if self.crosshair_v_label is None:
            self.crosshair_v_label = pg.InfLineLabel(
                self.crosshair_v, text="", color="#b8b8b8", rotateAxis=(1, 0)
            )
            self.crosshair_h_label = pg.InfLineLabel(
                self.crosshair_h, text="", color="#b8b8b8", rotateAxis=(1, 0)
            )

    def _update_crosshair(self, e):
        """Update crosshair position based on mouse movement."""
        if self.crosshair_v_label is None:
            return

        if not hasattr(self, "canvas_baseline"):
            return

        pos = e[0]
        if self.canvas_baseline.sceneBoundingRect().contains(pos):
            mousePoint = (
                self.canvas_baseline.getPlotItem().getViewBox().mapSceneToView(pos)
            )
            try:
                self.crosshair_v.setPos(mousePoint.x())
                self.crosshair_h.setPos(mousePoint.y())
                self.crosshair_v_label.setText(f"{mousePoint.x():.2f} min")
                self.crosshair_h_label.setText(f"{mousePoint.y():.0f} a.u.")
            except RuntimeError:
                pass

    def _update_line_marker(self, event):
        """Update line marker position on click."""
        if not hasattr(self, "canvas_baseline"):
            return

        mouse_pos = (
            self.canvas_baseline.getPlotItem()
            .getViewBox()
            .mapSceneToView(event._scenePos)
        )
        self.line_marker.setVisible(True)
        self.line_marker.setPos(mouse_pos.x())

    def _update_line_marker_with_key(self, event):
        """Update line marker position with arrow keys."""
        self.line_marker.setVisible(True)
        if event.key() == QtCore.Qt.Key.Key_Left:
            self.line_marker.setPos(self.line_marker.pos().x() - 0.01)
        elif event.key() == QtCore.Qt.Key.Key_Right:
            self.line_marker.setPos(self.line_marker.pos().x() + 0.01)

    def _show_scan_at_time_x(self, event):
        """Show MS scan at the selected time point for all checked MS files."""
        from ui.plotting import plot_average_ms_data, plot_placeholder

        if not hasattr(self, "canvas_avgMS") or self.canvas_avgMS is None:
            return
        if not self._controller:
            return
        if not hasattr(self._controller, "model"):
            return

        time_x = float(self.line_marker.pos().x())
        model = self._controller.model

        # If there are checked MS files, update all of them
        if self._ms_active_plots and hasattr(model, "ms_measurements"):
            # Update all checked MS files with their preserved colors
            is_first = True
            updated_plots = {}

            for filename, (old_plot_item, color) in list(self._ms_active_plots.items()):
                stem_filename = Path(filename).stem

                if stem_filename in model.ms_measurements:
                    try:
                        # Remove old plot item
                        if old_plot_item is not None:
                            self.canvas_avgMS.removeItem(old_plot_item)

                        # Create new plot at new time, preserving color
                        new_plot_item = plot_average_ms_data(
                            stem_filename,
                            time_x,
                            model.ms_measurements[stem_filename].data,
                            self.canvas_avgMS,
                            color=color,
                            name=filename,
                            clear=is_first,
                        )
                        updated_plots[filename] = (new_plot_item, color)
                        is_first = False
                    except Exception as e:
                        logger.error(f"Error updating MS plot for {filename}: {e}")
                        # Keep old entry if update fails
                        updated_plots[filename] = (old_plot_item, color)

            self._ms_active_plots = updated_plots
            return

        # No checked files - show placeholder prompting user to select a file
        plot_placeholder(self.canvas_avgMS, "← select a file from the MS list")

    # --- External Access ---

    def get_file_list(self, file_type):
        """Helper for Controller to get files."""
        widget = self._get_list_for_type(file_type)
        if widget:
            return [widget.item(i).text() for i in range(widget.count())]
        return []

    def clear_file_list(self, file_type):
        """Clear a specific file list."""
        widget = self._get_list_for_type(file_type)
        if widget:
            widget.clear()

    # --- Compatibility Properties ---

    @property
    def comboBoxChangeMode(self):
        """Provide access to mode combo box for View compatibility."""
        # This will be managed by View, not UploadTab
        return getattr(self, "_mode_combo", None)

    @property
    def statusbar(self):
        """Forward statusbar access to parent window."""
        parent = self.window()
        if parent and hasattr(parent, "statusbar"):
            return parent.statusbar
        return None
