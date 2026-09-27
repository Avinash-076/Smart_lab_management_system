"""
Smoke test to verify that the test infrastructure is operational and
client agent core modules can be imported and inspected without errors.
"""

def test_test_environment_operational():
    assert True


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
