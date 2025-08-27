import pytest
import numpy as np
import json
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch

# Add the lc-inspector directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lc-inspector'))

from ui.model import Model
from ui.controller import Controller
from utils.classes import Compound, MSMeasurement
from calculation.calc_conc import calculate_concentration

class MockView:
    """Mock View class to enable Controller functionality without GUI."""
    
    def __init__(self):
        # Mock necessary view components
        self.processButton = Mock()
        self.calibrateButton = Mock()
        self.comboBoxChooseCompound = Mock()
        self.logXCheckBox = Mock()
        self.logYCheckBox = Mock()
        self.unifiedResultsTable = Mock()
        self.comboBox_currentfile = Mock()
        self.comboBox_currentfile.currentIndexChanged = Mock()

        # Mock methods
        self.get_calibration_files = Mock()
        self.update_choose_compound = Mock()
        self.display_calibration_curve = Mock()
        self.show_critical_error = Mock()
        self.display_concentrations = Mock()
        self.display_ms2 = Mock()
        self.display_library_ms2 = Mock()


class TestLogTransformCalibration:
    """
    Tests for the log-transform feature in the calibration curve.
    """

    def setup_method(self):
        """Set up test fixtures."""
        self.model = Model()
        self.view = MockView()
        self.controller = Controller(self.model, self.view)

        # Create a dummy compound
        self.compound = Compound(name='TestCompound', ions=[100.0], ion_info=['TestIon'])
        self.model.compounds = [self.compound]

        # Mock calibration data
        self.calibration_files = {
            'file1': '1 mM',
            'file2': '2 mM',
            'file3': '4 mM',
            'file4': '8 mM',
        }
        self.view.get_calibration_files.return_value = self.calibration_files

        # Mock MS measurements with some data
        self.model.ms_measurements = {}
        with patch('utils.classes.MSMeasurement.__init__', lambda self, path, mass_accuracy=0.0001: None):
            for i, (file, conc) in enumerate(self.calibration_files.items()):
                ms_measurement = MSMeasurement(path=file)
                ms_measurement.filename = file
                ms_compound = Compound(name='TestCompound', ions=[100.0], ion_info=['TestIon'])
                # Simulate some signal that is not perfectly linear
                signal = float(conc.split()[0]) * 1000 + np.random.uniform(-50, 50) + (float(conc.split()[0])**2 * 100)
                ms_compound.ions[100.0]['MS Peak Area'] = {'baseline_corrected_area': signal}
                ms_measurement.xics = [ms_compound]
                self.model.ms_measurements[file] = ms_measurement

    def test_no_log_transform(self):
        """Test calibration without any log transformation."""
        self.view.logXCheckBox.isChecked.return_value = False
        self.view.logYCheckBox.isChecked.return_value = False

        self.controller.calibrate()

        params = self.model.compounds[0].calibration_parameters
        assert not params['log_x']
        assert not params['log_y']
        assert 'slope' in params
        assert 'intercept' in params
        assert 'r_squared' in params

        # Check concentration calculation
        test_signal = 2500
        calculated_conc = calculate_concentration(test_signal, params)
        expected_conc = (test_signal - params['intercept']) / params['slope']
        assert np.isclose(calculated_conc, expected_conc)

    def test_log_x_transform(self):
        """Test calibration with log-X transformation."""
        self.view.logXCheckBox.isChecked.return_value = True
        self.view.logYCheckBox.isChecked.return_value = False

        self.controller.calibrate()

        params = self.model.compounds[0].calibration_parameters
        assert params['log_x']
        assert not params['log_y']
        
        # Check concentration calculation
        test_signal = 2500
        calculated_conc = calculate_concentration(test_signal, params)
        expected_conc = 10**((test_signal - params['intercept']) / params['slope'])
        assert np.isclose(calculated_conc, expected_conc)

    def test_log_y_transform(self):
        """Test calibration with log-Y transformation."""
        self.view.logXCheckBox.isChecked.return_value = False
        self.view.logYCheckBox.isChecked.return_value = True

        self.controller.calibrate()

        params = self.model.compounds[0].calibration_parameters
        assert not params['log_x']
        assert params['log_y']

        # Check concentration calculation
        test_signal = 2500
        calculated_conc = calculate_concentration(test_signal, params)
        expected_conc = (np.log10(test_signal) - params['intercept']) / params['slope']
        assert np.isclose(calculated_conc, expected_conc)

    def test_log_xy_transform(self):
        """Test calibration with both log-X and log-Y transformation."""
        self.view.logXCheckBox.isChecked.return_value = True
        self.view.logYCheckBox.isChecked.return_value = True

        self.controller.calibrate()

        params = self.model.compounds[0].calibration_parameters
        assert params['log_x']
        assert params['log_y']

        # Check concentration calculation
        test_signal = 2500
        calculated_conc = calculate_concentration(test_signal, params)
        expected_conc = 10**((np.log10(test_signal) - params['intercept']) / params['slope'])
        assert np.isclose(calculated_conc, expected_conc)

    def test_non_positive_y_with_log_y(self):
        """Test that non-positive values are handled gracefully with log-Y."""
        # Inject a non-positive signal
        ms_measurement = self.model.ms_measurements['file1']
        ms_measurement.xics[0].ions[100.0]['MS Peak Area']['baseline_corrected_area'] = 0

        self.view.logXCheckBox.isChecked.return_value = False
        self.view.logYCheckBox.isChecked.return_value = True

        self.controller.calibrate()

        # The calibration should have run with the remaining 3 points
        assert len(self.model.compounds[0].calibration_curve) == 4 # still has 4 points
        
        # Check that the calculation with a non-positive area returns 0
        params = self.model.compounds[0].calibration_parameters
        assert calculate_concentration(0, params) == 0
        assert calculate_concentration(-100, params) == 0

    def test_recalibration_with_state_change(self):
        """Test that recalibrating with different log states works correctly."""
        # Initial calibration: no log
        self.view.logXCheckBox.isChecked.return_value = False
        self.view.logYCheckBox.isChecked.return_value = False
        self.controller.calibrate()
        params1 = self.model.compounds[0].calibration_parameters
        assert not params1['log_x'] and not params1['log_y']

        # Second calibration: log-X
        self.view.logXCheckBox.isChecked.return_value = True
        self.view.logYCheckBox.isChecked.return_value = False
        self.controller.calibrate()
        params2 = self.model.compounds[0].calibration_parameters
        assert params2['log_x'] and not params2['log_y']
        assert params1['slope'] != params2['slope']

        # Third calibration: back to no log
        self.view.logXCheckBox.isChecked.return_value = False
        self.view.logYCheckBox.isChecked.return_value = False
        self.controller.calibrate()
        params3 = self.model.compounds[0].calibration_parameters
        assert not params3['log_x'] and not params3['log_y']
        assert np.isclose(params1['slope'], params3['slope'])
        assert np.isclose(params1['intercept'], params3['intercept'])
