import pytest, sys, os
import numpy as np
import pandas as pd
from utils.preprocessing import baseline_correction, construct_xics
from utils.loading import load_absorbance_data, load_ms_data
from utils.classes import Compound

def test_simple():
    assert True

def test_baseline_correction_agilent():
    assert True

def test_baseline_correction_thermo():
    data = load_absorbance_data('tests/STMIX5mM-pos.txt')
    baseline_corrected = baseline_correction(data)
    assert len(baseline_corrected) == len(data)
    assert baseline_corrected['Value (mAU)'].min() >= 0

def test_baseline_correction_waters():
    assert True

def test_baseline_correction_generic_txt():
    data = load_absorbance_data('tests/generic.txt')
    baseline_corrected = baseline_correction(data)
    assert len(baseline_corrected) == len(data)
    assert baseline_corrected['Value (mAU)'].min() >= 0

def test_construct_xics():
    compound1 = Compound(name="Compound1", ions=[11.11, 12.22, 34.43], ion_info=["Ion 1", "Ion 2", "Ion 3"])
    compound2 = Compound(name="Compound2", ions=[11.11, 12.22, 34.43], ion_info=["Ion 1", "Ion 2", "Ion 3"])
    compound3 = Compound(name="Compound3", ions=[11.11, 12.22, 34.43], ion_info=["Ion 1", "Ion 2", "Ion 3"])
    compounds = (compound1, compound2, compound3)
    ms1_data, ms2_data = load_ms_data('tests/STMIX5mM-neg.mzml', compounds, 0.001)
    mass_accuracy = 0.001
    xics = construct_xics(ms1_data, compounds, mass_accuracy)
    for xic in xics:
        for ion in xic.ions.keys():
            assert xic.ions[ion]['MS Intensity'] is not None
            assert xic.ions[ion]['RT'] is not None
            