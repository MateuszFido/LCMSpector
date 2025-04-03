import os, time, logging
import numpy as np
import pandas as pd
import pyqtgraph as pg
from scipy.signal import find_peaks, peak_widths
from pyqtgraph import exporters, mkPen, mkBrush
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout
from pyqtgraph.dockarea import DockArea
from calculation.wrappers import freezeargs
from pyteomics.auxiliary import cvquery
from static_frame import FrameHE

logger = logging.getLogger(__name__)
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

    filename = os.path.basename(path).split('.')[0]

    # Plotting chromatogram before background correction
    widget.setBackground("w")
    widget.addLegend()
    widget.setTitle(f'LC chromatogram of {filename}')
    widget.plot(dataframe['Time (min)'], dataframe['Uncorrected'], pen=pg.mkPen('b', width=2), name='Before correction')
    widget.plot(dataframe['Time (min)'], dataframe['Baseline'], pen=pg.mkPen('r', width=2, style=Qt.PenStyle.DashLine), name='Baseline')
    widget.setLabel('left', 'Absorbance (mAU)')
    widget.setLabel('bottom', 'Time (min)')

    # Plotting chromatogram after background correction
    widget.plot(title='Chromatogram After Background Correction')
    widget.plot(dataframe['Time (min)'], dataframe['Value (mAU)'], pen=pg.mkPen('g', width=2), name='After correction')
    widget.setLabel('left', 'Absorbance (mAU)')
    widget.setLabel('bottom', 'Time (min)')


def plot_average_ms_data(rt: float, data_matrix: tuple, widget: pg.PlotWidget):
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
    
    scan_time_diff = np.abs([np.abs(cvquery(data_matrix[i], 'MS:1000016') - rt) for i in range(len(data_matrix))])
    index = np.argmin(scan_time_diff)
    widget.clear()
    # Plotting the average MS data
    widget.setBackground("w")
    widget.showGrid(x=True, y=True, alpha=0.2)
    if len(data_matrix[index]['m/z array']) < 500:
        # Plot as a histogram
        widget.addItem(pg.BarGraphItem(x=data_matrix[index]['m/z array'], height=data_matrix[index]['intensity array'], width=0.2, pen=mkPen('b', width=2), brush=mkBrush('b')))
    else:
        # Plot as a curve
        widget.plot(data_matrix[index]['m/z array'], data_matrix[index]['intensity array'], pen=mkPen('b', width=2))
    widget.getPlotItem().setTitle(f'MS1 full-scan spectrum at {round(rt, 2)} minutes', color='#b8b8b8', size='12pt')
    widget.setLabel('left', 'Intensity / a.u.')
    widget.setLabel('bottom', 'm/z')
    
    # Annotate the m/z of the 5 highest peaks
    mzs = data_matrix[index]['m/z array']
    intensities = data_matrix[index]['intensity array']
    peaks, _ = find_peaks(intensities, prominence=10)
    sorted_indices = np.argsort(intensities[peaks])[::-1]
    sorted_mzs = mzs[peaks][sorted_indices][0:10]
    sorted_intensities = intensities[peaks][sorted_indices][0:10]
    i = 0 
    while i < len(sorted_mzs) and sorted_mzs[i] in mzs[peaks][sorted_indices] and i < 10:
        text_item = pg.TextItem(text=f"{sorted_mzs[i]:.4f}", color='#232323', anchor=(0, 0))
        text_item.setPos(sorted_mzs[i], sorted_intensities[i])
        text_item.setFont(pg.QtGui.QFont('Arial', 10, weight=pg.QtGui.QFont.Weight.ExtraLight))
        widget.addItem(text_item)
        i += 1

def plot_annotated_LC(path: str, chromatogram: FrameHE, widget: pg.PlotWidget):
    '''
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
    '''
    filename = os.path.basename(path).split('.')[0]

    widget.clear()
    # Plot the LC data
    widget.setBackground("w")
    widget.setLabel('left', 'Absorbance (mAU)')
    widget.setLabel('bottom', 'Retention time (min)')
    widget.setTitle(f'Chromatogram of {filename} with annotations (click a peak to select it)')
    widget.plot(chromatogram['Time (min)'], chromatogram['Value (mAU)'], pen=mkPen('#dddddd', width=1))
    start_time = time.time()
    lc_peaks = find_peaks(chromatogram['Value (mAU)'], distance=10, prominence=10)        
    widths, width_heights, left, right = peak_widths(chromatogram['Value (mAU)'], lc_peaks[0], rel_height=0.9)
    chromatogram['Time (min)'][lc_peaks[0]]
    colors = ['#cc6677', '#332288', '#ddcc77', '#117733', '#88ccee', '#882255', '#44aa99', '#999933', '#aa4499']
    curve_dict = {}
    for i, peak_idx in enumerate(lc_peaks[0]):
        peak_curve = np.transpose(np.array((chromatogram['Time (min)'][int(left[i]):int(right[i])], chromatogram['Value (mAU)'][int(left[i]):int(right[i])])))
        pen = mkPen(colors[i % len(colors)], width=1)
        default_brush = pg.mkBrush(colors[i % len(colors)])
        plot_item = widget.plot(peak_curve, pen=pen, name=f'Peak {i}', fillLevel=1.0, brush=default_brush)
        plot_item.setCurveClickable(True)
        curve_dict[plot_item.curve] = default_brush

    logger.info(f"---Plotting annotated LC of {filename} took {(time.time() - start_time)/1000} miliseconds ---")
    return curve_dict

def plot_annotated_XICs(path: str, xics: tuple, widget: DockArea):
    filename = os.path.basename(path).split('.')[0]
    start_time = time.time()
    tot = len(xics)
    cols = 5
    int(np.ceil(2*tot / cols))

    # Plot the XICs
    for i, compound in enumerate(xics):
        if i % cols == 0:
            dock_0 = widget.addDock(position='bottom', name=f'{compound.name}', widget=pg.PlotWidget(), size=(100, 100))
            plot_item = dock_0.widgets[0]
        else:
            dock = widget.addDock(position='right', relativeTo=dock_0, name=f'{compound.name}', widget=pg.PlotWidget(), size=(100, 100))
            plot_item = dock.widgets[0]
        plot_item.setBackground("w")
        plot_item.setMouseEnabled(x=True, y=False)
        args = ({'color': 'b', 'font-size': '10pt'})
        plot_item.setLabel('bottom', text='Time (min)', **args)
        plot_item.setLabel('left', text='Intensity (a.u.)', **args)
        color_list = ('#a559aa', "#59a89c", "#f0c571", "#e02b35", "#082a54", '#9d2c00', '#7e4794', '#c8c8c8')
        plot_item.addLegend().setPos(0,0)
        for j, ion in enumerate(compound.ions.keys()):
            if compound.ions[ion]["MS Intensity"] is None:
                continue
            plotting_data = compound.ions[ion]["MS Intensity"]
            try:
                plot_item.plot(np.transpose(plotting_data), pen=mkPen(color_list[j], width=1), name=f'{ion} ({compound.ion_info[j]})')
                text_item = pg.TextItem(f"{compound.ion_info[j]}", color=color_list[j], anchor=(0, 0))
            except IndexError:
                plot_item.plot(np.transpose(plotting_data), pen=mkPen(color_list[j], width=1), name=f'{ion}')
                text_item = pg.TextItem(f"{ion}", color=color_list[j], anchor=(0, 0))
            highest_intensity = np.argmax(plotting_data[1])
            scan_time = plotting_data[0][highest_intensity]
            plot_item.plot([scan_time], [plotting_data[1][highest_intensity]], pen=mkPen(color_list[j], width=1), symbol='o', symbolSize=5)

            text_item.setFont(pg.QtGui.QFont('Arial', 10, weight=pg.QtGui.QFont.Weight.ExtraLight))
            text_item.setPos(scan_time, plotting_data[1][highest_intensity])
            plot_item.addItem(text_item)
            plot_item.getViewBox().enableAutoRange(axis='y', enable=True)
            plot_item.getViewBox().setAutoVisible(y=True)

    #HACK: Forces scrollArea to realize that the widget is bigger than it is
    widget.setMinimumSize(pg.QtCore.QSize(len(xics)*20,len(xics)*40))
    logger.info(f"---Plotting annotated XICs of {filename} took {(time.time() - start_time)/1000} miliseconds ---")

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
    x=list(compound.calibration_curve.keys())
    y=list(compound.calibration_curve.values())
    try:
        compound.calibration_parameters['slope']
        compound.calibration_parameters['intercept']
    except Exception as e:
        logger.error(f"---Error when trying to plot calibration curve for {compound.name} {e} ---")
        return
    m=int(round(compound.calibration_parameters['slope']))
    b=int(round(compound.calibration_parameters['intercept']))
    curve=np.array([m*x+b for x in x])
    widget.plot(x, y, name=compound.name, pen=None, symbol='o', symbolSize=5)
    widget.plot(x, curve, pen=mkPen('r', width=1))
    widget.plotItem.setTitle(f'Calibration curve for {compound.name}')
    widget.setLabel('left', 'Intensity / a.u.')
    widget.setLabel('bottom', 'Concentration (mM)')
    text_item = pg.TextItem(text=f"Curve equation:\ny = {m}\u22c5x+{b}\nR\u00b2 = {np.round(compound.calibration_parameters['r_value']**2, 4)}",
    color='#232323', border=pg.mkPen('#232323', width=1), anchor=(0, 0))
    text_item.setPos(np.min(x), np.max(y))
    text_item.setFont(pg.QtGui.QFont('Arial', 10, weight=pg.QtGui.QFont.Weight.ExtraLight))
    widget.addItem(text_item)
    widget.getPlotItem().vb.setAutoVisible(x=True, y=True)

def plot_total_ion_current(widget: pg.PlotWidget, ms_data: tuple, filename: str):
    widget.setBackground("w")
    widget.setTitle(f'Total ion chromatogram of {filename}')
    tic = []
    times = []
    for scan in ms_data:
        tic.append(scan['total ion current'])
        times.append(cvquery(scan, 'MS:1000016'))
    widget.plot(times, tic, pen=mkPen('b', width=1))
    widget.setLabel('left', 'Intensity (cps)')
    widget.setLabel('bottom', 'Time (min)')
    widget.addLegend()

def plot_ms2(library_entry: dict, compound, widget: pg.PlotWidget):
    # Reset the plot
    widget.clear()
    widget.getPlotItem().vb.enableAutoRange(axis='y', enable=True)
    widget.getPlotItem().vb.enableAutoRange(axis='x', enable=True)
    widget.getPlotItem().vb.setAutoVisible(x=True, y=True)
    widget.setBackground("w")
    widget.setTitle(f'MS2 spectrum of {compound.name}')
    mzs = []
    intensities = []
    for line in library_entry:
        try:
            mz = float(line.split(' ')[0])
            intensity = float(line.split(' ')[1])
        except ValueError:
            continue   
        mzs.append(mz)
        intensities.append(intensity)
    widget.addItem(pg.BarGraphItem(x=mzs, height=intensities, width=0.2, pen=mkPen('r', width=1), brush=mkBrush('r')))
    # Draw a flat black line at 0 intensity
    widget.plot([min(mzs), max(mzs)], [0, 0], pen=mkPen('k', width=1))
    widget.setLabel('left', 'Intensity (%)')
    widget.setLabel('bottom', 'm/z')

def plot_no_ms2_found(widget: pg.PlotWidget):
    widget.setBackground("w")
    widget.setTitle('No MS2 spectrum found')
    widget.setLabel('left', 'Intensity (%)')
    widget.setLabel('bottom', 'm/z')