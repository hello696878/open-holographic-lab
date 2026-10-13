"""V2f public-operation reuse, optional isolation and reference independence."""

import ast
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from ohlab import ComplexField, SamplingGrid
from ohlab.optics.polarization import JonesField
from ohlab.optics import polarized_interference as module
from ohlab.optics.polarized_interference import (
    PolarizerAction, RetarderAction, PolarizationArm, PolarizedTwoArmSpec,
    mix_balanced_jones, run_polarized_two_arm,
)
from scripts import validate_v2f_interference as reference

ROOT = Path(__file__).resolve().parents[1]


def field():
    grid = SamplingGrid(ny=3, nx=4, dy=4.1e-6, dx=3.7e-6)
    return JonesField(x=ComplexField(data=np.arange(12).reshape(3, 4)+1j,
                                     grid=grid, wavelength_m=633e-9),
                      y=ComplexField(data=.3-.4j*np.arange(12).reshape(3, 4),
                                     grid=grid, wavelength_m=633e-9))


def test_core_imports_and_runs_without_optional_plotting_ui_io_or_servers():
    code = r'''
import importlib.abc, sys
blocked = {'matplotlib','PIL','streamlit','plotly','pandas','pyarrow','altair','pydeck','starlette','uvicorn'}
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in blocked or fullname.startswith(('ohlab.io','apps.')):
            raise ModuleNotFoundError('blocked '+fullname)
sys.meta_path.insert(0, Block())
import ohlab, ohlab.optics
from ohlab.optics.polarization import JonesField
from ohlab.optics.polarized_interference import *
g = ohlab.SamplingGrid(ny=2,nx=3,dy=4e-6,dx=4e-6)
u = ohlab.ComplexField.uniform(grid=g,wavelength_m=633e-9)
j = JonesField.from_scalar(u,x_coefficient=1,y_coefficient=1j)
s = PolarizedTwoArmSpec(arm_0=PolarizationArm(distance_m=0),arm_1=PolarizationArm(distance_m=0),relative_phase_rad=.37)
r = run_polarized_two_arm(j,spec=s)
assert len(r.outputs)==2 and all(v.shape==(2,3) for v in r.outputs)
assert not blocked.intersection(name.split('.')[0] for name in sys.modules)
assert not any(name.startswith(('ohlab.io','ohlab.algorithms','ohlab.metrics','apps.')) for name in sys.modules)
for name in ('PolarizerAction','RetarderAction','PolarizationArm','PolarizedTwoArmSpec','PolarizedTwoArmNorms','PolarizedTwoArmResult','mix_balanced_jones','run_polarized_two_arm'):
    assert not hasattr(ohlab,name) and not hasattr(ohlab.optics,name)
print('V2F_CORE_PUBLIC_ONLY_OK')
'''
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", code],
                            cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout+result.stderr
    assert "V2F_CORE_PUBLIC_ONLY_OK" in result.stdout


def test_exact_eight_direct_public_names_and_no_new_fft_io_or_private_imports():
    assert set(module.__all__) == {"PolarizerAction", "RetarderAction", "PolarizationArm",
        "PolarizedTwoArmSpec", "PolarizedTwoArmNorms", "PolarizedTwoArmResult",
        "mix_balanced_jones", "run_polarized_two_arm"}
    tree = ast.parse((ROOT/"src/ohlab/optics/polarized_interference.py").read_text(encoding="utf-8"))
    prohibited = ("matplotlib", "PIL", "streamlit", "plotly", "pandas", "pyarrow",
                  "starlette", "uvicorn", "ohlab.io", "apps", "io", "algorithms", "metrics")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(not alias.name.startswith(prohibited) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith(prohibited)
            assert all(not alias.name.startswith("_") for alias in node.names), ast.unparse(node)
        elif isinstance(node, ast.Call):
            name = ast.unparse(node.func)
            assert "fft" not in name.lower(), name
            assert not name.endswith(("meshgrid", "angular_spectrum_transfer_function")), name
            assert name not in ("np.seterr", "numpy.seterr", "warnings.filterwarnings",
                                "warnings.simplefilter", "open", "Path.write_text", "Path.write_bytes")
            assert not name.startswith(("np.random.", "numpy.random.")), name
        elif isinstance(node, ast.Attribute):
            assert node.attr not in {"fx_fft", "fy_fft", "kx_fft", "ky_fft", "freq_meshgrid"}


def test_mixer_calls_two_public_matching_component_mixers(monkeypatch):
    first, second = field(), field()
    original = module.mix_balanced
    calls = []
    def record(a, b, *, matrix):
        calls.append((a.data.copy(), b.data.copy(), matrix))
        return original(a, b, matrix=matrix)
    monkeypatch.setattr(module, "mix_balanced", record)
    mix_balanced_jones(first, second, matrix="B_dagger")
    assert len(calls) == 2
    for call, a, b in zip(calls, (first.x, first.y), (second.x, second.y)):
        np.testing.assert_array_equal(call[0], a.data)
        np.testing.assert_array_equal(call[1], b.data)
        assert call[2] == "B_dagger"


@pytest.mark.parametrize("z0,z1", [(0., 0.), (.002, .003), (0., .002), (.002, 0.)])
def test_runner_calls_four_public_asm_in_order_with_explicit_pad_one(monkeypatch, z0, z1):
    source = field()
    original = module.propagate_angular_spectrum
    calls = []
    def record(component, *, distance_m, pad_factor):
        calls.append((component.data.copy(), component.grid, component.wavelength_m, distance_m, pad_factor))
        return original(component, distance_m=distance_m, pad_factor=pad_factor)
    monkeypatch.setattr(module, "propagate_angular_spectrum", record)
    request = PolarizedTwoArmSpec(arm_0=PolarizationArm(distance_m=z0),
        arm_1=PolarizationArm(distance_m=z1), relative_phase_rad=.37)
    run_polarized_two_arm(source, spec=request)
    assert len(calls) == 4
    for call, target, distance in zip(calls,
        (source.x.data/np.sqrt(2), source.y.data/np.sqrt(2),
         1j*source.x.data/np.sqrt(2), 1j*source.y.data/np.sqrt(2)), (z0, z0, z1, z1)):
        np.testing.assert_allclose(call[0], target, rtol=2e-14, atol=2e-14*np.max(np.abs(target)))
        assert call[1:] == (source.grid, source.wavelength_m, distance, 1)


def test_ordered_public_actions_and_same_phase_on_both_arm_one_components(monkeypatch):
    calls = []
    p, w, phase = module.apply_linear_polarizer, module.apply_linear_retarder, module.apply_uniform_phase
    def polarizer(field, *, axis_angle_rad):
        calls.append(("P", axis_angle_rad))
        return p(field, axis_angle_rad=axis_angle_rad)
    def retarder(field, *, axis_angle_rad, retardance_rad):
        calls.append(("W", axis_angle_rad, retardance_rad))
        return w(field, axis_angle_rad=axis_angle_rad, retardance_rad=retardance_rad)
    def common(field, *, phase_rad):
        calls.append(("phase", phase_rad))
        return phase(field, phase_rad=phase_rad)
    monkeypatch.setattr(module, "apply_linear_polarizer", polarizer)
    monkeypatch.setattr(module, "apply_linear_retarder", retarder)
    monkeypatch.setattr(module, "apply_uniform_phase", common)
    request = PolarizedTwoArmSpec(
        arm_0=PolarizationArm(distance_m=.002, actions=(PolarizerAction(axis_angle_rad=.13),
            RetarderAction(axis_angle_rad=-.47, retardance_rad=.83))),
        arm_1=PolarizationArm(distance_m=.003, actions=(
            RetarderAction(axis_angle_rad=.61, retardance_rad=-1.13), PolarizerAction(axis_angle_rad=-.29))),
        relative_phase_rad=-.37)
    run_polarized_two_arm(field(), spec=request)
    assert calls == [("P", .13), ("W", -.47, .83), ("W", .61, -1.13), ("P", -.29),
                     ("phase", -.37), ("phase", -.37)]


def test_direct_reference_does_not_call_production_helpers_fft_or_grid_mesh(monkeypatch):
    data = np.stack((np.arange(12).reshape(3, 4)+1j,
                     .3-.4j*np.arange(12).reshape(3, 4))).astype(np.complex128)
    args = (data, .002731, .004123, (("polarizer", .31), ("retarder", -.47, .83)),
            (("retarder", .61, -1.13), ("polarizer", -.29)), .37)
    kwargs = dict(dy=4.1e-6, dx=3.7e-6, wavelength=633e-9)
    expected = reference.direct_path(*args, **kwargs)
    def prohibited(*args, **kwargs):
        raise AssertionError("independent reference called production or FFT/grid helper")
    for owner in (module, reference):
        for name in ("mix_balanced", "mix_balanced_jones", "apply_uniform_phase",
            "apply_linear_polarizer", "apply_linear_retarder", "propagate_angular_spectrum",
            "run_polarized_two_arm", "JonesField", "ComplexField"):
            if hasattr(owner, name):
                monkeypatch.setattr(owner, name, prohibited)
    for name in ("fft", "ifft", "fft2", "ifft2", "fftfreq", "fftshift", "ifftshift"):
        monkeypatch.setattr(np.fft, name, prohibited)
    for name in ("meshgrid", "freq_meshgrid"):
        monkeypatch.setattr(SamplingGrid, name, prohibited)
    for name in ("x", "y", "fx_fft", "fy_fft", "fx_centered", "fy_centered"):
        monkeypatch.setattr(SamplingGrid, name, property(prohibited))
    actual = reference.direct_path(*args, **kwargs)
    for a, b in zip(actual, expected):
        np.testing.assert_array_equal(a, b)


def test_independent_dense_reference_is_bounded_to_sixty_four_spatial_samples():
    with pytest.raises(ValueError, match="64"):
        reference.direct_propagate(np.ones((8, 9), dtype=np.complex128), dy=4e-6,
                                   dx=4e-6, wavelength=633e-9, distance=.002)
