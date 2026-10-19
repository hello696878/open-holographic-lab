/** Numeric conveniences only. Every coefficient and retardance remains visible. */
import { freezePolarizationExperiment, type PolarizationExperiment, type ComplexPair } from './polarization_contracts';

const a = 1 / Math.sqrt(2);
export const COEFFICIENT_PRESETS: readonly { id: string; label: string; coefficients: ComplexPair }[] = Object.freeze([
  { id: 'x', label: 'x=(1,0), y=(0,0)', coefficients: { x: { re: 1, im: 0 }, y: { re: 0, im: 0 } } },
  { id: 'y', label: 'x=(0,0), y=(1,0)', coefficients: { x: { re: 0, im: 0 }, y: { re: 1, im: 0 } } },
  { id: 'diagonal', label: '(1,1)/√2', coefficients: { x: { re: a, im: 0 }, y: { re: a, im: 0 } } },
  { id: 'plus_i', label: '(1,+i)/√2', coefficients: { x: { re: a, im: 0 }, y: { re: 0, im: a } } },
  { id: 'minus_i', label: '(1,−i)/√2', coefficients: { x: { re: a, im: 0 }, y: { re: 0, im: -a } } },
]);
const base: PolarizationExperiment = { schema_version: 1, model_contract: 'v2d_ideal_jones_same_plane_v1', wavelength_m: 633e-9,
  grid: { ny: 64, nx: 64, dy: 4e-6, dx: 4e-6 }, source: { kind: 'uniform', amplitude: 1, phase_rad: 0 },
  coefficients: structuredClone(COEFFICIENT_PRESETS[0].coefficients), elements: [], readout: { row: 32, column: 32 } };
export const POLARIZATION_PRESETS = Object.freeze([
  { id: 'analyzer', label: 'x Input + Analyzer', experiment: freezePolarizationExperiment({ ...base,
    elements: [{ id: 'p1', kind: 'linear_polarizer', axis_angle_rad: 0 }] }) },
  { id: 'crossed', label: 'x Input + Crossed Polarizers', experiment: freezePolarizationExperiment({ ...base,
    elements: [{ id: 'p1', kind: 'linear_polarizer', axis_angle_rad: 0 }, { id: 'p2', kind: 'linear_polarizer', axis_angle_rad: Math.PI / 2 }] }) },
  { id: 'middle', label: 'x Input + Intermediate 45° Polarizer', experiment: freezePolarizationExperiment({ ...base,
    elements: [{ id: 'p1', kind: 'linear_polarizer', axis_angle_rad: 0 }, { id: 'pm', kind: 'linear_polarizer', axis_angle_rad: Math.PI / 4 },
      { id: 'p2', kind: 'linear_polarizer', axis_angle_rad: Math.PI / 2 }] }) },
  { id: 'qwp', label: 'Diagonal Input + QWP (δ=π/2)', experiment: freezePolarizationExperiment({ ...base,
    coefficients: structuredClone(COEFFICIENT_PRESETS[2].coefficients), elements: [{ id: 'w1', kind: 'linear_retarder', axis_angle_rad: 0, retardance_rad: Math.PI / 2 }] }) },
  { id: 'hwp', label: 'x Input + HWP (θ=π/8, δ=π)', experiment: freezePolarizationExperiment({ ...base,
    elements: [{ id: 'w1', kind: 'linear_retarder', axis_angle_rad: Math.PI / 8, retardance_rad: Math.PI }] }) },
  { id: 'identity', label: 'Empty Train · Identity', experiment: freezePolarizationExperiment(base) },
]);
export function polarizationPreset(id: string): PolarizationExperiment {
  const preset = POLARIZATION_PRESETS.find(item => item.id === id);
  if (!preset) throw new Error(`Unknown polarization preset: ${id}`);
  return structuredClone(preset.experiment);
}
