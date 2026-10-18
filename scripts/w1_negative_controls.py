"""Isolated W1 scientific fault controls; never mutate production files.

Each deliberate fault is a copied new W1 module under a fresh owned evidence
directory. A child process imports that copy under the correct package name.
Only the intended scientific/ownership AssertionError counts as detection.
Schema, import, timeout and unrelated failures do not count. Positive controls
and restored focused tests establish that unchanged source still passes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'src/ohlab/optics/wave_field.py'

RAW_RUNNER = '''import importlib.util,sys
from pathlib import Path
root=Path(sys.argv[1]);sys.path.insert(0,str(root))
import ohlab.optics
name='ohlab.optics.wave_field'
spec=importlib.util.spec_from_file_location(name,sys.argv[2])
module=importlib.util.module_from_spec(spec);sys.modules[name]=module
spec.loader.exec_module(module);ohlab.optics.wave_field=module
if sys.argv[3]=='pytest':
    import pytest
    raise SystemExit(pytest.main(['-q','-p','no:cacheprovider',sys.argv[4]]))
import numpy as np
from ohlab.optics import run_experiment
from scripts.validate_w1_wave_field import asymmetric,independent_sections
e=asymmetric()
positions=(.0001,.0005,.001)
plan=module.section_plan(e,interior_z_m=positions)
canonical=run_experiment(e,record_fields=('source','after:aperture','after:lens'))
anchors={s:canonical.field_at(s) for s in ('source','after:aperture','after:lens')}
expected=independent_sections(e,positions)
selector=sys.argv[4]
p=next(p for p in plan if p.id==selector)
actual=module._section_field(p,canonical,anchors)
if sys.argv[3]=='intensity':
    print('INTENDED_ASSERTION physical x/y intensity orientation '+selector,flush=True)
    np.testing.assert_allclose(module._plane_intensity(actual),expected[selector].real**2+expected[selector].imag**2,rtol=4e-11,atol=4e-11)
    print('INDEPENDENT_RAW_INTENSITY_ASSERTION_PASSED',flush=True)
    raise SystemExit(0)
print('INTENDED_ASSERTION independent complete complex field '+selector,flush=True)
np.testing.assert_allclose(actual.data,expected[selector],rtol=2e-11,atol=2e-11*np.max(abs(expected['section:source'])))
print('INDEPENDENT_RAW_SECTION_ASSERTION_PASSED',flush=True)
'''


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_hashes() -> dict[str, str]:
    """Tracked numerical/test files plus this six-path new numerical scope."""
    result = subprocess.run(['git', 'ls-files', '--', 'src/ohlab', 'tests'], cwd=ROOT,
                            capture_output=True, text=True, check=True)
    names = set(result.stdout.splitlines())
    names.update(('src/ohlab/optics/wave_field.py', 'tests/test_optics_wave_field.py',
                  'tests/test_optics_wave_field_analytic.py', 'tests/test_optics_wave_field_architecture.py',
                  'scripts/validate_w1_wave_field.py', 'scripts/w1_negative_controls.py'))
    return {name: sha(ROOT/name) for name in sorted(names)}


def replace_once(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise ValueError(f'fault site must have exactly one match; got {source.count(old)}: {old!r}')
    return source.replace(old, new, 1)


def controls(source: str) -> list[dict]:
    """Faults are confined to the new copied wrapper, never old science."""
    dft = 'tests/test_optics_wave_field_analytic.py::test_every_section_complex_against_independent_physical_dft[0.08-False-11-14]'
    tests = []
    def add(name, old, new, mode='pytest', target=dft, intended='independent complex/intensity assertion'):
        tests.append(dict(name=name, source=replace_once(source, old, new), mode=mode, target=target, intended=intended))
    add('wrong_upstream_anchor', 'upstream = anchors[position.anchor_selector]',
        'upstream = anchors["source"] if position.stage == "interior" else anchors[position.anchor_selector]')
    add('wrong_absolute_instead_of_interval_distance',
        'distance_m=position.separation_m, pad_factor=1)',
        'distance_m=position.z_m if position.stage == "interior" else position.separation_m, pad_factor=1)')
    add('double_propagation_distance', 'distance_m=position.separation_m, pad_factor=1)',
        'distance_m=position.separation_m*2 if position.stage == "interior" else position.separation_m, pad_factor=1)')
    add('aperture_applied_on_before_side',
        'if position.stage == "observation":\n        return canonical.observation',
        'if position.stage == "before:"+canonical.experiment.components[0].id:\n        return anchors["after:"+canonical.experiment.components[0].id]\n    if position.stage == "observation":\n        return canonical.observation',
        mode='raw', target='section:before:aperture', intended='independent before-aperture complex assertion')
    add('lens_omitted_on_after_side',
        'if position.stage == "observation":\n        return canonical.observation',
        'if position.stage == "after:"+canonical.experiment.components[1].id:\n        a,l=canonical.experiment.components\n        return propagate_angular_spectrum(anchors["after:"+a.id],distance_m=l.z_m-a.z_m,pad_factor=1)\n    if position.stage == "observation":\n        return canonical.observation',
        mode='raw', target='section:after:lens', intended='independent after-lens complex phase assertion')
    add('double_lens_phase', 'return anchors[position.stage]',
        'return __import__("ohlab.optics",fromlist=["apply_component"]).apply_component(anchors[position.stage],canonical.experiment.components[1]) if position.stage == "after:"+canonical.experiment.components[1].id else anchors[position.stage]',
        mode='raw', target='section:after:lens', intended='independent after-lens complex phase assertion')
    add('colocated_event_collapse', 'return tuple(rows)',
        'return tuple(row for index,row in enumerate(rows) if index==0 or row.z_m != rows[index-1].z_m)',
        target='tests/test_optics_wave_field.py::test_colocated_events_never_collapse_and_zero_spans_get_no_interiors',
        intended='six distinct physical event identities assertion')
    add('independent_color_normalization_hides_loss', 'return image\n',
        'return image/float(np.max(image)) if float(np.max(image)) > 0 else image\n',
        intended='raw intensity equality assertion, independent of display color')
    add('reversed_transverse_rows', 'return image\n', 'return image[::-1].copy()\n',
        intended='independent physical row-coordinate intensity assertion')
    add('transposed_x_y_intensity', 'return image\n', 'return image.T.copy()\n',
        mode='intensity', target='section:source',
        intended='physical x/y intensity shape/orientation assertion')
    add('fabricated_endpoint_field_interpolation',
        'upstream = anchors[position.anchor_selector]',
        'if position.stage == "interior":\n        t=position.z_m/canonical.experiment.observation.z_m\n        return ComplexField(data=(1-t)*anchors["source"].data+t*canonical.observation.data,grid=canonical.experiment.grid,wavelength_m=canonical.experiment.wavelength_m)\n    upstream = anchors[position.anchor_selector]')
    add('fabricated_unperturbed_gaussian_section', 'upstream = anchors[position.anchor_selector]',
        'if position.stage == "interior":\n        return anchors["source"]\n    upstream = anchors[position.anchor_selector]')
    add('duplicate_canonical_v0_execution', 'canonical = run_experiment(experiment, record_fields=selectors)',
        'canonical = run_experiment(experiment, record_fields=selectors)\n    run_experiment(experiment, record_fields=selectors)',
        target='tests/test_optics_wave_field.py::test_only_one_canonical_call_three_anchors_and_exact_terminal_identity',
        intended='exactly one canonical execution assertion')
    add('recomputed_terminal_replaces_actual_object', 'return self.canonical.observation\n',
        'a,l=self.experiment.components\n        return propagate_angular_spectrum(self.canonical.field_at("after:"+l.id),distance_m=self.experiment.observation.z_m-l.z_m,pad_factor=1)\n',
        target='tests/test_optics_wave_field.py::test_only_one_canonical_call_three_anchors_and_exact_terminal_identity',
        intended='terminal object identity assertion even when values are identical')
    return tests


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    before = protected_hashes()
    runner = args.output/'control_runner.py'
    runner.write_text(RAW_RUNNER, encoding='utf-8')
    source = SOURCE.read_text(encoding='utf-8')
    rows = []
    variants = controls(source)
    # A source-identical copied positive control executes the same DFT assertion.
    variants.insert(0, dict(name='unchanged_positive', source=source, mode='pytest',
                           target=variants[0]['target'], intended='positive reference must pass'))
    for variant in variants:
        owned = args.output/variant['name']
        owned.mkdir()
        copied = owned/'wave_field.py'
        copied.write_text(variant['source'], encoding='utf-8')
        command = [sys.executable, '-B', '-X', 'utf8', str(runner.resolve()), str(ROOT),
                   str(copied.resolve()), variant['mode'], variant['target']]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
        (owned/'stdout.txt').write_text(result.stdout, encoding='utf-8')
        (owned/'stderr.txt').write_text(result.stderr, encoding='utf-8')
        text = result.stdout+result.stderr
        positive = variant['name'] == 'unchanged_positive'
        detected = result.returncode == 0 if positive else result.returncode != 0 and 'AssertionError' in text
        if not positive:
            detected = detected and not any(token in text for token in ('ImportError', 'ModuleNotFoundError', 'SyntaxError', 'ERROR collecting'))
        row = dict(name=variant['name'], command=command, returncode=result.returncode,
                   intended=variant['intended'], detected=detected,
                   copied_source_sha256=sha(copied))
        rows.append(row)
        (owned/'result.json').write_text(json.dumps(row, indent=2)+'\n', encoding='utf-8')
        print(f"{variant['name']}: {'DETECTED' if detected and not positive else 'PASS' if detected else 'NOT_DETECTED'}; exit={result.returncode}", flush=True)
        if not detected:
            raise AssertionError(f"intended assertion not detected for {variant['name']}; inspect preserved child output")
    after = protected_hashes()
    assert before == after, 'production source/test hashes changed across isolated controls'
    restored_command = [sys.executable, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                        'tests/test_optics_wave_field.py', 'tests/test_optics_wave_field_analytic.py',
                        'tests/test_optics_wave_field_architecture.py']
    restored = subprocess.run(restored_command, cwd=ROOT, capture_output=True, text=True, timeout=60)
    (args.output/'restored.stdout.txt').write_text(restored.stdout, encoding='utf-8')
    (args.output/'restored.stderr.txt').write_text(restored.stderr, encoding='utf-8')
    assert restored.returncode == 0, restored.stdout+restored.stderr
    report = dict(controls=rows, protected_before=before, protected_after=after,
                  source_and_test_hashes_preserved=True,
                  restored_command=restored_command, restored_returncode=restored.returncode,
                  note='Only numerical/ownership controls here; stale/gate/cursor/color/texture resource state controls belong to frontend/backend acceptance')
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(restored.stdout, end='')


if __name__ == '__main__':
    main()
