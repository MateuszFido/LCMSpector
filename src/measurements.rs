use mzdata::spectrum::MultiLayerSpectrum;
use std::collections::HashMap;
use std::fmt;

pub struct MSMeasurement {
    pub mass_accuracy: f32,
    pub data: Vec<MultiLayerSpectrum>,
    pub xics: Vec<Compound>,
}

pub struct LCMeasurement {
    pub lc_scans: Vec<u32>,
}

#[derive(Debug, Clone)]
pub struct Compound {
    /// The name of the compound
    pub name: String,

    /// A dictionary of ions with their associated information
    pub ions: HashMap<String, HashMap<String, Option<f64>>>,

    /// List of MS2 data (type not specified in original, so using a generic Vec)
    pub ms2: Vec<()>,

    /// Additional ion information
    pub ion_info: Vec<String>,

    /// Calibration curve data
    pub calibration_curve: HashMap<String, f64>,
}

impl Compound {
    /// Constructor method equivalent to __init__
    pub fn new(name: String, ions: Vec<f64>, ion_info: Vec<String>) -> Self {
        Compound {
            name: name.clone(),
            ions: ions
                .into_iter()
                .map(|ion| {
                    let ion_name = format!("{ion}");
                    (
                        ion_name,
                        HashMap::from([
                            ("m/z".to_string(), Some(ion)),
                            ("RT".to_string(), None),
                            ("MS Intensity".to_string(), None),
                            ("LC Intensity".to_string(), None),
                        ]),
                    )
                })
                .collect(),
            ms2: Vec::new(),
            ion_info,
            calibration_curve: HashMap::new(),
        }
    }

    /// Create a Compound from a JSON entry in the ion lists
    pub fn from_ion_list_entry(name: String, ions: &Vec<f64>, ion_info: &Vec<String>) -> Self {
        Self::new(name, ions.clone(), ion_info.clone())
    }
}

// Optional: Implement Display trait for string representation
impl fmt::Display for Compound {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "Compound: {}, ions: {:?}, ion info: {:?}",
            self.name, self.ions, self.ion_info
        )
    }
}

impl MSMeasurement {
    /// Create an MSMeasurement from MultiLayerSpectrum data and a list of Compounds
    pub fn from_data(
        data: Vec<MultiLayerSpectrum>,
        ion_list: &Vec<Compound>,
        mass_accuracy: f32,
    ) -> Self {
        use crate::processing::construct_xics;

        let xics = construct_xics(&data, ion_list, mass_accuracy as f64);

        MSMeasurement {
            mass_accuracy,
            data,
            xics,
        }
    }
}
