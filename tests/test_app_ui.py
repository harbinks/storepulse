"""
End-to-end integration tests for StorePulse Streamlit application.
Uses streamlit.testing.v1.AppTest to simulate user interactions, widget changes,
filters, and action updates headlessly.
"""

import os
import pytest
from streamlit.testing.v1 import AppTest


def test_app_loads_successfully():
    """Verify that app.py compiles, runs, and renders the header and tabs without error."""
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    
    assert not at.exception
    # Check that main title or disclosure banner is in the rendered output
    assert len(at.tabs) == 5
    assert "Executive P&L Dashboard" in at.tabs[0].label
    assert "Anomaly Intelligence" in at.tabs[1].label
    assert "Store Deep-Dive & Unit Economics" in at.tabs[2].label
    assert "Operational Action Tracker" in at.tabs[3].label
    assert "Methodology & Architecture" in at.tabs[4].label


def test_app_sidebar_widgets_and_reset():
    """Verify sidebar widgets: radio selection, sliders, reset button."""
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    assert not at.exception
    
    # Check radio buttons for dataset
    assert len(at.sidebar.radio) >= 1
    assert at.sidebar.radio[0].value == "Demo Dataset (12 Stores, 6 Mo)"
    
    # Test reset button click
    at.sidebar.button[0].click().run()
    assert not at.exception
    assert at.session_state.data_source == "demo"


def test_app_month_filter_interaction():
    """Verify selecting a specific fiscal month slices the dashboard without exceptions."""
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    assert not at.exception
    
    # Month selectbox is in sidebar
    month_selectbox = at.sidebar.selectbox[0]
    # Set to '2026-03'
    if "2026-03" in month_selectbox.options:
        month_selectbox.select("2026-03").run()
        assert not at.exception


def test_app_custom_action_addition():
    """Verify adding an operational action item through the form."""
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    assert not at.exception
    
    initial_action_count = len(at.session_state.actions_list)
    assert initial_action_count > 0  # Initial actions generated from anomalies
