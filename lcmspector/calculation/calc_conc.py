import numpy as np


def calculate_concentration(area, curve_params):
    """
    Given the calibration curve parameters, calculate the concentration based on peak area.

    Args:
        area (float): Peak area value from chromatogram integration
        curve_params (dict): Calibration curve parameters containing 'slope' and 'intercept'

    Returns:
        float: Calculated concentration rounded to 6 decimal places, or 0 for invalid results

    Edge Cases:
        - Returns 0 when slope is 0 (prevents division by zero)
        - Returns 0 when result is NaN or infinite
        - Handles negative slopes normally (valid for some calibration curves)
        - Handles negative concentrations (below detection limit cases)
    """
    slope = curve_params["slope"]
    intercept = curve_params["intercept"]

    # Check for zero slope to prevent division by zero
    if slope == 0:
        return 0

    # Calculate concentration
    concentration = (area - intercept) / slope

    # Handle NaN and infinity
    if np.isnan(concentration) or not np.isfinite(concentration):
        return 0

    if concentration < 0:
        # level below detection limit, no point in reporting negative
        return 0

    # Return rounded result
    return round(concentration, 6)

