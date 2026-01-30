"""
Base class for all tab widgets in the application.
"""
from abc import abstractmethod
from PySide6 import QtWidgets, QtCore


class TabBase(QtWidgets.QWidget):
    """
    Abstract base class for tab widgets.

    Provides common interface for controller injection, signal handling,
    and layout management. All tabs should inherit from this class.
    """

    # Common signal for status bar messages
    status_message = QtCore.Signal(str, int)  # (message, duration_ms)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._controller = None
        self._model = None

    @property
    def controller(self):
        """Access the controller."""
        return self._controller

    @property
    def model(self):
        """Access the model through the controller."""
        return self._model

    def set_controller(self, controller):
        """
        Inject controller after initialization.

        This method should be called after the View creates all tabs
        and the Controller is ready to be connected.

        Parameters
        ----------
        controller : Controller
            The application controller
        """
        self._controller = controller
        self._model = controller.model if controller else None
        self._connect_controller_signals()

    @abstractmethod
    def _connect_controller_signals(self):
        """
        Connect signals between the tab and controller.

        Subclasses must implement this to set up their specific
        signal/slot connections with the controller.
        """
        pass

    @abstractmethod
    def setup_layout(self, mode: str = None):
        """
        Build or rebuild the layout.

        This method should clear any existing layout and rebuild it
        from scratch. Called on initialization and when mode changes
        require layout reconstruction.

        Parameters
        ----------
        mode : str, optional
            The application mode (e.g., "LC/GC-MS", "MS Only", "LC/GC Only")
        """
        pass

    @abstractmethod
    def clear(self):
        """
        Clear all data from the tab.

        Resets the tab to its initial state, clearing any displayed
        data, plots, or user input.
        """
        pass
