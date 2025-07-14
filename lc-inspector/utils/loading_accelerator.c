#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>

// Structure to hold MS scan data
typedef struct {
    double rt;
    double *mz_array;
    double *intensity_array;
    size_t array_size;
    int ms_level;
} MSScan;

// Structure to hold CSV data
typedef struct {
    double *time_values;
    double *intensity_values;
    size_t size;
    size_t capacity;
} CSVData;

// Fast delimiter detection
static char detect_delimiter_fast(const char *line) {
    if (strchr(line, ',')) return ',';
    if (strchr(line, '\t')) return '\t';
    if (strchr(line, ' ')) return ' ';
    return '\0';
}

// Fast CSV parser for absorbance data
static CSVData* parse_csv_fast(const char *filepath) {
    FILE *file = fopen(filepath, "r");
    if (!file) {
        PyErr_SetString(PyExc_FileNotFoundError, "Could not open file");
        return NULL;
    }
    
    CSVData *data = malloc(sizeof(CSVData));
    if (!data) {
        fclose(file);
        PyErr_SetString(PyExc_MemoryError, "Could not allocate memory for CSV data");
        return NULL;
    }
    
    data->capacity = 1000;
    data->size = 0;
    data->time_values = malloc(data->capacity * sizeof(double));
    data->intensity_values = malloc(data->capacity * sizeof(double));
    
    if (!data->time_values || !data->intensity_values) {
        free(data->time_values);
        free(data->intensity_values);
        free(data);
        fclose(file);
        PyErr_SetString(PyExc_MemoryError, "Could not allocate memory for arrays");
        return NULL;
    }
    
    char line[1024];
    char delimiter = '\0';
    
    // Detect delimiter from first few lines
    for (int i = 0; i < 5 && fgets(line, sizeof(line), file); i++) {
        char detected = detect_delimiter_fast(line);
        if (detected != '\0') {
            if (delimiter == '\0') {
                delimiter = detected;
            } else if (delimiter != detected) {
                // Multiple delimiters detected - use comma as default
                delimiter = ',';
                break;
            }
        }
    }
    
    if (delimiter == '\0') delimiter = ','; // Default fallback
    
    // Reset file pointer
    rewind(file);
    
    // Parse data
    int line_count = 0;
    while (fgets(line, sizeof(line), file)) {
        line_count++;
        
        char *token;
        char *line_copy = strdup(line);
        if (!line_copy) continue;
        
        // Get first column (time)
        token = strtok(line_copy, &delimiter);
        if (!token) {
            free(line_copy);
            continue;
        }
        
        char *endptr;
        double time_val = strtod(token, &endptr);
        if (endptr == token) {
            // Skip header row and invalid time values
            free(line_copy);
            continue;
        }
        
        // Find last column (intensity)
        char *last_token = token;
        while ((token = strtok(NULL, &delimiter)) != NULL) {
            last_token = token;
        }
        
        double intensity_val = strtod(last_token, &endptr);
        if (endptr == last_token) {
            // Skip invalid intensity values
            free(line_copy);
            continue;
        }
        
        // Resize arrays if needed
        if (data->size >= data->capacity) {
            data->capacity *= 2;
            data->time_values = realloc(data->time_values, data->capacity * sizeof(double));
            data->intensity_values = realloc(data->intensity_values, data->capacity * sizeof(double));
            
            if (!data->time_values || !data->intensity_values) {
                free(line_copy);
                break;
            }
        }
        
        data->time_values[data->size] = time_val;
        data->intensity_values[data->size] = intensity_val;
        data->size++;
        
        free(line_copy);
    }
    
    fclose(file);
    return data;
}

// Python wrapper for fast CSV loading
static PyObject* load_absorbance_data_fast(PyObject *self, PyObject *args) {
    const char *filepath;
    if (!PyArg_ParseTuple(args, "s", &filepath)) {
        return NULL;
    }
    
    CSVData *data = parse_csv_fast(filepath);
    if (!data) {
        return NULL;
    }
    
    // Create Python lists
    PyObject *time_list = PyList_New(data->size);
    PyObject *intensity_list = PyList_New(data->size);
    
    if (!time_list || !intensity_list) {
        Py_XDECREF(time_list);
        Py_XDECREF(intensity_list);
        free(data->time_values);
        free(data->intensity_values);
        free(data);
        return NULL;
    }
    
    for (size_t i = 0; i < data->size; i++) {
        PyList_SET_ITEM(time_list, i, PyFloat_FromDouble(data->time_values[i]));
        PyList_SET_ITEM(intensity_list, i, PyFloat_FromDouble(data->intensity_values[i]));
    }
    
    // Create pandas DataFrame equivalent structure
    PyObject *pandas_module = PyImport_ImportModule("pandas");
    if (!pandas_module) {
        Py_DECREF(time_list);
        Py_DECREF(intensity_list);
        free(data->time_values);
        free(data->intensity_values);
        free(data);
        return NULL;
    }
    
    PyObject *dataframe_class = PyObject_GetAttrString(pandas_module, "DataFrame");
    PyObject *dict = PyDict_New();
    PyDict_SetItemString(dict, "Time (min)", time_list);
    PyDict_SetItemString(dict, "Value (mAU)", intensity_list);
    
    PyObject *result = PyObject_CallFunctionObjArgs(dataframe_class, dict, NULL);
    
    // Cleanup
    Py_DECREF(pandas_module);
    Py_DECREF(dataframe_class);
    Py_DECREF(dict);
    Py_DECREF(time_list);
    Py_DECREF(intensity_list);
    free(data->time_values);
    free(data->intensity_values);
    free(data);
    
    return result;
}

// Fast string processing for MS2 library
static PyObject* process_msp_line_fast(PyObject *self, PyObject *args) {
    const char *line;
    if (!PyArg_ParseTuple(args, "s", &line)) {
        return NULL;
    }
    
    // Fast check for "Name: " prefix
    if (strncmp(line, "Name: ", 6) == 0) {
        const char *name_start = line + 6;
        // Find end of line
        const char *name_end = strchr(name_start, '\n');
        if (!name_end) name_end = name_start + strlen(name_start);
        
        // Create Python string
        return PyUnicode_FromStringAndSize(name_start, name_end - name_start);
    }
    
    Py_RETURN_NONE;
}

// Fast numeric parsing for peak detection
static PyObject* parse_numeric_fast(PyObject *self, PyObject *args) {
    const char *str;
    if (!PyArg_ParseTuple(args, "s", &str)) {
        return NULL;
    }
    
    char *endptr;
    double value = strtod(str, &endptr);
    
    if (endptr == str) {
        // No conversion performed
        Py_RETURN_NONE;
    }
    
    return PyFloat_FromDouble(value);
}

// Method definitions
static PyMethodDef LoadingAcceleratorMethods[] = {
    {"load_absorbance_data_fast", load_absorbance_data_fast, METH_VARARGS,
     "Fast CSV parser for absorbance data"},
    {"process_msp_line_fast", process_msp_line_fast, METH_VARARGS,
     "Fast MSP line processing"},
    {"parse_numeric_fast", parse_numeric_fast, METH_VARARGS,
     "Fast numeric parsing"},
    {NULL, NULL, 0, NULL}
};

// Module definition
static struct PyModuleDef loadingacceleratormodule = {
    PyModuleDef_HEAD_INIT,
    "loading_accelerator",
    "C extensions for loading module performance optimization",
    -1,
    LoadingAcceleratorMethods
};

// Module initialization
PyMODINIT_FUNC PyInit_loading_accelerator(void) {
    return PyModule_Create(&loadingacceleratormodule);
}
