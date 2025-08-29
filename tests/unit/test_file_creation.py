"""
Unit tests for core file loading capability, including file creation and validation.
"""

from pathlib import Path
from utils.classes import MSMeasurement

class TestFileCreation:
    """
    Unit tests for core file loading capability, including file creation and validation.
    """
    def test_create_file_from_stmix_data(self):
        """
        Test the creation of a file from STMIX data.
        """
        
        data_dir = Path(__file__).parent.parent.parent / "tests" / "data"
        file_path = data_dir / "LCMSpector-sample-data" / "STMIX_BIG_2.5mM_pos.mzml"
        assert file_path.exists(), f"File not found: {file_path}"

        file = MSMeasurement(file_path, mass_accuracy=0.0001)

        # Verify mass accuracy was properly applied
        assert file.mass_accuracy == 0.0001, "Mass accuracy not applied correctly"

        # Verify file creation
        assert file.data is not None, "File not created"
        assert len(file.data) > 0, "File is empty"