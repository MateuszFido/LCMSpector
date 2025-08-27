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
    slope = curve_params.get('slope', 0)
    intercept = curve_params.get('intercept', 0)
    log_x = curve_params.get('log_x', False)
    log_y = curve_params.get('log_y', False)

    # Check for zero slope to prevent division by zero
    if slope == 0:
        return 0

    # Transform area if y-axis is log-scaled
    if log_y:
        if area <= 0:
            return 0  # Cannot take log of non-positive area
        area = np.log10(area)

    # Calculate concentration
    concentration = (area - intercept) / slope

    # Back-transform concentration if x-axis is log-scaled
    if log_x:
        concentration = 10**concentration
    
    # Handle NaN and infinity cases
    if np.isnan(concentration) or not np.isfinite(concentration):
        return 0
    
    # Return rounded result
    return round(concentration, 6)
    