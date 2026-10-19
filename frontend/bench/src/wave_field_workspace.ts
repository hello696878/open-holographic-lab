/** Existing calculated W1 arrays, presented in a contained linked bench inspector. */
import { structuralEqual, type Experiment } from './contracts';
import { validateColorLimits, type ColorLimits } from './detector';
import { detectorEdges } from './mapping';
import type { BenchScene } from './scene';
import { createWaveFieldApparatus, type WaveFieldApparatus } from './wave_field_apparatus';
import { W1_APPARATUS_CAP, requireWaveFieldExperiment, waveFieldOwnedResults, waveFieldSection, type WaveFieldResult } from './wave_field_contracts';
import { formatWaveFieldNumber, prepareWaveFieldDisplay, sectionSample, W1_INITIAL_RANGE, type WaveFieldDisplay, type WaveFieldPresentation } from './wave_field_display';
import { WaveFieldController, type WaveFieldPrepared, type WaveFieldState } from './wave_field_state';

export interface WaveFieldWorkspaceOptions {
  admit(persistent: number, transient: number): void; loadExample(): void | Promise<void>; select(id: string): void;
  cursorHost?: HTMLElement;
  /** The actual existing scientific editor is moved, never cloned or replaced. */
  editorHost?: HTMLElement;
}
type DockTab = 'profile' | 'display' | 'evidence' | 'parameters';
type ProfileQuantity = 'on_axis_intensity' | 'max_intensity' | 'norm';
type CameraView = 'overview' | 'beam' | 'top' | 'section' | 'focus';
const quantities: readonly [ProfileQuantity, string, string][] = [
  ['on_axis_intensity', 'On-axis intensity', 'amplitude-unit²'],
  ['max_intensity', 'Maximum intensity', 'amplitude-unit²'], ['norm', 'Sampled norm', 'amplitude-unit² m²'],
];

export class WaveFieldWorkspace {
  private active = true; private disposed = false; private apparatus: WaveFieldApparatus | null = null;
  private apparatusExperiment: Experiment | null = null; private resource: WaveFieldDisplay | null = null;
  private displays = new Set<WaveFieldDisplay>(); private mounted = false; private hasFramed = false;
  private limits: ColorLimits = { ...W1_INITIAL_RANGE }; private glow = true; private fullPrecision = false;
  private presentation: WaveFieldPresentation = { selected: true, sparse: true, curtains: true, guides: false, magnification: 4 };
  private tab: DockTab = 'profile'; private profileQuantity: ProfileQuantity = 'on_axis_intensity';
  private section = 0; private row = 0; private column = 0;
  private readonly editorAnchor: Comment | null;
  private unsubscribe: () => void; private unsubscribeSource: () => void; private unsubscribeGate: () => void;

  constructor(readonly host: HTMLElement, private readonly scene: BenchScene | null, readonly controller: WaveFieldController,
      private readonly options: WaveFieldWorkspaceOptions) {
    this.editorAnchor = options.editorHost ? document.createComment('Existing Sequential editor home') : null;
    if (this.editorAnchor) options.editorHost!.before(this.editorAnchor);
    host.innerHTML = `<div class="w1-header"><div><span class="eyebrow">W1 · COMPUTED SECTIONS</span><h2>Wave-Field Inspection</h2></div>
      <label class="w1-enable"><input type="checkbox" data-testid="w1-enable">Computed Sections</label><output data-testid="w1-dock-status" aria-live="polite"></output></div>
      <p class="error" data-testid="w1-error" role="alert" hidden></p><p class="error" data-testid="w1-display-error" role="alert" hidden></p>
      <button type="button" data-testid="w1-retry-display" hidden>Restore Display (No Recalculation)</button>
      <div class="w1-body" data-w1="body" hidden>
        <div class="w1-bench-navigation" data-w1="navigation">
          <div class="w1-live-status"><output data-testid="w1-status" aria-live="polite"></output><span data-testid="w1-display-scale"></span></div>
          <button type="button" data-testid="w1-load-example">Load W1 Example</button>
          <label class="w1-section-control">Calculated Section <select data-testid="w1-section" aria-label="Calculated Section"></select></label>
          <label class="w1-cursor-control">Axial Inspection Cursor · sampled sections only <input type="range" data-testid="w1-cursor" min="0" max="0" step="1" value="0" aria-label="Select a calculated section"></label>
          <div class="w1-camera-controls"><button type="button" data-testid="w1-overview">Whole Train</button><button type="button" data-testid="w1-beam">Beam</button>
            <button type="button" data-testid="w1-top">Top</button><button type="button" data-testid="w1-section-view">Section</button><button type="button" data-testid="w1-focus">Focus</button><button type="button" data-testid="w1-reset">Reset</button></div>
          <div class="w1-layer-controls" aria-label="Independent display layers"><label><input type="checkbox" data-testid="w1-layer-selected" checked>Selected Overlay</label>
            <label><input type="checkbox" data-testid="w1-layer-sparse" checked>Sampled Sections</label><label><input type="checkbox" data-testid="w1-layer-curtains" checked>Sampled Curtains</label>
            <label><input type="checkbox" data-testid="w1-layer-guides">Layout Guides</label><label>Display Scale <select data-testid="w1-magnification" aria-label="Transverse field display magnification only"><option value="1">×1</option><option value="2">×2</option><option value="4" selected>×4</option></select></label></div>
          <p class="w1-legend" data-testid="w1-legend">Cyan/amber: selected calculated overlay, visible through schematic housings. Faint planes: other calculated sections. Curtains: nearest samples within each event interval. Dashed lines: layout guides, not rays or side scattering. Scale affects field display only; apparatus, raw coordinates and physical waist are unchanged.</p>
        </div>
        <section class="w1-inspector w1-selected-preview" aria-label="Selected calculated section">
          <div class="w1-inspector-heading"><h3>Quantitative Section</h3><label><input type="checkbox" data-testid="w1-full-precision">17 digits</label></div>
          <output class="w1-selected-title" data-testid="w1-selected-title">Not Yet Calculated</output>
          <div data-w1="canvas-host" class="w1-canvas-host"></div><p class="w1-preview-empty" data-w1="empty-preview">Set parameters, then press Simulate. Views, sections and color limits use calculated data only.</p>
          <div class="w1-key-metrics"><label>z / mm<output data-testid="w1-summary-z">—</output></label><label>raw peak / a.u.²<output data-testid="w1-summary-peak">—</output></label><label>sampled N / a.u.²m²<output data-testid="w1-summary-norm">—</output></label></div>
          <output class="w1-readout w1-selected-pixel" data-testid="w1-pixel"></output>
          <div class="w1-pixel-controls"><label>row <input type="number" min="0" step="1" data-testid="w1-row" value="0"></label><label>column <input type="number" min="0" step="1" data-testid="w1-column" value="0"></label><span>+y ↓ · I / a.u.²</span></div>
          <p class="w1-stage-note" data-testid="w1-stage-note"></p>
        </section>
        <nav class="w1-tabs" role="tablist" aria-label="Wave-field inspection tools">
          <button type="button" role="tab" id="w1-tab-profile" data-testid="w1-tab-profile" data-w1-tab="profile" aria-controls="w1-panel-profile">Profile</button>
          <button type="button" role="tab" id="w1-tab-display" data-testid="w1-tab-display" data-w1-tab="display" aria-controls="w1-panel-display">Display</button>
          <button type="button" role="tab" id="w1-tab-evidence" data-testid="w1-tab-evidence" data-w1-tab="evidence" aria-controls="w1-panel-evidence">Data</button>
          <button type="button" role="tab" id="w1-tab-parameters" data-testid="w1-tab-parameters" data-w1-tab="parameters" aria-controls="w1-panel-parameters">Parameters</button>
        </nav>
        <div class="w1-tabpanels">
          <section class="w1-profile w1-tabpanel" id="w1-panel-profile" data-w1-panel="profile" role="tabpanel" aria-labelledby="w1-tab-profile" tabindex="0">
            <label>Quantity <select data-testid="w1-profile-quantity"><option value="on_axis_intensity">On-axis intensity</option><option value="max_intensity">Maximum intensity</option><option value="norm">Sampled norm</option></select></label>
            <div data-w1="profile"></div><output class="w1-readout" data-testid="w1-profile-selected"></output>
            <p class="w1-note">Discrete calculated samples; the bright line marks the selected z. ○ before/source, ◇ after, □ observation. Co-located stages stay distinct; aperture loss is not normalized away.</p>
          </section>
          <section class="w1-controls w1-tabpanel" id="w1-panel-display" data-w1-panel="display" role="tabpanel" aria-labelledby="w1-tab-display" tabindex="0" hidden>
            <h3>Shared Section Color Limits</h3><div class="w1-range-controls"><label>Minimum <input type="number" data-testid="w1-range-min" value="0" step="any"></label><label>Maximum <input type="number" data-testid="w1-range-max" value="3" step="any"></label>
              <button type="button" data-testid="w1-apply-range">Apply Limits</button><button type="button" data-testid="w1-auto-range">Auto shared range</button></div>
            <output class="w1-readout" data-testid="w1-color-limits">0–3 amplitude-unit² · shared linear</output>
            <label class="w1-display-checkbox"><input type="checkbox" data-testid="w1-glow" checked>Enhance Faint 3D Fields (Shared sqrt Opacity)</label>
            <p class="w1-note">The shared sqrt opacity enhancement affects 3D presentation only. Quantitative grayscale keeps shared linear limits and nearest pixels. No section is independently normalized; float64 intensity is unchanged. Transverse scale does not alter apparatus, z, coordinates or physical waist. The selected inspection overlay is visible through schematic housings; optical transmission and quantitative detector textures are unchanged.</p>
          </section>
          <section class="w1-tabpanel" id="w1-panel-evidence" data-w1-panel="evidence" role="tabpanel" aria-labelledby="w1-tab-evidence" tabindex="0" hidden>
            <h3>Selected Calculated Section</h3><output class="w1-readout" data-testid="w1-section-readout"></output>
            <div class="w1-stage-table" tabindex="0" role="region" aria-label="Calculated sections and norm, horizontally scrollable" data-w1="table"></div>
            <p class="w1-note">Row 0 is at the top; column 0 is at the left; physical +y points down. Periodic full-window ASM · pad_factor=1 · scalar monochromatic forward model. Strong clipping, finite-window and sampling limitations remain. Sampled norm is not calibrated watts; no universal Gaussian envelope is fitted.</p>
          </section>
          <section class="w1-tabpanel" id="w1-panel-parameters" data-w1-panel="parameters" role="tabpanel" aria-labelledby="w1-tab-parameters" tabindex="0" hidden>
            <h3>Selected Component · Existing Scientific Editor</h3><div data-w1="editor"></div><p class="w1-note">Editing detaches the old result. Only Simulate recomputes. Gaussian → circular aperture → ideal thin lens → observation plane.</p>
          </section>
        </div>
      </div>`;
    if (options.cursorHost) { options.cursorHost.classList.add('w1-bench-controls'); options.cursorHost.append(this.area('navigation')); options.cursorHost.hidden = true; }
    this.node<HTMLInputElement>('w1-enable').addEventListener('change', event => this.controller.setContext((event.target as HTMLInputElement).checked, this.active));
    this.node('w1-load-example').addEventListener('click', () => { void options.loadExample(); });
    this.node('w1-retry-display').addEventListener('click', () => { this.controller.retryPresentation(); });
    this.node<HTMLSelectElement>('w1-section').addEventListener('change', event => this.select(Number((event.target as HTMLSelectElement).value)));
    this.node<HTMLInputElement>('w1-cursor').addEventListener('input', event => this.select(Number((event.target as HTMLInputElement).value)));
    for (const id of ['w1-row', 'w1-column']) this.node<HTMLInputElement>(id).addEventListener('change', () => this.pickNumeric());
    this.node<HTMLInputElement>('w1-full-precision').addEventListener('change', event => { this.fullPrecision = (event.target as HTMLInputElement).checked; this.updateReadout(); });
    this.node('w1-apply-range').addEventListener('click', () => this.changeRange(false)); this.node('w1-auto-range').addEventListener('click', () => this.changeRange(true));
    this.node<HTMLInputElement>('w1-glow').addEventListener('change', event => { const old = this.glow; this.glow = (event.target as HTMLInputElement).checked;
      if (!this.rebuildDisplay()) { this.glow = old; (event.target as HTMLInputElement).checked = old; } });
    for (const field of ['selected', 'sparse', 'curtains', 'guides'] as const) this.node<HTMLInputElement>(`w1-layer-${field}`).addEventListener('change', event => {
      this.changePresentation({ ...this.presentation, [field]: (event.target as HTMLInputElement).checked }); });
    this.node<HTMLSelectElement>('w1-magnification').addEventListener('change', event => {
      this.changePresentation({ ...this.presentation, magnification: Number((event.target as HTMLSelectElement).value) as 1 | 2 | 4 }); });
    for (const [id, view] of [['w1-overview', 'overview'], ['w1-beam', 'beam'], ['w1-top', 'top'], ['w1-section-view', 'section'], ['w1-focus', 'focus'], ['w1-reset', 'overview']] as const)
      this.node(id).addEventListener('click', () => this.cameraView(view));
    for (const button of host.querySelectorAll<HTMLButtonElement>('[data-w1-tab]')) {
      button.addEventListener('click', () => this.setTab(button.dataset.w1Tab as DockTab)); button.addEventListener('keydown', event => this.tabKey(event, button.dataset.w1Tab as DockTab));
    }
    this.node<HTMLSelectElement>('w1-profile-quantity').addEventListener('change', event => { this.profileQuantity = (event.target as HTMLSelectElement).value as ProfileQuantity; this.showProfile(); this.updateReadout(); });
    this.controller.bindPresentation(result => this.prepare(result)); this.unsubscribe = this.controller.subscribe(state => this.render(state));
    this.unsubscribeSource = this.controller.bench.subscribe(() => this.render(this.controller.state)); this.unsubscribeGate = this.controller.gate.subscribe(() => this.render(this.controller.state));
    this.scene?.setWaveFieldInteraction((id, row, column) => {
      const result = this.controller.state.currentResult; if (!result || this.resource?.result !== result) return;
      const index = result.planes.findIndex(plane => plane.id === id); if (index < 0) return; this.row = row; this.column = column; this.select(index);
    });
    this.showTab(); this.refreshPresentationControls();
  }
  private node<T extends HTMLElement = HTMLElement>(id: string): T { const selector = `[data-testid="${id}"]`, node = this.host.querySelector<T>(selector) ?? this.options.cursorHost?.querySelector<T>(selector); if (!node) throw new Error(`Missing W1 ${id}`); return node; }
  private area(id: string): HTMLElement { const selector = `[data-w1="${id}"]`, node = this.host.querySelector<HTMLElement>(selector) ?? this.options.cursorHost?.querySelector<HTMLElement>(selector); if (!node) throw new Error(`Missing W1 area ${id}`); return node; }
  private setTab(tab: DockTab): void { this.tab = tab; this.showTab(); }
  private showTab(): void {
    for (const button of this.host.querySelectorAll<HTMLButtonElement>('[data-w1-tab]')) { const selected = button.dataset.w1Tab === this.tab; button.setAttribute('aria-selected', String(selected)); button.tabIndex = selected ? 0 : -1; }
    for (const panel of this.host.querySelectorAll<HTMLElement>('[data-w1-panel]')) panel.hidden = panel.dataset.w1Panel !== this.tab;
  }
  private tabKey(event: KeyboardEvent, current: DockTab): void {
    const tabs: DockTab[] = ['profile', 'display', 'evidence', 'parameters'], index = tabs.indexOf(current);
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : event.key === 'ArrowRight' ? (index + 1) % tabs.length : event.key === 'ArrowLeft' ? (index + tabs.length - 1) % tabs.length : null;
    if (next === null) return; event.preventDefault(); this.setTab(tabs[next]); this.node(`w1-tab-${tabs[next]}`).focus();
  }
  private portEditor(enabled: boolean): void {
    if (!this.options.editorHost || !this.editorAnchor) return;
    if (enabled) { if (this.options.editorHost.parentElement !== this.area('editor')) this.area('editor').append(this.options.editorHost); }
    else if (this.editorAnchor.parentNode && this.options.editorHost.previousSibling !== this.editorAnchor) this.editorAnchor.after(this.options.editorHost);
  }
  setActive(active: boolean): void { this.active = active; this.controller.setContext(this.controller.enabled, active); this.render(this.controller.state); }
  private syncApparatus(): void {
    if (!this.controller.enabled || !this.active) { if (this.mounted) this.scene?.hideWaveFieldApparatus(); this.mounted = false; return; }
    const experiment = this.controller.bench.state.validatedDraft;
    if (!experiment) { this.apparatus?.setDisplay(null, null); return; }
    requireWaveFieldExperiment(experiment); if (!this.scene) throw new Error('Existing WebGL2 scene unavailable; no substitute calculation is displayed.');
    if (!this.apparatus || !structuralEqual(this.apparatusExperiment, experiment)) {
      this.options.admit(W1_APPARATUS_CAP, W1_APPARATUS_CAP); const next = createWaveFieldApparatus(experiment), previous = this.apparatus;
      try { if (this.mounted) this.scene.replaceWaveFieldApparatus(next.group); else { this.scene.showWaveFieldApparatus(next.group); this.mounted = true; }
        this.apparatus = next; this.apparatusExperiment = experiment; previous?.dispose(); } catch (error) { next.dispose(); throw error; }
    } else if (!this.mounted) { this.scene.showWaveFieldApparatus(this.apparatus.group); this.mounted = true; }
    this.scene.setWaveFieldLabelUpdater((camera, width, height) => this.apparatus?.updateLabels(camera, width, height)); this.apparatus.select(this.controller.bench.state.selection);
    if (!this.hasFramed) {
      const bounds = this.apparatus.framingBounds(), edges = detectorEdges(experiment.grid), magnitude = this.presentation.magnification;
      // Include the declared display window before the first response, without any propagation.
      for (const x of [edges.xMin, edges.xMax]) for (const y of [edges.yMin, edges.yMax]) for (const z of [0, experiment.observation.z_m])
        bounds.expandByPoint(bounds.min.clone().set(x * 1000 * magnitude, 1 - y * 1000 * magnitude, z * 100));
      this.scene.fitWaveFieldApparatus(bounds, 'overview'); this.hasFramed = true;
    }
  }
  private cameraView(view: CameraView): void {
    try { if (!this.apparatus || !this.mounted || !this.scene) return;
      const current = this.controller.state.currentResult, display = current && this.resource?.result === current ? this.resource : null;
      if ((view === 'beam' || view === 'section') && !display) return;
      const bounds = view === 'beam' || view === 'section' ? display!.framingBounds(view) : this.apparatus.framingBounds(view === 'focus' ? this.controller.bench.state.selection : undefined);
      if ((view === 'overview' || view === 'top') && display) bounds.union(display.framingBounds('beam')); this.scene.fitWaveFieldApparatus(bounds, view);
    } catch (error) { this.controller.reportPresentationFailure(String(error)); }
  }
  private prepare(result: WaveFieldResult): WaveFieldPrepared {
    this.syncApparatus(); if (!this.active || !this.controller.enabled || !this.apparatus || !this.scene) throw new Error('Computed Sections is detached; numerical data retained.');
    this.scene.assertWaveFieldReady(); const before = this.ownedNumericalBytes(), after = waveFieldOwnedResults([...this.numericalOwners(), result]);
    const { nx, ny } = result.experiment.grid, pixels = nx * ny, displayReserve = result.planes.length * pixels * 4 + pixels * 8 + result.planes.length * (nx + ny) * 8 + 128 * 1024;
    this.options.admit(after - before + displayReserve, after - before + displayReserve + pixels * 8); const next = prepareWaveFieldDisplay(result, this.limits, this.glow);
    try {
    next.setPresentation(this.presentation); this.options.admit(after - before + next.ownedBytes, after - before + next.ownedBytes + pixels * 8);
    const previous = this.resource, oldSelection = { section: this.section, row: this.row, column: this.column };
    const oldCanvas = [...this.area('canvas-host').childNodes], oldProfiles = [...this.area('profile').childNodes], oldTable = [...this.area('table').childNodes], oldOptions = [...this.node('w1-section').childNodes];
    const cursor = this.node<HTMLInputElement>('w1-cursor'), oldCursor = { max: cursor.max, value: cursor.value, disabled: cursor.disabled };
    const select = this.node<HTMLSelectElement>('w1-section'), oldSelect = { value: select.value, disabled: select.disabled };
    let committed = false, closed = false; this.displays.add(next); next.canvas.addEventListener('pointermove', this.pickCanvas); next.canvas.addEventListener('click', this.pickCanvas);
    return {
      commit: () => { if (closed || this.resource !== previous || !this.active || !this.controller.enabled) throw new Error('W1 presentation destination changed');
        this.scene!.assertWaveFieldReady(); this.apparatus!.setDisplay(next.group, next.detectorTexture); this.resource = next; committed = true;
        this.area('canvas-host').replaceChildren(next.canvas); this.section = result.planes.length - 1; this.row = Math.floor(ny / 2); this.column = Math.floor(nx / 2);
        this.fillSections(result); this.drawProfiles(result); next.select(this.section); },
      dispose: () => { if (closed) return; closed = true; if (committed && this.resource === next) {
          this.resource = previous; this.section = oldSelection.section; this.row = oldSelection.row; this.column = oldSelection.column;
          this.area('canvas-host').replaceChildren(...oldCanvas); this.area('profile').replaceChildren(...oldProfiles); this.area('table').replaceChildren(...oldTable);
          select.replaceChildren(...oldOptions); select.value = oldSelect.value; select.disabled = oldSelect.disabled; cursor.max = oldCursor.max; cursor.value = oldCursor.value; cursor.disabled = oldCursor.disabled;
          this.apparatus?.setDisplay(previous?.group ?? null, previous?.detectorTexture ?? null); this.showProfile(); }
        this.drop(next); },
      finalize: () => { if (closed) return; closed = true; if (previous && previous !== next) this.drop(previous); },
    };
    } catch (error) { next.canvas.removeEventListener('pointermove', this.pickCanvas); next.canvas.removeEventListener('click', this.pickCanvas); next.dispose(); this.displays.delete(next); throw error; }
  }
  private drop(display: WaveFieldDisplay): void { display.canvas.removeEventListener('pointermove', this.pickCanvas); display.canvas.removeEventListener('click', this.pickCanvas); display.dispose(); this.displays.delete(display); }
  private fillSections(result: WaveFieldResult): void {
    const select = this.node<HTMLSelectElement>('w1-section'); select.replaceChildren(); result.planes.forEach((plane, index) => {
      const option = document.createElement('option'); option.value = String(index); option.textContent = `${index + 1}/${result.planes.length} · ${(plane.z_m * 1000).toPrecision(7)} mm · ${plane.stage === 'interior' ? plane.id : plane.stage}`; select.append(option); });
    const cursor = this.node<HTMLInputElement>('w1-cursor'); cursor.max = String(result.planes.length - 1); cursor.disabled = false;
    this.node<HTMLInputElement>('w1-row').max = String(result.experiment.grid.ny - 1); this.node<HTMLInputElement>('w1-column').max = String(result.experiment.grid.nx - 1);
  }
  private select(index: number): void {
    const result = this.controller.state.currentResult; if (!result || this.resource?.result !== result) return;
    if (!Number.isInteger(index) || index < 0 || index >= result.planes.length) return;
    this.section = index; this.resource.select(index); this.updateReadout();
  }
  private pickCanvas = (event: MouseEvent): void => {
    const result = this.controller.state.currentResult; if (!result || this.resource?.result !== result) return;
    const rect = this.resource.canvas.getBoundingClientRect(), column = Math.floor((event.clientX - rect.left) / rect.width * result.experiment.grid.nx), row = Math.floor((event.clientY - rect.top) / rect.height * result.experiment.grid.ny);
    if (row < 0 || column < 0 || row >= result.experiment.grid.ny || column >= result.experiment.grid.nx) return; this.row = row; this.column = column; this.updateReadout();
  };
  private pickNumeric(): void {
    const result = this.controller.state.currentResult; if (!result) return; const row = Number(this.node<HTMLInputElement>('w1-row').value), column = Number(this.node<HTMLInputElement>('w1-column').value);
    try { sectionSample(result, this.section, row, column); this.row = row; this.column = column; this.updateReadout(); } catch (error) { this.node('w1-error').textContent = String(error); this.node('w1-error').hidden = false; }
  }
  private updateReadout(): void {
    const result = this.controller.state.currentResult; if (!result || this.resource?.result !== result) return;
    const plane = result.planes[this.section], sample = sectionSample(result, this.section, this.row, this.column), f = (value: number | null) => formatWaveFieldNumber(value, this.fullPrecision);
    this.node<HTMLSelectElement>('w1-section').value = String(this.section); this.node<HTMLInputElement>('w1-cursor').value = String(this.section); this.node<HTMLInputElement>('w1-row').value = String(this.row); this.node<HTMLInputElement>('w1-column').value = String(this.column);
    this.node('w1-selected-title').textContent = `${this.section + 1}/${result.planes.length} · ${plane.stage === 'interior' ? plane.id : plane.stage}`;
    this.node('w1-summary-z').textContent = f(plane.z_m * 1000); this.node('w1-summary-peak').textContent = f(plane.max_intensity); this.node('w1-summary-norm').textContent = f(plane.norm);
    this.node('w1-pixel').textContent = `I=${f(sample.intensity)} amplitude-unit²\nrow=${sample.row}, column=${sample.column}\nx=${f(sample.x_m)} m · y=${f(sample.y_m)} m`;
    const [aperture, lens] = result.experiment.components;
    this.node('w1-stage-note').textContent = plane.stage === `after:${aperture.id}` ? 'The physical aperture removes the field outside its opening. Transmission and signed ΔN are in the Data tab.'
      : plane.stage === `after:${lens.id}` ? 'The ideal thin lens changes phase here; intensity evolves downstream. This preview shows intensity only.'
      : plane.stage === 'observation' ? 'Authoritative V0 field · matches submitted settings.' : `Calculated Section · upstream ${plane.anchor_selector} · cursor movement does not recompute.`;
    let saturated = 0; for (const value of waveFieldSection(result, this.section)) if (value > this.limits.max) saturated++;
    this.node('w1-section-readout').textContent = `${plane.id}\nz=${f(plane.z_m)} m · ${plane.stage}\nupstream=${plane.anchor_selector} @ ${f(plane.anchor_z_m)} m · Δz=${f(plane.separation_m)} m\nraw peak=${f(plane.max_intensity)} amplitude-unit²\nN=${f(plane.norm)} amplitude-unit² m²\nΔN=${f(plane.delta_norm)} · ratio=${f(plane.transmission_ratio)}\ncomparison=${plane.comparison} · saturated=${saturated}/${result.experiment.grid.nx * result.experiment.grid.ny}\nrequest=${result.requestId}`;
    this.node('w1-color-limits').textContent = `${f(this.limits.min)}–${f(this.limits.max)} amplitude-unit² · shared linear · saturation ${saturated}/${result.experiment.grid.nx * result.experiment.grid.ny}`;
    this.node('w1-profile-selected').textContent = `z=${f(plane.z_m * 1000)} mm · ${f(plane[this.profileQuantity])}\n${plane.id}`; this.updateProfileMarker(result);
  }
  private updateProfileMarker(result: WaveFieldResult): void {
    const plane = result.planes[this.section], end = result.experiment.observation.z_m, x = 28 + (end === 0 ? 0 : plane.z_m / end) * 264;
    for (const svg of this.area('profile').querySelectorAll<SVGSVGElement>('svg')) {
      svg.dataset.activeSectionId = plane.id; svg.dataset.activeZ = String(plane.z_m);
      const cursor = svg.querySelector<SVGLineElement>('[data-w1-profile-cursor]'); cursor?.setAttribute('x1', String(x)); cursor?.setAttribute('x2', String(x));
      for (const marker of svg.querySelectorAll<SVGElement>('[data-section-id]')) { const active = marker.dataset.sectionId === plane.id; marker.classList.toggle('w1-profile-active', active);
        marker.setAttribute('aria-current', active ? 'true' : 'false'); marker.setAttribute('stroke', active ? '#fff7c4' : 'none'); marker.setAttribute('stroke-width', active ? '2.5' : '0'); }
    }
  }
  private refreshPresentationControls(): void {
    for (const field of ['selected', 'sparse', 'curtains', 'guides'] as const) this.node<HTMLInputElement>(`w1-layer-${field}`).checked = this.presentation[field];
    this.node<HTMLSelectElement>('w1-magnification').value = String(this.presentation.magnification); this.node('w1-display-scale').textContent = `Field display ×${this.presentation.magnification} · physical coordinates unchanged`;
  }
  private changePresentation(next: WaveFieldPresentation): void {
    try { this.resource?.setPresentation(next); this.presentation = { ...next }; this.refreshPresentationControls(); } catch (error) { this.refreshPresentationControls(); this.node('w1-error').hidden = false; this.node('w1-error').textContent = `Display change rejected: ${String(error)}`; }
  }
  private changeRange(auto: boolean): void {
    const result = this.controller.state.currentResult, previous = this.limits;
    try { const peak = result ? Math.max(...result.planes.map(plane => plane.max_intensity)) : 0;
      const limits = auto ? { min: 0, max: peak > 0 ? peak : 1 } : { min: Number(this.node<HTMLInputElement>('w1-range-min').value), max: Number(this.node<HTMLInputElement>('w1-range-max').value) };
      validateColorLimits(limits); this.limits = limits; if (!this.rebuildDisplay()) this.limits = previous;
      this.node<HTMLInputElement>('w1-range-min').value = String(this.limits.min); this.node<HTMLInputElement>('w1-range-max').value = String(this.limits.max); this.updateReadout();
    } catch (error) { this.limits = previous; this.node('w1-error').textContent = String(error); this.node('w1-error').hidden = false; }
  }
  private rebuildDisplay(): boolean {
    const result = this.controller.state.currentResult; if (!result) return true; const selected = this.section, row = this.row, column = this.column; let transaction: WaveFieldPrepared | null = null;
    try { transaction = this.prepare(result); transaction.commit(); this.section = selected; this.row = row; this.column = column; this.resource!.select(selected); this.updateReadout(); transaction.finalize(); return true; }
    catch (error) { transaction?.dispose(); this.node('w1-error').textContent = `Display change rejected; previous result retained: ${String(error)}`; this.node('w1-error').hidden = false; return false; }
  }
  private showProfile(): void { for (const svg of this.area('profile').querySelectorAll<SVGSVGElement>('svg')) { if (svg.dataset.quantity === this.profileQuantity) svg.removeAttribute('hidden'); else svg.setAttribute('hidden', ''); } }
  private drawProfiles(result: WaveFieldResult): void {
    const host = this.area('profile'); host.replaceChildren(); const namespace = 'http://www.w3.org/2000/svg';
    for (const [key, title, unit] of quantities) {
      const svg = document.createElementNS(namespace, 'svg'); svg.setAttribute('viewBox', '0 0 300 174'); svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', title); svg.dataset.quantity = key;
      const maximum = Math.max(...result.planes.map(plane => plane[key])), end = result.experiment.observation.z_m;
      const text = (x: number, y: number, content: string, color = '#dce9ec') => { const node = document.createElementNS(namespace, 'text'); node.setAttribute('x', String(x)); node.setAttribute('y', String(y)); node.setAttribute('font-size', '13'); node.setAttribute('fill', color); node.textContent = content; svg.append(node); };
      text(8, 17, title); text(8, 36, `0…${maximum.toPrecision(5)} ${unit}`);
      const axis = document.createElementNS(namespace, 'path'); axis.setAttribute('d', 'M28 46V136H292'); axis.setAttribute('stroke', '#72909c'); axis.setAttribute('fill', 'none'); svg.append(axis);
      const cursor = document.createElementNS(namespace, 'line'); cursor.dataset.w1ProfileCursor = key; cursor.dataset.testid = `w1-profile-cursor-${key}`; cursor.setAttribute('y1', '44'); cursor.setAttribute('y2', '139'); cursor.setAttribute('stroke', '#e9f4e9'); cursor.setAttribute('stroke-width', '1.5'); cursor.setAttribute('stroke-dasharray', '3 3'); svg.append(cursor);
      result.planes.forEach((plane, index) => {
        const x = 28 + (end === 0 ? 0 : plane.z_m / end) * 264, y = 136 - (maximum === 0 ? 0 : plane[key] / maximum) * 82;
        const marker = document.createElementNS(namespace, plane.stage.startsWith('after:') ? 'path' : plane.stage === 'observation' ? 'rect' : 'circle');
        if (marker.tagName === 'path') marker.setAttribute('d', `M${x} ${y - 4}l4 4l-4 4l-4 -4Z`);
        else if (marker.tagName === 'rect') { marker.setAttribute('x', String(x - 3)); marker.setAttribute('y', String(y - 3)); marker.setAttribute('width', '6'); marker.setAttribute('height', '6'); }
        else { marker.setAttribute('cx', String(x)); marker.setAttribute('cy', String(y)); marker.setAttribute('r', plane.stage === 'interior' ? '2.5' : '4'); }
        marker.setAttribute('fill', plane.stage.startsWith('after:') ? '#72c9ca' : '#f2c478'); marker.dataset.sectionId = plane.id; marker.setAttribute('tabindex', '0');
        const label = document.createElementNS(namespace, 'title'); label.textContent = `${plane.id}; z=${plane.z_m.toPrecision(17)} m; ${key}=${plane[key].toPrecision(17)}`; marker.append(label);
        marker.addEventListener('click', () => this.select(index)); marker.addEventListener('keydown', event => { const key = (event as KeyboardEvent).key; if (key === 'Enter' || key === ' ') { event.preventDefault(); this.select(index); } }); svg.append(marker);
      });
      text(28, 160, `z / mm: 0 → ${(end * 1000).toPrecision(6)}`, '#a6c0c9'); host.append(svg);
    }
    const table = document.createElement('table'), header = table.createTHead().insertRow(); for (const title of ['actual plane', 'z / m', 'sampled norm', 'signed ΔN']) { const th = document.createElement('th'); th.textContent = title; header.append(th); }
    result.planes.forEach(plane => { const row = table.insertRow(); for (const value of [plane.stage === 'interior' ? plane.id : plane.stage, plane.z_m.toPrecision(17), plane.norm.toPrecision(17), formatWaveFieldNumber(plane.delta_norm, true)]) row.insertCell().textContent = value; });
    this.area('table').replaceChildren(table); this.showProfile(); this.updateProfileMarker(result);
  }
  private render(state: WaveFieldState): void {
    if (this.disposed) return; const enabled = state.enabled && this.active;
    this.host.hidden = !enabled; this.area('body').hidden = !enabled; this.node<HTMLInputElement>('w1-enable').checked = state.enabled; if (this.options.cursorHost) this.options.cursorHost.hidden = !enabled; this.portEditor(enabled);
    let availability = ''; try { this.syncApparatus(); } catch (error) { availability = String(error); if (this.mounted) this.scene?.hideWaveFieldApparatus(); this.mounted = false; }
    const showing = !!state.currentResult && this.resource?.result === state.currentResult && enabled; this.area('empty-preview').hidden = showing;
    if (!showing) { this.apparatus?.setDisplay(null, null); this.area('canvas-host').replaceChildren(); this.area('profile').replaceChildren(); this.area('table').replaceChildren();
      for (const id of ['w1-pixel', 'w1-section-readout', 'w1-profile-selected', 'w1-stage-note']) this.node(id).textContent = '';
      for (const id of ['w1-summary-z', 'w1-summary-peak', 'w1-summary-norm']) this.node(id).textContent = '—'; this.node('w1-selected-title').textContent = state.lastResult ? 'Stale Result · old field detached; press Simulate' : 'Not Yet Calculated';
      this.node<HTMLSelectElement>('w1-section').disabled = true; this.node<HTMLInputElement>('w1-cursor').disabled = true; }
    else { this.apparatus?.setDisplay(this.resource!.group, this.resource!.detectorTexture); if (!this.resource!.canvas.isConnected) this.area('canvas-host').append(this.resource!.canvas); this.node<HTMLSelectElement>('w1-section').disabled = false; this.updateReadout(); }
    const status = !state.enabled ? 'OFF · ordinary Sequential retained' : state.active ? 'COMPUTING · explicit submission' : state.error || availability ? 'UNAVAILABLE / FAILED'
      : state.renderError ? 'DISPLAY FAILURE · numerical data retained' : showing ? 'SUCCESS · calculated sections' : state.lastResult || state.completedNumerical ? 'STALE / DETACHED · explicitly Simulate' : 'READY · explicitly Simulate';
    for (const id of ['w1-status', 'w1-dock-status']) { this.node(id).textContent = status; this.node(id).dataset.state = showing ? 'success' : state.active ? 'computing' : state.lastResult ? 'stale' : 'ready'; }
    this.node('w1-error').hidden = !state.error && !availability; this.node('w1-error').textContent = state.error ?? availability; this.node('w1-display-error').hidden = !state.renderError; this.node('w1-display-error').textContent = state.renderError ?? '';
    this.node('w1-retry-display').hidden = !state.renderError || !this.controller.canRetryPresentation; this.node<HTMLButtonElement>('w1-retry-display').disabled = this.controller.gate.busy; this.node<HTMLButtonElement>('w1-load-example').disabled = this.controller.gate.busy;
    for (const id of ['w1-beam', 'w1-section-view']) this.node<HTMLButtonElement>(id).disabled = !showing || !this.mounted; this.showTab(); this.refreshPresentationControls();
  }
  numericalOwners(): (WaveFieldResult | null)[] { return [...this.controller.numericalOwners(), ...[...this.displays].map(display => display.result)]; }
  ownedNumericalBytes(): number { return waveFieldOwnedResults(this.numericalOwners()); }
  ownedBytes(): number { return this.ownedNumericalBytes() + (this.apparatus?.ownedBytes ?? 0) + [...this.displays].reduce((n, resource) => n + resource.ownedBytes, 0); }
  borrowedGeometryBytes(): number { return this.apparatus?.borrowedGeometryBytes ?? 0; }
  releaseResults(): void { if (this.controller.gate.busy) return; this.apparatus?.setDisplay(null, null); for (const resource of [...this.displays]) this.drop(resource); this.resource = null;
    this.area('canvas-host').replaceChildren(); this.area('profile').replaceChildren(); this.area('table').replaceChildren(); this.controller.releaseResults(); }
  snapshot(): object {
    const state = this.controller.state, summary = (result: WaveFieldResult | null) => result ? { requestId: result.requestId, experimentSha256: result.experimentSha256,
      experiment: structuredClone(result.experiment), sampling: structuredClone(result.sampling), planes: structuredClone(result.planes), stages: structuredClone(result.stages), shape: [result.planes.length, result.experiment.grid.ny, result.experiment.grid.nx], x: Array.from(result.x), y: Array.from(result.y) } : null;
    return { enabled: state.enabled, activeWorkspace: this.active, mounted: this.mounted, attachmentEpoch: state.attachmentEpoch, active: state.active ? structuredClone(state.active) : null,
      currentResult: summary(state.currentResult), lastResult: summary(state.lastResult), completedNumerical: summary(state.completedNumerical), selectedId: state.currentResult?.planes[this.section]?.id ?? null, selectedIndex: this.section, selectedRow: this.row, selectedColumn: this.column,
      selectedSample: state.currentResult ? sectionSample(state.currentResult, this.section, this.row, this.column) : null, sectionIntensity: state.currentResult ? Array.from(waveFieldSection(state.currentResult, this.section)) : null,
      display: this.resource?.snapshot() ?? null, limits: { ...this.limits }, glow: this.glow, fullPrecision: this.fullPrecision, presentation: { ...this.presentation },
      dock: { tab: this.tab, profileQuantity: this.profileQuantity, activeSectionId: state.currentResult?.planes[this.section]?.id ?? null, activeZ_m: state.currentResult?.planes[this.section]?.z_m ?? null, editorPorted: !!this.options.editorHost && this.options.editorHost.parentElement === this.area('editor') },
      error: state.error, renderError: state.renderError, canRetryPresentation: this.controller.canRetryPresentation, timings: state.timings, ownedBytes: this.ownedBytes(), numericalBytes: this.ownedNumericalBytes(), displayBytes: [...this.displays].reduce((n, resource) => n + resource.ownedBytes, 0), apparatus: this.apparatus?.snapshot() ?? null };
  }
  dispose(): void {
    if (this.disposed) return; this.setActive(false); this.portEditor(false); this.apparatus?.setDisplay(null, null); for (const display of [...this.displays]) this.drop(display); this.resource = null;
    this.disposed = true; this.unsubscribe(); this.unsubscribeSource(); this.unsubscribeGate(); this.controller.bindPresentation(null); this.controller.dispose(); this.scene?.setWaveFieldInteraction(null); this.apparatus?.dispose(); this.apparatus = null;
    this.options.cursorHost?.replaceChildren(); this.editorAnchor?.remove(); this.host.replaceChildren();
  }
}
