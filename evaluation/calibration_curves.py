import os
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import pearsonr
from statistics import linear_regression
from pathlib import Path
#FIXME: How is this different from cal_curves? 
def calibrate(all_compounds, file_path):
    compounds_df = pd.DataFrame(
        {'Name': [compound.name for compound in all_compounds],
        'Concentration (mM)': [compound.concentration for compound in all_compounds],
        'Area': [compound.area for compound in all_compounds]})

    # Create and plot individual calibration curves in separate subplots
    unique_compounds = compounds_df['Name'].unique()
    num_compounds = len(unique_compounds)
    plt.figure(figsize=(15, 10))

    # Create the "plots" directory if it doesn't exist
    cal_dir = Path(file_path / 'plots' / 'calibration_curves')
    os.makedirs(cal_dir, exist_ok=True)
    
    slope_intercept_values = {}

    for idx, compound_name in enumerate(unique_compounds, start=1):
        plt.figure(figsize=(8, 6))
        plt.scatter(compounds_df.loc[compounds_df['Name'] == compound_name, 'Concentration (mM)'],
                    compounds_df.loc[compounds_df['Name'] == compound_name, 'Area'],
                    label=f'{compound_name} Calibration Curve',
                    color=plt.cm.jet(idx / num_compounds))
        
        # Fit a linear equation to the concentration-peak area relationship
        slope = linear_regression(compounds_df.loc[compounds_df['Name'] == compound_name, 'Concentration (mM)'],
                                               compounds_df.loc[compounds_df['Name'] == compound_name, 'Area'], proportional=True)[0]

        slope_intercept_values[compound_name] = {'Slope': round(slope, 2), 'R-squared': round(pearsonr(compounds_df.loc[compounds_df['Name'] == compound_name, 
        'Concentration (mM)'], compounds_df.loc[compounds_df['Name'] == compound_name, 'Area'])[0] ** 2, 4)}
        
        # Plot the fitted curve
        plt.plot(compounds_df.loc[compounds_df['Name'] == compound_name, 'Concentration (mM)'],
                 slope * compounds_df.loc[compounds_df['Name'] == compound_name, 'Concentration (mM)'],
                 color='black', linestyle='--',
                 label=f'Fit: y = {slope:.4f}x')

        plt.title(f'{compound_name} Calibration Curve')
        plt.xlabel('Concentration (mM)')
        plt.ylabel('Peak Area')
        plt.legend()
        
        # Save the plot as a PNG file
        plt.savefig(os.path.join(cal_dir, f'{compound_name}_calibration_curve.png'))
        plt.close()

    return slope_intercept_values