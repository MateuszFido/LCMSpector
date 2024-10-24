import sys
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView

class Controller(QMainWindow):
    def __init__(self):
        super().__init__()

        self.model = Model()  # Create a model instance

        # Create the view
        self.view = View(self)
        self.setCentralWidget(self.view)

        # Initialize the UI
        self.initUI()

    def initUI(self):
        # Connect signals to slots
        self.view.pushButton.clicked.connect(self.upload_files)
        self.view.pushButton_2.clicked.connect(self.upload_mzml_file)
        self.view.pushButton_3.clicked.connect(self.preprocess_files)
        self.view.horizontalSlider.valueChanged['int'].connect(self.update_mass_resolution)

    def upload_files(self):
        # Call the model's method to upload files
        self.model.upload_txt_files()

    def upload_mzml_file(self):
        # Call the model's method to upload mzml file
        self.model.upload_mzml_file()

    def preprocess_files(self):
        # Call the model's method to preprocess files
        self.model.preprocess_files()

    def update_mass_resolution(self, value):
        # Update the mass resolution in the view
        self.view.label_5.setText(str(value))

class Model:
    def __init__(self):
        self.txt_files = []
        self.mzml_file = None

    def upload_txt_files(self):
        # Simulate uploading txt files (replace with actual logic)
        self.txt_files.append("file1.txt")
        self.txt_files.append("file2.txt")

    def upload_mzml_file(self):
        # Simulate uploading mzml file (replace with actual logic)
        self.mzml_file = "mzml_file.mzml"

    def preprocess_files(self):
        # Simulate preprocessing files (replace with actual logic)
        print("Preprocessing files...")

class View(QMainWindow):
    def __init__(self, controller):
        super().__init__()

        self.controller = controller

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.pushButton = QPushButton("Upload Files")
        self.layout.addWidget(self.pushButton)

        self.pushButton_2 = QPushButton("Upload mzml File")
        self.layout.addWidget(self.pushButton_2)

        self.pushButton_3 = QPushButton("Preprocess Files")
        self.layout.addWidget(self.pushButton_3)

        self.label_5 = QLabel()
        self.layout.addWidget(self.label_5)

    def upload_files(self):
        # Call the controller's method to upload files
        self.controller.upload_files()

    def upload_mzml_file(self):
        # Call the controller's method to upload mzml file
        self.controller.upload_mzml_file()

    def preprocess_files(self):
        # Call the controller's method to preprocess files
        self.controller.preprocess_files()

    def update_mass_resolution(self, value):
        # Update the mass resolution label in the view
        self.label_5.setText(str(value))
