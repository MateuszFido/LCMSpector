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
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, model, mode, file_paths, file_type):
        super().__init__()
        self.model = model
        self.mode = mode
        self.file_paths = file_paths
        self.file_type = file_type
        self.file_count = len(file_paths)

    def run(self):
        st = time.time()
        results = {}

        try:
            self.file_count
        except AttributeError:
            logger.error("File count attribute not properly initialized.")
            return

        if self.file_count == 0:
            logger.warning("No files to process.")
            return

        progress = 0

        def update_progress(filename):
            nonlocal progress
            progress += 1
            pct = int((progress / self.file_count) * 100)
            self.progressUpdated.emit(pct, filename)

        if self.mode not in {"LC/GC-MS", "LC/GC Only", "MS Only"}:
            logger.error(f"Invalid mode: {self.mode}")
            return

        ctx = multiprocessing.get_context("spawn")
        try:
            with ProcessPoolExecutor(mp_context=ctx) as executor:
                futures = {}

                if self.file_type == "LC":
                    for lc_file in self.file_paths:
                        future = executor.submit(LCMeasurement, lc_file)
                        futures[future] = lc_file
                elif self.file_type == "MS":
                    for ms_file in self.file_paths:
                        future = executor.submit(MSMeasurement, ms_file)
                        futures[future] = ms_file
                else:
                    logger.error(f"Invalid file type: {self.file_type}")
                    return

                for future in as_completed(futures):
                    filename = futures[future]
                    try:
                        result_obj = future.result()
                        # Unpickle from the worker process
                        results[result_obj.filename] = result_obj
                        update_progress(result_obj.filename)
                    except Exception as e:
                        logger.error(
                            f"Error loading {filename}", traceback.format_exc()
                        )
                        self.error.emit(str(e))
        except Exception as e:
            logger.error("Error in loading pool: %s", traceback.format_exc())
            self.error.emit(str(e))
            return

        logger.debug(
            f"Loaded {len(results)} {self.file_type} files in {time.time() - st:.2f} s.",
        )
        self.finished.emit(results)


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
            ms_measurements = list(self.model.ms_measurements.values())
            total_files = len(ms_measurements)
        except AttributeError:
            logger.error("Model attributes not initialized properly.")
            return
        if total_files == 0:
            logger.warning("No files to process.")
            return

        progress = 0

        def update_progress():
            nonlocal progress
            progress += 1
            self.progressUpdated.emit(int(progress / total_files * 100))

        if self.mode not in {"LC/GC-MS", "LC/GC Only", "MS Only"}:
            logger.error(f"Invalid mode: {self.mode}")
            return
        results = []
        ctx = multiprocessing.get_context("spawn")
        max_workers = max(1, multiprocessing.cpu_count() - 1)
        try:
            with ProcessPoolExecutor(
                max_workers=max_workers, mp_context=ctx
            ) as executor:
                futures = {}
                if self.mode in {"LC/GC-MS", "MS Only"}:
                    for ms_file in ms_measurements:
                        future = executor.submit(
                            construct_xics,
                            ms_file.path,
                            self.model.compounds,
                            self.mass_accuracy,
                        )
                        futures[future] = ms_file.filename
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        logger.error(
                            f"Error in processing pool: {traceback.format_exc()}"
                        )
                        self.error.emit(str(e))
                    update_progress()
        except Exception as e:
            logger.error(f"Error in processing pool: {traceback.format_exc()}")
            self.error.emit(str(e))
            return

        logger.info(f"Processed {len(results)} MS files in {time.time() - st:.2f} s.")
        self.finished.emit(results)
