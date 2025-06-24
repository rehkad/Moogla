import pytest
from moogla.server import create_app


def test_invalid_plugin_raises_import_error():
    with pytest.raises(ImportError):
        create_app(["nonexistent.module"])
