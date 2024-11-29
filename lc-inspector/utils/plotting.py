import os, time, logging
from functools import lru_cache
from pathlib import Path
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
    widget.setTitle(f'LC chromatogram of {filename}')
    widget.plot(dataframe['Time (min)'], dataframe['Uncorrected'], pen=pg.mkPen('b', width=2), name='Before correction')
    widget.plot(dataframe['Time (min)'], dataframe['Baseline'], pen=pg.mkPen('r', width=2, style=Qt.PenStyle.DashLine), name='Baseline')
    widget.setLabel('left', 'Absorbance (mAU)')
    widget.setLabel('bottom', 'Time (min)')
    widget.addLegend()

    # Plotting chromatogram after background correction
    widget.plot(title='Chromatogram After Background Correction')
    widget.plot(dataframe['Time (min)'], dataframe['Value (mAU)'], pen=pg.mkPen('g', width=2), name='After correction')
    widget.setLabel('left', 'Absorbance (mAU)')
    widget.setLabel('bottom', 'Time (min)')
    widget.addLegend()


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
    start_time = time.time()
    scan_time_diff = np.abs([np.abs(cvquery(data_matrix[i], 'MS:1000016') - rt) for i in range(len(data_matrix))])
    index = np.argmin(scan_time_diff)
    widget.clear()
    # Plotting the average MS data
    widget.setBackground("w")
    widget.showGrid(x=True, y=True, alpha=0.2)
    curve = widget.plot(data_matrix[index]['m/z array'], data_matrix[index]['intensity array'], pen=mkPen('b', width=2))
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
    for i in range(0, 10):
        text_item = pg.TextItem(text=f"{sorted_mzs[i]:.4f}", color='#232323', anchor=(0, 0))
        text_item.setPos(sorted_mzs[i], sorted_intensities[i])
        text_item.setFont(pg.QtGui.QFont('Arial', 10, weight=pg.QtGui.QFont.Weight.ExtraLight))
        widget.addItem(text_item)

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
    lc_peaks_RTs = chromatogram['Time (min)'][lc_peaks[0]]
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
    rows = int(np.ceil(2*tot / cols))

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
            plot_item.plot(np.transpose(plotting_data), pen=mkPen(color_list[j], width=1), name=f'{ion} ({compound.ion_info[j]})')
            highest_intensity = np.argmax(plotting_data[1])
            scan_time = plotting_data[0][highest_intensity]
            plot_item.plot([scan_time], [plotting_data[1][highest_intensity]], pen=mkPen(color_list[j], width=1), symbol='o', symbolSize=5)

            text_item = pg.TextItem(f"{compound.ion_info[j]}", color=color_list[j], anchor=(0, 0))
            text_item.setFont(pg.QtGui.QFont('Arial', 10, weight=pg.QtGui.QFont.Weight.ExtraLight))
            text_item.setPos(scan_time, plotting_data[1][highest_intensity])
            plot_item.addItem(text_item)
            plot_item.getViewBox().enableAutoRange(axis='y', enable=True)
            plot_item.getViewBox().setAutoVisible(y=1.0)

    #HACK: Forces scrollArea to realize that the widget is bigger than it is
    widget.setMinimumSize(pg.QtCore.QSize(len(xics)*20,len(xics)*40))
    logger.info(f"---Plotting annotated XICs of {filename} took {(time.time() - start_time)/1000} miliseconds ---")

def plot_calibration_curve(compound, widget: pg.PlotWidget):
    widget.setBackground("w")
    #BUG: Calibration curve is None here
    print(compound.calibration_curve)
    x = [key for key in compound.calibration_curve.keys()]
    y = [value for value in compound.calibration_curve.values()]
    widget.plot(x=x, y=y, pen=mkPen('b', width=1), name=compound.name)
    widget.setWindowTitle(f'Calibration curve for {compound.name}')