"""Independent V0 references and sequential optical acceptance.

Run the five large aperture cases explicitly with ``--full``. No fitted
amplitude/phase, normalization or changing ROI enters an error calculation.
References construct coordinates/frequency bins independently of production.
This module is outside the numerical core and is also used by tests/figures.
"""
from __future__ import annotations

import argparse
import gc
import json
import math
from pathlib import Path
import time
from typing import Any

import numpy as np
from scipy.special import erfc, fresnel

from ohlab import SamplingGrid

WAVELENGTH_M = 633e-9
GAUSSIAN_CASES = ((256, 4e-6), (512, 4e-6), (1024, 4e-6),
                  (512, 2e-6), (1024, 2e-6))
APERTURE_CASES = ((512, 4e-6), (1024, 4e-6), (1024, 2e-6),
                  (2048, 2e-6), (2048, 1e-6))


def physical_axes(grid: SamplingGrid) -> tuple[np.ndarray, np.ndarray]:
    """Independent center coordinates in metres; never call grid axis helpers."""
    x = np.array([(j - grid.nx // 2) * grid.dx for j in range(grid.nx)])
    y = np.array([(i - grid.ny // 2) * grid.dy for i in range(grid.ny)])
    return x, y


def physical_mesh(grid: SamplingGrid) -> tuple[np.ndarray, np.ndarray]:
    """Independent x/y broadcast meshes in metres."""
    x, y = physical_axes(grid)
    return np.broadcast_to(x[None, :], grid.shape), np.broadcast_to(y[:, None], grid.shape)


def independent_frequency_bins(n: int, pitch_m: float) -> np.ndarray:
    """DFT signed integer bins; no fftfreq or production frequency helper."""
    return np.array([m if m < (n + 1) // 2 else m - n for m in range(n)]) / (n * pitch_m)


def complex_l2(actual: np.ndarray, reference: np.ndarray,
               roi: np.ndarray | None = None) -> float:
    """sqrt(sum |actual-reference|² / sum |reference|²), without fitting."""
    u = actual if roi is None else actual[roi]
    v = reference if roi is None else reference[roi]
    denominator = float(np.sum(np.abs(v) ** 2))
    if denominator == 0.0:
        raise ValueError("complex L2 reference norm is zero; ratio is undefined")
    return math.sqrt(float(np.sum(np.abs(u - v) ** 2)) / denominator)


def sampled_norm(data: np.ndarray, grid: SamplingGrid) -> float:
    """Independent area-weighted norm, in amplitude-unit² m²."""
    return float(np.sum(data.real ** 2 + data.imag ** 2) * grid.dx * grid.dy)


def second_moment_radius(data: np.ndarray, grid: SamplingGrid) -> float:
    """Centered Gaussian 1/e-amplitude radius inferred from its second moment."""
    x, y = physical_mesh(grid)
    intensity = np.abs(data) ** 2
    total = float(np.sum(intensity))
    if total == 0.0:
        raise ValueError("second-moment radius is undefined for a dark field")
    return math.sqrt(float(2 * np.sum((x*x + y*y) * intensity)) / total)


def gaussian_reference(grid: SamplingGrid, *, wavelength_m: float, z_m: float,
                       amplitude: float = 1.0, waist_radius_m: float = 100e-6,
                       waist_z_m: float = 0.0, center_x_m: float = 0.0,
                       center_y_m: float = 0.0, phase_rad: float = 0.0) -> np.ndarray:
    """Full paraxial Gaussian via real amplitude/curvature/Gouy/carrier.

    The reference is written separately from the production rational Gaussian
    source. Time dependence is exp(-i omega t); q=s-i*zR. Units are SI.
    """
    x, y = physical_mesh(grid)
    r2 = (x - center_x_m)**2 + (y - center_y_m)**2
    s = z_m - waist_z_m
    zr = math.pi * waist_radius_m**2 / wavelength_m
    radius = waist_radius_m * math.sqrt(1 + (s/zr)**2)
    inverse_curvature = s / (s*s + zr*zr)
    k = 2*math.pi / wavelength_m
    # Expected decaying continuous-Gaussian tails may reach machine zero.
    with np.errstate(under="ignore"):
        envelope = amplitude * waist_radius_m / radius * np.exp(-r2/radius**2)
    phase = k*s + phase_rad - math.atan(s/zr) + k*r2*inverse_curvature/2
    return envelope * np.exp(1j*phase)


def lens_gaussian_reference(grid: SamplingGrid, *, wavelength_m: float,
                            z_m: float, focal_length_m: float,
                            amplitude: float = 1.0,
                            waist_radius_m: float = 100e-6,
                            waist_z_m: float = 0.0,
                            phase_rad: float = 0.0) -> np.ndarray:
    """Centered Gaussian through a lens at z=0, with its full complex prefactor.

    Let the incident Gaussian be C0 exp(-a0*r²). At the lens its coefficient
    becomes a=a0+i*k/(2*f), without changing C0. Fresnel propagation gives
    C0 exp(i*k*z)/(1+2i*z*a/k) exp(-a*r²/(1+2i*z*a/k)). This preserves the
    incident phase and amplitude at z=0; it is not merely a width reference.
    """
    x, y = physical_mesh(grid)
    k = 2*math.pi/wavelength_m
    zr = math.pi*waist_radius_m**2/wavelength_m
    s0 = -waist_z_m
    b0 = 1 + 1j*s0/zr
    a0 = 1/(waist_radius_m**2*b0)
    c0 = amplitude*np.exp(1j*(k*s0 + phase_rad))/b0
    a = a0 + 1j*k/(2*focal_length_m)
    b = 1 + 2j*z_m*a/k
    with np.errstate(under="ignore"):
        return c0*np.exp(1j*k*z_m)/b * np.exp(-a*(x*x + y*y)/b)


def rectangular_fresnel_reference(grid: SamplingGrid, *, wavelength_m: float,
                                  z_m: float, width_m: float = 80e-6,
                                  height_m: float = 120e-6,
                                  amplitude: float = 1.0,
                                  phase_rad: float = 0.0) -> np.ndarray:
    """Continuous rectangle Fresnel integral; original dimensions, absolute U.

    U=U0*exp(i*k*z)/(i*lambda*z)*Ix*Iy. Each integral is sqrt(lambda*z/2)
    times [C(hi)-C(lo)+i(S(hi)-S(lo))]. Its normalization is therefore
    U0*exp(i*k*z)/(2i); no sampled-area or peak correction is made.
    """
    x, y = physical_axes(grid)
    scale = math.sqrt(2/(wavelength_m*z_m))

    def integral(axis: np.ndarray, dimension: float) -> np.ndarray:
        hi = scale*(dimension/2 - axis)
        lo = scale*(-dimension/2 - axis)
        shi, chi = fresnel(hi)
        slo, clo = fresnel(lo)
        return (chi-clo) + 1j*(shi-slo)

    return (amplitude*np.exp(1j*(2*math.pi*z_m/wavelength_m + phase_rad))/(2j)
            * integral(y, height_m)[:, None] * integral(x, width_m)[None, :])


def fixed_roi(grid: SamplingGrid, half_width_m: float = 100e-6) -> np.ndarray:
    """Exact inclusive center selection |x|,|y|<=100 µm, without epsilon."""
    x, y = physical_mesh(grid)
    return (np.abs(x) <= half_width_m) & (np.abs(y) <= half_width_m)


def direct_dft_train(experiment: Any) -> np.ndarray:
    """Small independent complete train via explicit physical-coordinate sums.

    Independently construct space, integer frequency bins, dense Fourier
    matrices, principal-root H, source, transmissions and ordered intervals.
    No production source/component/propagator/grid-array helper is called.
    """
    grid = experiment.grid
    if grid.nx*grid.ny > 256:
        raise ValueError("direct DFT reference is bounded to at most 256 samples")
    x, y = physical_mesh(grid)
    coords = np.array([(x[i, j], y[i, j])
                       for i in range(grid.ny) for j in range(grid.nx)])
    fx = independent_frequency_bins(grid.nx, grid.dx)
    fy = independent_frequency_bins(grid.ny, grid.dy)
    frequencies = np.array([(a, b) for b in fy for a in fx])
    forward = np.exp(-2j*math.pi*(frequencies @ coords.T))
    k = 2*math.pi/experiment.wavelength_m
    kz = np.sqrt((k*k - (2*math.pi*frequencies[:, 0])**2
                  - (2*math.pi*frequencies[:, 1])**2).astype(np.complex128))

    def advance(u: np.ndarray, separation_m: float) -> np.ndarray:
        if separation_m == 0:
            return u.copy()
        with np.errstate(under="ignore"):
            transfer = np.exp(1j*kz*separation_m)
        return (forward.conj().T @ (transfer*(forward @ u.ravel()))
                / (grid.nx*grid.ny)).reshape(grid.shape)

    spec = experiment.to_dict()
    source = spec["source"]
    if source["kind"] == "uniform":
        u = np.full(grid.shape, source["amplitude"]*np.exp(1j*source["phase_rad"]),
                    dtype=np.complex128)
    else:
        u = gaussian_reference(grid, wavelength_m=experiment.wavelength_m, z_m=0,
                               amplitude=source["amplitude"],
                               waist_radius_m=source["waist_radius_m"],
                               waist_z_m=source["waist_z_m"],
                               center_x_m=source["center_x_m"],
                               center_y_m=source["center_y_m"],
                               phase_rad=source["phase_rad"])
    current_z = 0.0
    for component in spec["components"]:
        u = advance(u, component["z_m"] - current_z)
        tag = component["kind"]
        if tag == "rectangular_aperture":
            transmission = ((np.abs(x) <= component["width_m"]/2)
                            & (np.abs(y) <= component["height_m"]/2))
        elif tag == "circular_aperture":
            transmission = x*x + y*y <= component["radius_m"]**2
        elif tag == "thin_lens":
            transmission = np.exp(-1j*k*(x*x + y*y)/(2*component["focal_length_m"]))
        else:
            raise ValueError(f"unsupported reference component {tag!r}")
        u = u*transmission
        current_z = component["z_m"]
    return advance(u, spec["observation"]["z_m"] - current_z)


def experiment_spec(*, n: int = 512, pitch_m: float = 4e-6,
                    focal_length_m: float | None = None,
                    aperture_radius_m: float | None = None,
                    observation_z_m: float = .02) -> dict[str, Any]:
    """Declared centered-waist physical Gaussian fixture, in metres."""
    components: list[dict[str, Any]] = []
    if aperture_radius_m is not None:
        components.append(dict(id="aperture", kind="circular_aperture", z_m=0.0,
                               radius_m=aperture_radius_m))
    if focal_length_m is not None:
        components.append(dict(id="lens", kind="thin_lens", z_m=0.0,
                               focal_length_m=focal_length_m))
    return dict(schema_version=1, model_contract="v0_aligned_scalar_forward_v1",
                wavelength_m=WAVELENGTH_M,
                grid=dict(ny=n, nx=n, dy=pitch_m, dx=pitch_m),
                source=dict(kind="gaussian", amplitude=1.0, phase_rad=0.0,
                            waist_radius_m=100e-6, waist_z_m=0.0,
                            center_x_m=0.0, center_y_m=0.0),
                components=components, observation=dict(id="detector", z_m=observation_z_m))


def asymmetric_train_spec(ny: int = 5, nx: int = 6) -> dict[str, Any]:
    """Mixed parity/unequal pitch and separated noncommuting components."""
    spec = experiment_spec(n=nx)
    spec["grid"] = dict(ny=ny, nx=nx, dy=13e-6, dx=9e-6)
    spec["source"] = dict(kind="gaussian", amplitude=1.7, phase_rad=.31,
                          waist_radius_m=25e-6, waist_z_m=-.0004,
                          center_x_m=4e-6, center_y_m=-6e-6)
    spec["components"] = [dict(id="slit", kind="rectangular_aperture", z_m=.0013,
                               width_m=36e-6, height_m=52e-6),
                          dict(id="lens", kind="thin_lens", z_m=.0018,
                               focal_length_m=.02),
                          dict(id="stop", kind="circular_aperture", z_m=.0023,
                               radius_m=24e-6)]
    spec["observation"] = dict(id="detector", z_m=.0034)
    return spec


def sampling_diagnostics(experiment: Any, source_data: np.ndarray) -> dict[str, Any]:
    """Separate analytic/truncation/sampling indicators, never an accuracy badge."""
    grid = experiment.grid
    x, y = physical_axes(grid)
    source = experiment.to_dict()["source"]
    k = 2*math.pi/experiment.wavelength_m
    result: dict[str, Any] = dict(extent_x_m=grid.nx*grid.dx,
                                  extent_y_m=grid.ny*grid.dy,
                                  pitch_x_m=grid.dx, pitch_y_m=grid.dy,
                                  window_policy="one complete periodic window; no intermediate crop")
    if source["kind"] == "gaussian":
        s = -source["waist_z_m"]
        zr = math.pi*source["waist_radius_m"]**2/experiment.wavelength_m
        w = source["waist_radius_m"]*math.sqrt(1+(s/zr)**2)
        # Integrate outside each axis directly. Subtracting nearly-one erf
        # fractions from one erases small but physically nonzero Gaussian
        # tails (the default fixture is about 8.8e-93 outside this rectangle).
        axis_outside = []
        for axis, pitch, center in ((x, grid.dx, source["center_x_m"]),
                                     (y, grid.dy, source["center_y_m"])):
            hi = math.sqrt(2)*(axis[-1]+pitch/2-center)/w
            lo = math.sqrt(2)*(axis[0]-pitch/2-center)/w
            axis_outside.append(float((erfc(hi)+erfc(-lo))/2))
        outside_x, outside_y = axis_outside
        result["continuous_gaussian_fraction_outside_source_rectangle"] = (
            outside_x + outside_y - outside_x*outside_y)
        result["source_radius_samples_xy"] = [w/grid.dx, w/grid.dy]
    lens_records = []
    for component in experiment.to_dict()["components"]:
        if component["kind"] == "thin_lens":
            f = component["focal_length_m"]
            deltas = [float(np.max(np.abs(np.diff(-k*axis**2/(2*f)))))
                      if len(axis) > 1 else 0.0 for axis in (x, y)]
            lens_records.append(dict(id=component["id"],
                                     max_analytic_adjacent_phase_rad_xy=deltas))
    result["lens_phase_sampling"] = lens_records
    intensity = np.abs(source_data)**2
    edge = np.zeros(grid.shape, dtype=bool)
    ey, ex = max(1, grid.ny//20), max(1, grid.nx//20)
    edge[:ey, :] = edge[-ey:, :] = True
    edge[:, :ex] = edge[:, -ex:] = True
    total = float(np.sum(intensity))
    result["source_outer_five_percent_norm_fraction"] = (float(np.sum(intensity[edge]))/total
                                                        if total else None)
    fx = independent_frequency_bins(grid.nx, grid.dx)
    fy = independent_frequency_bins(grid.ny, grid.dy)
    radial = 1/experiment.wavelength_m**2 - fy[:, None]**2 - fx[None, :]**2
    propagating = radial >= 0
    spectrum = np.abs(np.fft.fft2(source_data))**2
    spectral_total = float(np.sum(spectrum))
    result["source_evanescent_spectral_norm_fraction"] = (
        float(np.sum(spectrum[~propagating]))/spectral_total if spectral_total else None)
    occupied = spectrum > (float(spectrum.max())*1e-10)
    result["occupied_threshold_relative_to_peak_spectral_intensity"] = 1e-10
    result["occupied_spectrum_stage"] = "source before all thin-element actions"
    result["occupied_bin_fraction"] = float(np.count_nonzero(occupied)/occupied.size)
    distances = np.diff([0.0] + [c["z_m"] for c in experiment.to_dict()["components"]]
                        + [experiment.observation.z_m])
    sorted_radial = radial[np.ix_(np.argsort(fy), np.argsort(fx))]
    valid = sorted_radial >= 0
    sorted_occupied = occupied[np.ix_(np.argsort(fy), np.argsort(fx))]
    kz_real = 2*math.pi*np.sqrt(np.maximum(sorted_radial, 0))
    transfer_records = []
    for separation in distances:
        maxima, occupied_maxima = [], []
        for axis in (1, 0):
            differences = np.abs(np.diff(kz_real*separation, axis=axis))
            if axis == 1:
                pairs = valid[:, :-1] & valid[:, 1:]
                opairs = sorted_occupied[:, :-1] & sorted_occupied[:, 1:] & pairs
            else:
                pairs = valid[:-1, :] & valid[1:, :]
                opairs = sorted_occupied[:-1, :] & sorted_occupied[1:, :] & pairs
            maxima.append(float(np.max(differences[pairs])) if np.any(pairs) else None)
            occupied_maxima.append(float(np.max(differences[opairs])) if np.any(opairs) else None)
        transfer_records.append(dict(distance_m=float(separation),
                                     max_analytic_propagating_phase_increment_xy=maxima,
                                     max_occupied_phase_increment_xy=occupied_maxima))
    result["transfer_phase_sampling"] = transfer_records
    result["limitations"] = ("Indicators distinguish source truncation, pitch, lens and transfer phase. "
                              "They do not prove isolated-field accuracy; window/refinement evidence is required. "
                              "Occupied-bin filtering uses the source spectrum; elements can change that spectrum.")
    return result


def validate_source_cases() -> list[dict[str, Any]]:
    from ohlab.optics import SequentialExperiment, sample_source
    records = []
    for waist_z in (.003, 0.0, -.003):
        spec = experiment_spec(n=9, pitch_m=11e-6, observation_z_m=0)
        spec["grid"] = dict(ny=8, nx=9, dy=14e-6, dx=11e-6)
        spec["source"].update(amplitude=2.3, waist_radius_m=45e-6,
                              waist_z_m=waist_z, center_x_m=5e-6,
                              center_y_m=-7e-6, phase_rad=.47)
        experiment = SequentialExperiment.from_dict(spec)
        expected = gaussian_reference(experiment.grid, wavelength_m=WAVELENGTH_M, z_m=0,
                                      **{k: v for k, v in spec["source"].items() if k != "kind"})
        actual = sample_source(experiment).data
        error = complex_l2(actual, expected)
        records.append(dict(s_m=-waist_z, relative_complex_l2=error,
                            max_absolute=float(np.max(np.abs(actual-expected))),
                            tolerance_relative=2e-11, passed=error <= 2e-11))
    return records


def validate_direct_dft() -> list[dict[str, Any]]:
    from ohlab.optics import SequentialExperiment, run_experiment
    records = []
    for ny, nx in ((5, 6), (6, 5)):
        experiment = SequentialExperiment.from_dict(asymmetric_train_spec(ny, nx))
        expected = direct_dft_train(experiment)
        actual = run_experiment(experiment).observation.data
        error = complex_l2(actual, expected)
        records.append(dict(shape=[ny, nx], relative_complex_l2=error,
                            max_absolute=float(np.max(np.abs(actual-expected))),
                            reference_norm=sampled_norm(expected, experiment.grid),
                            actual_norm=sampled_norm(actual, experiment.grid),
                            tolerance_relative=1e-10, passed=error <= 1e-10))
    return records


def validate_gaussian_cases(full: bool) -> list[dict[str, Any]]:
    from ohlab.optics import SequentialExperiment, run_experiment
    records = []
    for n, pitch in GAUSSIAN_CASES if full else ((512, 4e-6),):
        for focal in (None, .02, -.02):
            experiment = SequentialExperiment.from_dict(experiment_spec(n=n, pitch_m=pitch,
                                                                         focal_length_m=focal))
            start = time.perf_counter()
            result = run_experiment(experiment)
            elapsed = time.perf_counter()-start
            expected = (gaussian_reference(experiment.grid, wavelength_m=WAVELENGTH_M, z_m=.02)
                        if focal is None else lens_gaussian_reference(
                            experiment.grid, wavelength_m=WAVELENGTH_M, z_m=.02,
                            focal_length_m=focal))
            error = complex_l2(result.observation.data, expected)
            # The two deliberately small windows expose divergence wraparound.
            small_diverging = focal == -.02 and n*pitch < .002
            threshold = 1e-6 if focal is None else 5e-5
            records.append(dict(n=n, pitch_m=pitch, focal_length_m=focal, z_m=.02,
                                relative_complex_l2=error,
                                seconds=elapsed,
                                relative_norm_difference=abs(result.stages[-1].norm/result.stages[0].norm-1),
                                analytic_radius_m=100e-6*math.sqrt(
                                    (1 if focal is None else 1-.02/focal)**2
                                    + (.02/(math.pi*(100e-6)**2/WAVELENGTH_M))**2),
                                second_moment_radius_m=second_moment_radius(result.observation.data,
                                                                          experiment.grid),
                                acceptance_applies=not small_diverging,
                                tolerance_relative=threshold,
                                passed=(not small_diverging and error <= threshold),
                                interpretation=("small-window counterexample; not accepted as isolated optics"
                                                if small_diverging else
                                                "finite-pitch/window ASM versus paraxial Gaussian; model floor retained")))
            del result, expected, experiment
            gc.collect()
    return records


def validate_waist_scan() -> dict[str, Any]:
    from ohlab.optics import SequentialExperiment, run_experiment
    w, f = 100e-6, .02
    zr = math.pi*w*w/WAVELENGTH_M
    predicted = f/(1+(f/zr)**2)
    records = []
    for z in (predicted-.001, predicted, predicted+.001, f):
        experiment = SequentialExperiment.from_dict(experiment_spec(focal_length_m=f,
                                                                     observation_z_m=z))
        result = run_experiment(experiment)
        radius = second_moment_radius(result.observation.data, experiment.grid)
        expected_radius = w*math.sqrt((1-z/f)**2+(z/zr)**2)
        reference = lens_gaussian_reference(experiment.grid, wavelength_m=WAVELENGTH_M,
                                             z_m=z, focal_length_m=f)
        records.append(dict(z_m=z, radius_m=radius, analytic_radius_m=expected_radius,
                            relative_complex_l2=complex_l2(result.observation.data, reference)))
    minimum_detected = records[1]["radius_m"] < min(r["radius_m"] for r in
                                                   (records[0], records[2], records[3]))
    width_good = all(abs(r["radius_m"]/r["analytic_radius_m"]-1) <= 1e-4 for r in records)
    complex_good = all(r["relative_complex_l2"] <= 5e-5 for r in records)
    return dict(rayleigh_m=zr, predicted_minimum_z_m=predicted, records=records,
                passed=minimum_detected and width_good and complex_good,
                width_relative_tolerance=1e-4, complex_relative_tolerance=5e-5)


def validate_aperture_cases(full: bool) -> list[dict[str, Any]]:
    from ohlab.optics import SequentialExperiment, run_experiment
    records = []
    for n, pitch in APERTURE_CASES if full else ((512, 4e-6),):
        spec = experiment_spec(n=n, pitch_m=pitch, observation_z_m=.005)
        spec["source"] = dict(kind="uniform", amplitude=1.0, phase_rad=0.0)
        spec["components"] = [dict(id="slit", kind="rectangular_aperture", z_m=0.,
                                   width_m=80e-6, height_m=120e-6)]
        experiment = SequentialExperiment.from_dict(spec)
        start = time.perf_counter()
        result = run_experiment(experiment)
        elapsed = time.perf_counter()-start
        reference = rectangular_fresnel_reference(experiment.grid, wavelength_m=WAVELENGTH_M,
                                                    z_m=.005)
        roi = fixed_roi(experiment.grid)
        error = complex_l2(result.observation.data, reference, roi)
        sampled_area = result.stages[2].norm
        physical_area = 80e-6*120e-6
        finest = n == 2048 and pitch == 1e-6
        records.append(dict(n=n, pitch_m=pitch, extent_m=n*pitch, seconds=elapsed,
                            relative_complex_l2_roi=error, relative_complex_l2=error,
                            roi_rule="abs(x)<=100e-6 AND abs(y)<=100e-6, inclusive center coordinates",
                            roi_sample_count=int(np.count_nonzero(roi)),
                            normalization="absolute unit incident complex amplitude, continuous 80x120um aperture",
                            sampled_area_m2=sampled_area, physical_area_m2=physical_area,
                            relative_sampled_area_bias=sampled_area/physical_area-1,
                            finest_gate_applies=finest, finest_threshold=.035,
                            below_finest_threshold=error <= .035,
                            passed=finest and error <= .035,
                            limitation="Complex L2 ROI metric; not intensity, worst-pixel or universal percent accuracy."))
        print(f"aperture {n} x {n}, pitch {pitch:.9g} m: ROI complex L2 {error:.12g}", flush=True)
        del result, reference, roi, experiment
        gc.collect()
    return records


def validate_apertured_gaussian(full: bool) -> dict[str, Any]:
    """Same physical aperture/lens experiment at all windows and pitches.

    Compare only common physical sample centers in a fixed 100-µm ROI, with
    absolute fields. Differences are convergence diagnostics, not independent
    continuous truth or an unmeasured accuracy guarantee.
    """
    from ohlab.optics import SequentialExperiment, run_experiment
    saved: dict[tuple[int, float], np.ndarray] = {}
    records = []
    cases = GAUSSIAN_CASES if full else ((512, 4e-6),)
    for n, pitch in cases:
        experiment = SequentialExperiment.from_dict(experiment_spec(n=n, pitch_m=pitch,
                                                                     focal_length_m=.02,
                                                                     aperture_radius_m=80e-6))
        result = run_experiment(experiment)
        roi = fixed_roi(experiment.grid)
        x, y = physical_axes(experiment.grid)
        rows, columns = np.abs(y) <= 100e-6, np.abs(x) <= 100e-6
        selected = result.observation.data[np.ix_(rows, columns)].copy()
        saved[n, pitch] = selected
        records.append(dict(n=n, pitch_m=pitch, circular_radius_m=80e-6,
                            focal_length_m=.02, observation_z_m=.02,
                            source_norm=result.stages[0].norm,
                            after_aperture_norm=result.stages[2].norm,
                            final_norm=result.stages[-1].norm,
                            selected_roi_norm=sampled_norm(result.observation.data*roi, experiment.grid)))
        del result, roi, selected, experiment
        gc.collect()
    comparisons = []
    for first, second in (((256, 4e-6), (512, 4e-6)),
                          ((512, 4e-6), (1024, 4e-6)),
                          ((512, 2e-6), (1024, 2e-6))):
        if first in saved and second in saved:
            comparisons.append(dict(kind="larger_window_same_pitch", first=list(first), second=list(second),
                                    relative_complex_l2_roi=complex_l2(saved[first], saved[second])))
    for coarse, fine in (((256, 4e-6), (512, 2e-6)),
                         ((512, 4e-6), (1024, 2e-6))):
        if coarse in saved and fine in saved:
            # ROI axes contain symmetric -100..100 µm sample centers for both pitches.
            restricted_fine = saved[fine][::2, ::2]
            comparisons.append(dict(kind="refined_pitch_same_extent_common_centers",
                                    first=list(coarse), second=list(fine),
                                    relative_complex_l2_roi=complex_l2(saved[coarse], restricted_fine)))
    return dict(cases=records, comparisons=comparisons,
                interpretation="same fixed physical Gaussian, circle, lens and ROI; no continuous-reference claim")


def run_validation(*, full: bool) -> dict[str, Any]:
    from ohlab.optics import SequentialExperiment, sample_source
    source = validate_source_cases()
    direct = validate_direct_dft()
    gaussian = validate_gaussian_cases(full)
    waist = validate_waist_scan()
    aperture = validate_aperture_cases(full)
    apertured = validate_apertured_gaussian(full)
    experiment = SequentialExperiment.from_dict(experiment_spec(focal_length_m=.02))
    diagnostics = sampling_diagnostics(experiment, sample_source(experiment).data)
    finest = next((r for r in aperture if r["finest_gate_applies"]), None)
    gaussian_ok = all(r["passed"] for r in gaussian if r["acceptance_applies"])
    passed = (all(r["passed"] for r in source+direct) and gaussian_ok and waist["passed"]
              and (finest is not None and finest["passed"] if full else True))
    # Pointwise model estimates are separate from hard-edge sampled-area bias
    # and from the measured complex-L2 field discrepancy. They are not a bound
    # on an integrated diffraction field, whose contributions can cancel.
    max_rho2 = (100e-6+80e-6/2)**2 + (100e-6+120e-6/2)**2
    z = .005
    k = 2*math.pi/WAVELENGTH_M
    fresnel_model_estimates = dict(
        maximum_transverse_displacement_m=[140e-6, 160e-6],
        max_rho_squared_over_z_squared=max_rho2/z**2,
        maximum_quartic_path_phase_magnitude_rad=k*max_rho2**2/(8*z**3),
        exact_spherical_minus_quadratic_path_phase_rad=k*(
            math.sqrt(z*z+max_rho2)-z-max_rho2/(2*z)),
        relative_inverse_distance_amplitude_difference=1-z/math.sqrt(z*z+max_rho2),
        interpretation="Extremal geometric path/kernel estimates, not an integrated-field L2 bound or calibration.")
    return dict(validation_mode="full_required_acceptance" if full else "lightweight_checks_not_full_acceptance",
                wavelength_m=WAVELENGTH_M, source_checks=source, direct_dft=direct,
                gaussian=gaussian, waist_scan=waist, aperture_convergence=aperture,
                apertured_gaussian_convergence=apertured, diagnostics=diagnostics,
                fresnel_model_estimates=fresnel_model_estimates,
                reference_policy="independent physical coordinates/source/transmissions/direct sums; no fitting or normalization",
                acceptance_passed=passed, required_2048_finest_case_executed=finest is not None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="Run all declared cases, including 2048-grid acceptance.")
    parser.add_argument("--output", type=Path, required=True, help="Fresh owned output directory; existing paths refused.")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    report = run_validation(full=args.full)
    report["total_seconds"] = time.perf_counter()-started
    (args.output/"validation_report.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2, allow_nan=False), flush=True)
    return 0 if report["acceptance_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
