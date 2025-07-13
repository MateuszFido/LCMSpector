import os, time, logging
import numpy as np
import pandas as pd
import pyqtgraph as pg
from scipy.signal import find_peaks, peak_widths
from pyqtgraph import exporters, mkPen, mkBrush
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout
from pyqtgraph.dockarea import DockArea
from pyteomics.auxiliary import cvquery
from static_frame import FrameHE

logger = logging.getLogger(__name__)
logger.propagate = False

def plot_absorbance_data(path, dataframe, widget):
    """Plots absorbance data"""
    filename = os.path.basename(path).split('.')[0]
    widget.setBackground("w")
    widget.addLegend()
    widget.setTitle(f'LC chromatogram of {filename}')
    widget.plot(dataframe['Time (min)'], dataframe['Uncorrected'], pen=pg.mkPen('b', width=2), name='Before correction')
    widget.plot(dataframe['Time (min)'], dataframe['Baseline'], pen=pg.mkPen('r', width=2, style=Qt.PenStyle.DashLine), name='Baseline')
    widget.setLabel('left', 'Absorbance (mAU)')
    widget.setLabel('bottom', 'Time (min)')
    widget.plot(title='Chromatogram After Background Correction')
    widget.plot(dataframe['Time (min)'], dataframe['Value (mAU)'], pen=pg.mkPen('g', width=2), name='After correction')
    widget.setLabel('left', 'Absorbance (mAU)')
    widget.setLabel('bottom', 'Time (min)')

def plot_average_ms_data(rt, data_matrix, widget):
    """Plots MS data at a specific retention time"""
    logger.info(f"Plotting average MS data at RT {rt}")
    if not data_matrix:
        logger.error("Empty data_matrix")
        return
    
    logger.info(f"Data matrix contains {len(data_matrix)} scans")
    
    # Calculate time differences for each scan
    scan_time_diff = []
    valid_indices = []
    
    for i in range(len(data_matrix)):
        if data_matrix[i] is None:
            logger.warning(f"Scan at index {i} is None")
            continue
        try:
            # Extract the scan time
            scan_time = data_matrix[i]['retention_time']
            if scan_time is None:
                logger.warning(f"Scan time at index {i} is None")
                continue
                
            time_diff = abs(scan_time - rt)
            scan_time_diff.append(time_diff)
            valid_indices.append(i)
        except Exception as e:
            logger.error(f"Error calculating scan time diff for index {i}: {e}")
            logger.error(f"Scan data: {data_matrix[i]}")
            continue
    
    logger.info(f"Found {len(valid_indices)} valid scans")
    try:
        min_index = np.argmin(scan_time_diff)
        index = valid_indices[min_index]
    except Exception as e:
        logger.error(f"Error finding minimum time difference: {e}")
        if valid_indices:
            index = valid_indices[0]
        else:
            return
    widget.clear()
    # Plotting the average MS data
    widget.setBackground("w")
    try:
        if data_matrix[index] is None:
            logger.error(f"Data at index {index} is None")
            return
    except IndexError:
        logger.error(f"Index {index} out of range for data_matrix with length {len(data_matrix)}")
        return
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
    while i < len(sorted_mzs) and i < 10:
        text_item = pg.TextItem(text=f"{sorted_mzs[i]:.4f}", color='#232323', anchor=(0, 0))
        text_item.setPos(sorted_mzs[i], sorted_intensities[i])
        text_item.setFont(pg.QtGui.QFont('Helvetica', 10, weight=pg.QtGui.QFont.Weight.ExtraLight))
        widget.addItem(text_item)
        i += 1

def plot_annotated_LC(path, chromatogram, widget):
    """Annotates and plots LC data"""
    filename = os.path.basename(path).split('.')[0]
    widget.clear()
    widget.setBackground("w")
    widget.setLabel('left', 'Absorbance (mAU)')
    widget.setLabel('bottom', 'Retention time (min)')
    widget.setTitle(f'Chromatogram of {filename} with annotations (click a peak to select it)')
    widget.plot(chromatogram['Time (min)'], chromatogram['Value (mAU)'], pen=mkPen('#dddddd', width=1))
    start_time = time.time()
    lc_peaks = find_peaks(chromatogram['Value (mAU)'], distance=10, prominence=10)        
    widths, width_heights, left, right = peak_widths(chromatogram['Value (mAU)'], lc_peaks[0], rel_height=0.9)
    colors = ['#cc6677', '#332288', '#ddcc77', '#117733', '#88ccee', '#882255', '#44aa99', '#999933', '#aa4499']
    curve_dict = {}
    for i, peak_idx in enumerate(lc_peaks[0]):
        peak_curve = np.transpose(np.array((chromatogram['Time (min)'][int(left[i]):int(right[i])], chromatogram['Value (mAU)'][int(left[i]):int(right[i])])))
        pen = mkPen(colors[i % len(colors)], width=1)
        default_brush = pg.mkBrush(colors[i % len(colors)])
        plot_item = widget.plot(peak_curve, pen=pen, name=f'Peak {i}', fillLevel=1.0, brush=default_brush)
        plot_item.setCurveClickable(True)
        curve_dict[plot_item.curve] = default_brush
    logger.info(f"Plotting annotated LC of {filename} took {(time.time() - start_time)/1000} miliseconds")
    return curve_dict

def plot_annotated_XICs(path, xics, widget):
    """Plots XICs from MS data"""
    filename = os.path.basename(path).split('.')[0]
    logger.info(f"Plotting XICs for {filename}")
    
    if not xics:
        logger.error(f"XICs is None or empty for {filename}")
        return
    
    tot = len(xics)
    cols = 5
    
    # Debug: inspect compounds and their ions
    for compound_idx, compound in enumerate(xics):
        logger.info(f"Compound {compound_idx}: {compound.name}")
        for ion, data in compound.ions.items():
            if data["MS Intensity"] is None:
                logger.warning(f"  Ion {ion} has None MS Intensity")
            else:
                logger.info(f"  Ion {ion} has MS Intensity with shape: {np.shape(data['MS Intensity'])}")

    # Plot the XICs
    for i, compound in enumerate(xics):
        try:
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
                if len(plotting_data) != 2 or len(plotting_data[0]) == 0 or len(plotting_data[1]) == 0:
                    continue
                    
                try:
                    plot_item.plot(np.transpose(plotting_data), pen=mkPen(color_list[j % len(color_list)], width=1), name=f'{ion} ({compound.ion_info[j]})')
                    text_item = pg.TextItem(f"{compound.ion_info[j]}", color=color_list[j % len(color_list)], anchor=(0, 0))
                except IndexError:
                    plot_item.plot(np.transpose(plotting_data), pen=mkPen(color_list[j % len(color_list)], width=1), name=f'{ion}')
                    text_item = pg.TextItem(f"{ion}", color=color_list[j % len(color_list)], anchor=(0, 0))
                except Exception as e:
                    logger.error(f"Error plotting XIC for ion {ion}: {e}")
                    continue
                
                try:
                    highest_intensity = np.argmax(plotting_data[1])
                    scan_time = plotting_data[0][highest_intensity]
                    plot_item.plot([scan_time], [plotting_data[1][highest_intensity]], pen=mkPen(color_list[j % len(color_list)], width=1), symbol='o', symbolSize=5)
                    text_item.setFont(pg.QtGui.QFont('Arial', 10, weight=pg.QtGui.QFont.Weight.ExtraLight))
                    text_item.setPos(scan_time, plotting_data[1][highest_intensity])
                    plot_item.addItem(text_item)
                except Exception as e:
                    logger.error(f"Error adding peak marker for ion {ion}: {e}")
            
            plot_item.getViewBox().enableAutoRange(axis='y', enable=True)
            plot_item.getViewBox().setAutoVisible(y=True)
        except Exception as e:
            logger.error(f"Error creating dock for compound {compound.name}: {e}")

    # Forces scrollArea to realize that the widget is bigger than it is
    widget.setMinimumSize(pg.QtCore.QSize(len(xics)*20, len(xics)*40))

def plot_calibration_curve(compound, widget):
    """Plots calibration curve for a compound"""
    widget.setBackground("w")
    x = np.array(list(compound.calibration_curve.keys()))
    y = np.array(list(compound.calibration_curve.values()))
    
    try: 
        compound.calibration_parameters
    except AttributeError:
        logger.error(f"No calibration parameters for {compound.name}")
        return
        
    if not all(k in compound.calibration_parameters for k in ('slope', 'intercept')):
        logger.error(f"Missing calibration parameters for {compound.name}")
        return
        
    try: 
        m = int(round(compound.calibration_parameters['slope']))
        b = int(round(compound.calibration_parameters['intercept']))
    except Exception as e:
        logger.error(f"Error extracting calibration parameters for {compound.name}: {e}")
        return
    
    curve = m * x + b
    widget.plot(x, y, name=compound.name, pen=None, symbol='o', symbolSize=5)
    widget.plot(x, curve, pen=mkPen('r', width=1))
    widget.setTitle(f'Calibration curve for {compound.name}')
    widget.setLabel('left', 'Intensity / a.u.')
    widget.setLabel('bottom', 'Concentration (mM)')
    
    text_item = pg.TextItem(
        text=f"Curve equation:\ny = {m}\u22c5x+{b}\nR\u00b2 = {np.round(compound.calibration_parameters['r_value']**2, 4)}",
        color='#232323', border=pg.mkPen('#232323', width=1), anchor=(0, 0)
    )
    text_item.setPos(np.min(x), np.max(y))
    text_item.setFont(pg.QtGui.QFont('Arial', 10, weight=pg.QtGui.QFont.Weight.ExtraLight))
    widget.addItem(text_item)
    widget.getPlotItem().vb.setAutoVisible(x=True, y=True)

def plot_total_ion_current(widget, ms_data, filename):
    """Plots total ion chromatogram"""
    widget.setBackground("w")
    widget.addLegend()
    widget.setTitle(f'Total ion chromatogram of {filename}')
    tic = []
    times = []
    for scan in ms_data:
        tic.append(scan['total ion current'])
        times.append(scan['retention_time'])
    widget.plot(times, tic, pen=mkPen('b', width=1))
    widget.setLabel('left', 'Intensity (cps)')
    widget.setLabel('bottom', 'Time (min)')

def plot_library_ms2(library_entry, widget):
    """Plot an MS2 spectrum from a library entry"""
    widget.clear()
    widget.setBackground("w")
    
    if not library_entry:
        widget.setTitle("No library entry found")
        return
    
    # Safe title extraction
    title = "Library MS2 spectrum"
    try:
        if "Name:" in library_entry[0]:
            title_parts = library_entry[0].split("Name:")
            title = "Library MS2 spectrum of " + title_parts[1].strip().split("\n")[0]
    except (IndexError, AttributeError) as e:
        logger.error(f"Error extracting title: {e}")
    
    widget.setTitle(title)
    
    # Extract mz and intensity values
    mzs = []
    intensities = []
    
    for line in library_entry:
        try:
            parts = line.split()
            if len(parts) >= 2:
                mz = float(parts[0])
                intensity = float(parts[1])
                mzs.append(mz)
                intensities.append(intensity)
        except (ValueError, IndexError):
            continue
    
    if not mzs:
        return
    
    # Convert to numpy arrays and plot
    mzs = np.array(mzs)
    intensities = np.array(intensities)
    
    widget.addItem(pg.BarGraphItem(
        x=mzs, height=intensities, width=0.2, 
        pen=mkPen('r', width=1), brush=mkBrush('r')
    ))
    
    widget.plot([min(mzs), max(mzs)], [0, 0], pen=mkPen('k', width=0.5))
    
    # Label peaks
    top_peaks = sorted(zip(mzs, intensities), key=lambda x: x[1], reverse=True)[:5]
    for mz, intensity in top_peaks:
        text_item = pg.TextItem(text=f"{mz:.4f}", color='#232323', anchor=(0, 0))
        text_item.setPos(mz, intensity)
        text_item.setFont(pg.QtGui.QFont('Helvetica', 10))
        widget.addItem(text_item)
    
    widget.setLabel('left', 'Intensity (%)')
    widget.setLabel('bottom', 'm/z')

def plot_ms2_from_file(ms_file, ms_compound, precursor, canvas):
    """Plot MS2 data from a file"""
    canvas.clear()
    canvas.setBackground("w")
    
    if not ms_file or not ms_compound:
        return
    
    try:
        xics = ms_file.xics
        compound_to_plot = next((xic for xic in xics if xic.name == ms_compound.name), None)
        if not compound_to_plot or not compound_to_plot.ms2:
            return
            
        mzs = []
        intensities = []
        
        for scan in compound_to_plot.ms2:
            try:
                if np.isclose(cvquery(scan, 'MS:1000744'), precursor, atol=0.0005):
                    mzs = scan['m/z array']
                    intensities = scan['intensity array']
                    break
            except Exception:
                continue
                
        if not isinstance(mzs, np.ndarray) or len(mzs) == 0:
            return
            
        if not isinstance(intensities, np.ndarray) or len(intensities) == 0:
            return
            
        canvas.setTitle(f'{ms_file.filename}: MS2 spectrum of {ms_compound.name}')
        canvas.addItem(pg.BarGraphItem(
            x=mzs, 
            height=intensities/np.max(intensities)*100, 
            width=0.2, 
            pen=mkPen('b', width=1), 
            brush=mkBrush('b')
        ))
        
        canvas.plot([min(mzs), max(mzs)], [0, 0], pen=mkPen('k', width=0.5))
        
        top_5 = sorted(zip(mzs, intensities), key=lambda x: x[1], reverse=True)[:5]
        for mz, intensity in top_5:
            text_item = pg.TextItem(text=f"{mz:.4f}", color='#232323', anchor=(0, 0))
            text_item.setPos(mz, intensity/np.max(intensities)*100)
            text_item.setFont(pg.QtGui.QFont('Helvetica', 10))
            canvas.addItem(text_item)
            
        canvas.setLabel('left', 'Intensity (%)')
        canvas.setLabel('bottom', 'm/z')
        
    except Exception as e:
        logger.error(f"Error in plot_ms2_from_file: {e}")

def plot_no_ms2_found(widget):
    """Display when no MS2 spectrum is found"""
    widget.setBackground("w")
    widget.setTitle('No MS2 spectrum found')
    widget.setLabel('left', 'Intensity (%)')
    widget.setLabel('bottom', 'm/z')
