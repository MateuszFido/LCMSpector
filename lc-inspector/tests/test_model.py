"""
Tests for the model layer of the LC-Inspector application.

This module contains tests for the model layer, demonstrating how the refactored
code can be tested more easily due to the improved separation of concerns.
"""

import unittest
import sys
import os
import logging

# Add the parent directory to the path so we can import the model
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from model import LCInspectorModel, EventEmitter

# Disable logging for tests
logging.disable(logging.CRITICAL)

class TestEventEmitter(unittest.TestCase):
    """Tests for the EventEmitter class."""
    
    def test_on_and_emit(self):
        """Test that events can be registered and emitted."""
        emitter = EventEmitter()
        
        # Create a mock callback
        called = False
        data_received = None
        
        def callback(data):
            nonlocal called, data_received
            called = True
            data_received = data
        
        # Register the callback
        emitter.on('test_event', callback)
        
        # Emit the event
        test_data = {'key': 'value'}
        emitter.emit('test_event', test_data)
        
        # Check that the callback was called with the correct data
        self.assertTrue(called)
        self.assertEqual(data_received, test_data)
    
    def test_off(self):
        """Test that event listeners can be removed."""
        emitter = EventEmitter()
        
        # Create a mock callback
        called = False
        
        def callback(data):
            nonlocal called
            called = True
        
        # Register the callback
        emitter.on('test_event', callback)
        
        # Remove the callback
        emitter.off('test_event', callback)
        
        # Emit the event
        emitter.emit('test_event', None)
        
        # Check that the callback was not called
        self.assertFalse(called)

class TestLCInspectorModel(unittest.TestCase):
    """Tests for the LCInspectorModel class."""
    
    def setUp(self):
        """Set up the test case."""
        self.model = LCInspectorModel()
    
    def test_initialization(self):
        """Test that the model is initialized correctly."""
        self.assertEqual(self.model.lc_measurements, {})
        self.assertEqual(self.model.ms_measurements, {})
        self.assertEqual(self.model.annotations, [])
        self.assertEqual(self.model.compounds, [])
        self.assertIsNotNone(self.model.library)
    
    def test_event_emission(self):
        """Test that the model emits events correctly."""
        # Create a mock callback
        called = False
        data_received = None
        
        def callback(data):
            nonlocal called, data_received
            called = True
            data_received = data
        
        # Register the callback
        self.model.on('test_event', callback)
        
        # Emit the event
        test_data = {'key': 'value'}
        self.model.emit('test_event', test_data)
        
        # Check that the callback was called with the correct data
        self.assertTrue(called)
        self.assertEqual(data_received, test_data)
    
    def test_get_plots(self):
        """Test that get_plots returns the correct files."""
        # Add mock files to the model
        self.model.lc_measurements = {'file1': 'lc_file1', 'file2': 'lc_file2'}
        self.model.ms_measurements = {'file1': 'ms_file1', 'file3': 'ms_file3'}
        
        # Test getting a file that exists in both
        lc_file, ms_file = self.model.get_plots('file1')
        self.assertEqual(lc_file, 'lc_file1')
        self.assertEqual(ms_file, 'ms_file1')
        
        # Test getting a file that exists only in lc_measurements
        lc_file, ms_file = self.model.get_plots('file2')
        self.assertEqual(lc_file, 'lc_file2')
        self.assertIsNone(ms_file)
        
        # Test getting a file that exists only in ms_measurements
        lc_file, ms_file = self.model.get_plots('file3')
        self.assertIsNone(lc_file)
        self.assertEqual(ms_file, 'ms_file3')
        
        # Test getting a file that doesn't exist
        lc_file, ms_file = self.model.get_plots('file4')
        self.assertIsNone(lc_file)
        self.assertIsNone(ms_file)

if __name__ == '__main__':
    unittest.main()
