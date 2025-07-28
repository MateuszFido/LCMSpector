use crate::measurements::Compound;
use mzdata::spectrum::{MultiLayerSpectrum};
use ndarray::Array2;
use rayon::prelude::*;
use std::time::Instant;

/// Optimized function to construct extracted ion chromatograms (XICs) from MS data
/// 
/// This implementation uses Rayon for parallel processing of compounds and ions,
/// designed to be both thread-safe and efficient, making it suitable for both
/// single and multi-process environments.
pub fn construct_xics<'a>(
    data: &'a [MultiLayerSpectrum],
    ion_list: &'a [Compound],
    mass_accuracy: f64,
) -> Vec<Compound> {
    let start_time = Instant::now();
    println!("Starting to construct XICs...");
    
    // Process compounds in parallel using Rayon
    let compounds: Vec<Compound> = ion_list
        .par_iter()
        .map(|compound| {
            // Clone the compound for mutation
            let mut compound_clone = compound.clone();
            
            // Extract all ion names first to avoid borrowing issues
            let ion_names: Vec<String> = compound_clone.ions.keys().cloned().collect();
            
            // Process each ion and collect results
            let ion_results: Vec<(String, Option<f64>, Option<f64>)> = ion_names
                .par_iter()
                .map(|ion_name| {
                    // Process each ion independently
                    process_ion(ion_name, data, mass_accuracy)
                })
                .collect();
            
            // Update the compound with results
            for (ion_name, ms_intensity, rt) in ion_results {
                if let Some(ion_data) = compound_clone.ions.get_mut(&ion_name) {
                    ion_data.insert("MS Intensity".to_string(), ms_intensity);
                    if let Some(rt_value) = rt {
                        ion_data.insert("RT".to_string(), Some(rt_value));
                    }
                }
            }
            
            compound_clone
        })
        .collect();
    
    println!("Finished constructing XICs in {:.2?} seconds.", start_time.elapsed());
    compounds
}

/// Process a single ion 
fn process_ion(
    ion_name: &str, 
    data: &[MultiLayerSpectrum],
    mass_accuracy: f64
) -> (String, Option<f64>, Option<f64>) {
    // Calculate mass range
    let mass = ion_name
        .parse::<f64>()
        .unwrap_or_else(|e| panic!("Failed to parse mass: {e}"));
    let mass_range = (mass - 3.0 * mass_accuracy, mass + 3.0 * mass_accuracy);

    // Safeguard for mass range
    let mass_range = if mass_range.0 < 0.0 {
        (0.0, mass_range.1)
    } else {
        mass_range
    };

    // Collect intensity data for this ion efficiently
    let (intensities, scan_times) = find_matching_intensities(data, mass_range);

    // Skip processing if no intensities found
    if intensities.is_empty() {
        return (ion_name.to_string(), None, None);
    }

    // Create XIC array
    let xic_array = Array2::from_shape_vec(
        (2, intensities.len()), 
        [scan_times, intensities].concat()
    ).expect("Failed to create XIC array");

    // Get the total intensity
    let total_intensity = if xic_array.is_empty() {
        None
    } else {
        Some(xic_array.sum())
    };

    // Find max intensity index and get corresponding scan time
    let rt = if !xic_array.is_empty() && xic_array.shape()[1] >= 2 {
        let max_index = xic_array
            .column(1)
            .iter()
            .enumerate()
            .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap())
            .map(|(index, _)| index);

        if let Some(index) = max_index {
            if index < data.len() {
                Some(data[index].description.acquisition.start_time())
            } else {
                None
            }
        } else {
            None
        }
    } else {
        None
    };

    (ion_name.to_string(), total_intensity, rt)
}

/// Find all matching intensities for a given mass range efficiently
fn find_matching_intensities(
    data: &[MultiLayerSpectrum], 
    mass_range: (f64, f64)
) -> (Vec<f64>, Vec<f64>) {
    let mut intensities = Vec::new();
    let mut scan_times = Vec::new();
    
    // Reserve capacity based on an estimate to reduce reallocations
    let estimated_matches = data.len() / 10;
    intensities.reserve(estimated_matches);
    scan_times.reserve(estimated_matches);

    for spectrum in data {
        if let Some(arrays) = spectrum.arrays.as_ref() {
            let mzs = arrays.mzs().unwrap();
            let intensity_values = arrays.intensities().unwrap();
            
            let scan_time = spectrum.description.acquisition.start_time();
            
            // Linear scan for all values in the mass range
            for i in 0..mzs.len() {
                // Convert each mz value to f64 before comparison
                let mz_value = mzs[i] as f64;
                if mz_value >= mass_range.0 && mz_value <= mass_range.1 {
                    intensities.push(intensity_values[i] as f64);
                    scan_times.push(scan_time);
                }
            }
        }
    }
    
    (intensities, scan_times)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;
    use mzdata::{spectrum::SpectrumLike};
    
    #[test]
    fn test_construct_xics() {
        // open the ion list from ion_lists.json
        let ion_list_file = std::fs::File::open("ion_lists.json")
            .unwrap_or_else(|e| panic!("Couldn't open ion list file: {e}"));
        let ion_list_reader = std::io::BufReader::new(ion_list_file);
        let ion_list: serde_json::Value = serde_json::from_reader(ion_list_reader)
            .unwrap_or_else(|e| panic!("Failed to parse ion list JSON: {e}"));

        // Take short-chain fatty acids
        let ion_list = ion_list["scfas"]
            .as_object()
            .unwrap()
            .iter()
            .map(|(name, compound_data)| Compound {
                name: name.to_string(),
                ions: HashMap::from_iter(
                    compound_data["ions"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .map(|ion| (ion.to_string(), HashMap::new())),
                ),
                ion_info: compound_data["info"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .map(|info| info.as_str().unwrap().to_string())
                    .collect(),
                calibration_curve: HashMap::new(),
                ms2: Vec::new(),
            })
            .collect::<Vec<Compound>>();

        // Read data in from tests/ANIL_1mM_1_neg.mzml
        let file = std::fs::File::open("tests/ANIL_1mM_1_neg.mzml").unwrap();
        let mut reader = mzdata::MzMLReader::new(file);
        let mut data = Vec::new();
        for scan in &mut reader {
            if scan.ms_level() == 1 {
                data.push(scan);
            }
        }

        // Call construct_xics
        let result = construct_xics(&data, &ion_list, 0.0001);

        // Verify results
        assert_eq!(result.len(), 4);
        let compound = &result[0];
        assert_eq!(compound.name, "Acetate");

        let negative_mode = [59.0139, 73.0295, 87.04515];

        // Check that RT and MS Intensity have been populated
        for (ion, ion_data) in compound.ions.iter() {
            if negative_mode
                .iter()
                .any(|negative_mode_ion| ion.parse::<f64>().unwrap() == *negative_mode_ion)
            {
                assert!(ion_data.contains_key("RT"));
                assert!(ion_data.contains_key("MS Intensity"));
                assert!(ion_data.get("MS Intensity").unwrap().is_some());
            }
        }
    }
}
