# tests/test_workers.py
from unittest import mock
import pytest
import calculation.workers as workers


# ----------------------------------------------------------------------
# Helper objects --------------------------------------------------------
# ----------------------------------------------------------------------
class DummyModel:
    """Simple container mimicking the real model used by the workers."""

    def __init__(self, lc_files=None, ms_files=None, compounds=None):
        self.lc_measurements = lc_files or []
        # ``ms_measurements`` is a dict in the real code (values accessed later)
        self.ms_measurements = ms_files or {}
        self.compounds = compounds or []


class DummyLC:
    """Mimic the LCMeasurement return value."""

    def __init__(self, filename):
        self.filename = filename


class DummyMS:
    """Mimic the MSMeasurement return value."""

    def __init__(self, filename):
        self.filename = filename
        self.data = f"data-{filename}"


# ----------------------------------------------------------------------
# Fixtures -------------------------------------------------------------
# ----------------------------------------------------------------------
@pytest.fixture
def dummy_lc_files():
    return [f"lc_{i}.txt" for i in range(3)]


@pytest.fixture
def dummy_ms_files():
    # The real code expects a dict of filename → DummyMS
    return {f"ms_{i}.txt": DummyMS(f"ms_{i}.txt") for i in range(2)}


@pytest.fixture
def dummy_model(dummy_lc_files, dummy_ms_files):
    return DummyModel(lc_files=dummy_lc_files, ms_files=dummy_ms_files)


# ----------------------------------------------------------------------
# Mocking utilities -----------------------------------------------------
# ----------------------------------------------------------------------
def mock_executor_submit(return_map):
    """
    Return a mock ProcessPoolExecutor whose ``submit`` method yields futures
    that resolve to the values in *return_map* (a dict of callable → result).
    """
    mock_executor = mock.Mock()
    # each call to submit returns a Future‑like mock
    futures = []

    def submit(fn, *args, **kwargs):
        # Find the matching entry in the map (fn may be a class or function)
        key = fn
        result = (
            return_map[key](*args, **kwargs)
            if callable(return_map[key])
            else return_map[key]
        )
        future = mock.Mock()
        future.result.return_value = result
        futures.append(future)
        return future

    mock_executor.submit.side_effect = submit
    mock_executor.__enter__.return_value = mock_executor
    mock_executor.__exit__.return_value = None
    mock_executor.futures = futures
    return mock_executor


# ----------------------------------------------------------------------
# Tests for LoadingWorker -----------------------------------------------
# ----------------------------------------------------------------------
def test_loading_worker_success(dummy_model):
    """Happy‑path: both LC and MS files are loaded and signals emitted."""
    # Prepare the mapping that the mocked executor will use
    return_map = {
        workers.LCMeasurement: lambda f: DummyLC(f),
        workers.MSMeasurement: lambda f: DummyMS(f),
    }

    mock_executor = mock_executor_submit(return_map)

    with mock.patch("workers.ProcessPoolExecutor", return_value=mock_executor):
        # Capture emitted signals
        worker = workers.LoadingWorker(dummy_model, mode="LC/GC-MS", file_type="LC")
        progress_calls = []
        finished_calls = []
        error_calls = []

        worker.progressUpdated.connect(lambda p, fn: progress_calls.append((p, fn)))
        worker.finished.connect(lambda lc, ms: finished_calls.append((lc, ms)))
        worker.error.connect(lambda msg: error_calls.append(msg))

        # Run synchronously (no event loop needed)
        worker.run()

    # ---- Assertions ----------------------------------------------------
    # All files should have been processed → progress emitted 5 times (3 LC + 2 MS)
    assert len(progress_calls) == 5
    # The final signal should contain dictionaries with the right keys
    lc_res, ms_res = finished_calls[0]
    assert set(lc_res.keys()) == set(dummy_model.lc_measurements)
    assert set(ms_res.keys()) == set(dummy_model.ms_measurements.keys())
    # No error signals should have been emitted
    assert not error_calls


def test_loading_worker_invalid_mode(dummy_model):
    """Worker should log an error and emit nothing when mode is invalid."""
    worker = workers.LoadingWorker(dummy_model, mode="UNKNOWN", file_type="LC")
    error_spy = mock.Mock()
    worker.error.connect(error_spy)

    with mock.patch.object(workers.logger, "error") as log_err:
        worker.run()

    # No progress / finished signals, but an error log entry is produced
    log_err.assert_called_once()
    error_spy.assert_not_called()


def test_loading_worker_executor_raises(dummy_model):
    """If the executor raises, the worker should emit an error signal."""
    # Make the executor raise on submit
    mock_executor = mock.Mock()
    mock_executor.submit.side_effect = RuntimeError("boom")
    mock_executor.__enter__.return_value = mock_executor
    mock_executor.__exit__.return_value = None

    with mock.patch("workers.ProcessPoolExecutor", return_value=mock_executor):
        worker = workers.LoadingWorker(dummy_model, mode="LC/GC-MS", file_type="LC")
        err_msgs = []
        worker.error.connect(lambda msg: err_msgs.append(msg))

        worker.run()

    assert err_msgs  # at least one error message captured
    assert "boom" in err_msgs[0]


# ----------------------------------------------------------------------
# Tests for ProcessingWorker --------------------------------------------
# ----------------------------------------------------------------------
def test_processing_worker_success(dummy_model):
    """ProcessingWorker should call ``construct_xics`` for each MS file."""
    # Mock construct_xics to return a predictable value
    fake_result = {"dummy": "result"}
    construct_mock = mock.Mock(return_value=fake_result)

    # Mock executor to return futures that resolve to ``fake_result``
    return_map = {workers.construct_xics: lambda *a, **k: fake_result}
    mock_executor = mock_executor_submit(return_map)

    with (
        mock.patch("workers.construct_xics", construct_mock),
        mock.patch("workers.ProcessPoolExecutor", return_value=mock_executor),
    ):
        worker = workers.ProcessingWorker(
            dummy_model, mode="LC/GC-MS", mass_accuracy=0.01
        )
        progress = []
        finished = []
        errors = []

        worker.progressUpdated.connect(lambda p: progress.append(p))
        worker.finished.connect(lambda res: finished.append(res))
        worker.error.connect(lambda msg: errors.append(msg))

        worker.run()

    # All MS files processed → progress emitted twice
    assert len(progress) == len(dummy_model.ms_measurements)
    # ``construct_xics`` called once per file with expected arguments
    assert construct_mock.call_count == len(dummy_model.ms_measurements)
    for call in construct_mock.call_args_list:
        args, _ = call
        # first arg is filename, second is data, third is compounds list, fourth is mass_accuracy
        assert args[0].endswith(".txt")
        assert args[2] == dummy_model.compounds
        assert args[3] == 0.01

    # Result list should contain the fake result for each file
    assert finished[0] == [fake_result] * len(dummy_model.ms_measurements)
    assert not errors


def test_processing_worker_no_ms_files():
    """When there are no MS measurements the worker should exit silently."""
    model = DummyModel(lc_files=[], ms_files={})
    worker = workers.ProcessingWorker(model, mode="MS Only", mass_accuracy=0.01)

    with mock.patch.object(workers.logger, "warning") as warn_spy:
        worker.run()

    warn_spy.assert_called_once_with("No files to process.")


def test_processing_worker_invalid_mode(dummy_model):
    """Invalid mode should be logged and no further work performed."""
    worker = workers.ProcessingWorker(dummy_model, mode="BAD", mass_accuracy=0.01)

    with mock.patch.object(workers.logger, "error") as err_spy:
        worker.run()

    err_spy.assert_called_once()
    # No calls to construct_xics
    assert not workers.construct_xics.called
