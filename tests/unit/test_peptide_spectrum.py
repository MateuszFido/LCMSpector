"""
Unit tests for peptide sequence support.

Tests input detection, precursor/fragment calculation, IonTable integration,
config persistence, and plotting dispatch.
"""

import json
import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from PySide6 import QtWidgets


# ===========================================================================
# TestIsValidPeptide
# ===========================================================================


class TestIsValidPeptide:
    """Tests for is_valid_peptide()."""

    def test_valid_peptide(self):
        from utils.theoretical_spectrum import is_valid_peptide

        assert is_valid_peptide("PEPTIDE") is True

    def test_valid_long_peptide(self):
        from utils.theoretical_spectrum import is_valid_peptide

        assert is_valid_peptide("MVLSPADKTNVK") is True

    def test_single_char_rejected(self):
        from utils.theoretical_spectrum import is_valid_peptide

        assert is_valid_peptide("A") is False

    def test_two_char_valid(self):
        from utils.theoretical_spectrum import is_valid_peptide

        assert is_valid_peptide("AA") is True

    def test_lowercase_rejected(self):
        from utils.theoretical_spectrum import is_valid_peptide

        assert is_valid_peptide("peptide") is False

    def test_numbers_rejected(self):
        from utils.theoretical_spectrum import is_valid_peptide

        assert is_valid_peptide("PEPTIDE2") is False

    def test_non_aa_letters_rejected(self):
        """Letters not in the standard 20 AA set should be rejected."""
        from utils.theoretical_spectrum import is_valid_peptide

        # B, J, O, U, X, Z are not standard amino acids
        assert is_valid_peptide("PEPTIDEB") is False
        assert is_valid_peptide("JK") is False

    def test_empty_rejected(self):
        from utils.theoretical_spectrum import is_valid_peptide

        assert is_valid_peptide("") is False


# ===========================================================================
# TestDetectInputTypePeptide
# ===========================================================================


class TestDetectInputTypePeptide:
    """Tests that detect_input_type correctly classifies peptide sequences."""

    def test_peptide_detected(self):
        from utils.theoretical_spectrum import detect_input_type

        assert detect_input_type("PEPTIDE") == "peptide"

    def test_long_peptide_detected(self):
        from utils.theoretical_spectrum import detect_input_type

        assert detect_input_type("MVLSPADKTNVK") == "peptide"

    def test_formula_takes_priority(self):
        """Strings that parse as valid formulas should remain 'formula'."""
        from utils.theoretical_spectrum import detect_input_type

        # CO, CH, etc. are valid formulas even though they contain AA letters
        assert detect_input_type("CO") == "formula"
        assert detect_input_type("CH") == "formula"

    def test_formula_still_works(self):
        from utils.theoretical_spectrum import detect_input_type

        assert detect_input_type("C8H10N4O2") == "formula"

    def test_name_still_works(self):
        from utils.theoretical_spectrum import detect_input_type

        assert detect_input_type("Caffeine") == "name"
        assert detect_input_type("caffeine") == "name"

    def test_single_aa_is_name(self):
        """Single amino acid letter should be 'name' (too short for peptide),
        unless it parses as a formula."""
        from utils.theoretical_spectrum import detect_input_type

        # 'C' is a valid formula (carbon)
        assert detect_input_type("C") == "formula"
        # 'A' doesn't parse as a formula, but is too short for peptide
        # It may parse as a formula or be classified as name depending on pyteomics
        result = detect_input_type("A")
        assert result in ("formula", "name")  # Not "peptide"

    def test_whitespace_peptide_is_name(self):
        from utils.theoretical_spectrum import detect_input_type

        assert detect_input_type("PEPTIDE CHAIN") == "name"


# ===========================================================================
# TestCalculatePeptidePrecursorMz
# ===========================================================================


class TestCalculatePeptidePrecursorMz:
    """Tests for calculate_peptide_precursor_mz()."""

    def test_peptide_mh_plus(self):
        """PEPTIDE [M+H]+ should be approximately 800.37."""
        from utils.theoretical_spectrum import calculate_peptide_precursor_mz

        result = calculate_peptide_precursor_mz("PEPTIDE", ["[M+H]+"])
        assert "[M+H]+" in result
        assert result["[M+H]+"] == pytest.approx(800.3678, abs=0.01)

    def test_peptide_mh_minus(self):
        """PEPTIDE [M-H]- should be approximately 798.35."""
        from utils.theoretical_spectrum import calculate_peptide_precursor_mz

        result = calculate_peptide_precursor_mz("PEPTIDE", ["[M-H]-"])
        assert "[M-H]-" in result
        assert result["[M-H]-"] == pytest.approx(798.3521, abs=0.01)

    def test_multiple_adducts(self):
        from utils.theoretical_spectrum import calculate_peptide_precursor_mz

        result = calculate_peptide_precursor_mz(
            "PEPTIDE", ["[M+H]+", "[M-H]-", "[M+2H]2+"]
        )
        assert len(result) == 3
        # [M+2H]2+ should be roughly half of [M+H]+
        assert result["[M+2H]2+"] == pytest.approx(400.688, abs=0.01)

    def test_default_adducts(self):
        from utils.theoretical_spectrum import calculate_peptide_precursor_mz

        result = calculate_peptide_precursor_mz("PEPTIDE")
        assert "[M+H]+" in result
        assert "[M-H]-" in result

    def test_unknown_adduct_skipped(self):
        from utils.theoretical_spectrum import calculate_peptide_precursor_mz

        result = calculate_peptide_precursor_mz("PEPTIDE", ["[M+H]+", "[FAKE]+"])
        assert len(result) == 1


# ===========================================================================
# TestCalculatePeptideFragments
# ===========================================================================


class TestCalculatePeptideFragments:
    """Tests for calculate_peptide_fragments()."""

    def test_fragment_count(self):
        """PEPTIDE (7 residues) should produce 6 b ions and 6 y ions."""
        from utils.theoretical_spectrum import calculate_peptide_fragments

        spec = calculate_peptide_fragments("PEPTIDE", ["[M+H]+"])
        b_ions = [f for f in spec.fragments if f.ion_type == "b"]
        y_ions = [f for f in spec.fragments if f.ion_type == "y"]
        assert len(b_ions) == 6
        assert len(y_ions) == 6

    def test_b1_mz(self):
        """b1 ion of PEPTIDE (P only) should have specific m/z."""
        from utils.theoretical_spectrum import calculate_peptide_fragments

        spec = calculate_peptide_fragments("PEPTIDE", ["[M+H]+"])
        b1 = [f for f in spec.fragments if f.label == "b1"][0]
        assert b1.mz == pytest.approx(98.06, abs=0.01)

    def test_y1_mz(self):
        """y1 ion of PEPTIDE (E only) should have specific m/z."""
        from utils.theoretical_spectrum import calculate_peptide_fragments

        spec = calculate_peptide_fragments("PEPTIDE", ["[M+H]+"])
        y1 = [f for f in spec.fragments if f.label == "y1"][0]
        assert y1.mz == pytest.approx(148.06, abs=0.01)

    def test_fragment_labels(self):
        """All fragments should have proper labels (b1-b6, y1-y6)."""
        from utils.theoretical_spectrum import calculate_peptide_fragments

        spec = calculate_peptide_fragments("PEPTIDE", ["[M+H]+"])
        b_labels = sorted([f.label for f in spec.fragments if f.ion_type == "b"])
        y_labels = sorted([f.label for f in spec.fragments if f.ion_type == "y"])
        assert b_labels == ["b1", "b2", "b3", "b4", "b5", "b6"]
        assert y_labels == ["y1", "y2", "y3", "y4", "y5", "y6"]

    def test_precursor_isotopes_present(self):
        from utils.theoretical_spectrum import calculate_peptide_fragments

        spec = calculate_peptide_fragments("PEPTIDE", ["[M+H]+"])
        assert "[M+H]+" in spec.precursor_isotopes
        iso = spec.precursor_isotopes["[M+H]+"]
        assert len(iso.mz_values) > 1
        assert iso.abundances.max() == pytest.approx(1.0)
        assert iso.monoisotopic_mz == pytest.approx(800.3678, abs=0.01)

    def test_sequence_stored(self):
        from utils.theoretical_spectrum import calculate_peptide_fragments

        spec = calculate_peptide_fragments("PEPTIDE", ["[M+H]+"])
        assert spec.sequence == "PEPTIDE"

    def test_invalid_sequence_raises(self):
        from utils.theoretical_spectrum import calculate_peptide_fragments

        with pytest.raises(ValueError):
            calculate_peptide_fragments("X", ["[M+H]+"])

    def test_short_peptide(self):
        """Two-residue peptide should produce 1 b ion and 1 y ion."""
        from utils.theoretical_spectrum import calculate_peptide_fragments

        spec = calculate_peptide_fragments("GK", ["[M+H]+"])
        b_ions = [f for f in spec.fragments if f.ion_type == "b"]
        y_ions = [f for f in spec.fragments if f.ion_type == "y"]
        assert len(b_ions) == 1
        assert len(y_ions) == 1


# ===========================================================================
# TestIonTablePeptideLookup
# ===========================================================================


class TestIonTablePeptideLookup:
    """Tests for IonTable peptide detection and local lookup."""

    @pytest.fixture
    def ion_table_with_mock_view(self, qapp, qtbot):
        from ui.widgets import IonTable

        mock_view = MagicMock()
        mock_view.comboBoxIonLists = MagicMock()
        mock_view.statusbar = MagicMock()

        table = IonTable(view=mock_view, parent=None)
        qtbot.addWidget(table)
        yield table

    def test_peptide_fills_cells(self, ion_table_with_mock_view, qtbot):
        """Entering a peptide fills m/z cells instantly, no PubChem call."""
        table = ion_table_with_mock_view

        with patch.object(table, "_execute_lookup_for") as mock_pubchem:
            table.setItem(0, 0, QtWidgets.QTableWidgetItem("PEPTIDE"))
            table.setCurrentCell(0, 0)
            table._on_editor_closed(MagicMock(), 0)

            mock_pubchem.assert_not_called()

        mz_item = table.item(0, 1)
        assert mz_item is not None
        assert mz_item.text().strip() != ""
        assert "800.3678" in mz_item.text()

    def test_peptide_does_not_trigger_formula(self, ion_table_with_mock_view, qtbot):
        """Entering a peptide should not call formula lookup."""
        table = ion_table_with_mock_view

        with patch.object(table, "_execute_formula_lookup") as mock_formula:
            table.setItem(0, 0, QtWidgets.QTableWidgetItem("PEPTIDE"))
            table.setCurrentCell(0, 0)
            table._on_editor_closed(MagicMock(), 0)

            mock_formula.assert_not_called()

    def test_theoretical_spectra_populated(self, ion_table_with_mock_view, qtbot):
        """Peptide lookup populates _theoretical_spectra dict."""
        table = ion_table_with_mock_view

        table.setItem(0, 0, QtWidgets.QTableWidgetItem("PEPTIDE"))
        table.setCurrentCell(0, 0)
        table._on_editor_closed(MagicMock(), 0)

        assert "PEPTIDE" in table._theoretical_spectra
        from utils.theoretical_spectrum import PeptideSpectrum

        spec = table._theoretical_spectra["PEPTIDE"]
        assert isinstance(spec, PeptideSpectrum)
        assert len(spec.fragments) == 12  # 6 b + 6 y

    def test_theoretical_spectrum_signal_emitted(self, ion_table_with_mock_view, qtbot):
        """Peptide lookup emits theoretical_spectrum_ready signal."""
        table = ion_table_with_mock_view

        from tests.conftest import SignalCatcher

        catcher = SignalCatcher()
        table.theoretical_spectrum_ready.connect(catcher.slot)

        table.setItem(0, 0, QtWidgets.QTableWidgetItem("PEPTIDE"))
        table.setCurrentCell(0, 0)
        table._on_editor_closed(MagicMock(), 0)

        assert catcher.was_called
        name, spectrum = catcher.args
        assert name == "PEPTIDE"
        from utils.theoretical_spectrum import PeptideSpectrum

        assert isinstance(spectrum, PeptideSpectrum)

    def test_info_column_filled_with_adducts(self, ion_table_with_mock_view, qtbot):
        """Info column should contain adduct labels."""
        table = ion_table_with_mock_view

        table.setItem(0, 0, QtWidgets.QTableWidgetItem("PEPTIDE"))
        table.setCurrentCell(0, 0)
        table._on_editor_closed(MagicMock(), 0)

        info_item = table.item(0, 2)
        assert info_item is not None
        info_text = info_item.text()
        assert "[M+H]+" in info_text or "[M-H]-" in info_text


# ===========================================================================
# TestConfigPersistence
# ===========================================================================


class TestConfigPersistence:
    """Tests for save/load round-trip with 'sequence' key."""

    @pytest.fixture
    def config_with_sequences(self, tmp_path):
        """Config with sequence fields for peptide compounds."""
        config = {
            "Peptide List": {
                "PEPTIDE": {
                    "ions": [800.3678, 798.3521],
                    "info": ["[M+H]+", "[M-H]-"],
                    "sequence": "PEPTIDE",
                },
                "Caffeine": {
                    "ions": [195.0882, 193.0726],
                    "info": ["[M+H]+", "[M-H]-"],
                    "formula": "C8H10N4O2",
                },
                "NoSpecial": {
                    "ions": [100.0],
                    "info": ["[M+H]+"],
                },
            }
        }
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config, indent=2))
        return config_path

    @pytest.fixture
    def tab_with_sequences(self, qapp, qtbot, config_with_sequences):
        from ui.tabs.upload_tab import UploadTab

        tab = UploadTab(parent=None, mode="MS Only")
        tab.config_path = config_with_sequences
        qtbot.addWidget(tab)

        tab.comboBoxIonLists.clear()
        tab.comboBoxIonLists.addItem("Create new ion list...")
        tab._load_ion_config_names()
        return tab

    def test_sequence_loads_peptide_spectrum(self, tab_with_sequences):
        """Loading a config with 'sequence' key creates a PeptideSpectrum."""
        tab = tab_with_sequences
        idx = tab.comboBoxIonLists.findText("Peptide List")
        tab.comboBoxIonLists.setCurrentIndex(idx)

        from utils.theoretical_spectrum import PeptideSpectrum

        assert "PEPTIDE" in tab.ionTable._theoretical_spectra
        spec = tab.ionTable._theoretical_spectra["PEPTIDE"]
        assert isinstance(spec, PeptideSpectrum)
        assert spec.sequence == "PEPTIDE"

    def test_formula_still_loads_correctly(self, tab_with_sequences):
        """Loading a config with 'formula' key still creates a TheoreticalSpectrum."""
        tab = tab_with_sequences
        idx = tab.comboBoxIonLists.findText("Peptide List")
        tab.comboBoxIonLists.setCurrentIndex(idx)

        from utils.theoretical_spectrum import TheoreticalSpectrum

        assert "Caffeine" in tab.ionTable._theoretical_spectra
        spec = tab.ionTable._theoretical_spectra["Caffeine"]
        assert isinstance(spec, TheoreticalSpectrum)

    def test_no_special_key_no_spectrum(self, tab_with_sequences):
        """Compounds without 'sequence' or 'formula' have no spectrum."""
        tab = tab_with_sequences
        idx = tab.comboBoxIonLists.findText("Peptide List")
        tab.comboBoxIonLists.setCurrentIndex(idx)

        assert "NoSpecial" not in tab.ionTable._theoretical_spectra

    def test_save_peptide_persists_sequence(self, tab_with_sequences):
        """Saving an ion list with peptide should persist 'sequence' key."""
        tab = tab_with_sequences
        idx = tab.comboBoxIonLists.findText("Peptide List")
        tab.comboBoxIonLists.setCurrentIndex(idx)

        # Build ions_data the same way save_ion_list does
        from utils.theoretical_spectrum import PeptideSpectrum

        ions_data = {}
        table = tab.ionTable
        for row in range(table.rowCount()):
            name_item = table.item(row, 0)
            if name_item is None:
                continue
            name = name_item.text().strip()
            if not name:
                continue
            ions_data[name] = {}
            mz_item = table.item(row, 1)
            mz_text = mz_item.text() if mz_item else ""
            try:
                ions_data[name]["ions"] = [
                    float(x) for x in mz_text.split(",") if x.strip()
                ]
            except ValueError:
                ions_data[name]["ions"] = []
            if name in table._theoretical_spectra:
                spectrum = table._theoretical_spectra[name]
                if isinstance(spectrum, PeptideSpectrum):
                    ions_data[name]["sequence"] = spectrum.sequence
                else:
                    ions_data[name]["formula"] = spectrum.formula

        assert "PEPTIDE" in ions_data
        assert ions_data["PEPTIDE"]["sequence"] == "PEPTIDE"
        assert "Caffeine" in ions_data
        assert ions_data["Caffeine"]["formula"] == "C8H10N4O2"
        assert "formula" not in ions_data.get("NoSpecial", {})
        assert "sequence" not in ions_data.get("NoSpecial", {})

    def test_peptide_plots_created(self, tab_with_sequences):
        """Peptide spectrum should create theoretical plots."""
        tab = tab_with_sequences
        idx = tab.comboBoxIonLists.findText("Peptide List")
        tab.comboBoxIonLists.setCurrentIndex(idx)

        assert "PEPTIDE" in tab._theoretical_plots
        # Should have multiple items (b bars, y bars, labels, precursor)
        assert len(tab._theoretical_plots["PEPTIDE"]) > 2


# ===========================================================================
# TestAdductChangeRecomputation
# ===========================================================================


class TestAdductChangeRecomputation:
    """Tests that adduct changes recompute peptide spectra."""

    @pytest.fixture
    def ion_table_with_mock_view(self, qapp, qtbot):
        from ui.widgets import IonTable

        mock_view = MagicMock()
        mock_view.comboBoxIonLists = MagicMock()
        mock_view.statusbar = MagicMock()

        table = IonTable(view=mock_view, parent=None)
        qtbot.addWidget(table)
        yield table

    def test_adduct_change_updates_peptide_mz(self, ion_table_with_mock_view, qtbot):
        """Changing adducts should update peptide m/z in the table."""
        table = ion_table_with_mock_view

        # First enter a peptide
        table.setItem(0, 0, QtWidgets.QTableWidgetItem("PEPTIDE"))
        table.setCurrentCell(0, 0)
        table._on_editor_closed(MagicMock(), 0)

        # Verify initial m/z
        mz_before = table.item(0, 1).text()
        assert "800.3678" in mz_before

        # Now change adducts to only [M+Na]+
        from tests.conftest import SignalCatcher

        catcher = SignalCatcher()
        table.theoretical_spectrum_ready.connect(catcher.slot)

        table._on_adducts_changed(["[M+Na]+"])

        # m/z should now be the [M+Na]+ value
        mz_after = table.item(0, 1).text()
        assert "[M+Na]+" in table.item(0, 2).text()
        assert "800.3678" not in mz_after  # Should be different now

    def test_adduct_change_reemits_signal(self, ion_table_with_mock_view, qtbot):
        """Changing adducts should re-emit theoretical_spectrum_ready for peptides."""
        table = ion_table_with_mock_view

        # Enter a peptide
        table.setItem(0, 0, QtWidgets.QTableWidgetItem("PEPTIDE"))
        table.setCurrentCell(0, 0)
        table._on_editor_closed(MagicMock(), 0)

        # Track signal emissions
        from tests.conftest import SignalCatcher

        catcher = SignalCatcher()
        table.theoretical_spectrum_ready.connect(catcher.slot)

        table._on_adducts_changed(["[M+H]+", "[M+2H]2+"])

        assert catcher.was_called
        name, spectrum = catcher.args
        assert name == "PEPTIDE"
        from utils.theoretical_spectrum import PeptideSpectrum

        assert isinstance(spectrum, PeptideSpectrum)

    def test_adduct_change_preserves_fragments(self, ion_table_with_mock_view, qtbot):
        """Fragment ions should still be present after adduct change."""
        table = ion_table_with_mock_view

        # Enter a peptide
        table.setItem(0, 0, QtWidgets.QTableWidgetItem("PEPTIDE"))
        table.setCurrentCell(0, 0)
        table._on_editor_closed(MagicMock(), 0)

        table._on_adducts_changed(["[M+Na]+"])

        from utils.theoretical_spectrum import PeptideSpectrum

        spec = table._theoretical_spectra["PEPTIDE"]
        assert isinstance(spec, PeptideSpectrum)
        assert len(spec.fragments) == 12  # Still 6 b + 6 y


# ===========================================================================
# TestPlottingDispatch
# ===========================================================================


class TestPlottingDispatch:
    """Tests for _on_theoretical_spectrum_ready dispatching."""

    @pytest.fixture
    def tab(self, qapp, qtbot):
        from ui.tabs.upload_tab import UploadTab

        tab = UploadTab(parent=None, mode="MS Only")
        qtbot.addWidget(tab)
        return tab

    def test_peptide_dispatches_to_plot_peptide(self, tab):
        """PeptideSpectrum triggers _plot_peptide_spectrum."""
        from utils.theoretical_spectrum import calculate_peptide_fragments

        spec = calculate_peptide_fragments("PEPTIDE", ["[M+H]+"])

        with patch.object(tab, "_plot_peptide_spectrum") as mock_plot:
            tab._on_theoretical_spectrum_ready("PEPTIDE", spec)
            mock_plot.assert_called_once_with("PEPTIDE", spec)

    def test_formula_dispatches_to_plot_formula(self, tab):
        """TheoreticalSpectrum triggers _plot_formula_spectrum."""
        from utils.theoretical_spectrum import calculate_theoretical_spectrum

        spec = calculate_theoretical_spectrum("C8H10N4O2")

        with patch.object(tab, "_plot_formula_spectrum") as mock_plot:
            tab._on_theoretical_spectrum_ready("C8H10N4O2", spec)
            mock_plot.assert_called_once_with("C8H10N4O2", spec)

    def test_peptide_plot_creates_items(self, tab):
        """Plotting a peptide spectrum creates bar graph and text items."""
        from utils.theoretical_spectrum import calculate_peptide_fragments

        spec = calculate_peptide_fragments("PEPTIDE", ["[M+H]+"])
        tab._on_theoretical_spectrum_ready("PEPTIDE", spec)

        assert "PEPTIDE" in tab._theoretical_plots
        items = tab._theoretical_plots["PEPTIDE"]
        # Should have b bars + b labels + y bars + y labels + precursor bars
        assert len(items) > 4

    def test_peptide_plot_cleanup(self, tab):
        """Removing a peptide compound cleans up all plots."""
        from utils.theoretical_spectrum import calculate_peptide_fragments

        spec = calculate_peptide_fragments("PEPTIDE", ["[M+H]+"])
        tab._on_theoretical_spectrum_ready("PEPTIDE", spec)

        assert "PEPTIDE" in tab._theoretical_plots
        tab._remove_theoretical_plots("PEPTIDE")
        assert "PEPTIDE" not in tab._theoretical_plots

    def test_peptide_labels_survive_update_labels(self, tab):
        """Peptide b/y TextItems must not be removed by update_labels_avgMS()."""
        import pyqtgraph as pg
        from utils.theoretical_spectrum import calculate_peptide_fragments
        from ui.plotting import update_labels_avgMS

        spec = calculate_peptide_fragments("PEPTIDE", ["[M+H]+"])
        tab._on_theoretical_spectrum_ready("PEPTIDE", spec)

        # Count peptide TextItems before
        peptide_texts_before = [
            item
            for item in tab.canvas_avgMS.items()
            if isinstance(item, pg.TextItem)
            and getattr(item, "_lcms_owner", None) != "peak_label"
        ]
        assert len(peptide_texts_before) > 0, "Peptide labels should exist"

        # Trigger the zoom/pan label refresh
        update_labels_avgMS(tab.canvas_avgMS)

        # Count peptide TextItems after — should be unchanged
        peptide_texts_after = [
            item
            for item in tab.canvas_avgMS.items()
            if isinstance(item, pg.TextItem)
            and getattr(item, "_lcms_owner", None) != "peak_label"
        ]
        assert len(peptide_texts_after) == len(peptide_texts_before)

    def test_formula_labels_created(self, tab):
        """Formula spectrum creates TextItem labels for each adduct."""
        import pyqtgraph as pg
        from utils.theoretical_spectrum import calculate_theoretical_spectrum

        spec = calculate_theoretical_spectrum("C8H10N4O2", ["[M+H]+", "[M-H]-"])
        tab._on_theoretical_spectrum_ready("C8H10N4O2", spec)

        assert "C8H10N4O2" in tab._theoretical_plots
        items = tab._theoretical_plots["C8H10N4O2"]

        text_items = [i for i in items if isinstance(i, pg.TextItem)]
        assert len(text_items) == 2  # One label per adduct

        labels = {t.toPlainText() for t in text_items}
        assert "[M+H]+" in labels
        assert "[M-H]-" in labels

    def test_mz_range_dialog_opens_for_peptide(self, qapp, qtbot):
        """MzRangeDialog does not crash when given a PeptideSpectrum."""
        from ui.widgets import MzRangeDialog
        from utils.theoretical_spectrum import calculate_peptide_fragments

        spec = calculate_peptide_fragments("PEPTIDE", ["[M+H]+"])
        mzs = np.linspace(100, 1000, 2000)
        intensities = np.random.default_rng(42).random(2000) * 10000

        # Get first precursor m/z for target
        adduct_spec = spec.precursor_isotopes["[M+H]+"]
        target_mz = float(adduct_spec.mz_values[0])

        d = MzRangeDialog(
            mzs=mzs,
            intensities=intensities,
            target_mz_values=[target_mz],
            ion_labels=["[M+H]+"],
            mass_accuracy=0.01,
            compound_name="PEPTIDE",
            existing_ranges={},
            theoretical_spectrum=spec,
        )
        qtbot.addWidget(d)

        # Dialog opened without crashing — verify theoretical overlay was plotted
        assert len(d._theo_items) > 0


# ===========================================================================
# TestExistingBehaviorPreserved
# ===========================================================================


class TestExistingBehaviorPreserved:
    """Verify no regressions in existing formula/name detection."""

    def test_formulas_still_detected(self):
        from utils.theoretical_spectrum import detect_input_type

        assert detect_input_type("C6H12O6") == "formula"
        assert detect_input_type("H2O") == "formula"
        assert detect_input_type("NaCl") == "formula"
        assert detect_input_type("C8H10N4O2") == "formula"

    def test_names_still_detected(self):
        from utils.theoretical_spectrum import detect_input_type

        assert detect_input_type("glucose") == "name"
        assert detect_input_type("caffeine") == "name"
        assert detect_input_type("Aspirin") == "name"
        assert detect_input_type("acetic acid") == "name"
        assert detect_input_type("") == "name"
        assert detect_input_type("   ") == "name"
