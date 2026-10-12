import { describe, expect, it } from 'vitest';
import { NumericFieldBinding } from '../src/numeric_fields';
describe('authoritative SI editor binding', () => {
  it('ignores unchanged shortened display text without a display unit round trip', () => {
    const value = .020000000000000004, display = String(Number((value / .001).toPrecision(14))), binding = new NumericFieldBinding();
    expect(Number(display) * .001).not.toBe(value);
    binding.paint(display, 'sequential:observation.z_m', '1:1', value);
    expect(binding.shouldEdit(display, 'sequential:observation.z_m', '1:1', value), 'UNTOUCHED_SI_BITS_DETECTED').toBe(false);
    expect(binding.shouldEdit('21', 'sequential:observation.z_m', '1:1', value)).toBe(true);
  });
  it('binds same formatted A then B to B generation and exact SI', () => {
    const a = .020000000000000004, b = .020000000000000007, binding = new NumericFieldBinding();
    const painted = (value: number) => String(Number((value / .001).toPrecision(14)));
    expect(painted(a)).toBe(painted(b)); binding.paint(painted(a), 'z', 'A', a); binding.paint(painted(b), 'z', 'B', b);
    expect(binding.shouldEdit(painted(b), 'z', 'B', b), 'SAME_FORMATTED_VALUE_GENERATION_DETECTED').toBe(false);
    expect(binding.shouldEdit(painted(b), 'z', 'A', b), 'SAME_FORMATTED_VALUE_GENERATION_DETECTED').toBe(true);
    expect(binding.shouldEdit(painted(b), 'other', 'B', b)).toBe(true);
  });
  it('rerender and passive unchanged controls preserve exact data while a named real edit stays local', () => {
    const binding = new NumericFieldBinding(), science = { dx: 2.0000000000000003e-6, dy: 3.0000000000000005e-6 };
    const before = structuredClone(science); binding.paint('2', 'dx', 3, science.dx);
    for (let i = 0; i < 5; i++) expect(binding.shouldEdit('2', 'dx', 3, science.dx), 'UNTOUCHED_SI_BITS_DETECTED').toBe(false);
    if (binding.shouldEdit('4', 'dx', 3, science.dx)) science.dx = Number('4') * 1e-6;
    expect(science.dy, 'UNTOUCHED_SI_BITS_DETECTED').toBe(before.dy); expect(science.dx).toBe(4e-6);
    binding.clear(); expect(binding.shouldEdit('2', 'dx', 3, before.dx)).toBe(true);
  });
});
