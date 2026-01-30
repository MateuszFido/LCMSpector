"""
Custom widget tests for DragDropListWidget, IonTable, and LabelledSlider.

Tests widget-specific functionality independent of the UploadTab context.
"""
import pytest
from pathlib import Path
from PySide6.QtCore import Qt, QMimeData, QUrl
from PySide6.QtGui import QDropEvent, QDragEnterEvent
from PySide6.QtWidgets import QTableWidgetItem
from unittest.mock import MagicMock, patch


class TestDragDropListWidget:
    """Test DragDropListWidget custom functionality."""

    def test_accepts_drops(self, drag_drop_list):
        """Widget is configured to accept drops."""
        assert drag_drop_list.acceptDrops() is True

    def test_word_wrap_enabled(self, drag_drop_list):
        """Widget has word wrap enabled."""
        assert drag_drop_list.wordWrap() is True

    def test_add_item(self, drag_drop_list):
        """Can add items programmatically."""
        drag_drop_list.addItem("test_file.txt")
        assert drag_drop_list.count() == 1
        assert drag_drop_list.item(0).text() == "test_file.txt"

    def test_clear_items(self, drag_drop_list):
        """Can clear all items."""
        drag_drop_list.addItem("file1.txt")
        drag_drop_list.addItem("file2.txt")
        drag_drop_list.clear()
        assert drag_drop_list.count() == 0

    def test_delete_key_removes_item(self, drag_drop_list, qtbot):
        """Delete key removes current item."""
        drag_drop_list.addItem("file1.txt")
        drag_drop_list.addItem("file2.txt")
        drag_drop_list.setCurrentRow(0)

        qtbot.keyClick(drag_drop_list, Qt.Key.Key_Delete)

        assert drag_drop_list.count() == 1
        assert drag_drop_list.item(0).text() == "file2.txt"

    def test_backspace_key_removes_item(self, drag_drop_list, qtbot):
        """Backspace key removes current item."""
        drag_drop_list.addItem("file1.txt")
        drag_drop_list.setCurrentRow(0)

        qtbot.keyClick(drag_drop_list, Qt.Key.Key_Backspace)

        assert drag_drop_list.count() == 0

    def test_files_dropped_signal_exists(self, drag_drop_list):
        """filesDropped signal is defined."""
        assert hasattr(drag_drop_list, 'filesDropped')

    def test_files_dropped_signal_emits_on_drop(self, drag_drop_list, signal_catcher, tmp_path):
        """filesDropped signal emits when files are dropped."""
        drag_drop_list.filesDropped.connect(signal_catcher.slot)

        # Create mock drop event with file URLs
        test_file = tmp_path / "dropped.txt"
        test_file.write_text("content")

        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(str(test_file))])

        # Create a mock drop event
        mock_event = MagicMock()
        mock_event.mimeData.return_value = mime_data

        # Call dropEvent directly
        drag_drop_list.dropEvent(mock_event)

        assert signal_catcher.was_called
        # Compare using Path objects to handle Windows/Unix path format differences
        # (Qt returns forward slashes on Windows, while str(Path) uses backslashes)
        dropped_paths = [Path(p) for p in signal_catcher.args[0]]
        assert test_file in dropped_paths

    def test_drag_enter_accepts_file_urls(self, drag_drop_list, tmp_path):
        """dragEnterEvent accepts events with file URLs."""
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile("/path/to/file.txt")])

        mock_event = MagicMock()
        mock_event.mimeData.return_value = mime_data

        drag_drop_list.dragEnterEvent(mock_event)

        mock_event.acceptProposedAction.assert_called_once()

    def test_context_menu_policy(self, drag_drop_list):
        """Widget has custom context menu policy."""
        assert drag_drop_list.contextMenuPolicy() == Qt.ContextMenuPolicy.CustomContextMenu


class TestIonTable:
    """Test IonTable custom functionality."""

    def test_has_three_columns(self, ion_table):
        """Table has 3 columns."""
        assert ion_table.columnCount() == 3

    def test_column_headers(self, ion_table):
        """Table has correct column headers."""
        headers = [
            ion_table.horizontalHeaderItem(i).text()
            for i in range(3)
        ]
        assert headers == ["Compound", "Expected m/z", "Add. info"]

    def test_object_name(self, ion_table):
        """Table has correct object name."""
        assert ion_table.objectName() == "ionTable"

    def test_initial_row_count(self, ion_table):
        """Table starts with 50 rows."""
        assert ion_table.rowCount() == 50

    def test_get_items_empty_table(self, ion_table):
        """get_items returns empty list for empty table."""
        ion_table.setRowCount(0)
        items = ion_table.get_items()
        assert items == []

    def test_get_items_parses_compound(self, ion_table):
        """get_items correctly parses compound data."""
        ion_table.setRowCount(1)
        ion_table.setItem(0, 0, QTableWidgetItem("Caffeine"))
        ion_table.setItem(0, 1, QTableWidgetItem("195.0877, 138.0662"))
        ion_table.setItem(0, 2, QTableWidgetItem("[M+H]+, Fragment"))

        items = ion_table.get_items()

        assert len(items) == 1
        assert items[0].name == "Caffeine"
        assert items[0].target_list == [195.0877, 138.0662]
        assert items[0].ion_info == ["[M+H]+", "Fragment"]

    def test_get_items_handles_single_ion(self, ion_table):
        """get_items handles single ion value."""
        ion_table.setRowCount(1)
        ion_table.setItem(0, 0, QTableWidgetItem("Simple"))
        ion_table.setItem(0, 1, QTableWidgetItem("100.0"))
        ion_table.setItem(0, 2, QTableWidgetItem("[M+H]+"))

        items = ion_table.get_items()

        assert len(items) == 1
        assert items[0].target_list == [100.0]
        assert items[0].ion_info == ["[M+H]+"]

    def test_get_items_skips_empty_names(self, ion_table):
        """get_items skips rows without compound name."""
        ion_table.setRowCount(3)
        ion_table.setItem(0, 0, QTableWidgetItem("Valid1"))
        ion_table.setItem(0, 1, QTableWidgetItem("100.0"))
        ion_table.setItem(1, 0, QTableWidgetItem(""))  # Empty name
        ion_table.setItem(1, 1, QTableWidgetItem("200.0"))
        ion_table.setItem(2, 0, QTableWidgetItem("Valid2"))
        ion_table.setItem(2, 1, QTableWidgetItem("300.0"))

        items = ion_table.get_items()

        assert len(items) == 2
        assert items[0].name == "Valid1"
        assert items[1].name == "Valid2"

    def test_get_items_handles_whitespace_only_name(self, ion_table):
        """get_items skips rows with whitespace-only name."""
        ion_table.setRowCount(1)
        ion_table.setItem(0, 0, QTableWidgetItem("   "))
        ion_table.setItem(0, 1, QTableWidgetItem("100.0"))

        items = ion_table.get_items()

        assert len(items) == 0

    def test_get_items_handles_empty_ions(self, ion_table):
        """get_items handles empty ion column."""
        ion_table.setRowCount(1)
        ion_table.setItem(0, 0, QTableWidgetItem("NoIons"))
        ion_table.setItem(0, 1, QTableWidgetItem(""))

        items = ion_table.get_items()

        assert len(items) == 1
        assert items[0].target_list == []

    def test_get_items_handles_invalid_ion_format(self, ion_table):
        """get_items handles non-numeric ion values gracefully."""
        ion_table.setRowCount(1)
        ion_table.setItem(0, 0, QTableWidgetItem("BadData"))
        ion_table.setItem(0, 1, QTableWidgetItem("abc, xyz"))

        items = ion_table.get_items()

        assert len(items) == 1
        assert items[0].target_list == []

    def test_get_items_handles_null_cells(self, ion_table):
        """get_items handles None/null cells."""
        ion_table.setRowCount(1)
        ion_table.setItem(0, 0, QTableWidgetItem("OnlyName"))
        # Columns 1 and 2 left as None

        items = ion_table.get_items()

        assert len(items) == 1
        assert items[0].target_list == []
        assert items[0].ion_info == []

    def test_clear_table(self, ion_table):
        """Table can be cleared."""
        ion_table.setRowCount(5)
        ion_table.setItem(0, 0, QTableWidgetItem("Test"))

        ion_table.clearContents()
        ion_table.setRowCount(0)

        assert ion_table.rowCount() == 0


class TestLabelledSlider:
    """Test LabelledSlider custom widget."""

    def test_has_label(self, labelled_slider):
        """Widget has label with text."""
        assert labelled_slider.label is not None
        assert labelled_slider.label.text() == "Test Label"

    def test_has_slider(self, labelled_slider):
        """Widget has slider."""
        assert labelled_slider.slider is not None

    def test_has_value_label(self, labelled_slider):
        """Widget has value display label."""
        assert labelled_slider.value_label is not None

    def test_default_value(self, labelled_slider):
        """Slider starts at specified default value."""
        assert labelled_slider.value() == 0.001

    def test_value_label_shows_default(self, labelled_slider):
        """Value label shows default value."""
        assert labelled_slider.value_label.text() == "0.001"

    def test_slider_range(self, labelled_slider):
        """Slider range matches values list length."""
        assert labelled_slider.slider.minimum() == 0
        assert labelled_slider.slider.maximum() == 3  # len([0.1, 0.01, 0.001, 0.0001]) - 1

    def test_value_method_returns_current(self, labelled_slider):
        """value() method returns current slider value."""
        labelled_slider.slider.setValue(0)
        assert labelled_slider.value() == 0.1

        labelled_slider.slider.setValue(3)
        assert labelled_slider.value() == 0.0001

    def test_value_label_updates_on_change(self, labelled_slider, qtbot):
        """Value label updates when slider moves."""
        labelled_slider.slider.setValue(0)
        assert labelled_slider.value_label.text() == "0.1"

        labelled_slider.slider.setValue(1)
        assert labelled_slider.value_label.text() == "0.01"

    def test_value_changed_signal_exists(self, labelled_slider):
        """valueChanged signal is defined."""
        assert hasattr(labelled_slider, 'valueChanged')

    def test_value_changed_signal_emits(self, labelled_slider, signal_catcher):
        """valueChanged signal emits with new value."""
        labelled_slider.valueChanged.connect(signal_catcher.slot)

        labelled_slider.slider.setValue(0)

        assert signal_catcher.was_called
        assert signal_catcher.args[0] == 0.1

    def test_value_changed_emits_float(self, labelled_slider, signal_catcher):
        """valueChanged signal emits float value."""
        labelled_slider.valueChanged.connect(signal_catcher.slot)

        # Change to a different value than default (0.001 is index 2)
        labelled_slider.slider.setValue(1)  # 0.01

        assert signal_catcher.was_called
        assert isinstance(signal_catcher.args[0], float)
        assert signal_catcher.args[0] == 0.01

    def test_slider_is_horizontal(self, labelled_slider):
        """Slider orientation is horizontal."""
        assert labelled_slider.slider.orientation() == Qt.Orientation.Horizontal


class TestLabelledSliderCustomValues:
    """Test LabelledSlider with various value configurations."""

    def test_integer_values(self, qapp, qtbot):
        """Works with integer values."""
        from ui.widgets import LabelledSlider

        values = [1, 5, 10, 50, 100]
        slider = LabelledSlider("Int Slider", values, 10)
        qtbot.addWidget(slider)

        assert slider.value() == 10
        slider.slider.setValue(4)
        assert slider.value() == 100

    def test_string_display(self, qapp, qtbot):
        """Value label displays values as strings."""
        from ui.widgets import LabelledSlider

        values = [0.1, 0.01]
        slider = LabelledSlider("Precision", values, 0.1)
        qtbot.addWidget(slider)

        # Default shows as string
        assert slider.value_label.text() == "0.1"

    def test_default_not_in_values(self, qapp, qtbot):
        """Handles default value not in values list."""
        from ui.widgets import LabelledSlider

        values = [1, 2, 3]
        slider = LabelledSlider("Test", values, 99)  # 99 not in values
        qtbot.addWidget(slider)

        # Should default to first value (index 0)
        assert slider.slider.value() == 0
        assert slider.value() == 1
