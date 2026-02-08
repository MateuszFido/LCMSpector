"""
Unit tests for theoretical mass spectrum prediction.

Tests formula detection, isotopic pattern calculation, IonTable formula
branching, and MzRangeDialog theoretical overlay.
"""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from PySide6 import QtWidgets


# ===========================================================================
# TestDetectInputType
# ===========================================================================


class TestDetectInputType:
    """Tests for detect_input_type()."""

    def test_simple_formula(self):
        from utils.theoretical_spectrum import detect_input_type

        assert detect_input_type("C6H12O6") == "formula"

    def test_water(self):
        from utils.theoretical_spectrum import detect_input_type

        assert detect_input_type("H2O") == "formula"

    def test_carbon_monoxide(self):
        from utils.theoretical_spectrum import detect_input_type

        assert detect_input_type("CO") == "formula"

    def test_single_element(self):
        from utils.theoretical_spectrum import detect_input_type

        assert detect_input_type("C") == "formula"

    def test_salt(self):
        from utils.theoretical_spectrum import detect_input_type

        assert detect_input_type("NaCl") == "formula"

    def test_caffeine_formula(self):
        from utils.theoretical_spectrum import detect_input_type

        assert detect_input_type("C8H10N4O2") == "formula"

    def test_name_lowercase_start(self):
        from utils.theoretical_spectrum import detect_input_type

        assert detect_input_type("glucose") == "name"

    def test_name_caffeine(self):
        from utils.theoretical_spectrum import detect_input_type

        assert detect_input_type("caffeine") == "name"

    def test_name_aspirin(self):
        """'Aspirin' parses to {'Aspirin': 1} which is not in nist_mass."""
        from utils.theoretical_spectrum import detect_input_type

        assert detect_input_type("Aspirin") == "name"

    def test_name_with_spaces(self):
        from utils.theoretical_spectrum import detect_input_type

        assert detect_input_type("acetic acid") == "name"

    def test_empty_string(self):
        from utils.theoretical_spectrum import detect_input_type

        assert detect_input_type("") == "name"

    def test_whitespace_only(self):
        from utils.theoretical_spectrum import detect_input_type

        assert detect_input_type("   ") == "name"


# ===========================================================================
# TestCalculateTheoreticalSpectrum
# ===========================================================================


class TestCalculateTheoreticalSpectrum:
    """Tests for calculate_theoretical_spectrum()."""

    def test_glucose_has_both_adducts(self):
        from utils.theoretical_spectrum import calculate_theoretical_spectrum

        spec = calculate_theoretical_spectrum("C6H12O6")
        assert "[M+H]+" in spec.adducts
        assert "[M-H]-" in spec.adducts

    def test_caffeine_monoisotopic_mz(self):
        from utils.theoretical_spectrum import calculate_theoretical_spectrum

        spec = calculate_theoretical_spectrum("C8H10N4O2")
        pos = spec.adducts["[M+H]+"]
        # Caffeine exact mass ~194.0804, [M+H]+ = ~195.088
        assert pos.monoisotopic_mz == pytest.approx(195.088, abs=0.01)

    def test_abundances_normalized(self):
        from utils.theoretical_spectrum import calculate_theoretical_spectrum

        spec = calculate_theoretical_spectrum("C6H12O6")
        for adduct in spec.adducts.values():
            assert adduct.abundances.max() == pytest.approx(1.0)

    def test_mz_values_sorted(self):
        from utils.theoretical_spectrum import calculate_theoretical_spectrum

        spec = calculate_theoretical_spectrum("C6H12O6")
        for adduct in spec.adducts.values():
            assert np.all(np.diff(adduct.mz_values) >= 0)

    def test_invalid_formula_raises_valueerror(self):
        from utils.theoretical_spectrum import calculate_theoretical_spectrum

        with pytest.raises(ValueError):
            calculate_theoretical_spectrum("XyzNotAnElement123")

    def test_threshold_filtering(self):
        """Higher threshold should yield fewer isotopologue peaks."""
        from utils.theoretical_spectrum import calculate_theoretical_spectrum

        spec_low = calculate_theoretical_spectrum("C6H12O6", abundance_threshold=0.0001)
        spec_high = calculate_theoretical_spectrum("C6H12O6", abundance_threshold=0.01)

        pos_low = spec_low.adducts["[M+H]+"]
        pos_high = spec_high.adducts["[M+H]+"]
        assert len(pos_high.mz_values) <= len(pos_low.mz_values)

    def test_formula_stored(self):
        from utils.theoretical_spectrum import calculate_theoretical_spectrum

        spec = calculate_theoretical_spectrum("H2O")
        assert spec.formula == "H2O"


# ===========================================================================
# TestIonTableFormulaLookup
# ===========================================================================


class TestIonTableFormulaLookup:
    """Tests for IonTable formula detection and local lookup."""

    @pytest.fixture
    def ion_table_with_mock_view(self, qapp, qtbot):
        from ui.widgets import IonTable

        mock_view = MagicMock()
        mock_view.comboBoxIonLists = MagicMock()
        mock_view.statusbar = MagicMock()

        table = IonTable(view=mock_view, parent=None)
        qtbot.addWidget(table)
        yield table

    def test_formula_fills_cells_without_pubchem(self, ion_table_with_mock_view, qtbot):
        """Entering a formula fills m/z cells instantly, no PubChem call."""
        table = ion_table_with_mock_view

        with patch.object(table, "_execute_lookup_for") as mock_pubchem:
            table.setItem(0, 0, QtWidgets.QTableWidgetItem("C8H10N4O2"))
            table.setCurrentCell(0, 0)
            table._on_editor_closed(MagicMock(), 0)

            # PubChem should NOT be called
            mock_pubchem.assert_not_called()

        # m/z should be filled
        mz_item = table.item(0, 1)
        assert mz_item is not None
        assert mz_item.text().strip() != ""
        # Should contain [M+H]+ value
        assert "195.0882" in mz_item.text()

    def test_name_still_triggers_pubchem(self, ion_table_with_mock_view, qtbot):
        """Entering a compound name still triggers PubChem lookup."""
        table = ion_table_with_mock_view

        with patch.object(table, "_execute_lookup_for") as mock_pubchem:
            table.setItem(0, 0, QtWidgets.QTableWidgetItem("Caffeine"))
            table.setCurrentCell(0, 0)
            table._on_editor_closed(MagicMock(), 0)

            mock_pubchem.assert_called_once_with(0, "Caffeine")

    def test_theoretical_spectra_populated(self, ion_table_with_mock_view, qtbot):
        """Formula lookup populates _theoretical_spectra dict."""
        table = ion_table_with_mock_view

        table.setItem(0, 0, QtWidgets.QTableWidgetItem("C8H10N4O2"))
        table.setCurrentCell(0, 0)
        table._on_editor_closed(MagicMock(), 0)

        assert "C8H10N4O2" in table._theoretical_spectra
        spec = table._theoretical_spectra["C8H10N4O2"]
        assert "[M+H]+" in spec.adducts

    def test_theoretical_spectrum_signal_emitted(self, ion_table_with_mock_view, qtbot):
        """Formula lookup emits theoretical_spectrum_ready signal."""
        table = ion_table_with_mock_view

        from tests.conftest import SignalCatcher

        catcher = SignalCatcher()
        table.theoretical_spectrum_ready.connect(catcher.slot)

        table.setItem(0, 0, QtWidgets.QTableWidgetItem("C8H10N4O2"))
        table.setCurrentCell(0, 0)
        table._on_editor_closed(MagicMock(), 0)

        assert catcher.was_called
        name, spectrum = catcher.args
        assert name == "C8H10N4O2"
        assert "[M+H]+" in spectrum.adducts

    def test_pubchem_lookup_also_computes_theoretical(
        self, ion_table_with_mock_view, qtbot
    ):
        """PubChem lookup with molecular_formula triggers theoretical computation."""
        table = ion_table_with_mock_view

        from tests.conftest import SignalCatcher

        catcher = SignalCatcher()
        table.theoretical_spectrum_ready.connect(catcher.slot)

        table._lookup_row = 0
        table.setItem(0, 0, QtWidgets.QTableWidgetItem("Caffeine"))

        data = {
            "mz_pos": 195.0877,
            "mz_neg": 193.0731,
            "molecular_formula": "C8H10N4O2",
        }
        table._on_lookup_finished("Caffeine", data)

        assert "Caffeine" in table._theoretical_spectra
        assert catcher.was_called
        name, spectrum = catcher.args
        assert name == "Caffeine"


# ===========================================================================
# TestMzRangeDialogTheoretical
# ===========================================================================


class TestMzRangeDialogTheoretical:
    """Tests for MzRangeDialog theoretical spectrum overlay."""

    @pytest.fixture
    def sample_spectrum_data(self):
        """Provide sample m/z and intensity arrays for dialog."""
        mzs = np.linspace(190, 200, 100)
        intensities = np.random.RandomState(42).uniform(0, 1000, 100)
        # Add a peak at ~195
        intensities[50] = 10000
        return mzs, intensities

    def test_dialog_no_crash_without_theoretical(self, qapp, qtbot, sample_spectrum_data):
        """Dialog works normally when theoretical_spectrum is None."""
        from ui.widgets import MzRangeDialog

        mzs, intensities = sample_spectrum_data
        dialog = MzRangeDialog(
            mzs=mzs,
            intensities=intensities,
            target_mz_values=[195.0882],
            ion_labels=["[M+H]+"],
            mass_accuracy=0.0001,
            compound_name="Test",
            theoretical_spectrum=None,
        )
        qtbot.addWidget(dialog)
        # Should not crash; no theoretical items
        assert dialog._theo_items == []

    def test_dialog_displays_theoretical_peaks(self, qapp, qtbot, sample_spectrum_data):
        """Dialog displays theoretical bar items when spectrum is provided."""
        from ui.widgets import MzRangeDialog
        from utils.theoretical_spectrum import calculate_theoretical_spectrum

        mzs, intensities = sample_spectrum_data
        spectrum = calculate_theoretical_spectrum("C8H10N4O2")

        dialog = MzRangeDialog(
            mzs=mzs,
            intensities=intensities,
            target_mz_values=[195.0882, 193.0726],
            ion_labels=["[M+H]+", "[M-H]-"],
            mass_accuracy=0.0001,
            compound_name="Caffeine",
            theoretical_spectrum=spectrum,
        )
        qtbot.addWidget(dialog)

        # Should have theoretical items (bar + text label)
        assert len(dialog._theo_items) >= 2

    def test_theoretical_items_cleaned_on_ion_switch(
        self, qapp, qtbot, sample_spectrum_data
    ):
        """Theoretical items are cleaned up when switching ions."""
        from ui.widgets import MzRangeDialog
        from utils.theoretical_spectrum import calculate_theoretical_spectrum

        mzs, intensities = sample_spectrum_data
        spectrum = calculate_theoretical_spectrum("C8H10N4O2")

        dialog = MzRangeDialog(
            mzs=mzs,
            intensities=intensities,
            target_mz_values=[195.0882, 193.0726],
            ion_labels=["[M+H]+", "[M-H]-"],
            mass_accuracy=0.0001,
            compound_name="Caffeine",
            theoretical_spectrum=spectrum,
        )
        qtbot.addWidget(dialog)

        # Items from first ion
        items_ion0 = list(dialog._theo_items)
        assert len(items_ion0) >= 2

        # Switch to second ion
        dialog._ion_combo.setCurrentIndex(1)

        # Previous items should be cleaned, new ones created
        # (items list should have been cleared and repopulated)
        assert len(dialog._theo_items) >= 2
        # Items should be different objects (old ones removed)
        assert dialog._theo_items[0] is not items_ion0[0]
