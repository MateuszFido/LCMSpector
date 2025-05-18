import pytest

def test_simple():
    assert True

test_simple()

import numpy as np
from ui.preprocessing import construct_xics

@pytest.mark.parametrize("compound,expected_result", [
    (Compound("test", {"ion1": {"MS Intensity": np.array([[1, 2, 3], [4, 5, 6]])}}), {"ion1": {"RT": 2, "MS Intensity": np.array([[1, 2, 3], [4, 5, 6]])}})
])
def test_construct_xics(compound, expected_result):
    data = [{"m/z array": np.array([1, 2, 3]), "intensity array": np.array([4, 5, 6])}]
    result = construct_xics(data, [compound], 0.000001)
    assert all(result[0].ions[ion]["RT"] == expected_result[ion]["RT"] for ion in expected_result)
    assert all(np.array_equal(result[0].ions[ion]["MS Intensity"], expected_result[ion]["MS Intensity"]) for ion in expected_result)
