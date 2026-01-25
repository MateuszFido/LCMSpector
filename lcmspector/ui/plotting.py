import os
import time
import logging
import itertools
from typing import Optional, List, Any

from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import Qt, QSize
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
        widget.setBackground(PlotStyle.BACKGROUND)
        widget.setTitle(title, color=PlotStyle.TEXT_COLOR, size="12pt")

        label_style = {"color": PlotStyle.TEXT_COLOR, "font-size": "12pt"}
        widget.setLabel("bottom", x_label, **label_style)
        widget.setLabel("left", y_label, **label_style)

        # Axis styling
        for axis_name in ["left", "bottom"]:
            axis = widget.getAxis(axis_name)
            axis.setTextPen(PlotStyle.TEXT_COLOR)
            axis.setTickPen(PlotStyle.AXIS_PEN)
            axis.setStyle(tickFont=fonts.get_main_font(12))


# --- Plotting Functions ---


def plot_absorbance_data(path: str, dataframe: pd.DataFrame, widget: pg.PlotWidget):
    """Generates plots of absorbance data before and after background correction."""
    filename = os.path.basename(path).split(".")[0]

    # Clear previous content just in case
    widget.clear()
    PlotStyle.apply_standard_style(
        widget, title=filename, x_label="Time (min)", y_label="Absorbance (mAU)"
    )
    widget.addLegend(labelTextSize="12pt")

    # Plot Uncorrected
    widget.plot(
        dataframe["Time (min)"],
        dataframe["Uncorrected"],
        pen=mkPen("#333333", width=2),
        name="Before correction",
    )

    # Plot Baseline
    widget.plot(
        dataframe["Time (min)"],
        dataframe["Baseline"],
        pen=mkPen("#FF5C5C", width=2, style=Qt.PenStyle.DashLine),
        name="Baseline",
    )

    # Plot Corrected
    widget.plot(
        dataframe["Time (min)"],
        dataframe["Value (mAU)"],
        pen=mkPen("#2EC4B6", width=2),
        name="After correction",
    )


def plot_average_ms_data(
    filename: str, rt: float, data_matrix: MzML, widget: pg.PlotWidget
):
    """Plots the average MS data and annotates peaks."""
    try:
        spectrum = data_matrix.time[rt]
    except (ValueError, IndexError):
        # Fallback to first scan or fail gracefully
        try:
            spectrum = data_matrix.time[0]
        except IndexError:
            logger.error("MzML file is empty.")
            return

    widget.clear()
    title = f"{filename}\n{spectrum.get('id', 'Scan')} MS{spectrum.get('ms level', '')} at {round(rt, 2)} mins"
    PlotStyle.apply_standard_style(
        widget, title=title, x_label="m/z", y_label="Intensity / a.u."
    )

    mzs = spectrum["m/z array"]
    intensities = spectrum["intensity array"]

    # Choose plot type based on density
    if len(mzs) < 500:
        graph_item = pg.BarGraphItem(
            x=mzs,
            height=intensities,
            width=0.2,
            pen=mkPen("#3c5488ff", width=2),
            brush=mkBrush("#3c5488ff"),
        )
        widget.addItem(graph_item)
    else:
        widget.plot(
            mzs,
            intensities,
            pen=mkPen("#3c5488ff", width=2),
            brush=mkBrush("#3c5488ff"),
        )

    # Peak Annotation
    _annotate_peaks(widget, mzs, intensities, count=5)


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
        plot_placeholder(widget, "No Calibration Data")
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


def plot_total_ion_current(widget: pg.PlotWidget, ms_data: List[dict], filename: str):
    """Plots TIC."""
    widget.clear()
    PlotStyle.apply_standard_style(
        widget,
        title=f"Total Ion Current (TIC): {filename}",
        x_label="Time (min)",
        y_label="Intensity (cps)",
    )

    tic = []
    times = []

    for scan in ms_data:
        try:
            curr_tic = scan.get("total ion current", 0)

            # Scan start time extraction can be tricky depending on parser
            scan_list = scan.get("scanList", {}).get("scan", [{}])[0]
            curr_time = scan_list.get("scan start time", 0)

            tic.append(curr_tic)
            times.append(curr_time)
        except (KeyError, IndexError):
            continue

    if times and tic:
        widget.plot(times, tic, pen=mkPen("#3c5488ff", width=1))


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
    """Displays a centered placeholder text."""
    widget.clear()
    widget.setBackground("w")
    widget.getPlotItem().hideAxis("bottom")
    widget.getPlotItem().hideAxis("left")
    text_item = pg.TextItem(text=text, color="#c5c5c5", anchor=(0.5, 0.5))
    text_item.setFont(
        fonts.get_main_font(14)
        if hasattr(fonts, "get_main_font")
        else QFont("Arial", 14)
    )
    widget.addItem(text_item)


def plot_library_ms2():
    pass


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
