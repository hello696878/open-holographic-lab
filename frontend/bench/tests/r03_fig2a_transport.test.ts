import { describe, expect, it, vi } from 'vitest';
import { R03_DEFAULT, R03_IDENTITY, R03_MODEL, R03_RESPONSE_CAP, createR03FetchAPI, decodeR03Result,
  validateR03Reply, type R03Envelope } from '../src/r03_fig2a_contracts';
const id = '12345678-1234-4234-8234-000000000001', sha = 'a'.repeat(64);
const sent = (): R03Envelope => ({ protocol_version: 1, message_type: 'r03_ideal_submission', request_id: id,
  experiment_sha256: sha, experiment: { ...R03_DEFAULT, mean_phase_rad: 0, phase_std_rad: 0 } });
/** Hand-state transport fixture, not a numerical benchmark or browser-generated mask. */
function wire(envelope = sent()): any { return { protocol_version: 1, message_type: 'r03_ideal_result', request_id: envelope.request_id,
  experiment_sha256: envelope.experiment_sha256, experiment: envelope.experiment,
  phase: { shape: [16, 16], order: 'C', unwrapped_rad: Array(256).fill(0), wrapped_rad: Array(256).fill(0) },
  stages: ['source', 'after_slm', 'after_qwp', 'output'].map((id, i) => ({ id,
    coherency: [[{ re: .5, im: 0 }, { re: i < 2 ? .5 : 0, im: i === 2 ? -.5 : i === 3 ? .5 : 0 }],
      [{ re: i < 2 ? .5 : 0, im: i === 2 ? .5 : i === 3 ? -.5 : 0 }, { re: .5, im: 0 }]],
    stokes: [1, 0, i < 2 ? 1 : 0, i === 2 ? 1 : i === 3 ? -1 : 0], normalized_stokes: [0, i < 2 ? 1 : 0, i === 2 ? 1 : i === 3 ? -1 : 0],
    polarized_direction: [0, i < 2 ? 1 : 0, i === 2 ? 1 : i === 3 ? -1 : 0], degree_of_polarization: 1, eigenvalues: [0, 1], roundoff_limited: false })),
  population: { infinite_gaussian_degree_of_polarization: 1, assumption: 'Explicit ideal Gaussian population reference.' },
  provenance: { model_contract: R03_MODEL, identity: R03_IDENTITY, rng_algorithm: 'PCG64', rng_normal_sampler: 'Generator.standard_normal',
    rng_draw_shape: [16, 16], sample_order: 'C', sample_count: 256, probability_weight: 1 / 256,
    measurement: 'probability_mean_uncentered_second_moment', source: 'amplitude*(1,1)/sqrt(2)', element_order: ['SLM', 'QWP', 'HWP'],
    units: { phase: 'rad', coherency: 'amplitude_unit^2', stokes: 'amplitude_unit^2', eigenvalues: 'amplitude_unit^2', normalized_stokes: 'dimensionless', polarized_direction: 'dimensionless', degree_of_polarization: 'dimensionless' }, python_version: 'fixture', numpy_version: 'fixture' },
  limitations: ['Ideal model only.', 'No physical propagation.', 'No PAX calibration.', 'No measured-data comparison.'] }; }
describe('independent ideal-model bounded wire', () => {
  it('preserves all submitted settings, phase order, complex signs and full authoritative readouts', () => {
    const raw = wire(), result = decodeR03Result(raw, sent());
    expect(result.phase.unwrapped).toHaveLength(256); expect(result.phase.wrapped).toHaveLength(256);
    expect(result.stages[2].coherency[0][1].im).toBe(-.5); expect(result.stages[3].stokes).toEqual([1, 0, 0, -1]);
    raw.phase.wrapped_rad[0] = 1; raw.stages[3].stokes[0] = 99;
    expect(result.phase.wrapped[0]).toBe(0); expect(result.stages[3].stokes[0]).toBe(1);
  });
  it.each(['request', 'digest', 'seed', 'shape', 'order', 'extra', 'phase', 'stage', 'units', 'provenance'])('rejects mismatched %s instead of attaching a different identity', what => {
    const raw = wire(); if (what === 'request') raw.request_id = id.replace(/1$/, '2'); if (what === 'digest') raw.experiment_sha256 = 'b'.repeat(64);
    if (what === 'seed') raw.experiment = { ...raw.experiment, seed: 7 }; if (what === 'shape') raw.phase.shape = [256, 1];
    if (what === 'order') raw.phase.order = 'F'; if (what === 'extra') raw.reference = {}; if (what === 'phase') raw.phase.wrapped_rad[255] = 2 * Math.PI + 1e-12;
    if (what === 'stage') raw.stages.reverse(); if (what === 'units') raw.provenance.units.stokes = 'W'; if (what === 'provenance') raw.provenance.measurement = 'coherent_field_mean';
    expect(() => decodeR03Result(raw, sent()), 'A_WHOLE_IDENTITY').toThrow();
  });
  it('dark observables remain null and raw roundoff-limited values are never clamped', () => {
    const envelope = sent(); envelope.experiment.source_amplitude = 0; const dark = wire(envelope); dark.population.infinite_gaussian_degree_of_polarization = null;
    for (const stage of dark.stages) { stage.coherency = [[{ re: 0, im: 0 }, { re: 0, im: 0 }], [{ re: 0, im: 0 }, { re: 0, im: 0 }]];
      stage.stokes = [0, 0, 0, 0]; stage.normalized_stokes = stage.polarized_direction = stage.degree_of_polarization = null; stage.eigenvalues = [0, 0]; }
    expect(decodeR03Result(dark, envelope).stages[3].degree_of_polarization).toBeNull(); dark.stages[3].degree_of_polarization = 0;
    expect(() => decodeR03Result(dark, envelope)).toThrow('dark');
    const raw = wire(); raw.stages[3].degree_of_polarization = 1 + Number.EPSILON; raw.stages[3].roundoff_limited = true;
    expect(decodeR03Result(raw, sent()).stages[3].degree_of_polarization).toBe(1 + Number.EPSILON);
  });
  it('preserves the exact NumPy modulo-roundoff endpoint without rewrapping samples', () => {
    const envelope = sent(); envelope.experiment.mean_phase_rad = -Number.MIN_VALUE;
    const raw = wire(envelope); raw.phase.unwrapped_rad.fill(-Number.MIN_VALUE); raw.phase.wrapped_rad.fill(2 * Math.PI);
    const decoded = decodeR03Result(raw, envelope); expect(decoded.phase.unwrapped[0]).toBe(-Number.MIN_VALUE);
    expect(decoded.phase.wrapped[0]).toBe(2 * Math.PI); expect(raw.phase.wrapped_rad[0]).toBe(2 * Math.PI);
  });
  it('validation is noncomputing and accepts no normalized replacement settings', () => {
    const envelope = sent(), reply = { protocol_version: 1, message_type: 'r03_ideal_validation', request_id: id, experiment_sha256: sha, experiment: envelope.experiment };
    expect(validateR03Reply(reply, envelope).experiment.seed).toBe(20261017);
    expect(() => validateR03Reply({ ...reply, experiment: { ...reply.experiment, mean_phase_rad: Math.PI } }, envelope)).toThrow('settings identity');
  });
  it('uses only the new same-origin routes with installed fetch, and no implicit retry', async () => {
    const fetch = vi.fn(async (_url: string | URL | Request, _init?: RequestInit) => new Response(JSON.stringify(wire()), { headers: { 'Content-Type': 'application/json' } }));
    const api = createR03FetchAPI(fetch as typeof globalThis.fetch); await api.simulate(sent());
    expect(fetch).toHaveBeenCalledOnce(); expect(fetch.mock.calls[0][0]).toBe('/api/research/r03-fig2a/simulate');
    expect((fetch.mock.calls[0] as unknown as [string, RequestInit])[1]).toMatchObject({ redirect: 'error', credentials: 'same-origin', method: 'POST' });
  });
  it.each(['declared', 'streamed', 'mime', 'duplicate', 'HTTP'])('fails closed on %s transport faults', async fault => {
    const response = fault === 'declared' ? new Response('{}', { headers: { 'Content-Type': 'application/json', 'Content-Length': String(R03_RESPONSE_CAP + 1) } })
      : fault === 'streamed' ? new Response(' '.repeat(R03_RESPONSE_CAP + 1), { headers: { 'Content-Type': 'application/json' } })
      : fault === 'mime' ? new Response('<html>', { headers: { 'Content-Type': 'text/html' } })
      : fault === 'duplicate' ? new Response('{"a":1,"a":2}', { headers: { 'Content-Type': 'application/json' } })
      : new Response(JSON.stringify({ error: { code: 'controlled', message: 'Controlled numerical error' } }), { status: 422, headers: { 'Content-Type': 'application/json' } });
    const fetch = vi.fn(async () => response); await expect(createR03FetchAPI(fetch as typeof globalThis.fetch).simulate(sent())).rejects.toThrow(); expect(fetch).toHaveBeenCalledOnce();
  });
});
