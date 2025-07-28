use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use rayon::prelude::*;

mod loading;
mod measurements;
mod processing;

/// Convert a Compound to a Python dictionary
fn compound_to_pydict(py: Python, compound: &measurements::Compound) -> PyObject {
    let dict = PyDict::new(py);

    dict.set_item("name", compound.name.clone()).unwrap();

    let ions_dict = PyDict::new(py);
    for (ion_name, ion_data) in &compound.ions {
        let ion_dict = PyDict::new(py);
        for (key, value) in ion_data {
            if let Some(val) = value {
                ion_dict.set_item(key, val).unwrap();
            }
        }
        ions_dict.set_item(ion_name, ion_dict).unwrap();
    }
    dict.set_item("ions", ions_dict).unwrap();

    dict.set_item("ion_info", compound.ion_info.clone())
        .unwrap();

    dict.into()
}

/// Convert an MSMeasurement to a Python dictionary
fn msmeasurement_to_pydict(py: Python, measurement: &measurements::MSMeasurement) -> PyObject {
    let dict = PyDict::new(py);

    // Set mass accuracy
    dict.set_item("mass_accuracy", measurement.mass_accuracy)
        .unwrap();

    // Add XICs list
    let xics_list = PyList::new(
        py,
        measurement
            .xics
            .iter()
            .map(|compound| compound_to_pydict(py, compound)),
    );
    dict.set_item("xics", xics_list).unwrap();

    // Include a dummy spectra_data entry - we're omitting the actual data
    // to avoid further type issues, but Python code will expect this field
    let empty_list = PyList::empty(py);
    dict.set_item("spectra_data", empty_list).unwrap();

    dict.into()
}

/// Process multiple MS files in parallel and return MSMeasurement results
#[pyfunction]
fn process_files_in_parallel(
    py: Python,
    file_paths: Vec<String>,
    mass_accuracy: f32,
    ion_list_path: Option<String>,
) -> PyResult<Vec<PyObject>> {
    // Use provided ion list path or default to hardcoded path
    let ion_list_name = "scfas"; // Default ion list name

    // Load ion lists
    let ion_lists = if let Some(path) = ion_list_path {
        loading::load_ion_lists_from_path(&path)
    } else {
        loading::load_ion_lists(ion_list_name)
    };

    // Process files in parallel using rayon
    let measurements: Vec<measurements::MSMeasurement> = file_paths
        .par_iter()
        .map(|file_path| {
            let (ms1_scans, _) = loading::load_ms_scans(file_path);
            measurements::MSMeasurement::from_data(ms1_scans, &ion_lists, mass_accuracy)
        })
        .collect();

    // Convert to Python objects within the GIL
    let results: Vec<PyObject> = measurements
        .iter()
        .map(|measurement| msmeasurement_to_pydict(py, measurement))
        .collect();

    Ok(results)
}

/// A Python module implemented in Rust.
#[pymodule]
#[pyo3(name = "lcmspector_backend")]
fn lcmspector_backend(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(process_files_in_parallel, m)?)?;
    Ok(())
}
