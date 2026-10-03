"""
Smoke test to verify that the test infrastructure is operational and
client agent core modules can be imported and inspected without errors.
"""

def test_test_environment_operational():
    import sys
    import psutil
    import requests
    import websocket

    assert sys.version_info >= (3, 13), f"Python 3.13+ required, got {sys.version}"
    assert hasattr(psutil, "__version__")
    assert hasattr(requests, "__version__")
    assert hasattr(websocket, "__version__")


def test_core_config_importable():
    import config

    assert hasattr(config, "CLIENT_NAME")
    assert hasattr(config, "VERSION")
    assert hasattr(config, "MONITOR_INTERVAL")
    assert config.MONITOR_INTERVAL > 0


def test_core_paths_importable():
    import paths

    assert hasattr(paths, "BASE_PATH")
    assert hasattr(paths, "LOG_FOLDER")
