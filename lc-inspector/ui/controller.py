# controller.py
from utils.threading import Worker, AnnotationWorker
from multiprocessing import Manager
import gc

class Controller:
    def __init__(self, model, view):
        """
        Initialize the Controller with the given model and view.

        Parameters
        ----------
        model : Model
            The data model that contains the logic for processing data.
        view : View
            The view component of the application, responsible for the GUI.

        This constructor sets up the controller by connecting the view's signals
        to the appropriate methods in the controller, allowing user interactions
        in the view to trigger data processing and updates in the model.
        """
        self.model = model
        self.view = view
        self.view.controller = self  # Set a reference to the controller in the view

        # Connect view signals to controller methods
        self.view.browseLC.clicked.connect(self.load_lc_data)
        self.view.browseMS.clicked.connect(self.load_ms_data)
        self.view.processButton.clicked.connect(self.process_data)
        self.view.comboBox_currentfile.currentIndexChanged.connect(self.display_selected_plots)


    def load_lc_data(self):
        # Logic to load LC data is handled in the view
        pass

    def load_ms_data(self):
        # Logic to load MS data is handled in the view
        pass

    def load_annotations(self):
        # Logic to load annotations is handled in the view
        pass
        
    def process_data(self):
        # Call the process method in the model with the loaded file lists
        """
        Trigger the processing action in the model.

        This method is called when the user clicks the process button.
        It checks whether the model has the necessary file lists loaded,
        and if so, calls the process method in the model with those lists.
        If not, it shows an error message to the user.
        """
        
        if (hasattr(self.model, 'ms_measurements') and hasattr(self.model, 'lc_measurements')) or (hasattr(self.model, 'lc_measurements') and hasattr(self.model, 'annotations')):
            # Ensure that the lists are not empty
            if not self.model.lc_measurements:
                self.view.show_critical_error("Please load LC files and either corresponding MS files or manual annotations before processing.")
                return
            
            # Disable the process button
            self.view.processButton.setEnabled(False)

            # Set the status message and show the progress bar
            self.view.statusbar.showMessage("Processing data... [Step 1/3]")
            self.view.progressBar.setVisible(True)
            self.view.progressLabel.setVisible(True)
            self.view.progressLabel.setText("0%")
            self.view.progressBar.setValue(0)  # Reset progress bar

            # Create and start the worker thread
            self.worker = Worker(self.model, self.model.ms_measurements, self.model.lc_measurements)
            self.worker.progress_update.connect(self.view.progress_update.emit)  # Connect progress updates
            self.worker.finished.connect(self.start_ms_annotation)  # Connect finished signal
            
            print("Starting the processing...")
            self.worker.start()  # Start the worker thread

        else:
            self.view.show_critical_error("Nothing to process. Please load LC files and either corresponding MS files or manual annotations before proceeding.")

    def start_ms_annotation(self, results):
        del(self.model.lc_measurements)
        del(self.model.ms_measurements)
        # Force garbage collection
        gc.collect()
        # Start the annotation for MS files
        self.view.progressBar.setValue(0)  # Reset progress bar
        self.view.progressLabel.setText("0%") # Reset progress label
        self.view.statusbar.showMessage("Rebuilding extracted ion chromatograms... [Step 2/3]")

        self.ms_annotation_worker = AnnotationWorker(self.model.annotate_MS, results)
        self.ms_annotation_worker.progress_update.connect(self.view.progress_update.emit)
        self.ms_annotation_worker.finished.connect(self.start_lc_annotation)
        self.ms_annotation_worker.start()

    def start_lc_annotation(self, results):
        # Start the annotation for LC files
        self.view.progressBar.setValue(0)  # Reset progress bar
        self.view.progressLabel.setText("0%") # Reset progress label
        self.view.statusbar.showMessage(f"Annotating LC chromatograms... [Step 3/3]")

        self.lc_annotation_worker = AnnotationWorker(self.model.annotate_LC, results)
        self.lc_annotation_worker.progress_update.connect(self.view.progress_update.emit)
        self.lc_annotation_worker.finished.connect(self.on_processing_finished)
        self.lc_annotation_worker.start()

    def on_processing_finished(self, results):
        
        # Memory clean-up
        del(self.model.lc_results)
        del(self.model.ms_results)
        # Force garbage collection
        gc.collect()
        # Hide the progress bar after processing
        self.view.progressBar.setVisible(False)
        self.view.progressLabel.setVisible(False)
        self.view.processButton.setEnabled(True)  # Enable the process button again
        self.view.statusbar.showMessage("Finished: data processing completed successfully.", 5000)

        self.view.tabWidget.setTabEnabled(self.view.tabWidget.indexOf(self.view.tabResults), True)  # Enable the results tab
        self.view.tabWidget.setCurrentIndex(self.view.tabWidget.indexOf(self.view.tabResults))
        self.view.tabWidget.setTabEnabled(self.view.tabWidget.indexOf(self.view.tabQuantitation), True)  # Enable the quantitation tab

        self.update_filenames_combo_box()

       
    def update_filenames_combo_box(self):
        # Collect filenames from processed results
        filenames = [file.filename for file in self.model.annotated_lc_measurements]
        self.view.update_combo_box(filenames)
    
    def display_selected_plots(self):
        selected_file = self.view.comboBox_currentfile.currentText()
        print("Selected file:", selected_file)
        try:
            lc_file, ms_file = self.model.get_plots(selected_file)  # Retrieve plot data from the model
        except TypeError as e:
            print(f"Error: {e}")
        self.view.display_plots(lc_file, ms_file)  # Update the view with the selected plots