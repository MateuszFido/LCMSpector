# LC-Inspector Test Suite Architecture

## Overview

This test suite provides comprehensive validation for LC-Inspector's concentration calculation and calibration workflows. The tests are designed to run independently of the GUI and validate against the STMIX concentration series as ground truth.

## Key Validation Principle

**CRITICAL**: The test suite validates against the STMIX concentration series filenames as the ground truth, NOT against export.csv. Each STMIX file contains all compounds from the `aminoacids` config section at the concentration indicated in the filename:

- `STMIX_BIG_0.01mM` → All compounds at 0.01 mM
- `STMIX_BIG_0.1mM` → All compounds at 0.1 mM  
- `STMIX_BIG_2.5mM` → All compounds at 2.5 mM
- etc.

## Test Organization Structure

```
tests/
├── unit/                          # Individual component tests
│   ├── test_concentration_calc.py  # Core calculation functions
│   ├── test_calibration.py         # Calibration workflow tests
│   └── test_*.py                   # Other unit tests
├── integration/                    # Component interaction tests
│   ├── test_stmix_workflow.py      # End-to-end STMIX processing
│   └── test_*.py                   # Other integration tests
├── regression/                     # Reference data validation
│   ├── test_stmix_validation.py    # STMIX concentration validation
│   └── test_*.py                   # Other regression tests
├── fixtures/                       # Test data and utilities
│   └── test_utilities.py           # Common fixtures and validation tools
├── conftest.py                     # Pytest configuration
└── README.md                       # This documentation
```

## Test Categories

### 1. Unit Tests (`tests/unit/`)

**Purpose**: Test individual functions and methods in isolation

**Key Files**:
- [`test_concentration_calc.py`](unit/test_concentration_calc.py) - Tests core `calculate_concentration()` function
- [`test_calibration.py`](unit/test_calibration.py) - Tests calibration workflow in Model class

**Focus Areas**:
- Mathematical accuracy of concentration calculations
- Calibration curve generation and validation
- Error handling and edge cases
- Unit conversion functionality

### 2. Integration Tests (`tests/integration/`)

**Purpose**: Test interaction between multiple components in complete workflows

**Key Files**:
- [`test_stmix_workflow.py`](integration/test_stmix_workflow.py) - Complete STMIX processing pipeline

**Focus Areas**:
- End-to-end data processing workflows
- Peak area integration with concentration calculation
- Multi-threading and data pipeline integrity
- Cross-component error propagation

### 3. Regression Tests (`tests/regression/`)

**Purpose**: Validate against known reference standards and detect accuracy regressions

**Key Files**:
- [`test_stmix_validation.py`](regression/test_stmix_validation.py) - STMIX concentration accuracy validation

**Focus Areas**:
- Validation against STMIX concentration series
- Accuracy benchmarking and performance standards
- Detection rate analysis for known compounds
- Cross-concentration consistency validation

## Test Data Strategy

### Primary Reference: STMIX Concentration Series

The STMIX concentration series serves as the primary validation reference:

```python
STMIX_CONCENTRATIONS = [0.01, 0.1, 0.5, 2.5, 5.0, 10.0]  # mM
```

**Ground Truth Extraction**:
```python
# Example: Extract true concentration from filename
def parse_stmix_concentration(filename: str) -> float:
    # 'STMIX_BIG_0.01mM_pos.mzml' -> 0.01
    pattern = r'STMIX_BIG_(\d+\.?\d*)mM'
    match = re.search(pattern, filename)
    return float(match.group(1))
```

**Compound Reference**: All compounds from `config.json["aminoacids"]` (19 compounds)

### Synthetic Test Data

For controlled testing scenarios:
- Gaussian peak generation with known parameters
- Calibration series with defined noise levels
- Edge case simulation (zero concentrations, extreme values)

## Validation Criteria

### Concentration Accuracy Thresholds

```python
CONCENTRATION_TOLERANCE = {
    'relative_error': 0.15,      # ±15% for biological measurements
    'absolute_error': 0.05,      # ±0.05 mM for low concentrations
    'r_squared_min': 0.95,       # Calibration curve quality
}
```

### Integration Quality Metrics

```python
INTEGRATION_CRITERIA = {
    'snr_minimum': 3.0,          # Signal-to-noise ratio
    'quality_score_min': 0.2,    # Peak quality threshold
    'area_cv_max': 0.20,         # Coefficient of variation
    'retention_time_window': 0.1, # RT tolerance (minutes)
}
```

### Performance Benchmarks

```python
PERFORMANCE_STANDARDS = {
    'accuracy_rate_target': 0.85,     # 85% within ±15%
    'detection_rate_target': 0.80,    # 80% compound detection
    'calibration_r2_min': 0.95,       # Minimum calibration quality
}
```

## Key Test Utilities

### ConcentrationTestValidator

Provides validation methods for concentration calculations:

```python
validator = ConcentrationTestValidator()

# Validate individual concentration
is_accurate = validator.validate_concentration_accuracy(
    calculated=0.095, expected=0.1, tolerance=0.15
)

# Validate calibration curve
curve_stats = validator.validate_calibration_curve(
    x_data=[0.1, 1.0, 5.0], y_data=[1000, 10000, 50000]
)
```

### DataComparisonTools

Provides STMIX-specific validation methods:

```python
comparator = DataComparisonTools()

# Validate STMIX concentration results
validation_stats = comparator.validate_stmix_concentrations(
    results_df=test_results,
    expected_concentration=0.1,  # From filename
    known_compounds=aminoacids_compounds
)
```

## Running Tests

### Basic Test Execution

```bash
# Run all tests
pytest tests/

# Run specific test categories
pytest tests/unit/           # Unit tests only
pytest tests/integration/    # Integration tests only
pytest tests/regression/     # Regression tests only

# Run STMIX-specific tests
pytest -m stmix            # Tests marked with @pytest.mark.stmix
pytest --stmix-only        # Custom option for STMIX validation only
```

### Test Markers

Tests are automatically marked based on location and content:

```bash
pytest -m unit              # Unit tests
pytest -m integration       # Integration tests  
pytest -m regression        # Regression tests
pytest -m stmix             # STMIX-related tests
pytest -m slow              # Slow-running tests (requires --run-slow)
```

### CI/CD Integration

The test suite is designed for tiered execution in CI/CD pipelines:

```yaml
# Example CI pipeline
stages:
  - smoke_tests:      # < 2 min - Basic functionality
    - pytest tests/unit/test_concentration_calc.py
    
  - unit_tests:       # < 10 min - All unit tests
    - pytest tests/unit/
    
  - integration:      # < 30 min - Workflow validation
    - pytest tests/integration/ tests/regression/
    
  - full_validation:  # < 2 hrs - Complete STMIX validation
    - pytest tests/ --run-slow
```

## Implementation Guidelines

### Test Development Standards

1. **Naming Convention**: `test_<functionality>_<scenario>_<expected_outcome>()`
2. **Documentation**: Comprehensive docstrings with test purpose and validation criteria
3. **Assertions**: Descriptive messages with context
4. **Isolation**: Independent tests with no shared state

### Data Management

1. **File Paths**: Use relative paths from test root
2. **Mock Data**: Realistic synthetic data based on actual LC-MS characteristics
3. **Reference Data**: STMIX concentrations as ground truth
4. **Cleanup**: Automatic cleanup of temporary files

### Error Handling

1. **Expected Failures**: Use `pytest.raises()` for expected exceptions
2. **Tolerance Levels**: Multiple tolerance levels for different scenarios
3. **Graceful Degradation**: Tests should handle missing data appropriately

## Example Test Implementation

### Unit Test Example

```python
def test_calculate_concentration_linear_calibration():
    """
    Test core concentration calculation with linear calibration curve.
    
    Data: Known calibration parameters
    Expected: Exact calculation within floating point precision
    Validation: Mathematical accuracy verification
    """
    curve_params = {'slope': 1000.0, 'intercept': 500.0}
    area = 2500.0
    expected_concentration = 2.0
    
    result = calculate_concentration(area, curve_params)
    
    assert result == expected_concentration
    assert isinstance(result, float)
```

### STMIX Validation Example

```python
def test_stmix_concentration_validation(stmix_filename_parser, aminoacids_polyamines_compounds):
    """
    Validate calculated concentrations against STMIX filename ground truth.
    
    Data: STMIX file results with filename-derived true concentrations
    Expected: 85% accuracy within ±15% relative error
    Validation: Statistical validation against known compounds
    """
    filename = "STMIX_BIG_0.1mM_pos.mzml"
    true_concentration = stmix_filename_parser(filename)  # 0.1
    
    # Mock results from LC-Inspector processing
    mock_results = create_mock_stmix_results(filename, true_concentration)
    
    # Validate using STMIX-specific validation
    validator = DataComparisonTools()
    stats = validator.validate_stmix_concentrations(
        mock_results, true_concentration, aminoacids_polyamines_compounds
    )
    
    assert stats['accuracy_rate'] >= 0.85
    assert stats['detection_rate'] >= 0.80
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `lc-inspector` directory is in Python path
2. **Missing Config**: Verify `config.json` exists with `aminoacids` section
3. **Test Failures**: Check that validation thresholds match your quality requirements
4. **Slow Tests**: Use `pytest --run-slow` for complete validation suite

### Test Data Issues

1. **STMIX File Format**: Ensure filenames follow `STMIX_BIG_{concentration}mM` pattern
2. **Compound Mismatch**: Verify compound names match exactly with config.json
3. **Concentration Units**: All concentrations should be in mM (millimolar)

### Performance Issues

1. **Memory Usage**: Large datasets may require chunked processing
2. **Test Timeout**: Increase timeout for slow integration tests
3. **Parallel Execution**: Use `pytest -n auto` for parallel test execution

## Future Enhancements

### Phase 2 Implementations

1. **Performance Tests**: Scalability and speed benchmarking
2. **Cross-Platform Tests**: Windows/Linux/macOS compatibility
3. **Real Data Integration**: Tests with actual STMIX mzML files
4. **Statistical Analysis**: Advanced statistical validation methods

### Test Suite Extensions

1. **Additional Compound Lists**: Support for other config.json sections
2. **Multi-Ionization Modes**: Positive/negative mode comparison tests
3. **Retention Time Validation**: RT consistency across concentration series
4. **Matrix Effect Testing**: Sample matrix interference validation

## Support and Maintenance

### Test Maintenance

1. **Regular Validation**: Ensure STMIX reference data remains current
2. **Threshold Updates**: Adjust accuracy thresholds based on method improvements
3. **New Test Cases**: Add tests for new functionality and edge cases

### Documentation Updates

1. **Test Results**: Document validation outcomes and accuracy trends
2. **Method Changes**: Update tests when calculation methods change
3. **Configuration Updates**: Sync tests with config.json modifications

For questions and support, refer to the test implementation files and inline documentation.