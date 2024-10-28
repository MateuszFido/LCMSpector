# controller.py

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
        self.model.controller = self  # Set a reference to the controller in the model

        # Connect view signals to controller methods
        self.view.browseLC.clicked.connect(self.load_lc_data)
        self.view.browseMS.clicked.connect(self.load_ms_data)
        self.view.browseAnnotations.clicked.connect(self.load_annotations)
        self.view.processButton.clicked.connect(self.process_data)

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
            
            # Call the process method in the model
            self.model.process_data(self.model.ms_measurements, self.model.lc_measurements)

            self.view.show_message(self.view, "Success: data processing completed successfully.")

        else:
            self.view.show_critical_error("Nothing to process. Please load LC files and either corresponding MS files or manual annotations before proceeding.")
