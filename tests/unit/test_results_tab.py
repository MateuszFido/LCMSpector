import pytest
import pytestqt 
from ui.tabs.results_tab import ResultsTab

def test_tab_spawn(qtbot):

    tab = ResultsTab()
    qtbot.addWidget(tab)

    assert tab
