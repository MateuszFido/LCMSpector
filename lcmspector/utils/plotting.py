import os
import time
import logging
from PySide6.QtGui import QFont
import numpy as np
import pandas as pd
import pyqtgraph as pg
from scipy.signal import find_peaks, peak_widths
from pyqtgraph import mkPen, mkBrush
from PySide6.QtCore import Qt
from pyqtgraph.dockarea import DockArea
from static_frame import FrameHE
from pyteomics.mzml import MzML
from ui import fonts

logger = logging.getLogger(__name__)
logger.propagate = False


def plot_absorbance_data(path: str, dataframe: pd.DataFrame, widget: pg.PlotWidget):
    """
    Generates and saves plots of absorbance data before and after background correction.

    The function creates two plots: the first plot shows the chromatogram before background correction,
    and the second plot shows the chromatogram after background correction. The plots are saved as SVG files
    in the specified directory.

    Parameters
    ----------
    path : str
        The path where the plot files will be saved. It is used to determine the directory for saving plots.

    dataframe : pd.DataFrame
        A pandas DataFrame containing the absorbance data. It must include the columns 'Time (min)',
        'Uncorrected', 'Baseline', and 'Value (mAU)'.

    Returns
    -------
    None
    """

    filename = os.path.basename(path).split(".")[0]
    default_family = fonts.get_family_name()

    args = {"color": "#2C2D2D", "font-size": "12pt", "font-family": default_family}
    # Plotting chromatogram before background correction
    widget.setBackground("w")
    widget.addLegend()
    widget.setTitle(f"{filename}")
    widget.plot(
        dataframe["Time (min)"],
        dataframe["Uncorrected"],
        pen=pg.mkPen("#333333", width=2),
        name="Before correction",
    )
    widget.plot(
        dataframe["Time (min)"],
        dataframe["Baseline"],
        pen=pg.mkPen("#FF5C5C", width=2, style=Qt.PenStyle.DashLine),
        name="Baseline",
    )
    widget.setLabel("left", "Absorbance (mAU)", **args)
    widget.setLabel("bottom", "Time (min)", **args)

    # Plotting chromatogram after background correction
    widget.plot(title=f"{filename} after background correction")
    widget.plot(
        dataframe["Time (min)"],
        dataframe["Value (mAU)"],
        pen=pg.mkPen("#2EC4B6", width=2),
        name="After correction",
    )
    widget.setLabel("left", "Absorbance (mAU)", **args)
    widget.setLabel("bottom", "Time (min)", **args)


def plot_average_ms_data(rt: float, data_matrix: MzML, widget: pg.PlotWidget):
    """
    Plots the average MS data and annotates it with the m/z of the 5 highest peaks.

    Parameters
    ----------
    path : Path
        The path to the .mzML file used for naming and saving the plot.
    data_matrix : pd.DataFrame
        The DataFrame containing the m/z and intensity values.

    Returns
    -------
    None
    """

    default_font = fonts.get_main_font(11)
    default_family = fonts.get_family_name()

    try:
        spectrum = data_matrix.time[rt]
    except ValueError:
        try:
            spectrum = data_matrix.time[0]
        except IndexError:
            logger.error("MzML file is empty.")
            return

    widget.clear()
    # Plotting the average MS data
    widget.setBackground("w")
    if len(spectrum["m/z array"]) < 500:
        # Plot as a histogram
        widget.addItem(
            pg.BarGraphItem(
                x=spectrum["m/z array"],
                height=spectrum["intensity array"],
                width=0.2,
                pen=mkPen("#3c5488ff", width=2),
                brush=mkBrush("#3c5488ff"),
            )
        )
    else:
        # Plot as a curve
        widget.plot(
            spectrum["m/z array"],
            spectrum["intensity array"],
            pen=mkPen("#3c5488ff", width=2),
            brush=mkBrush("#3c5488ff"),
        )
    if widget.getPlotItem():
        widget.getPlotItem().setTitle(
            f"Scan {spectrum['id']} MS{spectrum['ms level']} at {round(rt, 2)} mins",
            color="#2C2D2D",
            size="11pt",
        )
    args = {"color": "#2C2D2D", "font-family": default_family, "font-size": "11pt"}
    widget.setLabel("left", "Intensity / a.u.", **args)
    widget.getAxis("left").setTextPen("#2C2D2D", width=2)
    widget.getAxis("left").setStyle(tickFont="Helvetica", maxTickLevel=1)
    widget.getAxis("left").setTickPen("#2C2D2D", width=2)
    widget.getAxis("left").setFont(default_font)
    widget.getAxis("left").setTickFont(default_font)
    widget.setLabel("bottom", "m/z", **args)
    widget.getAxis("bottom").setTextPen("#2C2D2D", width=2)
    widget.getAxis("bottom").setStyle(tickFont="Helvetica", maxTickLevel=1)
    widget.getAxis("bottom").setTickPen("#2C2D2D", width=2)
    widget.getAxis("bottom").setFont(default_font)
    widget.getAxis("bottom").setTickFont(default_font)

    # Annotate the m/z of the 5 highest peaks
    mzs = spectrum["m/z array"]
    intensities = spectrum["intensity array"]
    peaks, _ = find_peaks(intensities, prominence=10)
    sorted_indices = np.argsort(intensities[peaks])[::-1]
    sorted_mzs = mzs[peaks][sorted_indices][0:10]
    sorted_intensities = intensities[peaks][sorted_indices][0:10]
    i = 0
    while (
        i < len(sorted_mzs) and sorted_mzs[i] in mzs[peaks][sorted_indices] and i < 10
    ):
        text_item = pg.TextItem(
            text=f"{sorted_mzs[i]:.4f}", color="#3c5488ff", anchor=(0, 0)
        )
        text_item.setPos(sorted_mzs[i], sorted_intensities[i])
        text_item.setFont(default_font)
        widget.addItem(text_item)
        i += 1


def plot_annotated_LC(path: str, chromatogram: FrameHE, widget: pg.PlotWidget):
    """
    Annotates the LC data with the given targeted list of ions and plot the results.

    Parameters
    ----------
    path : str
        The path to the .mzML file.

    chromatogram : pd.DataFrame
        The DataFrame containing the LC data.

    Returns
    -------
    None
    """
    filename = os.path.basename(path).split(".")[0]

    widget.clear()
    # Plot the LC data
    widget.setBackground("w")
    widget.setLabel("left", "Absorbance (mAU)")
    widget.setLabel("bottom", "Retention time (min)")
    widget.setTitle(
        f"Chromatogram of {filename} with annotations (click a peak to select it)"
    )
    widget.plot(
        chromatogram["Time (min)"],
        chromatogram["Value (mAU)"],
        pen=mkPen("#dddddd", width=1),
    )
    start_time = time.time()
    lc_peaks = find_peaks(chromatogram["Value (mAU)"], distance=10, prominence=10)
    widths, width_heights, left, right = peak_widths(
        chromatogram["Value (mAU)"], lc_peaks[0], rel_height=0.9
    )
    chromatogram["Time (min)"][lc_peaks[0]]
    colors = [
        "#cc6677",
        "#332288",
        "#ddcc77",
        "#117733",
        "#88ccee",
        "#882255",
        "#44aa99",
        "#999933",
        "#aa4499",
    ]
    curve_dict = {}
    for i, peak_idx in enumerate(lc_peaks[0]):
        peak_curve = np.transpose(
            np.array(
                (
                    chromatogram["Time (min)"][int(left[i]) : int(right[i])],
                    chromatogram["Value (mAU)"][int(left[i]) : int(right[i])],
                )
            )
        )
        pen = mkPen(colors[i % len(colors)], width=1)
        default_brush = pg.mkBrush(colors[i % len(colors)])
        plot_item = widget.plot(
            peak_curve, pen=pen, name=f"Peak {i}", fillLevel=1.0, brush=default_brush
        )
        plot_item.setCurveClickable(True)
        curve_dict[plot_item.curve] = default_brush.color()
    return curve_dict


def plot_annotated_XICs(path: str, xics: tuple, widget: DockArea):
    filename = os.path.basename(path).split(".")[0]
    start_time = time.time()
    tot = len(xics)
    cols = 5
    int(np.ceil(2 * tot / cols))

    # Plot the XICs
    for i, compound in enumerate(xics):
        if i % cols == 0:
            dock_0 = widget.addDock(
                position="bottom",
                name=f"{compound.name}",
                widget=pg.PlotWidget(),
                size=(100, 100),
            )
            plot_item = dock_0.widgets[0]
        else:
            dock = widget.addDock(
                position="right",
                relativeTo=dock_0,
                name=f"{compound.name}",
                widget=pg.PlotWidget(),
                size=(100, 100),
            )
            plot_item = dock.widgets[0]
        plot_item.setBackground("w")
        plot_item.setMouseEnabled(x=True, y=False)
        args = {"color": "#2C2D2D", "font-size": "10pt"}
        plot_item.setLabel("bottom", text="Time (min)", **args)
        plot_item.setLabel("left", text="Intensity (a.u.)", **args)
        color_list = (
            "#e25759",
            "#0b81a2",
            "#7e4794",
            "#59a89c",
            "#9d2c00",
            "#36b700",
            "#f0c571",
            "#c8c8c8",
            "#e25759",
            "#0b81a2",
            "#7e4794",
            "#59a89c",
            "#9d2c00",
            "#36b700",
            "#f0c571",
            "#c8c8c8",
        )
        plot_item.addLegend().setPos(0, 0)
        for j, ion in enumerate(compound.ions.keys()):
            if j >= len(color_list):
                break
            if compound.ions[ion]["MS Intensity"] is None:
                continue
            plotting_data = compound.ions[ion]["MS Intensity"]
            try:
                plot_item.plot(
                    np.transpose(plotting_data),
                    pen=mkPen(color_list[j], width=1),
                    name=f"{ion} ({compound.ion_info[j]})",
                )
                text_item = pg.TextItem(
                    f"{compound.ion_info[j]}", color=color_list[j], anchor=(0, 0)
                )
            except Exception as e:
                logger.warning(f"Failed to plot {ion} ({compound.ion_info[j]}): {e}")
                continue
            highest_intensity = np.argmax(plotting_data[1])
            scan_time = plotting_data[0][highest_intensity]
            plot_item.plot(
                [scan_time],
                [plotting_data[1][highest_intensity]],
                pen=mkPen(color_list[j], width=1),
                symbol="o",
                symbolSize=5,
            )

            text_item.setFont(pg.QtGui.QFont("Helvetica", 10))
            text_item.setPos(scan_time, plotting_data[1][highest_intensity])
            plot_item.addItem(text_item)
            plot_item.getViewBox().enableAutoRange(axis="y", enable=True)
            plot_item.getViewBox().setAutoVisible(y=True)

    # HACK: Forces scrollArea to realize that the widget is bigger than it is
    widget.setMinimumSize(pg.QtCore.QSize(len(xics) * 20, len(xics) * 40))
    logger.info(
        f"Plotting annotated XICs of {filename} took {(time.time() - start_time) / 1000} miliseconds ({tot} XICs)"
    )


def plot_calibration_curve(compound, widget: pg.PlotWidget):
    """
    Plots the calibration curve of a compound.

    Parameters
    ----------
    compound : utils.classes.Compound
        The compound to plot the calibration curve for.

    widget : pyqtgraph.PlotWidget
        The widget to plot the calibration curve in.

    Notes
    -----
    The calibration curve is calculated using the calibration equation saved in the
    compound object. The function will fail if the compound object is missing this
    information.

    """

    widget.setBackground("w")
    x = np.array(list(compound.calibration_curve.keys()))
    y = np.array(list(compound.calibration_curve.values()))
    try:
        compound.calibration_parameters
    except AttributeError as e:
        logger.error(
            f"---Error when trying to plot calibration curve for {compound.name}: {e} ---"
        )
        return
    if not all(k in compound.calibration_parameters for k in ("slope", "intercept")):
        logger.error(
            f"---Error when trying to plot calibration curve for {compound.name} ---"
        )
        return
    try:
        m = int(round(compound.calibration_parameters["slope"]))
        b = int(round(compound.calibration_parameters["intercept"]))
    except Exception as e:
        logger.error(
            f"---Error when trying to plot calibration curve for {compound.name}: {e} ---"
        )
        return

    curve = m * x + b
    widget.plot(x, y, name=compound.name, pen=None, symbol="o", symbolSize=5)
    widget.plot(x, curve, pen=mkPen("r", width=1))
    widget.setTitle(f"Calibration curve for {compound.name}")
    widget.setLabel("left", "Intensity / a.u.")
    widget.setLabel("bottom", "Concentration (mM)")

    text_item = pg.TextItem(
        text=f"Curve equation:\ny = {m}\u22c5x+{b}\nR\u00b2 = {np.round(compound.calibration_parameters['r_value'] ** 2, 4)}",
        color="#3c5488ff",
        border=pg.mkPen("#3c5488ff", width=1),
        anchor=(0, 0),
    )
    text_item.setPos(np.min(x), np.max(y))
    text_item.setFont(default_font)
    widget.addItem(text_item)
    widget.getPlotItem().vb.setAutoVisible(x=True, y=True)


def plot_total_ion_current(widget: pg.PlotWidget, ms_data: tuple, filename: str):
    default_font = fonts.get_main_font()
    default_family = fonts.get_family_name()
    widget.setBackground("w")
    widget.addLegend()
    widget.setTitle(
        f"Total ion current (TIC) of {filename}",
        color="#2C2D2D",
        size="12pt",
        font="Helvetica",
    )
    tic = []
    times = []
    for scan in ms_data:
        tic.append(scan["total ion current"])
        times.append(scan["scanList"]["scan"][0]["scan start time"])

    args = {"color": "#2C2D2D", "font-size": "11pt", "font-family": default_family}
    widget.plot(times, tic, pen=mkPen("#3c5488ff", width=1))
    widget.getAxis("left").setTextPen("#2C2D2D", width=2)
    widget.getAxis("left").setStyle(tickFont="Helvetica", maxTickLevel=1)
    widget.getAxis("left").setTickPen("#2C2D2D", width=2)
    widget.getAxis("left").setFont(default_font)
    widget.getAxis("left").setTickFont(default_font)
    widget.setLabel(
        "left",
        "Intensity",
        "cps",
        **args,
    )
    widget.setLabel("bottom", "Time (min)", **args)
    widget.getAxis("bottom").setTextPen("#2C2D2D", width=2)
    widget.getAxis("bottom").setStyle(tickFont="Helvetica", maxTickLevel=1)
    widget.getAxis("bottom").setTickPen("#2C2D2D", width=2)
    widget.getAxis("bottom").setFont(default_font)
    widget.getAxis("bottom").setTickFont(default_font)


def plot_library_ms2(library_entry: tuple, widget: pg.PlotWidget):
    """Plot an MS2 spectrum from a library entry."""
    # Reset the plot
    widget.clear()
    widget.setBackground("w")
    widget.setTitle(
        f"Library MS2 spectrum of {library_entry[0].split('Name: ', 1)[1].partition('\n')[0]}",
        color="#2C2D2D",
        size="12pt",
    )
    if not library_entry:
        return

    mzs = []
    intensities = []
    for line in library_entry:
        try:
            mz, intensity = map(float, line.split(" ")[:2])
        except ValueError:
            continue
        mzs.append(mz)
        intensities.append(intensity)

    if not mzs or not intensities:
        return
    else:
        # turn mzs and intensities into np arrays
        mzs = np.array(mzs)
        intensities = np.array(intensities)

    widget.addItem(
        pg.BarGraphItem(
            x=mzs,
            height=intensities,
            width=0.2,
            pen=mkPen("r", width=1),
            brush=mkBrush("r"),
        ),
        name="Library spectrum",
    )
    # Draw a flat black line at 0 intensity
    widget.plot([min(mzs), max(mzs)], [0, 0], pen=mkPen("k", width=0.5))

    # Add labels to top 5 peaks
    top_5 = sorted(zip(mzs, intensities), key=lambda x: x[1])[:5]
    for i, (mz, intensity) in enumerate(top_5):
        text_item = pg.TextItem(text=f"{mz:.4f}", color="#3c5488ff", anchor=(0, 0))
        text_item.setPos(mz, intensity)
        text_item.setFont(
            pg.QtGui.QFont("Helvetica", 10, weight=pg.QtGui.QFont.Weight.ExtraLight)
        )
        widget.addItem(text_item)

    widget.setLabel("left", "Intensity (%)")
    widget.setLabel("bottom", "m/z")


def plot_ms2_from_file(ms_file, ms_compound, precursor: float, canvas: pg.PlotWidget):
    canvas.clear()
    canvas.setBackground("w")
    if not ms_file:
        logger.error("plot_ms2_from_file: ms_file is None")
        raise Exception
        return

    if not ms_compound:
        logger.error("plot_ms2_from_file: ms_compound is None")
        raise Exception
        return

    try:
        xics = ms_file.xics
    except AttributeError:
        logger.error("plot_ms2_from_file: ms_file.xics is None")
        return

    compound_to_plot = next((xic for xic in xics if xic.name == ms_compound.name), None)

    if not compound_to_plot:
        logger.error("plot_ms2_from_file: compound_to_plot is None")
        raise Exception
        return

    mzs = []
    intensities = []

    ms2_scans = compound_to_plot.ms2
    if not ms2_scans:
        logger.error(
            f"plot_ms2_from_file: ms2_scans is None for {ms_compound.name} in {ms_file.filename}"
        )
        return

    for scan in ms2_scans:
        try:
            if np.isclose(
                scan["precursorList"]["precursor"][0]["selectedIonList"]["selectedIon"][
                    0
                ]["selected ion m/z"],
                precursor,
                atol=0.0005,
            ):
                mzs = scan["m/z array"]
                intensities = scan["intensity array"]
                break
        except TypeError as e:
            logger.error(f"plot_ms2_from_file: TypeError {e} in {ms_file.filename}")
            continue
        except KeyError as e:
            logger.error(f"plot_ms2_from_file: KeyError {e} in {ms_file.filename}")
            continue
        mzs.append(scan["m/z array"])
        intensities.append(scan["intensity array"])

    try:
        mzs = np.concatenate(mzs)
        intensities = np.concatenate(intensities)
    except ValueError as e:
        logger.error(f"plot_ms2_from_file: ValueError: {e} in {ms_file.filename}")
        plot_no_ms2_found(canvas)
        return

    canvas.setTitle(f"{ms_file.filename}: MS2 spectrum of {ms_compound.name}")
    canvas.addItem(
        pg.BarGraphItem(
            x=mzs,
            height=intensities / np.max(intensities) * 100,
            width=0.2,
            pen=mkPen("b", width=1),
            brush=mkBrush("b"),
            name=f"{ms_file}",
        )
    )
    canvas.plot([min(mzs), max(mzs)], [0, 0], pen=mkPen("k", width=0.5))

    top_5 = sorted(zip(mzs, intensities), key=lambda x: x[1], reverse=True)[:5]
    for i, (mz, intensity) in enumerate(top_5):
        try:
            text_item = pg.TextItem(text=f"{mz:.4f}", color="#3c5488ff", anchor=(0, 0))
        except TypeError as e:
            logger.error(
                f"plot_ms2_from_file: TypeError {e} when creating text item for peak {mz} in {ms_file.filename}"
            )
            continue
        text_item.setPos(mz, intensity / np.max(intensities) * 100)
        text_item.setFont(pg.QtGui.QFont("Helvetica", 10))
        canvas.addItem(text_item)

    canvas.setLabel("left", "Intensity (%)")
    canvas.setLabel("bottom", "m/z")
    logger.info(
        f"Plotting MS2 for {ms_compound.name} (m/z {precursor:.4f}) in {ms_file.filename}"
    )


def plot_no_ms2_found(widget: pg.PlotWidget):
    widget.setBackground("w")
    widget.setTitle("No MS2 spectrum found")
    widget.setLabel("left", "Intensity (%)")
    widget.setLabel("bottom", "m/z")


def plot_placeholder(widget: pg.PlotWidget, text: str):
    default_font = fonts.get_main_font(14)
    widget.setBackground("w")
    widget.getPlotItem().hideAxis("bottom")
    widget.getPlotItem().hideAxis("left")
    text_item = pg.TextItem(text=text, color="#c5c5c5", anchor=(0.5, 0.5))
    text_item.setFont(default_font)
    widget.addItem(text_item)
