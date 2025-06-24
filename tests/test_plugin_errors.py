import os
import pytest
from moogla.server import create_app

os.environ.setdefault("OPENAI_API_KEY", "test-key")


def test_invalid_plugin_raises_import_error():
    with pytest.raises(ImportError):
        create_app(["nonexistent.module"])
