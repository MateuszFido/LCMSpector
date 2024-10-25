import math

def calculate_concentration(area, curve_params):
    """
    Given the calibration curve parameters, calculate the concentration based on peak area.
    """
    slope = curve_params['Slope']
    concentration = area / slope
    if not math.isnan(concentration):
        return round(concentration, 6)
    else:
        return 0