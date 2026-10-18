"""Independent W1 physical-coordinate references and bounded shipped probes.

No production FFT, source, aperture, lens or coordinate helper is used by the
dense DFT reference. A testing-only observation of each transient complex field
allows complex comparisons without expanding the shipped intensity-only API.
Run from the repository root with the existing interpreter and --output DIR.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import replace
import gc
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics
import sys
import time
import tracemalloc

import numpy as np

from ohlab.optics import SequentialExperiment, run_experiment
from ohlab.optics import wave_field as wf


def example(*, n: int = 128, pitch: float = 16e-6, radius: float = 260e-6,
            focal: float = .08, terminal: float = .22) -> SequentialExperiment:
    """Explicit fixed W1 example, using SI; does not change product defaults."""
    return SequentialExperiment.from_dict({
        "schema_version": 1, "model_contract": "v0_aligned_scalar_forward_v1",
        "wavelength_m": 633e-9, "grid": {"ny": n, "nx": n, "dy": pitch, "dx": pitch},
        "source": {"kind": "gaussian", "amplitude": 1., "phase_rad": .31,
                   "waist_radius_m": 160e-6, "waist_z_m": 0., "center_x_m": 0., "center_y_m": 0.},
        "components": [{"id": "aperture", "kind": "circular_aperture", "z_m": .03, "radius_m": radius},
                       {"id": "lens", "kind": "thin_lens", "z_m": .06, "focal_length_m": focal}],
        "observation": {"id": "screen", "z_m": terminal}})


def axes(experiment: SequentialExperiment) -> tuple[np.ndarray, np.ndarray]:
    """Independent physical axes in metres, row -> +y, column -> +x."""
    g = experiment.grid
    return (np.array([(j-g.nx//2)*g.dx for j in range(g.nx)]),
            np.array([(i-g.ny//2)*g.dy for i in range(g.ny)]))


def gaussian(experiment: SequentialExperiment, z: float) -> np.ndarray:
    """Independent real width/curvature/Gouy form, including absolute phase."""
    x, y = axes(experiment)
    s = experiment.source
    r2 = (x[None, :]-s.center_x_m)**2+(y[:, None]-s.center_y_m)**2
    distance = z-s.waist_z_m
    rayleigh = math.pi*s.waist_radius_m**2/experiment.wavelength_m
    width = s.waist_radius_m*math.sqrt(1+(distance/rayleigh)**2)
    curvature_inverse = distance/(distance*distance+rayleigh*rayleigh)
    k = 2*math.pi/experiment.wavelength_m
    with np.errstate(under="ignore"):
        amplitude = s.amplitude*s.waist_radius_m/width*np.exp(-r2/width**2)
    phase = k*distance+s.phase_rad-math.atan(distance/rayleigh)+k*r2*curvature_inverse/2
    return amplitude*np.exp(1j*phase)


def lens_gaussian(experiment: SequentialExperiment, z: float) -> np.ndarray:
    """Centered paraxial lens reference with continuous complex prefactor.

    This fixture requires aperture/lens at zero and an aperture passing every
    sample. It does not apply a Gaussian envelope to a clipped field.
    """
    x, y = axes(experiment)
    source, lens = experiment.source, experiment.components[1]
    k = 2*math.pi/experiment.wavelength_m
    zr = math.pi*source.waist_radius_m**2/experiment.wavelength_m
    s0 = -source.waist_z_m
    b0 = 1+1j*s0/zr
    c0 = source.amplitude*np.exp(1j*(k*s0+source.phase_rad))/b0
    a = 1/(source.waist_radius_m**2*b0)+1j*k/(2*lens.focal_length_m)
    b = 1+2j*z*a/k
    with np.errstate(under="ignore"):
        return c0*np.exp(1j*k*z)/b*np.exp(-a*(x[None, :]**2+y[:, None]**2)/b)


def relative_l2(actual: np.ndarray, reference: np.ndarray) -> float:
    """Unfitted relative complex/intensity L2; a zero reference is undefined."""
    denominator = float(np.sum(np.abs(reference)**2))
    if denominator == 0:
        raise ValueError("reference is dark; relative L2 is undefined")
    return math.sqrt(float(np.sum(np.abs(actual-reference)**2))/denominator)


def independent_sections(experiment: SequentialExperiment,
                         interior_z_m: tuple[float, ...]) -> dict[str, np.ndarray]:
    """All W1 fields from explicit physical-coordinate dense DFT sums.

    Bounded to 256 transverse samples. Builds its own event order, upstream
    selection, source, integer frequency bins, square-root branch and masks.
    It never calls production section_plan or any numerical/grid array helper.
    """
    g = experiment.grid
    if g.nx*g.ny > 256:
        raise ValueError("independent dense reference is limited to 256 transverse samples")
    x, y = axes(experiment)
    coords = np.array([(x[j], y[i]) for i in range(g.ny) for j in range(g.nx)])
    fx = np.array([m if m < (g.nx+1)//2 else m-g.nx for m in range(g.nx)])/(g.nx*g.dx)
    fy = np.array([m if m < (g.ny+1)//2 else m-g.ny for m in range(g.ny)])/(g.ny*g.dy)
    bins = np.array([(a, b) for b in fy for a in fx])
    transform = np.exp(-2j*math.pi*(bins @ coords.T))
    k = 2*math.pi/experiment.wavelength_m
    kz = np.sqrt((k*k-(2*math.pi*bins[:, 0])**2-(2*math.pi*bins[:, 1])**2).astype(np.complex128))
    def travel(data: np.ndarray, d: float) -> np.ndarray:
        if d == 0:
            return data.copy()
        with np.errstate(under="ignore"):
            h = np.exp(1j*kz*d)
        return (transform.conj().T @ (h*(transform @ data.ravel()))/(g.nx*g.ny)).reshape(g.shape)
    data = gaussian(experiment, 0.)
    results = {"section:source": data.copy()}
    origin = 0.
    for component in experiment.components:
        for ordinal, z in enumerate(interior_z_m):
            if origin < z < component.z_m:
                results[f"section:interior:{ordinal:03d}"] = travel(data, z-origin)
        before = travel(data, component.z_m-origin)
        results[f"section:before:{component.id}"] = before.copy()
        transmission = np.empty(g.shape, np.complex128)
        for i in range(g.ny):
            for j in range(g.nx):
                xx, yy = x[j], y[i]
                if component.kind == "circular_aperture":
                    transmission[i, j] = float(xx*xx+yy*yy <= component.radius_m**2)
                elif component.kind == "rectangular_aperture":
                    transmission[i, j] = float(abs(xx) <= component.width_m/2 and abs(yy) <= component.height_m/2)
                else:
                    phase = -math.pi*(xx*xx+yy*yy)/(experiment.wavelength_m*component.focal_length_m)
                    transmission[i, j] = complex(math.cos(phase), math.sin(phase))
        data = before*transmission
        results[f"section:after:{component.id}"] = data.copy()
        origin = component.z_m
    for ordinal, z in enumerate(interior_z_m):
        if origin < z < experiment.observation.z_m:
            results[f"section:interior:{ordinal:03d}"] = travel(data, z-origin)
    results["section:observation"] = travel(data, experiment.observation.z_m-origin)
    return results


@contextmanager
def observe_complex(module=wf):
    """Testing-only capture of transient fields; restored even on exceptions."""
    captured: list[np.ndarray] = []
    original = module._plane_intensity
    def observer(field):
        captured.append(field.data.copy())
        return original(field)
    module._plane_intensity = observer
    try:
        yield captured
    finally:
        module._plane_intensity = original


def asymmetric(*, ny=11, nx=14, rectangular=True, focal=.08) -> SequentialExperiment:
    """Mixed parity, unequal pitch and off-axis source, all SI."""
    s = example(n=nx, radius=140e-6, focal=focal).to_dict()
    s['observation']['z_m'] = .0013
    s['grid'] = dict(ny=ny, nx=nx, dy=45e-6, dx=31e-6)
    s['source'].update(center_x_m=25e-6, center_y_m=-37e-6)
    s['components'][0]['z_m'] = .0003
    s['components'][1]['z_m'] = .0007
    if rectangular:
        s['components'][0] = dict(id='aperture', kind='rectangular_aperture', z_m=.0003,
                                   width_m=280e-6, height_m=224e-6)
    return SequentialExperiment.from_dict(s)


def second_moment_radius(data: np.ndarray, experiment: SequentialExperiment) -> float:
    """Centered Gaussian-only radius from its second moment, metres."""
    x, y = axes(experiment)
    intensity = data.real**2+data.imag**2
    return math.sqrt(float(2*np.sum((x[None, :]**2+y[:, None]**2)*intensity)/np.sum(intensity)))


def gaussian_fixture(*, focal=.08, terminal=.12) -> SequentialExperiment:
    """Adequate 128² window for positive/negative-lens analytic checks."""
    e = example(pitch=24e-6, radius=.01, focal=focal)
    return replace(e, components=(replace(e.components[0], z_m=0.), replace(e.components[1], z_m=0.)),
                   observation=replace(e.observation, z_m=terminal))


def numerical_report() -> dict:
    """Run the predeclared independent checks on shipped W1 code."""
    discrete = []
    for ny, nx in ((11, 14), (14, 11), (5, 6), (6, 5)):
        for rect in (False, True):
            e = asymmetric(ny=ny, nx=nx, rectangular=rect)
            zs = wf.default_interior_positions(e)
            expected = independent_sections(e, zs)
            with observe_complex() as fields:
                result = wf.sample_wave_field(e, interior_z_m=zs)
            scale = float(np.max(np.abs(expected['section:source'])))
            checks = []
            for row, actual in zip(result.planes, fields):
                reference = expected[row.id]
                error = relative_l2(actual, reference)
                np.testing.assert_allclose(actual, reference, rtol=2e-11, atol=2e-11*scale)
                assert error <= 2e-11
                checks.append(dict(id=row.id, z_m=row.z_m, relative_complex_l2=error,
                                   max_complex_error_scaled=float(np.max(np.abs(actual-reference)))/scale))
            plain = run_experiment(e)
            assert result.observation.data.tobytes() == plain.observation.data.tobytes()
            discrete.append(dict(grid=e.grid.to_dict(), aperture=e.components[0].kind,
                                 checks=checks, terminal_byte_identity=True))
    gaussians = []
    # The aperture and lens are downstream of these free-space samples.
    free = example(radius=.01).to_dict()
    free['components'][0]['z_m'] = .14
    free['components'][1]['z_m'] = .15
    e = SequentialExperiment.from_dict(free)
    with observe_complex() as fields:
        r = wf.sample_wave_field(e, interior_z_m=(.03, .06, .12))
    for row, actual in zip(r.planes, fields):
        if row.stage == 'interior':
            err = relative_l2(actual, gaussian(e, row.z_m))
            assert err <= 1e-6
            gaussians.append(dict(kind='free', z_m=row.z_m, relative_complex_l2=err, bound=1e-6))
    for focal in (.08, -.08):
        e = gaussian_fixture(focal=focal)
        with observe_complex() as fields:
            r = wf.sample_wave_field(e, interior_z_m=(.02, .04, .08))
        for row, actual in zip(r.planes, fields):
            if row.stage == 'interior' or row.stage == 'observation':
                err = relative_l2(actual, lens_gaussian(e, row.z_m))
                assert err <= 5e-5
                gaussians.append(dict(kind='lens', focal_m=focal, z_m=row.z_m,
                                      relative_complex_l2=err, bound=5e-5))
    # Same source/window, refining pitch and extending the window separately.
    # Reference larger grids are unchanged public V0, never admitted as W1.
    convergence = []
    for radius in (260e-6, 80e-6):
        e = example(radius=radius)
        r = wf.sample_wave_field(e, interior_z_m=wf.default_interior_positions(e))
        pitch = run_experiment(example(n=256, pitch=8e-6, radius=radius)).observation.intensity[::2, ::2]
        window = run_experiment(example(n=256, pitch=16e-6, radius=radius)).observation.intensity[64:192, 64:192]
        a, b = relative_l2(r.intensities[-1], pitch), relative_l2(r.intensities[-1], window)
        if radius == 260e-6:
            assert a <= .01 and b <= .01
        convergence.append(dict(radius_m=radius, pitch_relative_intensity_l2=a,
                                window_relative_intensity_l2=b,
                                interpretation='fixture-specific periodic computation; no general isolated-optics guarantee'))
    # A long free-space Gaussian remains an explicit truncation counterexample.
    e = example(radius=.01).to_dict()
    e['components'][0]['z_m'] = .22
    e['components'][1]['z_m'] = .22
    e = SequentialExperiment.from_dict(e)
    r = wf.sample_wave_field(e, interior_z_m=())
    before_lens = run_experiment(replace(e, components=())).observation.data
    long_error = relative_l2(before_lens, gaussian(e, .22))
    default = example()
    actual = wf.sample_wave_field(default, interior_z_m=wf.default_interior_positions(default))
    stage_rows = [dict(selector=s.selector, z_m=s.z_m, norm=s.norm,
                       previous_norm=s.previous_norm, signed_delta_norm=s.delta_norm,
                       transmission_ratio=s.transmission_ratio) for s in actual.canonical.stages]
    comparisons = [dict(id=p.id, z_m=p.z_m, anchor=p.anchor_selector, norm=p.norm,
                        signed_delta_norm=p.delta_norm, comparison=p.comparison,
                        on_axis_intensity=p.on_axis_intensity, max_intensity=p.max_intensity)
                   for p in actual.planes]
    return dict(discrete=discrete, gaussians=gaussians, convergence=convergence,
                default_canonical_stages=stage_rows, default_sections=comparisons,
                default_terminal_norm_exact=actual.planes[-1].norm == actual.canonical.stages[-1].norm,
                long_free_gaussian_220mm_relative_complex_l2=long_error,
                long_free_interpretation='finite-window/paraxial discrepancy retained; not required <=1e-6 at 220mm')


def working_set() -> int | None:
    """Current process working set (not traced peak), using Windows stdlib."""
    if sys.platform != 'win32':
        return None
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                    *[(name, ctypes.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize',
                       'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                       'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = (wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
    record = Counters()
    record.cb = ctypes.sizeof(record)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(record), record.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(record.WorkingSetSize)


def performance_report() -> dict:
    """Three warmed shipped sampler runs; allocation and process RSS separated."""
    e = example()
    zs = wf.default_interior_positions(e)
    wf.sample_wave_field(e, interior_z_m=zs)
    times = []
    for _ in range(3):
        gc.collect()
        started = time.perf_counter()
        result = wf.sample_wave_field(e, interior_z_m=zs)
        times.append(time.perf_counter()-started)
        del result
    before_rss = working_set()
    tracemalloc.start()
    result = wf.sample_wave_field(e, interior_z_m=zs)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    after_rss = working_set()
    median = statistics.median(times)
    assert median <= .5
    return dict(seconds=times, median_seconds=median, median_bound_seconds=.5,
                traced_current_bytes=current, traced_peak_bytes=peak,
                working_set_before_bytes=before_rss, working_set_after_bytes=after_rss,
                intensity_owned_bytes=result.intensities.nbytes,
                axes_owned_bytes=result.x_m.nbytes+result.y_m.nbytes,
                retained_canonical_complex_bytes=sum(f.data.nbytes for f in (
                    result.observation, *(s.field for s in result.canonical.recorded_fields))),
                interpretation='Tracemalloc current/peak differ from instantaneous process working set and whole-browser/GPU memory')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = Path(wf.__file__)
    report = dict(python=sys.executable, python_version=platform.python_version(), numpy=np.__version__,
                  imported_source=str(source), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  numerical=numerical_report(), performance=performance_report())
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
