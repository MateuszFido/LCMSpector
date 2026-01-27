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
        MainWindow.browseMS.setText(_translate("MainWindow", "Browse"))
        MainWindow.browseAnnotations.setText(_translate("MainWindow", "Browse"))
        MainWindow.labelAnnotations.setText(
            _translate("MainWindow", "Annotations (.txt)")
        )
        MainWindow.labelLCdata.setText(
            _translate("MainWindow", "Chromatography data (.txt)")
        )
        MainWindow.labelMSdata.setText(_translate("MainWindow", "MS data (.mzML)"))
        MainWindow.labelIonList.setText(
            _translate("MainWindow", "Targeted m/z values:")
        )
        MainWindow.comboBoxIonLists.setToolTip(
            _translate(
                "MainWindow",
                "Choose an ion list from the list of ion lists provided with the software",
            )
        )
        MainWindow.processButton.setText(_translate("MainWindow", "Process"))
        MainWindow.tabWidget.setTabText(
            MainWindow.tabWidget.indexOf(MainWindow.tabUpload),
            _translate("MainWindow", "Upload"),
        )
        MainWindow.tabResults.label_results_currentfile.setText(
            _translate("MainWindow", "Current file:")
        )
        MainWindow.tabWidget.setTabText(
            MainWindow.tabWidget.indexOf(MainWindow.tabResults),
            _translate("MainWindow", "Results"),
        )
        MainWindow.label_curr_compound.setText(_translate("MainWindow", "Compound:"))
        MainWindow.label_calibrate.setText(
            _translate("MainWindow", "Select the files to be used for calibration.")
        )
        MainWindow.calibrateButton.setText(_translate("MainWindow", "Calculate"))
        MainWindow.tabWidget.setTabText(
            MainWindow.tabWidget.indexOf(MainWindow.tabQuantitation),
            _translate("MainWindow", "Quantitation"),
        )
        MainWindow.menubar.file_menu.setTitle(_translate("MainWindow", "File"))
        MainWindow.menubar.view_menu.setTitle(_translate("MainWindow", "View"))
        MainWindow.menubar.help_menu.setTitle(_translate("MainWindow", "Help"))

        MainWindow.menubar.action_open.setText(_translate("MainWindow", "Open"))
        MainWindow.menubar.action_open.setShortcut(_translate("MainWindow", "Ctrl+O"))

        MainWindow.menubar.action_save.setText(_translate("MainWindow", "Save"))
        MainWindow.menubar.action_save.setShortcut(_translate("MainWindow", "Ctrl+S"))

        MainWindow.menubar.action_exit.setText(_translate("MainWindow", "Exit"))
        MainWindow.menubar.action_exit.setShortcut(_translate("MainWindow", "Ctrl+W"))

        MainWindow.menubar.action_export.setText(_translate("MainWindow", "Export"))
        MainWindow.menubar.action_export.setShortcut(_translate("MainWindow", "Ctrl+E"))

        MainWindow.menubar.action_about.setText(_translate("MainWindow", "About"))
        MainWindow.menubar.action_about.setShortcut(_translate("MainWindow", "F1"))

        MainWindow.menubar.action_prefs.setText(_translate("MainWindow", "Preferences"))

        MainWindow.menubar.action_readme.setText(_translate("MainWindow", "Readme"))
        MainWindow.menubar.action_readme.setShortcut(_translate("MainWindow", "F10"))

        MainWindow.menubar.action_logs.setText(_translate("MainWindow", "Logs"))
        MainWindow.menubar.action_logs.setShortcut(_translate("MainWindow", "F11"))

        MainWindow.button_clear_LC.setText(_translate("MainWindow", "Clear"))
        MainWindow.button_clear_MS.setText(_translate("MainWindow", "Clear"))
        MainWindow.button_clear_ion_list.setText(_translate("MainWindow", "Clear"))
        MainWindow.button_save_ion_list.setText(_translate("MainWindow", "Save"))
        MainWindow.button_delete_ion_list.setText(_translate("MainWindow", "Delete"))

    except RuntimeError:
        logger.error("Error retranslating ui:", traceback.format_exc())
    except AttributeError:
        logger.error("Error retranslating ui:", traceback.format_exc())
