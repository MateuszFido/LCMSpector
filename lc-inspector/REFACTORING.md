# LC-Inspector Refactoring

This document describes the refactoring of the LC-Inspector application to improve separation of concerns according to the Model-View-Controller (MVC) pattern.

## Overview

The refactoring aims to:

1. Separate the model (data and business logic) from the view (UI)
2. Implement a proper event system for communication between components
3. Make the controller a true mediator between model and view
4. Improve testability and maintainability

## Directory Structure

The refactored code introduces a new directory structure:

```
lc-inspector/
├── model/                  # Model layer
│   ├── __init__.py         # Package initialization
│   ├── base.py             # Base model class
│   ├── events.py           # Event system
│   └── lc_inspector_model.py # Main model class
├── ui/                     # View and controller layer
│   ├── controller_refactored.py # Refactored controller
│   └── view.py             # View (unchanged)
├── calculation/            # Processing logic
│   ├── calc_conc.py        # Concentration calculation
│   └── workers_refactored.py # Refactored worker threads
├── utils/                  # Utility functions
│   ├── classes.py          # Data classes
│   ├── loading.py          # Data loading
│   ├── plotting.py         # Plotting functions
│   └── preprocessing.py    # Data preprocessing
└── main_refactored.py      # Refactored entry point
```

## Key Changes

### 1. Event System

A new event system has been implemented in `model/events.py`. This allows components to subscribe to events and be notified when those events occur, reducing direct dependencies between components.

```python
# Example of using the event system
# In the model:
self.emit('processing_finished', results)

# In the controller:
self.model.on('processing_finished', self._on_processing_finished)
```

### 2. Model Layer

The model layer has been completely refactored to remove UI dependencies:

- `model/base.py`: Provides a base model class with event emission capabilities
- `model/lc_inspector_model.py`: Main model class that handles data and business logic

The model no longer directly references the view or controller, but instead emits events that the controller can listen to.

### 3. Controller Layer

The controller has been refactored to act as a true mediator between model and view:

- It subscribes to model events and updates the view accordingly
- It handles user actions from the view and updates the model
- It transforms data between model and view formats

### 4. Worker Threads

Worker threads have been refactored to focus solely on data processing, without UI dependencies:

- They emit signals that the model can listen to
- They no longer directly update the UI

## How to Use the Refactored Code

To use the refactored code, run the `main_refactored.py` script:

```bash
python main_refactored.py
```

This will start the application with the refactored components.

## Benefits of the Refactoring

1. **Improved Testability**: Each component can be tested in isolation
2. **Better Maintainability**: Changes to one component won't affect others
3. **Enhanced Flexibility**: Easier to modify or replace individual components
4. **Clearer Structure**: More organized code with clear responsibilities

## Testing Improvements

As part of the refactoring, we've added unit tests for the model and controller components. These tests demonstrate how the improved separation of concerns makes the code more testable:

1. **Model Tests**: Tests for the event system and basic model functionality
2. **Controller Tests**: Tests for the controller's interaction with the model and view
3. **Testing Notes**: A document with testing best practices and common issues

The tests use mock objects to isolate the components being tested, allowing us to test each component independently without relying on the actual implementation of other components.

## Future Improvements

While this refactoring significantly improves the separation of concerns, there are still areas that could be further improved:

1. **View Refactoring**: The view could be further refactored to remove any remaining business logic
2. **Data Transfer Objects**: Implement DTOs for communication between layers
3. **Dependency Injection**: Use dependency injection for better testability
4. **More Comprehensive Tests**: Add more tests to cover edge cases and error handling
5. **View Tests**: Add tests for the view component
