"""
Unit tests for AdductDropdown widget and IonTable adduct integration.

Tests widget state management, signal emission, IonTable integration
with active adducts, and adduct selection persistence.
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from PySide6 import QtWidgets


# ===========================================================================
# TestAdductDropdownWidget
# ===========================================================================


class TestAdductDropdownWidget:
    """Tests for the AdductDropdown widget itself."""

    @pytest.fixture
    def dropdown(self, qapp, qtbot):
        from ui.widgets import AdductDropdown

        dd = AdductDropdown(parent=None)
        qtbot.addWidget(dd)
        return dd

    def test_default_checked_state(self, dropdown):
        """Default state has [M+H]+ and [M-H]- checked."""
        checked = dropdown.checked_adducts()
        assert "[M+H]+" in checked
        assert "[M-H]-" in checked
        assert len(checked) == 2

    def test_checked_adducts_returns_list(self, dropdown):
        """checked_adducts() returns a list of strings."""
        result = dropdown.checked_adducts()
        assert isinstance(result, list)
        assert all(isinstance(a, str) for a in result)

    def test_set_checked(self, dropdown):
        """set_checked() updates the checked state."""
        dropdown.set_checked(["[M+Na]+", "[M+K]+"])
        checked = dropdown.checked_adducts()
        assert "[M+Na]+" in checked
        assert "[M+K]+" in checked
        assert "[M+H]+" not in checked
        assert "[M-H]-" not in checked

    def test_set_checked_blocks_signals(self, dropdown, qtbot):
        """set_checked() does not emit adducts_changed."""
        from tests.conftest import SignalCatcher

        catcher = SignalCatcher()
        dropdown.adducts_changed.connect(catcher.slot)

        dropdown.set_checked(["[M+Na]+"])
        assert not catcher.was_called

    def test_signal_emitted_on_action_toggle(self, dropdown, qtbot):
        """Toggling an action emits adducts_changed."""
        from tests.conftest import SignalCatcher

        catcher = SignalCatcher()
        dropdown.adducts_changed.connect(catcher.slot)

        # Toggle [M+Na]+ on
        dropdown._actions["[M+Na]+"].trigger()

        assert catcher.was_called
        adduct_list = catcher.args[0]
        assert "[M+Na]+" in adduct_list

    def test_all_adducts_represented(self, dropdown):
        """All 13 adducts appear in the menu actions."""
        assert len(dropdown._actions) == 13

    def test_set_checked_empty_unchecks_all(self, dropdown):
        """set_checked([]) unchecks all adducts."""
        dropdown.set_checked([])
        assert dropdown.checked_adducts() == []

    def test_set_checked_all(self, dropdown):
        """set_checked with all labels checks everything."""
        all_labels = list(dropdown._actions.keys())
        dropdown.set_checked(all_labels)
        assert set(dropdown.checked_adducts()) == set(all_labels)


# ===========================================================================
# TestIonTableAdductIntegration
# ===========================================================================


class TestIonTableAdductIntegration:
    """Tests for IonTable integration with AdductDropdown."""

    @pytest.fixture
    def table_with_dropdown(self, qapp, qtbot):
        from ui.widgets import IonTable, AdductDropdown

        mock_view = MagicMock()
        mock_view.comboBoxIonLists = MagicMock()
        mock_view.statusbar = MagicMock()

        table = IonTable(view=mock_view, parent=None)
        dropdown = AdductDropdown(parent=None)
        table.set_adduct_dropdown(dropdown)
        qtbot.addWidget(table)
        qtbot.addWidget(dropdown)
        return table, dropdown

    def test_get_active_adducts_default(self, qapp, qtbot):
        """Without dropdown, returns DEFAULT_ADDUCTS."""
        from ui.widgets import IonTable
        from utils.theoretical_spectrum import DEFAULT_ADDUCTS

        mock_view = MagicMock()
        mock_view.comboBoxIonLists = MagicMock()
        mock_view.statusbar = MagicMock()

        table = IonTable(view=mock_view, parent=None)
        qtbot.addWidget(table)
        assert table._get_active_adducts() == DEFAULT_ADDUCTS

    def test_get_active_adducts_from_dropdown(self, table_with_dropdown):
        """With dropdown, returns dropdown's checked adducts."""
        table, dropdown = table_with_dropdown
        dropdown.set_checked(["[M+Na]+", "[M+Cl]-"])
        assert table._get_active_adducts() == ["[M+Na]+", "[M+Cl]-"]

    def test_formula_lookup_uses_active_adducts(self, table_with_dropdown, qtbot):
        """Formula lookup uses dropdown adducts, not hardcoded defaults."""
        table, dropdown = table_with_dropdown
        dropdown.set_checked(["[M+H]+", "[M+Na]+"])

        table.setItem(0, 0, QtWidgets.QTableWidgetItem("C8H10N4O2"))
        table.setCurrentCell(0, 0)
        table._on_editor_closed(MagicMock(), 0)

        # m/z should have two values
        mz_item = table.item(0, 1)
        assert mz_item is not None
        mz_values = [x.strip() for x in mz_item.text().split(",")]
        assert len(mz_values) == 2

        # Info should have [M+H]+ and [M+Na]+
        info_item = table.item(0, 2)
        assert "[M+H]+" in info_item.text()
        assert "[M+Na]+" in info_item.text()

    def test_adducts_changed_recomputes_mz(self, table_with_dropdown, qtbot):
        """Changing adducts via dropdown updates m/z values for existing formulas."""
        table, dropdown = table_with_dropdown

        # First: enter formula with defaults
        table.setItem(0, 0, QtWidgets.QTableWidgetItem("C8H10N4O2"))
        table.setCurrentCell(0, 0)
        table._on_editor_closed(MagicMock(), 0)

        # Verify defaults
        mz_text_before = table.item(0, 1).text()
        assert "195.0882" in mz_text_before

        # Now add [M+Na]+ via dropdown
        dropdown.set_checked(["[M+H]+", "[M-H]-", "[M+Na]+"])
        # Manually trigger since set_checked blocks signals
        table._on_adducts_changed(["[M+H]+", "[M-H]-", "[M+Na]+"])

        mz_text_after = table.item(0, 1).text()
        # Should now contain 3 values
        mz_values = [x.strip() for x in mz_text_after.split(",")]
        assert len(mz_values) == 3

        info_text = table.item(0, 2).text()
        assert "[M+Na]+" in info_text

    def test_adducts_changed_emits_theoretical_spectrum(self, table_with_dropdown, qtbot):
        """Changing adducts emits theoretical_spectrum_ready for each formula compound."""
        table, dropdown = table_with_dropdown

        from tests.conftest import SignalCatcher

        # First: enter formula with defaults
        table.setItem(0, 0, QtWidgets.QTableWidgetItem("C8H10N4O2"))
        table.setCurrentCell(0, 0)
        table._on_editor_closed(MagicMock(), 0)

        # Now listen for signal
        catcher = SignalCatcher()
        table.theoretical_spectrum_ready.connect(catcher.slot)

        # Trigger adduct change
        table._on_adducts_changed(["[M+H]+", "[M+Na]+"])

        assert catcher.was_called
        name, spectrum = catcher.args
        assert name == "C8H10N4O2"
        assert "[M+H]+" in spectrum.adducts
        assert "[M+Na]+" in spectrum.adducts

    def test_find_row_by_name(self, table_with_dropdown):
        """_find_row_by_name returns correct row index."""
        table, _ = table_with_dropdown
        table.setItem(0, 0, QtWidgets.QTableWidgetItem("CompA"))
        table.setItem(1, 0, QtWidgets.QTableWidgetItem("CompB"))

        assert table._find_row_by_name("CompA") == 0
        assert table._find_row_by_name("CompB") == 1
        assert table._find_row_by_name("NotHere") == -1

    def test_pubchem_lookup_uses_active_adducts(self, table_with_dropdown, qtbot):
        """PubChem result with molecular_formula uses active adducts."""
        table, dropdown = table_with_dropdown
        dropdown.set_checked(["[M+H]+", "[M+Na]+"])

        table._lookup_row = 0
        table.setItem(0, 0, QtWidgets.QTableWidgetItem("Caffeine"))

        data = {
            "mz_pos": 195.0877,
            "mz_neg": 193.0731,
            "molecular_formula": "C8H10N4O2",
        }
        table._on_lookup_finished("Caffeine", data)

        info_text = table.item(0, 2).text()
        assert "[M+H]+" in info_text
        assert "[M+Na]+" in info_text
        # Should NOT have [M-H]- since it's not checked
        assert "[M-H]-" not in info_text


# ===========================================================================
# TestAdductPersistence
# ===========================================================================


class TestAdductPersistence:
    """Tests for adduct selection persistence via config.json."""

    @pytest.fixture
    def config_with_adducts(self, tmp_path):
        """Config with _adducts metadata key."""
        config = {
            "Custom Adducts": {
                "_adducts": ["[M+H]+", "[M+Na]+", "[M+Cl]-"],
                "Caffeine": {
                    "ions": [195.0882, 217.0695, 229.052],
                    "info": ["[M+H]+", "[M+Na]+", "[M+Cl]-"],
                    "formula": "C8H10N4O2",
                },
            },
            "Legacy List": {
                "Caffeine": {
                    "ions": [195.0882, 193.0726],
                    "info": ["[M+H]+", "[M-H]-"],
                    "formula": "C8H10N4O2",
                },
            },
        }
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config, indent=2))
        return config_path

    @pytest.fixture
    def tab_with_adducts(self, qapp, qtbot, config_with_adducts):
        from ui.tabs.upload_tab import UploadTab

        tab = UploadTab(parent=None, mode="MS Only")
        tab.config_path = config_with_adducts
        qtbot.addWidget(tab)

        tab.comboBoxIonLists.clear()
        tab.comboBoxIonLists.addItem("Create new ion list...")
        tab._load_ion_config_names()
        return tab

    def test_load_restores_adduct_selection(self, tab_with_adducts):
        """Loading a config with _adducts restores dropdown selection."""
        tab = tab_with_adducts
        idx = tab.comboBoxIonLists.findText("Custom Adducts")
        tab.comboBoxIonLists.setCurrentIndex(idx)

        checked = tab.adduct_dropdown.checked_adducts()
        assert "[M+H]+" in checked
        assert "[M+Na]+" in checked
        assert "[M+Cl]-" in checked
        assert "[M-H]-" not in checked

    def test_load_legacy_uses_defaults(self, tab_with_adducts):
        """Loading a config without _adducts keeps default selection."""
        tab = tab_with_adducts
        idx = tab.comboBoxIonLists.findText("Legacy List")
        tab.comboBoxIonLists.setCurrentIndex(idx)

        # Dropdown should keep its current state (defaults)
        checked = tab.adduct_dropdown.checked_adducts()
        # Should have whatever was set before (at minimum the defaults)
        assert "[M+H]+" in checked
        assert "[M-H]-" in checked

    def test_adducts_key_not_rendered_as_compound(self, tab_with_adducts):
        """_adducts metadata key should not appear as a table row."""
        tab = tab_with_adducts
        idx = tab.comboBoxIonLists.findText("Custom Adducts")
        tab.comboBoxIonLists.setCurrentIndex(idx)

        # Should have only 1 row (Caffeine), not 2
        assert tab.ionTable.rowCount() == 1
        name_item = tab.ionTable.item(0, 0)
        assert name_item.text() == "Caffeine"
