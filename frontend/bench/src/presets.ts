import { cloneExperiment, freezeExperiment, type Experiment } from './contracts';

const base: Experiment = {
  schema_version: 1, model_contract: 'v0_aligned_scalar_forward_v1', wavelength_m: 633e-9,
  grid: { ny: 512, nx: 512, dy: 4e-6, dx: 4e-6 },
  source: { kind: 'gaussian', amplitude: 1, phase_rad: 0, waist_radius_m: 100e-6,
    waist_z_m: 0, center_x_m: 0, center_y_m: 0 },
  components: [], observation: { id: 'screen', z_m: 20e-3 },
};
export const PRESETS: readonly { id: string; label: string; experiment: Experiment }[] = Object.freeze([
  { id: 'free', label: '高斯光自由傳播（Gaussian free propagation）', experiment: freezeExperiment(base) },
  { id: 'lens', label: '高斯光＋薄透鏡（Thin lens）', experiment: freezeExperiment({ ...base,
    components: [{ id: 'lens', kind: 'thin_lens', z_m: 0, focal_length_m: 20e-3 }] }) },
  { id: 'aperture', label: '高斯光＋圓孔＋薄透鏡（Aperture and lens）', experiment: freezeExperiment({ ...base,
    components: [{ id: 'aperture', kind: 'circular_aperture', z_m: 0, radius_m: 80e-6 },
      { id: 'lens', kind: 'thin_lens', z_m: 0, focal_length_m: 20e-3 }] }) },
]);
export function presetExperiment(id: string): Experiment {
  const preset = PRESETS.find(value => value.id === id);
  if (!preset) throw new Error(`Unknown preset: ${id}`);
  return cloneExperiment(preset.experiment);
}
