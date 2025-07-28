import math

def calculate_concentration(area, curve_params):
    """
    Given the calibration curve parameters, calculate the concentration based on peak area.
    """
    slope = curve_params['slope']
    intercept = curve_params['intercept']
    concentration = (area-intercept) / slope
    if not math.isnan(concentration):
        return round(concentration, 6)
    else:
        return 0