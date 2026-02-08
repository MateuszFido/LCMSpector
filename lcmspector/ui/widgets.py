from datetime import datetime
import json
import webbrowser
from pathlib import Path
import numpy as np
import pyqtgraph as pg
from pyqtgraph import mkPen
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from utils.classes import Compound


class DragDropListWidget(QtWidgets.QListWidget):
    filesDropped = QtCore.Signal(list)  # Define a custom signal

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)  # Enable accepting drops
        self.setWordWrap(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.contextMenuEvent)

    def contextMenuEvent(self, pos):
        item = self.itemAt(pos)
        if item is not None:
            menu = QtWidgets.QMenu()
            deleteAction = menu.addAction("(⌫/Del) Delete")
            action = menu.exec(self.mapToGlobal(pos))
            if action == deleteAction:
                self.takeItem(self.row(item))

    def keyPressEvent(self, event):
        if (
            event.key() == QtCore.Qt.Key.Key_Backspace
            or event.key() == QtCore.Qt.Key.Key_Delete
        ):
            item = self.currentItem()
            self.takeItem(self.row(item))

    def dragEnterEvent(self, event):
        # Check if the dragged item is a file
        if event.mimeData().hasUrls():
            event.acceptProposedAction()  # Accept the drag event

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)  # Set the drop action to copy
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)  # Set the drop action to copy
            event.accept()
            file_paths = []
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                file_paths.append(file_path)
            self.filesDropped.emit(file_paths)
        else:
            event.ignore()


class CheckableDragDropListWidget(DragDropListWidget):
    """DragDropListWidget with checkboxes for each item."""

    itemCheckStateChanged = QtCore.Signal(str, bool)  # (filename, is_checked)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.itemChanged.connect(self._on_item_changed)
        self._checkbox_click_pending = False  # Track if last click was on checkbox

    def mousePressEvent(self, event):
        """Detect if click is on checkbox area."""
        # Use position() for Qt6 compatibility (pos() is deprecated)
        pos = event.position().toPoint()
        item = self.itemAt(pos)
        if item:
            # Get the checkbox rect for this item
            rect = self.visualItemRect(item)
            # Checkbox is typically in the left ~20-30 pixels
            checkbox_width = 24  # Approximate checkbox click area
            checkbox_rect = QtCore.QRect(
                rect.left(), rect.top(), checkbox_width, rect.height()
            )
            self._checkbox_click_pending = checkbox_rect.contains(pos)
        else:
            self._checkbox_click_pending = False
        super().mousePressEvent(event)

    def was_checkbox_click(self):
        """Return True if the last click was on the checkbox area."""
        return self._checkbox_click_pending

    def addItem(self, item):
        """Override to add checkbox functionality."""
        if isinstance(item, str):
            list_item = QtWidgets.QListWidgetItem(item)
        else:
            list_item = item
        list_item.setFlags(list_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        list_item.setCheckState(Qt.CheckState.Unchecked)
        super().addItem(list_item)

    def checkItem(self, row):
        """Programmatically check a box next to the item."""
        self.item(row).setCheckState(Qt.CheckState.Checked)

    def _on_item_changed(self, item):
        """Emit signal when checkbox state changes."""
        is_checked = item.checkState() == Qt.CheckState.Checked
        self.itemCheckStateChanged.emit(item.text(), is_checked)

    def takeItem(self, row):
        """Override to emit uncheck signal for checked items being removed."""
        item = self.item(row)
        if item and item.checkState() == Qt.CheckState.Checked:
            self.itemCheckStateChanged.emit(item.text(), False)
        return super().takeItem(row)


class GenericTable(QtWidgets.QTableWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents
        )
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self.setShowGrid(True)
        self.setGridStyle(QtCore.Qt.PenStyle.SolidLine)
        self.setStyleSheet("gridline-color: #e0e0e0;")
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.undoStack = QtGui.QUndoStack(self)
        self.undoStack.setUndoLimit(100)
        self.customContextMenuRequested.connect(self.contextMenuEvent)

    def contextMenuEvent(self, event):
        self.menu = QtWidgets.QMenu(self)

        add_row_action = QtGui.QAction(
            QtGui.QIcon.fromTheme("document-new"), "(⌘+N) Add Row", self
        )
        add_row_action.triggered.connect(self.append_row)
        self.menu.addAction(add_row_action)

        remove_row_action = QtGui.QAction(
            QtGui.QIcon.fromTheme("edit-delete"), "(⌫) Remove Row", self
        )
        remove_row_action.triggered.connect(self.clear_selection)
        self.menu.addAction(remove_row_action)

        select_all_action = QtGui.QAction(
            QtGui.QIcon.fromTheme("edit-select-all"), "(⌘+A) Select All", self
        )
        select_all_action.triggered.connect(self.select_all)
        self.menu.addAction(select_all_action)

        copy_action = QtGui.QAction(
            QtGui.QIcon.fromTheme("edit-copy"), "(⌘+C) Copy", self
        )
        copy_action.triggered.connect(self.copy)
        self.menu.addAction(copy_action)

        paste_action = QtGui.QAction(
            QtGui.QIcon.fromTheme("edit-paste"), "(⌘+V) Paste", self
        )
        paste_action.triggered.connect(self.paste_from_clipboard)
        self.menu.addAction(paste_action)

        undo_action = QtGui.QAction(
            QtGui.QIcon.fromTheme("edit-undo"), "(⌘+Z) Undo", self
        )
        undo_action.triggered.connect(self.undoStack.undo)
        self.menu.addAction(undo_action)

        redo_action = QtGui.QAction(
            QtGui.QIcon.fromTheme("edit-redo"), "(⌘+U) Redo", self
        )
        redo_action.triggered.connect(self.undoStack.redo)
        self.menu.addAction(redo_action)

        self.menu.popup(QtGui.QCursor.pos())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_V and (
            event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
        ):
            self.paste_from_clipboard()
        elif event.key() == Qt.Key.Key_A and (
            event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
        ):
            self.select_all()
        elif (
            event.key() == QtCore.Qt.Key.Key_Backspace
            or event.key() == QtCore.Qt.Key.Key_Delete
        ):
            self.clear_selection()
        elif event.key() == Qt.Key.Key_C and (
            event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
        ):
            self.copy()
        elif event.key() == Qt.Key.Key_Z and (
            event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
        ):
            self.undoStack.undo()
        elif event.key() == Qt.Key.Key_U and (
            event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
        ):
            self.undoStack.redo()
        elif event.key() == Qt.Key.Key_N and (
            event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
        ):
            self.append_row(self.rowCount())
        else:
            super().keyPressEvent(event)

    def select_all(self):
        self.selectAll()

    def clear_selection(self):
        command = ClearSelectionCommand(self)
        self.undoStack.push(command)

    def paste_from_clipboard(self):
        command = PasteFromClipboardCommand(self)
        self.undoStack.push(command)

    def copy(self):
        command = CopyCommand(self)
        self.undoStack.push(command)

    def insert_row(self, row):
        command = InsertRowCommand(self, row)
        self.undoStack.push(command)
        super().insertRow(row)

    def append_row(self, row):
        # Append row to the end of the table
        self.insert_row(self.rowCount())

    def set_item(self, row, col, item):
        if self.item(row, col) is None or self.item(row, col).text() != item.text():
            command = SetItemCommand(self, row, col, item.text())
            self.undoStack.push(command)
        super().setItem(row, col, item)


class AdductDropdown(QtWidgets.QToolButton):
    """Checkable dropdown for selecting MS adduct types.

    Displays a QMenu with checkable actions grouped by polarity (positive/negative).
    The menu stays open after clicking an action so users can check multiple adducts
    without re-opening.

    Signals
    -------
    adducts_changed : Signal(list)
        Emitted when the set of checked adducts changes. Payload is a list of
        checked adduct label strings.
    """

    adducts_changed = QtCore.Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        from utils.theoretical_spectrum import ADDUCT_DEFINITIONS

        self.setText("Adducts")
        self.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setToolTip("Select adduct types for m/z calculation")

        menu = QtWidgets.QMenu(self)
        self._actions: dict[str, QtGui.QAction] = {}

        # Group by polarity
        menu.addSection("Positive")
        for label, defn in ADDUCT_DEFINITIONS.items():
            if defn.polarity == "positive":
                action = menu.addAction(label)
                action.setCheckable(True)
                action.setChecked(defn.default_checked)
                action.triggered.connect(self._on_action_triggered)
                self._actions[label] = action

        menu.addSection("Negative")
        for label, defn in ADDUCT_DEFINITIONS.items():
            if defn.polarity == "negative":
                action = menu.addAction(label)
                action.setCheckable(True)
                action.setChecked(defn.default_checked)
                action.triggered.connect(self._on_action_triggered)
                self._actions[label] = action

        # Keep menu open after clicking an action
        menu.setToolTipsVisible(True)
        self._keep_open = True

        # Override close behavior to keep menu open on action click
        original_mouse_release = menu.mouseReleaseEvent

        def _custom_mouse_release(event):
            action = menu.actionAt(event.position().toPoint())
            if action and action.isCheckable():
                action.trigger()
                return  # Don't close menu
            original_mouse_release(event)

        menu.mouseReleaseEvent = _custom_mouse_release

        self.setMenu(menu)

    def _on_action_triggered(self):
        """Emit adducts_changed when any action is toggled."""
        self.adducts_changed.emit(self.checked_adducts())

    def checked_adducts(self) -> list[str]:
        """Return list of currently checked adduct labels."""
        return [label for label, action in self._actions.items() if action.isChecked()]

    def set_checked(self, labels: list[str]):
        """Set which adducts are checked, blocking signals during update.

        Parameters
        ----------
        labels : list[str]
            Adduct labels to check. All others will be unchecked.
        """
        self.blockSignals(True)
        label_set = set(labels)
        for label, action in self._actions.items():
            action.setChecked(label in label_set)
        self.blockSignals(False)


class IonTable(GenericTable):
    # Signal emitted for status bar updates
    lookup_status = QtCore.Signal(str, int)  # (message, duration_ms)
    # Signal emitted when a theoretical spectrum is computed
    theoretical_spectrum_ready = QtCore.Signal(
        str, object
    )  # (compound_name, TheoreticalSpectrum)
    # Signal emitted when a compound is removed from the table
    compound_removed = QtCore.Signal(str)  # compound_name

    def __init__(self, view, parent=None):
        super().__init__(50, 3, parent)
        self.setHorizontalHeaderLabels(["Compound", "Expected m/z", "Add. info"])
        self.setObjectName("ionTable")
        self.setStyleSheet("gridline-color: #e0e0e0;")
        self.view = view

        # PubChem lookup state
        self._lookup_thread = None
        self._lookup_worker = None

        # Custom m/z range storage: {compound_name: {mz: (left, right)}}
        self._custom_mz_ranges = {}

        # Theoretical spectra storage: {compound_name: TheoreticalSpectrum}
        self._theoretical_spectra = {}

        # Adduct dropdown reference (set via set_adduct_dropdown)
        self._adduct_dropdown = None

        # Connect closeEditor signal (fires only when editing finishes, not on each keystroke)
        self.itemDelegate().closeEditor.connect(self._on_editor_closed)

    def set_adduct_dropdown(self, dropdown: "AdductDropdown"):
        """Store reference to the adduct dropdown.

        Note: No signal connection here — UploadTab orchestrates the
        adducts_changed flow to ensure correct clear→recompute→replot order.
        """
        self._adduct_dropdown = dropdown

    def _get_active_adducts(self) -> list[str]:
        """Return currently checked adducts from dropdown, or defaults."""
        from utils.theoretical_spectrum import DEFAULT_ADDUCTS

        if self._adduct_dropdown is not None:
            return self._adduct_dropdown.checked_adducts()
        return list(DEFAULT_ADDUCTS)

    def _find_row_by_name(self, name: str) -> int:
        """Find the table row index for a compound name, or -1 if not found."""
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if item and item.text().strip() == name:
                return row
        return -1

    def _on_adducts_changed(self, adduct_list: list[str]):
        """Recompute m/z and theoretical spectra for all formula-based compounds."""
        from utils.theoretical_spectrum import (
            calculate_monoisotopic_mz,
            calculate_theoretical_spectrum,
        )

        for name, spectrum in list(self._theoretical_spectra.items()):
            formula = spectrum.formula

            # Fast path: update table m/z values
            mz_dict = calculate_monoisotopic_mz(formula, adduct_list)
            if not mz_dict:
                continue

            row = self._find_row_by_name(name)
            if row < 0:
                continue

            mz_text = ", ".join(str(v) for v in mz_dict.values())
            info_text = ", ".join(mz_dict.keys())

            self.blockSignals(True)
            mz_item = self.item(row, 1)
            if mz_item is None:
                mz_item = QtWidgets.QTableWidgetItem()
                self.setItem(row, 1, mz_item)
            mz_item.setText(mz_text)

            info_item = self.item(row, 2)
            if info_item is None:
                info_item = QtWidgets.QTableWidgetItem()
                self.setItem(row, 2, info_item)
            info_item.setText(info_text)
            self.blockSignals(False)

            self._highlight_cell(row, 1)
            self._highlight_cell(row, 2)

            # Slow path: recompute theoretical spectrum with new adducts
            try:
                new_spectrum = calculate_theoretical_spectrum(formula, adduct_list)
                self._theoretical_spectra[name] = new_spectrum
                self.theoretical_spectrum_ready.emit(name, new_spectrum)
            except Exception:
                pass

    def clear_selection(self):
        """Override to detect removed compounds and emit compound_removed signal."""
        removed_names = set()
        for item in self.selectedItems():
            if item.column() == 0 and item.text().strip():
                removed_names.add(item.text().strip())
        super().clear_selection()
        for name in removed_names:
            self._theoretical_spectra.pop(name, None)
            self.compound_removed.emit(name)

    def contextMenuEvent(self, pos):
        """Override to add 'Edit integration...' action to context menu."""
        # Build the base menu (same as GenericTable but without popup)
        self.menu = QtWidgets.QMenu(self)

        add_row_action = QtGui.QAction(
            QtGui.QIcon.fromTheme("document-new"), "(⌘+N) Add Row", self
        )
        add_row_action.triggered.connect(self.append_row)
        self.menu.addAction(add_row_action)

        remove_row_action = QtGui.QAction(
            QtGui.QIcon.fromTheme("edit-delete"), "(⌫) Remove Row", self
        )
        remove_row_action.triggered.connect(self.clear_selection)
        self.menu.addAction(remove_row_action)

        select_all_action = QtGui.QAction(
            QtGui.QIcon.fromTheme("edit-select-all"), "(⌘+A) Select All", self
        )
        select_all_action.triggered.connect(self.select_all)
        self.menu.addAction(select_all_action)

        copy_action = QtGui.QAction(
            QtGui.QIcon.fromTheme("edit-copy"), "(⌘+C) Copy", self
        )
        copy_action.triggered.connect(self.copy)
        self.menu.addAction(copy_action)

        paste_action = QtGui.QAction(
            QtGui.QIcon.fromTheme("edit-paste"), "(⌘+V) Paste", self
        )
        paste_action.triggered.connect(self.paste_from_clipboard)
        self.menu.addAction(paste_action)

        undo_action = QtGui.QAction(
            QtGui.QIcon.fromTheme("edit-undo"), "(⌘+Z) Undo", self
        )
        undo_action.triggered.connect(self.undoStack.undo)
        self.menu.addAction(undo_action)

        redo_action = QtGui.QAction(
            QtGui.QIcon.fromTheme("edit-redo"), "(⌘+U) Redo", self
        )
        redo_action.triggered.connect(self.undoStack.redo)
        self.menu.addAction(redo_action)

        # --- Add integration editor action ---
        self.menu.addSeparator()
        edit_action = QtGui.QAction("Edit integration...", self)

        # Only enable if the right-clicked row has m/z values
        row = self.rowAt(pos.y())
        mz_item = self.item(row, 1) if row >= 0 else None
        has_mz = mz_item is not None and mz_item.text().strip()
        edit_action.setEnabled(bool(has_mz))

        edit_action.triggered.connect(lambda: self._open_mz_range_dialog(row))
        self.menu.addAction(edit_action)

        self.menu.popup(QtGui.QCursor.pos())

    def _open_mz_range_dialog(self, row):
        """Open the MzRangeDialog for the compound at the given row."""
        # 1. Parse compound info from the row
        name_item = self.item(row, 0)
        if name_item is None:
            return
        compound_name = name_item.text().strip()
        if not compound_name:
            return

        mz_item = self.item(row, 1)
        if mz_item is None:
            return
        try:
            mz_values = [float(x) for x in mz_item.text().split(",") if x.strip()]
        except ValueError:
            return
        if not mz_values:
            return

        info_item = self.item(row, 2)
        info_text = info_item.text() if info_item else ""
        ion_labels = [x.strip() for x in info_text.split(",") if x.strip()]
        # Pad labels
        while len(ion_labels) < len(mz_values):
            ion_labels.append(f"m/z {mz_values[len(ion_labels)]:.4f}")

        # 2. Get spectrum data from UploadTab
        spectrum_data = self.view.get_current_spectrum_data()
        if spectrum_data is None:
            self.lookup_status.emit(
                "No MS data available. Check an MS file first.", 5000
            )
            return
        mzs, intensities = spectrum_data

        # 3. Get mass accuracy
        mass_accuracy = self.view.mass_accuracy

        # 4. Launch dialog
        dialog = MzRangeDialog(
            mzs=mzs,
            intensities=intensities,
            target_mz_values=mz_values,
            ion_labels=ion_labels,
            mass_accuracy=mass_accuracy,
            compound_name=compound_name,
            existing_ranges=self._custom_mz_ranges.get(compound_name, {}),
            theoretical_spectrum=self._theoretical_spectra.get(compound_name),
            parent=self,
        )
        dialog.exec()

        # 5. Store result
        ranges = dialog.get_ranges()
        if ranges:
            self._custom_mz_ranges[compound_name] = ranges
            self.lookup_status.emit(
                f"Applied integration boundaries for '{compound_name}' to all files",
                5000,
            )
        elif compound_name in self._custom_mz_ranges:
            del self._custom_mz_ranges[compound_name]

    def _on_editor_closed(self, editor, hint):
        """Handle editor close - trigger PubChem lookup for compound names.

        This fires only when editing is finished (Enter, Tab, or click away),
        not on every keystroke like cellChanged does.
        """
        row = self.currentRow()
        col = self.currentColumn()

        # Only trigger on compound name column (col 0)
        if col != 0:
            return

        # Get the compound name
        name_item = self.item(row, 0)
        if name_item is None:
            return
        compound_name = name_item.text().strip()
        if not compound_name:
            return

        # Only lookup if m/z column is empty
        mz_item = self.item(row, 1)
        if mz_item is not None and mz_item.text().strip():
            return

        # Branch: formula → local calculation, name → PubChem lookup
        from utils.theoretical_spectrum import detect_input_type

        if detect_input_type(compound_name) == "formula":
            self._execute_formula_lookup(row, compound_name)
        else:
            # Execute PubChem lookup (no debounce needed since closeEditor only fires once)
            self._execute_lookup_for(row, compound_name)

    def _execute_lookup_for(self, row: int, compound_name: str):
        """Execute a PubChem lookup for the given row and compound name."""
        # Clean up any existing lookup
        self._cleanup_lookup()

        # Emit status message
        self.lookup_status.emit(f"Looking up '{compound_name}' on PubChem...", 0)

        # Create worker and thread
        from PySide6.QtCore import QThread
        from utils.pubchem import PubChemLookupWorker

        self._lookup_thread = QThread()
        self._lookup_worker = PubChemLookupWorker(compound_name)
        self._lookup_worker.moveToThread(self._lookup_thread)

        # Store row for the callback
        self._lookup_row = row

        # Connect signals
        self._lookup_thread.started.connect(self._lookup_worker.run)
        self._lookup_worker.finished.connect(self._on_lookup_finished)
        self._lookup_worker.error.connect(self._on_lookup_error)
        self._lookup_worker.finished.connect(self._cleanup_lookup)
        self._lookup_worker.error.connect(self._cleanup_lookup)

        # Start the lookup
        self._lookup_thread.start()

    def _execute_formula_lookup(self, row: int, formula: str):
        """Resolve a molecular formula locally and fill m/z cells.

        Computes monoisotopic m/z for all active adducts from the formula
        using pyteomics, fills the table cells, and emits
        ``theoretical_spectrum_ready``.
        """
        from utils.theoretical_spectrum import (
            calculate_monoisotopic_mz,
            calculate_theoretical_spectrum,
        )

        active_adducts = self._get_active_adducts()

        # Fast path: compute monoisotopic m/z for table display
        try:
            mz_dict = calculate_monoisotopic_mz(formula, active_adducts)
        except Exception as e:
            self.lookup_status.emit(f"Invalid formula '{formula}': {e}", 5000)
            return

        if not mz_dict:
            self.lookup_status.emit(f"Could not compute adducts for '{formula}'", 5000)
            return

        mz_text = ", ".join(str(v) for v in mz_dict.values())
        info_text = ", ".join(mz_dict.keys())

        # Block signals to avoid re-triggering
        self.blockSignals(True)

        mz_item = self.item(row, 1)
        if mz_item is None:
            mz_item = QtWidgets.QTableWidgetItem()
            self.setItem(row, 1, mz_item)
        mz_item.setText(mz_text)

        info_item = self.item(row, 2)
        if info_item is None:
            info_item = QtWidgets.QTableWidgetItem()
            self.setItem(row, 2, info_item)
        info_item.setText(info_text)

        self.blockSignals(False)

        # Apply green highlight
        self._highlight_cell(row, 1)
        self._highlight_cell(row, 2)

        # Slow path: compute theoretical spectrum with isotopic patterns
        try:
            spectrum = calculate_theoretical_spectrum(formula, active_adducts)
            self._theoretical_spectra[formula] = spectrum
            self.theoretical_spectrum_ready.emit(formula, spectrum)
        except ValueError as e:
            self.lookup_status.emit(f"Invalid formula '{formula}': {e}", 5000)
            return

        first_label = next(iter(mz_dict))
        first_mz = mz_dict[first_label]
        self.lookup_status.emit(
            f"Formula '{formula}' resolved: {first_label} = {first_mz}", 5000
        )

    def _on_lookup_finished(self, compound_name: str, data: dict):
        """Handle successful PubChem lookup - fill m/z and info columns."""
        row = getattr(self, "_lookup_row", None)
        if row is None:
            return

        # Verify the row still has the same compound name
        name_item = self.item(row, 0)
        if name_item is None or name_item.text().strip() != compound_name:
            return

        molecular_formula = data.get("molecular_formula", "")

        # If PubChem returned a molecular formula, use active adducts for m/z
        if molecular_formula:
            from utils.theoretical_spectrum import (
                calculate_monoisotopic_mz,
                calculate_theoretical_spectrum,
            )

            active_adducts = self._get_active_adducts()
            try:
                mz_dict = calculate_monoisotopic_mz(molecular_formula, active_adducts)
            except Exception:
                mz_dict = {}

            if mz_dict:
                mz_text = ", ".join(str(v) for v in mz_dict.values())
                info_text = ", ".join(mz_dict.keys())
            else:
                # Fallback to PubChem's simple [M+H]+/[M-H]- values
                mz_pos = data.get("mz_pos")
                mz_neg = data.get("mz_neg")
                if mz_pos is not None and mz_neg is not None:
                    mz_text = f"{mz_pos}, {mz_neg}"
                    info_text = "[M+H]+, [M-H]-"
                else:
                    return
        else:
            # No molecular formula - use PubChem's simple values
            mz_pos = data.get("mz_pos")
            mz_neg = data.get("mz_neg")
            if mz_pos is not None and mz_neg is not None:
                mz_text = f"{mz_pos}, {mz_neg}"
                info_text = "[M+H]+, [M-H]-"
            else:
                return

        # Block signals to avoid re-triggering
        self.blockSignals(True)

        # Fill m/z column
        mz_item = self.item(row, 1)
        if mz_item is None:
            mz_item = QtWidgets.QTableWidgetItem()
            self.setItem(row, 1, mz_item)
        mz_item.setText(mz_text)

        # Fill info column
        info_item = self.item(row, 2)
        if info_item is None:
            info_item = QtWidgets.QTableWidgetItem()
            self.setItem(row, 2, info_item)
        info_item.setText(info_text)

        self.blockSignals(False)

        # Apply green highlight to filled cells
        self._highlight_cell(row, 1)
        self._highlight_cell(row, 2)

        # Emit success status
        first_mz = mz_text.split(",")[0].strip()
        first_info = info_text.split(",")[0].strip()
        self.lookup_status.emit(
            f"PubChem lookup successful for '{compound_name}': {first_info} = {first_mz}",
            5000,
        )

        # Compute theoretical spectrum if molecular formula is available
        if molecular_formula:
            try:
                active_adducts = self._get_active_adducts()
                spectrum = calculate_theoretical_spectrum(
                    molecular_formula, active_adducts
                )
                self._theoretical_spectra[compound_name] = spectrum
                self.theoretical_spectrum_ready.emit(compound_name, spectrum)
            except Exception:
                pass  # Non-critical: theoretical overlay is optional

    def _on_lookup_error(self, compound_name: str, error_msg: str):
        """Handle PubChem lookup error."""
        # Emit descriptive error status
        if "not found" in error_msg.lower():
            self.lookup_status.emit(
                f"Compound '{compound_name}' not found on PubChem", 5000
            )
        else:
            self.lookup_status.emit(
                f"PubChem lookup failed for '{compound_name}': {error_msg}", 5000
            )

    def _highlight_cell(self, row: int, col: int):
        """Apply temporary green highlight to cell (reverts after 10 seconds)."""
        item = self.item(row, col)
        if item is None:
            return

        highlight_color = QtGui.QColor(200, 255, 200)
        original_brush = item.background()
        item.setBackground(highlight_color)

        # Store coordinates for safe revert
        target_row, target_col = row, col
        table_ref = self

        def revert():
            """Safely revert background color, handling deleted items."""
            try:
                if (
                    table_ref.rowCount() > target_row
                    and table_ref.columnCount() > target_col
                ):
                    current_item = table_ref.item(target_row, target_col)
                    if current_item is not None:
                        current_item.setBackground(original_brush)
            except RuntimeError:
                # Table or item was deleted, ignore
                pass

        QtCore.QTimer.singleShot(10000, revert)

    def _cleanup_lookup(self):
        """Clean up lookup thread and worker."""
        if self._lookup_thread is not None:
            self._lookup_thread.quit()
            self._lookup_thread.wait(1000)
            self._lookup_thread.deleteLater()
            self._lookup_thread = None

        if self._lookup_worker is not None:
            self._lookup_worker.deleteLater()
            self._lookup_worker = None

    def get_items(self):
        """
        Parses the table rows into Compound objects.
        Robustly handles empty cells for m/z or info columns.
        """
        items = []
        for row in range(self.rowCount()):
            # 1. Get Name (Required)
            name_item = self.item(row, 0)
            if name_item is None:
                continue
            name = name_item.text().strip()
            if not name:
                continue

            # 2. Get Ions (Optional-ish, usually required but handled safely)
            mz_item = self.item(row, 1)
            mz_text = mz_item.text() if mz_item else ""
            try:
                # Split by comma and filter out empty strings to prevent conversion errors
                ions = [float(x) for x in mz_text.split(",") if x.strip()]
            except ValueError:
                ions = []

            # 3. Get Info (Strictly Optional)
            info_item = self.item(row, 2)
            info_text = info_item.text() if info_item else ""
            # Create list, filtering out empty strings
            ion_info = [x.strip() for x in info_text.split(",") if x.strip()]

            try:
                compound = Compound(name=name, target_list=ions, ion_info=ion_info)
                if name in self._custom_mz_ranges:
                    compound.custom_mz_ranges = dict(self._custom_mz_ranges[name])
                items.append(compound)
            except Exception as e:
                print(f"Error creating compound '{name}': {e}")
                continue

        return items

    def save_ion_list(self):
        """
        Saves the current table state to config.json.
        Ensures 'info' key is always present (even if empty) to prevent KeyErrors on load.
        """
        # Prompt the user how they want to name the list
        ion_list_name, okPressed = QtWidgets.QInputDialog.getText(
            self, "New ion list", "Name the new ion list:"
        )
        if not okPressed or not ion_list_name.strip():
            return

        ions_data = {}
        for row in range(self.rowCount()):
            # 1. Get Name
            name_item = self.item(row, 0)
            if name_item is None:
                continue
            name = name_item.text().strip()
            if not name:
                continue

            # Initialize dictionary for this compound
            ions_data[name] = {}

            # 2. Get Ions
            mz_item = self.item(row, 1)
            mz_text = mz_item.text() if mz_item else ""
            try:
                ions_data[name]["ions"] = [
                    float(x) for x in mz_text.split(",") if x.strip()
                ]
            except ValueError:
                ions_data[name]["ions"] = []

            # 3. Get Info - THE FIX
            # Instead of skipping the row if this fails, we default to an empty list.
            info_item = self.item(row, 2)
            info_text = info_item.text() if info_item else ""
            ions_data[name]["info"] = [
                x.strip() for x in info_text.split(",") if x.strip()
            ]

            # 4. Persist formula if available (for auto-plotting on reload)
            if name in self._theoretical_spectra:
                ions_data[name]["formula"] = self._theoretical_spectra[name].formula

        # 5. Persist adduct selection
        active_adducts = self._get_active_adducts()
        from utils.theoretical_spectrum import DEFAULT_ADDUCTS

        # Compare as sets so the same selection in a different order
        # does not trigger unnecessary persistence.
        if set(active_adducts) != set(DEFAULT_ADDUCTS):
            ions_data["_adducts"] = active_adducts

        # Save locally in config.json
        try:
            config_path = Path(__file__).parent.parent / "config.json"

            # Helper to ensure file exists or create empty dict
            if not config_path.exists():
                config = {}
            else:
                with open(config_path, "r") as f:
                    try:
                        config = json.load(f)
                    except json.JSONDecodeError:
                        config = {}

            # Update config with new data
            config[ion_list_name] = ions_data

            with open(config_path, "w") as f:
                json.dump(config, f, indent=4)

            # Update View
            self.view.comboBoxIonLists.clear()
            self.view.comboBoxIonLists.addItem("Create new ion list...")
            self.view.comboBoxIonLists.addItems(
                list(config.keys())
            )  # Use list() for safety

            self.view.statusbar.showMessage(
                f'{datetime.now().strftime("%d/%m/%Y %H:%M:%S")} -- Saved new ion list: "{ion_list_name}".',
                5000,
            )
        except Exception as e:
            print(f"Could not save ions to config.json: {e}")
            # Optional: Show an error message box here so the user knows save failed

    def delete_ion_list(self):
        # ... (Your existing delete logic is fine, keep it as is) ...
        ion_list_name = self.view.comboBoxIonLists.currentText()
        msgBox = QtWidgets.QMessageBox()
        msgBox.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        msgBox.setText(
            f'Are you sure you want to delete the ion list "{ion_list_name}"? This cannot be undone.'
        )
        msgBox.setStandardButtons(
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No
        )
        msgBox.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
        if msgBox.exec() == QtWidgets.QMessageBox.StandardButton.Yes:
            try:
                config_path = Path(__file__).parent.parent / "config.json"
                with open(config_path, "r+") as f:
                    config = json.load(f)
                    if ion_list_name in config:
                        config.pop(ion_list_name)
                        f.seek(0)
                        json.dump(config, f, indent=4)
                        f.truncate()

                self.view.comboBoxIonLists.clear()
                self.view.comboBoxIonLists.addItem("Create new ion list...")
                self.view.comboBoxIonLists.addItems(list(config.keys()))
                self.view.statusbar.showMessage(
                    f'{datetime.now().strftime("%d/%m/%Y %H:%M:%S")} -- Deleted ion list: "{ion_list_name}".',
                    5000,
                )
            except Exception as e:
                print(f"Error deleting ion list: {e}")


class ClearSelectionCommand(QtGui.QUndoCommand):
    def __init__(self, table):
        super().__init__()
        self.table = table
        self.items = table.selectedItems()
        self.texts = [item.text() for item in self.items]

    def redo(self):
        for item in self.items:
            item.setText("")

    def undo(self):
        for item, text in zip(self.items, self.texts):
            item.setText(text)


class PasteFromClipboardCommand(QtGui.QUndoCommand):
    def __init__(self, table):
        super().__init__()
        self.table = table
        self.clipboard_text = QtWidgets.QApplication.clipboard().text()
        self.current_row = table.currentRow()
        self.current_col = table.currentColumn()
        self.items = []
        self.redo()

    def redo(self):
        rows = self.clipboard_text.splitlines()
        row_index = self.current_row
        col_index = self.current_col
        for row_data in rows:
            columns = row_data.split("\t")
            col_index = self.current_col
            for value in columns:
                item = QtWidgets.QTableWidgetItem(value)
                self.table.setItem(row_index, col_index, item)
                self.items.append(item)
                col_index += 1
            row_index += 1

    def undo(self):
        for item in reversed(self.items):
            self.table.takeItem(self.table.row(item), self.table.column(item))


class CopyCommand(QtGui.QUndoCommand):
    def __init__(self, table):
        super().__init__()
        self.table = table
        self.clipboard_text = ""
        self.items = table.selectedIndexes()
        self.redo()

    def redo(self):
        try:
            self.clipboard_text = "\t".join([str(item.data()) for item in self.items])
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.setText(self.clipboard_text)
        except TypeError:
            pass

    def undo(self):
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText("")


class InsertRowCommand(QtGui.QUndoCommand):
    def __init__(self, table, row):
        super().__init__()
        self.table = table
        self.row = row

    def redo(self):
        self.table.insertRow(self.row)

    def undo(self):
        self.table.removeRow(self.row)


class SetItemCommand(QtGui.QUndoCommand):
    def __init__(self, table, row, col, value):
        super().__init__()
        self.table = table
        self.row = row
        self.col = col
        self.value = value
        self.old_value = table.item(row, col).text() if table.item(row, col) else ""

    def redo(self):
        try:
            item = QtWidgets.QTableWidgetItem(self.value)
        except Exception:
            item = None
        if item is None:
            item = QtWidgets.QTableWidgetItem(self.value)
            self.table.setItem(self.row, self.col, item)
        else:
            item.setText(self.value)

    def undo(self):
        item = self.table.item(self.row, self.col)
        if item is None:
            self.table.takeItem(self.row, self.col)
        else:
            item.setText(self.old_value)


class UnifiedResultsTable(GenericTable):
    """
    Unified table widget that combines the functionality of tableWidget_files and tableWidget_concentrations.
    Shows file names, calibration options, concentrations, and ion intensities in a single scrollable table.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("unifiedResultsTable")
        self.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        # Enable horizontal scrolling
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        self.horizontalHeader().setStretchLastSection(False)

        # Store compound information for dynamic column generation
        self.compounds = []
        self.file_data = {}

    def contextMenuEvent(self, event):
        """
        Override context menu to disable row deletion while preserving other functionality.
        """
        self.menu = QtWidgets.QMenu(self)

        # Keep useful actions but remove row deletion
        select_all_action = QtGui.QAction(
            QtGui.QIcon.fromTheme("edit-select-all"), "(⌘+A) Select All", self
        )
        select_all_action.triggered.connect(self.select_all)
        self.menu.addAction(select_all_action)

        copy_action = QtGui.QAction(
            QtGui.QIcon.fromTheme("edit-copy"), "(⌘+C) Copy", self
        )
        copy_action.triggered.connect(self.copy)
        self.menu.addAction(copy_action)

        paste_action = QtGui.QAction(
            QtGui.QIcon.fromTheme("edit-paste"), "(⌘+V) Paste", self
        )
        paste_action.triggered.connect(self.paste_from_clipboard)
        self.menu.addAction(paste_action)

        undo_action = QtGui.QAction(
            QtGui.QIcon.fromTheme("edit-undo"), "(⌘+Z) Undo", self
        )
        undo_action.triggered.connect(self.undoStack.undo)
        self.menu.addAction(undo_action)

        redo_action = QtGui.QAction(
            QtGui.QIcon.fromTheme("edit-redo"), "(⌘+U) Redo", self
        )
        redo_action.triggered.connect(self.undoStack.redo)
        self.menu.addAction(redo_action)

        self.menu.popup(QtGui.QCursor.pos())

    def keyPressEvent(self, event):
        """
        Override key press events to disable row deletion while preserving other shortcuts.
        """
        if event.key() == Qt.Key.Key_V and (
            event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
        ):
            self.paste_from_clipboard()
        elif event.key() == Qt.Key.Key_A and (
            event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
        ):
            self.select_all()
        elif event.key() == Qt.Key.Key_C and (
            event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
        ):
            self.copy()
        elif event.key() == Qt.Key.Key_Z and (
            event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
        ):
            self.undoStack.undo()
        elif event.key() == Qt.Key.Key_U and (
            event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
        ):
            self.undoStack.redo()
        # Note: Deliberately NOT handling Delete/Backspace keys to prevent row deletion
        else:
            # Call QTableWidget's keyPressEvent directly to skip GenericTable's row deletion
            QtWidgets.QTableWidget.keyPressEvent(self, event)

    def setup_columns(self, compound):
        """
        Set up the table columns based on a single compound and its ions.

        Parameters:
        -----------
        compound : Compound
            Single Compound object containing ion information
        """
        self.current_compound = compound

        # Base columns: File, Concentration
        base_headers = ["File", "Concentration"]

        # Dynamic columns for the current compound's ions
        ion_headers = []
        if compound:
            ion_keys = list(compound.ions.keys())
            for i, ion_key in enumerate(ion_keys):
                label = compound.get_ion_label(i)
                # Add MS intensity column for each ion
                ion_headers.append(f"{label} (MS)")
                # Add LC intensity column for each ion if available
                ion_headers.append(f"{label} (LC)")

        all_headers = base_headers + ion_headers

        self.setColumnCount(len(all_headers))
        self.setHorizontalHeaderLabels(all_headers)

        # Set appropriate column widths
        self.setColumnWidth(0, 200)  # File column
        self.setColumnWidth(1, 150)  # Concentration column

        # Set ion columns to reasonable width
        for i in range(2, len(all_headers)):
            self.setColumnWidth(i, 120)

    def populate_data(self, file_concentrations, ms_measurements, current_compound):
        """
        Populate the table with file data, concentrations, and ion intensities for the current compound.

        Parameters:
        -----------
        file_concentrations : list
            List of [filename, concentration] pairs
        ms_measurements : dict
            Dictionary of MS measurement objects
        current_compound : Compound
            The currently selected compound to display data for
        """
        self.file_data = {}

        # Clear existing data but preserve row count and basic structure
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                if col >= 2:  # Only clear ion data columns, preserve file/concentration
                    self.setItem(row, col, None)

        # If no rows exist yet, set them up
        if self.rowCount() != len(file_concentrations):
            self.setRowCount(len(file_concentrations))

        for row, (filename, concentration) in enumerate(file_concentrations):
            # Store file data for later retrieval
            self.file_data[row] = filename

            # Column 0: File name (only set if not already set)
            if not self.item(row, 0):
                file_item = QtWidgets.QTableWidgetItem(filename)
                file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.setItem(row, 0, file_item)

            # Column 1: Concentration (editable) - only set if not already present
            if not self.item(row, 1):
                conc_item = QtWidgets.QTableWidgetItem(concentration or "")
                self.setItem(row, 1, conc_item)

            # Dynamic columns: Ion intensities for current compound only
            if current_compound and hasattr(current_compound, "ions"):
                col_index = 2
                ms_file = ms_measurements.get(filename)

                if ms_file and ms_file.xics:
                    # Find the matching compound in the MS file
                    ms_compound = None
                    for xic_compound in ms_file.xics:
                        if xic_compound.name == current_compound.name:
                            ms_compound = xic_compound
                            break

                    if ms_compound:
                        for ion_idx, ion in enumerate(current_compound.ions.keys()):
                            # MS Intensity column
                            if ion in ms_compound.ions:
                                ms_intensity = ms_compound.ions[ion]["MS Intensity"]
                                if ms_intensity is not None:
                                    import numpy as np

                                    ms_value = f"{np.format_float_scientific(np.round(np.sum(ms_intensity), 0), precision=2)}"
                                else:
                                    ms_value = "N/A"
                            else:
                                ms_value = "N/A"

                            ms_item = QtWidgets.QTableWidgetItem(ms_value)
                            ms_item.setFlags(
                                ms_item.flags() & ~Qt.ItemFlag.ItemIsEditable
                            )
                            self.setItem(row, col_index, ms_item)
                            col_index += 1

                            # LC Intensity column
                            if ion in ms_compound.ions:
                                lc_intensity = ms_compound.ions[ion]["LC Intensity"]
                                lc_value = (
                                    str(lc_intensity)
                                    if lc_intensity is not None
                                    else "N/A"
                                )
                            else:
                                lc_value = "N/A"

                            lc_item = QtWidgets.QTableWidgetItem(lc_value)
                            lc_item.setFlags(
                                lc_item.flags() & ~Qt.ItemFlag.ItemIsEditable
                            )
                            self.setItem(row, col_index, lc_item)
                            col_index += 1
                    else:
                        # Fill with N/A if compound not found in MS file
                        for ion in current_compound.ions.keys():
                            for _ in range(2):  # MS and LC columns
                                na_item = QtWidgets.QTableWidgetItem("N/A")
                                na_item.setFlags(
                                    na_item.flags() & ~Qt.ItemFlag.ItemIsEditable
                                )
                                self.setItem(row, col_index, na_item)
                                col_index += 1
                else:
                    # Fill with N/A if no MS file found
                    for ion in current_compound.ions.keys():
                        for _ in range(2):  # MS and LC columns
                            na_item = QtWidgets.QTableWidgetItem("N/A")
                            na_item.setFlags(
                                na_item.flags() & ~Qt.ItemFlag.ItemIsEditable
                            )
                            self.setItem(row, col_index, na_item)
                            col_index += 1

    def get_calibration_files(self):
        """
        Get files with concentrations for calibration.

        Returns:
        --------
        dict : Dictionary mapping filename to concentration for files with non-empty concentrations
        """
        selected_files = {}
        for row in range(self.rowCount()):
            filename_item = self.item(row, 0)
            concentration_item = self.item(row, 1)
            if filename_item and concentration_item:
                filename = filename_item.text()
                concentration = concentration_item.text()
                if concentration and concentration.strip():
                    selected_files[filename] = concentration
        return selected_files

    def get_selected_file(self):
        """
        Get the currently selected file for MS2 display.

        Returns:
        --------
        str : Filename of the selected row, or None if no selection
        """
        selected_rows = self.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            return self.item(row, 0).text()
        elif self.rowCount() > 0:
            return self.item(0, 0).text()
        return None

    def update_concentrations(self, compounds):
        """
        Update the concentration display after calibration.

        Parameters:
        -----------
        compounds : list
            List of Compound objects with updated concentration information
        """
        # This method can be called to refresh concentration displays
        # after calibration calculations are complete
        pass

    def update_ion_values(self, filename, compound):
        """
        Update all ion columns for a specific file based on a Compound object.
        Applies a temporary visual highlight to changed cells.

        Parameters
        ----------
        filename : str
            The name of the file to update (must match the File column).
        compound : Compound
            The compound object containing updated peak area data.
        """

        matching_items = self.findItems(filename, Qt.MatchFlag.MatchExactly)
        if not matching_items:
            raise AttributeError(
                "No matching entries for filename in UnifiedResultsTable."
            )

        # Ensure we found the item in column 0 (File Name)
        target_row = -1
        for item in matching_items:
            if item.column() == 0:
                target_row = item.row()
                break

        if target_row == -1:
            raise AttributeError(
                "No matching entries for filename in UnifiedResultsTable."
            )

        # 2. Iterate through all ions in the compound and update table
        ion_names = list(compound.ions.keys())

        for i, ion_name in enumerate(ion_names):
            ion_data = compound.ions[ion_name]

            # Calculate column indices:
            # Base offset is 2 (File, Conc). Each ion has 2 columns (MS, LC).
            ms_col = 2 + (i * 2)
            lc_col = ms_col + 1

            # --- Update MS Column ---
            # Extract baseline_corrected_area from the nested dictionary
            ms_area_data = ion_data.get("Integration Data")
            if isinstance(ms_area_data, dict):
                ms_val = ms_area_data.get("baseline_corrected_area")
                if ms_val is not None:
                    # Format: Scientific notation with 2 decimal places
                    new_text = f"{ms_val:.2e}"
                    self._update_and_highlight_cell(target_row, ms_col, new_text)

            # --- Update LC Column ---
            lc_val = ion_data.get("LC Intensity")
            if lc_val is not None:
                new_text = str(lc_val)
                self._update_and_highlight_cell(target_row, lc_col, new_text)

    def update_single_ion_value(self, filename: str, compound, ion_key: str):
        """
        Update a single ion's column for a specific file based on manual integration changes.
        Applies a temporary visual highlight to the changed cell.

        Parameters
        ----------
        filename : str
            The name of the file to update (must match the File column).
        compound : Compound
            The compound object containing updated peak area data.
        ion_key : str
            The specific ion key to update (as a string).
        """
        # Find the row for this filename
        matching_items = self.findItems(filename, Qt.MatchFlag.MatchExactly)
        if not matching_items:
            raise AttributeError(
                f"No matching entries for filename '{filename}' in UnifiedResultsTable."
            )

        # Ensure we found the item in column 0 (File Name)
        target_row = -1
        for item in matching_items:
            if item.column() == 0:
                target_row = item.row()
                break

        if target_row == -1:
            raise AttributeError(
                f"No matching entries for filename '{filename}' in column 0."
            )

        # Find the ion index in the compound
        ion_names = list(compound.ions.keys())
        ion_index = -1
        actual_ion_key = None

        for i, ion_name in enumerate(ion_names):
            if str(ion_name) == ion_key:
                ion_index = i
                actual_ion_key = ion_name
                break

        if ion_index == -1 or actual_ion_key is None:
            raise AttributeError(
                f"Ion key '{ion_key}' not found in compound '{compound.name}'."
            )

        ion_data = compound.ions[actual_ion_key]

        # Calculate column index:
        # Base offset is 2 (File, Conc). Each ion has 2 columns (MS, LC).
        ms_col = 2 + (ion_index * 2)

        # Update MS Column with the new integration data
        ms_area_data = ion_data.get("Integration Data")
        if isinstance(ms_area_data, dict):
            ms_val = ms_area_data.get("baseline_corrected_area")
            if ms_val is not None:
                new_text = f"{ms_val:.2e}"
                self._update_and_highlight_cell(target_row, ms_col, new_text)

    def _update_and_highlight_cell(self, row, col, new_text):
        """
        Helper to update cell text and apply a temporary background color.
        """
        item = self.item(row, col)

        # Create item if it doesn't exist (e.g., if cell was previously empty)
        if not item:
            item = QtWidgets.QTableWidgetItem()
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.setItem(row, col, item)

        # Only update and highlight if the text actually changed or if it's a forced update
        # (Optional: remove the check if you want to highlight even if values are identical)
        if item.text() != new_text:
            item.setText(new_text)

            # --- Visual Cue Implementation ---
            # 1. Define highlight color (Soft Green)
            highlight_color = QtGui.QColor(200, 255, 200)

            # 2. Store original background to revert later
            # We use the table's default palette base color usually, or white
            original_brush = item.background()

            # 3. Apply highlight
            item.setBackground(highlight_color)

            # 4. Set timer to revert after 10 seconds (10000 ms)
            # IMPORTANT: Store row/col coordinates instead of item reference
            # to handle cases where the table may be cleared during the delay
            target_row, target_col = row, col
            table_ref = self  # Capture table reference

            def revert_background():
                """Safely revert background color, handling deleted items."""
                try:
                    # Verify table still exists and has this cell
                    if (
                        table_ref.rowCount() > target_row
                        and table_ref.columnCount() > target_col
                    ):
                        current_item = table_ref.item(target_row, target_col)
                        # Only revert if item exists and text matches (same item)
                        if current_item is not None and current_item.text() == new_text:
                            current_item.setBackground(original_brush)
                except (RuntimeError, AttributeError):
                    # Table or item was deleted, ignore
                    pass

            QtCore.QTimer.singleShot(10000, revert_background)


class ChromatogramPlotWidget(pg.PlotWidget):
    sigKeyPressed = QtCore.Signal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def keyPressEvent(self, ev):
        self.scene().keyPressEvent(ev)
        self.sigKeyPressed.emit(ev)


class LabelledSlider(QtWidgets.QWidget):
    """
    A widget that combines a QLabel, a QSlider, and another QLabel to display the current value.
    The slider works with floating-point values over a specified range.
    """

    valueChanged = QtCore.Signal(float)

    def __init__(self, label_text, values, default_val, parent=None):
        super().__init__(parent)
        self.values = values
        self.layout = QtWidgets.QHBoxLayout(self)
        self.label = QtWidgets.QLabel(label_text)
        self.slider = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        self.value_label = QtWidgets.QLabel(str(default_val))

        self.slider.setMinimum(0)
        self.slider.setMaximum(len(values) - 1)
        try:
            default_index = self.values.index(default_val)
            self.slider.setValue(default_index)
        except ValueError:
            self.slider.setValue(0)

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.slider)
        self.layout.addWidget(self.value_label)

        self.slider.valueChanged.connect(self.update_value_label)

    def update_value_label(self, index):
        value = self.values[index]
        self.value_label.setText(str(value))
        self.valueChanged.emit(value)

    def value(self):
        return self.values[self.slider.value()]


class ReadmeDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("README")
        self.resize(500, 400)

        layout = QtWidgets.QVBoxLayout(self)
        self.browser = QtWidgets.QTextBrowser()
        self.browser.setOpenExternalLinks(False)  # we handle links ourselves
        self.browser.setOpenLinks(False)
        layout.addWidget(self.browser)
        self.browser.anchorClicked.connect(self.open_link)
        self.load_readme_html(Path(__file__).parent / "README.html")

    def open_link(self, url: QtCore.QUrl):
        """Open the clicked link in the default web browser."""
        webbrowser.open(url.toString())

    def load_readme_html(self, filepath):
        """Load README HTML content from a file."""
        try:
            print("Reading from", filepath)
            html_content = filepath.read_text(encoding="utf-8")
        except FileNotFoundError:
            html_content = "<p><b>README file not found.</b></p>"
        self.browser.setHtml(html_content)


class MzRangeDialog(QtWidgets.QDialog):
    """Dialog for editing m/z integration boundaries per ion.

    Displays the current mass spectrum zoomed to one ion at a time with
    draggable boundary lines. Users switch between ions via a combo box
    and apply/reset ranges individually.

    Parameters
    ----------
    mzs : np.ndarray
        Spectrum m/z array.
    intensities : np.ndarray
        Spectrum intensity array.
    target_mz_values : list[float]
        Ion m/z values for this compound.
    ion_labels : list[str]
        Display labels (e.g. "[M+H]+").
    mass_accuracy : float
        Default mass accuracy for ±3x window.
    compound_name : str
        Compound name for the dialog title.
    existing_ranges : dict
        Previously applied ``{mz: (left, right)}`` overrides.
    parent : QWidget, optional
        Parent widget.
    """

    def __init__(
        self,
        mzs,
        intensities,
        target_mz_values,
        ion_labels,
        mass_accuracy,
        compound_name,
        existing_ranges=None,
        theoretical_spectrum=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Integration \u2014 {compound_name}")
        self.resize(700, 500)

        self._mzs = mzs
        self._intensities = intensities
        self._target_mz_values = target_mz_values
        self._ion_labels = ion_labels
        self._mass_accuracy = mass_accuracy
        self._compound_name = compound_name
        self._theoretical_spectrum = theoretical_spectrum

        # Internal state: {mz: (left, right)} for all ions
        self._ranges = dict(existing_ranges) if existing_ranges else {}
        self._current_ion_idx = 0
        self._left_line = None
        self._right_line = None
        self._theo_items = []  # Tracked theoretical overlay items

        self._build_ui()
        self._plot_spectrum()
        self._update_ion_view()

    def _build_ui(self):
        """Build the dialog layout."""
        layout = QtWidgets.QVBoxLayout(self)

        # Ion selector combo
        combo_layout = QtWidgets.QHBoxLayout()
        combo_layout.addWidget(QtWidgets.QLabel("Ion:"))
        self._ion_combo = QtWidgets.QComboBox()
        for i, (mz, label) in enumerate(zip(self._target_mz_values, self._ion_labels)):
            self._ion_combo.addItem(f"{label} ({mz:.4f})")
        self._ion_combo.currentIndexChanged.connect(self._on_ion_changed)
        combo_layout.addWidget(self._ion_combo)
        combo_layout.addStretch()
        layout.addLayout(combo_layout)

        # Plot widget
        self._plot_widget = pg.PlotWidget()
        self._plot_widget.setBackground("w")
        self._plot_widget.setMouseEnabled(x=True, y=False)

        # Auto Y-range on X-range change
        def _auto_y(vb):
            vb.enableAutoRange(axis="y")
            vb.setAutoVisible(y=True)

        self._plot_widget.getPlotItem().getViewBox().sigXRangeChanged.connect(_auto_y)

        layout.addWidget(self._plot_widget)

        # Boundary value display labels
        boundary_layout = QtWidgets.QHBoxLayout()
        self._left_label = QtWidgets.QLabel("Left: ---")
        self._right_label = QtWidgets.QLabel("Right: ---")
        boundary_layout.addWidget(self._left_label)
        boundary_layout.addStretch()
        boundary_layout.addWidget(self._right_label)
        layout.addLayout(boundary_layout)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self._apply_btn = QtWidgets.QPushButton("Apply")
        self._apply_btn.clicked.connect(self._on_apply)
        self._reset_btn = QtWidgets.QPushButton("Reset")
        self._reset_btn.clicked.connect(self._on_reset)
        self._close_btn = QtWidgets.QPushButton("Close")
        self._close_btn.clicked.connect(self.accept)

        btn_layout.addWidget(self._apply_btn)
        btn_layout.addWidget(self._reset_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self._close_btn)
        layout.addLayout(btn_layout)

    def _plot_spectrum(self):
        """Plot the full spectrum on the internal PlotWidget."""
        from ui.plotting import PlotStyle

        PlotStyle.apply_standard_style(
            self._plot_widget,
            title=f"Spectrum \u2014 {self._compound_name}",
            x_label="m/z",
            y_label="Intensity (a.u.)",
        )

        if len(self._mzs) < 500:
            graph_item = pg.BarGraphItem(
                x=self._mzs,
                height=self._intensities,
                width=0.2,
                pen=mkPen("#3c5488ff", width=1),
                brush=pg.mkBrush("#3c5488ff"),
            )
            self._plot_widget.addItem(graph_item)
        else:
            self._plot_widget.plot(
                self._mzs,
                self._intensities,
                pen=mkPen("#3c5488ff", width=1),
            )

    def _default_bounds(self, mz):
        """Compute default ±3x mass_accuracy bounds for a target m/z."""
        delta = mz * self._mass_accuracy * 3
        return (mz - delta, mz + delta)

    def _update_ion_view(self):
        """Update the view for the currently selected ion."""
        from ui.plotting import PlotStyle

        idx = self._current_ion_idx
        if idx >= len(self._target_mz_values):
            return

        mz = self._target_mz_values[idx]
        color = PlotStyle.PALETTE[idx % len(PlotStyle.PALETTE)]

        # Get current or default bounds
        if mz in self._ranges:
            left_pos, right_pos = self._ranges[mz]
        else:
            left_pos, right_pos = self._default_bounds(mz)

        # Remove old lines
        plot_item = self._plot_widget.getPlotItem()
        if self._left_line is not None:
            plot_item.removeItem(self._left_line)
            self._left_line = None
        if self._right_line is not None:
            plot_item.removeItem(self._right_line)
            self._right_line = None

        # Create boundary lines
        line_pen = mkPen(color, width=2)
        hover_pen = mkPen("red", width=2)

        self._left_line = plot_item.addLine(
            x=left_pos,
            pen=line_pen,
            hoverPen=hover_pen,
            movable=True,
            markers=[("|>", 0.5, 10.0)],
            name=f"{mz}_left",
        )

        self._right_line = plot_item.addLine(
            x=right_pos,
            pen=line_pen,
            hoverPen=hover_pen,
            movable=True,
            markers=[("<|", 0.5, 10.0)],
            name=f"{mz}_right",
        )

        # Connect signals to update boundary labels
        self._left_line.sigPositionChanged.connect(self._update_boundary_labels)
        self._right_line.sigPositionChanged.connect(self._update_boundary_labels)

        # Zoom to ion region (±2 Da)
        self._plot_widget.setXRange(mz - 2.0, mz + 2.0)

        # Update labels with initial values
        self._update_boundary_labels()

        # Overlay theoretical spectrum for current ion
        self._plot_theoretical_for_current_ion()

    def _plot_theoretical_for_current_ion(self):
        """Overlay theoretical isotopic peaks for the currently selected ion."""
        # Clean up previous theoretical items
        plot_item = self._plot_widget.getPlotItem()
        for item in self._theo_items:
            try:
                plot_item.removeItem(item)
            except Exception:
                pass
        self._theo_items.clear()

        if self._theoretical_spectrum is None:
            return

        idx = self._current_ion_idx
        if idx >= len(self._ion_labels):
            return

        # Match ion label to adduct key
        label = self._ion_labels[idx]
        adduct = self._theoretical_spectrum.adducts.get(label)
        if adduct is None:
            return

        # Scale abundances relative to experimental data in view window
        mz = self._target_mz_values[idx]
        view_mask = (self._mzs >= mz - 2.0) & (self._mzs <= mz + 2.0)
        if np.any(view_mask):
            max_exp = np.max(self._intensities[view_mask])
        else:
            max_exp = 1.0
        scaled_heights = adduct.abundances * max_exp * 0.9

        # Plot as bar graph
        bar_item = pg.BarGraphItem(
            x=adduct.mz_values,
            height=scaled_heights,
            width=0.1,
            pen=mkPen("#d95f02", width=1),
            brush=pg.mkBrush(217, 95, 2, 80),
        )
        plot_item.addItem(bar_item)
        self._theo_items.append(bar_item)

        # Add "Theoretical" text label above the monoisotopic peak
        text_item = pg.TextItem("Theoretical", color="#d95f02", anchor=(0.5, 1.0))
        text_item.setPos(adduct.monoisotopic_mz, scaled_heights[0] * 1.05)
        plot_item.addItem(text_item)
        self._theo_items.append(text_item)

    def _update_boundary_labels(self):
        """Update the boundary value labels when lines are moved."""
        if self._left_line is None or self._right_line is None:
            return
        left_val = self._left_line.value()
        right_val = self._right_line.value()
        self._left_label.setText(f"Left: {left_val:.4f}")
        self._right_label.setText(f"Right: {right_val:.4f}")

    def _on_ion_changed(self, index):
        """Handle ion combo box selection change."""
        self._current_ion_idx = index
        self._update_ion_view()

    def _on_apply(self):
        """Store current line positions in _ranges."""
        if self._left_line is None or self._right_line is None:
            return

        idx = self._current_ion_idx
        if idx >= len(self._target_mz_values):
            return

        mz = self._target_mz_values[idx]
        left_pos = self._left_line.value()
        right_pos = self._right_line.value()
        self._ranges[mz] = (left_pos, right_pos)

    def _on_reset(self):
        """Remove custom range for current ion, reset lines to defaults."""
        idx = self._current_ion_idx
        if idx >= len(self._target_mz_values):
            return

        mz = self._target_mz_values[idx]
        if mz in self._ranges:
            del self._ranges[mz]

        # Reset lines to default positions
        left_pos, right_pos = self._default_bounds(mz)
        if self._left_line is not None:
            self._left_line.setValue(left_pos)
        if self._right_line is not None:
            self._right_line.setValue(right_pos)

    def get_ranges(self):
        """Return the applied custom ranges.

        Returns
        -------
        dict
            ``{mz_float: (left, right)}`` for ions with custom ranges.
        """
        return dict(self._ranges)
