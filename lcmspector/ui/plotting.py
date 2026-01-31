import os
import time
import logging
import itertools
from typing import Optional, List, Any

from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import Qt, QSize
from PySide6.QtCore import Qt as QtCore_Qt
import numpy as np
import pandas as pd
import pyqtgraph as pg
from pyqtgraph import mkPen, mkBrush
from pyqtgraph.dockarea import DockArea
from scipy.signal import find_peaks, peak_widths
from static_frame import FrameHE
from pyteomics.mzml import MzML

# Assuming these exist in your project structure
from ui import fonts

logger = logging.getLogger(__name__)
logger.propagate = False


# --- Global style config ---
class PlotStyle:
    """Centralized configuration for plot styling."""

    BACKGROUND = "w"
    TEXT_COLOR = "#2C2D2D"
    AXIS_PEN = mkPen("#2C2D2D", width=2)
    GRID_ALPHA = 0.3

    # Color palette for multi-line plots (XICs, annotatedlC)
    PALETTE = [
        "#e25759",
        "#0b81a2",
        "#7e4794",
        "#59a89c",
        "#9d2c00",
        "#36b700",
        "#f0c571",
        "#c8c8c8",
        "#cc6677",
        "#332288",
        "#ddcc77",
        "#117733",
        "#88ccee",
        "#882255",
        "#44aa99",
    ]

    @staticmethod
    def apply_standard_style(
        widget: pg.PlotWidget, title: str = "", x_label: str = "", y_label: str = ""
    ):
        """Applies standard formatting to a PlotWidget."""
        default_font = fonts.get_main_font(12)
        widget.setBackground(PlotStyle.BACKGROUND)
        widget.setTitle(title, color=PlotStyle.TEXT_COLOR, size="12pt", family="Nunito")

        label_style = {
            "color": PlotStyle.TEXT_COLOR,
            "font-size": "13pt",
            "font-family": "Nunito",
        }
        widget.setLabel("bottom", x_label, **label_style)
        widget.setLabel("left", y_label, **label_style)

        # Axis styling
        for axis_name in ["left", "bottom"]:
            axis = widget.getAxis(axis_name)
            axis.setTextPen(PlotStyle.TEXT_COLOR, size="12pt")
            axis.setTickPen(PlotStyle.AXIS_PEN)
            axis.setStyle(tickFont=default_font)


# --- Plotting Functions ---


def plot_absorbance_data(
    path: str,
    dataframe: pd.DataFrame,
    widget: pg.PlotWidget,
    color: str = "#2EC4B6",
    pen_width: int = 1,
):
    """Plots baseline-corrected chromatography data with filename in legend."""
    filename = os.path.basename(path).split(".")[0]

    PlotStyle.apply_standard_style(
        widget,
        title="Chromatography Data",
        x_label="Retention time (min)",
        y_label="Absorbance (mAU)",
    )
    # Plot Corrected trace only, using filename as legend entry
    widget.plot(
        dataframe["Time (min)"],
        dataframe["Value (mAU)"],
        pen=mkPen(color, width=pen_width),
        name=filename,
    )


def plot_average_ms_data(
    filename: str,
    rt: float,
    data_matrix: MzML,
    widget: pg.PlotWidget,
    color: str = "#3c5488ff",
    name: str | None = None,
    clear: bool = True,
):
    """
    Plots the average MS data and annotates peaks.

    Parameters
    ----------
    filename : str
        The filename (used for logging/identification)
    rt : float
        Retention time to extract spectrum at
    data_matrix : MzML
        The MzML data object
    widget : pg.PlotWidget
        Target plot widget
    color : str
        Color for the spectrum (default: blue)
    name : str | None
        Legend name for the plot item. If None, no legend entry.
    clear : bool
        If True, applies standard style (clears widget). If False, overlays.

    Returns
    -------
    plot_item
        The created BarGraphItem or PlotDataItem, or None on error
    """
    try:
        spectrum = data_matrix.time[rt]
        if spectrum["ms level"] > 1:
            # DDA shield
            spec_range = data_matrix.time[rt - 0.1 : rt + 0.1]
            for spec in spec_range:
                if spec["ms level"] == 1:
                    spectrum = spec
                    break

    except (ValueError, IndexError):
        # Fallback to first scan or fail gracefully
        try:
            spectrum = data_matrix.time[0]
        except IndexError:
            logger.error("MzML file is empty.")
            return None

    if clear:
        PlotStyle.apply_standard_style(
            widget,
            title="Mass Spectrometry Data",
            x_label="m/z",
            y_label="Intensity / a.u.",
        )

    mzs = spectrum["m/z array"]
    intensities = spectrum["intensity array"]

    # Choose plot type based on density
    if len(mzs) < 500:
        graph_item = pg.BarGraphItem(
            x=mzs,
            height=intensities,
            width=0.2,
            pen=mkPen(color, width=2),
            brush=mkBrush(color),
            name=name,
        )
        widget.addItem(graph_item)
        plot_item = graph_item
    else:
        plot_item = widget.plot(
            mzs,
            intensities,
            pen=mkPen(color, width=2),
            brush=mkBrush(color),
            name=name,
        )

    # Peak Annotation
    _annotate_peaks(widget, mzs, intensities, count=5)

    return plot_item


def plot_annotated_LC(path: str, chromatogram: FrameHE, widget: pg.PlotWidget):
    """Annotates LC data with detected peaks."""
    filename = os.path.basename(path).split(".")[0]
    widget.clear()
    PlotStyle.apply_standard_style(
        widget,
        title=f"Chromatogram of {filename} (click peak to select)",
        x_label="Retention time (min)",
        y_label="Absorbance (mAU)",
    )

    # Convert to NumPy arrays immediately ---
    # StaticFrame Series struggle with pyqtgraph's internal type checks.
    # .values ensures we are working with raw numpy arrays, which are faster and safer here.
    time_arr = chromatogram["Time (min)"].values
    val_arr = chromatogram["Value (mAU)"].values

    # Base Chromatogram
    widget.plot(
        time_arr,
        val_arr,
        pen=mkPen("#dddddd", width=1),
    )

    # Peak Detection (on numpy array)
    lc_peaks, _ = find_peaks(val_arr, distance=10, prominence=10)

    if len(lc_peaks) == 0:
        return {}

    # Peak Widths
    widths, width_heights, left, right = peak_widths(val_arr, lc_peaks, rel_height=0.9)

    curve_dict = {}
    color_cycle = itertools.cycle(PlotStyle.PALETTE)

    for i, peak_idx in enumerate(lc_peaks):
        l_idx = int(left[i])
        r_idx = int(right[i])

        # Safety check for indices
        if l_idx < 0:
            l_idx = 0
        if r_idx >= len(time_arr):
            r_idx = len(time_arr) - 1

        # Slice the NumPy arrays (not the StaticFrame Series)
        time_segment = time_arr[l_idx:r_idx]
        val_segment = val_arr[l_idx:r_idx]

        # Skip empty segments
        if len(time_segment) == 0:
            continue

        current_color = next(color_cycle)
        pen = mkPen(current_color, width=1)
        brush = mkBrush(current_color)

        # Plot individual peak area
        plot_item = widget.plot(
            time_segment,
            val_segment,
            pen=pen,
            name=f"Peak {i}",
            fillLevel=1.0,
            brush=brush,
        )
        plot_item.setCurveClickable(True)
        curve_dict[plot_item.curve] = current_color

    return curve_dict


def plot_annotated_XICs(xics: tuple, widget: DockArea):
    """
    Plots XICs in a grid layout (5 columns).
    Safely handles missing ion_info or missing MS data.
    """

    docks = widget.findAll()[1]

    for compound in xics:
        try:
            plot_widget = docks[compound.name].widgets[0]
            plot_widget.clear()
        except KeyError:
            logger.error(f"No key {compound.name} found in dock area.")
            continue
        except AttributeError:
            logger.error("No plotItem found for dock.")
            continue
        except Exception as e:
            logger.error(e)
            continue
        color_cycle = itertools.cycle(PlotStyle.PALETTE)
        PlotStyle.apply_standard_style(
            plot_widget, x_label="Time (min)", y_label="Intensity (a.u.)"
        )

        # Safely access compound data
        ions_dict = getattr(compound, "ions", {})
        ion_info_list = getattr(compound, "ion_info", [])

        for j, (ion_key, ion_data) in enumerate(ions_dict.items()):
            ms_intensity = ion_data.get("MS Intensity")

            if ms_intensity is None:
                continue

            # Safe info string retrieval
            info_str = ion_info_list[j] if j < len(ion_info_list) else ""
            current_color = next(color_cycle)

            try:
                x_data = ms_intensity[0]
                y_data = ms_intensity[1]

                # Plot trace
                plot_widget.plot(
                    x_data,
                    y_data,
                    pen=mkPen(current_color, width=1),
                    name=f"{ion_key} {info_str}",
                )

                # Annotate Max
                if len(y_data) > 0:
                    max_idx = np.argmax(y_data)
                    max_time = x_data[max_idx]
                    max_val = y_data[max_idx]

                    plot_widget.plot(
                        [max_time],
                        [max_val],
                        pen=mkPen(current_color, width=1),
                        symbol="o",
                        symbolSize=5,
                        brush=mkBrush(current_color),
                    )

                    if info_str:
                        text_item = pg.TextItem(
                            text=info_str, color=current_color, anchor=(0, 0)
                        )
                        text_item.setFont(QFont("Helvetica", 10))
                        text_item.setPos(max_time, max_val)
                        plot_widget.addItem(text_item)

            except Exception as e:
                logger.warning(f"Failed to plot {ion_key} for {compound.name}: {e}")
                continue


def plot_calibration_curve(compound, widget: pg.PlotWidget):
    """Plots the calibration curve. Safely handles missing parameters."""
    widget.clear()
    PlotStyle.apply_standard_style(
        widget,
        title=f"Calibration: {compound.name}",
        x_label="Concentration (mM)",
        y_label="Intensity / a.u.",
    )

    # Validate Data
    cal_curve = getattr(compound, "calibration_curve", {})
    if not cal_curve:
        plot_placeholder(
            widget,
            '<p style="display: block; color: #d5d5d5; text-align: center; margin: auto">← Start by entering concentration values,<br> \
            click calculate, and calibration curves will appear here. </p>',
        )
        return

    x = np.array(list(cal_curve.keys()))
    y = np.array(list(cal_curve.values()))

    # Plot Scatter
    widget.plot(x, y, pen=None, symbol="o", symbolSize=7, symbolBrush="b", name="Data")

    # Validate Parameters for Line
    params = getattr(compound, "calibration_parameters", {})
    if params and "slope" in params and "intercept" in params:
        try:
            m = params["slope"]
            b = params["intercept"]
            r2 = params.get("r_value", 0) ** 2

            # Plot Line
            curve_y = m * x + b
            widget.plot(x, curve_y, pen=mkPen("r", width=2), name="Fit")

            # Annotation
            eq_text = f"y = {m:.2f}x + {b:.2f}\nR² = {r2:.4f}"
            text_item = pg.TextItem(
                text=eq_text, color="#3c5488", border=mkPen("#3c5488"), anchor=(0, 0)
            )
            text_item.setPos(np.min(x), np.max(y))
            widget.addItem(text_item)

        except Exception as e:
            logger.error(f"Error plotting calibration fit: {e}")
    else:
        logger.warning(f"No calibration parameters found for {compound.name}")


def plot_total_ion_current(
    widget: pg.PlotWidget, ms_measurement, filename: str, clear: bool = True
):
    """Plots TIC using pre-extracted data from MSMeasurement."""
    if clear:
        widget.clear()
    PlotStyle.apply_standard_style(
        widget,
        title=f"Total Ion Current (TIC): {filename}",
        x_label="Time (min)",
        y_label="Intensity (cps)",
    )

    # Use pre-extracted TIC data (no iteration needed - instant)
    if ms_measurement.tic_times is not None and len(ms_measurement.tic_times) > 0:
        widget.plot(
            ms_measurement.tic_times,
            ms_measurement.tic_values,
            pen=mkPen("#3c5488ff", width=1),
        )


def plot_ms2_from_file(ms_file, ms_compound, precursor: float, canvas: pg.PlotWidget):
    """Plots MS2 spectrum matching a precursor."""
    canvas.clear()

    if not ms_file or not ms_compound:
        plot_placeholder(canvas, "Invalid Data")
        return

    xics = getattr(ms_file, "xics", [])
    compound_to_plot = next((c for c in xics if c.name == ms_compound.name), None)

    if not compound_to_plot:
        plot_placeholder(canvas, "Compound not found in file")
        return

    # Find matching scan
    ms2_scans = getattr(compound_to_plot, "ms2", [])
    found_scan = None

    for scan in ms2_scans:
        try:
            selected_ion = scan["precursorList"]["precursor"][0]["selectedIonList"][
                "selectedIon"
            ][0]
            selected_mz = selected_ion["selected ion m/z"]
            if np.isclose(
                selected_mz, precursor, atol=0.005
            ):  # Increased tolerance slightly
                found_scan = scan
                break
        except (KeyError, IndexError, TypeError):
            continue

    if not found_scan:
        plot_no_ms2_found(canvas)
        return

    # Plot
    mzs = found_scan["m/z array"]
    intensities = found_scan["intensity array"]

    title = (
        f"{ms_file.filename}: MS2 of {ms_compound.name} (Precursor: {precursor:.2f})"
    )
    PlotStyle.apply_standard_style(
        canvas, title=title, x_label="m/z", y_label="Intensity (%)"
    )

    # Normalize
    max_int = np.max(intensities) if len(intensities) > 0 else 1
    rel_intensities = (intensities / max_int) * 100

    canvas.addItem(
        pg.BarGraphItem(x=mzs, height=rel_intensities, width=0.2, pen="b", brush="b")
    )

    # Annotate Top 5
    _annotate_peaks(canvas, mzs, rel_intensities, count=5)


def plot_no_ms2_found(widget: pg.PlotWidget):
    widget.clear()
    PlotStyle.apply_standard_style(widget, title="No MS2 spectrum found")
    plot_placeholder(widget, "No MS2 Data Found")


def plot_placeholder(widget: pg.PlotWidget, text: str):
    """Displays a centered placeholder text by setting any HTML input."""
    widget.clear()
    widget.setBackground("w")
    widget.getPlotItem().hideAxis("bottom")
    widget.getPlotItem().hideAxis("left")
    text_item = pg.TextItem(html=text, anchor=(0.5, 0.5))
    text_item.setFont(
        fonts.get_main_font(14)
        if hasattr(fonts, "get_main_font")
        else QFont("Arial", 14)
    )
    widget.addItem(text_item)


def plot_compound_integration(
    widget: pg.PlotWidget, compound, selected_ion: str = None
) -> dict:
    """
    Plot compound integration with XIC traces and integration boundaries.

    Parameters
    ----------
    widget : pg.PlotWidget
        The plot widget to draw on.
    compound : Compound
        The compound object containing ion data.
    selected_ion : str, optional
        The ion key to make editable. Only this ion will have movable boundary lines.
        Other ions will be shown with dashed, non-movable boundaries.

    Returns
    -------
    dict
        Dictionary mapping ion_key to curve reference for click handling.
    """
    widget.clear()
    widget.addLegend(labelTextSize="12pt")
    PlotStyle.apply_standard_style(
        widget,
        title=f"Integration of {compound.name}",
        x_label="Time (min)",
        y_label="Intensity / a.u.",
    )
    # Safely access compound data
    ions_dict = getattr(compound, "ions", {})
    ion_info_list = getattr(compound, "ion_info", [])

    curve_refs = {}  # Store curve references for click handling
    color_cycle = itertools.cycle(PlotStyle.PALETTE)

    for j, (ion_key, ion_data) in enumerate(ions_dict.items()):
        ms_intensity = ion_data.get("MS Intensity")
        integration_data = ion_data.get("Integration Data")

        if ms_intensity is None:
            continue

        # Safe info string retrieval
        info_str = ion_info_list[j] if j < len(ion_info_list) else ""
        current_color = next(color_cycle)

        # Determine if this ion is selected (editable)
        is_selected = selected_ion is not None and str(ion_key) == str(selected_ion)

        try:
            x_data = ms_intensity[0]
            y_data = ms_intensity[1]

            # Plot trace - make clickable for selection
            curve = widget.plot(
                x_data,
                y_data,
                pen=mkPen(current_color, width=2 if is_selected else 1),
                name=f"{ion_key} {info_str}",
            )
            # Make curve clickable
            curve.setCurveClickable(True)
            curve_refs[str(ion_key)] = curve

            # Annotate Max only for selected ion or if no ion selected
            if len(y_data) > 0:
                max_idx = np.argmax(y_data)
                max_time = x_data[max_idx]
                max_val = y_data[max_idx]

                if is_selected or selected_ion is None:
                    widget.plot(
                        [max_time],
                        [max_val],
                        pen=mkPen(current_color, width=1),
                        symbol="o",
                        symbolSize=5,
                        brush=mkBrush(current_color),
                    )

                # Configure line style based on selection
                if is_selected:
                    # Selected ion: solid lines, movable, with markers and labels
                    line_pen = mkPen(current_color, width=2)
                    line_style = Qt.PenStyle.SolidLine
                    movable = True
                    markers_left = [("|>", 0.5, 10.0)]
                    markers_right = [("<|", 0.5, 10.0)]
                    label_left = f"{ion_key} (LEFT)"
                    label_right = f"{ion_key} (RIGHT)"
                else:
                    # Non-selected ion: dashed lines, not movable, no markers/labels
                    line_pen = mkPen(current_color, width=1, style=Qt.PenStyle.DashLine)
                    line_style = Qt.PenStyle.DashLine
                    movable = False
                    markers_left = None
                    markers_right = None
                    label_left = None
                    label_right = None

                # Add left boundary line
                left_line = widget.getPlotItem().addLine(
                    x=integration_data["start_time"],
                    pen=line_pen,
                    hoverPen=mkPen("red", width=2) if is_selected else None,
                    label=label_left,
                    labelOpts={
                        "position": 0.7,
                        "color": current_color,
                        "rotateAxis": (1, 0),
                    }
                    if label_left
                    else None,
                    movable=movable,
                    bounds=[0, x_data[-1]] if movable else None,
                    markers=markers_left,
                    name=f"{ion_key}_left",
                )

                # Add right boundary line
                right_line = widget.getPlotItem().addLine(
                    x=integration_data["end_time"],
                    pen=line_pen,
                    hoverPen=mkPen("red", width=2) if is_selected else None,
                    label=label_right,
                    labelOpts={
                        "position": 0.7,
                        "color": current_color,
                        "rotateAxis": (1, 0),
                    }
                    if label_right
                    else None,
                    movable=movable,
                    bounds=[0, x_data[-1]] if movable else None,
                    markers=markers_right,
                    name=f"{ion_key}_right",
                )

                # Add text annotation only for selected or if no selection
                if info_str and (is_selected or selected_ion is None):
                    text_item = pg.TextItem(
                        text=info_str, color=current_color, anchor=(0, 0)
                    )
                    text_item.setFont(QFont("Helvetica", 12))
                    text_item.setPos(max_time, max_val)
                    widget.addItem(text_item)

        except Exception as e:
            logger.warning(f"Failed to plot {ion_key} for {compound.name}: {e}")
            continue

    return curve_refs


# --- Helper Functions ---


def _annotate_peaks(
    widget: pg.PlotWidget, mzs: np.array, intensities: np.array, count: int = 5
):
    """Helper to annotate the top N peaks in a spectrum."""
    if len(mzs) == 0:
        return

    # Find peaks to avoid labeling noise
    peaks_idx, _ = find_peaks(
        intensities, prominence=np.max(intensities) * 0.05
    )  # 5% prominence

    # If find_peaks returns nothing (sparse spectrum), just take raw maxes
    if len(peaks_idx) == 0:
        valid_mzs = mzs
        valid_ints = intensities
    else:
        valid_mzs = mzs[peaks_idx]
        valid_ints = intensities[peaks_idx]

    # Sort by intensity descending
    sorted_indices = np.argsort(valid_ints)[::-1]

    top_mzs = valid_mzs[sorted_indices][:count]
    top_ints = valid_ints[sorted_indices][:count]

    for mz, intensity in zip(top_mzs, top_ints):
        text = pg.TextItem(text=f"{mz:.4f}", color="#3c5488", anchor=(0.5, 1))
        text.setFont(QFont("Helvetica", 9))
        text.setPos(mz, intensity)
        widget.addItem(text)


def highlight_peak(
    selected_curve: pg.PlotCurveItem,
    curve_list: dict,
    canvas: pg.PlotWidget,
    xics: dict,
):
    # Clear previous annotations
    for curve in curve_list:
        if selected_curve != curve:
            color = QColor(curve_list[curve])
            color.setAlpha(50)
            curve.setBrush(color)
            curve.setPen(color)
    for item in canvas.items():
        if isinstance(item, pg.TextItem):
            canvas.removeItem(item)
    # Annotate the selected peak with every compound
    text_items = []
    for compound in xics:
        for j, ion in enumerate(compound.ions.keys()):
            if np.any(
                np.isclose(
                    compound.ions[ion]["RT"], selected_curve.getData()[0], atol=0.1
                )
            ):  # If the ion's RT overlaps with the RT of selected peak +/- 6 seconds
                text_item = pg.TextItem(
                    text=f"{compound.name} ({ion})", color="#242526", anchor=(0, 0)
                )
                text_item.setFont(
                    QFont("Helvetica", 12, weight=QFont.Weight.ExtraLight)
                )
                text_items.append(text_item)
                canvas.addItem(text_item)
    selected_curve.setBrush(pg.mkBrush("#ee6677"))
    selected_curve.setPen(pg.mkPen("#ee6677"))
    positions = np.linspace(
        np.max(selected_curve.getData()[1]) / 2,
        np.max(selected_curve.getData()[1]) + 400,
        20,
    )
    for i, text_item in enumerate(text_items):
        text_item.setPos(
            float(np.median(selected_curve.getData()[0] + i // 20)),
            float(positions[i % len(positions)]),
        )


def update_labels_avgMS(canvas):
    # Remove all the previous labels
    for item in canvas.items():
        if isinstance(item, pg.TextItem):
            canvas.removeItem(item)
    if canvas.getPlotItem().listDataItems():
        try:
            data = canvas.getPlotItem().listDataItems()[0].getData()
        except IndexError:
            logger.error(
                f"Error getting data items for MS viewing. {traceback.format_exc()}"
            )
            return
    else:
        return
    current_view_range = canvas.getViewBox().viewRange()
    # Get the intensity range within the current view range
    mz_range = data[0][
        np.logical_and(
            data[0] >= current_view_range[0][0], data[0] <= current_view_range[0][1]
        )
    ]
    indices = [i for i, x in enumerate(data[0]) if x in mz_range]
    intensity_range = data[1][indices]
    peaks, _ = find_peaks(intensity_range, prominence=10)
    if len(peaks) < 5:
        peaks, _ = find_peaks(intensity_range)
    # Get the 10 highest peaks within the current view range
    sorted_indices = np.argsort(intensity_range[peaks])[::-1]
    # Get their mz values
    mzs = mz_range[peaks][sorted_indices][0:10]
    intensities = intensity_range[peaks][sorted_indices][0:10]
    for mz, intensity in zip(mzs, intensities):
        text_item = pg.TextItem(text=f"{mz:.4f}", color="#242526", anchor=(0, 0))
        text_item.setFont(
            pg.QtGui.QFont("Helvetica", 10, weight=pg.QtGui.QFont.Weight.Normal)
        )
        text_item.setPos(mz, intensity)
        canvas.addItem(text_item)
