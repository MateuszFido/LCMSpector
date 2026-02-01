"""
Unit tests for PubChem compound lookup functionality.

Tests the PubChemLookupWorker and IonTable integration with mocked API responses.
"""
import pytest
from unittest.mock import MagicMock, patch
from PySide6 import QtWidgets


class TestPubChemLookupWorker:
    """Tests for the PubChemLookupWorker class."""

    def test_worker_emits_finished_on_success(self, qtbot):
        """Worker emits finished signal with correct data on successful lookup."""
        from utils.pubchem import PubChemLookupWorker, PROTON_MASS

        worker = PubChemLookupWorker("Caffeine")

        # Mock PubChem response
        mock_response = [
            {
                "IUPACName": "1,3,7-trimethylpurine-2,6-dione",
                "ExactMass": "194.0804",
            }
        ]

        with patch("pubchempy.get_properties", return_value=mock_response):
            # Catch the finished signal
            with qtbot.waitSignal(worker.finished, timeout=5000) as blocker:
                worker.run()

            compound_name, data = blocker.args
            assert compound_name == "Caffeine"
            assert data["exact_mass"] == 194.0804
            assert data["mz_pos"] == round(194.0804 + PROTON_MASS, 4)
            assert data["mz_neg"] == round(194.0804 - PROTON_MASS, 4)
            assert data["iupac_name"] == "1,3,7-trimethylpurine-2,6-dione"

    def test_worker_emits_error_when_compound_not_found(self, qtbot):
        """Worker emits error signal when compound is not found."""
        from utils.pubchem import PubChemLookupWorker

        worker = PubChemLookupWorker("NonExistentCompound12345")

        with patch("pubchempy.get_properties", return_value=[]):
            with qtbot.waitSignal(worker.error, timeout=5000) as blocker:
                worker.run()

            compound_name, error_msg = blocker.args
            assert compound_name == "NonExistentCompound12345"
            assert "not found" in error_msg.lower()

    def test_worker_emits_error_on_network_failure(self, qtbot):
        """Worker emits error signal on network failures."""
        from utils.pubchem import PubChemLookupWorker

        worker = PubChemLookupWorker("Caffeine")

        with patch(
            "pubchempy.get_properties",
            side_effect=ConnectionError("Network unreachable"),
        ):
            with qtbot.waitSignal(worker.error, timeout=5000) as blocker:
                worker.run()

            compound_name, error_msg = blocker.args
            assert compound_name == "Caffeine"
            assert "network" in error_msg.lower()

    def test_worker_emits_error_when_no_exact_mass(self, qtbot):
        """Worker emits error when compound has no exact mass."""
        from utils.pubchem import PubChemLookupWorker

        worker = PubChemLookupWorker("SomeCompound")

        mock_response = [
            {
                "IUPACName": "some-name",
                # No ExactMass field
            }
        ]

        with patch("pubchempy.get_properties", return_value=mock_response):
            with qtbot.waitSignal(worker.error, timeout=5000) as blocker:
                worker.run()

            compound_name, error_msg = blocker.args
            assert compound_name == "SomeCompound"
            assert "mass" in error_msg.lower()


class TestProtonMass:
    """Tests for the proton mass constant."""

    def test_proton_mass_value(self):
        """Proton mass constant has correct value."""
        from utils.pubchem import PROTON_MASS

        # Proton mass should be approximately 1.007276 Da
        assert PROTON_MASS == pytest.approx(1.007276, rel=1e-5)


class TestIonTableLookupIntegration:
    """Integration tests for IonTable PubChem lookup."""

    @pytest.fixture
    def ion_table_with_mock_view(self, qapp, qtbot):
        """Create an IonTable with a mock view."""
        from ui.widgets import IonTable

        mock_view = MagicMock()
        mock_view.comboBoxIonLists = MagicMock()
        mock_view.statusbar = MagicMock()

        table = IonTable(view=mock_view, parent=None)
        qtbot.addWidget(table)
        yield table

    def test_lookup_triggered_on_editor_close(
        self, ion_table_with_mock_view, qtbot
    ):
        """Lookup is triggered when editor is closed (not on every keystroke)."""
        table = ion_table_with_mock_view

        # Mock the lookup execution
        with patch.object(table, "_execute_lookup_for") as mock_execute:
            # Set up a cell with compound name (simulating pre-edit state)
            table.setItem(0, 0, QtWidgets.QTableWidgetItem("Caffeine"))

            # Simulate closeEditor signal (as if user finished editing)
            # First, select the cell so currentRow/currentColumn return correct values
            table.setCurrentCell(0, 0)

            # Trigger closeEditor with a mock editor
            mock_editor = MagicMock()
            table._on_editor_closed(mock_editor, 0)

            # Verify lookup was executed
            mock_execute.assert_called_once_with(0, "Caffeine")

    def test_lookup_not_triggered_when_mz_has_value(
        self, ion_table_with_mock_view, qtbot
    ):
        """Lookup is not triggered if m/z column already has a value."""
        table = ion_table_with_mock_view

        # Pre-fill m/z column
        table.setItem(0, 1, QtWidgets.QTableWidgetItem("195.0877"))
        # Set compound name
        table.setItem(0, 0, QtWidgets.QTableWidgetItem("Caffeine"))

        with patch.object(table, "_execute_lookup_for") as mock_execute:
            # Simulate closeEditor on compound column
            table.setCurrentCell(0, 0)
            mock_editor = MagicMock()
            table._on_editor_closed(mock_editor, 0)

            # Lookup should not be executed since m/z is filled
            mock_execute.assert_not_called()

    def test_lookup_not_triggered_for_non_compound_columns(
        self, ion_table_with_mock_view, qtbot
    ):
        """Lookup is not triggered for edits in m/z or info columns."""
        table = ion_table_with_mock_view

        with patch.object(table, "_execute_lookup_for") as mock_execute:
            # Simulate closeEditor on m/z column
            table.setItem(0, 1, QtWidgets.QTableWidgetItem("195.0877"))
            table.setCurrentCell(0, 1)
            mock_editor = MagicMock()
            table._on_editor_closed(mock_editor, 0)

            # Simulate closeEditor on info column
            table.setItem(0, 2, QtWidgets.QTableWidgetItem("[M+H]+"))
            table.setCurrentCell(0, 2)
            table._on_editor_closed(mock_editor, 0)

            # Lookup should not be executed for non-compound columns
            mock_execute.assert_not_called()

    def test_lookup_fills_mz_and_info_columns_with_highlight(
        self, ion_table_with_mock_view, qtbot
    ):
        """Successful lookup fills m/z and info columns with green highlight."""
        from PySide6.QtGui import QColor

        table = ion_table_with_mock_view

        # Simulate receiving lookup results
        table._lookup_row = 0
        table.setItem(0, 0, QtWidgets.QTableWidgetItem("Caffeine"))

        # Call the callback directly
        data = {
            "exact_mass": 194.0804,
            "mz_pos": 195.0877,
            "mz_neg": 193.0731,
            "iupac_name": "1,3,7-trimethylpurine-2,6-dione",
        }
        table._on_lookup_finished("Caffeine", data)

        # Verify cells were filled
        mz_item = table.item(0, 1)
        assert mz_item is not None
        assert "195.0877" in mz_item.text()
        assert "193.0731" in mz_item.text()

        info_item = table.item(0, 2)
        assert info_item is not None
        assert "[M+H]+" in info_item.text()
        assert "[M-H]-" in info_item.text()

        # Verify green highlight was applied
        highlight_color = QColor(200, 255, 200)
        assert mz_item.background().color() == highlight_color
        assert info_item.background().color() == highlight_color

    def test_lookup_status_signal_emitted(
        self, ion_table_with_mock_view, qtbot
    ):
        """lookup_status signal is emitted during lookup process."""
        table = ion_table_with_mock_view

        # Catch the status signal
        from tests.conftest import SignalCatcher

        catcher = SignalCatcher()
        table.lookup_status.connect(catcher.slot)

        # Trigger error callback for not found
        table._on_lookup_error("UnknownCompound", "Compound not found")

        assert catcher.was_called
        message, duration = catcher.args
        # Check for descriptive message format
        assert "UnknownCompound" in message
        assert "not found" in message.lower()

    def test_lookup_success_status_message_format(
        self, ion_table_with_mock_view, qtbot
    ):
        """Success status message includes compound name and m/z value."""
        table = ion_table_with_mock_view

        from tests.conftest import SignalCatcher

        catcher = SignalCatcher()
        table.lookup_status.connect(catcher.slot)

        # Set up lookup row
        table._lookup_row = 0
        table.setItem(0, 0, QtWidgets.QTableWidgetItem("Caffeine"))

        # Trigger success callback
        data = {
            "mz_pos": 195.0877,
            "mz_neg": 193.0731,
        }
        table._on_lookup_finished("Caffeine", data)

        assert catcher.was_called
        message, duration = catcher.args
        assert "PubChem lookup successful" in message
        assert "Caffeine" in message
        assert "195.0877" in message

    def test_cleanup_stops_running_lookup(
        self, ion_table_with_mock_view, qtbot
    ):
        """Cleanup properly stops a running lookup thread."""
        table = ion_table_with_mock_view

        # Create mock thread and worker
        from PySide6.QtCore import QThread

        mock_thread = MagicMock(spec=QThread)
        mock_worker = MagicMock()

        table._lookup_thread = mock_thread
        table._lookup_worker = mock_worker

        # Call cleanup
        table._cleanup_lookup()

        # Verify thread was stopped
        mock_thread.quit.assert_called_once()
        mock_thread.wait.assert_called_once()
        mock_thread.deleteLater.assert_called_once()

        # Verify references cleared
        assert table._lookup_thread is None
        assert table._lookup_worker is None


class TestUploadTabLookupStatus:
    """Tests for UploadTab handling of lookup status messages."""

    def test_lookup_status_forwarded_to_statusbar(
        self, upload_tab, qtbot
    ):
        """Lookup status messages are forwarded to the status bar."""
        # Create a mock statusbar
        mock_statusbar = MagicMock()

        # Create a mock parent window with statusbar
        mock_window = MagicMock()
        mock_window.statusbar = mock_statusbar

        with patch.object(upload_tab, "window", return_value=mock_window):
            # Trigger a status message through the ion table
            upload_tab.ionTable.lookup_status.emit("Test message", 5000)

            # Verify statusbar received the message
            mock_statusbar.showMessage.assert_called_with("Test message", 5000)


class TestIonListSwitchingNoLookup:
    """Tests that ion list switching doesn't trigger PubChem lookups."""

    def test_ion_list_switch_does_not_trigger_lookup(self, upload_tab, qtbot, tmp_path):
        """Switching ion lists via combobox should not trigger PubChem lookups."""
        import json

        # Create a test config file
        config_data = {
            "TestList": {
                "Caffeine": {"ions": [195.0877], "info": ["[M+H]+"]},
                "Glucose": {"ions": [181.0707], "info": ["[M+H]+"]},
            }
        }
        config_path = tmp_path / "config.json"
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        # Point upload_tab to test config
        upload_tab.config_path = config_path

        # Add the test list to combobox
        upload_tab.comboBoxIonLists.addItem("TestList")

        # Mock the lookup execution
        with patch.object(upload_tab.ionTable, "_execute_lookup_for") as mock_execute:
            # Switch to the test ion list (triggers update_ion_list)
            upload_tab.comboBoxIonLists.setCurrentText("TestList")

            # Process events to allow signals to propagate
            qtbot.wait(100)

            # Lookup should NOT be triggered (signals are blocked during update)
            mock_execute.assert_not_called()

        # Verify the table was populated correctly
        assert upload_tab.ionTable.item(0, 0).text() == "Caffeine"
        assert upload_tab.ionTable.item(0, 1).text() == "195.0877"
