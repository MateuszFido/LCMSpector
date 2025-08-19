# LC-Inspector Processing Pipeline

Technical reference for LC/GC-MS data loading, processing, integration, and quantitation.

---

## Table of Contents

1. [Architecture](#architecture)
2. [MVC Components](#mvc-components)
3. [Application Initialization](#application-initialization)
4. [File Loading](#file-loading)
5. [Data Processing](#data-processing)
6. [Calibration and Quantitation](#calibration-and-quantitation)
7. [Peak Integration](#peak-integration)
8. [Configuration and Compound Database](#configuration-and-compound-database)
9. [Error Handling and Threads](#error-handling-and-threads)
10. [End-to-End Flow](#end-to-end-flow)

---

## Architecture

MVC application with worker threads for I/O and CPU-bound work.

```mermaid
graph TB
    subgraph "Application Layer"
        A[main.py] --> B[PyQt6 Application]
    end
    
    subgraph "MVC Architecture"
        C[Model<br/>ui/model.py] --> D[View<br/>ui/view.py]
        D --> E[Controller<br/>ui/controller.py]
        E --> C
    end
    
    subgraph "Worker Threads"
        F[LoadingWorker<br/>calculation/workers.py]
        G[ProcessingWorker<br/>calculation/workers.py]
    end
    
    subgraph "Core Processing"
        H[Data Loading<br/>utils/loading.py]
        I[Preprocessing<br/>utils/preprocessing.py]
        J[Peak Integration<br/>utils/peak_integration.py]
        K[Concentration Calc<br/>calculation/calc_conc.py]
    end
    
    subgraph "Data Structures"
        L[LCMeasurement<br/>utils/classes.py]
        M[MSMeasurement<br/>utils/classes.py]
        N[Compound<br/>utils/classes.py]
    end
    
    subgraph "Configuration"
        O[config.json<br/>Compound Database]
    end
    
    B --> C
    C --> F
    C --> G
    F --> H
    G --> I
    I --> J
    J --> K
    H --> L
    H --> M
    C --> N
    O --> C
```

---

## MVC Components

- Model (ui/model.py)
  - Holds ms_measurements, lc_measurements, annotations, compounds.
  - Starts and tracks LoadingWorker and ProcessingWorker.
  - Calibrates via linear regression (calibrate()).
  - Loads MS2 library and exports results.

- View (ui/view.py)
  - Tabs for Upload, Results, Quantitation.
  - Drag/drop (DragDropListWidget), PyQtGraph plots, progress indicators.
  - Ion/compound configuration UI.

- Controller (ui/controller.py)
  - Connects signals to model actions.
  - Orchestrates load/process/calibrate workflows.
  - Validates user input and propagates errors.

---

## Application Initialization

```mermaid
sequenceDiagram
    participant Main as main.py
    participant App as QApplication
    participant Model as Model
    participant View as View
    participant Controller as Controller
    participant Config as config.json
    
    Main->>App: QApplication()
    Main->>Model: Model()
    Model->>Config: load_ms2_library()
    Config-->>Model: MS2 library data
    Main->>View: View()
    View->>View: setupUi()
    Main->>Controller: Controller(model, view)
    Controller->>Controller: Connect signals/slots
    Main->>View: show()
    Main->>App: exec()
```

Key steps:
- configure_logging() in main.py sets file/console logging.
- Create QApplication with Fusion style.
- Instantiate Model, View, Controller.
- Load MS2 library (utils/loading.py: load_ms2_library()).
- Connect signals.

---

## File Loading

```mermaid
graph TB
    subgraph "UI"
        A[Drag & Drop / Browse] --> B[Validate Files]
    end
    
    subgraph "Controller"
        B --> D[update_file_lists]
        D --> E[model.load]
    end
    
    subgraph "Model"
        E --> F[Create LoadingWorker]
        F --> G[Start Thread]
    end
    
    subgraph "LoadingWorker"
        G --> H[ProcessPoolExecutor]
        H --> I[Parallel Load]
        I --> J[LCMeasurement]
        I --> K[MSMeasurement]
    end
    
    subgraph "Data"
        J --> L[load_absorbance_data]
        L --> M[baseline_correction]
        M --> N[_calculate_lc_peak_areas]
        
        K --> O[load_ms1_data]
        O --> P[Scan Objects]
    end
    
    subgraph "Results"
        N --> Q[LC Peak Areas]
        P --> R[MS Scans]
        Q --> S[Progress]
        R --> S
        S --> T[UI Updates]
    end
```

Details:
- Supported formats
  - LC: .txt, .csv
  - MS: .mzML
- Validation: handle_files_dropped_LC/MS in ui/view.py.
- Worker: LoadingWorker(model, mode, file_type); signals: progressUpdated, finished, error.
- Parallelism: ProcessPoolExecutor(max_workers=max(1, cpu_count-3)).
- LC: load_absorbance_data() → baseline_correction() → _calculate_lc_peak_areas().
- MS: load_ms1_data() (pyteomics.mzml) → scan list with RT index.

---

## Data Processing

```mermaid
graph TB
    subgraph "Trigger"
        A[Process Click] --> B[Validate compounds]
        B --> C[Extract from Ion Table]
    end
    
    subgraph "ProcessingWorker"
        C --> D[Create ProcessingWorker]
        D --> E[ProcessPoolExecutor]
        E --> F[Parallel XIC Build]
    end
    
    subgraph "Core"
        F --> G[construct_xics]
        G --> H[Mass Ranges]
        H --> I[Scan Intensity Extraction]
        I --> J[XIC Arrays]
        J --> K[Peak Integration]
    end
    
    subgraph "Results"
        K --> L[Peak Areas + RT]
        L --> M[Update Compound Objects]
        M --> N[Progress + UI]
    end
```

Input validation (controller.py):
```python
def process_data(self):
    self.model.compounds = self.view.ionTable.get_items()
    if not self.model.compounds:
        self.view.show_critical_error("No compounds found!")
        return
```

XIC construction (utils/preprocessing.py: construct_xics()):
```python
def construct_xics(data, ion_list, mass_accuracy, file_name):
    compounds = copy.deepcopy(ion_list)
    for compound in compounds:
        for ion in compound.ions.keys():
            mass_range = (ion-3*mass_accuracy, ion+3*mass_accuracy)
            xic = []
            for scan in data:
                idx = np.where((scan['m/z array'] >= mass_range[0]) &
                               (scan['m/z array'] <= mass_range[1]))
                intensities = scan['intensity array'][idx]
                xic.append(np.sum(intensities))
            # store xic per ion
```

Peak integration: integrate_ms_xic_peak() (utils/peak_integration.py) returns area, boundaries, and quality metrics.

---

## Calibration and Quantitation

```mermaid
graph TB
    subgraph "Setup"
        A[Select calibration files] --> B[Enter concentrations]
        B --> C[Calculate]
    end
    
    subgraph "Calibration"
        C --> D[model.calibrate]
        D --> E[Parse/convert units]
        E --> F[Extract signals]
        F --> G[Build calibration points]
        G --> H[Linear regression]
        H --> I[Store slope/intercept]
    end
    
    subgraph "Quantitation"
        I --> J[calculate_concentration]
        J --> K[Apply to samples]
        K --> L[Store results]
    end
```

Signal extraction priority (ui/model.py: calibrate()):
```python
compound_signal = 0
use_peak_areas = False
for ion in compound.ions.keys():
    ion_data = ms_file.xics[i].ions[ion]
    area = ion_data.get('MS Peak Area', {}).get('baseline_corrected_area', 0)
    if area and area > 0:
        compound_signal += area
        use_peak_areas = True
    else:
        intens = ion_data.get('MS Intensity')
        if intens is not None:
            compound_signal += float(np.round(np.sum(intens[1]), 0))
```

Concentration calculation (calculation/calc_conc.py):
```python
def calculate_concentration(area, curve_params):
    slope = curve_params['slope']
    intercept = curve_params['intercept']
    if slope == 0:
        return 0
    conc = (area - intercept) / slope
    if np.isnan(conc) or not np.isfinite(conc):
        return 0
    return round(conc, 6)
```

---

## Peak Integration

```mermaid
graph TB
    subgraph "Detection"
        A[RT / Intensity] --> B[Signal stats]
        B --> C[Prominence]
        C --> D[find_peaks]
        D --> E[Pick max]
    end
    
    subgraph "Boundaries"
        E --> F[detect_peak_boundaries]
        F --> G[Adaptive thresholds]
        G --> H[Valley/width checks]
    end
    
    subgraph "Baseline"
        H --> I[calculate_baseline_linear]
        I --> J[Interpolation + correction]
    end
    
    subgraph "Integration"
        J --> K[integrate_peak_area_trapezoidal]
        K --> L[Total + corrected area]
    end
    
    subgraph "Quality"
        L --> M[calculate_peak_quality_metrics]
        M --> N[SNR, symmetry, baseline]
    end
```

Adaptive prominence example:
```python
signal_max = np.max(corrected_values)
signal_std = np.std(corrected_values)
noise_level = np.std(corrected_values[corrected_values <= np.percentile(corrected_values, 25)])
baseline_level = np.percentile(corrected_values, 10)

prominence_threshold = max(
    5.0,
    noise_level * 4,
    signal_std * 2,
    (signal_max - baseline_level) * 0.005
)
```

Quality metrics:
- SNR estimation from lower percentile noise.
- Symmetry (USP tailing).
- Baseline stability in flanking regions.
- Combined score from the above.

---

## Configuration and Compound Database

config.json structure:
```json
{
  "Amino acids and polyamines (DEEMM)": {
    "Adenine": {
      "ions": [306.1197, 260.0779, 476.1776],
      "info": ["Adenine-D", "Adenine-NL", "Adenine-D-D"]
    }
  },
  "Short-chain fatty acids": {},
  "Flavonoids": {},
  "Terpenoids": {}
}
```

Loading flow:
```mermaid
graph LR
    A[Start] --> B[Model.__init__]
    B --> C[load_ms2_library]
    C --> D[Read config.json]
    D --> E[Parse categories/ions]
    E --> F[Populate UI]
```

---

## Error Handling and Threads

```mermaid
graph TB
    subgraph "Sources"
        A[File load]
        B[Processing]
        C[Peak integration]
        D[Calibration]
    end
    
    subgraph "Handling"
        E[Worker error signals]
        F[Safe integration wrappers]
        G[Controller handlers]
        H[User feedback]
    end
    
    A --> E
    B --> E
    C --> F
    D --> G
```

Worker example (calculation/workers.py):
```python
class LoadingWorker(QThread):
    progressUpdated = pyqtSignal(int, str)
    finished = pyqtSignal(dict, dict)
    error = pyqtSignal(str)

    def run(self):
        try:
            # load and preprocess
            self.finished.emit(lc_results, ms_results)
        except Exception as e:
            logger.error("Error in loading pool", exc_info=True)
            self.error.emit(str(e))
```

Safe integration wrapper:
```python
def safe_peak_integration(integration_func, *args, **kwargs):
    try:
        return integration_func(*args, **kwargs)
    except InsufficientDataError:
        logger.warning("Insufficient data; using fallback")
        return create_fallback_peak_area(*args)
    except Exception:
        logger.error("Peak integration failed", exc_info=True)
        return create_fallback_peak_area(*args)
```

---

## End-to-End Flow

```mermaid
graph TB
    subgraph "Init"
        A1[main.py] --> A2[QApplication]
        A2 --> A3[MVC]
        A3 --> A4[MS2/config load]
        A4 --> A5[UI show]
    end
    
    subgraph "Load"
        B1[User files] --> B2[Validate]
        B2 --> B3[LoadingWorker]
        B3 --> B4[ProcessPoolExecutor]
        B4 --> B5[LCMeasurement]
        B4 --> B6[MSMeasurement]
        B5 --> B7[Baseline]
        B6 --> B8[MS1 scans]
        B7 --> B9[LC peak areas]
        B8 --> B10[MS ready]
    end
    
    subgraph "Process"
        C1[Compounds] --> C2[Process]
        C2 --> C3[ProcessingWorker]
        C3 --> C4[XIC build]
        C4 --> C5[Mass filter]
        C5 --> C6[Peak integrate]
        C6 --> C7[Quality]
        C7 --> C8[Results]
    end
    
    subgraph "Calibrate"
        D1[Cal files] --> D2[Concentrations]
        D2 --> D3[Signals]
        D3 --> D4[Linear fit]
        D4 --> D5[Params]
        D5 --> D6[Concentrations]
        D6 --> D7[Export]
    end
    
    A5 --> B1
    B10 --> C1
    C8 --> D1
```

```mermaid
sequenceDiagram
    participant U as User
    participant V as View
    participant C as Controller
    participant M as Model
    participant LW as LoadingWorker
    participant PW as ProcessingWorker
    participant PC as Processing Core
    
    U->>V: Drag & drop
    V->>V: handle_files_dropped_*( )
    V->>M: model.load(mode, file_type)
    M->>LW: start
    LW->>PC: load_absorbance_data()/load_ms1_data()
    PC->>PC: baseline/_calculate_lc_peak_areas()
    LW->>M: finished(lc, ms)
    M->>C: on_loading_finished()
    C->>V: update
    
    U->>V: Process click
    V->>C: process_data()
    C->>M: model.process(mode)
    M->>PW: start
    PW->>PC: construct_xics()/integrate_ms_xic_peak()
    PW->>M: finished(results)
    M->>C: on_processing_finished()
    C->>V: display
    
    U->>V: Calibrate click
    C->>M: model.calibrate(selected_files)
    M->>PC: extract signals/linregress/calculate_concentration()
    M->>V: update
```
