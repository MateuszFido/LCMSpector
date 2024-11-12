import unittest
import pandas as pd
import numpy as np
from utils.preprocessing import baseline_correction

class TestBaselineCorrection(unittest.TestCase):

    def setUp(self):
        # Sample data for testing
        self.data = {
            'Time (min)': [0, 1, 2, 3, 4, 5],
            'Value (mAU)': [1, 2, 3, 2, 1, 0]
        }
        self.dataframe = pd.DataFrame(self.data)

    def test_baseline_correction_output_structure(self):
        # Test the output structure
        result = baseline_correction(self.dataframe)
        
        # Check if the result is a DataFrame
        self.assertIsInstance(result, pd.DataFrame)
        
        # Check if the DataFrame has the correct columns
        expected_columns = ['Time (min)', 'Value (mAU)', 'Baseline', 'Uncorrected']
        self.assertListEqual(list(result.columns), expected_columns)

    def test_baseline_correction_values(self):
        # Test the output values (this is a simple check, you may want to use more complex checks)
        result = baseline_correction(self.dataframe)
        
        # Check if the baseline corrected values are as expected
        # Here you would need to define what the expected output is based on your algorithm
        # For demonstration, let's assume we expect some specific values
        expected_values = np.array([0.0, 1.0, 2.0, 1.0, 0.0, 0.0])  # Replace with actual expected values
        np.testing.assert_array_almost_equal(result['Value (mAU)'].values, expected_values, decimal=5)

    def test_baseline_correction_negative_values(self):
        # Test with negative values in the input
        self.data['Value (mAU)'] = [1, -1, 3, 2, -2, 0]
        dataframe_with_negatives = pd.DataFrame(self.data)
        
        result = baseline_correction(dataframe_with_negatives)
        
        # Check if the baseline corrected values are as expected
        # Define expected values based on the algorithm's behavior with negative inputs
        expected_values = np.array([0.0, 0.0, 3.0, 2.0, 0.0, 0.0])  # Replace with actual expected values
        np.testing.assert_array_almost_equal(result['Value (mAU)'].values, expected_values, decimal=5)

if __name__ == '__main__':
    unittest.main()
