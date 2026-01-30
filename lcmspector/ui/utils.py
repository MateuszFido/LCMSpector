"""
Shared utility functions for UI components.
"""
from PySide6 import QtCore, QtWidgets
import pyqtgraph as pg


def clear_layout(layout):
    """
    Recursively clears all widgets from a layout.

    This function iterates through all items in the layout in reverse order,
    clearing and deleting each widget. Nested layouts are also handled
    recursively.

    Parameters
    ----------
    layout : QLayout
        The layout to clear
    """
    if layout is None:
        return

    for i in reversed(range(layout.count())):
        item = layout.itemAt(i)
        if item is None:
            continue

        widget = item.widget()
        if widget is not None:
            try:
                widget.clear()
            except AttributeError:
                pass
            widget.deleteLater()
        else:
            # Handle nested layouts
            nested_layout = item.layout()
            if nested_layout is not None:
                clear_layout(nested_layout)


def create_crosshair_lines():
    """
    Create standard crosshair lines for plot widgets.

    Returns
    -------
    tuple
        (crosshair_v, crosshair_h, line_marker) - vertical crosshair,
        horizontal crosshair, and vertical line marker for selection
    """
    crosshair_v = pg.InfiniteLine(
        angle=90,
        pen=pg.mkPen(color="#b8b8b8", width=1, style=QtCore.Qt.PenStyle.DashLine),
        movable=False,
    )
    crosshair_h = pg.InfiniteLine(
        angle=0,
        pen=pg.mkPen(color="#b8b8b8", style=QtCore.Qt.PenStyle.DashLine, width=1),
        movable=False,
    )
    line_marker = pg.InfiniteLine(
        angle=90,
        pen=pg.mkPen(color="#000000", style=QtCore.Qt.PenStyle.SolidLine, width=1),
        movable=True,
    )
    return crosshair_v, crosshair_h, line_marker


def create_crosshair_proxy(canvas, update_callback):
    """
    Create a signal proxy for mouse movement crosshair updates.

    Parameters
    ----------
    canvas : pg.PlotWidget
        The plot widget to track mouse movement on
    update_callback : callable
        Function to call when mouse moves

    Returns
    -------
    pg.SignalProxy
        The signal proxy object (must be kept alive)
    """
    return pg.SignalProxy(
        canvas.scene().sigMouseMoved,
        rateLimit=60,
        slot=update_callback,
    )
