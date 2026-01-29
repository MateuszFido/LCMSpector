"""
Tests for highlight_peak functionality and sigClicked signal handling.

These tests verify that the curve click handlers correctly pass arguments
and that highlight_peak can iterate over compound xics without errors.
"""
import numpy as np
import pytest
from unittest.mock import MagicMock, patch

import pyqtgraph as pg
from PySide6.QtCore import Signal, QObject


class MockMouseClickEvent:
    """Mock PyQtGraph MouseClickEvent for testing signal handlers."""
    pass


class MockCompound:
    """Mock Compound with ions attribute for testing highlight_peak."""
    def __init__(self, name, ions_dict):
        self.name = name
        self.ions = ions_dict


class TestHighlightPeakLambdaSignature:
    """Test that sigClicked lambda correctly captures xics, not the event."""

    def test_lambda_receives_xics_not_event(self, qapp, qtbot):
        """
        Verify the lambda pattern passes xics dict, not MouseClickEvent.

        This tests the fix for the bug where sigClicked emits (curve, event)
        and the event was overwriting the captured xics default value.
        """
        from ui.plotting import highlight_peak

        # Track what highlight_peak receives
        received_args = {}

        def mock_highlight_peak(curve, curve_list, canvas, xics):
            received_args['curve'] = curve
            received_args['curve_list'] = curve_list
            received_args['canvas'] = canvas
            received_args['xics'] = xics

        # Create test objects
        canvas = pg.PlotWidget()
        qtbot.addWidget(canvas)
        curve = pg.PlotCurveItem()
        canvas.addItem(curve)

        curve_list = {curve: "#ff0000"}
        expected_xics = [MockCompound("TestCompound", {195.0: {"RT": 1.5}})]

        # Connect using the FIXED lambda pattern (with _event parameter)
        curve.sigClicked.connect(
            lambda c, _event, xics=expected_xics: mock_highlight_peak(
                c,
                curve_list,
                canvas,
                xics,
            )
        )

        # Emit signal with (curve, event) like PyQtGraph does
        mock_event = MockMouseClickEvent()
        curve.sigClicked.emit(curve, mock_event)

        # Verify xics received is the compound list, not the event
        assert 'xics' in received_args
        assert received_args['xics'] is expected_xics
        assert not isinstance(received_args['xics'], MockMouseClickEvent)
        assert received_args['curve'] is curve

    def test_old_lambda_would_fail(self, qapp, qtbot):
        """
        Demonstrate that the OLD lambda pattern would receive event as xics.

        This documents the bug that was fixed.
        """
        received_args = {}

        def capture_args(curve, curve_list, canvas, xics):
            received_args['xics'] = xics

        canvas = pg.PlotWidget()
        qtbot.addWidget(canvas)
        curve = pg.PlotCurveItem()
        canvas.addItem(curve)

        curve_list = {curve: "#ff0000"}
        expected_xics = [MockCompound("TestCompound", {195.0: {"RT": 1.5}})]

        # OLD buggy lambda pattern (without _event parameter)
        curve.sigClicked.connect(
            lambda c, xics=expected_xics: capture_args(
                c,
                curve_list,
                canvas,
                xics,
            )
        )

        mock_event = MockMouseClickEvent()
        curve.sigClicked.emit(curve, mock_event)

        # With the OLD pattern, xics receives the event (the bug!)
        assert received_args['xics'] is mock_event
        assert isinstance(received_args['xics'], MockMouseClickEvent)


class TestHighlightPeakFunction:
    """Test highlight_peak function with valid input."""

    def test_highlight_peak_iterates_xics_without_error(self, qapp, qtbot):
        """Verify highlight_peak can iterate over compound xics without TypeError."""
        from ui.plotting import highlight_peak

        # Create canvas and curve
        canvas = pg.PlotWidget()
        qtbot.addWidget(canvas)

        # Create curve with RT data
        rt_data = np.array([1.0, 1.5, 2.0])
        intensity_data = np.array([100, 200, 150])
        curve = pg.PlotCurveItem(rt_data, intensity_data)
        canvas.addItem(curve)

        curve_list = {curve: "#ff0000"}

        # Create compound with matching RT
        compound = MockCompound(
            "Caffeine",
            {195.0877: {"RT": 1.5, "MS Intensity": 1000, "LC Intensity": 500}}
        )
        xics = [compound]

        # Should not raise TypeError
        highlight_peak(curve, curve_list, canvas, xics)

    def test_highlight_peak_with_empty_xics(self, qapp, qtbot):
        """Verify highlight_peak handles empty xics list."""
        from ui.plotting import highlight_peak

        canvas = pg.PlotWidget()
        qtbot.addWidget(canvas)

        rt_data = np.array([1.0, 1.5, 2.0])
        intensity_data = np.array([100, 200, 150])
        curve = pg.PlotCurveItem(rt_data, intensity_data)
        canvas.addItem(curve)

        curve_list = {curve: "#ff0000"}
        xics = []

        # Should not raise any exception
        highlight_peak(curve, curve_list, canvas, xics)

    def test_highlight_peak_with_multiple_compounds(self, qapp, qtbot):
        """Verify highlight_peak iterates over multiple compounds."""
        from ui.plotting import highlight_peak

        canvas = pg.PlotWidget()
        qtbot.addWidget(canvas)

        rt_data = np.array([1.0, 1.5, 2.0])
        intensity_data = np.array([100, 200, 150])
        curve = pg.PlotCurveItem(rt_data, intensity_data)
        canvas.addItem(curve)

        curve_list = {curve: "#ff0000"}

        # Multiple compounds with different RTs
        compounds = [
            MockCompound("Caffeine", {195.0: {"RT": 1.5}}),
            MockCompound("Glucose", {203.0: {"RT": 2.0}}),
            MockCompound("Aspirin", {180.0: {"RT": 3.0}}),  # No overlap
        ]

        # Should iterate all compounds without error
        highlight_peak(curve, curve_list, canvas, compounds)


class TestHighlightPeakWithMouseClickEvent:
    """Test that passing MouseClickEvent as xics raises appropriate error."""

    def test_mouse_click_event_not_iterable(self, qapp, qtbot):
        """
        Verify that passing MouseClickEvent as xics raises TypeError.

        This confirms the bug symptom that was fixed.
        """
        from ui.plotting import highlight_peak

        canvas = pg.PlotWidget()
        qtbot.addWidget(canvas)

        rt_data = np.array([1.0, 1.5, 2.0])
        intensity_data = np.array([100, 200, 150])
        curve = pg.PlotCurveItem(rt_data, intensity_data)
        canvas.addItem(curve)

        curve_list = {curve: "#ff0000"}

        # Passing event object instead of xics list
        mock_event = MockMouseClickEvent()

        with pytest.raises(TypeError, match="not iterable"):
            highlight_peak(curve, curve_list, canvas, mock_event)
