# model.py
import logging
import traceback
import threading
import os
import numpy as np
from scipy.stats import linregress
import pandas as pd
from calculation.calc_conc import calculate_concentration
from calculation.peak_integration import integrate_peak_manual_boundaries
from calculation.workers import LoadingWorker, ProcessingWorker
from utils.loading import load_ms2_library
from PySide6.QtCore import QThread

logger = logging.getLogger(__name__)


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

    __slots__ = [
        "ms_measurements",
        "lc_measurements",
        "annotations",
        "controller",
        "compounds",
        "library",
        "worker",
        "mass_accuracy",
    ]

    def __init__(self):
        super().__init__()
        self.lc_measurements = dict()
        self.ms_measurements = dict()
        self.annotations = tuple()
        self.compounds = tuple()
        self.mass_accuracy = 0.0001
        self.library = load_ms2_library()
        if self.library:
            logger.info("MS2 library loaded.")
        else:
            logger.error(
                "No MS2 library found. Please make sure a corresponding library in .msp format is in the 'resources' folder."
            )
        self.controller = None
        self.worker = None
        logger.info("Model initialized.")
        logger.info("Current thread: %s", threading.current_thread().name)
        logger.info("Current process: %d", os.getpid())

    def load(self, mode, file_paths, file_type):
        self.worker = LoadingWorker(self, mode, file_paths, file_type)
        self.worker.progressUpdated.connect(self.controller.view.update_progressBar)
        self.worker.progressUpdated.connect(
            self.controller.view.update_statusbar_with_loaded_file
        )
        self.worker.finished.connect(self.controller.on_loading_finished)
        self.worker.error.connect(self.controller.on_worker_error)
        self.worker.start()

    def process(self, mode):
        self.worker = ProcessingWorker(self, mode, self.mass_accuracy)
        self.worker.progressUpdated.connect(self.controller.view.update_progressBar)
        self.worker.finished.connect(self.controller.on_processing_finished)
        self.worker.error.connect(self.controller.on_worker_error)
        self.worker.start()

    def get_plots(self, filename):
        # Find the corresponding MS and LC files
        ms_file = self.ms_measurements.get(filename, None)
        lc_file = self.lc_measurements.get(filename, None)
        return lc_file, ms_file

    def _get_compound_signal(self, ms_compound, use_peak_area=True):
        """Helper to calculate compound signal, with option to force intensity sum."""
        compound_signal = 0
        peak_area_was_used = False
        for ion in ms_compound.ions.keys():
            ion_data = ms_compound.ions[ion]
            # Use peak area if requested and available
            if (
                use_peak_area
                and "MS Peak Area" in ion_data
                and ion_data["MS Peak Area"].get("baseline_corrected_area", 0) > 0
            ):
                compound_signal += ion_data["MS Peak Area"]["baseline_corrected_area"]
                peak_area_was_used = True
            else:
                # Fallback to intensity sum
                if (
                    ion_data["MS Intensity"] is not None
                    and len(ion_data["MS Intensity"]) > 1
                ):
                    compound_signal += np.round(np.sum(ion_data["MS Intensity"][1]), 0)

        return compound_signal, peak_area_was_used

    def calibrate(self, selected_files):
        for i, compound in enumerate(self.compounds):
            if not compound.ions:
                logger.error(f"No ions found for compound {compound.name}.")
                continue

            # 1. Initial calibration attempt using peak areas
            use_peak_area_calibration = True
            compound.calibration_curve.clear()
            for file, concentration_str in selected_files.items():
                if not concentration_str.strip():
                    continue
                concentration_value, suffix = (concentration_str.split(" ") + [None])[
                    :2
                ]
                conversion_factors = {
                    "m": 1e3,
                    "mm": 1,
                    "um": 1e-3,
                    "nm": 1e-9,
                    "pm": 1e-12,
                }
                concentration = float(concentration_value) * conversion_factors.get(
                    suffix and suffix.lower(), 1
                )

                ms_file = self.ms_measurements.get(file)
                if not ms_file or not ms_file.xics:
                    logger.error(f"No xics found for file {file}.")
                    continue

                ms_compound = ms_file.xics[i]
                compound_signal, _ = self._get_compound_signal(
                    ms_compound, use_peak_area=True
                )
                compound.calibration_curve[concentration] = compound_signal

            # 2. Perform linear regression and check R²
            concentrations = list(compound.calibration_curve.keys())
            signals = list(compound.calibration_curve.values())

            if len(concentrations) < 2:
                logger.error(f"Not enough calibration points for {compound.name}.")
                continue

            slope, intercept, r_value, p_value, std_err = linregress(
                concentrations, signals
            )
            r_squared = r_value**2

            # 3. Fallback to intensity sum if R² is poor
            if r_squared < 0.75:
                logger.warning(
                    f"Low R² ({r_squared:.2f}) for {compound.name} with peak areas. Falling back to intensity sum."
                )
                use_peak_area_calibration = False
                compound.calibration_curve.clear()
                for file, concentration_str in selected_files.items():
                    if not concentration_str.strip():
                        continue
                    concentration_value, suffix = (
                        concentration_str.split(" ") + [None]
                    )[:2]
                    conversion_factors = {
                        "m": 1e3,
                        "mm": 1,
                        "um": 1e-3,
                        "nm": 1e-9,
                        "pm": 1e-12,
                    }
                    concentration = float(concentration_value) * conversion_factors.get(
                        suffix and suffix.lower(), 1
                    )

                    ms_file = self.ms_measurements.get(file)
                    if not ms_file or not ms_file.xics:
                        continue

                    ms_compound = ms_file.xics[i]
                    compound_signal, _ = self._get_compound_signal(
                        ms_compound, use_peak_area=False
                    )
                    compound.calibration_curve[concentration] = compound_signal

                concentrations = list(compound.calibration_curve.keys())
                signals = list(compound.calibration_curve.values())
                slope, intercept, r_value, p_value, std_err = linregress(
                    concentrations, signals
                )
                r_squared = r_value**2
                logger.info(
                    f"Recalibrated {compound.name} with intensity sum, new R²: {r_squared:.2f}"
                )

            compound.calibration_parameters = {
                "slope": slope,
                "intercept": intercept,
                "r_value": r_value,
                "r_squared": r_squared,
                "p_value": p_value,
                "std_err": std_err,
                "use_peak_area": use_peak_area_calibration,
            }

        # 4. Calculate concentrations for all files using the determined calibration method
        for ms_file in self.ms_measurements.values():
            if not ms_file.xics:
                logger.warning(
                    f"Skipping concentration calculation for {ms_file.filename}: no XIC data"
                )
                continue
            for ms_compound, model_compound in zip(ms_file.xics, self.compounds):
                try:
                    if not model_compound.calibration_parameters:
                        continue

                    use_peak_area_for_calc = model_compound.calibration_parameters.get(
                        "use_peak_area", True
                    )
                    compound_signal, peak_area_was_used = self._get_compound_signal(
                        ms_compound, use_peak_area=use_peak_area_for_calc
                    )

                    if peak_area_was_used:
                        logger.info(
                            f"Concentration calculation using peak areas for {ms_compound.name}: {compound_signal}"
                        )
                    else:
                        logger.info(
                            f"Concentration calculation using intensity sums for {ms_compound.name}: {compound_signal}"
                        )

                    ms_compound.concentration = calculate_concentration(
                        compound_signal, model_compound.calibration_parameters
                    )
                    ms_compound.calibration_parameters = (
                        model_compound.calibration_parameters
                    )
                except Exception:
                    logger.error(
                        f"Error calculating concentration for {ms_compound.name} in {ms_file.filename}: {traceback.format_exc()}"
                    )

    def find_ms2_precursors(self) -> dict:
        compound = self.compounds[
            self.controller.view.comboBoxChooseCompound.currentIndex()
        ]
        library_entries = set()
        # safety check
        if not compound:
            raise ValueError("No compound selected.")
        for ion in compound.ions.keys():
            try:
                library_entry = next(
                    (
                        section
                        for section in self.library.values()
                        if (
                            precursor_mz := next(
                                (
                                    line.split(" ")[1]
                                    for line in section
                                    if "PrecursorMZ:" in line
                                ),
                                None,
                            )
                        )
                        is not None
                        and np.isclose(float(precursor_mz), float(ion), atol=0.005)
                    ),
                    None,
                )
                if library_entry:
                    logger.info(
                        f"Precursor m/z {ion} found for {compound.name} in the library."
                    )
                    library_entries.add(tuple(library_entry))
                else:
                    logger.debug(f"Library entry not found for {compound.name}: {ion}")
            except StopIteration:
                logger.debug(
                    "Library entry not found for %s: %.4f", {compound.name}, {ion}
                )
                break
        # HACK: Terribly complex dict comprehension
        library_entries = {
            entry[0].split("Name: ", 1)[1].partition("\n")[0]
            + (
                f"m/z ({
                    round(
                        float(
                            next(
                                (
                                    line.split(' ')[1]
                                    for line in entry
                                    if 'PrecursorMZ:' in line
                                ),
                                None,
                            )
                        ),
                        4,
                    )
                })"
                if (
                    precursor_mz := next(
                        (
                            line.split(" ")[1]
                            for line in entry
                            if "PrecursorMZ:" in line
                        ),
                        None,
                    )
                )
                else ""
            ).strip(): entry
            for entry in library_entries
        }
        self.controller.view.comboBoxChooseMS2File.clear()
        self.controller.view.comboBoxChooseMS2File.addItems(library_entries.keys())
        return library_entries

    def export(self):
        results = []
        for ms_measurement in self.ms_measurements.values():
            # Get corresponding LC measurement for peak area matching
            lc_measurement = self.lc_measurements.get(ms_measurement.filename, None)

            for compound in ms_measurement.xics:
                ion_data = zip(
                    compound.ions.keys(), compound.ions.values(), compound.ion_info
                )
                for ion, data, ion_name in ion_data:
                    results_dict = {
                        # Existing fields
                        "File": ms_measurement.filename,
                        "Ion (m/z)": ion,
                        "Compound": compound.name,
                        "RT (min)": np.round(data["RT"], 3),
                        "MS Intensity (cps)": np.round(
                            np.sum(data["MS Intensity"][1])
                            if data["MS Intensity"] is not None
                            else 0,
                            0,
                        ),
                        "LC Intensity (a.u.)": data.get("LC Intensity", 0),
                        "Ion name": str(ion_name).strip() if ion_name else ion,
                    }

                    # NEW: MS Peak Area fields
                    ms_peak_area = data.get("MS Peak Area", {})
                    results_dict.update(
                        {
                            "MS Peak Area (Total)": ms_peak_area.get("total_area", 0),
                            "MS Peak Area (Baseline Corrected)": ms_peak_area.get(
                                "baseline_corrected_area", 0
                            ),
                            "MS Peak Start Time (min)": ms_peak_area.get(
                                "start_time", 0
                            ),
                            "MS Peak End Time (min)": ms_peak_area.get("end_time", 0),
                            "MS Peak Height": ms_peak_area.get("peak_height", 0),
                            "MS Peak SNR": ms_peak_area.get("snr", 0),
                            "MS Peak Quality Score": ms_peak_area.get(
                                "quality_score", 0
                            ),
                            "MS Integration Method": ms_peak_area.get(
                                "integration_method", "none"
                            ),
                        }
                    )

                    # NEW: LC Peak Area fields (match by retention time if LC data available)
                    lc_peak_area = {}
                    if lc_measurement and hasattr(lc_measurement, "peak_areas"):
                        # Find LC peak closest to MS retention time
                        rt_target = data.get("RT", 0)
                        if rt_target > 0:
                            matched_lc_peak = lc_measurement.get_peak_at_rt(
                                rt_target, tolerance=0.2
                            )
                            if matched_lc_peak:
                                lc_peak_area = matched_lc_peak

                    results_dict.update(
                        {
                            "LC Peak Area (Total)": lc_peak_area.get("total_area", 0),
                            "LC Peak Area (Baseline Corrected)": lc_peak_area.get(
                                "baseline_corrected_area", 0
                            ),
                            "LC Peak Start Time (min)": lc_peak_area.get(
                                "start_time", 0
                            ),
                            "LC Peak End Time (min)": lc_peak_area.get("end_time", 0),
                            "LC Peak Height": lc_peak_area.get("peak_height", 0),
                            "LC Peak SNR": lc_peak_area.get("snr", 0),
                            "LC Peak Quality Score": lc_peak_area.get(
                                "quality_score", 0
                            ),
                            "LC Integration Method": lc_peak_area.get(
                                "integration_method", "none"
                            ),
                        }
                    )

                    # Existing concentration and calibration fields
                    try:
                        results_dict["Concentration (mM)"] = compound.concentration
                        results_dict["Calibration slope"] = (
                            compound.calibration_parameters["slope"]
                        )
                        results_dict["Calibration intercept"] = (
                            compound.calibration_parameters["intercept"]
                        )
                        results_dict["Calibration R2"] = (
                            compound.calibration_parameters.get("r_squared", 0)
                        )
                    except Exception as e:
                        logger.error(
                            f"Error exporting concentration information for {ms_measurement.filename}: {e}"
                        )
                        results_dict["Concentration (mM)"] = 0
                        results_dict["Calibration slope"] = 0
                        results_dict["Calibration intercept"] = 0

                    results.append(results_dict)

        df = pd.DataFrame(results)
        logger.info(f"Exported {len(df)} rows with peak area information")
        return df

    def shutdown(self):
        """Gracefully stop any running workers and threads."""
        logger.debug("Trying to shut down model and workers...")
        if self.worker:
            if hasattr(self.worker, "isRunning") and self.worker.isRunning():
                self.worker.terminate()
                self.worker.wait()
        logger.debug("Model shutdown complete.")

    def apply_integration_changes(self):
        """
        Retrieves the current boundaries, computes the peak area, and updates the quantitation table.
        """
        current_compound_text = (
            self.controller.view.comboBoxChooseCompound.currentText()
        )
        current_file_text = self.controller.view.unifiedResultsTable.get_selected_file()

        current_compound = self.ms_measurements[current_file_text].get_compound_by_name(
            current_compound_text
        )

        integration_bounds = self.controller.view.get_integration_bounds(
            self.controller.view.canvas_library_ms2
        )

        for ion in current_compound.ions:
            try:
                ion_data = current_compound.ions[ion]
            except Exception:
                logger.error(f"Problem retrieving integration data. Skipping {ion}...")
                continue
            try:
                ion_data["Integration Data"]["start_time"] = integration_bounds[0]
                ion_data["Integration Data"]["end_time"] = integration_bounds[1]
            except AttributeError:
                logger.error(f"Problem setting integration bounds. Skipping {ion}...")
                continue
            try:
                ion_data["Integration Data"] = integrate_peak_manual_boundaries(
                    ion_data["MS Intensity"][0],
                    ion_data["MS Intensity"][1],
                    ion_data["Integration Data"]["start_time"],
                    ion_data["Integration Data"]["end_time"],
                )
            except Exception:
                logger.error(traceback.format_exc())

        self.controller.view.unifiedResultsTable.update_ion_values(
            current_file_text, current_compound
        )

    def recalculate_integration_all_files(self):
        pass

    def reset_integration(self):
        pass
