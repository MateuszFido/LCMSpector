from PySide6 import QtCore, QtGui
import os
import logging
import traceback

logger = logging.getLogger(__name__)


def retranslateUi(MainWindow):
    """
    Set the text of the UI elements according to the current locale.

    Parameters
    ----------
        MainWindow: The main window object for which the UI is being set up.
    """
    _translate = QtCore.QCoreApplication.translate
    MainWindow.setWindowTitle(_translate("MainWindow", "LCMSpector"))
    MainWindow.setWindowIcon(
        QtGui.QIcon(os.path.join(os.path.dirname(__file__), "resources", "icon.icns"))
    )
    try:
        # Upload tab widgets
        if hasattr(MainWindow, "browseLC"):
            MainWindow.browseLC.setText(_translate("MainWindow", "Browse"))
        MainWindow.comboBoxChangeMode.setItemText(
            0, _translate("MainWindow", "LC/GC-MS")
        )
        MainWindow.comboBoxChangeMode.setItemText(
            1, _translate("MainWindow", "MS Only")
        )
        MainWindow.comboBoxChangeMode.setItemText(
            2, _translate("MainWindow", "Chromatography Only")
        )
        if hasattr(MainWindow, "browseMS"):
            MainWindow.browseMS.setText(_translate("MainWindow", "Browse"))
        if hasattr(MainWindow, "browseAnnotations"):
            MainWindow.browseAnnotations.setText(_translate("MainWindow", "Browse"))
        if hasattr(MainWindow, "labelAnnotations"):
            MainWindow.labelAnnotations.setText(
                _translate("MainWindow", "Annotations (.txt)")
            )
        if hasattr(MainWindow, "labelLCdata"):
            MainWindow.labelLCdata.setText(
                _translate("MainWindow", "Chromatography data (.txt)")
            )
        if hasattr(MainWindow, "labelMSdata"):
            MainWindow.labelMSdata.setText(_translate("MainWindow", "MS data (.mzML)"))
        if hasattr(MainWindow, "labelIonList"):
            MainWindow.labelIonList.setText(
                _translate("MainWindow", "Targeted m/z values:")
            )
        if hasattr(MainWindow, "comboBoxIonLists"):
            MainWindow.comboBoxIonLists.setToolTip(
                _translate(
                    "MainWindow",
                    "Choose an ion list from the list of ion lists provided with the software",
                )
            )
        MainWindow.processButton.setText(_translate("MainWindow", "Process"))

        # Tab titles
        MainWindow.tabWidget.setTabText(
            MainWindow.tabWidget.indexOf(MainWindow.tabUpload),
            _translate("MainWindow", "Upload"),
        )
        MainWindow.tabWidget.setTabText(
            MainWindow.tabWidget.indexOf(MainWindow.tabResults),
            _translate("MainWindow", "Results"),
        )
        MainWindow.tabWidget.setTabText(
            MainWindow.tabWidget.indexOf(MainWindow.tabQuantitation),
            _translate("MainWindow", "Quantitation"),
        )

        # Results tab widgets - access through results_tab
        if hasattr(MainWindow, "results_tab") and hasattr(
            MainWindow.results_tab, "label_results_currentfile"
        ):
            MainWindow.results_tab.label_results_currentfile.setText(
                _translate("MainWindow", "Current file:")
            )

        # Quantitation tab widgets - access through quantitation_tab
        if hasattr(MainWindow, "quantitation_tab"):
            quant = MainWindow.quantitation_tab
            if hasattr(quant, "label_compound"):
                quant.label_compound.setText(_translate("MainWindow", "Compound:"))
            if hasattr(quant, "label_calibrate"):
                quant.label_calibrate.setText(
                    _translate(
                        "MainWindow",
                        'Select files with known concentrations or enter them manually, and click "Calculate".',
                    )
                )
            if hasattr(quant, "calibrateButton"):
                quant.calibrateButton.setText(_translate("MainWindow", "Calculate"))
            if hasattr(quant, "button_apply_integration"):
                quant.button_apply_integration.setText(
                    _translate("MainWindow", "Apply")
                )
            if hasattr(quant, "button_recalculate_integration"):
                quant.button_recalculate_integration.setText(
                    _translate("MainWindow", "Recalculate")
                )
            if hasattr(quant, "button_reset_integration"):
                quant.button_reset_integration.setText(
                    _translate("MainWindow", "Reset")
                )

        # Menu bar
        MainWindow.menuFile.setTitle(_translate("MainWindow", "File"))
        MainWindow.menuEdit.setTitle(_translate("MainWindow", "View"))
        MainWindow.menuHelp.setTitle(_translate("MainWindow", "Help"))

        MainWindow.actionOpen.setText(_translate("MainWindow", "Open"))
        MainWindow.actionOpen.setShortcut(_translate("MainWindow", "Ctrl+O"))

        MainWindow.actionSave.setText(_translate("MainWindow", "Save"))
        MainWindow.actionSave.setShortcut(_translate("MainWindow", "Ctrl+S"))

        MainWindow.actionExit.setText(_translate("MainWindow", "Exit"))
        MainWindow.actionExit.setShortcut(_translate("MainWindow", "Ctrl+W"))

        MainWindow.actionExport.setText(_translate("MainWindow", "Export"))
        MainWindow.actionExport.setShortcut(_translate("MainWindow", "Ctrl+E"))

        MainWindow.actionAbout.setText(_translate("MainWindow", "About"))
        MainWindow.actionAbout.setShortcut(_translate("MainWindow", "F1"))

        MainWindow.actionPreferences.setText(_translate("MainWindow", "Preferences"))

        MainWindow.actionReadme.setText(_translate("MainWindow", "Readme"))
        MainWindow.actionReadme.setShortcut(_translate("MainWindow", "F10"))

        MainWindow.actionLogs.setText(_translate("MainWindow", "Logs"))
        MainWindow.actionLogs.setShortcut(_translate("MainWindow", "F11"))

        # Clear/Save/Delete buttons (if they exist)
        if hasattr(MainWindow, "button_clear_LC"):
            MainWindow.button_clear_LC.setText(_translate("MainWindow", "Clear"))
        if hasattr(MainWindow, "button_clear_MS"):
            MainWindow.button_clear_MS.setText(_translate("MainWindow", "Clear"))
        if hasattr(MainWindow, "button_clear_ion_list"):
            MainWindow.button_clear_ion_list.setText(_translate("MainWindow", "Clear"))
        if hasattr(MainWindow, "button_save_ion_list"):
            MainWindow.button_save_ion_list.setText(_translate("MainWindow", "Save"))
        if hasattr(MainWindow, "button_delete_ion_list"):
            MainWindow.button_delete_ion_list.setText(
                _translate("MainWindow", "Delete")
            )

    except RuntimeError:
        logger.error("Error retranslating ui: %s", traceback.format_exc())
    except AttributeError:
        logger.error("Error retranslating ui: %s", traceback.format_exc())
