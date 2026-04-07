def test_version_exists():
    from cosmotech.example_api import __version__

    assert __version__ is not None
