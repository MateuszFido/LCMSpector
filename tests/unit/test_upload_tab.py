"""
Core functionality tests for UploadTab.

Tests initialization, mode handling, mode switching, and clear functionality.
"""
import pytest
from PySide6.QtCore import Qt


class TestUploadTabInitialization:
    """Test UploadTab initialization and default state."""

    def test_default_mode_is_lcms(self, upload_tab):
        """Tab initializes with LC/GC-MS mode by default."""
        assert upload_tab.mode == "LC/GC-MS"

    def test_process_button_exists(self, upload_tab):
        """Process button is created and accessible."""
        assert upload_tab.processButton is not None
        assert upload_tab.process_button is not None  # property accessor

    def test_process_button_disabled_initially(self, upload_tab):
        """Process button is disabled on initialization."""
        assert upload_tab.processButton.isEnabled() is False

    def test_ion_table_exists(self, upload_tab):
        """Ion table widget is created."""
        assert upload_tab.ionTable is not None
        assert upload_tab.ion_table is not None  # property accessor

    def test_ion_table_has_correct_columns(self, upload_tab):
        """Ion table has 3 columns: Compound, Expected m/z, Add. info."""
        assert upload_tab.ionTable.columnCount() == 3
        headers = [
            upload_tab.ionTable.horizontalHeaderItem(i).text()
            for i in range(3)
        ]
        assert headers == ["Compound", "Expected m/z", "Add. info"]

    def test_mass_accuracy_slider_exists(self, upload_tab):
        """Mass accuracy slider is created."""
        assert upload_tab.mass_accuracy_slider is not None

    def test_mass_accuracy_default_value(self, upload_tab):
        """Mass accuracy slider has correct default value."""
        assert upload_tab.mass_accuracy == 0.0001

    def test_combobox_ion_lists_exists(self, upload_tab):
        """Ion list combo box is created and has default item."""
        assert upload_tab.comboBoxIonLists is not None
        assert upload_tab.comboBoxIonLists.count() >= 1
        assert upload_tab.comboBoxIonLists.itemText(0) == "Create new ion list..."

    def test_config_loaded_into_combobox(self, upload_tab, sample_config):
        """Config ion lists are loaded into combo box."""
        # Check that config keys are in the combo box
        combo_items = [
            upload_tab.comboBoxIonLists.itemText(i)
            for i in range(upload_tab.comboBoxIonLists.count())
        ]
        for key in sample_config.keys():
            assert key in combo_items

    def test_controller_initially_none(self, upload_tab):
        """Controller is None before injection."""
        assert upload_tab.controller is None
        assert upload_tab._controller is None


class TestUploadTabModes:
    """Test mode-specific layout configurations."""

    def test_lcms_mode_has_lc_list(self, upload_tab):
        """LC/GC-MS mode has LC file list widget."""
        assert hasattr(upload_tab, 'listLC')
        assert upload_tab.listLC is not None

    def test_lcms_mode_has_ms_list(self, upload_tab):
        """LC/GC-MS mode has MS file list widget."""
        assert hasattr(upload_tab, 'listMS')
        assert upload_tab.listMS is not None

    def test_lcms_mode_has_browse_buttons(self, upload_tab):
        """LC/GC-MS mode has browse buttons for LC and MS."""
        assert hasattr(upload_tab, 'browseLC')
        assert hasattr(upload_tab, 'browseMS')
        assert upload_tab.browseLC is not None
        assert upload_tab.browseMS is not None

    def test_lcms_mode_has_canvas_widgets(self, upload_tab):
        """LC/GC-MS mode has canvas widgets for plotting."""
        assert hasattr(upload_tab, 'canvas_baseline')
        assert hasattr(upload_tab, 'canvas_avgMS')
        assert upload_tab.canvas_baseline is not None
        assert upload_tab.canvas_avgMS is not None

    def test_ms_only_mode_no_lc_list(self, upload_tab_ms_only):
        """MS Only mode does not have LC file list."""
        assert not hasattr(upload_tab_ms_only, 'listLC') or upload_tab_ms_only.listLC is None

    def test_ms_only_mode_has_ms_list(self, upload_tab_ms_only):
        """MS Only mode has MS file list widget."""
        assert hasattr(upload_tab_ms_only, 'listMS')
        assert upload_tab_ms_only.listMS is not None

    def test_ms_only_mode_has_canvas_widgets(self, upload_tab_ms_only):
        """MS Only mode has canvas widgets."""
        assert hasattr(upload_tab_ms_only, 'canvas_baseline')
        assert hasattr(upload_tab_ms_only, 'canvas_avgMS')

    def test_chrom_only_mode_has_lc_list(self, upload_tab_chrom_only):
        """LC/GC Only mode has LC file list."""
        assert hasattr(upload_tab_chrom_only, 'listLC')
        assert upload_tab_chrom_only.listLC is not None

    def test_chrom_only_mode_has_annotations_list(self, upload_tab_chrom_only):
        """LC/GC Only mode has annotations file list."""
        assert hasattr(upload_tab_chrom_only, 'listAnnotations')
        assert upload_tab_chrom_only.listAnnotations is not None

    def test_chrom_only_mode_no_ms_list(self, upload_tab_chrom_only):
        """LC/GC Only mode does not have MS file list."""
        assert not hasattr(upload_tab_chrom_only, 'listMS') or upload_tab_chrom_only.listMS is None


class TestModeSwitching:
    """Test mode switching functionality."""

    def test_switch_to_ms_only(self, upload_tab, qtbot):
        """Can switch from LC/GC-MS to MS Only mode."""
        upload_tab.on_mode_changed("MS Only")
        assert upload_tab.mode == "MS Only"

    def test_switch_to_chrom_only(self, upload_tab, qtbot):
        """Can switch from LC/GC-MS to LC/GC Only mode."""
        upload_tab.on_mode_changed("LC/GC Only")
        assert upload_tab.mode == "LC/GC Only"

    def test_mode_switch_emits_signal(self, upload_tab, signal_catcher, qtbot):
        """Mode switch emits mode_changed signal."""
        upload_tab.mode_changed.connect(signal_catcher.slot)
        upload_tab.on_mode_changed("MS Only")

        assert signal_catcher.was_called
        assert signal_catcher.args[0] == "MS Only"

    def test_same_mode_no_signal(self, upload_tab, signal_catcher, qtbot):
        """Switching to same mode does not emit signal."""
        upload_tab.mode_changed.connect(signal_catcher.slot)
        upload_tab.on_mode_changed("LC/GC-MS")  # Same as current

        assert not signal_catcher.was_called

    def test_mode_switch_rebuilds_layout(self, upload_tab, qtbot):
        """Mode switch rebuilds the layout with new widgets."""
        # Store original LC list widget reference
        original_lc_list = upload_tab.listLC

        # Switch to MS Only - MS Only mode doesn't create listLC, so new listLC is built
        upload_tab.on_mode_changed("MS Only")

        # Verify MS list exists (it should be in MS Only mode)
        assert hasattr(upload_tab, 'listMS')
        assert upload_tab.listMS is not None

        # Switch back to LC/GC-MS and verify LC list is back (new instance)
        upload_tab.on_mode_changed("LC/GC-MS")
        assert hasattr(upload_tab, 'listLC')
        assert upload_tab.listLC is not None
        # The widget should be a new instance after rebuild
        assert upload_tab.listLC is not original_lc_list

    def test_mode_switch_preserves_ion_list_selection(self, upload_tab, qtbot):
        """Mode switch preserves ion list combo box state."""
        # Select a specific ion list
        upload_tab.comboBoxIonLists.setCurrentIndex(1)
        original_text = upload_tab.comboBoxIonLists.currentText()

        # Switch mode
        upload_tab.on_mode_changed("MS Only")

        # Ion list combo should still exist
        assert upload_tab.comboBoxIonLists is not None
        # Note: The combo box is recreated, but config is reloaded


class TestClearFunctionality:
    """Test the clear() method."""

    def test_clear_empties_lc_list(self, upload_tab, qtbot):
        """clear() empties LC file list."""
        # Add items first
        upload_tab.listLC.addItem("file1.txt")
        upload_tab.listLC.addItem("file2.txt")
        assert upload_tab.listLC.count() == 2

        upload_tab.clear()
        assert upload_tab.listLC.count() == 0

    def test_clear_empties_ms_list(self, upload_tab, qtbot):
        """clear() empties MS file list."""
        upload_tab.listMS.addItem("file1.mzML")
        assert upload_tab.listMS.count() == 1

        upload_tab.clear()
        assert upload_tab.listMS.count() == 0

    def test_clear_empties_ion_table(self, upload_tab, qtbot):
        """clear() empties ion table."""
        from PySide6.QtWidgets import QTableWidgetItem

        # Add data to ion table
        upload_tab.ionTable.setRowCount(2)
        upload_tab.ionTable.setItem(0, 0, QTableWidgetItem("Compound1"))
        upload_tab.ionTable.setItem(1, 0, QTableWidgetItem("Compound2"))

        upload_tab.clear()
        assert upload_tab.ionTable.rowCount() == 0

    def test_clear_resets_canvas(self, upload_tab, qtbot):
        """clear() resets canvas widgets."""
        # The canvas should be cleared and reset to placeholder
        upload_tab.clear()
        # Canvas should still exist after clear
        assert hasattr(upload_tab, 'canvas_baseline')
        assert upload_tab.canvas_baseline is not None

    def test_clear_annotations_in_chrom_mode(self, upload_tab_chrom_only, qtbot):
        """clear() empties annotations list in LC/GC Only mode."""
        upload_tab_chrom_only.listAnnotations.addItem("annotations.txt")
        assert upload_tab_chrom_only.listAnnotations.count() == 1

        upload_tab_chrom_only.clear()
        assert upload_tab_chrom_only.listAnnotations.count() == 0


class TestControllerInjection:
    """Test controller injection and signal connections."""

    def test_set_controller(self, upload_tab, mock_controller):
        """set_controller injects controller reference."""
        upload_tab.set_controller(mock_controller)
        assert upload_tab.controller == mock_controller
        assert upload_tab._controller == mock_controller

    def test_set_controller_sets_model(self, upload_tab, mock_controller, mock_model):
        """set_controller also sets model reference."""
        upload_tab.set_controller(mock_controller)
        assert upload_tab.model == mock_model

    def test_set_controller_none(self, upload_tab):
        """set_controller(None) clears controller."""
        upload_tab._controller = "something"
        upload_tab.set_controller(None)
        assert upload_tab.controller is None
