import { cloneTwoPathExperiment, freezeTwoPathExperiment, type TwoPathExperiment } from './two_path_contracts';

const wavelength = 633e-9;
const uniform: TwoPathExperiment = { wavelength_m: wavelength, grid: { ny: 64, nx: 64, dy: 4e-6, dx: 4e-6 },
  source: { kind: 'uniform', amplitude: 1, phase_rad: 0 },
  two_arm_spec: { arm_0_distance_m: 2e-3, arm_1_distance_m: 2e-3, relative_phase_rad: 0 } };
export const TWO_PATH_PRESETS: readonly { id: string; label: string; experiment: TwoPathExperiment }[] = Object.freeze([
  { id: 'uniform64', label: '64×64 均勻光・等長双臂', experiment: freezeTwoPathExperiment(uniform) },
  { id: 'gaussian128', label: '128×128 Gaussian・等長双臂', experiment: freezeTwoPathExperiment({ ...uniform,
    grid: { ny: 128, nx: 128, dy: 4e-6, dx: 4e-6 },
    source: { kind: 'gaussian', amplitude: 1, phase_rad: 0, waist_radius_m: 40e-6, waist_z_m: 0, center_x_m: 12e-6, center_y_m: -8e-6 } }) },
  { id: 'unequal64', label: '64×64 均勻光・不等長載波案例', experiment: freezeTwoPathExperiment({ ...uniform,
    two_arm_spec: { arm_0_distance_m: wavelength / 7, arm_1_distance_m: wavelength / 7 + wavelength / 6, relative_phase_rad: 0 } }) },
]);
export function twoPathPreset(id: string): TwoPathExperiment {
  const preset = TWO_PATH_PRESETS.find(item => item.id === id);
  if (!preset) throw new Error(`Unknown two-path preset: ${id}`);
  return cloneTwoPathExperiment(preset.experiment);
}
