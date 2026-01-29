"""
Signal emission tests for UploadTab.

Tests that signals are emitted correctly with proper arguments.
"""
import pytest
from PySide6.QtCore import Qt


class TestFilesLoadedSignal:
    """Test files_loaded signal emission."""

    def test_signal_emitted_on_lc_files_dropped(self, upload_tab, sample_lc_file, signal_catcher):
        """files_loaded emits for LC file drops."""
        upload_tab.files_loaded.connect(signal_catcher.slot)

        upload_tab.handle_files_dropped([str(sample_lc_file)], "LC")

        assert signal_catcher.was_called
        assert signal_catcher.call_count == 1

    def test_signal_emitted_on_ms_files_dropped(self, upload_tab, sample_ms_file, signal_catcher):
        """files_loaded emits for MS file drops."""
        upload_tab.files_loaded.connect(signal_catcher.slot)

        upload_tab.handle_files_dropped([str(sample_ms_file)], "MS")

        assert signal_catcher.was_called
        assert signal_catcher.call_count == 1

    def test_signal_contains_file_type(self, upload_tab, sample_lc_file, signal_catcher):
        """files_loaded signal includes file type."""
        upload_tab.files_loaded.connect(signal_catcher.slot)

        upload_tab.handle_files_dropped([str(sample_lc_file)], "LC")

        assert signal_catcher.args[0] == "LC"

    def test_signal_contains_file_paths(self, upload_tab, sample_lc_file, signal_catcher):
        """files_loaded signal includes file paths."""
        upload_tab.files_loaded.connect(signal_catcher.slot)

        upload_tab.handle_files_dropped([str(sample_lc_file)], "LC")

        file_paths = signal_catcher.args[1]
        assert len(file_paths) == 1
        assert str(sample_lc_file) in file_paths[0]

    def test_signal_not_emitted_for_invalid_files(self, upload_tab, tmp_path, signal_catcher):
        """files_loaded not emitted when all files are invalid."""
        invalid_file = tmp_path / "test.xyz"
        invalid_file.write_text("data")

        upload_tab.files_loaded.connect(signal_catcher.slot)
        upload_tab.handle_files_dropped([str(invalid_file)], "LC")

        # files_loaded should NOT be called (status_message is called instead)
        assert not signal_catcher.was_called

    def test_signal_emitted_once_for_multiple_files(self, upload_tab, tmp_path, signal_catcher):
        """files_loaded emits once with all valid files."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("data1")
        file2.write_text("data2")

        upload_tab.files_loaded.connect(signal_catcher.slot)
        upload_tab.handle_files_dropped([str(file1), str(file2)], "LC")

        # Should emit once with both files
        assert signal_catcher.call_count == 1
        assert len(signal_catcher.args[1]) == 2

    def test_signal_for_annotations(self, upload_tab_chrom_only, sample_annotation_file, signal_catcher):
        """files_loaded emits for annotation files."""
        upload_tab_chrom_only.files_loaded.connect(signal_catcher.slot)

        upload_tab_chrom_only.handle_files_dropped([str(sample_annotation_file)], "Annotations")

        assert signal_catcher.was_called
        assert signal_catcher.args[0] == "Annotations"


class TestProcessRequestedSignal:
    """Test process_requested signal emission."""

    def test_signal_emitted_on_button_click(self, upload_tab, signal_catcher, qtbot):
        """process_requested emits when process button clicked."""
        upload_tab.process_requested.connect(signal_catcher.slot)
        upload_tab.processButton.setEnabled(True)

        qtbot.mouseClick(upload_tab.processButton, Qt.MouseButton.LeftButton)

        assert signal_catcher.was_called

    def test_signal_has_no_arguments(self, upload_tab, signal_catcher, qtbot):
        """process_requested signal has no arguments."""
        upload_tab.process_requested.connect(signal_catcher.slot)
        upload_tab.processButton.setEnabled(True)

        qtbot.mouseClick(upload_tab.processButton, Qt.MouseButton.LeftButton)

        # Args should be empty tuple
        assert signal_catcher.args == ()

    def test_signal_emitted_each_click(self, upload_tab, signal_catcher, qtbot):
        """process_requested emits for each click."""
        upload_tab.process_requested.connect(signal_catcher.slot)
        upload_tab.processButton.setEnabled(True)

        qtbot.mouseClick(upload_tab.processButton, Qt.MouseButton.LeftButton)
        qtbot.mouseClick(upload_tab.processButton, Qt.MouseButton.LeftButton)
        qtbot.mouseClick(upload_tab.processButton, Qt.MouseButton.LeftButton)

        assert signal_catcher.call_count == 3

    def test_using_waitSignal(self, upload_tab, qtbot):
        """Test using qtbot.waitSignal for process_requested."""
        upload_tab.processButton.setEnabled(True)

        with qtbot.waitSignal(upload_tab.process_requested, timeout=1000):
            qtbot.mouseClick(upload_tab.processButton, Qt.MouseButton.LeftButton)


class TestModeChangedSignal:
    """Test mode_changed signal emission."""

    def test_signal_emitted_on_mode_change(self, upload_tab, signal_catcher):
        """mode_changed emits when mode changes."""
        upload_tab.mode_changed.connect(signal_catcher.slot)

        upload_tab.on_mode_changed("MS Only")

        assert signal_catcher.was_called

    def test_signal_contains_new_mode(self, upload_tab, signal_catcher):
        """mode_changed signal includes new mode string."""
        upload_tab.mode_changed.connect(signal_catcher.slot)

        upload_tab.on_mode_changed("MS Only")

        assert signal_catcher.args[0] == "MS Only"

    def test_signal_not_emitted_for_same_mode(self, upload_tab, signal_catcher):
        """mode_changed not emitted when mode unchanged."""
        upload_tab.mode_changed.connect(signal_catcher.slot)

        # Current mode is LC/GC-MS, try to set it again
        upload_tab.on_mode_changed("LC/GC-MS")

        assert not signal_catcher.was_called

    def test_signal_emitted_for_each_change(self, upload_tab, signal_catcher):
        """mode_changed emits for each distinct mode change."""
        upload_tab.mode_changed.connect(signal_catcher.slot)

        upload_tab.on_mode_changed("MS Only")
        upload_tab.on_mode_changed("LC/GC Only")
        upload_tab.on_mode_changed("LC/GC-MS")

        assert signal_catcher.call_count == 3
        assert signal_catcher.all_args[0] == ("MS Only",)
        assert signal_catcher.all_args[1] == ("LC/GC Only",)
        assert signal_catcher.all_args[2] == ("LC/GC-MS",)

    def test_using_waitSignal(self, upload_tab, qtbot):
        """Test using qtbot.waitSignal for mode_changed."""
        with qtbot.waitSignal(upload_tab.mode_changed, timeout=1000) as blocker:
            upload_tab.on_mode_changed("MS Only")

        assert blocker.args == ["MS Only"]


class TestStatusMessageSignal:
    """Test status_message signal emission."""

    def test_signal_emitted_for_invalid_files(self, upload_tab, tmp_path, signal_catcher):
        """status_message emits when invalid files dropped."""
        invalid_file = tmp_path / "test.pdf"
        invalid_file.write_text("data")

        upload_tab.status_message.connect(signal_catcher.slot)
        upload_tab.handle_files_dropped([str(invalid_file)], "LC")

        assert signal_catcher.was_called

    def test_signal_contains_message(self, upload_tab, tmp_path, signal_catcher):
        """status_message signal includes message string."""
        invalid_file = tmp_path / "test.pdf"
        invalid_file.write_text("data")

        upload_tab.status_message.connect(signal_catcher.slot)
        upload_tab.handle_files_dropped([str(invalid_file)], "LC")

        message = signal_catcher.args[0]
        assert isinstance(message, str)
        assert "No valid files" in message

    def test_signal_contains_duration(self, upload_tab, tmp_path, signal_catcher):
        """status_message signal includes duration in ms."""
        invalid_file = tmp_path / "test.pdf"
        invalid_file.write_text("data")

        upload_tab.status_message.connect(signal_catcher.slot)
        upload_tab.handle_files_dropped([str(invalid_file)], "LC")

        duration = signal_catcher.args[1]
        assert isinstance(duration, int)
        assert duration > 0

    def test_signal_emitted_for_successful_add(self, upload_tab, sample_lc_file, signal_catcher):
        """status_message emits when files successfully added."""
        upload_tab.status_message.connect(signal_catcher.slot)
        upload_tab.handle_files_dropped([str(sample_lc_file)], "LC")

        assert signal_catcher.was_called
        message = signal_catcher.args[0]
        assert "Added" in message
        assert "1" in message  # Number of files


class TestMultipleSignalConnections:
    """Test behavior with multiple signal connections."""

    def test_multiple_handlers_all_called(self, upload_tab, sample_lc_file):
        """Multiple handlers connected to same signal all receive emission."""
        catcher1 = type('Catcher', (), {'called': False, 'slot': lambda self, *a: setattr(self, 'called', True)})()
        catcher2 = type('Catcher', (), {'called': False, 'slot': lambda self, *a: setattr(self, 'called', True)})()

        upload_tab.files_loaded.connect(catcher1.slot)
        upload_tab.files_loaded.connect(catcher2.slot)

        upload_tab.handle_files_dropped([str(sample_lc_file)], "LC")

        assert catcher1.called
        assert catcher2.called

    def test_disconnect_prevents_emission(self, upload_tab, sample_lc_file, signal_catcher):
        """Disconnected handlers don't receive emissions."""
        upload_tab.files_loaded.connect(signal_catcher.slot)
        upload_tab.files_loaded.disconnect(signal_catcher.slot)

        upload_tab.handle_files_dropped([str(sample_lc_file)], "LC")

        assert not signal_catcher.was_called
