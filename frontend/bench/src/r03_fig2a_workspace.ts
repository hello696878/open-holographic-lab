/** A-only laboratory presentation. Scientific state remains in the unchanged controller. */
import type { BenchScene } from './scene';
import { R03Controller, R03_COMPONENTS, type R03State, type R03Prepared } from './r03_fig2a_state';
import { R03_IDENTITY, R03_MODEL, type R03Result, type R03StageId } from './r03_fig2a_contracts';
import { createR03Apparatus, R03_COMPONENT_LABELS, type R03Apparatus } from './r03_fig2a_apparatus';
import { R03_APPARATUS_CAP, R03_PHASE_DISPLAY_BYTES, R03_RESULT_METADATA_RESERVATION, R03_TRANSPORT_RESERVATION,
  R03_PHASE_GRADIENT, prepareR03Display, r03OwnedResults, r03ResultSnapshot, formatR03Readout, type R03Display } from './r03_fig2a_display';
const stageNames: Record<R03StageId, string> = { source: 'Source · 入射 D 態', after_slm: 'SLM · 相位調制後', after_qwp: 'QWP · 四分之一波片後', output: 'Output · 最終讀值' };
const componentStage: Record<string, R03StageId | null> = { source: 'source', input_hwp: 'source', router: null, slm: 'after_slm', qwp: 'after_qwp', hwp: 'output', measurement: 'output' };
const explanations: Record<string, string> = {
  source: 'D source = A·(1,1)/√2。A 為 amplitude unit；S₀ 是機率平均強度，並非校準瓦特。',
  input_hwp: '唯讀輸入準備示意。本模型直接指定 D 態；圖示不是可調波片，也不是恢復的歷史實驗設定。',
  router: 'UNKNOWN · 中性功能連接。器件型式、分光比、距離與歷史角度未知；沒有 transfer matrix 或獨立計算階段。',
  slm: '對 x 分量乘 exp(iφ)。256 個局部 coherent Jones samples；以等機率 second moment 觀察。',
  qwp: '理想 QWP · 固定延遲 δ=π/2。角度作用於同一代數基底，無額外空間傳播。',
  hwp: '理想 HWP · 固定延遲 δ=π。與 QWP 依序作用；不引入損耗或空間傳播。',
  measurement: 'C = Σ(1/256) EₘEₘ†。Uncentered probability mean；不是 coherent field sum 或 M−1 covariance。',
};
const fields = [
  ['source_amplitude', '振幅 A · Source', 'amplitude unit · 0…10⁶', 'source'],
  ['mean_phase_rad', '平均相位 μ', 'rad · −2π…2π', 'slm'],
  ['phase_std_rad', '相位標準差 σ', 'rad · 0…π；不是 variance', 'slm'],
  ['seed', '實現種子 · Seed', 'PCG64 · integer 0…2³²−1', 'slm'],
  ['qwp_angle_rad', 'QWP 光軸角度', 'rad · −2π…2π', 'qwp'],
  ['hwp_angle_rad', 'HWP 光軸角度', 'rad · −2π…2π', 'hwp'],
] as const;
const tabs = [['summary', '摘要'], ['phase', '相位遮罩'], ['measurements', '量測'], ['evidence', '依據']] as const;
type Tab = typeof tabs[number][0];
export interface R03WorkspaceOptions {
  admit(extraPersistent: number, extraTransient: number): void;
  reserveOperation(extraPersistent: number, extraTransient: number): void;
  chrome: { navigation: HTMLElement; releaseButton: HTMLButtonElement; releaseStatus: HTMLElement };
}
export class R03Workspace {
  readonly host: HTMLElement; readonly viewport: HTMLElement;
  private apparatus: R03Apparatus | null = null; private active = false; private resource: R03Display | null = null;
  private displays = new Set<R03Display>(); private unsubscribe: () => void; private selectedSample = 0;
  private disposed = false; private readonly inputs = new Map<string, HTMLInputElement>(); private unsubscribeGate: () => void;
  private editorText = new Map<string, string>(); private tab: Tab = 'summary'; private selectedStage: R03StageId | null = 'after_slm';
  private allParameters = false; private fullPrecision = false; private previousSelection = 'slm'; private hasFramed = false;
  private chromeAnchors: { node: HTMLElement; anchor: Comment }[] = []; private releaseText: string;
  constructor(host: HTMLElement, readonly controller: R03Controller, private scene: BenchScene | null, private options: R03WorkspaceOptions) {
    this.host = host; this.releaseText = options.chrome.releaseButton.textContent ?? '';
    for (const node of [options.chrome.navigation, options.chrome.releaseButton, options.chrome.releaseStatus]) {
      const anchor = document.createComment('research chrome return point'); node.before(anchor); this.chromeAnchors.push({ node, anchor });
    }
    host.innerHTML = `<header class="r03-toolbar" aria-label="理想統計偏振工作區控制">
      <div data-r03="navigation"></div><div class="r03-title"><strong>統計偏振實驗台</strong><span>A · 獨立理想模型</span></div>
      <div class="r03-actions"><output data-r03="status" data-testid="r03-status" aria-live="polite"></output>
        <button class="primary" data-r03="compute" data-testid="r03-compute">計算 · Compute</button>
        <button data-r03="retry" data-testid="r03-retry-display" hidden>恢復顯示</button><span data-r03="release"></span></div>
      <div class="r03-feedback" tabindex="0" aria-label="操作訊息"><p data-r03="error" data-testid="r03-error" role="alert" hidden></p>
        <p data-r03="display-error" data-testid="r03-display-error" role="alert" hidden></p><span data-r03="release-status"></span></div></header>
      <div class="r03-grid"><aside class="r03-inspector r03-card" aria-label="元件與屬性">
        <div class="r03-card-heading"><h2>元件</h2><button data-r03="all" data-testid="r03-all-parameters" aria-pressed="false">全部參數</button></div>
        <nav data-r03="components" aria-label="理想裝置元件"></nav>
        <section class="r03-context"><h3 data-r03="selected-label"></h3><p data-r03="selected-explanation"></p></section>
        <div data-r03="fields"></div><button data-r03="inspect-mask">檢視實際相位遮罩</button>
        <p class="r03-note">M=256 · 16×16 · pₘ=1/256。編輯只驗證；只有 Compute 產生一個 realization。</p></aside>
      <section class="r03-center" aria-label="裝置視窗"><div class="r03-camera" role="toolbar" aria-label="裝置視角">
        <button data-r03="overview" data-testid="r03-overview-view">實驗總覽</button><button data-r03="top" data-testid="r03-top-view">俯視</button>
        <button data-r03="focus" data-testid="r03-focus-selected">聚焦選取</button><button data-r03="reset" data-testid="r03-reset-view">重設</button></div>
        <div class="r03-viewport" data-r03="viewport" data-testid="r03-viewport"></div>
        <footer class="r03-viewport-caption"><strong>功能光路示意 · 非光線追跡</strong><span>拖曳旋轉 · 右鍵平移 · 滾輪縮放 · 點擊選取</span></footer></section>
      <aside class="r03-results r03-card" aria-label="統計結果與依據"><div class="r03-tabs" role="tablist" aria-label="結果檢視">
        ${tabs.map(([id, title]) => `<button id="r03-tab-${id}" data-testid="r03-tab-${id}" role="tab" aria-controls="r03-panel-${id}" data-tab="${id}">${title}</button>`).join('')}</div>
        <label class="r03-stage">觀察階段<select data-r03="stage" data-testid="r03-selected-stage" aria-label="觀察階段">
          <option value="">UNKNOWN · 無獨立階段</option>${Object.entries(stageNames).map(([id, name]) => `<option value="${id}">${name}</option>`).join('')}</select></label>
        <div data-r03="readout" class="r03-readout"></div></aside></div>`;
    this.viewport = this.node('viewport'); this.node('readout').append(this.readout(null));
    for (const id of R03_COMPONENTS) {
      const button = document.createElement('button'); button.textContent = R03_COMPONENT_LABELS[id]; button.dataset.component = id;
      button.dataset.testid = `r03-select-${id}`; button.addEventListener('click', () => controller.select(id)); this.node('components').append(button);
    }
    for (const [key, title, hint, component] of fields) {
      const label = document.createElement('label'); label.className = 'r03-number-field'; label.dataset.component = component;
      const text = document.createElement('span'); text.textContent = title; const input = document.createElement('input'); input.type = 'text'; input.inputMode = key === 'seed' ? 'numeric' : 'decimal';
      input.autocomplete = 'off'; input.dataset.testid = `r03-edit-${key}`; input.setAttribute('aria-label', title);
      const help = document.createElement('small'); help.textContent = hint; label.append(text, input, help); this.inputs.set(key, input); this.node('fields').append(label);
      input.addEventListener('input', () => { this.editorText.set(key, input.value); void controller.edit(key, input.value); });
    }
    this.node('compute').addEventListener('click', () => { void controller.simulate(); }); this.node('retry').addEventListener('click', () => controller.retryPresentation());
    this.node('all').addEventListener('click', () => { this.allParameters = true; this.render(controller.state); });
    this.node('inspect-mask').addEventListener('click', () => this.setTab('phase'));
    for (const button of this.host.querySelectorAll<HTMLButtonElement>('[data-tab]')) {
      button.addEventListener('click', () => this.setTab(button.dataset.tab as Tab));
      button.addEventListener('keydown', event => {
        if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return; event.preventDefault();
        const index = tabs.findIndex(([id]) => id === this.tab), next = event.key === 'Home' ? 0 : event.key === 'End' ? 3 : (index + (event.key === 'ArrowRight' ? 1 : 3)) % 4;
        this.setTab(tabs[next][0]); this.host.querySelector<HTMLButtonElement>(`[data-tab="${this.tab}"]`)!.focus();
      });
    }
    this.node<HTMLSelectElement>('stage').addEventListener('change', event => { this.selectedStage = (event.target as HTMLSelectElement).value as R03StageId || null; this.refreshNumbers(); });
    for (const [key, view] of [['overview', 'overview'], ['top', 'top'], ['focus', 'focus'], ['reset', 'overview']] as const) this.node(key).addEventListener('click', () => {
      if (this.apparatus) this.scene?.fitResearchApparatus(this.apparatus.framingBounds(view === 'focus' ? controller.state.selection : undefined), view);
    });
    controller.setOperationAdmission(() => this.options.reserveOperation(4096 + R03_RESULT_METADATA_RESERVATION + R03_PHASE_DISPLAY_BYTES, R03_TRANSPORT_RESERVATION + 4096 + R03_RESULT_METADATA_RESERVATION + 4096));
    controller.setResultPreparer(result => this.prepare(result)); this.unsubscribe = controller.subscribe(state => this.render(state));
    this.unsubscribeGate = controller.gate.subscribe(() => this.render(controller.state));
  }
  private node<T extends HTMLElement = HTMLElement>(key: string): T { const value = this.host.querySelector<T>(`[data-r03="${key}"]`); if (!value) throw new Error(`Missing ideal workspace ${key}`); return value; }
  private setTab(tab: Tab): void { this.tab = tab; this.showTab(); }
  private showTab(): void {
    for (const button of this.host.querySelectorAll<HTMLButtonElement>('[data-tab]')) { const selected = button.dataset.tab === this.tab; button.setAttribute('aria-selected', String(selected)); button.tabIndex = selected ? 0 : -1; }
    for (const panel of this.host.querySelectorAll<HTMLElement>('[data-panel]')) panel.hidden = panel.dataset.panel !== this.tab;
  }
  enter(): void {
    if (this.disposed) return; this.active = true; this.host.hidden = false;
    this.node('navigation').append(this.options.chrome.navigation); this.node('release').append(this.options.chrome.releaseButton);
    this.options.chrome.releaseButton.textContent = '釋放結果'; this.options.chrome.releaseButton.title = this.releaseText;
    this.node('release-status').append(this.options.chrome.releaseStatus);
    try {
      if (!this.scene) throw new Error('既有 WebGL2 renderer 不可用；未產生替代裝置。');
      if (!this.apparatus) { this.options.admit(R03_APPARATUS_CAP, R03_APPARATUS_CAP); this.apparatus = createR03Apparatus(); }
      this.scene.showResearchApparatus(this.viewport, this.apparatus.group);
      this.scene.setResearchLabelUpdater((camera, width, height) => this.apparatus?.updateLabels(camera, width, height));
      if (!this.hasFramed) { this.scene.fitResearchApparatus(this.apparatus.framingBounds(), 'overview'); this.hasFramed = true; }
      this.render(this.controller.state);
    } catch (error) { this.controller.reportRenderFailure(String(error)); this.viewport.textContent = '3D 裝置不可用；請查看顯示錯誤。沒有替代光學結果。'; }
    void this.controller.activate();
  }
  leave(): void {
    this.active = false; this.controller.deactivate(); this.apparatus?.setPhase(null); this.scene?.setResearchLabelUpdater(null); this.scene?.hideResearchApparatus(); this.host.hidden = true;
    for (const { node, anchor } of this.chromeAnchors) anchor.after(node); this.options.chrome.releaseButton.textContent = this.releaseText;
  }
  private prepare(result: R03Result): R03Prepared {
    if (!this.active || !this.apparatus || !this.scene) throw new Error('理想裝置未掛載；數值結果保留，尚未顯示。');
    this.scene.assertResearchReady(); const before = this.ownedNumericalBytes(), after = r03OwnedResults([...this.numericalOwners(), result]);
    this.options.admit(after - before + R03_PHASE_DISPLAY_BYTES, after - before + R03_PHASE_DISPLAY_BYTES + 1024);
    const next = prepareR03Display(result); this.displays.add(next); let content: HTMLElement;
    try { content = this.readout(result, next.canvas); } catch (error) { next.dispose(); this.displays.delete(next); throw error; }
    const previous = this.resource, oldReadout = [...this.node('readout').childNodes], oldId = this.node('readout').dataset.requestId; let committed = false, closed = false;
    return {
      commit: () => {
        if (closed || !this.active || this.resource !== previous) throw new Error('Ideal display transaction changed'); this.scene!.assertResearchReady();
        committed = true; this.resource = next; this.node('readout').replaceChildren(content); this.node('readout').dataset.requestId = result.requestId; this.showTab(); this.apparatus!.setPhase(next.texture);
        this.selectedSample = 0; next.canvas.addEventListener('click', this.pickPhase);
      },
      dispose: () => { if (closed) return; closed = true; if (committed && this.resource === next) { this.resource = previous;
          this.node('readout').replaceChildren(...oldReadout); if (oldId) this.node('readout').dataset.requestId = oldId; else delete this.node('readout').dataset.requestId;
          this.apparatus?.setPhase(previous?.texture ?? null); this.showTab(); }
        next.canvas.removeEventListener('click', this.pickPhase); next.dispose(); this.displays.delete(next); },
      finalize: () => { if (closed) return; closed = true; if (previous) { previous.canvas.removeEventListener('click', this.pickPhase); previous.dispose(); this.displays.delete(previous); } },
    };
  }
  private pickPhase = (event: MouseEvent): void => {
    if (!this.resource || this.controller.state.currentResult !== this.resource.result) return;
    const rect = this.resource.canvas.getBoundingClientRect(); const column = Math.max(0, Math.min(15, Math.floor((event.clientX - rect.left) / rect.width * 16)));
    const row = Math.max(0, Math.min(15, Math.floor((event.clientY - rect.top) / rect.height * 16))); this.selectedSample = row * 16 + column; this.updateSample(this.resource.result);
  };
  private modelEvidence(host: HTMLElement): void {
    const title = document.createElement('h2'); title.textContent = R03_IDENTITY; host.append(title);
    const p = document.createElement('p'); p.className = 'r03-note'; p.textContent = `${R03_MODEL}\nC=ΣpₘEₘEₘ† · pₘ=1/256 · exp(−iωt) · (+x,+y) · S₃=−2 Im Cxy。Gaussian unwrapped φ=μ+σz → φ mod 2π；Local PCG64，沒有 browser RNG、centering、variance correction、clipping 或 quantization。Random phases 本身不建立 incoherent collection；此處明定 ideal statistical measurement。`; host.append(p);
    const limits = document.createElement('p'); limits.className = 'r03-note'; limits.textContent = '支架、距離、路由與方向箭頭僅為功能示意；無 computed rays、propagated field sections 或收集孔徑。光軸標記使用代數 (+x,+y) → 裝置示意 (+z,−y)，不代表反射座標轉換。B / Figure 2a 實驗比較仍另行門控；不是 PAX 校準讀值，不宣稱實驗重現。'; host.append(limits);
  }
  private readout(result: R03Result | null, canvas?: HTMLCanvasElement): HTMLElement {
    const host = document.createElement('div'); host.className = 'r03-panels';
    for (const [id, title] of tabs) {
      const panel = document.createElement('section'); panel.id = `r03-panel-${id}`; panel.dataset.panel = id; panel.setAttribute('role', 'tabpanel'); panel.setAttribute('aria-labelledby', `r03-tab-${id}`); panel.tabIndex = 0;
      const heading = document.createElement('h3'); heading.textContent = title; panel.append(heading);
      if (id === 'summary') { const summary = document.createElement('div'); summary.dataset.r03 = 'summary'; panel.append(summary); }
      if (id === 'phase' && result && canvas) {
        const phaseHost = document.createElement('div'); phaseHost.className = 'r03-phase-host'; phaseHost.append(canvas); panel.append(phaseHost);
        const bar = document.createElement('div'); bar.className = 'r03-colorbar'; bar.style.background = R03_PHASE_GRADIENT; panel.append(bar);
        const scale = document.createElement('div'); scale.className = 'r03-phase-scale'; scale.innerHTML = '<span>0</span><span>π</span><span>2π rad</span>'; panel.append(scale);
        const hint = document.createElement('p'); hint.className = 'r03-note'; hint.textContent = '實際提交的 16×16 遮罩 · row 0 在上，column 0 在左 · C-order。點擊選取原始相位。'; panel.append(hint);
        const sample = document.createElement('output'); sample.className = 'r03-sample'; sample.dataset.r03 = 'sample'; sample.dataset.testid = 'r03-sample'; panel.append(sample);
      }
      if (id === 'measurements') {
        const label = document.createElement('label'); label.className = 'r03-precision'; const input = document.createElement('input'); input.type = 'checkbox'; input.checked = this.fullPrecision; input.dataset.testid = 'r03-full-precision';
        input.addEventListener('change', () => { this.fullPrecision = input.checked; this.refreshNumbers(); }); label.append(input, '完整精度 · 17 位有效數字'); panel.append(label);
        const measurements = document.createElement('div'); measurements.dataset.r03 = 'measurements'; panel.append(measurements);
      }
      if (id === 'evidence') {
        this.modelEvidence(panel); const identity = document.createElement('p'); identity.className = 'r03-identity'; identity.dataset.testid = 'r03-result-identity'; identity.dataset.r03 = 'identity'; panel.append(identity);
        if (result) {
          identity.textContent = `SUBMITTED RESULT\n${result.requestId}\nseed ${result.experiment.seed}\nSHA-256 ${result.experimentSha256}`;
          const population = document.createElement('p'); population.className = 'r03-population'; population.textContent = `Infinite Gaussian ensemble expectation · ${formatR03Readout(result.population.infinite_gaussian_degree_of_polarization, true)}\n${result.population.assumption}\n獨立標示的無限母體預測，不取代實際 finite realization，不是實驗誤差或 accuracy percent。`; panel.append(population);
          const details = document.createElement('details'); details.open = true; const summary = document.createElement('summary'); summary.textContent = '完整設定、讀值與 provenance（可選取複製）';
          const pre = document.createElement('pre'); pre.textContent = JSON.stringify(r03ResultSnapshot(result), null, 2); details.append(summary, pre); panel.append(details);
        }
      }
      if (!result && id !== 'evidence') { const empty = document.createElement('p'); empty.className = 'r03-empty'; empty.textContent = '尚無目前結果。設定後按 Compute；不使用預覽 RNG 或替代遮罩。'; panel.append(empty); }
      host.append(panel);
    }
    if (result) this.fillNumbers(host, result); return host;
  }
  private fillNumbers(host: HTMLElement, result: R03Result): void {
    const summary = host.querySelector<HTMLElement>('[data-r03="summary"]')!, stage = result.stages.find(value => value.id === this.selectedStage); summary.replaceChildren();
    if (stage) {
      const title = document.createElement('p'); title.className = 'r03-note'; title.textContent = stageNames[stage.id]; summary.append(title);
      const headline = document.createElement('div'); headline.className = 'r03-dop'; headline.innerHTML = '<span>Finite ensemble DoP</span><strong data-testid="r03-dop"></strong>';
      headline.querySelector('strong')!.textContent = formatR03Readout(stage.degree_of_polarization, stage.roundoff_limited); summary.append(headline);
      const intensity = document.createElement('p'); intensity.className = 'r03-intensity'; intensity.dataset.testid = 'r03-intensity'; intensity.textContent = `S₀ = ${formatR03Readout(stage.stokes[0])} amplitude-unit²\nprobability mean`; summary.append(intensity);
      const note = document.createElement('p'); note.className = 'r03-note'; note.textContent = stage.stokes[0] === 0 ? 'Dark source：DoP、normalized Stokes、direction 為 undefined (null)，不以 0 或 epsilon 代替。' : stage.roundoff_limited ? 'Roundoff limited · 顯示原始值，未 clamp。請於量測檢視完整精度。' : '同一次有限樣本計算 · 可在量測檢視 C、Stokes 與 eigenvalues。'; summary.append(note);
    } else { const p = document.createElement('p'); p.className = 'r03-note'; p.textContent = 'UNKNOWN 路由沒有獨立計算階段。請選取已記錄的觀察階段；不推造中間讀值。'; summary.append(p); }
    const measurements = host.querySelector<HTMLElement>('[data-r03="measurements"]')!; measurements.replaceChildren(); const format = (value: number | null) => formatR03Readout(value, this.fullPrecision);
    const table = document.createElement('table'); table.createCaption().textContent = '同一有限樣本 · 四階段比較';
    const header = table.createTHead().insertRow(); for (const text of ['階段', 'S₀', 'DoP']) { const th = document.createElement('th'); th.textContent = text; header.append(th); }
    for (const item of result.stages) { const row = table.insertRow(); row.insertCell().textContent = stageNames[item.id].split(' · ')[0]; row.insertCell().textContent = format(item.stokes[0]); row.insertCell().textContent = format(item.degree_of_polarization); }
    const tableScroll = document.createElement('div'); tableScroll.className = 'r03-measurement-table'; tableScroll.tabIndex = 0;
    tableScroll.setAttribute('role', 'region'); tableScroll.setAttribute('aria-label', '四階段數值比較，可水平捲動'); tableScroll.append(table); measurements.append(tableScroll);
    for (const item of result.stages) {
      const details = document.createElement('details'); details.open = item.id === this.selectedStage; const title = document.createElement('summary'); title.textContent = stageNames[item.id]; details.append(title);
      const pre = document.createElement('pre'); pre.textContent = 'C / amplitude-unit²\n' + item.coherency.map(row => row.map(c => `${format(c.re)} ${c.im < 0 ? '−' : '+'} ${format(Math.abs(c.im))}i`).join('   ')).join('\n') +
        `\nStokes [S₀,S₁,S₂,S₃]\n${item.stokes.map(format).join(', ')}\nDoP = ${format(item.degree_of_polarization)}\nS/S₀ = ${item.normalized_stokes?.map(format).join(', ') ?? 'undefined (null)'}\nS/|S| direction = ${item.polarized_direction?.map(format).join(', ') ?? 'undefined (null)'}\nEigenvalues = ${item.eigenvalues.map(format).join(', ')}\nRoundoff limited = ${item.roundoff_limited}`; details.append(pre); measurements.append(details);
    }
  }
  private refreshNumbers(): void { const result = this.controller.state.currentResult; if (result && result === this.resource?.result) this.fillNumbers(this.node('readout'), result); }
  private updateSample(result: R03Result): void { const i = this.selectedSample; this.node('sample').textContent = `row=${Math.floor(i / 16)}, col=${i % 16}, index=${i}\nwrapped=${result.phase.wrapped[i].toPrecision(17)} rad\nunwrapped=${result.phase.unwrapped[i].toPrecision(17)} rad`; }
  private render(state: R03State): void {
    if (state.selection !== this.previousSelection) { this.previousSelection = state.selection; this.allParameters = false; this.selectedStage = componentStage[state.selection]; if (state.selection === 'measurement') this.tab = 'measurements'; this.refreshNumbers(); }
    for (const [key, input] of this.inputs) {
      if (!this.editorText.has(key)) this.editorText.set(key, state.invalidEdits[key] ?? String(state.candidate[key as keyof typeof state.candidate]));
      if (document.activeElement !== input) input.value = state.invalidEdits[key] ?? this.editorText.get(key)!;
      input.classList.toggle('invalid', Object.hasOwn(state.invalidEdits, key)); input.setAttribute('aria-invalid', String(Object.hasOwn(state.invalidEdits, key)));
      input.closest<HTMLElement>('label')!.hidden = !this.allParameters && input.closest('label')!.getAttribute('data-component') !== state.selection;
    }
    this.node('all').setAttribute('aria-pressed', String(this.allParameters)); this.node('selected-label').textContent = this.allParameters ? '全部參數 · 同一份草稿' : R03_COMPONENT_LABELS[state.selection];
    this.node('selected-explanation').textContent = explanations[state.selection]; this.node('inspect-mask').hidden = state.selection !== 'slm' && !this.allParameters;
    this.host.querySelectorAll<HTMLButtonElement>('button[data-component]').forEach(button => { const selected = button.dataset.component === state.selection; button.classList.toggle('selected', selected); button.setAttribute('aria-pressed', String(selected)); });
    this.node<HTMLSelectElement>('stage').value = this.selectedStage ?? ''; this.apparatus?.select(state.selection);
    if (state.validatedDraft) this.apparatus?.setAngles(state.validatedDraft.qwp_angle_rad, state.validatedDraft.hwp_angle_rad);
    const ready = !!state.validatedDraft && !state.pendingValidation && !Object.keys(state.invalidEdits).length; this.node<HTMLButtonElement>('compute').disabled = !ready || this.controller.gate.busy;
    const showing = !!state.currentResult && this.resource?.result === state.currentResult;
    if (!showing && this.node('readout').dataset.requestId) { this.node('readout').replaceChildren(this.readout(null)); delete this.node('readout').dataset.requestId; }
    if (showing) { this.node('readout').dataset.requestId = state.currentResult!.requestId; this.updateSample(state.currentResult!); if (this.active) this.apparatus?.setPhase(this.resource!.texture); } else this.apparatus?.setPhase(null);
    const status = state.active ? 'COMPUTING · 計算中' : state.pendingValidation ? 'VALIDATING · 驗證中' : state.error ? 'INVALID / FAILED · 請檢查輸入'
      : state.renderError ? 'DISPLAY FAILURE · 數值保留' : showing ? 'SUCCESS · 同一次實現' : state.lastResult || state.completedNumerical ? 'STALE / DETACHED · 需重新提交' : ready ? 'READY · 尚未計算' : '尚未驗證';
    this.node('status').textContent = status; this.node('status').dataset.state = state.active ? 'computing' : showing ? 'success' : state.error ? 'error' : state.lastResult ? 'stale' : 'ready';
    this.node('error').hidden = !state.error; this.node('error').textContent = state.error;
    this.node('display-error').hidden = !state.renderError; this.node('display-error').textContent = state.renderError ? `DISPLAY FAILURE · ${state.renderError} · 數值保留，不重送計算。` : '';
    this.node('retry').hidden = !state.renderError || !this.controller.canRetryPresentation; this.node<HTMLButtonElement>('retry').disabled = !ready || !this.controller.canRetryPresentation; this.showTab();
  }
  numericalOwners(): (R03Result | null)[] { return [this.controller.state.lastResult, this.controller.state.completedNumerical, this.controller.state.currentResult, ...[...this.displays].map(display => display.result)]; }
  ownedNumericalBytes(): number { return r03OwnedResults(this.numericalOwners()); }
  ownedBytes(): number { return this.ownedNumericalBytes() + (this.apparatus?.ownedBytes ?? 0) + [...this.displays].reduce((n, display) => n + display.ownedBytes, 0); }
  releaseResults(): void { this.apparatus?.setPhase(null); for (const resource of this.displays) { resource.canvas.removeEventListener('click', this.pickPhase); resource.dispose(); }
    this.displays.clear(); this.resource = null; this.node('readout').replaceChildren(this.readout(null)); delete this.node('readout').dataset.requestId; this.controller.releaseResults(); }
  snapshot(): object { const s = this.controller.state; return { activeWorkspace: this.active, candidate: { ...s.candidate }, validatedDraft: s.validatedDraft ? { ...s.validatedDraft } : null,
    pendingValidation: s.pendingValidation, canRetryPresentation: this.controller.canRetryPresentation, invalidEdits: { ...s.invalidEdits }, revision: s.revision, attachmentEpoch: s.attachmentEpoch, selection: s.selection,
    tab: this.tab, selectedStage: this.selectedStage, allParameters: this.allParameters, fullPrecision: this.fullPrecision,
    error: s.error, renderError: s.renderError, active: s.active ? structuredClone(s.active) : null,
    currentResult: r03ResultSnapshot(s.currentResult), lastResult: r03ResultSnapshot(s.lastResult), completedNumerical: r03ResultSnapshot(s.completedNumerical),
    displayedRequestId: this.resource && s.currentResult === this.resource.result ? this.resource.result.requestId : null,
    selectedSample: this.selectedSample, phaseRGBA: this.resource && s.currentResult === this.resource.result ? Array.from(this.resource.rgba) : null,
    ownedBytes: this.ownedBytes(), numericalBytes: this.ownedNumericalBytes(), phaseDisplayBytes: [...this.displays].reduce((n, d) => n + d.ownedBytes, 0), apparatus: this.apparatus?.snapshot() ?? null }; }
  dispose(): void { if (this.disposed) return; this.leave(); this.disposed = true; this.unsubscribe(); this.unsubscribeGate(); this.releaseResults(); this.apparatus?.dispose(); this.apparatus = null; }
}
