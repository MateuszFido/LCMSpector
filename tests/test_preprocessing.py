import pytest, sys, os, json, pathlib, tempfile
from urllib.request import urlretrieve
import numpy as np
import pandas as pd
from utils.preprocessing import baseline_correction, construct_xics
from utils.loading import load_absorbance_data, load_ms1_data, load_annotated_peaks
from utils.classes import Compound, MSMeasurement, LCMeasurement
from ui.model import Model

@pytest.fixture(scope="session")
def ms1_data():
    if not os.path.isfile('test_data.mzml'):
        print("Downloading data from the MassIVE repository...")
        data = urlretrieve('ftp://massive-ftp.ucsd.edu/v04/MSV000088442/raw/KU0036_ESI-_opt_MSMS_41_01_20747.mzML', 'test_data.mzml')
        print("Done.")
    ms1_data = load_ms1_data('test_data.mzml')
    assert len(ms1_data) > 0
    return ms1_data

@pytest.fixture(scope="session")
def absorbance_data():
    if not os.path.isfile('test_lc_data.txt'):
        print("Downloading data from the MassIVE repository...")
        data = urlretrieve('ftp://massive-ftp.ucsd.edu/v04/MSV000088442/metadata/Erugosa_UV_data.txt', 'test_lc_data.txt')
        print("Done.")
    absorbance_data = load_absorbance_data('test_lc_data.txt')
    assert len(absorbance_data) > 0
    return absorbance_data

@pytest.fixture(scope="session")
def config():
    config_path = "config.json"
    with open(config_path, "r") as f:
        lists = json.load(f)
    return lists 

def test_baseline_correction_generic_txt():
    data = load_absorbance_data('tests/generic.txt')
    baseline_corrected = baseline_correction(data)
    assert len(baseline_corrected) == len(data)
    assert baseline_corrected['Value (mAU)'].min() >= 0

def test_baseline_correction_agilent(absorbance_data):
    baseline_corrected = baseline_correction(absorbance_data)
    assert len(baseline_corrected) == len(absorbance_data)
    assert baseline_corrected['Value (mAU)'].min() >= 0

def test_construct_xics(ms1_data):
    assert ms1_data is not None
    compound1 = Compound(name="Compound1", ions=[91.11, 92.22, 34.43], ion_info=["Ion 1", "Ion 2", "Ion 3"])
    compound2 = Compound(name="Compound2", ions=[91.11, 92.22, 34.43], ion_info=["Ion 1", "Ion 2", "Ion 3"])
    compound3 = Compound(name="Compound3", ions=[91.11, 92.22, 34.43], ion_info=["Ion 1", "Ion 2", "Ion 3"])
    compounds = (compound1, compound2, compound3)
    mass_accuracy = 0.001
    xics = construct_xics(ms1_data, compounds, mass_accuracy)
    for xic in xics:
        for ion in xic.ions.keys():
            assert xic.ions[ion]['MS Intensity'] is not None
            assert xic.ions[ion]['RT'] is not None

def test_msmeasurement_creation(ms1_data, config):
    assert ms1_data is not None
    # Create Compound instances from the config's ion list
    ion_list = []
    for compound in config['terpenoids']:
        entry = Compound(name=compound, ions=config['terpenoids'][compound]["ions"], ion_info=config['terpenoids'][compound]["info"])
        ion_list.append(entry)

    ms_measurement = MSMeasurement(path='test_data.mzml', ion_list=tuple(ion_list))
    assert ms_measurement.xics
    assert ms_measurement.data

def test_lcmeasurement_creation(absorbance_data):
    assert absorbance_data is not None
    lc_measurement = LCMeasurement(path='test_lc_data.txt')
    assert lc_measurement

def test_load_annotated_peaks():
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
        tmp.write("Header 1\n")
        tmp.write("Header 2\n")
        tmp.write("Peak Results\n")
        tmp.write("Peakname\tRet.Time\tArea\tPeak Start\tPeak Stop\n")
        tmp.write("Peak1\t10.0\t100.0\t1.0\t10.0\n")
        tmp.write("Peak2\t20.0\t200.0\t2.0\t20.0\n")
        file_path = tmp.name

    # Load annotated peaks
    df = load_annotated_peaks(file_path)

    # Check if the DataFrame is not empty
    assert df is not None
    assert not df.empty

    # Check if the DataFrame has the correct columns
    expected_columns = ['Peakname', 'Ret.Time', 'Area', 'Peak Start', 'Peak Stop']
    assert set(df.columns) == set(expected_columns)

    # Check if the DataFrame has the correct data
    expected_data = pd.DataFrame({
        'Peakname': ['Peak1', 'Peak2'],
        'Ret.Time': [10.0, 20.0],
        'Area': [100.0, 200.0],
        'Peak Start': [1.0, 2.0],
        'Peak Stop': [10.0, 20.0]
    })
    pd.testing.assert_frame_equal(df, expected_data)

    # Remove the temporary file
    os.remove(file_path)


def test_load_annotated_peaks_integration_results():
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
        tmp.write("Header 1\n")
        tmp.write("Header 2\n")
        tmp.write("Integration Results\n")
        tmp.write("Peakname\tRet.Time\tArea\tPeak Start\tPeak Stop\n")
        tmp.write("Peak1\t10.0\t100.0\t1.0\t10.0\n")
        tmp.write("Peak2\t20.0\t200.0\t2.0\t20.0\n")
        file_path = tmp.name

    # Load annotated peaks
    df = load_annotated_peaks(file_path)

    # Check if the DataFrame is not empty
    assert df is not None
    assert not df.empty

    # Check if the DataFrame has the correct columns
    expected_columns = ['Peakname', 'Ret.Time', 'Area', 'Peak Start', 'Peak Stop']
    assert set(df.columns) == set(expected_columns)

    # Check if the DataFrame has the correct data
    expected_data = pd.DataFrame({
        'Peakname': ['Peak1', 'Peak2'],
        'Ret.Time': [10.0, 20.0],
        'Area': [100.0, 200.0],
        'Peak Start': [1.0, 2.0],
        'Peak Stop': [10.0, 20.0]
    })
    pd.testing.assert_frame_equal(df, expected_data)

    # Remove the temporary file
    os.remove(file_path)


def test_load_annotated_peaks_no_header():
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
        tmp.write("Peakname\tRet.Time\tArea\tPeak Start\tPeak Stop\n")
        tmp.write("Peak1\t10.0\t100.0\t1.0\t10.0\n")
        tmp.write("Peak2\t20.0\t200.0\t2.0\t20.0\n")
        file_path = tmp.name

    # Load annotated peaks
    with pytest.raises(pd.errors.EmptyDataError):
        load_annotated_peaks(file_path)

    # Remove the temporary file
    os.remove(file_path)


def test_load_annotated_peaks_empty_file():
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
        file_path = tmp.name

    # Load annotated peaks
    with pytest.raises(pd.errors.EmptyDataError):
        load_annotated_peaks(file_path)

    # Remove the temporary file
    os.remove(file_path)
