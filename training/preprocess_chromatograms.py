from utils.load_data import load_absorbance_data
from utils.list_files import read_files
from pathlib import Path


# load chromatograms from ../data/training

cal_files, res_files = read_files(Path("../data/training/"))

for cal_file, res_file in zip(cal_files, res_files):
    print(cal_file, res_file)
    chromatogram = load_absorbance_data(cal_file)
    print(chromatogram)
    chromatogram = load_absorbance_data(res_file)
    print(chromatogram)