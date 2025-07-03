import subprocess
import sys
from pathlib import Path


def test_module_entrypoint():
    proc = subprocess.run([sys.executable, '-m', 'moogla', '--help'], capture_output=True, text=True)
    assert proc.returncode == 0
    assert 'Moogla command line interface' in proc.stdout
