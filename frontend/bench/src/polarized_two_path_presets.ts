/** Explicit parameter presets; no coefficient normalization or alternate optics. */
import { freezePolarizedTwoPathExperiment, type PolarizedTwoPathExperiment } from './polarized_two_path_contracts';
const base: PolarizedTwoPathExperiment = { schema_version: 1, model_contract: 'v2g_ideal_polarized_two_path_v1', wavelength_m: 633e-9,
  grid: { ny: 64, nx: 64, dy: 4e-6, dx: 4e-6 }, source: { kind: 'uniform', amplitude: 1, phase_rad: 0 },
  coefficients: { x: { re: 1, im: 0 }, y: { re: 0, im: 0 } }, arm_0: { distance_m: .002, actions: [] },
  arm_1: { distance_m: .002, actions: [] }, relative_phase_rad: 0, analyzer: { enabled: false, axis_angle_rad: Math.PI / 4 } };
const orthogonal: PolarizedTwoPathExperiment = { ...base, arm_1: { distance_m: .002,
  actions: [{ id: 'hwp1', kind: 'linear_retarder', axis_angle_rad: Math.PI / 4, retardance_rad: Math.PI }] } };
export const POLARIZED_TWO_PATH_PRESETS = Object.freeze([
  { id: 'identical', label: 'Equal-Length Arms · Identical Polarization', experiment: freezePolarizedTwoPathExperiment(base) },
  { id: 'orthogonal', label: 'Orthogonal Arms · Raw Outputs', experiment: freezePolarizedTwoPathExperiment(orthogonal) },
  { id: 'orthogonal_analyzed', label: 'Orthogonal Arms + Shared 45° Analyzer', experiment: freezePolarizedTwoPathExperiment({ ...orthogonal, analyzer: { enabled: true, axis_angle_rad: Math.PI / 4 } }) },
]);
export function polarizedTwoPathPreset(id: string): PolarizedTwoPathExperiment {
  const preset = POLARIZED_TWO_PATH_PRESETS.find(item => item.id === id); if (!preset) throw new Error(`Unknown polarized two-path preset ${id}`); return structuredClone(preset.experiment);
}
