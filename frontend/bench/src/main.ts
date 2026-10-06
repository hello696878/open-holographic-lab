import './styles.css';
import { BenchController, ClientOperationGate, type BenchState } from './state';
import { cloneExperiment, type Experiment, type DecodedResult } from './contracts';
import { PRESETS, presetExperiment } from './presets';
import { pixelCoordinates, pixelFromUV } from './mapping';
import { automaticColorLimits, automaticDualColorLimits, prepareDualCanvases, drawDetector, INITIAL_COLOR_LIMITS, validateColorLimits, type ColorLimits } from './detector';
import { BenchScene } from './scene';
import { TwoPathController, type TwoPathState } from './two_path_state';
import type { TwoPathExperiment, DecodedTwoPathResult, DecodedTwoPathSweep } from './two_path_contracts';
import { TWO_PATH_PRESETS, twoPathPreset } from './two_path_presets';
import { countedResultBytes, estimateDualOperationBytes, sweepPlotPoints, OWNED_PERSISTENT_BUDGET_BYTES, OWNED_TRANSIENT_BUDGET_BYTES } from './phase_sweep';

const app = document.querySelector<HTMLDivElement>('#app');
if (!app) throw new Error('缺少應用程式容器。');
app.innerHTML = `
  <header class="app-header"><div><span class="eyebrow">OPEN HOLOGRAPHIC LAB / V1 + V2b</span><h1>虛擬光學實驗台</h1></div>
    <div class="header-detail">單色 · 純量 · 同軸前向光路<br><span>本機運作／明確提交</span></div></header>
  <main>
    <section class="toolbar" aria-label="實驗控制">
      <label>模式 <select id="mode" data-testid="mode"><option value="sequential">順序光路（Sequential）</option><option value="two_path">兩路干涉（Two-path）</option></select></label>
      <label class="sequential-only">載入預設 <select id="preset" data-testid="preset"></select></label>
      <button id="simulate" class="primary sequential-only" data-testid="simulate">模擬（Simulate）</button>
      <output id="status" class="sequential-only" data-testid="status" aria-live="polite"></output>
      <button id="tp-simulate" class="primary two-path-only" data-testid="tp-simulate">模擬兩埠（Simulate）</button>
      <button id="tp-sweep" class="two-path-only" data-testid="tp-sweep">相位掃描（17 points）</button>
      <output id="tp-status" class="two-path-only" data-testid="tp-status" aria-live="polite"></output>
    </section>
    <p id="error" class="error" data-testid="error" role="alert" hidden></p>
    <p id="render-error" class="error" data-testid="render-error" role="alert" hidden></p>
    <section class="workspace">
      <aside class="panel components"><h2>光路列表</h2><p class="muted">依列出的順序作用；同位置 ID 保留。</p>
        <div id="components" data-testid="components"></div>
        <div class="add-controls"><select id="add-kind" data-testid="add-kind" aria-label="新增元件種類">
          <option value="thin_lens">薄透鏡（Thin lens）</option><option value="circular_aperture">圓形孔徑</option><option value="rectangular_aperture">矩形孔徑</option></select>
          <button id="add" data-testid="add">新增元件</button><button id="delete" data-testid="delete">刪除選取元件</button></div>
        <details class="sampling" open><summary>取樣與波長</summary><div id="general-fields"></div></details>
      </aside>
      <aside class="panel two-path-controls two-path-only"><h2>兩路實驗參數</h2>
        <label>預設 <select id="tp-preset" data-testid="tp-preset"></select></label>
        <label>光源 <select id="tp-source-kind" data-testid="tp-source-kind"><option value="uniform">均勻（Uniform）</option><option value="gaussian">Gaussian</option></select></label>
        <div id="tp-fields" class="tp-fields"></div>
        <div class="phase-buttons"><button id="tp-phase-0" data-testid="tp-phase-0">0 rad</button><button id="tp-phase-halfpi" data-testid="tp-phase-halfpi">π/2 rad</button><button id="tp-phase-pi" data-testid="tp-phase-pi">π rad</button></div>
        <p id="tp-phase-note" class="muted"></p><p class="muted">編輯只驗證；模擬與掃描分開提交。瀏覽器 -0 相位採用 +0。非零相位不繞回。</p>
      </aside>
      <section class="bench-panel"><div class="bench-heading"><h2>3D 光學實驗台</h2><span id="bench-label">等待草稿驗證</span></div>
        <div id="bench" data-testid="bench-host"></div>
        <div class="camera-controls" aria-label="視角控制"><button id="reset-view" data-testid="reset-view">重設視角</button>
          <button id="zoom-in" data-testid="zoom-in" aria-label="放大視角">＋</button><button id="zoom-out" data-testid="zoom-out" aria-label="縮小視角">−</button>
          <button data-pan="-1,0" data-testid="pan-left" aria-label="向左平移視角">←</button><button data-pan="1,0" aria-label="向右平移視角">→</button>
          <button data-pan="0,1" aria-label="向上平移視角">↑</button><button data-pan="0,-1" aria-label="向下平移視角">↓</button></div>
        <p class="bench-help">左鍵旋轉（Orbit）・右鍵平移（Pan）・滾輪縮放（Zoom）・點擊選取<br>
          橘色控制球：僅沿 z 軸拖曳；放開後驗證，無效位置拒絕。虛線是軸線指引。</p>
        <output id="notice" data-testid="notice" aria-live="polite"></output>
        <div id="pick-choices" aria-label="重疊元件選擇"></div>
        <p class="scale-note">示意縮放：橫向 1 單位 = 1 mm；縱向 1 單位 = 10 mm。透鏡外形不代表物理孔徑。</p>
      </section>
      <aside class="panel inspector"><h2>元件屬性</h2><div id="inspector" data-testid="inspector"></div>
        <p class="muted">編輯只驗證草稿。請按「模擬」產生新結果；視角與色階不改變實驗。</p></aside>
      <aside class="panel two-path-note two-path-only"><h2>理想展開示意</h2><div id="tp-topology"></div>
        <p class="muted">虛線為指引，不是計算的體積光束。畫面路長與間距僅供辨識；只有數值 L₀/L₁ 參與傳播。</p>
        <p class="muted">輸出面位於 B† 之後立即量測；視覺分開不新增傳播。共同橫向座標，不加入鏡面反射翻轉。</p>
        <p class="muted">extra phase 為獨立 arm 1 相位；傳播本身包含載波與繞射。未加入第二載波或鏡位移規則。</p></aside>
    </section>
    <section class="result-panel panel sequential-only"><div class="result-heading"><h2>觀察結果</h2><strong id="result-status" data-testid="result-status">尚未提交模擬</strong></div>
      <div class="results"><div><div class="color-controls"><label>顯示下限 <input id="color-min" data-testid="color-min" type="text" inputmode="decimal" value="0"></label>
          <label>顯示上限 <input id="color-max" data-testid="color-max" type="text" inputmode="decimal" value="10"></label>
          <button id="auto-color" data-testid="auto-color">自動色階（不重算）</button></div>
        <p id="color-info" data-testid="color-info">共用色階 0–10 amplitude-unit²</p><p id="color-error" class="error" hidden></p>
        <div id="intensity-holder" class="intensity-holder" hidden><canvas id="intensity" data-testid="intensity-canvas" aria-label="原始強度的灰階顯示"></canvas></div>
        <p id="pixel-readout" data-testid="pixel-readout">點擊強度圖或 3D 觀察面讀取原始 float64 像素。</p>
      </div><div class="result-details"><p id="result-identity" data-testid="result-identity" class="monospace">—</p>
        <p id="result-spec" data-testid="result-spec">—</p><p id="raw-max" data-testid="raw-max">—</p>
        <p id="saturation" data-testid="saturation" class="warning" hidden></p>
        <label>階段 <select id="stage" data-testid="stage"></select></label>
        <p id="stage-note" data-testid="stage-note">階段表將在完成模擬後顯示。</p>
        <div class="table-scroll"><table><thead><tr><th>階段</th><th>z / mm</th><th>norm</th><th>Δnorm</th><th>比例</th></tr></thead><tbody id="stages" data-testid="stages"></tbody></table></div>
        <p class="muted">norm：amplitude-unit²·m²；零入射時未定義比例顯示 null。</p></div></div>
    </section>
    <section id="tp-result-area" class="result-panel panel two-path-only">
      <div class="result-heading"><h2>兩埠立即輸出</h2><strong id="tp-result-status" data-testid="tp-result-status">尚未提交模擬</strong></div>
      <p id="tp-error" data-testid="tp-error" class="error" hidden></p><p id="tp-render-error" data-testid="tp-render-error" class="error" hidden></p>
      <div class="color-controls"><label>共用下限 <input id="tp-color-min" data-testid="tp-color-min" value="0"></label><label>共用上限 <input id="tp-color-max" data-testid="tp-color-max" value="1"></label>
        <button id="tp-auto-color" data-testid="tp-auto-color">共同自動色階（不重算）</button></div>
      <p id="tp-color-info" class="muted"></p><p id="tp-color-error" class="error" hidden></p>
      <div id="tp-current-content"></div>
      <details id="tp-previous-result" data-testid="tp-previous-result" hidden><summary>上次完成結果 · 與目前草稿分開</summary><pre id="tp-previous-spec"></pre><div id="tp-prior-images" class="dual-images"></div></details>
      <p class="muted">兩埠共用橫向座標；norm 單位 amplitude-unit²·m²，非瓦特。極暗殘值與有號差異保留；零輸入比例 null。</p>
    </section>
    <section class="panel result-panel two-path-only"><div class="result-heading"><h2>實際相位掃描</h2><strong id="tp-sweep-status" data-testid="tp-sweep-status">尚未提交掃描</strong></div>
      <p class="muted">17 次真正計算；0 與 2π 分別呼叫。點擊標記只讀取該列，不模擬。連線僅視覺插值。</p>
      <div class="color-controls"><label>圖表共用下限 <input id="tp-chart-min" value="0"></label><label>圖表共用上限 <input id="tp-chart-max" value="1"></label><button id="tp-chart-range">套用圖表範圍（不重算）</button></div>
      <svg id="tp-sweep-chart" data-testid="tp-sweep-chart" viewBox="0 0 760 230" role="img" aria-label="實際計算的兩埠輸入比例"></svg>
      <p id="tp-sweep-identity" class="monospace"></p><p id="tp-sweep-selected" class="monospace"></p>
      <button id="tp-simulate-phase" data-testid="tp-simulate-phase" disabled>明確模擬選取相位（使用該掃描的原始來源與路長）</button>
      <div class="table-scroll"><table><thead><tr><th>phase / rad</th><th>input norm</th><th>port 0 norm</th><th>port 1 norm</th><th>η0</th><th>η1</th><th>total ratio</th><th>total Δ</th></tr></thead><tbody id="tp-sweep-rows" data-testid="tp-sweep-rows"></tbody></table></div>
    </section>
    <footer class="model-note"><strong>模型限制</strong>　週期性取樣視窗；Gaussian 與理想薄透鏡為近軸描述；硬孔徑使用離散中心取樣。
      不提供取樣精度保證、光線追跡、體積光束、校準瓦特或硬體控制。強度為任意 amplitude-unit²。</footer>
  </main>`;

function element<T extends HTMLElement>(id: string): T {
  const found = document.getElementById(id);
  if (!found) throw new Error(`缺少 ${id}`);
  return found as T;
}
const operationGate = new ClientOperationGate();
const controller = new BenchController(presetExperiment(PRESETS[0].id), undefined, undefined, operationGate);
const twoPathController = new TwoPathController(twoPathPreset(TWO_PATH_PRESETS[0].id), undefined, undefined, operationGate);
let mode: 'sequential' | 'two_path' = 'sequential';
app.dataset.mode = mode;
let scene: BenchScene | null = null;
let limits: ColorLimits = { ...INITIAL_COLOR_LIMITS };
let displayedResult: DecodedResult | null = null;
let displayKey = '';
let inspectorKey = '';
let selectedPixel: { row: number; column: number; x_m: number; y_m: number; intensity: number; requestId: string } | null = null;
let nextId = 1;
let disposed = false;
let dualLimits: ColorLimits = { min: 0, max: 1 };
let dualPublished: DecodedTwoPathResult | null = null;
let dualDisplayKey = '';
let dualFieldsKey = '';
let priorDisplayKey = '';
let dualSelectedPixel: { port: 0 | 1; row: number; column: number; x_m: number; y_m: number; intensity: number; requestId: string } | null = null;
let chartRange: ColorLimits = { min: 0, max: 1 };

function notice(text: string): void { element('notice').textContent = text; }

function reportPresentation(error: unknown): void {
  const message = error instanceof Error ? error.message : String(error);
  if (mode === 'two_path') {
    if (twoPathController.state.renderError !== message) twoPathController.reportRenderFailure(message);
  } else if (controller.state.renderError !== message) controller.reportRenderFailure(message);
}

try {
  scene = new BenchScene(element('bench'), {
    select(ids) {
      if (mode === 'two_path') { twoPathController.select(ids[0]); return; }
      controller.select(ids[0]);
      const choices = element('pick-choices');
      choices.replaceChildren();
      if (ids.length > 1) {
        choices.append(document.createTextNode('此視線有多個元件：'));
        for (const id of ids) {
          const button = document.createElement('button');
          button.textContent = id;
          button.addEventListener('click', () => controller.select(id));
          choices.append(button);
        }
      }
    },
    pixel: (row, column) => showPixel(controller.state.currentResult, row, column),
    dualPixel: (port, row, column) => showDualPixel(twoPathController.state.currentResult, port, row, column),
    commitZ(id, z_m) {
      const spec = cloneExperiment(controller.state.candidate);
      const component = spec.components.find((item) => item.id === id);
      if (component) component.z_m = z_m;
      else if (spec.observation.id === id) spec.observation.z_m = z_m;
      controller.replaceCandidate(spec);
    },
    notice,
    presentationFailure(message) {
      if (mode === 'two_path') twoPathController.reportRenderFailure(message);
      else controller.reportRenderFailure(message);
    },
  });
} catch (error) {
  element('bench').classList.add('unavailable');
  element('bench').textContent = 'WebGL2 3D 顯示不可用；請確認瀏覽器設定。沒有產生替代光束或假結果。';
  reportPresentation(error);
}

const preset = element<HTMLSelectElement>('preset');
for (const item of PRESETS) {
  const option = document.createElement('option');
  option.value = item.id;
  option.textContent = item.label;
  preset.append(option);
}
preset.addEventListener('change', () => {
  controller.select('source');
  controller.replaceCandidate(presetExperiment(preset.value));
  notice('已載入預設並驗證；請明確按下模擬。');
});
element('simulate').addEventListener('click', () => { void controller.simulate(); });
element('reset-view').addEventListener('click', () => scene?.resetCamera());
element('zoom-in').addEventListener('click', () => scene?.zoom(0.8));
element('zoom-out').addEventListener('click', () => scene?.zoom(1.25));
for (const button of document.querySelectorAll<HTMLButtonElement>('[data-pan]')) {
  button.addEventListener('click', () => {
    const [horizontal, vertical] = (button.dataset.pan ?? '0,0').split(',').map(Number);
    scene?.pan(horizontal, vertical);
  });
}

function readPath(spec: Experiment, path: string): number {
  let current: unknown = spec;
  for (const part of path.split('.')) current = (current as Record<string, unknown>)[part];
  return current as number;
}

function numberField(parent: HTMLElement, path: string, label: string, scale = 1, integer = false): void {
  const wrapper = document.createElement('label');
  wrapper.className = 'number-field';
  wrapper.append(document.createTextNode(label));
  const input = document.createElement('input');
  input.type = 'text';
  input.inputMode = integer ? 'numeric' : 'decimal';
  input.dataset.path = path;
  input.dataset.scale = String(scale);
  input.dataset.testid = `edit-${path.replaceAll('.', '-')}`;
  input.addEventListener('input', () => controller.edit(path, input.value, scale, integer));
  wrapper.append(input);
  parent.append(wrapper);
}

const general = element('general-fields');
numberField(general, 'wavelength_m', 'λ 波長 / nm', 1e-9);
numberField(general, 'grid.nx', 'Nx 橫向樣本 / 1', 1, true);
numberField(general, 'grid.ny', 'Ny 縱向樣本 / 1', 1, true);
numberField(general, 'grid.dx', 'dx 像素間距 / µm', 1e-6);
numberField(general, 'grid.dy', 'dy 像素間距 / µm', 1e-6);

function renderInspector(state: BenchState): void {
  const spec = state.candidate;
  const index = spec.components.findIndex((item) => item.id === state.selection);
  const key = `${state.selection}:${state.selection === 'source' ? spec.source.kind : index}:${spec.components[index]?.kind}`;
  const parent = element('inspector');
  if (key !== inspectorKey) {
    inspectorKey = key;
    parent.replaceChildren();
    const heading = document.createElement('h3');
    heading.textContent = state.selection;
    parent.append(heading);
    if (state.selection === 'source') {
      const label = document.createElement('label');
      label.textContent = '光源（Source）';
      const kind = document.createElement('select');
      kind.dataset.testid = 'source-kind';
      for (const [value, text] of [['gaussian', 'Gaussian'], ['uniform', '均勻（Uniform）']]) {
        const option = document.createElement('option'); option.value = value; option.textContent = text; kind.append(option);
      }
      kind.value = spec.source.kind;
      kind.addEventListener('change', () => {
        const edited = cloneExperiment(controller.state.candidate);
        const { amplitude, phase_rad } = edited.source;
        edited.source = kind.value === 'uniform' ? { kind: 'uniform', amplitude, phase_rad }
          : { kind: 'gaussian', amplitude, phase_rad, waist_radius_m: 100e-6, waist_z_m: 0, center_x_m: 0, center_y_m: 0 };
        controller.replaceCandidate(edited);
      });
      label.append(kind); parent.append(label);
      numberField(parent, 'source.amplitude', '振幅 / amplitude-unit');
      numberField(parent, 'source.phase_rad', '相位 / rad');
      if (spec.source.kind === 'gaussian') {
        numberField(parent, 'source.waist_radius_m', '腰半徑 w₀ / µm', 1e-6);
        numberField(parent, 'source.waist_z_m', '腰位置 z₀ / mm', 1e-3);
        numberField(parent, 'source.center_x_m', 'Gaussian 中心 x / µm', 1e-6);
        numberField(parent, 'source.center_y_m', 'Gaussian 中心 y / µm', 1e-6);
      }
    } else if (index >= 0) {
      const component = spec.components[index];
      numberField(parent, `components.${index}.z_m`, '位置 z / mm', 1e-3);
      if (component.kind === 'thin_lens') numberField(parent, `components.${index}.focal_length_m`, '焦距 f（可正負）/ mm', 1e-3);
      if (component.kind === 'circular_aperture') numberField(parent, `components.${index}.radius_m`, '半徑 / µm', 1e-6);
      if (component.kind === 'rectangular_aperture') {
        numberField(parent, `components.${index}.width_m`, '完整寬度 / µm', 1e-6);
        numberField(parent, `components.${index}.height_m`, '完整高度 / µm', 1e-6);
      }
      const note = document.createElement('p');
      note.className = 'muted';
      note.textContent = '固定同軸；沒有旋轉或 x/y 平移。z 可共位，但不可重排。';
      parent.append(note);
    } else if (state.selection === spec.observation.id) {
      numberField(parent, 'observation.z_m', '觀察位置 z / mm', 1e-3);
    }
  }
  for (const input of document.querySelectorAll<HTMLInputElement>('input[data-path]')) {
    const path = input.dataset.path ?? '';
    const invalid = Object.hasOwn(state.invalidEdits, path);
    input.classList.toggle('invalid', invalid);
    input.setAttribute('aria-invalid', String(invalid));
    if (document.activeElement !== input) {
      input.value = invalid ? state.invalidEdits[path]
        : String(Number((readPath(spec, path) / Number(input.dataset.scale)).toPrecision(14)));
    }
  }
}

function renderComponents(state: BenchState): void {
  const list = element('components');
  list.replaceChildren();
  const records = [
    { id: 'source', name: `光源 · ${state.candidate.source.kind}`, z_m: 0 },
    ...state.candidate.components.map((item, index) => ({ id: item.id, name: `${index + 1}. ${item.kind === 'thin_lens' ? '薄透鏡' : item.kind === 'circular_aperture' ? '圓形孔徑' : '矩形孔徑'}`, z_m: item.z_m })),
    { id: state.candidate.observation.id, name: '觀察面', z_m: state.candidate.observation.z_m },
  ];
  for (const record of records) {
    const button = document.createElement('button');
    button.className = `component${record.id === state.selection ? ' selected' : ''}`;
    button.dataset.testid = `select-${record.id}`;
    button.dataset.selected = String(record.id === state.selection);
    const title = document.createElement('strong'); title.textContent = record.name;
    const subtitle = document.createElement('span'); subtitle.textContent = `${record.id} · ${(record.z_m * 1000).toPrecision(5)} mm`;
    button.append(title, subtitle);
    button.addEventListener('click', () => controller.select(record.id));
    list.append(button);
  }
  element<HTMLButtonElement>('add').disabled = state.candidate.components.length >= 8;
  element<HTMLButtonElement>('delete').disabled = !state.candidate.components.some((item) => item.id === state.selection);
}

element('add').addEventListener('click', () => {
  const spec = cloneExperiment(controller.state.candidate);
  if (spec.components.length >= 8) return;
  const kind = element<HTMLSelectElement>('add-kind').value;
  let id: string;
  do { id = `element${nextId++}`; } while (spec.components.some((item) => item.id === id) || spec.observation.id === id);
  const z_m = spec.components.at(-1)?.z_m ?? 0;
  if (kind === 'thin_lens') spec.components.push({ kind: 'thin_lens', id, z_m, focal_length_m: 20e-3 });
  else if (kind === 'circular_aperture') spec.components.push({ kind: 'circular_aperture', id, z_m, radius_m: 80e-6 });
  else spec.components.push({ kind: 'rectangular_aperture', id, z_m, width_m: 160e-6, height_m: 100e-6 });
  controller.replaceCandidate(spec);
  controller.select(id);
});
element('delete').addEventListener('click', () => {
  const spec = cloneExperiment(controller.state.candidate);
  const index = spec.components.findIndex((item) => item.id === controller.state.selection);
  if (index < 0) return;
  spec.components.splice(index, 1);
  controller.replaceCandidate(spec);
  controller.select('source');
});

function showPixel(result: DecodedResult | null, row: number, column: number): void {
  if (!result) return;
  const { nx, ny } = result.experiment.grid;
  if (!Number.isInteger(row) || !Number.isInteger(column) || row < 0 || column < 0 || row >= ny || column >= nx) return;
  const coordinates = pixelCoordinates(result.experiment.grid, row, column);
  const intensity = result.intensity[row * nx + column];
  selectedPixel = { row, column, ...coordinates, intensity, requestId: result.requestId };
  const output = element('pixel-readout');
  output.textContent = `row=${row}, column=${column}；x=${coordinates.x_m.toPrecision(17)} m，y=${coordinates.y_m.toPrecision(17)} m；I=${intensity.toPrecision(17)} amplitude-unit²`;
  output.dataset.row = String(row); output.dataset.column = String(column);
  output.dataset.xM = String(coordinates.x_m); output.dataset.yM = String(coordinates.y_m);
  output.dataset.intensity = String(intensity); output.dataset.requestId = result.requestId;
}
element<HTMLCanvasElement>('intensity').addEventListener('click', (event) => {
  if (!displayedResult) return;
  const rect = element('intensity').getBoundingClientRect();
  const pixel = pixelFromUV(displayedResult.experiment.grid,
    (event.clientX - rect.left) / rect.width, 1 - (event.clientY - rect.top) / rect.height);
  if (pixel) showPixel(displayedResult, pixel.row, pixel.column);
});

function colorChanged(): void {
  const next = { min: Number(element<HTMLInputElement>('color-min').value), max: Number(element<HTMLInputElement>('color-max').value) };
  try {
    validateColorLimits(next);
    limits = next;
    element('color-error').hidden = true;
    render(controller.state);
  } catch (error) {
    element('color-error').hidden = false;
    element('color-error').textContent = error instanceof Error ? error.message : String(error);
  }
}
element('color-min').addEventListener('change', colorChanged);
element('color-max').addEventListener('change', colorChanged);
element('auto-color').addEventListener('click', () => {
  if (!controller.state.lastResult) return;
  limits = automaticColorLimits(controller.state.lastResult);
  element<HTMLInputElement>('color-min').value = String(limits.min);
  element<HTMLInputElement>('color-max').value = String(limits.max);
  element('color-error').hidden = true;
  render(controller.state);
});
element<HTMLSelectElement>('stage').addEventListener('change', () => {
  const selector = element<HTMLSelectElement>('stage').value;
  element('stage-note').textContent = selector === 'observation'
    ? '觀察面的場已記錄；上圖為原始強度。' : '未記錄此階段場：僅顯示標量。選取不會重新模擬。';
});

function renderResult(state: BenchState): void {
  const result = state.lastResult;
  const status = element('result-status');
  if (!result) { status.textContent = '尚未完成模擬'; return; }
  status.textContent = state.currentResult
    ? state.renderError ? '數值已完成；3D 顯示失敗，原始結果保留' : '目前草稿的完成結果'
    : '上次完成結果 · 已過期，與目前草稿分開';
  status.classList.toggle('warning', !state.currentResult);
  const key = `${result.requestId}:${limits.min}:${limits.max}`;
  if (key !== displayKey) {
    drawDetector(element('intensity'), result, limits);
    const holder = element('intensity-holder');
    holder.hidden = false;
    holder.style.aspectRatio = String(result.experiment.grid.nx * result.experiment.grid.dx
      / (result.experiment.grid.ny * result.experiment.grid.dy));
    displayedResult = result;
    displayKey = key;
    element('result-identity').textContent = `request=${result.requestId}\nSHA-256=${result.experimentSha256}`;
    const spec = result.experiment;
    element('result-spec').textContent = `原提交：λ=${(spec.wavelength_m * 1e9).toPrecision(7)} nm；${spec.grid.ny}×${spec.grid.nx}；觀察 z=${(spec.observation.z_m * 1000).toPrecision(7)} mm；${spec.components.length} 個元件。`;
    element('raw-max').textContent = `原始最大強度：${result.intensityMax.toPrecision(17)} amplitude-unit²`;
    element('raw-max').dataset.value = String(result.intensityMax);
    const stageSelect = element<HTMLSelectElement>('stage');
    const selected = stageSelect.value;
    stageSelect.replaceChildren();
    const body = element('stages'); body.replaceChildren();
    for (const stage of result.stages) {
      const option = document.createElement('option'); option.value = stage.selector; option.textContent = stage.selector; stageSelect.append(option);
      const row = document.createElement('tr');
      for (const value of [stage.selector, (stage.z_m * 1000).toPrecision(6), stage.norm.toPrecision(8),
        stage.delta_norm === null ? 'null' : stage.delta_norm.toPrecision(8), stage.transmission_ratio === null ? 'null' : stage.transmission_ratio.toPrecision(8)]) {
        const cell = document.createElement('td'); cell.textContent = value; row.append(cell);
      }
      body.append(row);
    }
    if ([...stageSelect.options].some((option) => option.value === selected)) stageSelect.value = selected;
    else stageSelect.value = result.stages.at(-1)?.selector ?? '';
    stageSelect.dispatchEvent(new Event('change'));
    showPixel(result, Math.floor(spec.grid.ny / 2), Math.floor(spec.grid.nx / 2));
  }
  element('color-info').textContent = `共用色階 ${limits.min}–${limits.max} amplitude-unit²；只改變顏色，不改變數值。`;
  const saturation = element('saturation');
  saturation.hidden = result.intensityMax <= limits.max;
  saturation.textContent = `顯示已飽和：原始最大值 ${result.intensityMax.toPrecision(8)} 超過上限 ${limits.max}；高值顯示白色，原始讀值保留。`;
}

function render(state: BenchState): void {
  if (disposed || mode !== 'sequential') return;
  const statusText: Record<string, string> = { idle: '尚未驗證', validating: '驗證草稿中', ready: '草稿已驗證', simulating: '計算中：不自動重試', error: '請檢查錯誤' };
  element('status').textContent = statusText[state.status] ?? state.status;
  element('status').dataset.status = state.status;
  element<HTMLButtonElement>('simulate').disabled = !state.validatedDraft || state.pendingValidation
    || !!state.active || operationGate.busy || Object.keys(state.invalidEdits).length > 0;
  element('error').hidden = !state.error; element('error').textContent = state.error ?? '';
  element('render-error').hidden = !state.renderError; element('render-error').textContent = state.renderError ?? '';
  renderInspector(state);
  renderComponents(state);
  element('bench-label').textContent = state.pendingValidation ? '編輯驗證中；不顯示舊結果'
    : Object.keys(state.invalidEdits).length ? '有無效輸入；不顯示舊結果'
      : state.currentResult ? '與目前提交一致的強度圖' : '已驗證草稿；尚無目前結果';
  try {
    if (scene) {
      scene.setDraftValidated(!!state.validatedDraft && !state.pendingValidation
        && Object.keys(state.invalidEdits).length === 0);
      // Detach immediately even while a new optical draft remains unvalidated.
      if (!state.currentResult) scene.updateResult(null, limits);
      if (state.validatedDraft) scene.updateExperiment(state.validatedDraft, state.selection);
      if (state.currentResult) scene.updateResult(state.currentResult, limits);
    }
  } catch (error) { reportPresentation(error); }
  // A WebGL failure must not hide an independently usable completed numerical result.
  try { renderResult(state); } catch (error) { reportPresentation(error); }
}

function dualValue(value: number | null): string { return value === null ? 'null（未定義）' : value.toPrecision(17); }

function showDualPixel(result: DecodedTwoPathResult | null, port: 0 | 1, row: number, column: number): void {
  if (!result || !Number.isInteger(row) || !Number.isInteger(column) || row < 0 || column < 0
      || row >= result.experiment.grid.ny || column >= result.experiment.grid.nx) return;
  const intensity = result.ports[port].intensity[row * result.experiment.grid.nx + column];
  dualSelectedPixel = { port, row, column, x_m: result.x[column], y_m: result.y[row], intensity, requestId: result.requestId };
  const output = document.getElementById('tp-pixel-readout');
  if (!output) return;
  output.textContent = `port_${port} · row=${row}, column=${column}；x=${result.x[column].toPrecision(17)} m，y=${result.y[row].toPrecision(17)} m；I=${intensity.toPrecision(17)} amplitude-unit²`;
  output.dataset.port = String(port); output.dataset.row = String(row); output.dataset.column = String(column);
  output.dataset.intensity = String(intensity); output.dataset.requestId = result.requestId;
}

/** Build all readout/image/table nodes off-DOM before the completed result swap. */
function dualContent(result: DecodedTwoPathResult, canvases: readonly [HTMLCanvasElement, HTMLCanvasElement]): HTMLDivElement {
  const content = document.createElement('div');
  content.innerHTML = `<div class="dual-results"><div class="dual-images"><div><h3>port 0</h3><div class="intensity-holder" id="tp-holder-0"></div><p id="tp-raw-max-0" data-testid="tp-raw-max-0"></p></div>
    <div><h3>port 1</h3><div class="intensity-holder" id="tp-holder-1"></div><p id="tp-raw-max-1" data-testid="tp-raw-max-1"></p></div><p id="tp-pixel-readout" data-testid="tp-pixel-readout" class="monospace"></p></div>
    <div class="result-details"><p id="tp-result-identity" data-testid="tp-result-identity" class="monospace"></p><p id="tp-fractions" data-testid="tp-fractions"></p>
    <pre id="tp-result-spec" data-testid="tp-result-spec"></pre><div class="table-scroll"><table><thead><tr><th>V2a plane</th><th>port 0 norm</th><th>port 1 norm</th><th>total</th></tr></thead><tbody id="tp-norms"></tbody></table></div>
    <pre id="tp-diagnostics" data-testid="tp-diagnostics"></pre></div></div>`;
  const local = <T extends HTMLElement>(id: string) => content.querySelector<T>(`#${id}`)!;
  local('tp-result-identity').textContent = `request=${result.requestId}\nSHA-256=${result.experimentSha256}`;
  local('tp-result-spec').textContent = `完整原提交（SI / rad）\n${JSON.stringify(result.experiment, null, 2)}`;
  local('tp-fractions').textContent = `原始輸入比例 η0=${dualValue(result.diagnostics.output_fractions[0])}；η1=${dualValue(result.diagnostics.output_fractions[1])}；total=${dualValue(result.diagnostics.total_output_ratio)}`;
  for (const port of [0, 1] as const) {
    const holder = local('tp-holder-' + port), canvas = canvases[port];
    holder.style.aspectRatio = String(result.experiment.grid.nx * result.experiment.grid.dx / (result.experiment.grid.ny * result.experiment.grid.dy));
    holder.append(canvas);
    canvas.addEventListener('click', event => {
      if (dualPublished !== result || !twoPathController.state.currentResult) return;
      const rect = canvas.getBoundingClientRect();
      const pixel = pixelFromUV(result.experiment.grid, (event.clientX - rect.left) / rect.width, 1 - (event.clientY - rect.top) / rect.height);
      if (pixel) showDualPixel(result, port, pixel.row, pixel.column);
    });
    const maximum = local('tp-raw-max-' + port), max = result.ports[port].intensityMax;
    maximum.dataset.value = String(max);
    maximum.textContent = `raw max=${max.toPrecision(17)} amplitude-unit²${max > dualLimits.max ? ' · 顯示飽和，原值保留' : ''}`;
    maximum.classList.toggle('warning', max > dualLimits.max);
  }
  const normTable = local('tp-norms');
  for (const plane of ['inputs', 'split', 'propagated', 'combiner', 'outputs'] as const) {
    const row = document.createElement('tr');
    for (const value of [plane, ...result.norms[plane].map(dualValue), dualValue(result.diagnostics[`${plane}_total`])]) {
      const cell = document.createElement('td'); cell.textContent = value; row.append(cell);
    }
    normTable.append(row);
  }
  local('tp-diagnostics').textContent = ['split_delta', 'propagation_delta', 'phase_delta', 'recombination_delta', 'total_delta']
    .map(key => `${key} = ${dualValue(result.diagnostics[key as keyof typeof result.diagnostics] as number)}`).join('\n');
  return content;
}

function prepareDualPresentation(result: DecodedTwoPathResult): { commit(): void; dispose(): void; finalize(): void } {
  if (!scene) throw new Error('數值已完成；WebGL2 兩埠顯示不可用，未重新計算。');
  const numericalBytes = countedResultBytes(controller.state.lastResult, twoPathController.state.lastResult, result, twoPathController.state.lastSweep);
  const imageBytes = 16 * result.experiment.grid.nx * result.experiment.grid.ny;
  if (numericalBytes + imageBytes + 128 * 1024 > OWNED_PERSISTENT_BUDGET_BYTES) throw new Error('兩埠準備超過 app-owned 資料預算。');
  const retained = (twoPathSnapshot() as { retainedBytes: number }).retainedBytes + 128 * 1024;
  if (estimateDualOperationBytes(result.experiment.grid, retained).peakOwnedBytes > OWNED_TRANSIENT_BUDGET_BYTES) {
    throw new Error('兩埠準備超過 app-owned 暫存資料預算。');
  }
  const scenePrepared = scene.prepareTwoPathResult(result, dualLimits);
  let content: HTMLDivElement;
  try { content = dualContent(result, prepareDualCanvases(result, dualLimits)); }
  catch (error) { scenePrepared.dispose(); throw error; }
  const host = element('tp-current-content'), oldChildren = Array.from(host.childNodes), previous = dualPublished;
  const previousKey = dualDisplayKey;
  let committed = false;
  return {
    commit() {
      scenePrepared.commit();
      host.replaceChildren(content); host.hidden = false;
      dualPublished = result; dualDisplayKey = `${result.requestId}:${dualLimits.min}:${dualLimits.max}`;
      committed = true;
      showDualPixel(result, 0, Math.floor(result.experiment.grid.ny / 2), Math.floor(result.experiment.grid.nx / 2));
    },
    finalize() {
      scenePrepared.finalize();
      for (const node of oldChildren) if (node instanceof HTMLElement) {
        for (const canvas of node.querySelectorAll('canvas')) { canvas.width = 0; canvas.height = 0; }
      }
    },
    dispose() {
      scenePrepared.dispose();
      if (committed) { host.replaceChildren(...oldChildren); dualPublished = previous; dualDisplayKey = previousKey; }
      for (const canvas of content.querySelectorAll('canvas')) { canvas.width = 0; canvas.height = 0; }
    },
  };
}

function renderDualFields(state: TwoPathState): void {
  const source = state.candidate.source;
  if (dualFieldsKey !== source.kind) {
    dualFieldsKey = source.kind;
    const parent = element('tp-fields'); parent.replaceChildren();
    const fields: [string, string, number, boolean?][] = [
      ['wavelength_m', 'λ / nm', 1e-9], ['grid.nx', 'Nx', 1, true], ['grid.ny', 'Ny', 1, true],
      ['grid.dx', 'dx / µm', 1e-6], ['grid.dy', 'dy / µm', 1e-6], ['source.amplitude', '振幅 / amplitude-unit', 1], ['source.phase_rad', '光源相位 / rad', 1],
    ];
    if (source.kind === 'gaussian') fields.push(['source.waist_radius_m', '腰半徑 w₀ / µm', 1e-6], ['source.waist_z_m', '腰位置 / mm', 1e-3],
      ['source.center_x_m', '中心 x / µm', 1e-6], ['source.center_y_m', '中心 y / µm', 1e-6]);
    fields.push(['two_arm_spec.arm_0_distance_m', 'L₀ 傳播 / mm', 1e-3], ['two_arm_spec.arm_1_distance_m', 'L₁ 傳播 / mm', 1e-3],
      ['two_arm_spec.relative_phase_rad', 'arm 1 extra phase / rad', 1]);
    for (const [path, label, scale, integer] of fields) {
      const wrapper = document.createElement('label'); wrapper.className = 'number-field'; wrapper.textContent = label;
      const input = document.createElement('input'); input.type = 'text'; input.inputMode = 'decimal';
      input.dataset.tpPath = path; input.dataset.scale = String(scale); input.dataset.testid = `tp-edit-${path.replaceAll('.', '-')}`;
      input.addEventListener('input', () => { void twoPathController.edit(path, input.value, scale, integer ?? false); });
      wrapper.append(input); parent.append(wrapper);
    }
  }
  element<HTMLSelectElement>('tp-source-kind').value = source.kind;
  for (const input of document.querySelectorAll<HTMLInputElement>('[data-tp-path]')) {
    const path = input.dataset.tpPath!; const invalid = Object.hasOwn(state.invalidEdits, path);
    input.classList.toggle('invalid', invalid); input.setAttribute('aria-invalid', String(invalid));
    if (document.activeElement === input) continue;
    let value: unknown = state.candidate;
    for (const part of path.split('.')) value = (value as Record<string, unknown>)[part];
    input.value = invalid ? state.invalidEdits[path] : String((value as number) / Number(input.dataset.scale));
  }
  const phi = state.candidate.two_arm_spec.relative_phase_rad;
  element('tp-phase-note').textContent = `extra phase=${phi.toPrecision(17)} rad；degrees=${(phi * 180 / Math.PI).toPrecision(8)}°（僅說明，不提交度數）`;
}

function renderSweep(sweep: DecodedTwoPathSweep | null, fresh: boolean): void {
  const status = element('tp-sweep-status'), svg = element<SVGSVGElement & HTMLElement>('tp-sweep-chart');
  status.textContent = !sweep ? '尚未完成掃描' : `${fresh ? '' : '先前掃描 · 已過期 · '}${sweep.status === 'failed' ? 'FAILED / PARTIAL' : '完成'} ${sweep.completedCount}/${sweep.requestedCount}${sweep.error ? ` · HTTP ${sweep.httpStatus} · ${sweep.error.message}` : ''}`;
  status.classList.toggle('warning', !!sweep && (!fresh || sweep.status === 'failed'));
  svg.replaceChildren(); const body = element('tp-sweep-rows'); body.replaceChildren();
  if (!sweep) return;
  element('tp-sweep-identity').textContent = `request=${sweep.requestId}\nSHA-256=${sweep.fixedExperimentSha256}\n原固定提交=${JSON.stringify(sweep.fixedExperiment)}`;
  const add = (tag: string, attributes: Record<string, string>, text?: string) => {
    const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
    if (text !== undefined) node.textContent = text;
    svg.append(node); return node;
  };
  add('path', { d: 'M55 20V190H725', fill: 'none', stroke: '#8ba2b1' });
  add('text', { x: '55', y: '218', fill: '#526e80' }, '0 rad');
  add('text', { x: '660', y: '218', fill: '#526e80' }, '2π rad');
  add('text', { x: '65', y: '16', fill: '#526e80' }, `原始輸入比例 · 共用 ${chartRange.min}–${chartRange.max} · 連線僅插值`);
  for (const port of [0, 1] as const) {
    const points = sweepPlotPoints(sweep, port, chartRange), color = port === 0 ? '#087f89' : '#9665a8';
    let segment: string[] = [];
    const finish = () => { if (segment.length > 1) add('polyline', { points: segment.join(' '), fill: 'none', stroke: color, 'stroke-width': '1.5' }); segment = []; };
    for (const point of points) {
      if (point.y === null || point.outOfRange) { finish(); continue; }
      const x = 55 + point.x * 670, y = 20 + point.y * 170; segment.push(`${x},${y}`);
      const circle = add('circle', { cx: String(x), cy: String(y), r: '4', fill: color, tabindex: '0', role: 'button',
        'data-testid': `tp-sweep-point-${port}-${point.index}`, 'aria-label': `port ${port} phase ${point.phaseRad} fraction ${point.value}` });
      const select = () => twoPathController.selectSweepPoint(point.index);
      circle.addEventListener('click', select); circle.addEventListener('keydown', event => { if ((event as KeyboardEvent).key === 'Enter') select(); });
    }
    finish();
    if (points.some(point => point.outOfRange)) add('text', { x: '60', y: String(35 + port * 16), fill: color }, `port ${port} 有值超出顯示範圍；原表值保留`);
    add('text', { x: String(550 + port * 85), y: '40', fill: color }, `● port ${port}`);
  }
  for (const row of sweep.rows) {
    const tr = document.createElement('tr'); tr.dataset.index = String(row.index);
    for (const value of [row.phase_rad, row.input_norm, ...row.output_norms, ...row.output_fractions, row.total_output_ratio, row.total_delta]) {
      const td = document.createElement('td'); td.textContent = dualValue(value); tr.append(td);
    }
    tr.addEventListener('click', () => twoPathController.selectSweepPoint(row.index)); body.append(tr);
  }
}

function renderTwoPath(state: TwoPathState): void {
  if (disposed || mode !== 'two_path') return;
  element('tp-status').textContent = state.status; element('tp-status').dataset.status = state.status;
  element('tp-error').hidden = !state.error; element('tp-error').textContent = state.error ?? '';
  element('tp-render-error').hidden = !state.renderError; element('tp-render-error').textContent = state.renderError ?? '';
  const ready = !!state.validatedDraft && !state.pendingValidation && !Object.keys(state.invalidEdits).length && !operationGate.busy;
  element<HTMLButtonElement>('tp-simulate').disabled = !ready;
  element<HTMLButtonElement>('tp-sweep').disabled = !ready || state.candidate.grid.nx > 128 || state.candidate.grid.ny > 128;
  element<HTMLButtonElement>('tp-simulate-phase').disabled = operationGate.busy || state.selectedSweepIndex === null;
  renderDualFields(state);
  element('bench-label').textContent = state.currentResult ? '兩埠立即輸出 · 與原提交一致' : '理想展開示意 · 尚無目前兩埠結果';
  try {
    if (!state.currentResult) {
      scene?.detachDualResult(); dualPublished = null; dualDisplayKey = ''; dualSelectedPixel = null;
      for (const canvas of element('tp-current-content').querySelectorAll('canvas')) { canvas.width = 0; canvas.height = 0; }
      element('tp-current-content').replaceChildren();
    }
    if (state.validatedDraft) scene?.updateTwoPathExperiment(state.validatedDraft, state.selection);
    if (state.currentResult && dualDisplayKey !== `${state.currentResult.requestId}:${dualLimits.min}:${dualLimits.max}`) {
      const prepared = prepareDualPresentation(state.currentResult);
      try { prepared.commit(); prepared.finalize(); } catch (error) { prepared.dispose(); throw error; }
    }
  } catch (error) { reportPresentation(error); }
  element('tp-color-info').textContent = `共同色階 ${dualLimits.min}–${dualLimits.max} amplitude-unit²；不自動隨結果或掃描改變。`;
  element('tp-result-status').textContent = state.currentResult ? state.renderError ? '數值完成 · 顯示故障' : '目前提交的完整兩埠結果'
    : state.completedNumerical && state.renderError ? '數值完成 · 顯示準備失敗，未發布半組結果' : state.lastResult ? '先前結果已過期 · 在原提交區保留' : '尚未完成模擬';
  const previous = element('tp-previous-result'); previous.hidden = !state.lastResult || state.currentResult === state.lastResult;
  if (state.lastResult) element('tp-previous-spec').textContent = `原 request=${state.lastResult.requestId}\n${JSON.stringify(state.lastResult.experiment, null, 2)}\n原 maxima=${state.lastResult.ports.map(p => p.intensityMax)}\n原 diagnostics=${JSON.stringify(state.lastResult.diagnostics)}`;
  const priorImages = element('tp-prior-images');
  if (previous.hidden) {
    for (const canvas of priorImages.querySelectorAll('canvas')) { canvas.width = 0; canvas.height = 0; }
    priorImages.replaceChildren(); priorDisplayKey = '';
  } else if (state.lastResult && priorDisplayKey !== `${state.lastResult.requestId}:${dualLimits.min}:${dualLimits.max}`) {
    const prior = prepareDualCanvases(state.lastResult, dualLimits);
    const holders = prior.map((canvas, port) => {
      canvas.dataset.testid = `tp-prior-intensity-${port}`;
      const holder = document.createElement('div'); holder.className = 'intensity-holder';
      const grid = state.lastResult!.experiment.grid;
      holder.style.aspectRatio = String(grid.nx * grid.dx / (grid.ny * grid.dy)); holder.append(canvas); return holder;
    });
    for (const canvas of priorImages.querySelectorAll('canvas')) { canvas.width = 0; canvas.height = 0; }
    priorImages.replaceChildren(...holders); priorDisplayKey = `${state.lastResult.requestId}:${dualLimits.min}:${dualLimits.max}`;
  }
  renderSweep(state.lastSweep, state.currentSweep === state.lastSweep);
  const selected = state.lastSweep?.rows.find(row => row.index === state.selectedSweepIndex);
  element('tp-sweep-selected').textContent = selected ? `選取實際列（不重算）=${JSON.stringify(selected)}` : '';
  const topology = element('tp-topology'); topology.replaceChildren();
  const spec = state.candidate.two_arm_spec;
  for (const [id, label] of [['source', 'input'], ['B', 'B'], ['arm_0', `arm 0 · L₀=${spec.arm_0_distance_m.toPrecision(7)} m`], ['arm_1', `arm 1 · L₁=${spec.arm_1_distance_m.toPrecision(7)} m`],
    ['phase', `extra phase=${spec.relative_phase_rad.toPrecision(7)} rad`], ['B_dagger', 'B†'], ['port_0', 'port 0'], ['port_1', 'port 1']]) {
    const button = document.createElement('button'); button.className = `component${state.selection === id ? ' selected' : ''}`;
    button.textContent = label; button.dataset.testid = `tp-select-${id}`; button.addEventListener('click', () => twoPathController.select(id)); topology.append(button);
  }
}

function twoPathSnapshot(): object {
  const state = twoPathController.state;
  const summary = (result: DecodedTwoPathResult | null) => result ? { requestId: result.requestId, experimentSha256: result.experimentSha256,
    experiment: structuredClone(result.experiment), norms: structuredClone(result.norms), diagnostics: structuredClone(result.diagnostics),
    ports: result.ports.map(port => ({ id: port.id, intensityMax: port.intensityMax })), intensityMax: result.ports.map(port => port.intensityMax),
    shape: [result.experiment.grid.ny, result.experiment.grid.nx] } : null;
  const resultBytes = countedResultBytes(controller.state.lastResult, state.lastResult, state.completedNumerical, state.lastSweep);
  const canvasBytes = [...document.querySelectorAll<HTMLCanvasElement>('#tp-result-area canvas, #intensity')].reduce((n, c) => n + c.width * c.height * 4, 0);
  const textureBytes = mode === 'two_path' && state.currentResult ? state.currentResult.experiment.grid.nx * state.currentResult.experiment.grid.ny * 8
    : mode === 'sequential' && controller.state.currentResult ? controller.state.currentResult.experiment.grid.nx * controller.state.currentResult.experiment.grid.ny * 4 : 0;
  return { candidate: structuredClone(state.candidate), validatedDraft: state.validatedDraft ? structuredClone(state.validatedDraft) : null,
    status: state.status, pendingValidation: state.pendingValidation, revision: state.revision, attachmentEpoch: state.attachmentEpoch,
    invalidEdits: { ...state.invalidEdits }, selection: state.selection, active: state.active ? structuredClone(state.active) : null,
    error: state.error, renderError: state.renderError, currentResult: summary(state.currentResult), lastResult: summary(state.lastResult), completedNumerical: summary(state.completedNumerical),
    lastSweep: state.lastSweep ? structuredClone(state.lastSweep) : null, currentSweep: state.currentSweep ? structuredClone(state.currentSweep) : null,
    selectedSweepIndex: state.selectedSweepIndex, selectedPixel: dualSelectedPixel ? { ...dualSelectedPixel } : null,
    colorLimits: { ...dualLimits }, retainedBytes: resultBytes + canvasBytes + textureBytes,
    budget: { persistent: OWNED_PERSISTENT_BUDGET_BYTES, transient: OWNED_TRANSIENT_BUDGET_BYTES,
      transientEstimate: Number.isSafeInteger(state.candidate.grid.nx) && Number.isSafeInteger(state.candidate.grid.ny)
        && state.candidate.grid.nx >= 1 && state.candidate.grid.ny >= 1 && state.candidate.grid.nx <= 512 && state.candidate.grid.ny <= 512
        ? estimateDualOperationBytes(state.candidate.grid, resultBytes + canvasBytes + textureBytes + 128 * 1024) : null,
      includes: 'deduplicated scientific buffers, scalar sweep JSON, both-mode canvas and active texture-source bytes; transient phase estimate includes wire chunks/join, decoded arrays and conversion buffers',
      excludes: 'JS object/string overhead, renderer framebuffer/cache, GPU/driver allocations, entire heap/tab/process' } };
}

for (const item of TWO_PATH_PRESETS) {
  const option = document.createElement('option'); option.value = item.id; option.textContent = item.label; element('tp-preset').append(option);
}
element('tp-preset').addEventListener('change', () => { void twoPathController.replaceCandidate(twoPathPreset(element<HTMLSelectElement>('tp-preset').value)); });
element('tp-source-kind').addEventListener('change', () => {
  const edited = structuredClone(twoPathController.state.candidate); const { amplitude, phase_rad } = edited.source;
  edited.source = element<HTMLSelectElement>('tp-source-kind').value === 'uniform' ? { kind: 'uniform', amplitude, phase_rad }
    : { kind: 'gaussian', amplitude, phase_rad, waist_radius_m: 50e-6, waist_z_m: 0, center_x_m: 0, center_y_m: 0 };
  void twoPathController.replaceCandidate(edited);
});
for (const [id, phase] of [['tp-phase-0', 0], ['tp-phase-halfpi', Math.PI / 2], ['tp-phase-pi', Math.PI]] as const) {
  element(id).addEventListener('click', () => { void twoPathController.edit('two_arm_spec.relative_phase_rad', String(phase)); });
}
element('tp-simulate').addEventListener('click', () => { void twoPathController.simulate(); });
element('tp-sweep').addEventListener('click', () => { void twoPathController.runSweep(); });
element('tp-simulate-phase').addEventListener('click', () => { void twoPathController.simulateSelectedPhase(); });
function dualColorChanged(): void {
  try {
    const next = { min: Number(element<HTMLInputElement>('tp-color-min').value), max: Number(element<HTMLInputElement>('tp-color-max').value) };
    validateColorLimits(next); dualLimits = next; element('tp-color-error').hidden = true; renderTwoPath(twoPathController.state);
  } catch (error) { element('tp-color-error').hidden = false; element('tp-color-error').textContent = String(error); }
}
element('tp-color-min').addEventListener('change', dualColorChanged); element('tp-color-max').addEventListener('change', dualColorChanged);
element('tp-auto-color').addEventListener('click', () => {
  const result = twoPathController.state.currentResult;
  if (!result) return;
  dualLimits = automaticDualColorLimits(result);
  element<HTMLInputElement>('tp-color-min').value = String(dualLimits.min); element<HTMLInputElement>('tp-color-max').value = String(dualLimits.max);
  renderTwoPath(twoPathController.state);
});
element('tp-chart-range').addEventListener('click', () => {
  const next = { min: Number(element<HTMLInputElement>('tp-chart-min').value), max: Number(element<HTMLInputElement>('tp-chart-max').value) };
  if (!Number.isFinite(next.min) || !Number.isFinite(next.max) || next.max <= next.min) { notice('圖表範圍必須有限且下限小於上限。'); return; }
  chartRange = next; renderSweep(twoPathController.state.lastSweep, twoPathController.state.currentSweep === twoPathController.state.lastSweep);
});
element('mode').addEventListener('change', () => {
  controller.deactivate(); twoPathController.deactivate();
  scene?.updateResult(null, limits); scene?.detachDualResult();
  mode = element<HTMLSelectElement>('mode').value === 'two_path' ? 'two_path' : 'sequential'; app!.dataset.mode = mode;
  dualPublished = null; dualSelectedPixel = null; dualDisplayKey = ''; displayedResult = null; displayKey = '';
  for (const canvas of document.querySelectorAll<HTMLCanvasElement>('#tp-result-area canvas')) { canvas.width = 0; canvas.height = 0; }
  element('tp-current-content').replaceChildren(); element('tp-prior-images').replaceChildren(); priorDisplayKey = '';
  const legacyCanvas = element<HTMLCanvasElement>('intensity'); legacyCanvas.width = 0; legacyCanvas.height = 0;
  element('intensity-holder').hidden = true;
  document.querySelector<HTMLElement>('.bench-help')!.textContent = mode === 'two_path'
    ? 'Orbit / Pan / Zoom 與選取只改顯示；固定展開光路不可拖曳。虛線僅為指引。'
    : '左鍵旋轉（Orbit）・右鍵平移（Pan）・滾輪縮放（Zoom）・點擊選取；橘色控制球僅沿 z 軸拖曳。';
  element('pick-choices').replaceChildren();
  if (mode === 'two_path') { renderTwoPath(twoPathController.state); void twoPathController.activate(); }
  else { render(controller.state); void controller.activate(); }
});
twoPathController.setResultPreparer(prepareDualPresentation);
controller.subscribe(render); twoPathController.subscribe(renderTwoPath);
operationGate.subscribe(() => {
  if (mode === 'sequential') element<HTMLButtonElement>('simulate').disabled = operationGate.busy || !controller.state.validatedDraft || controller.state.pendingValidation || !!Object.keys(controller.state.invalidEdits).length;
  else {
    const state = twoPathController.state; const ready = !operationGate.busy && !!state.validatedDraft && !state.pendingValidation && !Object.keys(state.invalidEdits).length;
    element<HTMLButtonElement>('tp-simulate').disabled = !ready; element<HTMLButtonElement>('tp-sweep').disabled = !ready || state.candidate.grid.nx > 128 || state.candidate.grid.ny > 128;
  }
});
void controller.validateInitial();

function stateSnapshot(): object {
  const state = controller.state;
  const resultSummary = (result: DecodedResult | null) => result ? {
    requestId: result.requestId, experimentSha256: result.experimentSha256,
    experiment: cloneExperiment(result.experiment), intensityMax: result.intensityMax,
    stages: structuredClone(result.stages), shape: [result.experiment.grid.ny, result.experiment.grid.nx],
  } : null;
  return {
    mode,
    candidate: cloneExperiment(state.candidate), validatedDraft: state.validatedDraft ? cloneExperiment(state.validatedDraft) : null,
    revision: state.revision, selection: state.selection, status: state.status,
    pendingValidation: state.pendingValidation, invalidEdits: { ...state.invalidEdits },
    error: state.error, renderError: state.renderError,
    active: state.active ? structuredClone(state.active) : null,
    lastResult: resultSummary(state.lastResult), currentResult: resultSummary(state.currentResult),
    colorLimits: { ...limits }, selectedPixel: selectedPixel ? { ...selectedPixel } : null,
    scene: scene?.snapshot() ?? { available: false },
    twoPath: twoPathSnapshot(),
  };
}

declare global {
  interface Window {
    __benchDebug: {
      snapshot: () => object;
      worldToClient: (x: number, y: number, z: number) => { x: number; y: number; visible: boolean } | null;
      dualPixelWorld: (port: 0 | 1, row: number, column: number) => { x: number; y: number; z: number } | null;
    };
  }
}
Object.defineProperty(window, '__benchDebug', { value: Object.freeze({
  snapshot: stateSnapshot,
  worldToClient: (x: number, y: number, z: number) => scene?.worldToClient(x, y, z) ?? null,
  dualPixelWorld: (port: 0 | 1, row: number, column: number) => scene?.dualPixelWorld(port, row, column) ?? null,
}), writable: false, configurable: false });
window.addEventListener('pagehide', () => { disposed = true; scene?.dispose(); }, { once: true });
