import pytest, sys, os
import numpy as np
import pandas as pd
from utils.preprocessing import baseline_correction, construct_xics
from utils.loading import load_absorbance_data
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