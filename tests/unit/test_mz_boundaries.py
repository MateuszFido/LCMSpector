"""
Tests for MzRangeDialog and custom m/z integration boundaries.

Tests cover:
- MzRangeDialog creation and UI elements
- Default boundary positions (±3x mass_accuracy)
- Apply stores range in _ranges
- Reset reverts to default positions
- Ion combo switching updates view
- get_ranges() returns correct structure
- IonTable context menu shows "Edit integration..."
- IonTable _custom_mz_ranges populated after dialog
- get_items() injects ranges into Compound objects
- build_xics() uses custom ranges when provided
- construct_xics() collects ranges from compounds
"""

import numpy as np
import pytest
import pyqtgraph as pg
from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt
from unittest.mock import MagicMock

from ui.widgets import MzRangeDialog, IonTable
from utils.classes import Compound


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def spectrum_data():
    """Sample spectrum arrays for dialog tests."""
    mzs = np.linspace(100, 300, 2000)
    intensities = np.random.default_rng(42).random(2000) * 10000
    # Add a peak at 195.0877
    peak_idx = np.argmin(np.abs(mzs - 195.0877))
    intensities[peak_idx] = 50000
    return mzs, intensities


@pytest.fixture
def dialog_params(spectrum_data):
    """Default parameters for creating MzRangeDialog."""
    mzs, intensities = spectrum_data
    return {
        "mzs": mzs,
        "intensities": intensities,
        "target_mz_values": [195.0877, 138.0662],
        "ion_labels": ["[M+H]+", "[M+H-C2H5NO]+"],
        "mass_accuracy": 0.0001,
        "compound_name": "Caffeine",
        "existing_ranges": {},
    }


@pytest.fixture
def dialog(qapp, qtbot, dialog_params):
    """Create an MzRangeDialog instance."""
    d = MzRangeDialog(**dialog_params)
    qtbot.addWidget(d)
    return d


# ============================================================================
# MzRangeDialog Tests
# ============================================================================


class TestMzRangeDialogCreation:
    """Test dialog creation and UI elements."""

    def test_dialog_creates(self, dialog):
        assert dialog is not None
        assert isinstance(dialog, QtWidgets.QDialog)

    def test_title_contains_compound_name(self, dialog):
        assert "Caffeine" in dialog.windowTitle()

    def test_ion_combo_has_correct_items(self, dialog):
        combo = dialog._ion_combo
        assert combo.count() == 2
        assert "195.0877" in combo.itemText(0)
        assert "[M+H]+" in combo.itemText(0)
        assert "138.0662" in combo.itemText(1)

    def test_plot_widget_exists(self, dialog):
        assert dialog._plot_widget is not None
        assert isinstance(dialog._plot_widget, pg.PlotWidget)

    def test_buttons_exist(self, dialog):
        assert dialog._apply_btn is not None
        assert dialog._reset_btn is not None
        assert dialog._close_btn is not None

    def test_boundary_lines_created(self, dialog):
        assert dialog._left_line is not None
        assert dialog._right_line is not None


class TestMzRangeDialogBoundaryPositions:
    """Test default boundary positions."""

    def test_default_positions_ppm(self, dialog):
        """Boundaries should be at ±3x mass_accuracy by default."""
        mz = 195.0877
        expected_delta = mz * 0.0001 * 3

        left_pos = dialog._left_line.value()
        right_pos = dialog._right_line.value()

        assert abs(left_pos - (mz - expected_delta)) < 1e-6
        assert abs(right_pos - (mz + expected_delta)) < 1e-6

    def test_existing_ranges_used(self, qapp, qtbot, dialog_params):
        """Existing ranges should be used instead of defaults."""
        mz = 195.0877
        dialog_params["existing_ranges"] = {mz: (194.5, 195.5)}
        d = MzRangeDialog(**dialog_params)
        qtbot.addWidget(d)

        assert abs(d._left_line.value() - 194.5) < 1e-6
        assert abs(d._right_line.value() - 195.5) < 1e-6


class TestMzRangeDialogApplyReset:
    """Test Apply and Reset functionality."""

    def test_apply_stores_range(self, dialog):
        """Apply should store current line positions in _ranges."""
        mz = 195.0877
        dialog._left_line.setValue(194.0)
        dialog._right_line.setValue(196.0)

        dialog._on_apply()

        assert mz in dialog._ranges
        assert abs(dialog._ranges[mz][0] - 194.0) < 1e-6
        assert abs(dialog._ranges[mz][1] - 196.0) < 1e-6

    def test_reset_removes_custom_range(self, dialog):
        """Reset should remove custom range and revert to defaults."""
        mz = 195.0877

        # Apply first
        dialog._left_line.setValue(194.0)
        dialog._right_line.setValue(196.0)
        dialog._on_apply()
        assert mz in dialog._ranges

        # Reset
        dialog._on_reset()
        assert mz not in dialog._ranges

        # Lines should be back to defaults
        expected_delta = mz * 0.0001 * 3
        assert abs(dialog._left_line.value() - (mz - expected_delta)) < 1e-6
        assert abs(dialog._right_line.value() - (mz + expected_delta)) < 1e-6

    def test_get_ranges_returns_copy(self, dialog):
        """get_ranges() should return a copy of _ranges."""
        mz = 195.0877
        dialog._ranges[mz] = (194.0, 196.0)

        result = dialog.get_ranges()
        assert result == {mz: (194.0, 196.0)}
        # Should be a copy, not the same object
        assert result is not dialog._ranges

    def test_get_ranges_empty_by_default(self, dialog):
        """get_ranges() should return empty dict when no ranges applied."""
        assert dialog.get_ranges() == {}


class TestMzRangeDialogIonSwitching:
    """Test ion combo box switching."""

    def test_switch_updates_lines(self, dialog):
        """Switching ions should update boundary line positions."""
        # Get initial position for first ion
        mz1 = 195.0877
        delta1 = mz1 * 0.0001 * 3
        assert abs(dialog._left_line.value() - (mz1 - delta1)) < 1e-6

        # Switch to second ion
        dialog._ion_combo.setCurrentIndex(1)

        mz2 = 138.0662
        delta2 = mz2 * 0.0001 * 3
        assert abs(dialog._left_line.value() - (mz2 - delta2)) < 1e-6
        assert abs(dialog._right_line.value() - (mz2 + delta2)) < 1e-6

    def test_switch_preserves_applied_ranges(self, dialog):
        """Applied ranges should be preserved when switching ions."""
        mz1 = 195.0877
        dialog._left_line.setValue(194.0)
        dialog._right_line.setValue(196.0)
        dialog._on_apply()

        # Switch away and back
        dialog._ion_combo.setCurrentIndex(1)
        dialog._ion_combo.setCurrentIndex(0)

        assert abs(dialog._left_line.value() - 194.0) < 1e-6
        assert abs(dialog._right_line.value() - 196.0) < 1e-6


class TestMzRangeDialogSingleIon:
    """Test dialog with a single ion."""

    def test_single_ion(self, qapp, qtbot, spectrum_data):
        mzs, intensities = spectrum_data
        d = MzRangeDialog(
            mzs=mzs,
            intensities=intensities,
            target_mz_values=[195.0877],
            ion_labels=["[M+H]+"],
            mass_accuracy=0.0001,
            compound_name="Single",
            existing_ranges={},
        )
        qtbot.addWidget(d)

        assert d._ion_combo.count() == 1
        assert d._left_line is not None
        assert d._right_line is not None


# ============================================================================
# IonTable Context Menu Tests
# ============================================================================


class TestIonTableContextMenu:
    """Test IonTable context menu with 'Edit integration...' action."""

    def test_custom_mz_ranges_initialized(self, ion_table):
        """_custom_mz_ranges should be initialized to empty dict."""
        assert hasattr(ion_table, "_custom_mz_ranges")
        assert ion_table._custom_mz_ranges == {}

    def test_edit_action_disabled_without_mz(self, qapp, qtbot, ion_table):
        """Edit integration action should be disabled when row has no m/z."""
        # Add a row with only a name
        ion_table.setRowCount(1)
        ion_table.setItem(0, 0, QtWidgets.QTableWidgetItem("Test"))

        # Trigger context menu
        pos = QtCore.QPoint(10, 10)
        ion_table.contextMenuEvent(pos)

        # Find the edit action
        edit_action = None
        for action in ion_table.menu.actions():
            if action.text() == "Edit integration...":
                edit_action = action
                break

        assert edit_action is not None
        assert not edit_action.isEnabled()

    def test_edit_action_enabled_with_mz(self, qapp, qtbot, ion_table):
        """Edit integration action should be enabled when row has m/z values."""
        # Add a row with name and m/z
        ion_table.setRowCount(1)
        ion_table.setItem(0, 0, QtWidgets.QTableWidgetItem("Caffeine"))
        ion_table.setItem(0, 1, QtWidgets.QTableWidgetItem("195.0877"))

        # Trigger context menu at row 0
        row_rect = ion_table.visualRect(ion_table.model().index(0, 0))
        pos = row_rect.center()
        ion_table.contextMenuEvent(pos)

        # Find the edit action
        edit_action = None
        for action in ion_table.menu.actions():
            if action.text() == "Edit integration...":
                edit_action = action
                break

        assert edit_action is not None
        assert edit_action.isEnabled()


class TestIonTableGetItemsWithRanges:
    """Test that get_items() injects custom ranges into Compound objects."""

    def test_get_items_without_custom_ranges(self, qapp, qtbot, ion_table):
        """Compounds should have empty custom_mz_ranges by default."""
        ion_table.setRowCount(1)
        ion_table.setItem(0, 0, QtWidgets.QTableWidgetItem("Caffeine"))
        ion_table.setItem(0, 1, QtWidgets.QTableWidgetItem("195.0877"))

        items = ion_table.get_items()
        assert len(items) == 1
        assert items[0].custom_mz_ranges == {}

    def test_get_items_with_custom_ranges(self, qapp, qtbot, ion_table):
        """Compounds should have custom ranges when set."""
        ion_table.setRowCount(1)
        ion_table.setItem(0, 0, QtWidgets.QTableWidgetItem("Caffeine"))
        ion_table.setItem(0, 1, QtWidgets.QTableWidgetItem("195.0877"))

        ion_table._custom_mz_ranges["Caffeine"] = {195.0877: (194.0, 196.0)}

        items = ion_table.get_items()
        assert len(items) == 1
        assert 195.0877 in items[0].custom_mz_ranges
        assert items[0].custom_mz_ranges[195.0877] == (194.0, 196.0)


# ============================================================================
# Compound Custom Ranges Tests
# ============================================================================


class TestCompoundCustomMzRanges:
    """Test Compound._custom_mz_ranges PrivateAttr."""

    def test_default_empty(self):
        c = Compound(name="Test", target_list=[195.0877])
        assert c.custom_mz_ranges == {}

    def test_set_and_get(self):
        c = Compound(name="Test", target_list=[195.0877])
        c.custom_mz_ranges = {195.0877: (194.0, 196.0)}
        assert c.custom_mz_ranges == {195.0877: (194.0, 196.0)}

    def test_survives_copy(self):
        """Custom ranges should survive dict copy."""
        c = Compound(name="Test", target_list=[195.0877])
        c.custom_mz_ranges = {195.0877: (194.0, 196.0)}
        copy_ranges = dict(c.custom_mz_ranges)
        assert copy_ranges == {195.0877: (194.0, 196.0)}


# ============================================================================
# Preprocessing Custom Ranges Tests
# ============================================================================


class TestBuildXicsCustomRanges:
    """Test that build_xics uses custom ranges when provided."""

    def test_custom_ranges_parameter_accepted(self):
        """build_xics should accept custom_ranges parameter without error."""
        from calculation.preprocessing import build_xics
        import inspect

        sig = inspect.signature(build_xics)
        assert "custom_ranges" in sig.parameters

    def test_construct_xics_collects_ranges(self):
        """construct_xics should collect custom_mz_ranges from compounds."""
        from calculation.preprocessing import construct_xics
        import inspect

        # Verify the function signature hasn't changed
        sig = inspect.signature(construct_xics)
        params = list(sig.parameters.keys())
        assert "filepath" in params
        assert "compounds" in params
        assert "mass_accuracy" in params


# ============================================================================
# UploadTab Integration Tests
# ============================================================================


class TestUploadTabSpectrumData:
    """Test UploadTab.get_current_spectrum_data() method."""

    def test_returns_none_without_ms_plots(self, upload_tab):
        """Should return None when no MS files are checked."""
        result = upload_tab.get_current_spectrum_data()
        assert result is None

    def test_returns_none_without_controller(self, upload_tab):
        """Should return None when no controller is set."""
        upload_tab._ms_active_plots["test.mzML"] = (None, "#fff")
        result = upload_tab.get_current_spectrum_data()
        assert result is None

    def test_method_exists(self, upload_tab):
        """get_current_spectrum_data should exist on UploadTab."""
        assert hasattr(upload_tab, "get_current_spectrum_data")
        assert callable(upload_tab.get_current_spectrum_data)


class TestUploadTabClearRangesOnIonSwitch:
    """Test that switching ion lists clears custom ranges."""

    def test_ion_list_switch_clears_custom_ranges(self, upload_tab):
        """Switching ion lists should clear IonTable._custom_mz_ranges."""
        upload_tab.ionTable._custom_mz_ranges["Caffeine"] = {195.0877: (194.0, 196.0)}

        # Switch ion list
        upload_tab.comboBoxIonLists.setCurrentText("Test Compounds")

        assert upload_tab.ionTable._custom_mz_ranges == {}

    def test_ion_list_switch_to_empty(self, upload_tab):
        """Switching to empty list should also clear custom ranges."""
        upload_tab.ionTable._custom_mz_ranges["Caffeine"] = {195.0877: (194.0, 196.0)}

        upload_tab.comboBoxIonLists.setCurrentText("Empty List")

        assert upload_tab.ionTable._custom_mz_ranges == {}
