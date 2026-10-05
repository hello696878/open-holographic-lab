"""Focused V2a boundaries: optional imports excluded and public ASM reused."""

from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from ohlab import ComplexField, SamplingGrid
from ohlab.optics import interference
from ohlab.optics.interference import TwoArmSpec, run_two_arm

ROOT = Path(__file__).resolve().parents[1]


def test_interference_imports_and_runs_without_optional_plot_ui_io_servers():
    code = '''
import importlib.abc,sys
blocked={'matplotlib','PIL','streamlit','plotly','pandas','pyarrow','altair','pydeck','starlette','uvicorn'}
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in blocked or fullname.startswith(('ohlab.io','apps.')):
            raise ModuleNotFoundError('blocked '+fullname)
sys.meta_path.insert(0,Block())
import ohlab,ohlab.optics
from ohlab.optics.interference import TwoArmSpec,run_two_arm
assert not hasattr(ohlab,'run_two_arm')
assert not hasattr(ohlab.optics,'run_two_arm')
g=ohlab.SamplingGrid(ny=2,nx=3,dy=4e-6,dx=4e-6)
u=ohlab.ComplexField.uniform(grid=g,wavelength_m=633e-9)
r=run_two_arm(u,spec=TwoArmSpec(arm_0_distance_m=0,arm_1_distance_m=0,relative_phase_rad=0))
assert len(r.outputs)==2 and all(v.shape==(2,3) for v in r.outputs)
assert not blocked.intersection(s.split('.')[0] for s in sys.modules)
assert not any(s.startswith(('ohlab.io','ohlab.algorithms','ohlab.metrics','apps.')) for s in sys.modules)
print('V2A_CORE_WITHOUT_OPTIONAL_IO_SERVER_OK')
'''
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", code], cwd=ROOT,
                               env=environment, capture_output=True, text=True, timeout=30)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "V2A_CORE_WITHOUT_OPTIONAL_IO_SERVER_OK" in completed.stdout


def test_new_core_has_no_fft_or_io_or_second_transfer_function():
    path = ROOT / "src" / "ohlab" / "optics" / "interference.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = ast.unparse(node.func)
            assert "fft" not in name.lower(), name
            assert not name.endswith(("freq_meshgrid", "meshgrid", "angular_spectrum_transfer_function")), name
        if isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith(("ohlab.io", "apps", "matplotlib", "streamlit"))
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"fx_fft", "fy_fft", "kx_fft", "ky_fft", "freq_meshgrid"}


@pytest.mark.parametrize("z0,z1", [(0., 0.), (.002, .003), (0., .002), (.002, 0.)])
def test_runner_reuses_exactly_two_public_asm_calls_in_order_pad_one(monkeypatch, z0, z1):
    source = ComplexField(data=np.arange(12).reshape(3, 4).astype(np.complex128) + 1j,
                          grid=SamplingGrid(ny=3, nx=4, dy=4.1e-6, dx=3.7e-6), wavelength_m=633e-9)
    original = interference.propagate_angular_spectrum
    calls = []

    def record(field, *, distance_m, pad_factor):
        calls.append((field.grid, field.wavelength_m, distance_m, pad_factor))
        return original(field, distance_m=distance_m, pad_factor=pad_factor)

    monkeypatch.setattr(interference, "propagate_angular_spectrum", record)
    run_two_arm(source, spec=TwoArmSpec(arm_0_distance_m=z0, arm_1_distance_m=z1, relative_phase_rad=.37))
    assert calls == [(source.grid, source.wavelength_m, z0, 1), (source.grid, source.wavelength_m, z1, 1)]
