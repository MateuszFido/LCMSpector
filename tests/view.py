from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QTextBrowser, QHBoxLayout
from PyQt6.QtGui import QPixmap

class FileView(QWidget):
    def __init__(self):
        super().__init__()

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.logo_label = QLabel()
        self.logo_label.setPixmap(QPixmap("/Users/mateuszfido/Library/CloudStorage/OneDrive-ETHZurich/Mice/otc.png").scaled(1200, 600)) 
        self.layout.addWidget(self.logo_label)

        self.left_layout = QVBoxLayout()
        self.layout.addLayout(self.left_layout)

        self.txt_upload_button = QPushButton("Upload .txt files")
        self.left_layout.addWidget(self.txt_upload_button)

        self.txt_file_label = QLabel("No .txt files uploaded")
        self.left_layout.addWidget(self.txt_file_label)

        self.txt_file_list = QTextBrowser()
        self.left_layout.addWidget(self.txt_file_list)

        self.mzml_upload_button = QPushButton("Upload .mzml files")
        self.left_layout.addWidget(self.mzml_upload_button)

        self.mzml_file_label = QLabel("No .mzml files uploaded")
        self.left_layout.addWidget(self.mzml_file_label)

        self.mzml_file_list = QTextBrowser()
        self.left_layout.addWidget(self.mzml_file_list)

        self.right_layout = QVBoxLayout()
        self.layout.addLayout(self.right_layout)

        self.function_button1 = QPushButton("Preprocess MS data")
        self.right_layout.addWidget(self.function_button1)

        self.function_button2 = QPushButton("Preprocess LC data")
        self.right_layout.addWidget(self.function_button2)

        self.function_button3 = QPushButton("Annotate LC spectra")
        self.right_layout.addWidget(self.function_button3)

    def update_txt_file_label(self, files):
        self.txt_file_label.setText(f"Uploaded {len(files)} .txt files")

    def update_txt_file_list(self, files):
        file_list_text = "\n".join(files)
        self.txt_file_list.setText(file_list_text)

    def update_mzml_file_label(self, files):
        self.mzml_file_label.setText(f"Uploaded {len(files)} .mzml files")

    def update_mzml_file_list(self, files):
        file_list_text = "\n".join(files)
        self.mzml_file_list.setText(file_list_text)
