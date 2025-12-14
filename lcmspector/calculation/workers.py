"""
Module for handling background workers in LC-Inspector application.

This module provides QThread-based worker classes for asynchronous loading and
processing of LC/GC-MS measurement data. It supports:
- Loading LC and MS measurement files in parallel
- Processing MS files with multiprocessing
- Emitting progress and result signals for UI updates

The module uses ProcessPoolExecutor for efficient parallel processing and
leverages PyQt6's signal-slot mechanism for thread communication.
"""

import time
import traceback
import multiprocessing
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed

from PySide6.QtCore import QThread, QObject, Signal
from utils.classes import LCMeasurement, MSMeasurement
from utils.preprocessing import construct_xics

logger = logging.getLogger(__name__)


class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        tuple (exctype, value, traceback.format_exc() )

    result
        object data returned from processing, anything

    progress
        int indicating % progress

    """

    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(int)


class LoadingWorker(QThread):
    progressUpdated = Signal(int, str)
    finished = Signal(dict, dict)
    error = Signal(str)

    def __init__(self, model, mode, file_type):
        super().__init__()
        self.model = model
        self.mode = mode
        self.file_type = file_type

    def run(self):
        st = time.time()
        lc_results = {}
        ms_results = {}

        try:
            total_files = len(self.model.lc_measurements) + len(
                self.model.ms_measurements
            )
            if total_files == 0:
                logger.warning("No files to process.")
                return
        except AttributeError:
            logger.error("Model attributes are not properly initialized.")
            return

        progress = 0

        def update_progress(filename):
            nonlocal progress
            progress += 1
            self.progressUpdated.emit(int(progress / total_files * 200), filename)

        if self.mode not in {"LC/GC-MS", "LC/GC Only", "MS Only"}:
            logger.error("ERROR: Invalid argument for load_data(mode): %s", self.mode)
            return

        try:
            with ProcessPoolExecutor(
                max_workers=max(1, multiprocessing.cpu_count() - 3)
            ) as executor:
                # Conditional loading based on mode and what is being uploaded
                if self.mode in ("LC/GC-MS", "LC/GC Only") and self.file_type == "LC":
                    lc_futures = {
                        executor.submit(LCMeasurement, lc_file): lc_file
                        for lc_file in self.model.lc_measurements
                    }
                else:
                    lc_futures = {}

                if self.mode in {"LC/GC-MS", "MS Only"} and self.file_type == "MS":
                    ms_futures = {
                        executor.submit(MSMeasurement, ms_file): ms_file
                        for ms_file in self.model.ms_measurements
                    }
                else:
                    ms_futures = {}

                for future in as_completed(list(lc_futures) + list(ms_futures)):
                    try:
                        result = future.result()
                        if future in lc_futures:
                            lc_results[result.filename] = result
                        else:
                            ms_results[result.filename] = result
                    except Exception as e:
                        logger.error("Error loading file: %s", traceback.format_exc())
                        self.error.emit(str(e))
                    update_progress(result.filename)
        except Exception as e:
            logger.error("Error in loading pool: %s", traceback.format_exc())
            self.error.emit(str(e))
            return

        logger.info(
            "Loaded %d LC files and %d MS files for %s in %.2f seconds.",
            len(lc_results),
            len(ms_results),
            self.mode,
            time.time() - st,
        )
        self.finished.emit(lc_results, ms_results)


class ProcessingWorker(QThread):
    progressUpdated = Signal(int)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, model, mode, mass_accuracy):
        super().__init__()
        self.model = model
        self.mode = mode
        self.mass_accuracy = mass_accuracy

    def run(self):
        st = time.time()

        try:
            total_files = len(self.model.ms_measurements)
            if total_files == 0:
                logger.warning("No files to process.")
                return
        except AttributeError:
            logger.error("Model attributes are not properly initialized.")
            return

        progress = 0

        def update_progress():
            nonlocal progress
            progress += 1
            self.progressUpdated.emit(int(progress / total_files * 100))

        if self.mode not in {"LC/GC-MS", "LC/GC Only", "MS Only"}:
            logger.error(
                "ERROR: Invalid argument for process_data(mode): %s", self.mode
            )
            return
        results = []
        try:
            with ProcessPoolExecutor(
                max_workers=max(1, multiprocessing.cpu_count() - 3)
            ) as executor:
                # Only process MS files if in MS or LC/GC-MS mode
                if self.mode in {"LC/GC-MS", "MS Only"}:
                    # for every MS file, call construct_xics on its data and store the result
                    ms_futures = {
                        executor.submit(
                            construct_xics,
                            ms_file.filename,
                            ms_file.data,
                            self.model.compounds,
                            self.mass_accuracy,
                        ): ms_file
                        for ms_file in self.model.ms_measurements.values()
                    }
                else:
                    ms_futures = {}

                for future in as_completed(list(ms_futures)):
                    try:
                        result = future.result()
                        results.append(result)
                    except AttributeError as e:
                        logger.error(
                            "Error in processing pool: %s", traceback.format_exc()
                        )
                        self.error.emit(str(e))
                    update_progress()
        except Exception as e:
            logger.error("Error in processing pool: %s", traceback.format_exc())
            self.error.emit(str(e))
            return

        logger.info(
            "Processed %d MS files in %.2f seconds.", len(results), time.time() - st
        )
        self.finished.emit(results)
