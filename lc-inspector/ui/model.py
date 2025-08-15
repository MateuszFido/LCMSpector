# model.py
import logging, traceback, multiprocessing, threading, os
import numpy as np
from scipy.stats import linregress
import pandas as pd
from utils.classes import LCMeasurement, MSMeasurement, Compound
from calculation.calc_conc import calculate_concentration
from utils.loading import load_ms2_library, load_ms2_data
from calculation.workers import LoadingWorker, ProcessingWorker
from PySide6.QtCore import QThread

logger = logging.getLogger(__name__)
logger.propagate = False
class Model(QThread):
    """
    The Model class handles the loading, processing, and annotation of LC and MS measurement files.

    Attributes
    ----------
    ms_measurements : dict
        -- A dictionary to store MSMeasurement objects.
    lc_measurements : dict
        -- A dictionary to store LCMeasurement objects.
    annotations : list
        -- A list to store annotations for the measurements.
    compounds : list
        -- A list of Compound objects representing targeted results.
    library : dict
        -- A dictionary representing the MS2 library loaded from external resources.
    worker : Worker or None
        -- A worker instance for handling concurrent processing tasks.

    Methods
    -------
    - process_data(mode):
        Initiates the data processing workflow.
    - get_plots(filename):
        Retrieves the corresponding LC and MS files for a given filename.
    - calibrate(selected_files):
        Calibrates the concentrations for selected files.
    """
    
    __slots__ = ['ms_measurements', 'lc_measurements', 'annotations', 'controller', 'compounds', 'library', 'worker']

    def __init__(self):
        super().__init__()
        self.lc_measurements = {}
        self.ms_measurements = {}
        self.annotations = []
        self.compounds = []
        self.library = load_ms2_library()
        if self.library:
            logger.info("MS2 library loaded.")
        else:
            logger.error("No MS2 library found. Please make sure a corresponding library in .msp format is in the 'resources' folder.")
        self.controller = None
        self.worker = None
        logger.info("Model initialized.")
        logger.info("Current thread: %s", threading.current_thread().name)
        logger.info("Current process: %d", os.getpid())

    def load(self, mode, file_type):
        self.worker = LoadingWorker(self, mode, file_type)
        self.worker.progressUpdated.connect(self.controller.view.update_progress_bar)
        self.worker.progressUpdated.connect(self.controller.view.update_statusbar_with_loaded_file)
        self.worker.finished.connect(self.controller.on_loading_finished)
        self.worker.error.connect(self.controller.on_worker_error)
        self.worker.start()

    def process(self, mode):
        self.worker = ProcessingWorker(self, mode)
        self.worker.progressUpdated.connect(self.controller.view.update_progress_bar)
        self.worker.finished.connect(self.controller.on_processing_finished)
        self.worker.error.connect(self.controller.on_worker_error)
        self.worker.start()

    def get_plots(self, filename):
        # Find the corresponding MS and LC files
        ms_file = self.ms_measurements.get(filename, None)
        lc_file = self.lc_measurements.get(filename, None)
        return lc_file, ms_file

    def calibrate(self, selected_files):
        for j, (file, concentration) in enumerate(selected_files.items()):
            if not concentration.strip():
                continue
            concentration_value, suffix = (concentration.split(" ") + [None])[:2]
            conversion_factors = {'m': 1e3, 'mm': 1, 'um': 1e-3, 'nm': 1e-9, 'pm': 1e-12}
            concentration = float(concentration_value) * conversion_factors.get(suffix and suffix.lower(), 1)
            
            ms_file = self.ms_measurements.get(file)
            if not ms_file or not ms_file.xics:
                logger.error(f"No xics found for file {file}.")
                continue

            for i, compound in enumerate(self.compounds):
                if not compound.ions:
                    logger.error(f"No ions found for compound {compound.name}.")
                    continue
                
                # NEW: Use peak area for calibration if available, otherwise fall back to intensity sum
                compound_signal = 0
                use_peak_areas = False
                
                for ion in compound.ions.keys():
                    ion_data = ms_file.xics[i].ions[ion]
                    
                    # Check if peak area data is available and use baseline-corrected area
                    if 'MS Peak Area' in ion_data and ion_data['MS Peak Area'].get('baseline_corrected_area', 0) > 0:
                        compound_signal += ion_data['MS Peak Area']['baseline_corrected_area']
                        use_peak_areas = True
                        logger.debug(f"Using peak area for calibration: {ion} = {ion_data['MS Peak Area']['baseline_corrected_area']}")
                    else:
                        # Fallback to original intensity sum method
                        if ion_data['MS Intensity'] is not None:
                            compound_signal += np.round(np.sum(ion_data['MS Intensity'][1]), 0)
                        logger.debug(f"Using intensity sum for calibration: {ion}")
                
                if use_peak_areas:
                    logger.info(f"Calibration using peak areas for {compound.name}: {compound_signal}")
                else:
                    logger.info(f"Calibration using intensity sums for {compound.name}: {compound_signal}")
                
                compound.calibration_curve[concentration] = compound_signal
                
                if j == len(selected_files) - 1:
                    slope, intercept, r_value, p_value, std_err = linregress(
                        list(compound.calibration_curve.keys()),
                        list(compound.calibration_curve.values())
                    )
                    compound.calibration_parameters = {
                        'slope': slope, 'intercept': intercept, 'r_value': r_value,
                        'p_value': p_value, 'std_err': std_err
                    }

        for ms_file in self.ms_measurements.values():
            if not ms_file.xics:  # Skip files with no XIC data
                logger.warning(f"Skipping concentration calculation for {ms_file.filename}: no XIC data")
                continue
            for ms_compound, model_compound in zip(ms_file.xics, self.compounds):
                try:
                    # NEW: Use peak areas for concentration calculation if available
                    compound_signal = 0
                    use_peak_areas = False
                    
                    for ion in ms_compound.ions.keys():
                        ion_data = ms_compound.ions[ion]
                        
                        # Check if peak area data is available and use baseline-corrected area
                        if 'MS Peak Area' in ion_data and ion_data['MS Peak Area'].get('baseline_corrected_area', 0) > 0:
                            compound_signal += ion_data['MS Peak Area']['baseline_corrected_area']
                            use_peak_areas = True
                        else:
                            # Fallback to original intensity sum method
                            if ion_data['MS Intensity'] is not None:
                                compound_signal += np.round(np.sum(ion_data['MS Intensity'][1]), 0)
                    
                    if use_peak_areas:
                        logger.debug(f"Concentration calculation using peak areas for {ms_compound.name}: {compound_signal}")
                    else:
                        logger.debug(f"Concentration calculation using intensity sums for {ms_compound.name}: {compound_signal}")
                    
                    ms_compound.concentration = calculate_concentration(
                        compound_signal, model_compound.calibration_parameters
                    )
                    ms_compound.calibration_parameters = model_compound.calibration_parameters
                except Exception as e:
                    logger.error(f"Error calibrating file {ms_file.filename}: {traceback.format_exc()}")

    def find_ms2_precursors(self) -> dict:
        compound = self.compounds[self.controller.view.comboBoxChooseCompound.currentIndex()]
        library_entries = set()
        # safety check
        if not compound:
            raise ValueError("No compound selected.")
        for ion in compound.ions.keys():
            try:
                library_entry = next((l for l in self.library.values() 
                                    if (precursor_mz := next((line.split(' ')[1] for line in l if 'PrecursorMZ:' in line), None)) is not None 
                                    and np.isclose(float(precursor_mz), float(ion), atol=0.005)), None)
                if library_entry:
                    logger.info(f"Precursor m/z {ion} found for {compound.name} in the library.")
                    library_entries.add(tuple(library_entry))
                else:
                    logger.debug(f"Library entry not found for {compound.name}: {ion}")
            except StopIteration:
                logger.debug("Library entry not found for %s: %.4f", {compound.name}, {ion})
                break
        #HACK: Terribly complex dict comprehension
        library_entries = {entry[0].split("Name: ", 1)[1].partition('\n')[0] \
            + (f"m/z ({round(float(next((line.split(' ')[1] for line in entry \
                if 'PrecursorMZ:' in line), None)), 4)})" if \
                    (precursor_mz := next((line.split(' ')[1] \
                        for line in entry if 'PrecursorMZ:' in line), None)) else "").strip(): \
                            entry for entry in library_entries}
        self.controller.view.comboBoxChooseMS2File.clear()
        self.controller.view.comboBoxChooseMS2File.addItems(library_entries.keys())
        return library_entries

    def find_ms2_in_file(self, ms_file):
        current_compound = self.compounds[self.controller.view.comboBoxChooseCompound.currentIndex()]
        current_compound_in_ms_file = next((c for c in ms_file.xics if c.name == current_compound.name), None)
        load_ms2_data(ms_file.path, current_compound_in_ms_file, ms_file.mass_accuracy)

    def export(self):
        results = []
        for ms_measurement in self.ms_measurements.values():
            # Get corresponding LC measurement for peak area matching
            lc_measurement = self.lc_measurements.get(ms_measurement.filename, None)
            
            for compound in ms_measurement.xics:
                ion_data = zip(compound.ions.keys(), compound.ions.values(), compound.ion_info)
                for ion, data, ion_name in ion_data:
                    results_dict = {
                        # Existing fields
                        'File': ms_measurement.filename,
                        'Ion (m/z)': ion,
                        'Compound': compound.name,
                        'RT (min)': np.round(data['RT'], 3),
                        'MS Intensity (cps)': np.round(np.sum(data['MS Intensity'][1]) if data['MS Intensity'] is not None else 0, 0),
                        'LC Intensity (a.u.)': data.get('LC Intensity', 0),
                        'Ion name': str(ion_name).strip() if ion_name else ion
                    }
                    
                    # NEW: MS Peak Area fields
                    ms_peak_area = data.get('MS Peak Area', {})
                    results_dict.update({
                        'MS Peak Area (Total)': ms_peak_area.get('total_area', 0),
                        'MS Peak Area (Baseline Corrected)': ms_peak_area.get('baseline_corrected_area', 0),
                        'MS Peak Start Time (min)': ms_peak_area.get('start_time', 0),
                        'MS Peak End Time (min)': ms_peak_area.get('end_time', 0),
                        'MS Peak Height': ms_peak_area.get('peak_height', 0),
                        'MS Peak SNR': ms_peak_area.get('snr', 0),
                        'MS Peak Quality Score': ms_peak_area.get('quality_score', 0),
                        'MS Integration Method': ms_peak_area.get('integration_method', 'none')
                    })
                    
                    # NEW: LC Peak Area fields (match by retention time if LC data available)
                    lc_peak_area = {}
                    if lc_measurement and hasattr(lc_measurement, 'peak_areas'):
                        # Find LC peak closest to MS retention time
                        rt_target = data.get('RT', 0)
                        if rt_target > 0:
                            matched_lc_peak = lc_measurement.get_peak_at_rt(rt_target, tolerance=0.2)
                            if matched_lc_peak:
                                lc_peak_area = matched_lc_peak
                    
                    results_dict.update({
                        'LC Peak Area (Total)': lc_peak_area.get('total_area', 0),
                        'LC Peak Area (Baseline Corrected)': lc_peak_area.get('baseline_corrected_area', 0),
                        'LC Peak Start Time (min)': lc_peak_area.get('start_time', 0),
                        'LC Peak End Time (min)': lc_peak_area.get('end_time', 0),
                        'LC Peak Height': lc_peak_area.get('peak_height', 0),
                        'LC Peak SNR': lc_peak_area.get('snr', 0),
                        'LC Peak Quality Score': lc_peak_area.get('quality_score', 0),
                        'LC Integration Method': lc_peak_area.get('integration_method', 'none')
                    })
                    
                    # Existing concentration and calibration fields
                    try:
                        results_dict['Concentration (mM)'] = compound.concentration
                        results_dict['Calibration slope'] = compound.calibration_parameters['slope']
                        results_dict['Calibration intercept'] = compound.calibration_parameters['intercept']
                    except Exception as e:
                        logger.error(f"Error exporting concentration information for {ms_measurement.filename}: {e}")
                        results_dict['Concentration (mM)'] = 0
                        results_dict['Calibration slope'] = 0
                        results_dict['Calibration intercept'] = 0
                    
                    results.append(results_dict)
        
        df = pd.DataFrame(results)
        logger.info(f"Exported {len(df)} rows with peak area information")
        return df
