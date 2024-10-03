class FileModel:
    def __init__(self):
        self.txt_files = []
        self.mzml_files = []

    def add_txt_files(self, files):
        self.txt_files.extend(files)

    def add_mzml_files(self, files):
        self.mzml_files.extend(files)

    def get_txt_files(self):
        return self.txt_files

    def get_mzml_files(self):
        return self.mzml_files
