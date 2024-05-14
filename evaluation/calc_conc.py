import math

def calculate_concentration(area, curve_params):
    """
    Given the calibration curve parameters, calculate the concentration based on peak area.
    """
    slope = curve_params['Slope']
    intercept = curve_params['Intercept']
    concentration = (area - intercept) / slope
    if not math.isnan(concentration):
        return round(concentration, 6)
    elif concentration < 0:
        return 0
    else:
        return 0