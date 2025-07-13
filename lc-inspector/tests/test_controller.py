"""
Tests for the controller layer of the LC-Inspector application.

This module contains tests for the controller layer, demonstrating how the refactored
code can be tested more easily due to the improved separation of concerns.
"""

import unittest
import sys
import os
import logging
from unittest.mock import MagicMock, patch

# Add the parent directory to the path so we can import the controller
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ui.controller_refactored import Controller
from model import LCInspectorModel
from utils.classes_optimized import Compound

# Disable logging for tests
logging.disable(logging.CRITICAL)

class TestController(unittest.TestCase):
    """Tests for the Controller class."""
    
    def setUp(self):
        """Set up the test case with mock model and view."""
        # Create mock model and view
        self.model = MagicMock(spec=LCInspectorModel)
        self.view = MagicMock()
        
        # Create the controller with the mock model and view
        self.controller = Controller(self.model, self.view)
    
    def test_initialization(self):
        """Test that the controller is initialized correctly."""
        # Create fresh mocks for this test
        model = MagicMock(spec=LCInspectorModel)
        view = MagicMock()
        
        # Create a new controller with these mocks
        controller = Controller(model, view)
        
        # Check that the controller has the correct attributes
        self.assertEqual(controller.model, model)
        self.assertEqual(controller.view, view)
        self.assertEqual(controller.mode, "LC/GC-MS")
        
        # Check that the view's controller attribute is set
        self.assertEqual(view.controller, controller)
        
        # Check that the model's event listeners are registered
        self.assertTrue(model.on.called)
        
        # Check that the view's signals are connected
        self.assertTrue(view.processButton.clicked.connect.called)
        self.assertTrue(view.comboBox_currentfile.currentIndexChanged.connect.called)
        self.assertTrue(view.calibrateButton.clicked.connect.called)
        self.assertTrue(view.comboBoxChooseCompound.currentIndexChanged.connect.called)
    
    def test_process_data(self):
        """Test that process_data calls the correct methods."""
        # Set up the model and view for a successful processing
        compound1 = Compound("compound1", [123.4], ["info1"])
        compound2 = Compound("compound2", [456.7], ["info2"])
        self.model.compounds = [compound1, compound2]
        self.model.lc_measurements = {'file1': 'lc_file1'}
        self.model.ms_measurements = {'file1': 'ms_file1'}
        self.view.ionTable.get_items.return_value = [compound1, compound2]
        
        # Call the method
        self.controller.process_data()
        
        # Check that the view methods were called
        self.view.update_lc_file_list.assert_called_once()
        self.view.update_ms_file_list.assert_called_once()
        self.view.update_annotation_file.assert_called_once()
        self.view.statusbar.showMessage.assert_called_once()
        self.view.ionTable.get_items.assert_called_once()
        
        # Check that the model method was called
        self.model.process.assert_called_once_with(mode="LC/GC-MS")
    
    def test_process_data_no_compounds(self):
        """Test that process_data shows an error when there are no compounds."""
        # Set up the model and view for a failed processing
        self.view.ionTable.get_items.return_value = []
        
        # Call the method
        self.controller.process_data()
        
        # Check that the view methods were called
        self.view.update_lc_file_list.assert_called_once()
        self.view.update_ms_file_list.assert_called_once()
        self.view.update_annotation_file.assert_called_once()
        self.view.statusbar.showMessage.assert_called_once()
        self.view.ionTable.get_items.assert_called_once()
        self.view.show_critical_error.assert_called_once()
        
        # Check that the model method was not called
        self.model.process.assert_not_called()
    
    def test_on_processing_finished(self):
        """Test that _on_processing_finished updates the view correctly."""
        # Set up the data
        lc_results = {'file1': 'lc_file1'}
        ms_results = {'file1': 'ms_file1'}
        data = {'lc_results': lc_results, 'ms_results': ms_results}
        
        # Call the method
        self.controller._on_processing_finished(data)
        
        # Check that the view methods were called
        self.view.progressBar.setVisible.assert_called_once_with(False)
        self.view.progressLabel.setVisible.assert_called_once_with(False)
        self.view.processButton.setEnabled.assert_called_once_with(True)
        self.view.statusbar.showMessage.assert_called_once()
        self.view.tabWidget.setTabEnabled.assert_called()
        self.view.tabWidget.setCurrentIndex.assert_called_once()
        self.view.actionExport.setEnabled.assert_called_once_with(True)
    
    def test_on_progress_updated(self):
        """Test that _on_progress_updated calls the view method."""
        # Call the method
        self.controller._on_progress_updated(50)
        
        # Check that the view method was called
        self.view.update_progress_bar.assert_called_once_with(50)
    
    def test_on_calibration_finished(self):
        """Test that _on_calibration_finished updates the view correctly."""
        # Set up the data
        compounds = [
            Compound("compound1", [123.4], ["info1"]),
            Compound("compound2", [456.7], ["info2"])
        ]
        
        # Set the model's compounds property to match what we're passing
        self.model.compounds = compounds
        
        # Call the method
        self.controller._on_calibration_finished(compounds)
        
        # Check that the view methods were called
        self.view.comboBoxChooseCompound.setEnabled.assert_called_once_with(True)
        self.view.update_choose_compound.assert_called_once_with(self.model.compounds)
    
    def test_display_selected_plots(self):
        """Test that display_selected_plots calls the correct methods."""
        # Set up the model and view
        self.view.comboBox_currentfile.currentText.return_value = 'file1'
        self.model.get_plots.return_value = ('lc_file1', 'ms_file1')
        
        # Call the method
        self.controller.display_selected_plots()
        
        # Check that the model and view methods were called
        self.view.comboBox_currentfile.currentText.assert_called_once()
        self.model.get_plots.assert_called_once_with('file1')
        self.view.display_plots.assert_called_once_with('lc_file1', 'ms_file1')
    
    def test_calibrate(self):
        """Test that calibrate calls the correct methods."""
        # Set up the model and view
        self.view.get_calibration_files.return_value = {'file1': '1 mM'}
        
        # Call the method
        self.controller.calibrate()
        
        # Check that the model and view methods were called
        self.view.get_calibration_files.assert_called_once()
        self.model.calibrate.assert_called_once_with({'file1': '1 mM'})
    
    def test_find_ms2_precursors(self):
        """Test that find_ms2_precursors calls the correct methods."""
        # Set up the model and view
        self.view.comboBoxChooseCompound.currentIndex.return_value = 0
        
        # Call the method
        self.controller.find_ms2_precursors()
        
        # Check that the model and view methods were called
        self.view.statusbar.showMessage.assert_called_once()
        self.view.comboBoxChooseCompound.currentIndex.assert_called_once()
        self.model.find_ms2_precursors.assert_called_once_with(0)

if __name__ == '__main__':
    unittest.main()
