"""The original R compatibility interface must remain usable without torch."""

import subprocess
import sys


def test_reference_import_does_not_attempt_to_load_torch():
    code = """
import importlib.abc
import sys
class NoTorch(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname == 'torch' or fullname.startswith('torch.'):
            raise ModuleNotFoundError('Torch deliberately unavailable', name='torch')
sys.meta_path.insert(0, NoTorch())
import amelia_torch
from amelia_torch import amelia_reference, read_reference_rds
assert 'torch' not in sys.modules
try:
    from amelia_torch import em_fit
except ImportError as error:
    assert 'official PyTorch selector' in str(error)
else:
    raise AssertionError('Native EM must require torch explicitly')
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
