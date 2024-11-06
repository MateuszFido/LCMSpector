from utils.threading import Worker, AnnotationWorker
from multiprocessing import Manager
import gc

class Controller:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.view.controller = self

        self.view.browseLC.clicked.connect(self.load_lc_data)
        self.view.browseMS.clicked.connect(self.load_ms_data)
        self.view.processButton.clicked.connect(self.process_data)
        self.view.comboBox_currentfile.currentIndexChanged.connect(self.display_selected_plots)

    def load_lc_data(self):
        pass

    def load_ms_data(self):
        pass

    def process_data(self):
        if (hasattr(self.model, 'ms_measurements') and hasattr(self.model, 'lc_measurements')) or (hasattr(self.model, 'lc_measurements') and hasattr(self.model, 'annotations')):
            if not self.model.lc_measurements:
                self.view.show_critical_error("Please load LC files and either corresponding MS files or manual annotations before processing.")
                return
            
            self.view.processButton.setEnabled(False)
            self.view.statusbar.showMessage("Processing data... [Step 1/3]")
            self.view.progressBar.setVisible(True)
            self.view.progressLabel.setVisible(True)
            self.view.progressLabel.setText("0%")
            self.view.progressBar.setValue(0)

            self.worker = Worker(self.model, self.model.ms_measurements, self.model.lc_measurements)
            self.worker.progress_update.connect(self.view.progress_update.emit)
            self.worker.finished.connect(self.start_ms_annotation)
            
            print("Starting the processing...")
            self.worker.start()

        else:
            self.view.show_critical_error("Nothing to process. Please load LC files and either corresponding MS files or manual annotations before proceeding.")

    def start_ms_annotation(self, results):
        # Clean up the model's measurements to free memory
        del self.model.lc_measurements
        del self.model.ms_measurements
        gc.collect()

        # Start the annotation for MS files
        self.view.progressBar.setValue(0)
        self.view.progressLabel.setText("0%")
        self.view.statusbar.showMessage("Rebuilding extracted ion chromatograms... [Step 2/3]")

        self.ms_annotation_worker = AnnotationWorker(self.model.annotate_MS)
        self.ms_annotation_worker.progress_update.connect(self.view.progress_update.emit)
        self.ms_annotation_worker.finished.connect(self.start_lc_annotation)
        self.ms_annotation_worker.start()

    def start_lc_annotation(self, results):
        # Start the annotation for LC files
        self.view.progressBar.setValue(0)
        self.view.progressLabel.setText("0%")
        self.view.statusbar.showMessage("Annotating LC chromatograms... [Step 3/3]")

        self.lc_annotation_worker = AnnotationWorker(self.model.annotate_LC)
        self.lc_annotation_worker.progress_update.connect(self.view.progress_update.emit)
        self.lc_annotation_worker.finished.connect(self.on_processing_finished)
        self.lc_annotation_worker.start()

    def on_processing_finished(self, results):
        # Memory clean-up
        del self.model.lc_results
        del self.model.ms_results
        gc.collect()

        self.view.progressBar.setVisible(False)
        self.view.progressLabel.setVisible(False)
        self.view.processButton.setEnabled(True)
        self.view.statusbar.showMessage("Finished: data processing completed successfully.", 5000)

        self.view.tabWidget.setTabEnabled(self.view.tabWidget.indexOf(self.view.tabResults), True)
        self.view.tabWidget.setCurrentIndex(self.view.tabWidget.indexOf(self.view.tabResults))
        self.view.tabWidget.setTabEnabled(self.view.tabWidget.indexOf(self.view.tabQuantitation), True)

        self.update_filenames_combo_box()

    def update_filenames_combo_box(self):
        filenames = [file.filename for file in self.model.annotated_lc_measurements]
        self.view.update_combo_box(filenames)

    def display_selected_plots(self):
        selected_file = self.view.comboBox_currentfile.currentText()
        print("Selected file:", selected_file)
        try:
            lc_file, ms_file = self.model.get_plots(selected_file)
        except TypeError as e:
            print(f"Error: {e}")
        self.view.display_plots(lc_file, ms_file)  # Update the view with the selected plots

