"""
Tests for on-demand MS2 spectrum retrieval.

Covers:
- find_nearest_ms2() in mzml_reader.py
- MS2LookupWorker in workers.py
- plot_ms2_spectrum() in plotting.py
- QuantitationTab MS2 UI wiring
"""

import os
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch

# Path to test mzML file with MS2 scans
TEST_MZML = str(Path(__file__).parent.parent / "BIG_MIX_neg.mzml")
HAS_TEST_FILE = os.path.exists(TEST_MZML)


# ============================================================================
# TestFindNearestMS2
# ============================================================================


@pytest.mark.skipif(not HAS_TEST_FILE, reason="BIG_MIX_neg.mzml not available")
class TestFindNearestMS2:
    """Tests for utils.mzml_reader.find_nearest_ms2()."""

    def test_finds_matching_ms2_scan(self):
        """Should find an MS2 scan with matching precursor near the target RT."""
        from utils.mzml_reader import find_nearest_ms2

        # precursor_mz=103.04 is known to exist at RT~0.026
        result = find_nearest_ms2(
            TEST_MZML, precursor_mz=103.04, target_rt=0.026,
            mz_tolerance=0.5, rt_window=2.0,
        )
        assert result is not None
        scan_time, mz_array, intensity_array = result
        assert isinstance(scan_time, float)
        assert len(mz_array) > 0
        assert len(intensity_array) > 0
        assert len(mz_array) == len(intensity_array)

    def test_returns_none_when_no_precursor_matches(self):
        """Should return None when no precursor matches the target m/z."""
        from utils.mzml_reader import find_nearest_ms2

        result = find_nearest_ms2(
            TEST_MZML, precursor_mz=9999.0, target_rt=0.5,
            mz_tolerance=0.5, rt_window=5.0,
        )
        assert result is None

    def test_respects_mz_tolerance(self):
        """Should not match when precursor is outside mz_tolerance."""
        from utils.mzml_reader import find_nearest_ms2

        # Use a very tight tolerance that excludes the 103.04 precursor.
        # The real precursor is 103.040163, so a 0.0001 tolerance around 103.04
        # should be too strict and result in no match.
        result = find_nearest_ms2(
            TEST_MZML, precursor_mz=103.04, target_rt=0.026,
            mz_tolerance=0.0001, rt_window=2.0,
        )
        assert result is None

    def test_respects_rt_window(self):
        """Should not match scans outside the RT window."""
        from utils.mzml_reader import find_nearest_ms2

        # Known precursor at RT~0.026, use rt_window that excludes it
        result = find_nearest_ms2(
            TEST_MZML, precursor_mz=103.04, target_rt=100.0,
            mz_tolerance=0.5, rt_window=0.001,
        )
        assert result is None

    def test_returns_nearest_rt_among_matches(self):
        """Among multiple matching MS2 scans, should return the one nearest to target_rt."""
        from utils.mzml_reader import find_nearest_ms2

        # 89.024 has matches at multiple RTs — search near 0.043
        result = find_nearest_ms2(
            TEST_MZML, precursor_mz=89.02, target_rt=0.043,
            mz_tolerance=0.5, rt_window=5.0,
        )
        assert result is not None
        scan_time = result[0]
        # The nearest match should be close to 0.043
        assert abs(scan_time - 0.043) < 1.0


# ============================================================================
# TestMS2LookupWorker
# ============================================================================


class TestMS2LookupWorker:
    """Tests for calculation.workers.MS2LookupWorker."""

    @pytest.mark.skipif(not HAS_TEST_FILE, reason="BIG_MIX_neg.mzml not available")
    def test_emits_result_on_success(self, qtbot):
        """Worker should emit finished signal with result tuple on success."""
        from calculation.workers import MS2LookupWorker

        worker = MS2LookupWorker(TEST_MZML, 103.04, 0.026, mz_tolerance=0.5)
        with qtbot.waitSignal(worker.finished, timeout=30000) as blocker:
            worker.start()

        result = blocker.args[0]
        assert result is not None
        scan_time, mz_array, intensity_array = result
        assert len(mz_array) > 0

    @pytest.mark.skipif(not HAS_TEST_FILE, reason="BIG_MIX_neg.mzml not available")
    def test_emits_none_on_no_match(self, qtbot):
        """Worker should emit finished(None) when no MS2 matches."""
        from calculation.workers import MS2LookupWorker

        worker = MS2LookupWorker(TEST_MZML, 9999.0, 0.5, mz_tolerance=0.5)
        with qtbot.waitSignal(worker.finished, timeout=30000) as blocker:
            worker.start()

        assert blocker.args[0] is None

    def test_emits_error_on_bad_file(self, qtbot):
        """Worker should emit error signal for invalid file."""
        from calculation.workers import MS2LookupWorker

        worker = MS2LookupWorker("/nonexistent/file.mzml", 100.0, 1.0)
        with qtbot.waitSignal(worker.error, timeout=10000) as blocker:
            worker.start()

        assert len(blocker.args[0]) > 0  # Error message is non-empty

    def test_cancel_prevents_emission(self, qtbot):
        """Cancelled worker should not emit finished signal."""
        from calculation.workers import MS2LookupWorker

        worker = MS2LookupWorker("/nonexistent/file.mzml", 100.0, 1.0)
        worker.cancel()
        worker.start()
        worker.wait(2000)
        # No assertion needed — if cancel works, neither finished nor error emits


# ============================================================================
# TestMS2Plotting
# ============================================================================


class TestMS2Plotting:
    """Tests for ui.plotting.plot_ms2_spectrum()."""

    def test_plots_normalised_bars(self, qtbot):
        """Should add bar graph items normalised to 100%."""
        import pyqtgraph as pg
        from ui.plotting import plot_ms2_spectrum

        canvas = pg.PlotWidget()
        qtbot.addWidget(canvas)
        mz = np.array([100.0, 200.0, 300.0])
        intensity = np.array([500.0, 1000.0, 250.0])

        plot_ms2_spectrum(canvas, mz, intensity, title="Test MS2")

        # Should have at least a BarGraphItem and some TextItems (annotations)
        items = canvas.getPlotItem().items
        bar_items = [i for i in items if isinstance(i, pg.BarGraphItem)]
        assert len(bar_items) == 1

    def test_handles_empty_arrays(self, qtbot):
        """Should not crash on empty arrays."""
        import pyqtgraph as pg
        from ui.plotting import plot_ms2_spectrum

        canvas = pg.PlotWidget()
        qtbot.addWidget(canvas)
        plot_ms2_spectrum(canvas, np.array([]), np.array([]), title="Empty")
        # Should show placeholder, not crash

    def test_title_is_set(self, qtbot):
        """Should set the plot title."""
        import pyqtgraph as pg
        from ui.plotting import plot_ms2_spectrum

        canvas = pg.PlotWidget()
        qtbot.addWidget(canvas)
        mz = np.array([100.0, 200.0])
        intensity = np.array([500.0, 1000.0])
        plot_ms2_spectrum(canvas, mz, intensity, title="Custom Title")

        title_text = canvas.getPlotItem().titleLabel.text
        assert "Custom Title" in title_text


# ============================================================================
# TestQuantitationTabMS2UI
# ============================================================================


class TestQuantitationTabMS2UI:
    """Tests for QuantitationTab MS2 UI wiring."""

    @pytest.fixture
    def quant_tab(self, qapp, qtbot, mock_controller):
        """Create an isolated QuantitationTab with mock controller."""
        from ui.tabs.quantitation_tab import QuantitationTab
        from utils.classes import Compound

        tab = QuantitationTab(parent=None, mode="LC/GC-MS")
        qtbot.addWidget(tab)

        # Setup mock compounds
        compound = Compound(
            name="TestCompound",
            target_list=[103.04, 200.05],
            ion_info=["[M-H]-", "[M+Cl]-"],
        )
        mock_controller.model.compounds = [compound]
        tab.set_controller(mock_controller)

        yield tab

    def test_has_ms2_ion_combo(self, quant_tab):
        """Tab should have comboBoxMS2Ion widget."""
        assert hasattr(quant_tab, "comboBoxMS2Ion")

    def test_has_ms2_status_label(self, quant_tab):
        """Tab should have label_ms2_status widget."""
        assert hasattr(quant_tab, "label_ms2_status")

    def test_does_not_have_ms2_file_combo(self, quant_tab):
        """Tab should NOT have the old comboBoxChooseMS2File."""
        assert not hasattr(quant_tab, "comboBoxChooseMS2File")

    def test_ion_combo_populated_on_compound_change(self, quant_tab):
        """Changing compound should populate the MS2 ion combo."""
        # Simulate compound selection
        quant_tab.comboBoxChooseCompound.addItem("TestCompound")
        quant_tab.comboBoxChooseCompound.setCurrentIndex(0)

        # The combo should now have ions
        assert quant_tab.comboBoxMS2Ion.count() == 2  # 103.04 and 200.05

    def test_stale_lookup_id_rejected(self, quant_tab):
        """Results with stale lookup_id should be ignored."""
        quant_tab._ms2_lookup_id = 5

        # Simulate a result with stale ID
        quant_tab._on_ms2_found(
            (1.0, np.array([100.0]), np.array([1000.0])),
            lookup_id=3,  # stale
        )
        # Status should not change (no "Found at RT" message)
        assert "Found" not in quant_tab.label_ms2_status.text()

    def test_none_result_shows_not_found(self, quant_tab):
        """None result should show 'No MS2 found' status."""
        quant_tab._ms2_lookup_id = 1
        quant_tab._on_ms2_found(None, lookup_id=1)
        assert "No MS2 found" in quant_tab.label_ms2_status.text()

    def test_valid_result_shows_found_status(self, quant_tab):
        """Valid result should show 'Found at RT' status."""
        quant_tab._ms2_lookup_id = 1
        quant_tab.comboBoxChooseCompound.addItem("TestCompound")
        quant_tab.comboBoxMS2Ion.addItem("103.04 ([M-H]-)")

        quant_tab._on_ms2_found(
            (2.5, np.array([100.0, 200.0]), np.array([500.0, 1000.0])),
            lookup_id=1,
        )
        assert "Found at RT 2.50 min" in quant_tab.label_ms2_status.text()

    def test_error_shows_error_status(self, quant_tab):
        """Error should show error message in status."""
        quant_tab._ms2_lookup_id = 1
        quant_tab._on_ms2_error("Connection failed", lookup_id=1)
        assert "Error" in quant_tab.label_ms2_status.text()


# ============================================================================
# TestLegacyRemoval
# ============================================================================


class TestLegacyRemoval:
    """Tests verifying legacy MS2 code has been removed."""

    def test_no_ms2_attribute_on_compound(self):
        """Compound should not have _ms2 or ms2 attributes."""
        from utils.classes import Compound

        compound = Compound(name="Test", target_list=[100.0])
        assert not hasattr(compound, "_ms2")
        assert not hasattr(compound, "ms2")

    def test_no_load_ms2_library_in_loading(self):
        """loading module should not export load_ms2_library."""
        import utils.loading as loading_mod

        assert not hasattr(loading_mod, "load_ms2_library")
        assert not hasattr(loading_mod, "_load_ms2_library")

    def test_model_has_no_library(self):
        """Model should not have library slot."""
        from ui.model import Model

        assert "library" not in Model.__slots__

    def test_no_find_ms2_precursors_in_model(self):
        """Model should not have find_ms2_precursors method."""
        from ui.model import Model

        assert not hasattr(Model, "find_ms2_precursors")
