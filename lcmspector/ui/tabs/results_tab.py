"""
Results Tab for displaying processed data visualizations.
"""
from PySide6 import QtWidgets, QtCore
import pyqtgraph as pg
from pyqtgraph.dockarea import DockArea
import logging
import traceback

from ui.tabs.base_tab import TabBase
from ui.widgets import ChromatogramPlotWidget
from ui.plotting import (
    plot_annotated_LC,
    plot_annotated_XICs,
    highlight_peak,
)

logger = logging.getLogger(__name__)


class ResultsTab(TabBase):
    """
    Handles the visualization of results: chromatograms and XICs.

    Displays annotated LC chromatograms and extracted ion chromatograms (XICs)
    after processing is complete.
    """

    # Signals to communicate back to the controller
    file_changed = QtCore.Signal(int)

    def __init__(self, parent=None, mode="LC/GC-MS"):
        super().__init__(parent)
        self._current_mode = mode

        # Internal State
        self.curve_list = {}

        # State tracking for data
        self.current_lc_file = None
        self.current_ms_file = None

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
        # File selection change is handled via signal emission
        # Controller connects to file_changed signal externally

    def clear(self):
        """Clear all data from the tab."""
        if hasattr(self, 'canvas_annotatedLC'):
            try:
                self.canvas_annotatedLC.clear()
            except RuntimeError:
                pass
        if hasattr(self, 'canvas_XICs'):
            # DockArea doesn't have a clear method, need to remove all docks
            try:
                for dock in list(self.canvas_XICs.docks.values()):
                    dock.close()
            except (AttributeError, RuntimeError):
                pass
        if hasattr(self, 'comboBox_currentfile'):
            try:
                self.comboBox_currentfile.clear()
            except RuntimeError:
                pass
        self.curve_list = {}
        self.current_lc_file = None
        self.current_ms_file = None

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
        """Build the results tab UI based on current mode."""
        # Control row with file selection
        self.label_results_currentfile = QtWidgets.QLabel("Current file:")
        self.label_results_currentfile.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Preferred
        )

        self.comboBox_currentfile = QtWidgets.QComboBox()
        self.comboBox_currentfile.setObjectName("comboBox_currentfile")

        self._main_layout.addWidget(self.label_results_currentfile, 0, 0, 1, 1)
        self._main_layout.addWidget(self.comboBox_currentfile, 0, 1, 1, 1)

        # XICs in scroll area
        self.scrollArea = QtWidgets.QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollArea.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.scrollArea.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )

        self.canvas_XICs = DockArea()
        self.canvas_XICs.setObjectName("canvas_XICs")
        self.scrollArea.setWidget(self.canvas_XICs)
        self.canvas_XICs.setContentsMargins(0, 0, 0, 0)

        if self._current_mode == "LC/GC-MS":
            # Show both annotated LC and XICs side by side
            self._main_layout.addWidget(self.scrollArea, 1, 1, 1, 1)

            # Annotated LC chromatogram
            self.canvas_annotatedLC = pg.PlotWidget()
            self.canvas_annotatedLC.setObjectName("canvas_annotatedLC")
            self.canvas_annotatedLC.setMouseEnabled(x=True, y=False)
            self._main_layout.addWidget(self.canvas_annotatedLC, 1, 0, 1, 1)
        elif self._current_mode == "MS Only":
            # Only show XICs spanning the full width
            self._main_layout.addWidget(self.scrollArea, 1, 0, 1, 2)
            # Create a hidden annotated LC widget for compatibility
            self.canvas_annotatedLC = pg.PlotWidget()
            self.canvas_annotatedLC.setObjectName("canvas_annotatedLC")
            self.canvas_annotatedLC.setVisible(False)
        else:  # LC/GC Only
            # Show only annotated LC spanning full width
            self.canvas_annotatedLC = pg.PlotWidget()
            self.canvas_annotatedLC.setObjectName("canvas_annotatedLC")
            self.canvas_annotatedLC.setMouseEnabled(x=True, y=False)
            self._main_layout.addWidget(self.canvas_annotatedLC, 1, 0, 1, 2)
            # Hide scroll area for XICs
            self.scrollArea.setVisible(False)

    def _connect_widget_signals(self):
        """Connect widget signals."""
        self.comboBox_currentfile.currentIndexChanged.connect(self._on_file_selected)

    def _on_file_selected(self, index):
        """Internal handler to emit signal."""
        if index is not None:
            self.file_changed.emit(index)

    def update_combo_box(self, filenames):
        """Update the file selection combo box."""
        self.comboBox_currentfile.clear()
        self.comboBox_currentfile.addItems(filenames)

    def display_plots(self, lc_file, ms_file):
        """
        Display plots for the given LC and MS files.

        Parameters
        ----------
        lc_file : LCMeasurement or None
            The LC measurement data
        ms_file : MSMeasurement or None
            The MS measurement data
        """
        self.current_lc_file = lc_file
        self.current_ms_file = ms_file

        try:
            # Clear old plots
            self.canvas_annotatedLC.clear()

            if self._current_mode == "LC/GC-MS":
                self._display_lcms_plots(lc_file, ms_file)
            elif self._current_mode == "MS Only":
                self._display_ms_only_plots(ms_file)
            # LC/GC Only mode doesn't show XICs

        except Exception as e:
            logger.error(f"Error displaying plots: {traceback.format_exc()}")

    def _display_lcms_plots(self, lc_file, ms_file):
        """Display plots for LC/GC-MS mode."""
        if lc_file and ms_file:
            if lc_file.filename == ms_file.filename:
                try:
                    self.curve_list = plot_annotated_LC(
                        lc_file.path,
                        lc_file.baseline_corrected,
                        self.canvas_annotatedLC,
                    )
                    # Connect curve click handlers
                    for curve in self.curve_list.keys():
                        curve.sigClicked.connect(
                            lambda c, _event, xics=ms_file.xics: highlight_peak(
                                c,
                                self.curve_list,
                                self.canvas_annotatedLC,
                                xics,
                            )
                        )
                except RuntimeError:
                    logger.error("Canvas was deleted, skipping LC plot")

            # Plot XICs
            if ms_file and hasattr(ms_file, 'xics') and ms_file.xics:
                plot_annotated_XICs(ms_file.xics, self.canvas_XICs)

    def _display_ms_only_plots(self, ms_file):
        """Display plots for MS Only mode."""
        if ms_file and hasattr(ms_file, 'xics') and ms_file.xics:
            plot_annotated_XICs(ms_file.xics, self.canvas_XICs)

    def setup_dock_area(self, xics, widget=None):
        """
        Setup the dock area with XIC plots.

        Parameters
        ----------
        xics : tuple
            Tuple of compound XIC data
        widget : DockArea, optional
            The dock area widget to use. If None, uses self.canvas_XICs
        """
        if widget is None:
            widget = self.canvas_XICs

        cols = 5
        row_anchor_dock = None

        for i, compound in enumerate(xics):
            if i % cols == 0:
                position = "bottom"
                relative_to = None
            else:
                position = "right"
                relative_to = row_anchor_dock

            dock = widget.addDock(
                position=position,
                relativeTo=relative_to,
                name=f"{compound.name}",
                widget=pg.PlotWidget(),
                size=(100, 100),
            )

            # If this was a new row (or first item), update the anchor
            if i % cols == 0:
                row_anchor_dock = dock

            plot_widget = dock.widgets[0]
            plot_widget.setMouseEnabled(x=True, y=False)
            plot_widget.addLegend(offset=(0, 0))
            plot_widget.getViewBox().enableAutoRange(axis="y", enable=True)

        # Resize logic to ensure docks aren't squashed
        widget.setMinimumSize(QtCore.QSize(cols * 150, (len(xics) // cols + 1) * 200))
