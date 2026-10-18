/** Optional Computed Sections inside Sequential. Every viewing action uses already returned data. */
import { structuralEqual, type Experiment } from './contracts';
import { validateColorLimits, type ColorLimits } from './detector';
import type { BenchScene } from './scene';
import { createWaveFieldApparatus, type WaveFieldApparatus } from './wave_field_apparatus';
import { W1_APPARATUS_CAP, requireWaveFieldExperiment, waveFieldOwnedResults, waveFieldSection, type WaveFieldResult } from './wave_field_contracts';
import { formatWaveFieldNumber, prepareWaveFieldDisplay, sectionSample, W1_INITIAL_RANGE, type WaveFieldDisplay } from './wave_field_display';
import { WaveFieldController, type WaveFieldPrepared, type WaveFieldState } from './wave_field_state';

export interface WaveFieldWorkspaceOptions {
  admit(persistent: number, transient: number): void; loadExample(): void | Promise<void>; select(id: string): void;
  cursorHost?: HTMLElement;
}
export class WaveFieldWorkspace {
  private active = true; private disposed = false; private apparatus: WaveFieldApparatus | null = null;
  private apparatusExperiment: Experiment | null = null; private resource: WaveFieldDisplay | null = null;
  private displays = new Set<WaveFieldDisplay>(); private mounted = false; private hasFramed = false;
  private limits: ColorLimits = { ...W1_INITIAL_RANGE }; private glow = true; private fullPrecision = false;
  private section = 0; private row = 0; private column = 0;
  private unsubscribe: () => void; private unsubscribeSource: () => void; private unsubscribeGate: () => void;
  constructor(readonly host: HTMLElement, private readonly scene: BenchScene | null, readonly controller: WaveFieldController,
      private readonly options: WaveFieldWorkspaceOptions) {
    host.innerHTML = `<div class="w1-header"><div><span class="eyebrow">W1 / CALCULATED WAVE-FIELD SECTIONS</span><h2>看見波場穿過光學元件</h2></div>
      <label class="w1-enable"><input type="checkbox" data-testid="w1-enable">Computed Sections</label>
      <button type="button" data-testid="w1-load-example">載入 W1 範例</button><output data-testid="w1-status" aria-live="polite"></output></div>
      <p class="w1-note">Gaussian → physical aperture → ideal thin lens → observation。使用既有 Simulate 明確計算；開啟、相機、游標與色階不會傳播波場。</p>
      <p class="error" data-testid="w1-error" role="alert" hidden></p><p class="error" data-testid="w1-display-error" role="alert" hidden></p>
      <button type="button" data-testid="w1-retry-display" hidden>重建顯示（不重算）</button>
      <div class="w1-body" data-w1="body" hidden><div class="w1-controls">
        <label>真實計算截面 <select data-testid="w1-section" aria-label="實際計算截面"></select></label>
        <label>縱向檢視游標 <input type="range" data-testid="w1-cursor" min="0" max="0" step="1" value="0" aria-label="切換已計算截面"></label>
        <div class="w1-camera-controls"><button type="button" data-testid="w1-overview">全景 Orbit</button><button type="button" data-testid="w1-top">俯視 Top</button><button type="button" data-testid="w1-focus">聚焦 Focus</button><button type="button" data-testid="w1-reset">重設 Reset</button></div>
        <p class="w1-note">薄元件兩側保留同 z 的獨立事件。游標只吸附真實計算截面；琥珀色截面是實際樣本，縱向幕面是事件分段的最近樣本展示，並非連續體積場或側向散射測量。</p>
        <div class="w1-range-controls"><label>共用下限 <input type="number" data-testid="w1-range-min" value="0" step="any"></label><label>共用上限 <input type="number" data-testid="w1-range-max" value="3" step="any"></label>
        <button type="button" data-testid="w1-apply-range">套用色階</button><button type="button" data-testid="w1-auto-range">Auto shared range</button>
        <label><input type="checkbox" data-testid="w1-glow" checked>琥珀亮度增強 · display only</label></div>
        <output class="w1-readout" data-testid="w1-color-limits">0–3 amplitude-unit² · shared linear</output>
      </div><div class="w1-inspector"><div class="w1-inspector-heading"><h3>定量橫截面</h3><label><input type="checkbox" data-testid="w1-full-precision">完整精度（17 位）</label></div>
        <div data-w1="canvas-host" class="w1-canvas-host"></div><div class="w1-pixel-controls"><label>row <input type="number" min="0" step="1" data-testid="w1-row" value="0"></label>
        <label>column <input type="number" min="0" step="1" data-testid="w1-column" value="0"></label></div>
        <output class="w1-readout" data-testid="w1-pixel"></output><output class="w1-readout" data-testid="w1-section-readout"></output>
        <p class="w1-note">灰階採原始 float64 強度、共用線性色階、nearest pixels。row 0 在上，column 0 在左；+y 朝下。取樣總 norm 是全視窗數值，不是孤立無限空間功率保證。</p></div>
        <div class="w1-profile"><h3>已取樣軸向量</h3><div data-w1="profile"></div><p class="w1-note">三圖各自標明縱軸與上限；○ before/source，◇ after，□ observation。相同 z 的事件仍是獨立記錄，孔徑損失不經歸一化。光源/元件支架尺寸為示意；橫向 1000 world/m、縱向 100 world/m。</p>
        <div class="w1-stage-table" tabindex="0" role="region" aria-label="實際截面與 norm，可水平捲動" data-w1="table"></div>
        <p class="w1-note">Periodic full-window ASM · pad_factor=1 · scalar monochromatic forward model。強裁切與邊界/取樣敏感性仍存在，沒有 universal Gaussian envelope fit。</p></div></div>`;
    if (options.cursorHost) {
      options.cursorHost.classList.add('w1-bench-controls');
      const select = this.node('w1-section').closest('label')!, cursor = this.node('w1-cursor').closest('label')!, camera = host.querySelector('.w1-camera-controls')!;
      options.cursorHost.append(this.node('w1-load-example'), select, cursor, camera); options.cursorHost.hidden = true;
    }
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
    for (const [id, view] of [['w1-overview', 'overview'], ['w1-top', 'top'], ['w1-focus', 'focus'], ['w1-reset', 'overview']] as const)
      this.node(id).addEventListener('click', () => { try { if (this.apparatus && this.mounted) this.scene?.fitWaveFieldApparatus(this.apparatus.framingBounds(view === 'focus' ? this.controller.bench.state.selection : undefined), view); }
        catch (error) { this.controller.reportPresentationFailure(String(error)); } });
    this.controller.bindPresentation(result => this.prepare(result));
    this.unsubscribe = this.controller.subscribe(state => this.render(state));
    this.unsubscribeSource = this.controller.bench.subscribe(() => this.render(this.controller.state));
    this.unsubscribeGate = this.controller.gate.subscribe(() => this.render(this.controller.state));
    this.scene?.setWaveFieldInteraction((id, row, column) => {
      const result = this.controller.state.currentResult; if (!result || this.resource?.result !== result) return;
      const index = result.planes.findIndex(plane => plane.id === id); if (index < 0) return; this.row = row; this.column = column; this.select(index);
    });
  }
  private node<T extends HTMLElement = HTMLElement>(id: string): T { const selector = `[data-testid="${id}"]`, node = this.host.querySelector<T>(selector) ?? this.options.cursorHost?.querySelector<T>(selector); if (!node) throw new Error(`Missing W1 ${id}`); return node; }
  private area(id: string): HTMLElement { return this.host.querySelector<HTMLElement>(`[data-w1="${id}"]`)!; }
  setActive(active: boolean): void { this.active = active; this.host.hidden = !active; this.controller.setContext(this.controller.enabled, active); this.render(this.controller.state); }
  private syncApparatus(): void {
    if (!this.controller.enabled || !this.active) { if (this.mounted) this.scene?.hideWaveFieldApparatus(); this.mounted = false; return; }
    const experiment = this.controller.bench.state.validatedDraft;
    if (!experiment) { this.apparatus?.setDisplay(null, null); return; }
    requireWaveFieldExperiment(experiment);
    if (!this.scene) throw new Error('Existing WebGL2 scene unavailable; no substitute calculation is displayed.');
    if (!this.apparatus || !structuralEqual(this.apparatusExperiment, experiment)) {
      this.options.admit(W1_APPARATUS_CAP, W1_APPARATUS_CAP);
      const next = createWaveFieldApparatus(experiment), previous = this.apparatus;
      try { if (this.mounted) this.scene.replaceWaveFieldApparatus(next.group); else { this.scene.showWaveFieldApparatus(next.group); this.mounted = true; }
        this.apparatus = next; this.apparatusExperiment = experiment; previous?.dispose(); }
      catch (error) { next.dispose(); throw error; }
    } else if (!this.mounted) { this.scene.showWaveFieldApparatus(this.apparatus.group); this.mounted = true; }
    this.scene.setWaveFieldLabelUpdater((camera, width, height) => this.apparatus?.updateLabels(camera, width, height));
    this.apparatus.select(this.controller.bench.state.selection);
    if (!this.hasFramed) { this.scene.fitWaveFieldApparatus(this.apparatus.framingBounds(), 'overview'); this.hasFramed = true; }
  }
  private prepare(result: WaveFieldResult): WaveFieldPrepared {
    this.syncApparatus(); if (!this.active || !this.controller.enabled || !this.apparatus || !this.scene) throw new Error('Computed Sections is detached; numerical data retained.');
    this.scene.assertWaveFieldReady();
    const before = this.ownedNumericalBytes(), after = waveFieldOwnedResults([...this.numericalOwners(), result]);
    const { nx, ny } = result.experiment.grid, pixels = nx * ny;
    const displayReserve = result.planes.length * pixels * 4 + pixels * 8 + result.planes.length * (nx + ny) * 8 + 128 * 1024;
    this.options.admit(after - before + displayReserve, after - before + displayReserve + pixels * 8);
    const next = prepareWaveFieldDisplay(result, this.limits, this.glow);
    const previous = this.resource; let committed = false, closed = false;
    const oldChildren = [...this.area('canvas-host').childNodes];
    next.canvas.addEventListener('pointermove', this.pickCanvas); next.canvas.addEventListener('click', this.pickCanvas);
    try { this.options.admit(after - before + next.ownedBytes, after - before + next.ownedBytes + pixels * 8); }
    catch (error) { next.dispose(); throw error; }
    this.displays.add(next);
    return {
      commit: () => { if (closed || this.resource !== previous || !this.active || !this.controller.enabled) throw new Error('W1 presentation destination changed');
        this.scene!.assertWaveFieldReady(); this.apparatus!.setDisplay(next.group, next.detectorTexture);
        this.resource = next; this.area('canvas-host').replaceChildren(next.canvas); committed = true;
        this.section = result.planes.length - 1; this.row = Math.floor(ny / 2); this.column = Math.floor(nx / 2); this.fillSections(result); this.drawProfiles(result); next.select(this.section); },
      dispose: () => { if (closed) return; closed = true; if (committed && this.resource === next) {
          this.resource = previous; this.area('canvas-host').replaceChildren(...oldChildren); this.apparatus?.setDisplay(previous?.group ?? null, previous?.detectorTexture ?? null); }
        this.drop(next); },
      finalize: () => { if (closed) return; closed = true; if (previous && previous !== next) this.drop(previous); },
    };
  }
  private drop(display: WaveFieldDisplay): void { display.canvas.removeEventListener('pointermove', this.pickCanvas); display.canvas.removeEventListener('click', this.pickCanvas); display.dispose(); this.displays.delete(display); }
  private fillSections(result: WaveFieldResult): void {
    const select = this.node<HTMLSelectElement>('w1-section'); select.replaceChildren();
    result.planes.forEach((plane, index) => { const option = document.createElement('option'); option.value = String(index); option.textContent = `${index + 1}/${result.planes.length} · ${(plane.z_m * 1000).toPrecision(7)} mm · ${plane.stage === 'interior' ? plane.id : plane.stage}`; select.append(option); });
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
    if (row < 0 || column < 0 || row >= result.experiment.grid.ny || column >= result.experiment.grid.nx) return;
    this.row = row; this.column = column; this.updateReadout();
  };
  private pickNumeric(): void {
    const result = this.controller.state.currentResult; if (!result) return;
    const row = Number(this.node<HTMLInputElement>('w1-row').value), column = Number(this.node<HTMLInputElement>('w1-column').value);
    try { sectionSample(result, this.section, row, column); this.row = row; this.column = column; this.updateReadout(); }
    catch (error) { this.node('w1-error').textContent = String(error); this.node('w1-error').hidden = false; }
  }
  private updateReadout(): void {
    const result = this.controller.state.currentResult; if (!result || this.resource?.result !== result) return;
    const plane = result.planes[this.section], sample = sectionSample(result, this.section, this.row, this.column), f = (value: number | null) => formatWaveFieldNumber(value, this.fullPrecision);
    this.node<HTMLSelectElement>('w1-section').value = String(this.section); this.node<HTMLInputElement>('w1-cursor').value = String(this.section);
    this.node<HTMLInputElement>('w1-row').value = String(this.row); this.node<HTMLInputElement>('w1-column').value = String(this.column);
    this.node('w1-pixel').textContent = `row=${sample.row}, column=${sample.column}\nx=${f(sample.x_m)} m · y=${f(sample.y_m)} m\nI=${f(sample.intensity)} amplitude-unit²`;
    let saturated = 0; for (const value of waveFieldSection(result, this.section)) if (value > this.limits.max) saturated++;
    this.node('w1-section-readout').textContent = `${plane.id}\nz=${f(plane.z_m)} m · ${plane.stage}\nupstream=${plane.anchor_selector} @ ${f(plane.anchor_z_m)} m · Δz=${f(plane.separation_m)} m\nraw peak=${f(plane.max_intensity)} amplitude-unit²\nN=${f(plane.norm)} amplitude-unit² m²\nΔN=${f(plane.delta_norm)} · ratio=${f(plane.transmission_ratio)}\ncomparison=${plane.comparison} · saturated=${saturated}/${result.experiment.grid.nx * result.experiment.grid.ny}\nrequest=${result.requestId}`;
    this.node('w1-color-limits').textContent = `${f(this.limits.min)}–${f(this.limits.max)} amplitude-unit² · shared linear (retained until explicit change)`;
  }
  private changeRange(auto: boolean): void {
    const result = this.controller.state.currentResult; const previous = this.limits;
    try { const peak = result ? Math.max(...result.planes.map(plane => plane.max_intensity)) : 0;
      const limits = auto ? { min: 0, max: peak > 0 ? peak : 1 } : { min: Number(this.node<HTMLInputElement>('w1-range-min').value), max: Number(this.node<HTMLInputElement>('w1-range-max').value) };
      validateColorLimits(limits); this.limits = limits;
      if (!this.rebuildDisplay()) this.limits = previous;
      this.node<HTMLInputElement>('w1-range-min').value = String(this.limits.min); this.node<HTMLInputElement>('w1-range-max').value = String(this.limits.max); this.updateReadout();
    } catch (error) { this.limits = previous; this.node('w1-error').textContent = String(error); this.node('w1-error').hidden = false; }
  }
  private rebuildDisplay(): boolean {
    const result = this.controller.state.currentResult; if (!result) return true;
    const selected = this.section, row = this.row, column = this.column; let transaction: WaveFieldPrepared | null = null;
    try { transaction = this.prepare(result); transaction.commit(); this.section = selected; this.row = row; this.column = column;
      this.resource!.select(selected); this.updateReadout(); transaction.finalize(); return true; }
    catch (error) { transaction?.dispose(); this.node('w1-error').textContent = `Display change rejected; previous result retained: ${String(error)}`; this.node('w1-error').hidden = false; return false; }
  }
  private drawProfiles(result: WaveFieldResult): void {
    const host = this.area('profile'); host.replaceChildren(); const namespace = 'http://www.w3.org/2000/svg';
    for (const [key, title, unit] of [['on_axis_intensity', 'On-axis sampled intensity', 'amplitude-unit²'], ['max_intensity', 'Maximum transverse intensity', 'amplitude-unit²'], ['norm', 'Sampled norm', 'amplitude-unit² m²']] as const) {
      const svg = document.createElementNS(namespace, 'svg'); svg.setAttribute('viewBox', '0 0 620 138'); svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', title); svg.dataset.quantity = key;
      const maximum = Math.max(...result.planes.map(plane => plane[key])), end = result.experiment.observation.z_m;
      const text = document.createElementNS(namespace, 'text'); text.setAttribute('x', '8'); text.setAttribute('y', '16'); text.setAttribute('fill', '#dce9ec'); text.textContent = `${title} · 0…${maximum.toPrecision(5)} ${unit}`; svg.append(text);
      const axis = document.createElementNS(namespace, 'path'); axis.setAttribute('d', 'M36 28V106H600'); axis.setAttribute('stroke', '#72909c'); axis.setAttribute('fill', 'none'); svg.append(axis);
      result.planes.forEach((plane, index) => {
        const x = 36 + (end === 0 ? 0 : plane.z_m / end) * 564, y = 106 - (maximum === 0 ? 0 : plane[key] / maximum) * 70;
        const marker = document.createElementNS(namespace, plane.stage.startsWith('after:') ? 'path' : plane.stage === 'observation' ? 'rect' : 'circle');
        if (marker.tagName === 'path') marker.setAttribute('d', `M${x} ${y - 4}l4 4l-4 4l-4 -4Z`);
        else if (marker.tagName === 'rect') { marker.setAttribute('x', String(x - 3)); marker.setAttribute('y', String(y - 3)); marker.setAttribute('width', '6'); marker.setAttribute('height', '6'); }
        else { marker.setAttribute('cx', String(x)); marker.setAttribute('cy', String(y)); marker.setAttribute('r', plane.stage === 'interior' ? '2' : '4'); }
        marker.setAttribute('fill', plane.stage.startsWith('after:') ? '#72c9ca' : '#f2c478'); marker.dataset.sectionId = plane.id; marker.setAttribute('tabindex', '0');
        const label = document.createElementNS(namespace, 'title'); label.textContent = `${plane.id}; z=${plane.z_m.toPrecision(17)} m; ${key}=${plane[key].toPrecision(17)}`; marker.append(label);
        marker.addEventListener('click', () => this.select(index)); marker.addEventListener('keydown', event => { const key = (event as KeyboardEvent).key; if (key === 'Enter' || key === ' ') { event.preventDefault(); this.select(index); } }); svg.append(marker);
      });
      const units = document.createElementNS(namespace, 'text'); units.setAttribute('x', '36'); units.setAttribute('y', '129'); units.setAttribute('fill', '#a6c0c9'); units.textContent = `z: 0 → ${(end * 1000).toPrecision(6)} mm · discrete samples; no connecting interpolation`; svg.append(units); host.append(svg);
    }
    const table = document.createElement('table'); const header = table.createTHead().insertRow(); for (const title of ['actual plane', 'z / m', 'sampled norm', 'signed ΔN']) { const th = document.createElement('th'); th.textContent = title; header.append(th); }
    result.planes.forEach(plane => { const row = table.insertRow(); for (const value of [plane.stage === 'interior' ? plane.id : plane.stage, plane.z_m.toPrecision(17), plane.norm.toPrecision(17), formatWaveFieldNumber(plane.delta_norm, true)]) row.insertCell().textContent = value; });
    this.area('table').replaceChildren(table);
  }
  private render(state: WaveFieldState): void {
    if (this.disposed) return;
    this.node<HTMLInputElement>('w1-enable').checked = state.enabled; this.area('body').hidden = !state.enabled;
    if (this.options.cursorHost) this.options.cursorHost.hidden = !state.enabled || !this.active;
    let availability = '';
    try { this.syncApparatus(); } catch (error) { availability = String(error); if (this.mounted) this.scene?.hideWaveFieldApparatus(); this.mounted = false; }
    const showing = !!state.currentResult && this.resource?.result === state.currentResult && state.enabled && this.active;
    if (!showing) { this.apparatus?.setDisplay(null, null); this.area('canvas-host').replaceChildren(); this.area('profile').replaceChildren(); this.area('table').replaceChildren(); this.node('w1-pixel').textContent = ''; this.node('w1-section-readout').textContent = '';
      this.node<HTMLSelectElement>('w1-section').disabled = true; this.node<HTMLInputElement>('w1-cursor').disabled = true; }
    else { this.apparatus?.setDisplay(this.resource!.group, this.resource!.detectorTexture); if (!this.resource!.canvas.isConnected) this.area('canvas-host').append(this.resource!.canvas);
      this.node<HTMLSelectElement>('w1-section').disabled = false; this.updateReadout(); }
    const status = !state.enabled ? 'OFF · ordinary Sequential retained' : state.active ? 'COMPUTING · one explicit submission'
      : state.error || availability ? 'UNAVAILABLE / FAILED' : state.renderError ? 'DISPLAY FAILURE · numerical data retained' : showing ? 'SUCCESS · calculated sections'
      : state.lastResult || state.completedNumerical ? 'STALE / DETACHED · explicitly Simulate' : 'READY · explicitly Simulate';
    this.node('w1-status').textContent = status; this.node('w1-status').dataset.state = showing ? 'success' : state.active ? 'computing' : state.lastResult ? 'stale' : 'ready';
    this.node('w1-error').hidden = !state.error && !availability; this.node('w1-error').textContent = state.error ?? availability;
    this.node('w1-display-error').hidden = !state.renderError; this.node('w1-display-error').textContent = state.renderError ?? '';
    this.node('w1-retry-display').hidden = !state.renderError || !this.controller.canRetryPresentation;
    this.node<HTMLButtonElement>('w1-retry-display').disabled = this.controller.gate.busy;
    this.node<HTMLButtonElement>('w1-load-example').disabled = this.controller.gate.busy;
  }
  numericalOwners(): (WaveFieldResult | null)[] { return [...this.controller.numericalOwners(), ...[...this.displays].map(display => display.result)]; }
  ownedNumericalBytes(): number { return waveFieldOwnedResults(this.numericalOwners()); }
  ownedBytes(): number { return this.ownedNumericalBytes() + (this.apparatus?.ownedBytes ?? 0) + [...this.displays].reduce((n, display) => n + display.ownedBytes, 0); }
  /** Deduct only when the app ledger has already charged the shared global Sprite quad. */
  borrowedGeometryBytes(): number { return this.apparatus?.borrowedGeometryBytes ?? 0; }
  releaseResults(): void {
    if (this.controller.gate.busy) return; this.apparatus?.setDisplay(null, null); for (const resource of [...this.displays]) this.drop(resource); this.resource = null;
    this.area('canvas-host').replaceChildren(); this.area('profile').replaceChildren(); this.area('table').replaceChildren(); this.controller.releaseResults();
  }
  snapshot(): object {
    const state = this.controller.state;
    const summary = (result: WaveFieldResult | null) => result ? { requestId: result.requestId, experimentSha256: result.experimentSha256,
      experiment: structuredClone(result.experiment), sampling: structuredClone(result.sampling), planes: structuredClone(result.planes), stages: structuredClone(result.stages),
      shape: [result.planes.length, result.experiment.grid.ny, result.experiment.grid.nx], x: Array.from(result.x), y: Array.from(result.y) } : null;
    return { enabled: state.enabled, activeWorkspace: this.active, mounted: this.mounted, attachmentEpoch: state.attachmentEpoch,
      active: state.active ? structuredClone(state.active) : null, currentResult: summary(state.currentResult), lastResult: summary(state.lastResult), completedNumerical: summary(state.completedNumerical),
      selectedId: state.currentResult?.planes[this.section]?.id ?? null, selectedIndex: this.section, selectedRow: this.row, selectedColumn: this.column,
      selectedSample: state.currentResult ? sectionSample(state.currentResult, this.section, this.row, this.column) : null,
      sectionIntensity: state.currentResult ? Array.from(waveFieldSection(state.currentResult, this.section)) : null,
      display: this.resource?.snapshot() ?? null, limits: { ...this.limits }, glow: this.glow, fullPrecision: this.fullPrecision,
      error: state.error, renderError: state.renderError, canRetryPresentation: this.controller.canRetryPresentation, timings: state.timings,
      ownedBytes: this.ownedBytes(), numericalBytes: this.ownedNumericalBytes(), displayBytes: [...this.displays].reduce((n, resource) => n + resource.ownedBytes, 0), apparatus: this.apparatus?.snapshot() ?? null };
  }
  dispose(): void {
    if (this.disposed) return; this.setActive(false); this.apparatus?.setDisplay(null, null);
    for (const display of [...this.displays]) this.drop(display); this.resource = null;
    this.disposed = true; this.unsubscribe(); this.unsubscribeSource(); this.unsubscribeGate();
    this.controller.bindPresentation(null); this.controller.dispose(); this.scene?.setWaveFieldInteraction(null); this.apparatus?.dispose(); this.apparatus = null;
    this.options.cursorHost?.replaceChildren();
    this.host.replaceChildren();
  }
}
