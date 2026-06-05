"""Shared pytest configuration.

Registers the ``integration`` marker and skips those tests by default. They
download real models and run inference (slow), so run them deliberately with::

    RUN_INTEGRATION=1 uv run pytest tests/ -m integration
"""

import os

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: needs real models / hardware; slow. "
        "Skipped unless RUN_INTEGRATION=1 is set.",
    )


def pytest_collection_modifyitems(config, items):
    if os.environ.get("RUN_INTEGRATION"):
        return
    skip_integration = pytest.mark.skip(
        reason="integration test; set RUN_INTEGRATION=1 to run"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
