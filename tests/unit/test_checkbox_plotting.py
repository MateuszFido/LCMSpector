"""
Tests for checkbox plotting feature in file lists.

Tests cover:
- CheckableDragDropListWidget functionality
- Checkbox state changes and signal emissions
- Plot overlay when files are checked
- Plot removal when files are unchecked
- Color cycling for multiple plots
- Graceful handling in modes without canvases
"""
import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import Qt


# ============================================================================
# CheckableDragDropListWidget Tests
# ============================================================================


class TestCheckableDragDropListWidget:
    """Tests for the CheckableDragDropListWidget class."""

    @pytest.fixture
    def checkable_list(self, qapp, qtbot):
        """Create an isolated CheckableDragDropListWidget for testing."""
        from ui.widgets import CheckableDragDropListWidget

        widget = CheckableDragDropListWidget(parent=None)
        qtbot.addWidget(widget)
        return widget

    def test_added_items_have_checkboxes(self, checkable_list):
        """Items added to the list should have checkbox functionality."""
        checkable_list.addItem("test_file.txt")

        item = checkable_list.item(0)
        assert item is not None
        # Check that the item has the user checkable flag
        assert item.flags() & Qt.ItemFlag.ItemIsUserCheckable

    def test_items_start_unchecked(self, checkable_list):
        """Items should start in unchecked state."""
        checkable_list.addItem("test_file.txt")

        item = checkable_list.item(0)
        assert item.checkState() == Qt.CheckState.Unchecked

    def test_checkbox_toggle_emits_signal(self, checkable_list, signal_catcher):
        """Toggling checkbox should emit itemCheckStateChanged signal."""
        checkable_list.itemCheckStateChanged.connect(signal_catcher.slot)
        checkable_list.addItem("test_file.txt")

        # Reset signal catcher after add (which also emits due to item creation)
        signal_catcher.reset()

        # Toggle the checkbox
        item = checkable_list.item(0)
        item.setCheckState(Qt.CheckState.Checked)

        assert signal_catcher.was_called
        assert signal_catcher.call_count == 1

    def test_signal_contains_correct_data(self, checkable_list, signal_catcher):
        """Signal should emit filename and boolean check state."""
        checkable_list.itemCheckStateChanged.connect(signal_catcher.slot)
        checkable_list.addItem("test_file.txt")

        # Reset after add
        signal_catcher.reset()

        # Check the item
        item = checkable_list.item(0)
        item.setCheckState(Qt.CheckState.Checked)

        assert signal_catcher.args == ("test_file.txt", True)

        # Uncheck the item
        signal_catcher.reset()
        item.setCheckState(Qt.CheckState.Unchecked)

        assert signal_catcher.args == ("test_file.txt", False)

    def test_takeItem_emits_uncheck_for_checked_items(self, checkable_list, signal_catcher):
        """Removing a checked item should emit uncheck signal."""
        checkable_list.itemCheckStateChanged.connect(signal_catcher.slot)
        checkable_list.addItem("test_file.txt")

        # Check the item
        item = checkable_list.item(0)
        item.setCheckState(Qt.CheckState.Checked)

        # Reset after checking
        signal_catcher.reset()

        # Remove the item
        checkable_list.takeItem(0)

        assert signal_catcher.was_called
        assert signal_catcher.args == ("test_file.txt", False)

    def test_takeItem_no_signal_for_unchecked_items(self, checkable_list, signal_catcher):
        """Removing an unchecked item should not emit signal."""
        checkable_list.addItem("test_file.txt")

        # Connect after adding (to avoid catching add signals)
        checkable_list.itemCheckStateChanged.connect(signal_catcher.slot)

        # Remove the unchecked item
        checkable_list.takeItem(0)

        assert not signal_catcher.was_called

    def test_multiple_items_independent_checkboxes(self, checkable_list, signal_catcher):
        """Multiple items should have independent checkbox states."""
        checkable_list.addItem("file1.txt")
        checkable_list.addItem("file2.txt")
        checkable_list.addItem("file3.txt")

        # Check only the second item
        checkable_list.item(1).setCheckState(Qt.CheckState.Checked)

        assert checkable_list.item(0).checkState() == Qt.CheckState.Unchecked
        assert checkable_list.item(1).checkState() == Qt.CheckState.Checked
        assert checkable_list.item(2).checkState() == Qt.CheckState.Unchecked


# ============================================================================
# UploadTab Checkbox Plotting Integration Tests
# ============================================================================


class TestUploadTabCheckboxPlotting:
    """Integration tests for checkbox plotting in UploadTab."""

    @pytest.fixture
    def mock_lc_data(self):
        """Create mock LC measurement data."""
        import pandas as pd

        mock_lc = MagicMock()
        mock_lc.baseline_corrected = pd.DataFrame({
            "Time (min)": [0.0, 1.0, 2.0, 3.0, 4.0],
            "Value (mAU)": [100.0, 150.0, 200.0, 150.0, 100.0]
        })
        return mock_lc

    @pytest.fixture
    def mock_ms_data(self):
        """Create mock MS measurement data."""
        mock_ms = MagicMock()
        mock_ms.tic_times = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        mock_ms.tic_values = np.array([1000.0, 1500.0, 2000.0, 1500.0, 1000.0])
        return mock_ms

    @pytest.fixture
    def upload_tab_with_mock_data(self, upload_tab, mock_controller, mock_lc_data, mock_ms_data):
        """Setup upload_tab with mock measurement data."""
        mock_controller.model.lc_measurements = {"test_file": mock_lc_data}
        mock_controller.model.ms_measurements = {"test_file": mock_ms_data}
        upload_tab.set_controller(mock_controller)
        return upload_tab

    def test_checking_lc_file_adds_plot_to_canvas(self, upload_tab_with_mock_data):
        """Checking an LC file should add its plot to canvas_baseline."""
        tab = upload_tab_with_mock_data

        # Add a file to the list
        tab.listLC.addItem("test_file.txt")

        # Initially no plots
        assert len(tab._lc_active_plots) == 0

        # Check the file
        item = tab.listLC.item(0)
        item.setCheckState(Qt.CheckState.Checked)

        # Should have one plot
        assert len(tab._lc_active_plots) == 1
        assert "test_file.txt" in tab._lc_active_plots

    def test_unchecking_lc_file_removes_plot(self, upload_tab_with_mock_data):
        """Unchecking an LC file should remove its plot from canvas_baseline."""
        tab = upload_tab_with_mock_data

        # Add and check a file
        tab.listLC.addItem("test_file.txt")
        item = tab.listLC.item(0)
        item.setCheckState(Qt.CheckState.Checked)

        assert len(tab._lc_active_plots) == 1

        # Uncheck the file
        item.setCheckState(Qt.CheckState.Unchecked)

        # Plot should be removed
        assert len(tab._lc_active_plots) == 0

    def test_multiple_checked_files_overlay(self, upload_tab, mock_controller):
        """Multiple checked files should create multiple overlaid plots."""
        import pandas as pd

        # Setup multiple mock LC files
        mock_lc1 = MagicMock()
        mock_lc1.baseline_corrected = pd.DataFrame({
            "Time (min)": [0.0, 1.0, 2.0],
            "Value (mAU)": [100.0, 150.0, 100.0]
        })
        mock_lc2 = MagicMock()
        mock_lc2.baseline_corrected = pd.DataFrame({
            "Time (min)": [0.0, 1.0, 2.0],
            "Value (mAU)": [200.0, 250.0, 200.0]
        })

        mock_controller.model.lc_measurements = {
            "file1": mock_lc1,
            "file2": mock_lc2
        }
        upload_tab.set_controller(mock_controller)

        # Add and check multiple files
        upload_tab.listLC.addItem("file1.txt")
        upload_tab.listLC.addItem("file2.txt")

        upload_tab.listLC.item(0).setCheckState(Qt.CheckState.Checked)
        upload_tab.listLC.item(1).setCheckState(Qt.CheckState.Checked)

        # Both should be plotted
        assert len(upload_tab._lc_active_plots) == 2
        assert "file1.txt" in upload_tab._lc_active_plots
        assert "file2.txt" in upload_tab._lc_active_plots

    def test_checked_files_use_different_colors(self, upload_tab, mock_controller):
        """Multiple checked files should use different colors from the palette."""
        import pandas as pd
        from ui.plotting import PlotStyle

        # Setup multiple mock LC files
        mock_lc1 = MagicMock()
        mock_lc1.baseline_corrected = pd.DataFrame({
            "Time (min)": [0.0, 1.0, 2.0],
            "Value (mAU)": [100.0, 150.0, 100.0]
        })
        mock_lc2 = MagicMock()
        mock_lc2.baseline_corrected = pd.DataFrame({
            "Time (min)": [0.0, 1.0, 2.0],
            "Value (mAU)": [200.0, 250.0, 200.0]
        })

        mock_controller.model.lc_measurements = {
            "file1": mock_lc1,
            "file2": mock_lc2
        }
        upload_tab.set_controller(mock_controller)

        # Add and check multiple files
        upload_tab.listLC.addItem("file1.txt")
        upload_tab.listLC.addItem("file2.txt")

        upload_tab.listLC.item(0).setCheckState(Qt.CheckState.Checked)
        upload_tab.listLC.item(1).setCheckState(Qt.CheckState.Checked)

        # Color index should have advanced
        assert upload_tab._color_index_lc == 2

    def test_checking_ms_file_plots_tic(self, upload_tab_with_mock_data):
        """Checking an MS file should plot its TIC to canvas_avgMS."""
        tab = upload_tab_with_mock_data

        # Add a file to the MS list
        tab.listMS.addItem("test_file.mzML")

        # Initially no plots
        assert len(tab._ms_active_plots) == 0

        # Check the file
        item = tab.listMS.item(0)
        item.setCheckState(Qt.CheckState.Checked)

        # Should have one plot
        assert len(tab._ms_active_plots) == 1
        assert "test_file.mzML" in tab._ms_active_plots

    def test_chrom_only_mode_checkbox_no_crash(self, upload_tab_chrom_only, mock_controller):
        """Checkbox changes in chrom-only mode (no canvases) should not crash."""
        import pandas as pd

        # Setup mock LC data
        mock_lc = MagicMock()
        mock_lc.baseline_corrected = pd.DataFrame({
            "Time (min)": [0.0, 1.0, 2.0],
            "Value (mAU)": [100.0, 150.0, 100.0]
        })

        mock_controller.model.lc_measurements = {"test_file": mock_lc}
        upload_tab_chrom_only.set_controller(mock_controller)

        # Add and check a file - should not raise
        upload_tab_chrom_only.listLC.addItem("test_file.txt")
        item = upload_tab_chrom_only.listLC.item(0)

        # This should not crash even though there's no canvas_baseline
        item.setCheckState(Qt.CheckState.Checked)
        item.setCheckState(Qt.CheckState.Unchecked)

        # No plots should be tracked since there's no canvas
        assert len(upload_tab_chrom_only._lc_active_plots) == 0

    def test_clear_resets_active_plots(self, upload_tab_with_mock_data):
        """Calling clear() should reset all plot tracking state."""
        tab = upload_tab_with_mock_data

        # Add and check files
        tab.listLC.addItem("test_file.txt")
        tab.listLC.item(0).setCheckState(Qt.CheckState.Checked)

        assert len(tab._lc_active_plots) == 1
        assert tab._color_index_lc > 0

        # Clear the tab
        tab.clear()

        # Plot tracking should be reset
        assert len(tab._lc_active_plots) == 0
        assert len(tab._ms_active_plots) == 0
        assert tab._color_index_lc == 0
        assert tab._color_index_ms == 0

    def test_removing_checked_item_removes_plot(self, upload_tab_with_mock_data):
        """Removing a checked item via takeItem should remove its plot."""
        tab = upload_tab_with_mock_data

        # Add and check a file
        tab.listLC.addItem("test_file.txt")
        tab.listLC.item(0).setCheckState(Qt.CheckState.Checked)

        assert len(tab._lc_active_plots) == 1

        # Remove the item using takeItem (simulating delete)
        tab.listLC.takeItem(0)

        # Plot should be removed
        assert len(tab._lc_active_plots) == 0

    def test_checkbox_no_plot_without_controller(self, upload_tab):
        """Checking files without controller set should not crash."""
        # No controller set
        upload_tab._controller = None

        # Add and check a file
        upload_tab.listLC.addItem("test_file.txt")
        item = upload_tab.listLC.item(0)

        # Should not crash
        item.setCheckState(Qt.CheckState.Checked)

        # No plots since no controller/data
        assert len(upload_tab._lc_active_plots) == 0

    def test_checkbox_no_plot_for_missing_file(self, upload_tab, mock_controller):
        """Checking a file not in measurements should not crash."""
        # Controller with empty measurements
        mock_controller.model.lc_measurements = {}
        upload_tab.set_controller(mock_controller)

        # Add and check a file that doesn't exist in measurements
        upload_tab.listLC.addItem("nonexistent_file.txt")
        item = upload_tab.listLC.item(0)

        # Should not crash
        item.setCheckState(Qt.CheckState.Checked)

        # No plots since file doesn't exist in measurements
        assert len(upload_tab._lc_active_plots) == 0


# ============================================================================
# Refresh After Load Tests (Race Condition Fix)
# ============================================================================


class TestRefreshCheckboxPlots:
    """Tests for the refresh_checkbox_plots() method that handles race conditions."""

    @pytest.fixture
    def mock_lc_data(self):
        """Create mock LC measurement data."""
        import pandas as pd

        mock_lc = MagicMock()
        mock_lc.baseline_corrected = pd.DataFrame({
            "Time (min)": [0.0, 1.0, 2.0, 3.0, 4.0],
            "Value (mAU)": [100.0, 150.0, 200.0, 150.0, 100.0]
        })
        return mock_lc

    @pytest.fixture
    def mock_ms_data(self):
        """Create mock MS measurement data."""
        mock_ms = MagicMock()
        mock_ms.tic_times = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        mock_ms.tic_values = np.array([1000.0, 1500.0, 2000.0, 1500.0, 1000.0])
        return mock_ms

    def test_refresh_plots_checked_lc_files_after_load(self, upload_tab, mock_controller, mock_lc_data):
        """Checked LC files should be plotted after refresh when data becomes available."""
        # Initially no data in model
        mock_controller.model.lc_measurements = {}
        upload_tab.set_controller(mock_controller)

        # Add and check a file BEFORE data is loaded
        upload_tab.listLC.addItem("test_file.txt")
        upload_tab.listLC.item(0).setCheckState(Qt.CheckState.Checked)

        # No plot yet (data not loaded)
        assert len(upload_tab._lc_active_plots) == 0

        # Now data loads
        mock_controller.model.lc_measurements = {"test_file": mock_lc_data}

        # Call refresh - simulates what controller does after loading
        upload_tab.refresh_checkbox_plots()

        # Plot should now exist
        assert len(upload_tab._lc_active_plots) == 1
        assert "test_file.txt" in upload_tab._lc_active_plots

    def test_refresh_plots_checked_ms_files_after_load(self, upload_tab, mock_controller, mock_ms_data):
        """Checked MS files should be plotted after refresh when data becomes available."""
        # Initially no data in model
        mock_controller.model.ms_measurements = {}
        upload_tab.set_controller(mock_controller)

        # Add and check a file BEFORE data is loaded
        upload_tab.listMS.addItem("test_file.mzML")
        upload_tab.listMS.item(0).setCheckState(Qt.CheckState.Checked)

        # No plot yet (data not loaded)
        assert len(upload_tab._ms_active_plots) == 0

        # Now data loads
        mock_controller.model.ms_measurements = {"test_file": mock_ms_data}

        # Call refresh
        upload_tab.refresh_checkbox_plots()

        # Plot should now exist
        assert len(upload_tab._ms_active_plots) == 1
        assert "test_file.mzML" in upload_tab._ms_active_plots

    def test_refresh_skips_already_plotted_files(self, upload_tab, mock_controller, mock_lc_data):
        """refresh_checkbox_plots should not re-plot files that are already plotted."""
        mock_controller.model.lc_measurements = {"test_file": mock_lc_data}
        upload_tab.set_controller(mock_controller)

        # Add and check a file (this will plot it immediately since data exists)
        upload_tab.listLC.addItem("test_file.txt")
        upload_tab.listLC.item(0).setCheckState(Qt.CheckState.Checked)

        assert len(upload_tab._lc_active_plots) == 1
        original_plot = upload_tab._lc_active_plots["test_file.txt"]

        # Call refresh
        upload_tab.refresh_checkbox_plots()

        # Should still have exactly one plot (same object)
        assert len(upload_tab._lc_active_plots) == 1
        assert upload_tab._lc_active_plots["test_file.txt"] is original_plot

    def test_refresh_only_plots_checked_files(self, upload_tab, mock_controller, mock_lc_data):
        """refresh_checkbox_plots should only plot checked files, not unchecked ones."""
        import pandas as pd

        mock_lc2 = MagicMock()
        mock_lc2.baseline_corrected = pd.DataFrame({
            "Time (min)": [0.0, 1.0, 2.0],
            "Value (mAU)": [50.0, 75.0, 50.0]
        })

        mock_controller.model.lc_measurements = {
            "file1": mock_lc_data,
            "file2": mock_lc2
        }
        upload_tab.set_controller(mock_controller)

        # Add two files, only check one
        upload_tab.listLC.addItem("file1.txt")
        upload_tab.listLC.addItem("file2.txt")
        upload_tab.listLC.item(0).setCheckState(Qt.CheckState.Checked)
        # file2 stays unchecked

        # Clear plots to simulate pre-load state
        upload_tab._lc_active_plots.clear()

        # Refresh
        upload_tab.refresh_checkbox_plots()

        # Only checked file should be plotted
        assert len(upload_tab._lc_active_plots) == 1
        assert "file1.txt" in upload_tab._lc_active_plots
        assert "file2.txt" not in upload_tab._lc_active_plots

    def test_refresh_handles_no_list_widgets(self, upload_tab_chrom_only, mock_controller):
        """refresh_checkbox_plots should handle modes without all list widgets."""
        upload_tab_chrom_only.set_controller(mock_controller)

        # Should not crash even if listMS doesn't exist
        upload_tab_chrom_only.refresh_checkbox_plots()


# ============================================================================
# Plot Preservation Tests (TIC Not Clearing LC Data)
# ============================================================================


class TestPlotPreservation:
    """Tests that clicking files doesn't clear checkbox overlay plots."""

    @pytest.fixture
    def mock_lc_data(self):
        """Create mock LC measurement data."""
        import pandas as pd

        mock_lc = MagicMock()
        mock_lc.baseline_corrected = pd.DataFrame({
            "Time (min)": [0.0, 1.0, 2.0, 3.0, 4.0],
            "Value (mAU)": [100.0, 150.0, 200.0, 150.0, 100.0]
        })
        mock_lc.path = "/path/to/test.txt"
        return mock_lc

    @pytest.fixture
    def mock_ms_data(self):
        """Create mock MS measurement data."""
        mock_ms = MagicMock()
        mock_ms.tic_times = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        mock_ms.tic_values = np.array([1000.0, 1500.0, 2000.0, 1500.0, 1000.0])
        mock_ms.filename = "test_file"
        mock_ms.data = []  # Mock MS scan data
        return mock_ms

    def test_clicking_ms_file_preserves_lc_checkbox_plots(self, upload_tab, mock_controller, mock_lc_data, mock_ms_data):
        """Clicking an MS file to view TIC should NOT clear LC checkbox plots."""
        import pandas as pd

        mock_controller.model.lc_measurements = {"lc_file": mock_lc_data}
        mock_controller.model.ms_measurements = {"ms_file": mock_ms_data}
        upload_tab.set_controller(mock_controller)

        # Add and check an LC file
        upload_tab.listLC.addItem("lc_file.txt")
        upload_tab.listLC.item(0).setCheckState(Qt.CheckState.Checked)

        assert len(upload_tab._lc_active_plots) == 1
        original_plot = upload_tab._lc_active_plots["lc_file.txt"]

        # Now simulate clicking an MS file (which calls _plot_raw_ms)
        with patch('ui.plotting.plot_total_ion_current'), \
             patch('ui.plotting.plot_average_ms_data'):
            upload_tab._plot_raw_ms(mock_ms_data)

        # LC checkbox plot should still be tracked
        assert len(upload_tab._lc_active_plots) == 1
        assert "lc_file.txt" in upload_tab._lc_active_plots

    def test_clicking_lc_file_preserves_checkbox_plots(self, upload_tab, mock_controller, mock_lc_data):
        """Clicking an LC file to view it should NOT clear other checkbox plots."""
        import pandas as pd

        mock_lc2 = MagicMock()
        mock_lc2.baseline_corrected = pd.DataFrame({
            "Time (min)": [0.0, 1.0, 2.0],
            "Value (mAU)": [50.0, 75.0, 50.0]
        })
        mock_lc2.path = "/path/to/file2.txt"

        mock_controller.model.lc_measurements = {
            "file1": mock_lc_data,
            "file2": mock_lc2
        }
        upload_tab.set_controller(mock_controller)

        # Add and check file1
        upload_tab.listLC.addItem("file1.txt")
        upload_tab.listLC.item(0).setCheckState(Qt.CheckState.Checked)

        assert len(upload_tab._lc_active_plots) == 1

        # Simulate clicking file2 (which calls _plot_raw_chromatography)
        with patch('ui.plotting.plot_absorbance_data'):
            upload_tab._plot_raw_chromatography(mock_lc2)

        # file1's checkbox plot should still be tracked
        assert len(upload_tab._lc_active_plots) == 1
        assert "file1.txt" in upload_tab._lc_active_plots

    def test_plot_absorbance_called_with_correct_args(self, upload_tab, mock_controller, mock_lc_data):
        """_plot_raw_chromatography should call plot_absorbance_data with color and pen_width."""
        mock_controller.model.lc_measurements = {"test_file": mock_lc_data}
        upload_tab.set_controller(mock_controller)

        with patch('ui.plotting.plot_absorbance_data') as mock_plot:
            upload_tab._plot_raw_chromatography(mock_lc_data)

            mock_plot.assert_called_once()
            # Verify color and pen_width were passed as keyword arguments
            call_kwargs = mock_plot.call_args
            assert call_kwargs.kwargs.get('color') == "#2EC4B6"
            assert call_kwargs.kwargs.get('pen_width') == 1

    def test_plot_tic_called_with_clear_false_in_ms_only_mode(self, upload_tab_ms_only, mock_controller, mock_ms_data):
        """_plot_raw_ms should call plot_total_ion_current with clear=False in MS Only mode."""
        mock_controller.model.ms_measurements = {"test_file": mock_ms_data}
        upload_tab_ms_only.set_controller(mock_controller)

        with patch('ui.plotting.plot_total_ion_current') as mock_tic, \
             patch('ui.plotting.plot_average_ms_data'):
            upload_tab_ms_only._plot_raw_ms(mock_ms_data)

            mock_tic.assert_called_once()
            # Verify clear=False was passed as keyword argument
            call_kwargs = mock_tic.call_args
            assert call_kwargs.kwargs.get('clear') is False

    def test_tic_not_plotted_in_lcgcms_mode(self, upload_tab, mock_controller, mock_ms_data):
        """_plot_raw_ms should NOT plot TIC in LC/GC-MS mode (would overwrite LC data)."""
        mock_controller.model.ms_measurements = {"test_file": mock_ms_data}
        upload_tab.set_controller(mock_controller)

        # upload_tab fixture is LC/GC-MS mode by default
        assert upload_tab._current_mode == "LC/GC-MS"

        with patch('ui.plotting.plot_total_ion_current') as mock_tic, \
             patch('ui.plotting.plot_average_ms_data') as mock_avg:
            upload_tab._plot_raw_ms(mock_ms_data)

            # TIC should NOT be called in LC/GC-MS mode
            mock_tic.assert_not_called()
            # But average MS should still be plotted
            mock_avg.assert_called_once()


class TestColorCycling:
    """Tests for color cycling in overlay plots."""

    def test_color_index_increments_on_each_plot(self, upload_tab, mock_controller):
        """Color index should increment each time a plot is added."""
        import pandas as pd

        # Setup multiple mock files
        for i in range(5):
            mock_lc = MagicMock()
            mock_lc.baseline_corrected = pd.DataFrame({
                "Time (min)": [0.0, 1.0, 2.0],
                "Value (mAU)": [100.0, 150.0, 100.0]
            })
            mock_controller.model.lc_measurements[f"file{i}"] = mock_lc

        upload_tab.set_controller(mock_controller)

        # Add and check multiple files
        for i in range(5):
            upload_tab.listLC.addItem(f"file{i}.txt")
            upload_tab.listLC.item(i).setCheckState(Qt.CheckState.Checked)

        assert upload_tab._color_index_lc == 5

    def test_color_index_wraps_around_palette(self, upload_tab, mock_controller):
        """Color index should wrap around when exceeding palette length."""
        import pandas as pd
        from ui.plotting import PlotStyle

        palette_length = len(PlotStyle.PALETTE)

        # Setup more files than palette colors
        for i in range(palette_length + 3):
            mock_lc = MagicMock()
            mock_lc.baseline_corrected = pd.DataFrame({
                "Time (min)": [0.0, 1.0, 2.0],
                "Value (mAU)": [100.0, 150.0, 100.0]
            })
            mock_controller.model.lc_measurements[f"file{i}"] = mock_lc

        upload_tab.set_controller(mock_controller)

        # Add and check more files than palette colors
        for i in range(palette_length + 3):
            upload_tab.listLC.addItem(f"file{i}.txt")
            upload_tab.listLC.item(i).setCheckState(Qt.CheckState.Checked)

        # Should have all plots (color wrapping handled by modulo)
        assert len(upload_tab._lc_active_plots) == palette_length + 3

    def test_lc_and_ms_have_independent_color_indices(self, upload_tab, mock_controller):
        """LC and MS should have independent color cycling."""
        import pandas as pd

        # Setup LC data
        mock_lc = MagicMock()
        mock_lc.baseline_corrected = pd.DataFrame({
            "Time (min)": [0.0, 1.0, 2.0],
            "Value (mAU)": [100.0, 150.0, 100.0]
        })
        mock_controller.model.lc_measurements = {"lc_file": mock_lc}

        # Setup MS data
        mock_ms = MagicMock()
        mock_ms.tic_times = np.array([0.0, 1.0, 2.0])
        mock_ms.tic_values = np.array([1000.0, 1500.0, 1000.0])
        mock_controller.model.ms_measurements = {"ms_file": mock_ms}

        upload_tab.set_controller(mock_controller)

        # Check LC file
        upload_tab.listLC.addItem("lc_file.txt")
        upload_tab.listLC.item(0).setCheckState(Qt.CheckState.Checked)

        # Check MS file
        upload_tab.listMS.addItem("ms_file.mzML")
        upload_tab.listMS.item(0).setCheckState(Qt.CheckState.Checked)

        # Both should be at index 1 (independent counters)
        assert upload_tab._color_index_lc == 1
        assert upload_tab._color_index_ms == 1


# ============================================================================
# Click Type Distinction Tests (Checkbox vs Text Click)
# ============================================================================


class TestClickTypeDistinction:
    """Tests that checkbox clicks and text clicks are handled differently."""

    def test_checkbox_click_pending_flag_initially_false(self, qapp, qtbot):
        """Checkbox click pending flag should start as False."""
        from ui.widgets import CheckableDragDropListWidget

        widget = CheckableDragDropListWidget(parent=None)
        qtbot.addWidget(widget)

        assert widget._checkbox_click_pending is False
        assert widget.was_checkbox_click() is False

    def test_was_checkbox_click_method_exists(self, qapp, qtbot):
        """CheckableDragDropListWidget should have was_checkbox_click method."""
        from ui.widgets import CheckableDragDropListWidget

        widget = CheckableDragDropListWidget(parent=None)
        qtbot.addWidget(widget)

        assert hasattr(widget, 'was_checkbox_click')
        assert callable(widget.was_checkbox_click)

    def test_checkbox_click_sets_flag_true(self, qapp, qtbot):
        """Clicking on checkbox area should set flag to True."""
        from ui.widgets import CheckableDragDropListWidget
        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtCore import QEvent

        widget = CheckableDragDropListWidget(parent=None)
        qtbot.addWidget(widget)
        widget.addItem("test_file.txt")
        widget.show()
        qtbot.waitExposed(widget)

        # Get the item rect
        item = widget.item(0)
        rect = widget.visualItemRect(item)

        # Click on the checkbox area (left side of item)
        checkbox_click_pos = QPoint(rect.left() + 10, rect.center().y())
        qtbot.mouseClick(widget.viewport(), Qt.MouseButton.LeftButton, pos=checkbox_click_pos)

        assert widget.was_checkbox_click() is True

    def test_text_click_sets_flag_false(self, qapp, qtbot):
        """Clicking on text area (not checkbox) should set flag to False."""
        from ui.widgets import CheckableDragDropListWidget
        from PySide6.QtCore import QPoint

        widget = CheckableDragDropListWidget(parent=None)
        qtbot.addWidget(widget)
        widget.addItem("test_file.txt")
        widget.show()
        qtbot.waitExposed(widget)

        # Get the item rect
        item = widget.item(0)
        rect = widget.visualItemRect(item)

        # Click on the text area (right side of item, past checkbox)
        text_click_pos = QPoint(rect.left() + 50, rect.center().y())
        qtbot.mouseClick(widget.viewport(), Qt.MouseButton.LeftButton, pos=text_click_pos)

        assert widget.was_checkbox_click() is False

    def test_handle_lc_clicked_skips_checkbox_click(self, upload_tab, mock_controller):
        """_handle_lc_clicked should return early when was_checkbox_click is True."""
        import pandas as pd

        mock_lc = MagicMock()
        mock_lc.baseline_corrected = pd.DataFrame({
            "Time (min)": [0.0, 1.0, 2.0],
            "Value (mAU)": [100.0, 150.0, 100.0]
        })
        mock_lc.path = "/path/to/test.txt"

        mock_controller.model.lc_measurements = {"test_file": mock_lc}
        upload_tab.set_controller(mock_controller)

        upload_tab.listLC.addItem("test_file.txt")
        item = upload_tab.listLC.item(0)

        # Simulate checkbox click pending
        upload_tab.listLC._checkbox_click_pending = True

        # Patch _plot_raw_chromatography to verify it's NOT called
        with patch.object(upload_tab, '_plot_raw_chromatography') as mock_plot:
            upload_tab._handle_lc_clicked(item)
            mock_plot.assert_not_called()

    def test_handle_lc_clicked_proceeds_for_text_click(self, upload_tab, mock_controller):
        """_handle_lc_clicked should highlight when was_checkbox_click is False."""
        import pandas as pd

        mock_lc = MagicMock()
        mock_lc.baseline_corrected = pd.DataFrame({
            "Time (min)": [0.0, 1.0, 2.0],
            "Value (mAU)": [100.0, 150.0, 100.0]
        })
        mock_lc.path = "/path/to/test.txt"

        mock_controller.model.lc_measurements = {"test_file": mock_lc}
        upload_tab.set_controller(mock_controller)

        upload_tab.listLC.addItem("test_file.txt")
        item = upload_tab.listLC.item(0)

        # First, check the file so it has a plot to highlight
        item.setCheckState(Qt.CheckState.Checked)

        # Simulate text click (not checkbox)
        upload_tab.listLC._checkbox_click_pending = False

        # Patch _set_plot_pen_width to verify highlighting is called
        with patch.object(upload_tab, '_set_plot_pen_width') as mock_highlight:
            upload_tab._handle_lc_clicked(item)
            # Verify the file was set as selected
            assert upload_tab._selected_lc_file == "test_file.txt"
            # Verify pen width was set to highlight
            mock_highlight.assert_called()

    def test_handle_ms_clicked_skips_checkbox_click(self, upload_tab, mock_controller):
        """_handle_ms_clicked should return early when was_checkbox_click is True."""
        mock_ms = MagicMock()
        mock_ms.tic_times = np.array([0.0, 1.0, 2.0])
        mock_ms.tic_values = np.array([1000.0, 1500.0, 1000.0])

        mock_controller.model.ms_measurements = {"test_file": mock_ms}
        upload_tab.set_controller(mock_controller)

        upload_tab.listMS.addItem("test_file.mzML")
        item = upload_tab.listMS.item(0)

        # Simulate checkbox click pending
        upload_tab.listMS._checkbox_click_pending = True

        # Patch _plot_raw_ms to verify it's NOT called
        with patch.object(upload_tab, '_plot_raw_ms') as mock_plot:
            upload_tab._handle_ms_clicked(item)
            mock_plot.assert_not_called()

    def test_handle_ms_clicked_proceeds_for_text_click(self, upload_tab, mock_controller):
        """_handle_ms_clicked should highlight when was_checkbox_click is False."""
        mock_ms = MagicMock()
        mock_ms.tic_times = np.array([0.0, 1.0, 2.0])
        mock_ms.tic_values = np.array([1000.0, 1500.0, 1000.0])

        mock_controller.model.ms_measurements = {"test_file": mock_ms}
        upload_tab.set_controller(mock_controller)

        upload_tab.listMS.addItem("test_file.mzML")
        item = upload_tab.listMS.item(0)

        # First, check the file so it has a plot to highlight
        item.setCheckState(Qt.CheckState.Checked)

        # Simulate text click (not checkbox)
        upload_tab.listMS._checkbox_click_pending = False

        # Patch _set_plot_pen_width to verify highlighting is called
        with patch.object(upload_tab, '_set_plot_pen_width') as mock_highlight:
            upload_tab._handle_ms_clicked(item)
            # Verify the file was set as selected
            assert upload_tab._selected_ms_file == "test_file.mzML"
            # Verify pen width was set to highlight
            mock_highlight.assert_called()


# ============================================================================
# Main View Plot Tracking Tests
# ============================================================================


class TestMainViewPlotTracking:
    """Tests for main view plot tracking and selective clearing."""

    @pytest.fixture
    def mock_lc_data(self):
        """Create mock LC measurement data."""
        import pandas as pd

        mock_lc = MagicMock()
        mock_lc.baseline_corrected = pd.DataFrame({
            "Time (min)": [0.0, 1.0, 2.0, 3.0, 4.0],
            "Value (mAU)": [100.0, 150.0, 200.0, 150.0, 100.0]
        })
        mock_lc.path = "/path/to/test.txt"
        return mock_lc

    def test_main_view_plots_initialized_empty(self, upload_tab):
        """_main_view_plots should be initialized as empty list."""
        assert hasattr(upload_tab, '_main_view_plots')
        assert upload_tab._main_view_plots == []

    def test_clear_resets_main_view_plots(self, upload_tab):
        """Calling clear() should reset _main_view_plots."""
        # Add some fake plots
        upload_tab._main_view_plots = [MagicMock(), MagicMock()]

        upload_tab.clear()

        assert upload_tab._main_view_plots == []

    def test_plot_raw_chromatography_removes_old_main_view_plots(self, upload_tab, mock_controller, mock_lc_data):
        """_plot_raw_chromatography should attempt to remove previous main view plots."""
        mock_controller.model.lc_measurements = {"test_file": mock_lc_data}
        upload_tab.set_controller(mock_controller)

        # Add a mock plot to main view plots that was previously plotted
        mock_old_plot = MagicMock()
        upload_tab._main_view_plots = [mock_old_plot]

        with patch('ui.plotting.plot_absorbance_data'):
            upload_tab._plot_raw_chromatography(mock_lc_data)

        # After plotting, _main_view_plots should be cleared and repopulated
        # The old list was cleared, so mock_old_plot should no longer be in it
        assert mock_old_plot not in upload_tab._main_view_plots

    def test_plot_raw_chromatography_tracks_new_plots(self, upload_tab, mock_controller, mock_lc_data):
        """_plot_raw_chromatography should track newly added plots."""
        mock_controller.model.lc_measurements = {"test_file": mock_lc_data}
        upload_tab.set_controller(mock_controller)

        with patch('ui.plotting.plot_absorbance_data'):
            upload_tab._plot_raw_chromatography(mock_lc_data)

        # Get the actual plot items from the canvas
        plot_items = upload_tab.canvas_baseline.getPlotItem().listDataItems()

        # If there are >= 3 plots, _main_view_plots should track the last 3
        if len(plot_items) >= 3:
            assert len(upload_tab._main_view_plots) == 3
            assert upload_tab._main_view_plots == plot_items[-3:]

    def test_checkbox_plots_preserved_after_file_click(self, upload_tab, mock_controller, mock_lc_data):
        """Checkbox overlay plots should be preserved when clicking a file."""
        import pandas as pd

        mock_lc2 = MagicMock()
        mock_lc2.baseline_corrected = pd.DataFrame({
            "Time (min)": [0.0, 1.0, 2.0],
            "Value (mAU)": [50.0, 75.0, 50.0]
        })
        mock_lc2.path = "/path/to/file2.txt"

        mock_controller.model.lc_measurements = {
            "file1": mock_lc_data,
            "file2": mock_lc2
        }
        upload_tab.set_controller(mock_controller)

        # Add and check file1 to create checkbox overlay
        upload_tab.listLC.addItem("file1.txt")
        upload_tab.listLC.item(0).setCheckState(Qt.CheckState.Checked)

        # Verify checkbox plot is tracked
        assert "file1.txt" in upload_tab._lc_active_plots
        checkbox_plot = upload_tab._lc_active_plots["file1.txt"]

        # Now simulate clicking file2 (text click, not checkbox)
        upload_tab.listLC._checkbox_click_pending = False

        with patch('ui.plotting.plot_absorbance_data'):
            upload_tab._plot_raw_chromatography(mock_lc2)

        # Checkbox plot should still be tracked (we don't touch _lc_active_plots)
        assert "file1.txt" in upload_tab._lc_active_plots
        # The checkbox plot object should still be the same
        assert upload_tab._lc_active_plots["file1.txt"] is checkbox_plot
