import os
from pathlib import Path
import numpy as np
import pandas as pd
from adjustText import adjust_text
import pyqtgraph as pg
from pyqtgraph import exporters
from PyQt6.QtCore import Qt
from pyqtgraph import mkPen

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

    # Create the "plots" directory if it doesn't exist
    plot_path = Path(path).parents[1] / 'plots' / f'{filename}'
    os.makedirs(plot_path, exist_ok=True)

    # Plotting chromatogram before background correction
    widget.setBackground("w")
    widget.plot(title='Chromatogram Before Background Correction')
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


def plot_average_ms_data(path: str, data_matrix: pd.DataFrame, widget: pg.PlotWidget):
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

    filename = os.path.basename(path).split('.')[0]

    # Create the "plots" directory if it doesn't exist
    plot_path = Path(path).parents[1] / 'plots' / f'{filename}'
    os.makedirs(plot_path, exist_ok=True)

    # Plotting the average MS data
    widget.setBackground("w")
    widget.plot(title='Average MS Data')
    widget.showGrid(x=True, y=True, alpha=0.2)
    widget.plot(data_matrix['m/z'], data_matrix['intensity / a.u.'], pen=mkPen('b', width=2))

    # Annotate the m/z of the 5 highest peaks
    highest_peaks = data_matrix.nlargest(10, 'intensity / a.u.')
    for index, row in highest_peaks.iterrows():
        widget.plot([row['m/z']], [row['intensity / a.u.']], pen=mkPen('r', width=2), symbol='o', symbolSize=10)
        text = pg.TextItem(text=str(row['m/z']), color='black')
        text.setPos(row['m/z'], row['intensity / a.u.'])
        widget.addItem(text)
        
    widget.setLabel('left', 'Average Intensity / a.u.')
    widget.setLabel('bottom', 'm/z')

def plot_annotated_LC(path: str, chromatogram: pd.DataFrame, compounds: list, widget: pg.PlotWidget):
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

    # Create the "plots" directory if it doesn't exist
    plot_path = Path(path).parents[1] / 'plots' / f'{filename}'
    os.makedirs(plot_path, exist_ok=True)

    # Plot the LC data
    widget.setBackground("w")
    widget.setLabel('left', 'Absorbance (mAU)')
    widget.setLabel('bottom', 'Retention time (min)')
    widget.plot(chromatogram['Time (min)'], chromatogram['Value (mAU)'], pen=mkPen('b', width=2))

    # Annotate with compounds
    for compound in compounds:
        for ion in compound.ions.keys():
            if compound.ions[ion]['RT'] is not None and compound.ions[ion]['Apex'] is not None:
                # Plot the intensity of the ion at that retention time
                widget.plot([compound.ions[ion]['RT']], [compound.ions[ion]['Apex']], pen=mkPen('r', width=2), symbol='o', symbolSize=5)
                
                # Create a text item for annotation
                text_item = pg.TextItem(text=f"{compound.name}\n{ion}", anchor=(0, 1), color='black')
                text_item.setPos(compound.ions[ion]['RT'], compound.ions[ion]['Apex'] - np.random.random() / 100)
                widget.addItem(text_item)



def plot_annotated_XICs(path: str, xics: pd.DataFrame, compound_list: list, widget: pg.GraphicsLayoutWidget):
    filename = os.path.basename(path).split('.')[0]
    plot_path = Path(path).parents[1] / 'plots' / f'{filename}'
    os.makedirs(plot_path, exist_ok=True)

    tot = len(compound_list)
    cols = int(np.ceil(np.sqrt(tot)))
    rows = int(np.ceil(tot / cols))

    widget.setBackground("w")
    for i, compound in enumerate(compound_list):
        plot_item = widget.addPlot(row=i // cols, col=i % cols)
        plot_item.setTitle(compound.name)
        args = ({'color': 'b', 'font-size': '10pt'})
        plot_item.setLabel('bottom', text='Scan time', units='min', **args)
        plot_item.setLabel('left', text='Intensity', units='a.u.', **args)

        for j, ion in enumerate(compound.ions.keys()):
            if compound.ions[ion]["RT"] is None or compound.ions[ion]["MS Intensity"] is None:
                continue
            
            closest = np.abs(xics.iloc[0] - ion).idxmin()
            
            scan_time = xics['Scan time (min)'].iloc[xics[closest][1:].idxmax()]  # Skip the first row

            # Check if closest is a valid column
            if closest not in xics.columns:
                print(f"Column {closest} does not exist in xics.")
                continue

            plotting_data = xics['Scan time (min)'][1:].to_numpy()
            # Add xics[closest][1:].tonumpy() as y axis
            plotting_data = np.append(plotting_data, xics[closest][1:].values)
            plot_item.plot(plotting_data)
            plot_item.pen = mkPen('b', width=1)
            highest_intensity = xics[closest].iloc[xics[closest][1:].idxmax()]
            plot_item.plot([scan_time], [highest_intensity], pen=None, symbol='o', symbolBrush='r')

            text_item = pg.TextItem(f"{ion}\n({closest})", anchor=(0, 0))
            text_item.setPos(scan_time - np.random.random() / 100, highest_intensity)
            plot_item.addItem(text_item)
            plot_item.getAxis('left').setHeight(100)
            plot_item.setMinimumSize(100, 100)

