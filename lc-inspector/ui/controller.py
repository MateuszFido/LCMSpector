from calculation.workers import Worker, WorkerSignals
from multiprocessing import Manager
import logging, traceback
logger = logging.getLogger(__name__)

class Controller:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.view.controller = self
        self.model.controller = self
        self.view.processButton.clicked.connect(self.process_data)
        self.view.comboBox_currentfile.currentIndexChanged.connect(self.display_selected_plots)
        self.view.calibrateButton.clicked.connect(self.calibrate)
        self.view.comboBoxChooseCompound.currentIndexChanged.connect(self.view.display_calibration_curve)
        self.view.comboBoxChooseCompound.currentIndexChanged.connect(self.view.display_concentrations)

    def load_lc_data(self):
        pass

    def load_ms_data(self):
        pass

    def process_data(self):
        self.model.compounds = self.view.ionTable.get_items()
        if (hasattr(self.model, 'ms_measurements') and hasattr(self.model, 'lc_measurements')) or (hasattr(self.model, 'lc_measurements') and hasattr(self.model, 'annotations')):
            if not self.model.lc_measurements:
                self.view.show_critical_error("Please load LC files and either corresponding MS files or manual annotations before processing.")
                return
            if not self.model.compounds or not self.model.compounds[0].ions:
                self.view.show_critical_error("Please define m/z values to trace or choose from the predefined lists before processing.")
                return
            
            logger.info("Starting the processing...")
            # Handle pre-processing UI events
            self.view.processButton.setEnabled(False)
            self.view.statusbar.showMessage("Loading data into memory... [Step 1/3]")
            self.view.progressBar.setVisible(True)
            self.view.progressLabel.setVisible(True)
            self.view.progressLabel.setText("0%")
            self.view.progressBar.setValue(0)
            # Start processing
            self.model.lc_measurements, self.model.ms_measurements = self.model.process_data()
        else:
            self.view.show_critical_error("Nothing to process. Please load LC files and either corresponding MS files or manual annotations before proceeding.")
        
        self.on_processing_finished()


    def on_processing_finished(self):
        self.view.progressBar.setVisible(False)
        self.view.progressLabel.setVisible(False)
        self.view.processButton.setEnabled(True)
        self.view.statusbar.showMessage("Finished.", 5000)

        self.view.tabWidget.setTabEnabled(self.view.tabWidget.indexOf(self.view.tabResults), True)
        self.view.tabWidget.setCurrentIndex(self.view.tabWidget.indexOf(self.view.tabResults))
        self.view.tabWidget.setTabEnabled(self.view.tabWidget.indexOf(self.view.tabQuantitation), True)

        # Resize view to fit the screen
        self.view.showMaximized()
        self.update_filenames()
    
    def update_filenames(self):
        filenames = list(self.model.lc_measurements.keys())
        self.view.update_combo_box(filenames)
        # Grab the return values of extract_concentration() for every file in lc_measurements
        concentrations = [[file, self.model.lc_measurements[file].extract_concentration()] for file in filenames]
        self.view.update_table_quantitation(concentrations)

    def display_selected_plots(self):
        selected_file = self.view.comboBox_currentfile.currentText()
        try:
            lc_file, ms_file = self.model.get_plots(selected_file)
        except Exception as e:
            logger.error(f"Error displaying plots for file {selected_file}: {traceback.format_exc()}")
        self.view.display_plots(lc_file, ms_file)  # Update the view with the selected plots

    def calibrate(self):
        selected_files = self.view.get_calibration_files()
        if selected_files:
            try:
                self.model.calibrate(selected_files)
            except Exception as e:
                logger.error(f"Error calibrating files: {traceback.format_exc()}")
                return
        else:
            logger.error("No files selected for calibration.")
        self.view.comboBoxChooseCompound.setEnabled(True)
        self.view.update_choose_compound(self.model.compounds)

        