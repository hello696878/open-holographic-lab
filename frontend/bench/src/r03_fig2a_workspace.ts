/** Integrated A workspace, with atomic display publication and no measured-data path. */
import type { BenchScene } from './scene';
import { R03Controller, R03_COMPONENTS, type R03State, type R03Prepared } from './r03_fig2a_state';
import { R03_IDENTITY, R03_MODEL, type R03Result, type R03StageId } from './r03_fig2a_contracts';
import { createR03Apparatus, R03_COMPONENT_LABELS, type R03Apparatus } from './r03_fig2a_apparatus';
import { R03_APPARATUS_CAP, R03_PHASE_DISPLAY_BYTES, R03_RESULT_METADATA_RESERVATION, R03_TRANSPORT_RESERVATION,
  R03_PHASE_GRADIENT, prepareR03Display, r03OwnedResults, r03ResultSnapshot, formatR03Number, type R03Display } from './r03_fig2a_display';

const stageNames: Record<R03StageId, string> = { source: 'Source · 入射 D 態', after_slm: 'SLM · 相位調制後', after_qwp: 'QWP · 四分之一波片後', output: 'Output · 最終統計讀值' };
const explanations: Record<string, string> = {
  source: 'D source = A·(1,1)/√2。A 的單位是 amplitude unit；S₀ 為機率平均強度，不是校準瓦特。',
  input_hwp: '輸入準備圖示：本模型直接指定 D 輸入。支架角度與距離是功能示意，不是恢復的實驗設定。',
  router: '反射路由的功能連接；器件型式、分光比、距離與歷史角度 UNKNOWN。本模型不推導其 transfer matrix。',
  slm: '只對 x 分量乘 exp(iφ)。256 個局部 coherent Jones samples，以明定的等機率 second moment 觀察；random mask 本身不證明 incoherent collection。',
  qwp: '理想 QWP：δ=π/2；作用在所選同一代數基底。角度是本模型輸入，沒有額外空間傳播。',
  hwp: '理想 HWP：δ=π；與 QWP 依序作用。Lossless retarder 應保留 S₀、coherency eigenvalues 與 DoP。',
  measurement: 'C = Σ(1/256) EₘEₘ†，uncentered probability mean。不是 coherent field sum，也不是 M−1 covariance。',
};
const fields = [
  ['source_amplitude', 'Source amplitude A', 'amplitude unit · 0…10⁶', 'source'],
  ['mean_phase_rad', 'Mean phase μ', 'rad · −2π…2π', 'slm'],
  ['phase_std_rad', 'Phase standard deviation σ', 'rad · 0…π；不是 variance', 'slm'],
  ['seed', 'Realization seed', 'PCG64 · integer 0…2³²−1', 'slm'],
  ['qwp_angle_rad', 'QWP axis angle', 'rad · −2π…2π', 'qwp'],
  ['hwp_angle_rad', 'HWP axis angle', 'rad · −2π…2π', 'hwp'],
] as const;
export interface R03WorkspaceOptions {
  /** Admission includes all pre-existing mode/document owners and rollback overlap. */
  admit(extraPersistent: number, extraTransient: number): void;
  reserveOperation(extraPersistent: number, extraTransient: number): void;
}
export class R03Workspace {
  readonly host: HTMLElement; readonly viewport: HTMLElement;
  private apparatus: R03Apparatus | null = null; private active = false; private resource: R03Display | null = null;
  private displays = new Set<R03Display>(); private unsubscribe: () => void; private selectedSample = 0;
  private disposed = false; private readonly inputs = new Map<string, HTMLInputElement>(); private unsubscribeGate: () => void;
  constructor(host: HTMLElement, readonly controller: R03Controller, private scene: BenchScene | null, private options: R03WorkspaceOptions) {
    this.host = host;
    host.innerHTML = `<div class="r03-hero"><div><span class="r03-eyebrow">RESEARCH WORKSPACE / DECLARED IDEAL ENSEMBLE</span>
      <h2>${R03_IDENTITY}</h2><p>理想統計偏振 · 256 個局部相干態，一個明確的 second-moment 觀察。</p></div><span class="r03-badge">A · INDEPENDENT MODEL</span></div>
      <div class="r03-grid"><aside class="r03-card r03-inspector"><div class="r03-section-label">01 / CONFIGURE & SELECT</div><h3>模型設定與元件</h3>
        <nav data-r03="components" aria-label="理想裝置元件"></nav><div class="r03-selected"><strong data-r03="selected-label"></strong><p data-r03="selected-explanation"></p></div>
        <div data-r03="fields"></div><p class="r03-small">M=256 · 16×16 · equal probability 1/256。無 sweep、fitting 或實驗資料匯入。</p></aside>
      <div class="r03-center"><section class="r03-card r03-apparatus-card"><div class="r03-section-label">02 / MOUNTED APPARATUS</div>
        <div class="r03-card-heading"><h3>相位調制與理想統計觀察</h3><span class="r03-guide-badge">FUNCTIONAL SCHEMATIC</span></div>
        <div class="r03-viewport" data-r03="viewport" data-testid="r03-viewport"></div>
        <div class="r03-camera"><button data-r03="camera-reset" data-testid="r03-reset-view">重設視角</button><button data-r03="zoom-in" aria-label="理想裝置放大">＋</button><button data-r03="zoom-out" aria-label="理想裝置縮小">−</button><span>拖曳旋轉 · 右鍵平移 · 滾輪縮放 · 點擊選取</span></div>
        <div class="r03-legend"><span><i class="r03-dash"></i> Layout guides</span><span><i class="r03-square"></i> Calculated phase / statistics</span><span>Computed rays / propagated field sections：未實作</span></div>
        <p class="r03-small">反射折返、支架與距離為功能設計；未推導物理光線、繞射、路由方塊型式或收集孔徑。</p></section>
      <section class="r03-card r03-compute"><div><div class="r03-section-label">03 / EXPLICIT SUBMISSION</div><output data-r03="status" data-testid="r03-status" aria-live="polite"></output></div>
        <button class="primary" data-r03="compute" data-testid="r03-compute">計算此 ensemble</button><button data-r03="retry" data-testid="r03-retry-display" hidden>重新顯示已計算結果</button>
        <p data-r03="error" data-testid="r03-error" class="error" role="alert" hidden></p><p data-r03="display-error" data-testid="r03-display-error" class="error" role="alert" hidden></p>
        <p class="r03-small">編輯只驗證；只有按下計算才產生一個 realization。視角、元件選取與 phase sample inspection 不計算。</p></section>
      <section class="r03-card"><div class="r03-section-label">MODEL ASSUMPTIONS / PROVENANCE</div>
        <p class="r03-assumptions">C = Σ pₘEₘEₘ† · pₘ=1/256 · exp(−iωt) · (+x,+y) · S₃=−2 Im Cxy</p>
        <p class="r03-small">Gaussian unwrapped φ=μ+σz → wrapped φ mod 2π。沒有 centering、variance correction、clipping、quantization 或 browser RNG。Random phases 本身不建立 incoherent collection；本工作區明確選定 ideal statistical measurement。</p>
        <details><summary>完整模型身份與限制</summary><pre data-r03="provenance"></pre></details>
        <p class="r03-b-deferred">B / Figure 2a experimental comparison：另行門控；observable、axes 與 estimator lineage 未建立。本模型不宣稱實驗重現。</p></section></div>
      <aside class="r03-readout"><section class="r03-card"><div class="r03-section-label">04 / SUBMITTED PHASE REALIZATION</div><h3>實際提交的 phase mask</h3>
        <div data-r03="phase-empty" class="r03-empty">尚未計算<br><small>不使用另一個預覽 RNG 或替代遮罩。</small></div><div data-r03="current" hidden>
        <div data-r03="phase-host" class="r03-phase-host"></div><div class="r03-colorbar"></div><div class="r03-phase-scale"><span>0</span><span>π</span><span>2π rad</span></div>
        <p class="r03-small">row 0 在上、column 0 在左 · C-order · 16×16。點擊查看同一 realization 的原值。</p><output data-r03="sample" data-testid="r03-sample" class="r03-sample"></output></div>
        <p data-r03="identity" data-testid="r03-result-identity" class="r03-identity"></p></section>
      <section class="r03-card"><div class="r03-section-label">05 / FINITE ENSEMBLE OBSERVABLES</div><h3>Coherency · Stokes · DoP</h3>
        <div data-r03="readout-empty" class="r03-empty">由同一次計算產生的讀值</div><div data-r03="readout" hidden></div></section>
      </aside></div>`;
    this.viewport = this.node('viewport'); this.node('provenance').textContent = `${R03_MODEL}\nLocal PCG64 / Generator.standard_normal((16,16))\nOne explicit submitted ensemble.\nNot calibrated PAX output; not Figure 2a reproduced.`;
    this.host.querySelector<HTMLElement>('.r03-colorbar')!.style.background = R03_PHASE_GRADIENT;
    for (const id of R03_COMPONENTS) { const button = document.createElement('button'); button.textContent = R03_COMPONENT_LABELS[id];
      button.dataset.component = id; button.dataset.testid = `r03-select-${id}`; button.addEventListener('click', () => controller.select(id)); this.node('components').append(button); }
    for (const [key, title, hint, component] of fields) { const label = document.createElement('label'); label.className = 'r03-number-field'; label.dataset.component = component;
      const text = document.createElement('span'); text.textContent = title; const input = document.createElement('input'); input.type = 'text'; input.inputMode = key === 'seed' ? 'numeric' : 'decimal';
      input.autocomplete = 'off'; input.dataset.testid = `r03-edit-${key}`; input.setAttribute('aria-label', title);
      const help = document.createElement('small'); help.textContent = hint; label.append(text, input, help); this.inputs.set(key, input); this.node('fields').append(label);
      input.addEventListener('input', () => { void controller.edit(key, input.value); }); }
    this.node('compute').addEventListener('click', () => { void controller.simulate(); }); this.node('retry').addEventListener('click', () => controller.retryPresentation());
    this.node('camera-reset').addEventListener('click', () => this.scene?.resetCamera()); this.node('zoom-in').addEventListener('click', () => this.scene?.zoom(.8)); this.node('zoom-out').addEventListener('click', () => this.scene?.zoom(1.25));
    controller.setOperationAdmission(() => this.options.reserveOperation(4096 + R03_RESULT_METADATA_RESERVATION + R03_PHASE_DISPLAY_BYTES, R03_TRANSPORT_RESERVATION + 4096 + R03_RESULT_METADATA_RESERVATION + 4096));
    controller.setResultPreparer(result => this.prepare(result)); this.unsubscribe = controller.subscribe(state => this.render(state));
    this.unsubscribeGate = controller.gate.subscribe(() => this.render(controller.state));
  }
  private node<T extends HTMLElement = HTMLElement>(key: string): T { const value = this.host.querySelector<T>(`[data-r03="${key}"]`); if (!value) throw new Error(`Missing ideal workspace ${key}`); return value; }
  enter(): void { if (this.disposed) return; this.active = true; this.host.hidden = false;
    try { if (!this.scene) throw new Error('既有 WebGL2 renderer 不可用；未產生替代裝置。');
      if (!this.apparatus) { this.options.admit(R03_APPARATUS_CAP, R03_APPARATUS_CAP); this.apparatus = createR03Apparatus(); }
      this.scene.showResearchApparatus(this.viewport, this.apparatus.group); this.render(this.controller.state);
    } catch (error) { this.controller.reportRenderFailure(String(error)); this.viewport.textContent = '3D 裝置不可用；請查看顯示錯誤。沒有產生替代光學結果。'; }
    void this.controller.activate();
  }
  leave(): void { this.active = false; this.controller.deactivate(); this.apparatus?.setPhase(null); this.scene?.hideResearchApparatus(); this.host.hidden = true; }
  private prepare(result: R03Result): R03Prepared {
    if (!this.active || !this.apparatus || !this.scene) throw new Error('理想裝置未掛載；數值結果保留，尚未顯示。');
    this.scene.assertResearchReady();
    const before = this.ownedNumericalBytes(), after = r03OwnedResults([...this.numericalOwners(), result]);
    this.options.admit(after - before + R03_PHASE_DISPLAY_BYTES, after - before + R03_PHASE_DISPLAY_BYTES + 1024);
    const next = prepareR03Display(result); this.displays.add(next); let content: HTMLElement;
    try { content = this.readout(result); } catch (error) { next.dispose(); this.displays.delete(next); throw error; }
    const previous = this.resource, oldReadout = [...this.node('readout').childNodes], oldPhase = [...this.node('phase-host').childNodes];
    let committed = false, closed = false;
    return {
      commit: () => { if (closed || !this.active || this.resource !== previous) throw new Error('Ideal display transaction changed'); this.scene!.assertResearchReady();
        committed = true; this.resource = next; this.node('readout').replaceChildren(content); this.node('phase-host').replaceChildren(next.canvas);
        this.apparatus!.setPhase(next.texture); this.selectedSample = 0; next.canvas.addEventListener('click', this.pickPhase); },
      dispose: () => { if (closed) return; closed = true; if (committed && this.resource === next) { this.resource = previous;
          this.node('readout').replaceChildren(...oldReadout); this.node('phase-host').replaceChildren(...oldPhase); this.apparatus?.setPhase(previous?.texture ?? null); }
        next.canvas.removeEventListener('click', this.pickPhase); next.dispose(); this.displays.delete(next); },
      finalize: () => { if (closed) return; closed = true; if (previous) { previous.canvas.removeEventListener('click', this.pickPhase); previous.dispose(); this.displays.delete(previous); } },
    };
  }
  private pickPhase = (event: MouseEvent): void => { if (!this.resource || this.controller.state.currentResult !== this.resource.result) return;
    const rect = this.resource.canvas.getBoundingClientRect(); const column = Math.max(0, Math.min(15, Math.floor((event.clientX - rect.left) / rect.width * 16)));
    const row = Math.max(0, Math.min(15, Math.floor((event.clientY - rect.top) / rect.height * 16))); this.selectedSample = row * 16 + column; this.render(this.controller.state); };
  private readout(result: R03Result): HTMLElement {
    const host = document.createElement('div'), final = result.stages[3];
    const headline = document.createElement('div'); headline.className = 'r03-dop'; headline.innerHTML = '<span>Finite ensemble DoP</span><strong data-testid="r03-dop"></strong>';
    headline.querySelector('strong')!.textContent = formatR03Number(final.degree_of_polarization); host.append(headline);
    const intensity = document.createElement('p'); intensity.className = 'r03-intensity'; intensity.dataset.testid = 'r03-intensity'; intensity.textContent = `S₀ = ${formatR03Number(final.stokes[0])} amplitude-unit² · probability mean`; host.append(intensity);
    if (final.stokes[0] === 0) { const dark = document.createElement('p'); dark.className = 'r03-dark'; dark.textContent = 'Dark source：DoP、normalized Stokes、direction 均未定義（null），不以 0 或 epsilon 代替。'; host.append(dark); }
    for (const measurement of result.stages) {
      const section = document.createElement('details'); section.open = measurement.id === 'output'; const summary = document.createElement('summary'); summary.textContent = stageNames[measurement.id]; section.append(summary);
      const matrix = document.createElement('pre'); matrix.className = 'r03-matrix'; matrix.textContent = 'C / amplitude-unit²\n' + measurement.coherency.map(row => row.map(c => `${formatR03Number(c.re)} ${c.im < 0 ? '−' : '+'} ${formatR03Number(Math.abs(c.im))}i`).join('    ')).join('\n'); section.append(matrix);
      const table = document.createElement('table'); const entries: [string, string][] = measurement.stokes.map((value, index) => [`S${index}`, formatR03Number(value)]);
      entries.push(['DoP', formatR03Number(measurement.degree_of_polarization)], ['S/S₀', measurement.normalized_stokes?.map(formatR03Number).join(', ') ?? 'undefined'],
        ['S/|S| direction', measurement.polarized_direction?.map(formatR03Number).join(', ') ?? 'undefined'], ['Eigenvalues', measurement.eigenvalues.map(formatR03Number).join(', ')], ['Roundoff limited', String(measurement.roundoff_limited)]);
      for (const [key, value] of entries) { const row = table.insertRow(); row.insertCell().textContent = key; row.insertCell().textContent = value; } section.append(table); host.append(section);
    }
    const population = document.createElement('p'); population.className = 'r03-population'; population.textContent = `Infinite Gaussian ensemble expectation · ${formatR03Number(result.population.infinite_gaussian_degree_of_polarization)}\n${result.population.assumption}\n解析 population 值不取代上方實際 finite realization，也不是實驗誤差。`; host.append(population); return host;
  }
  private render(state: R03State): void {
    for (const [key, input] of this.inputs) { if (document.activeElement !== input) input.value = state.invalidEdits[key] ?? String(state.candidate[key as keyof typeof state.candidate]);
      input.classList.toggle('invalid', Object.hasOwn(state.invalidEdits, key)); input.closest('label')?.classList.toggle('selected-field', input.closest('label')?.getAttribute('data-component') === state.selection); }
    this.host.querySelectorAll<HTMLButtonElement>('[data-component]').forEach(button => { if (button.tagName === 'BUTTON') button.classList.toggle('selected', button.dataset.component === state.selection); });
    this.node('selected-label').textContent = R03_COMPONENT_LABELS[state.selection]; this.node('selected-explanation').textContent = explanations[state.selection];
    this.apparatus?.select(state.selection); this.apparatus?.setAngles(state.candidate.qwp_angle_rad, state.candidate.hwp_angle_rad);
    const ready = !!state.validatedDraft && !state.pendingValidation && !Object.keys(state.invalidEdits).length;
    this.node<HTMLButtonElement>('compute').disabled = !ready || this.controller.gate.busy;
    const showing = !!state.currentResult && this.resource?.result === state.currentResult;
    this.node('current').hidden = !showing; this.node('readout').hidden = !showing; this.node('phase-empty').hidden = showing; this.node('readout-empty').hidden = showing;
    if (!showing) this.apparatus?.setPhase(null); else if (this.active) this.apparatus?.setPhase(this.resource!.texture);
    const status = state.active ? 'COMPUTING · 計算一個明確提交的 ensemble' : state.pendingValidation ? 'VALIDATING · 草稿驗證中'
      : state.error ? 'INVALID / FAILED · 沒有自動重算' : state.renderError ? 'DISPLAY FAILURE · 數值保留，等待明確的顯示恢復' : showing ? 'SUCCESS · 顯示同一 submitted realization'
      : state.lastResult || state.completedNumerical ? 'STALE / DETACHED · 先前結果不屬於目前顯示身份' : ready ? 'READY · 待明確計算' : '尚未驗證';
    this.node('status').textContent = status; this.node('status').dataset.state = state.active ? 'computing' : showing ? 'success' : state.error ? 'error' : state.lastResult ? 'stale' : 'ready';
    this.node('error').hidden = !state.error; this.node('error').textContent = state.error;
    this.node('display-error').hidden = !state.renderError; this.node('display-error').textContent = state.renderError ? `DISPLAY FAILURE · ${state.renderError} · 數值結果保留；不會重送計算。` : '';
    this.node('retry').hidden = !state.renderError || !this.controller.canRetryPresentation;
    this.node<HTMLButtonElement>('retry').disabled = !ready || !this.controller.canRetryPresentation;
    this.node('phase-empty').innerHTML = state.lastResult || state.completedNumerical ? '先前 phase 與讀值已分離<br><small>編輯／切換後不把舊遮罩重標為新結果。</small>' : '尚未計算<br><small>不使用另一個預覽 RNG 或替代遮罩。</small>';
    this.node('identity').textContent = showing ? `SUBMITTED RESULT\n${state.currentResult!.requestId}\nseed ${state.currentResult!.experiment.seed}\nSHA-256 ${state.currentResult!.experimentSha256}` : `No current submitted result · draft revision ${state.revision}`;
    if (showing) { const result = state.currentResult!, i = this.selectedSample; this.node('sample').textContent = `row=${Math.floor(i / 16)}, col=${i % 16}, index=${i}\nwrapped=${result.phase.wrapped[i].toPrecision(17)} rad\nunwrapped=${result.phase.unwrapped[i].toPrecision(17)} rad`;
      this.node('provenance').textContent = JSON.stringify({ experiment: result.experiment, provenance: result.provenance, limitations: result.limitations }, null, 2); }
  }
  numericalOwners(): (R03Result | null)[] { return [this.controller.state.lastResult, this.controller.state.completedNumerical, this.controller.state.currentResult,
    ...[...this.displays].map(display => display.result)]; }
  ownedNumericalBytes(): number { return r03OwnedResults(this.numericalOwners()); }
  ownedBytes(): number { return this.ownedNumericalBytes() + (this.apparatus?.ownedBytes ?? 0) + [...this.displays].reduce((n, display) => n + display.ownedBytes, 0); }
  releaseResults(): void { this.apparatus?.setPhase(null); for (const resource of this.displays) { resource.canvas.removeEventListener('click', this.pickPhase); resource.dispose(); }
    this.displays.clear(); this.resource = null; this.node('phase-host').replaceChildren(); this.node('readout').replaceChildren(); this.controller.releaseResults(); }
  snapshot(): object { const s = this.controller.state; return { activeWorkspace: this.active, candidate: { ...s.candidate }, validatedDraft: s.validatedDraft ? { ...s.validatedDraft } : null,
    pendingValidation: s.pendingValidation, canRetryPresentation: this.controller.canRetryPresentation, invalidEdits: { ...s.invalidEdits }, revision: s.revision, attachmentEpoch: s.attachmentEpoch, selection: s.selection,
    error: s.error, renderError: s.renderError, active: s.active ? structuredClone(s.active) : null,
    currentResult: r03ResultSnapshot(s.currentResult), lastResult: r03ResultSnapshot(s.lastResult), completedNumerical: r03ResultSnapshot(s.completedNumerical),
    displayedRequestId: this.resource && s.currentResult === this.resource.result ? this.resource.result.requestId : null,
    selectedSample: this.selectedSample, phaseRGBA: this.resource && s.currentResult === this.resource.result ? Array.from(this.resource.rgba) : null,
    ownedBytes: this.ownedBytes(), numericalBytes: this.ownedNumericalBytes(), phaseDisplayBytes: [...this.displays].reduce((n, d) => n + d.ownedBytes, 0), apparatus: this.apparatus?.snapshot() ?? null }; }
  dispose(): void { if (this.disposed) return; this.disposed = true; this.unsubscribe(); this.unsubscribeGate(); this.releaseResults(); this.apparatus?.dispose(); this.apparatus = null; }
}
