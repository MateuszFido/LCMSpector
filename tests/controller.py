from PyQt6.QtWidgets import QFileDialog
from model import FileModel
from view import FileView

class FileController:
    def __init__(self, view):
        self.model = FileModel()
        self.view = view
        self.view.txt_upload_button.clicked.connect(self.upload_txt_files)
        self.view.mzml_upload_button.clicked.connect(self.upload_mzml_files)
        self.view.function_button1.clicked.connect(self.function1)
        self.view.function_button2.clicked.connect(self.function2)
        self.view.function_button3.clicked.connect(self.function3)
        self.view.function_button1.setEnabled(False)
        self.view.function_button2.setEnabled(False)
        self.view.function_button3.setEnabled(False)

    def upload_txt_files(self):
        files, _ = QFileDialog.getOpenFileNames(self.view, "Upload .txt files", "", "Text Files (*.txt)")
        self.model.add_txt_files(files)
        self.view.update_txt_file_label(self.model.get_txt_files())
        self.view.update_txt_file_list(self.model.get_txt_files())
        self.check_buttons()

    def upload_mzml_files(self):
        files, _ = QFileDialog.getOpenFileNames(self.view, "Upload .mzml files", "", "MzML Files (*.mzml)")
        self.model.add_mzml_files(files)
        self.view.update_mzml_file_label(self.model.get_mzml_files())
        self.view.update_mzml_file_list(self.model.get_mzml_files())
        self.check_buttons()

    def check_buttons(self):
        if self.model.get_txt_files() and self.model.get_mzml_files():
            self.view.function_button1.setEnabled(True)
            self.view.function_button2.setEnabled(True)
            self.view.function_button3.setEnabled(True)
        else:
            self.view.function_button1.setEnabled(False)
            self.view.function_button2.setEnabled(False)
            self.view.function_button3.setEnabled(False)

    def function1(self):
        # Add your function 1 code here
        print("Function 1 executed")

    def function2(self):
        # Add your function 2 code here
        print("Function 2 executed")

    def function3(self):
        # Add your function 3 code here
        print("Function 3 executed")
