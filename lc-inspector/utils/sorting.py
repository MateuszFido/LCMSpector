import os
from settings import BASE_PATH

def get_path(path):
    return os.path.join(BASE_PATH, path)

def check_data():
# Sort the files found in data into their respective folders
    if any(file.endswith('.mzml') for file in os.listdir(BASE_PATH)) or any(file.endswith('.txt') for file in os.listdir(BASE_PATH)):
        for file in os.listdir(BASE_PATH):
            if file.endswith('.mzml'):
                try:
                    os.rename(get_path(file), ms_path / file)
                except(FileExistsError):
                    continue
            elif file.endswith('.txt'):
                try:
                    os.rename(get_path(file), ms_path / file)
                except(FileExistsError):
                    continue