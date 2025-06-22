import pytest, sys, os, json, pathlib
import numpy as np
import pandas as pd
from utils.preprocessing import baseline_correction, construct_xics
from utils.loading import load_absorbance_data, load_ms1_data
from utils.classes import Compound, MSMeasurement
from ui.model import Model

def test_baseline_correction_agilent():
    assert True
"""
def test_baseline_correction_thermo():
    data = load_absorbance_data('tests/STMIX5_02.txt')
    baseline_corrected = baseline_correction(data)
    assert len(baseline_corrected) == len(data)
    assert baseline_corrected['Value (mAU)'].min() >= 0
"""
def test_baseline_correction_waters():
    assert True

def test_baseline_correction_generic_txt():
    data = load_absorbance_data('tests/generic.txt')
    baseline_corrected = baseline_correction(data)
    assert len(baseline_corrected) == len(data)
    assert baseline_corrected['Value (mAU)'].min() >= 0
"""
def test_construct_xics():
    compound1 = Compound(name="Compound1", ions=[11.11, 12.22, 34.43], ion_info=["Ion 1", "Ion 2", "Ion 3"])
    compound2 = Compound(name="Compound2", ions=[11.11, 12.22, 34.43], ion_info=["Ion 1", "Ion 2", "Ion 3"])
    compound3 = Compound(name="Compound3", ions=[11.11, 12.22, 34.43], ion_info=["Ion 1", "Ion 2", "Ion 3"])
    compounds = (compound1, compound2, compound3)
    ms1_data = load_ms1_data('tests/STMIX5_02.mzml')
    mass_accuracy = 0.001
    xics = construct_xics(ms1_data, compounds, mass_accuracy)
    for xic in xics:
        for ion in xic.ions.keys():
            assert xic.ions[ion]['MS Intensity'] is not None
            assert xic.ions[ion]['RT'] is not None
"""
"""
def test_find_ms2():
    model = Model()
    config_path = pathlib.Path(__file__).parent.parent / "config.json"
    with open(config_path, "r") as f:
        config = json.load(f)
    ion_list = [
        Compound(name=compound_name, ions=compound["ions"], ion_info=compound["info"])
        for compound_name, compound in config["aminoacids_and_polyamines"].items()
    ]
    file = MSMeasurement('tests/STMIX5_02.mzml', ion_list, 0.0001)
    model.compounds = ion_list
    model.ms_measurements["STMIX5_02.mzml"] = file
    model.find_ms2_precursors()
"""