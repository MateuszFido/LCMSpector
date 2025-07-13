# Testing Notes for LC-Inspector

This document provides notes on testing the LC-Inspector application, including common issues and best practices.

## Common Issues

### 1. Using Proper Object Types in Tests

When testing code that expects specific object types, make sure to use those types in your tests. For example, in the controller tests, we initially used strings for compounds:

```python
# Incorrect
self.model.compounds = ['compound1', 'compound2']
```

But the actual code expects Compound objects with specific attributes like `ions`. We fixed this by creating proper Compound objects:

```python
# Correct
compound1 = Compound("compound1", [123.4], ["info1"])
compound2 = Compound("compound2", [456.7], ["info2"])
self.model.compounds = [compound1, compound2]
```

### 2. Mock Reset Timing

Be careful when resetting mocks in test setup. If you reset a mock after initialization, you'll lose the call history from the initialization process:

```python
# Problematic setup
def setUp(self):
    self.model = MagicMock(spec=LCInspectorModel)
    self.view = MagicMock()
    self.controller = Controller(self.model, self.view)
    self.model.reset_mock()  # This clears call history from initialization
    self.view.reset_mock()
```

If you need to test initialization behavior, create fresh mocks for that specific test:

```python
# Better approach for testing initialization
def test_initialization(self):
    model = MagicMock(spec=LCInspectorModel)
    view = MagicMock()
    controller = Controller(model, view)
    self.assertTrue(model.on.called)  # This will work
```

## Best Practices

### 1. Use Proper Mock Specifications

When creating mocks, use the `spec` parameter to specify the interface they should implement. This helps catch errors when you try to access attributes or methods that don't exist:

```python
self.model = MagicMock(spec=LCInspectorModel)
```

### 2. Test One Thing at a Time

Each test method should test one specific behavior or feature. This makes tests easier to understand and maintain.

### 3. Use Descriptive Test Names

Name your test methods to clearly describe what they're testing. This makes it easier to understand what's being tested and what's failing when a test fails.

### 4. Use Assertions Effectively

Use the most specific assertion for the situation. For example, use `assertEqual` for checking equality, `assertTrue` for checking boolean conditions, and `assertCalled` or `assert_called_once` for checking if a mock method was called.

### 5. Isolate Tests

Tests should be independent of each other. One test should not depend on the state set up by another test. Use the `setUp` method to set up the common state for all tests, and reset or create fresh objects as needed for specific tests.
