/** Preserve authoritative SI when an unchanged cosmetic editor string is replayed. */
export class NumericFieldBinding {
  private painted: Readonly<{ text: string; fieldKey: string; generation: string | number; authoritativeSI: number }> | null = null;
  paint(text: string, fieldKey: string, generation: string | number, authoritativeSI: number): void {
    this.painted = Object.freeze({ text, fieldKey, generation, authoritativeSI });
  }
  shouldEdit(text: string, fieldKey: string, generation: string | number, authoritativeSI: number): boolean {
    return !(this.painted && this.painted.text === text && this.painted.fieldKey === fieldKey
      && this.painted.generation === generation && Object.is(this.painted.authoritativeSI, authoritativeSI));
  }
  clear(): void { this.painted = null; }
}
