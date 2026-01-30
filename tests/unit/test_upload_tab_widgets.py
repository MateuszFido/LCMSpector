"""
Widget interaction tests for UploadTab.

Tests browse buttons, file list operations, clear buttons,
ion table operations, process button, and mass accuracy slider.
"""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem


class TestBrowseButtons:
    """Test browse button interactions."""

    def test_browse_lc_button_exists(self, upload_tab):
        """Browse LC button exists."""
        assert upload_tab.browseLC is not None
        # Note: isVisible() returns False when parent widget is not shown

    def test_browse_ms_button_exists(self, upload_tab):
        """Browse MS button exists."""
        assert upload_tab.browseMS is not None
        # Note: isVisible() returns False when parent widget is not shown

    def test_browse_lc_triggers_file_dialog(self, upload_tab, mock_file_dialog, qtbot, tmp_path):
        """Clicking browse LC opens file dialog and adds files."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("data")

        mock_file_dialog.set_return([str(test_file)])
        mock_file_dialog.start()

        qtbot.mouseClick(upload_tab.browseLC, Qt.MouseButton.LeftButton)

        mock_file_dialog.stop()

        # File should be added to list (basename only)
        assert upload_tab.listLC.count() == 1
        assert upload_tab.listLC.item(0).text() == "test.txt"

    def test_browse_ms_triggers_file_dialog(self, upload_tab, mock_file_dialog, qtbot, tmp_path):
        """Clicking browse MS opens file dialog and adds files."""
        test_file = tmp_path / "test.mzML"
        test_file.write_text("<mzML></mzML>")

        mock_file_dialog.set_return([str(test_file)])
        mock_file_dialog.start()

        qtbot.mouseClick(upload_tab.browseMS, Qt.MouseButton.LeftButton)

        mock_file_dialog.stop()

        # File should be added to list
        assert upload_tab.listMS.count() == 1
        assert upload_tab.listMS.item(0).text() == "test.mzML"

    def test_browse_canceled_no_files_added(self, upload_tab, mock_file_dialog, qtbot):
        """Canceling file dialog adds no files."""
        mock_file_dialog.set_return([])  # Empty = canceled
        mock_file_dialog.start()

        qtbot.mouseClick(upload_tab.browseLC, Qt.MouseButton.LeftButton)

        mock_file_dialog.stop()

        assert upload_tab.listLC.count() == 0

    def test_browse_annotations_in_chrom_mode(self, upload_tab_chrom_only, mock_file_dialog, qtbot, tmp_path):
        """Browse annotations works in LC/GC Only mode."""
        test_file = tmp_path / "annotations.txt"
        test_file.write_text("data")

        mock_file_dialog.set_return([str(test_file)])
        mock_file_dialog.start()

        qtbot.mouseClick(upload_tab_chrom_only.browseAnnotations, Qt.MouseButton.LeftButton)

        mock_file_dialog.stop()

        assert upload_tab_chrom_only.listAnnotations.count() == 1


class TestFileListOperations:
    """Test file list widget operations."""

    def test_add_file_to_lc_list(self, upload_tab):
        """Can add files to LC list programmatically."""
        upload_tab.listLC.addItem("file1.txt")
        upload_tab.listLC.addItem("file2.txt")
        assert upload_tab.listLC.count() == 2

    def test_add_file_to_ms_list(self, upload_tab):
        """Can add files to MS list programmatically."""
        upload_tab.listMS.addItem("file1.mzML")
        assert upload_tab.listMS.count() == 1

    def test_handle_files_dropped_lc_valid(self, upload_tab, sample_lc_file, signal_catcher):
        """handle_files_dropped adds valid LC files."""
        upload_tab.files_loaded.connect(signal_catcher.slot)

        upload_tab.handle_files_dropped([str(sample_lc_file)], "LC")

        assert upload_tab.listLC.count() == 1
        assert signal_catcher.was_called
        assert signal_catcher.args[0] == "LC"

    def test_handle_files_dropped_ms_valid(self, upload_tab, sample_ms_file, signal_catcher):
        """handle_files_dropped adds valid MS files."""
        upload_tab.files_loaded.connect(signal_catcher.slot)

        upload_tab.handle_files_dropped([str(sample_ms_file)], "MS")

        assert upload_tab.listMS.count() == 1
        assert signal_catcher.was_called
        assert signal_catcher.args[0] == "MS"

    def test_handle_files_dropped_invalid_extension(self, upload_tab, tmp_path, signal_catcher):
        """handle_files_dropped ignores files with invalid extensions."""
        invalid_file = tmp_path / "test.pdf"
        invalid_file.write_text("data")

        upload_tab.status_message.connect(signal_catcher.slot)
        upload_tab.handle_files_dropped([str(invalid_file)], "LC")

        assert upload_tab.listLC.count() == 0
        # Should emit status message about no valid files
        assert signal_catcher.was_called

    def test_handle_files_dropped_mixed_valid_invalid(self, upload_tab, sample_lc_file, tmp_path):
        """handle_files_dropped only adds valid files from mixed input."""
        invalid_file = tmp_path / "test.pdf"
        invalid_file.write_text("data")

        upload_tab.handle_files_dropped(
            [str(sample_lc_file), str(invalid_file)],
            "LC"
        )

        # Only valid file should be added
        assert upload_tab.listLC.count() == 1

    def test_get_file_list_lc(self, upload_tab):
        """get_file_list returns LC file names."""
        upload_tab.listLC.addItem("file1.txt")
        upload_tab.listLC.addItem("file2.txt")

        files = upload_tab.get_file_list("LC")
        assert files == ["file1.txt", "file2.txt"]

    def test_get_file_list_ms(self, upload_tab):
        """get_file_list returns MS file names."""
        upload_tab.listMS.addItem("data.mzML")

        files = upload_tab.get_file_list("MS")
        assert files == ["data.mzML"]

    def test_get_file_list_empty(self, upload_tab):
        """get_file_list returns empty list when no files."""
        files = upload_tab.get_file_list("LC")
        assert files == []

    def test_clear_file_list_lc(self, upload_tab):
        """clear_file_list clears LC list."""
        upload_tab.listLC.addItem("file.txt")
        upload_tab.clear_file_list("LC")
        assert upload_tab.listLC.count() == 0

    def test_clear_file_list_ms(self, upload_tab):
        """clear_file_list clears MS list."""
        upload_tab.listMS.addItem("file.mzML")
        upload_tab.clear_file_list("MS")
        assert upload_tab.listMS.count() == 0


class TestClearButtons:
    """Test clear button functionality."""

    def test_clear_lc_button_clears_list(self, upload_tab, qtbot):
        """Clear LC button empties the LC file list."""
        upload_tab.listLC.addItem("file1.txt")
        upload_tab.listLC.addItem("file2.txt")
        assert upload_tab.listLC.count() == 2

        qtbot.mouseClick(upload_tab.button_clear_LC, Qt.MouseButton.LeftButton)

        assert upload_tab.listLC.count() == 0

    def test_clear_ms_button_clears_list(self, upload_tab, qtbot):
        """Clear MS button empties the MS file list."""
        upload_tab.listMS.addItem("file.mzML")
        assert upload_tab.listMS.count() == 1

        qtbot.mouseClick(upload_tab.button_clear_MS, Qt.MouseButton.LeftButton)

        assert upload_tab.listMS.count() == 0

    def test_clear_ion_list_button(self, upload_tab, qtbot):
        """Clear ion list button empties the ion table."""
        # Add data to ion table
        upload_tab.ionTable.setRowCount(2)
        upload_tab.ionTable.setItem(0, 0, QTableWidgetItem("Compound1"))
        upload_tab.ionTable.setItem(0, 1, QTableWidgetItem("100.0"))

        qtbot.mouseClick(upload_tab.button_clear_ion_list, Qt.MouseButton.LeftButton)

        # Table should be cleared
        assert upload_tab.ionTable.rowCount() == 0 or (
            upload_tab.ionTable.item(0, 0) is None
        )


class TestIonTableOperations:
    """Test ion table widget operations."""

    def test_load_ion_list_from_combo(self, upload_tab, qtbot, sample_config):
        """Selecting ion list from combo populates table."""
        # Find "Test Compounds" in combo box
        index = upload_tab.comboBoxIonLists.findText("Test Compounds")
        assert index >= 0, "Test Compounds should be in combo box"

        upload_tab.comboBoxIonLists.setCurrentIndex(index)
        # update_ion_list is connected to currentIndexChanged

        # Table should have 2 rows (Caffeine and Glucose)
        assert upload_tab.ionTable.rowCount() == 2

    def test_ion_table_get_items(self, upload_tab):
        """ion_table.get_items() parses table into Compound objects."""
        # Set up table data manually
        upload_tab.ionTable.setRowCount(1)
        upload_tab.ionTable.setItem(0, 0, QTableWidgetItem("TestCompound"))
        upload_tab.ionTable.setItem(0, 1, QTableWidgetItem("100.0, 200.0"))
        upload_tab.ionTable.setItem(0, 2, QTableWidgetItem("[M+H]+, [M+Na]+"))

        items = upload_tab.ionTable.get_items()

        assert len(items) == 1
        assert items[0].name == "TestCompound"
        assert items[0].target_list == [100.0, 200.0]
        assert items[0].ion_info == ["[M+H]+", "[M+Na]+"]

    def test_ion_table_get_items_empty_row_skipped(self, upload_tab):
        """get_items() skips rows with empty compound name."""
        upload_tab.ionTable.setRowCount(2)
        upload_tab.ionTable.setItem(0, 0, QTableWidgetItem(""))  # Empty name
        upload_tab.ionTable.setItem(0, 1, QTableWidgetItem("100.0"))
        upload_tab.ionTable.setItem(1, 0, QTableWidgetItem("Valid"))
        upload_tab.ionTable.setItem(1, 1, QTableWidgetItem("200.0"))

        items = upload_tab.ionTable.get_items()

        assert len(items) == 1
        assert items[0].name == "Valid"

    def test_ion_table_get_items_handles_missing_info(self, upload_tab):
        """get_items() handles missing info column gracefully."""
        upload_tab.ionTable.setRowCount(1)
        upload_tab.ionTable.setItem(0, 0, QTableWidgetItem("TestCompound"))
        upload_tab.ionTable.setItem(0, 1, QTableWidgetItem("100.0"))
        # Column 2 (info) left empty

        items = upload_tab.ionTable.get_items()

        assert len(items) == 1
        assert items[0].ion_info == []

    def test_select_empty_ion_list(self, upload_tab):
        """Selecting 'Empty List' clears the table."""
        # First populate with data
        upload_tab.ionTable.setRowCount(2)
        upload_tab.ionTable.setItem(0, 0, QTableWidgetItem("Test"))

        # Select empty list
        index = upload_tab.comboBoxIonLists.findText("Empty List")
        if index >= 0:
            upload_tab.comboBoxIonLists.setCurrentIndex(index)
            assert upload_tab.ionTable.rowCount() == 0

    def test_select_create_new_clears_table(self, upload_tab):
        """Selecting 'Create new ion list...' sets row count to 0."""
        # First load a real ion list to populate the table
        index = upload_tab.comboBoxIonLists.findText("Test Compounds")
        if index >= 0:
            upload_tab.comboBoxIonLists.setCurrentIndex(index)

        # Now select "Create new ion list..."
        upload_tab.comboBoxIonLists.setCurrentIndex(0)  # "Create new ion list..."
        # update_ion_list sets row count to 0 for "Create new" selection
        assert upload_tab.ionTable.rowCount() == 0


class TestProcessButton:
    """Test process button behavior."""

    def test_process_button_initially_disabled(self, upload_tab):
        """Process button is disabled on init."""
        assert upload_tab.processButton.isEnabled() is False

    def test_process_button_can_be_enabled(self, upload_tab):
        """Process button can be enabled programmatically."""
        upload_tab.processButton.setEnabled(True)
        assert upload_tab.processButton.isEnabled() is True

    def test_process_button_emits_signal_on_click(self, upload_tab, signal_catcher, qtbot):
        """Clicking process button emits process_requested signal."""
        upload_tab.process_requested.connect(signal_catcher.slot)
        upload_tab.processButton.setEnabled(True)

        qtbot.mouseClick(upload_tab.processButton, Qt.MouseButton.LeftButton)

        assert signal_catcher.was_called

    def test_process_button_object_name(self, upload_tab):
        """Process button has correct object name."""
        assert upload_tab.processButton.objectName() == "processButton"

    def test_process_button_is_default(self, upload_tab):
        """Process button is marked as default."""
        assert upload_tab.processButton.isDefault() is True


class TestMassAccuracySlider:
    """Test mass accuracy slider behavior."""

    def test_slider_default_value(self, upload_tab):
        """Slider has correct default value (0.0001)."""
        assert upload_tab.mass_accuracy == 0.0001

    def test_slider_value_changes(self, upload_tab, qtbot):
        """Slider value can be changed."""
        # Move slider to different position
        upload_tab.mass_accuracy_slider.slider.setValue(0)  # First value (0.1)
        assert upload_tab.mass_accuracy == 0.1

    def test_slider_value_property(self, upload_tab):
        """mass_accuracy property returns current slider value."""
        # Set to a known position
        upload_tab.mass_accuracy_slider.slider.setValue(2)  # 0.001
        assert upload_tab.mass_accuracy == 0.001

    def test_slider_label_updates(self, upload_tab):
        """Slider label updates when value changes."""
        upload_tab.mass_accuracy_slider.slider.setValue(1)  # 0.01
        assert upload_tab.mass_accuracy_slider.value_label.text() == "0.01"

    def test_slider_emits_value_changed(self, upload_tab, signal_catcher):
        """Slider emits valueChanged signal."""
        upload_tab.mass_accuracy_slider.valueChanged.connect(signal_catcher.slot)

        upload_tab.mass_accuracy_slider.slider.setValue(0)

        assert signal_catcher.was_called
        assert signal_catcher.args[0] == 0.1
