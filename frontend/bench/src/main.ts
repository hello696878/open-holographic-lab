import './styles.css';
import { BenchController, ClientOperationGate, type BenchState } from './state';
import { cloneExperiment, createFetchAPI, type Experiment, type DecodedResult } from './contracts';
import { PRESETS, presetExperiment } from './presets';
import { pixelCoordinates, pixelFromUV } from './mapping';
import { automaticColorLimits, automaticDualColorLimits, prepareDualCanvases, drawDetector, INITIAL_COLOR_LIMITS, validateColorLimits, type ColorLimits } from './detector';
import { BenchScene } from './scene';
import { TwoPathController, type TwoPathState } from './two_path_state';
import { createTwoPathFetchAPI, type TwoPathExperiment, type DecodedTwoPathResult, type DecodedTwoPathSweep } from './two_path_contracts';
import { TWO_PATH_PRESETS, twoPathPreset } from './two_path_presets';
import { countedResultBytes, estimateDualOperationBytes, sweepPlotPoints, OWNED_PERSISTENT_BUDGET_BYTES, OWNED_TRANSIENT_BUDGET_BYTES } from './phase_sweep';
import { PolarizationController, type PolarizationState } from './polarization_state';
import { COEFFICIENT_PRESETS, POLARIZATION_PRESETS, polarizationPreset } from './polarization_presets';
import { type DecodedPolarizationResult, type DecodedPolarizationSweep, type PolarizationExperiment } from './polarization_contracts';
import { assertOwnedBudgets, estimateOwnedOperation, ownedScientificBytes, PolarizationPlayback, preparePolarizationResources,
  trajectoryMarker, validateDisplayScale, type PolarizationResources } from './polarization_display';
import { NumericFieldBinding } from './numeric_fields';
import { ExperimentDocumentController } from './experiment_document_state';
import { type BenchMode, type ValidatedDocument } from './experiment_documents';

const app = document.querySelector<HTMLDivElement>('#app');
if (!app) throw new Error('缺少應用程式容器。');
app.innerHTML = `
  <header class="app-header"><div><span class="eyebrow">OPEN HOLOGRAPHIC LAB / V1 + V2b + V2d</span><h1>虛擬光學實驗台</h1></div>
    <div class="header-detail">單色 · 純量 · 同軸前向光路<br><span>本機運作／明確提交</span></div></header>
  <main>
    <section class="toolbar" aria-label="實驗控制">
      <label>模式 <select id="mode" data-testid="mode"><option value="sequential">順序光路（Sequential）</option><option value="two_path">兩路干涉（Two-path）</option><option value="polarization">理想偏振（Jones polarization）</option></select></label>
      <label class="sequential-only">載入預設 <select id="preset" data-testid="preset"></select></label>
      <button id="simulate" class="primary sequential-only" data-testid="simulate">模擬（Simulate）</button>
      <output id="status" class="sequential-only" data-testid="status" aria-live="polite"></output>
      <button id="tp-simulate" class="primary two-path-only" data-testid="tp-simulate">模擬兩埠（Simulate）</button>
      <button id="tp-sweep" class="two-path-only" data-testid="tp-sweep">相位掃描（17 points）</button>
      <output id="tp-status" class="two-path-only" data-testid="tp-status" aria-live="polite"></output>
      <button id="pl-simulate" class="primary polarization-only" data-testid="pl-simulate">偏振模擬（Simulate）</button>
      <button id="pl-sweep" class="polarization-only" data-testid="pl-sweep">分析器角度掃描（13 points）</button>
      <output id="pl-status" class="polarization-only" data-testid="pl-status" aria-live="polite"></output>
    </section>
    <p id="error" class="error" data-testid="error" role="alert" hidden></p>
    <p id="render-error" class="error" data-testid="render-error" role="alert" hidden></p>
    <details id="documents" class="panel document-panel" data-testid="documents">
      <summary data-testid="doc-toggle">實驗設定檔 · 匯出目前草稿／匯入設定</summary>
      <p class="muted">一個檔案保存一個實驗的設定，不包含計算結果或掃描。未匯出的草稿不會自動保存。</p>
      <div class="document-fields">
        <label>設定標題 <input id="doc-title" data-testid="doc-title" type="text" autocomplete="off"></label>
        <label>備註 <textarea id="doc-notes" data-testid="doc-notes" rows="2"></textarea></label>
      </div>
      <div class="document-actions">
        <button id="doc-export" data-testid="doc-export">匯出實驗設定（目前有效草稿）</button>
        <label>匯入實驗設定 <input id="doc-file" data-testid="doc-file" type="file" accept=".json,application/json"></label>
        <button id="doc-cancel" data-testid="doc-cancel">取消匯入</button>
      </div>
      <output id="doc-status" data-testid="doc-status" aria-live="polite"></output>
      <p id="doc-error" data-testid="doc-error" class="error" role="alert" hidden></p>
      <div id="doc-download-area" data-testid="doc-download-area" hidden><p id="doc-download-label"></p>
        <a id="doc-download" data-testid="doc-download">下載實驗設定</a>
        <button id="doc-dismiss" data-testid="doc-dismiss">關閉下載連結</button>
      </div>
      <div id="doc-preview" data-testid="doc-preview" hidden>
        <h3>待套用設定</h3><pre id="doc-preview-text" data-testid="doc-preview-text"></pre>
        <label class="document-ack"><input id="doc-ack" data-testid="doc-ack" type="checkbox">我了解這會取代該模式目前的設定，包括尚未匯出的編輯。</label>
        <button id="doc-apply" data-testid="doc-apply" class="primary" disabled>取代目前設定並套用</button>
      </div>
    </details>
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
      <aside class="panel polarization-only polarization-controls"><h2>入射與有序元件</h2>
        <label>預設 <select id="pl-preset" data-testid="pl-preset"></select></label>
        <label>光源 <select id="pl-source-kind" data-testid="pl-source-kind"><option value="uniform">均勻 Uniform</option><option value="gaussian">Gaussian at waist</option></select></label>
        <label>複數係數預設 <select id="pl-coefficients-preset" data-testid="pl-coefficients-preset"></select></label>
        <div id="pl-fields"></div><div id="pl-elements" data-testid="pl-elements"></div>
        <div class="add-controls"><select id="pl-add-kind" data-testid="pl-add-kind" aria-label="偏振元件種類"><option value="linear_polarizer">線偏振片</option><option value="linear_retarder">線性延遲器</option></select>
          <button id="pl-add" data-testid="pl-add">新增元件</button><button id="pl-delete" data-testid="pl-delete">刪除選取元件</button>
          <button id="pl-up" data-testid="pl-up">選取元件往前</button><button id="pl-down" data-testid="pl-down">選取元件往後</button></div>
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
      <aside class="panel polarization-only"><h2>選取元件屬性</h2><div id="pl-inspector"></div>
        <button id="pl-qwp" data-testid="pl-qwp">QWP：δ=π/2 rad</button><button id="pl-hwp" data-testid="pl-hwp">HWP：δ=π rad</button>
        <p class="muted">同一參考平面上的理想有序作用。示意間距與外殼不新增傳播、厚度或光學相位。Gaussian 腰位置固定為零，無物理 z 控制。</p>
        <p class="muted">x/y 是偏振分量，不是光學埠。係數不自動正規化；數值欄位保留完整 radians 與 SI 值。編輯只驗證，請明確提交。</p></aside>
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
    <section class="panel result-panel polarization-only" id="pl-result-area"><div class="result-heading"><h2>偏振 · 實際場與固定樣本</h2><strong id="pl-result-status" data-testid="pl-result-status">尚未提交</strong></div>
      <p id="pl-error" data-testid="pl-error" class="error" hidden></p><p id="pl-render-error" data-testid="pl-render-error" class="error" hidden></p>
      <div class="color-controls"><label>共同強度下限 <input id="pl-color-min" data-testid="pl-color-min" value="0"></label><label>共同強度上限 <input id="pl-color-max" data-testid="pl-color-max" value="10"></label>
        <button id="pl-auto-color" data-testid="pl-auto-color">共同自動色階（不重算）</button><button id="pl-retry-display" data-testid="pl-retry-display">重試顯示（不重算）</button></div>
      <p id="pl-color-info" class="muted"></p><div id="pl-current-content"></div>
      <details id="pl-previous-result" data-testid="pl-previous-result" hidden><summary>先前結果 · 原提交與目前草稿分開</summary><pre id="pl-previous-spec"></pre></details>
      <div class="color-controls"><label>共同 τ / rad <input id="pl-tau" data-testid="pl-tau" value="0"></label><button id="pl-play" data-testid="pl-play">播放 / 暫停 τ</button><button id="pl-reset" data-testid="pl-reset">暫停並重設 τ=0</button>
        <label>共同振幅刻度 / amplitude-unit <input id="pl-amplitude-scale" data-testid="pl-amplitude-scale" value="1"></label><label>手動顯示放大（1..1e18）<input id="pl-display-gain" data-testid="pl-display-gain" value="1"></label></div>
      <p class="muted">沿 +z 看橫向平面，+x 向右／+y 向下；等比例座標。Re([Ux,Uy] exp(−iτ))，保留共同相位；τ 是無因次示意，不是物理影格速率。手動放大只改顯示，所有階段共用刻度。</p>
    </section>
    <section class="panel result-panel polarization-only"><div class="result-heading"><h2>實際分析器角度掃描</h2><strong id="pl-sweep-status" data-testid="pl-sweep-status">尚未掃描</strong></div>
      <p class="muted">13 次真正完整序列計算，每點由原始入射重新開始；−90° 與 +90° 分開計算。點選不重算；連線只是視覺插值。失敗只顯示真正完成前綴。</p>
      <svg id="pl-sweep-chart" data-testid="pl-sweep-chart" viewBox="0 0 760 230" role="img" aria-label="實際角度掃描"></svg>
      <p id="pl-sweep-identity" data-testid="pl-sweep-identity" class="monospace"></p><p id="pl-sweep-selected" class="monospace"></p>
      <button id="pl-apply-angle" data-testid="pl-apply-angle" disabled>明確套用選取角度並模擬（原掃描設定）</button>
      <div class="table-scroll"><table><thead><tr><th>index</th><th>θ / rad</th><th>final norm</th><th>原入射比例</th><th>signed Δnorm</th></tr></thead><tbody id="pl-sweep-rows" data-testid="pl-sweep-rows"></tbody></table></div>
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
const sequentialAPI = createFetchAPI(), dualAPI = createTwoPathFetchAPI();
const controller = new BenchController(presetExperiment(PRESETS[0].id), { ...sequentialAPI,
  simulate(envelope) { admitOperation('sequential', envelope.experiment.grid); return sequentialAPI.simulate(envelope); } }, undefined, operationGate);
const twoPathController = new TwoPathController(twoPathPreset(TWO_PATH_PRESETS[0].id), { ...dualAPI,
  simulate(envelope) { admitOperation('two_path', envelope.experiment.grid); return dualAPI.simulate(envelope); },
  sweep(envelope) { admitOperation('two_path', envelope.fixed_experiment.grid, 'sweep'); return dualAPI.sweep(envelope); } }, undefined, operationGate);
const polarizationController = new PolarizationController(polarizationPreset('analyzer'), undefined, undefined, operationGate);
let mode: 'sequential' | 'two_path' | 'polarization' = 'sequential';
app.dataset.mode = mode;
let scene: BenchScene | null = null;
let limits: ColorLimits = { ...INITIAL_COLOR_LIMITS };
let displayedResult: DecodedResult | null = null;
let displayKey = '';
let inspectorKey = '';
let selectedPixel: { row: number; column: number; x_m: number; y_m: number; intensity: number; requestId: string } | null = null;
let nextId = 1;
let disposed = false;
let applyingDocument = false;
let documents: ExperimentDocumentController | null = null;
let scientificReservations = { persistent: 0, transient: 0 };
const numericBindings = new WeakMap<HTMLInputElement, NumericFieldBinding>();
let dualLimits: ColorLimits = { min: 0, max: 1 };
let dualPublished: DecodedTwoPathResult | null = null;
let dualDisplayKey = '';
let dualFieldsKey = '';
let priorDisplayKey = '';
let dualSelectedPixel: { port: 0 | 1; row: number; column: number; x_m: number; y_m: number; intensity: number; requestId: string } | null = null;
let chartRange: ColorLimits = { min: 0, max: 1 };
let polarizationLimits: ColorLimits = { min: 0, max: 10 };
let polarizationPublished: DecodedPolarizationResult | null = null;
let polarizationResources: PolarizationResources | null = null;
let polarizationDisplayKey = '', polarizationFieldsKey = '', polarizationInspectorKey = '';
let polarizationScale = 1, polarizationGain = 1, nextPolarizationId = 1;
let polarizationSelectedPixel: { view: 0 | 1; row: number; column: number; intensity: number; x_m: number; y_m: number; requestId: string } | null = null;
const polarizationPlayback = new PolarizationPlayback();

function notice(text: string): void { element('notice').textContent = text; }

function reportPresentation(error: unknown): void {
  const message = error instanceof Error ? error.message : String(error);
  if (mode === 'polarization') { if (polarizationController.state.renderError !== message) polarizationController.reportRenderFailure(message); }
  else if (mode === 'two_path') {
    if (twoPathController.state.renderError !== message) twoPathController.reportRenderFailure(message);
  } else if (controller.state.renderError !== message) controller.reportRenderFailure(message);
}

try {
  scene = new BenchScene(element('bench'), {
    select(ids) {
      if (mode === 'polarization') { polarizationController.select(ids[0]); return; }
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
    polarizationPixel: (view, row, column) => showPolarizationPixel(polarizationController.state.currentResult, view, row, column),
    commitZ(id, z_m) {
      const spec = cloneExperiment(controller.state.candidate);
      const component = spec.components.find((item) => item.id === id);
      if (component) component.z_m = z_m;
      else if (spec.observation.id === id) spec.observation.z_m = z_m;
      controller.replaceCandidate(spec);
    },
    notice,
    presentationFailure(message) {
      if (mode === 'polarization') {
        if (message) { polarizationPlayback.detach(); polarizationController.invalidatePresentation(message); }
        else polarizationController.reportRenderFailure(null);
      } else if (mode === 'two_path') twoPathController.reportRenderFailure(message);
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

function readPath(spec: unknown, path: string): number {
  let current: unknown = spec;
  for (const part of path.split('.')) current = (current as Record<string, unknown>)[part];
  return current as number;
}

function paintNumeric(input: HTMLInputElement, benchMode: BenchMode, path: string,
    state: { candidate: unknown; revision: number; attachmentEpoch: number }, invalid: boolean): void {
  let binding = numericBindings.get(input);
  if (!binding) { binding = new NumericFieldBinding(); numericBindings.set(input, binding); }
  if (invalid) binding.clear();
  else binding.paint(input.value, `${benchMode}.${path}`, `${state.revision}:${state.attachmentEpoch}`, readPath(state.candidate, path));
}

function shouldEditNumeric(input: HTMLInputElement, benchMode: BenchMode, path: string,
    state: { candidate: unknown; revision: number; attachmentEpoch: number }): boolean {
  return numericBindings.get(input)?.shouldEdit(input.value, `${benchMode}.${path}`,
    `${state.revision}:${state.attachmentEpoch}`, readPath(state.candidate, path)) ?? true;
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
  input.addEventListener('input', () => {
    if (shouldEditNumeric(input, 'sequential', path, controller.state)) void controller.edit(path, input.value, scale, integer);
  });
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
      paintNumeric(input, 'sequential', path, state, invalid);
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
  if (disposed || applyingDocument || mode !== 'sequential') return;
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
  const numericalBytes = ownedSnapshot(result).scientificBytes;
  const imageBytes = 16 * result.experiment.grid.nx * result.experiment.grid.ny;
  if (numericalBytes + imageBytes + 128 * 1024 > OWNED_PERSISTENT_BUDGET_BYTES) throw new Error('兩埠準備超過 app-owned 資料預算。');
  const retained = ownedSnapshot().retainedBytes + 128 * 1024;
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
      input.addEventListener('input', () => {
        if (shouldEditNumeric(input, 'two_path', path, twoPathController.state)) void twoPathController.edit(path, input.value, scale, integer ?? false);
      });
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
    paintNumeric(input, 'two_path', path, state, invalid);
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
  if (disposed || applyingDocument || mode !== 'two_path') return;
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

/** All modes share these ownership calculations. Aliased arrays are counted once. */
function ownedSnapshot(additional: DecodedPolarizationResult | DecodedTwoPathResult | null = null): {
  scientificBytes: number; canvasBytes: number; textureBytes: number; trajectoryBytes: number; geometryBytes: number; documentBytes: number; retainedBytes: number;
} {
  const sceneResults = scene?.ownedNumericalResults();
  const scientificBytes = ownedScientificBytes([controller.state.lastResult, displayedResult, sceneResults?.sequential ?? null],
    [twoPathController.state.lastResult, twoPathController.state.completedNumerical, dualPublished, sceneResults?.dual ?? null,
      additional && 'ports' in additional ? additional : null],
    [polarizationController.state.lastResult, polarizationController.state.completedNumerical, polarizationPublished, sceneResults?.polarization ?? null,
      additional && 'incidentIntensity' in additional ? additional : null],
    [twoPathController.state.lastSweep, polarizationController.state.lastSweep]);
  const canvasBytes = [...document.querySelectorAll<HTMLCanvasElement>('#intensity, #tp-result-area canvas, #pl-result-area canvas')]
    .reduce((n, canvas) => n + canvas.width * canvas.height * 4, 0);
  const textureBuffers = new Set<ArrayBufferLike>(scene?.ownedTextureBuffers() ?? []);
  for (const texture of polarizationResources?.textures ?? []) textureBuffers.add((texture.image.data as Uint8Array).buffer);
  const textureBytes = [...textureBuffers].reduce((n, buffer) => n + buffer.byteLength, 0);
  const trajectoryBytes = polarizationResources?.trajectories.reduce((n, trajectory) => n + trajectory.points.byteLength, 0) ?? 0;
  const geometryBytes = scene?.ownedGeometryBuffers().reduce((n, buffer) => n + buffer.byteLength, 0) ?? 0;
  const documentBytes = documents?.ownershipSnapshot().retainedBytes ?? 0;
  return { scientificBytes, canvasBytes, textureBytes, trajectoryBytes, geometryBytes, documentBytes,
    retainedBytes: scientificBytes + canvasBytes + textureBytes + trajectoryBytes + geometryBytes + documentBytes };
}
function admitOperation(kind: 'sequential' | 'two_path' | 'polarization', grid: Experiment['grid'], operation: 'single' | 'sweep' = 'single'): void {
  const bytes = ownedSnapshot().retainedBytes, estimate = estimateOwnedOperation(kind, grid, bytes, operation);
  // Before any HTTP allocation, conservatively reserve a distinct successful
  // completion alongside all actual old owners. A scene/canvas preparation
  // failure may retain different sequential results, so replacement cannot be
  // assumed to release those buffers. No owner is discarded to make room.
  const projectedPersistent = bytes + (operation === 'sweep' ? 65536 : estimate.payloadBytes + 16384);
  const docReservation = documents?.ownershipSnapshot();
  assertOwnedBudgets(projectedPersistent + (docReservation?.projectedPersistentBytes ?? 0),
    estimate.peakOwnedBytes + (docReservation?.transientReservedBytes ?? 0));
  scientificReservations = { persistent: projectedPersistent - bytes, transient: Math.max(0, estimate.peakOwnedBytes - bytes) };
}

function detachPolarizationPresentation(): void {
  polarizationPlayback.detach(); scene?.setFrameCallback(null); scene?.detachPolarizationResult();
  polarizationResources?.dispose(); polarizationResources = null; polarizationPublished = null; polarizationDisplayKey = '';
  polarizationSelectedPixel = null; element('pl-current-content').replaceChildren();
}
function showPolarizationPixel(result: DecodedPolarizationResult | null, view: 0 | 1, row: number, column: number): void {
  if (!result || !Number.isInteger(row) || !Number.isInteger(column) || row < 0 || column < 0
      || row >= result.experiment.grid.ny || column >= result.experiment.grid.nx) return;
  const intensity = (view === 0 ? result.incidentIntensity : result.finalIntensity)[row * result.experiment.grid.nx + column];
  polarizationSelectedPixel = { view, row, column, intensity, x_m: result.x[column], y_m: result.y[row], requestId: result.requestId };
  const output = document.getElementById('pl-pixel-readout');
  if (output) output.textContent = `${view === 0 ? 'incident' : 'final'} intensity pixel row=${row}, column=${column}; x=${result.x[column]}, y=${result.y[row]} m; I=${intensity} amplitude-unit². 固定複數樣本未改變。`;
}
function polarizationContent(result: DecodedPolarizationResult, resources: PolarizationResources): HTMLDivElement {
  const content = document.createElement('div');
  content.innerHTML = `<p id="pl-identity" data-testid="pl-identity" class="monospace"></p><pre id="pl-result-spec"></pre>
    <div class="dual-images"><div><h3>incident · 入射強度</h3><div class="intensity-holder" id="pl-holder-0"></div><p id="pl-max-0" data-testid="pl-max-0"></p></div>
    <div><h3>final · 最終強度</h3><div class="intensity-holder" id="pl-holder-1"></div><p id="pl-max-1" data-testid="pl-max-1"></p></div></div>
    <p id="pl-pixel-readout" data-testid="pl-pixel-readout" class="monospace"></p>
    <label>已提交階段 <select id="pl-stage" data-testid="pl-stage"></select></label><p id="pl-stage-note" data-testid="pl-stage-note"></p>
    <pre id="pl-sample" data-testid="pl-sample"></pre><div id="pl-trajectories" data-testid="pl-trajectories" class="polarization-trajectories"></div>
    <div class="table-scroll"><table><thead><tr><th>stage</th><th>actual norm</th><th>signed Δnorm</th><th>adjacent ratio</th><th>original-incident ratio</th></tr></thead><tbody id="pl-stages" data-testid="pl-stages"></tbody></table></div>`;
  const local = <T extends HTMLElement>(id: string) => content.querySelector<T>(`#${id}`)!;
  local('pl-identity').textContent = `request=${result.requestId}\nSHA-256=${result.experimentSha256}`;
  local('pl-result-spec').textContent = `完整原提交 / SI / rad\n${JSON.stringify(result.experiment, null, 2)}`;
  for (const view of [0, 1] as const) {
    const holder = local('pl-holder-' + view), canvas = resources.canvases[view];
    holder.style.aspectRatio = String(result.experiment.grid.nx * result.experiment.grid.dx / (result.experiment.grid.ny * result.experiment.grid.dy));
    holder.append(canvas); local('pl-max-' + view).textContent = `raw max=${result.intensityMax[view]} amplitude-unit²${result.intensityMax[view] > polarizationLimits.max ? ' · 顯示飽和，原值保留' : ''}`;
    local('pl-max-' + view).dataset.value = String(result.intensityMax[view]);
    canvas.addEventListener('click', event => {
      if (mode !== 'polarization' || polarizationPublished !== result || polarizationController.state.currentResult !== result) return;
      const rect = canvas.getBoundingClientRect(), pixel = pixelFromUV(result.experiment.grid,
        (event.clientX - rect.left) / rect.width, 1 - (event.clientY - rect.top) / rect.height);
      if (pixel) showPolarizationPixel(result, view, pixel.row, pixel.column);
    });
  }
  const select = local<HTMLSelectElement>('pl-stage');
  for (const stage of result.stages) {
    const option = document.createElement('option'); option.value = stage.stage_id; option.textContent = stage.stage_id; select.append(option);
    const tr = document.createElement('tr');
    for (const value of [stage.stage_id, stage.norm, stage.delta_norm, stage.adjacent_transmission_ratio, stage.incident_transmission_ratio]) {
      const cell = document.createElement('td'); cell.textContent = value === null ? 'null（未定義）' : String(value); tr.append(cell);
    }
    local('pl-stages').append(tr);
  }
  select.value = result.orderedStageIds.includes(polarizationController.state.selectedStage) ? polarizationController.state.selectedStage : 'input';
  select.addEventListener('change', () => polarizationController.selectStage(select.value));
  const ns = 'http://www.w3.org/2000/svg';
  for (const trajectory of resources.trajectories) {
    const card = document.createElement('div'), label = document.createElement('h3'); label.textContent = trajectory.stageId;
    const svg = document.createElementNS(ns, 'svg'); svg.setAttribute('viewBox', '-120 -120 240 240'); svg.dataset.stageId = trajectory.stageId;
    svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', `${trajectory.stageId} actual complex trajectory`);
    const axes = document.createElementNS(ns, 'path'); axes.setAttribute('d', 'M-100 0H100 M0 -100V100'); axes.setAttribute('stroke', '#beced7'); axes.setAttribute('fill', 'none'); svg.append(axes);
    if (trajectory.renderable) {
      const line = document.createElementNS(ns, 'polyline'), points: string[] = [];
      for (let i = 0; i < trajectory.points.length; i += 2) points.push(`${trajectory.points[i] * 100},${trajectory.points[i + 1] * 100}`);
      line.setAttribute('points', points.join(' ')); line.setAttribute('fill', 'none'); line.setAttribute('stroke', '#087f89'); line.setAttribute('stroke-width', '1.5'); svg.append(line);
    }
    const marker = document.createElementNS(ns, 'circle'); marker.setAttribute('r', '4'); marker.setAttribute('fill', '#d28b28'); marker.dataset.marker = trajectory.stageId; svg.append(marker);
    const zero = trajectoryMarker(trajectory.sample, 0); const zeroDot = document.createElementNS(ns, 'circle');
    zeroDot.setAttribute('r', '2.5'); zeroDot.setAttribute('fill', '#9665a8');
    const zx = zero.x / resources.commonAmplitudeScale * resources.gain * 100, zy = zero.y / resources.commonAmplitudeScale * resources.gain * 100;
    zeroDot.setAttribute('cx', String(Number.isFinite(zx) ? zx : 0)); zeroDot.setAttribute('cy', String(Number.isFinite(zy) ? zy : 0));
    zeroDot.setAttribute('aria-label', 'tau=0 phase reference'); zeroDot.setAttribute('visibility', Number.isFinite(zx) && Number.isFinite(zy) ? 'visible' : 'hidden'); svg.append(zeroDot);
    const note = document.createElement('p'); note.className = 'muted';
    note.textContent = trajectory.dark ? 'no defined polarization state at this sample（精確零）'
      : trajectory.displayLimited ? '非零樣本 · display-scale/precision limitation；原始複數值保留。' : '非零樣本 · shared scale · τ=0 紫點；橘點沿增加 τ 移動。';
    card.append(label, svg, note); local('pl-trajectories').append(card);
  }
  return content;
}
function updatePolarizationMarkers(tau: number): void {
  if (mode !== 'polarization' || !polarizationResources || !polarizationPublished) return;
  element<HTMLInputElement>('pl-tau').value = String(tau);
  for (const trajectory of polarizationResources.trajectories) {
    const marker = element('pl-current-content').querySelector<SVGCircleElement>(`[data-marker="${trajectory.stageId}"]`);
    if (!marker) continue;
    const raw = trajectoryMarker(trajectory.sample, tau), x = raw.x / polarizationResources.commonAmplitudeScale * polarizationResources.gain * 100,
      y = raw.y / polarizationResources.commonAmplitudeScale * polarizationResources.gain * 100;
    marker.setAttribute('visibility', !trajectory.dark && Number.isFinite(x) && Number.isFinite(y) ? 'visible' : 'hidden');
    if (Number.isFinite(x) && Number.isFinite(y)) { marker.setAttribute('cx', String(x)); marker.setAttribute('cy', String(y)); }
    marker.dataset.rawX = String(raw.x); marker.dataset.rawY = String(raw.y); marker.dataset.tau = String(tau);
  }
}
function preparePolarizationPresentation(result: DecodedPolarizationResult): { commit(): void; dispose(): void; finalize(): void } {
  if (!scene) throw new Error('數值完成；WebGL2 不可用，未重算。');
  const estimate = estimateOwnedOperation('polarization', result.experiment.grid, ownedSnapshot().retainedBytes);
  const persistent = ownedSnapshot(result).retainedBytes + 16 * result.experiment.grid.nx * result.experiment.grid.ny + result.stages.length * 257 * 16;
  assertOwnedBudgets(persistent, estimate.peakOwnedBytes);
  const resources = preparePolarizationResources(result, polarizationLimits, polarizationScale, polarizationGain);
  let content: HTMLDivElement, prepared: ReturnType<BenchScene['preparePolarizationResult']>;
  try { content = polarizationContent(result, resources); prepared = scene.preparePolarizationResult(result, resources.textures); }
  catch (error) { resources.dispose(); throw error; }
  const host = element('pl-current-content'), oldNodes = Array.from(host.childNodes), oldResources = polarizationResources;
  const previous = polarizationPublished, previousKey = polarizationDisplayKey; let committed = false, closed = false;
  return {
    commit() {
      if (closed) throw new Error('Polarization presentation transaction closed');
      prepared.commit(); host.replaceChildren(content); polarizationPublished = result; polarizationResources = resources;
      polarizationDisplayKey = `${result.requestId}:${polarizationLimits.min}:${polarizationLimits.max}:${polarizationScale}:${polarizationGain}`;
      committed = true; polarizationPlayback.bind(updatePolarizationMarkers); scene!.setFrameCallback(time => polarizationPlayback.tick(time));
      showPolarizationPixel(result, 0, result.readout.row, result.readout.column);
    },
    dispose() {
      if (closed) return; closed = true; prepared.dispose(); resources.dispose();
      if (committed) { host.replaceChildren(...oldNodes); polarizationPublished = previous; polarizationResources = oldResources; polarizationDisplayKey = previousKey;
        polarizationPlayback.detach(); if (previous && oldResources) polarizationPlayback.bind(updatePolarizationMarkers); }
    },
    finalize() { if (closed) return; closed = true; prepared.finalize(); oldResources?.dispose(); },
  };
}
function renderPolarizationSample(state: PolarizationState): void {
  const result = polarizationPublished; if (!result) return;
  const stage = result.stages.find(item => item.stage_id === state.selectedStage) ?? result.stages[0];
  const trajectory = polarizationResources?.trajectories.find(item => item.stageId === stage.stage_id);
  element<HTMLSelectElement>('pl-stage').value = stage.stage_id;
  element('pl-sample').textContent = `固定複數樣本 request=${result.requestId}\nstage=${stage.stage_id}; row=${result.readout.row}, column=${result.readout.column}\nx=${result.readout.x_m} m; y=${result.readout.y_m} m\nUx={re:${stage.sample.x.re}, im:${stage.sample.x.im}}\nUy={re:${stage.sample.y.re}, im:${stage.sample.y.im}}`;
  element('pl-stage-note').textContent = `${trajectory?.dark ? 'no defined polarization state at this sample（精確零）' : trajectory?.displayLimited ? '非零樣本 · display-scale/precision limitation；原值保留。' : '非零樣本 · 保留共同相位。'} actual norm=${stage.norm}; signed Δ=${stage.delta_norm}; adjacent ratio=${stage.adjacent_transmission_ratio}; original-incident ratio=${stage.incident_transmission_ratio}. null=未定義。比例不證明因果或硬體效率。`;
  for (const card of element('pl-trajectories').children) card.classList.toggle('selected', card.querySelector('svg')?.getAttribute('data-stage-id') === stage.stage_id);
}
function renderPolarizationFields(state: PolarizationState): void {
  const make = (parent: HTMLElement, path: string, label: string, integer = false) => {
    const wrapper = document.createElement('label'); wrapper.className = 'number-field'; wrapper.textContent = label;
    const input = document.createElement('input'); input.type = 'text'; input.inputMode = integer ? 'numeric' : 'decimal';
    input.dataset.plPath = path; input.dataset.testid = `pl-edit-${path.replaceAll('.', '-')}`;
    input.addEventListener('input', () => {
      if (shouldEditNumeric(input, 'polarization', path, polarizationController.state)) void polarizationController.edit(path, input.value, integer);
    }); wrapper.append(input); parent.append(wrapper);
  };
  if (polarizationFieldsKey !== state.candidate.source.kind) {
    polarizationFieldsKey = state.candidate.source.kind; const parent = element('pl-fields'); parent.replaceChildren();
    for (const [path, label, integer] of [['wavelength_m', 'λ / m'], ['grid.nx', 'Nx (max128)', true], ['grid.ny', 'Ny (max128)', true],
      ['grid.dx', 'dx / m'], ['grid.dy', 'dy / m'], ['source.amplitude', 'scalar amplitude'], ['source.phase_rad', 'source phase / rad'],
      ['coefficients.x.re', 'coefficient x real'], ['coefficients.x.im', 'coefficient x imaginary'], ['coefficients.y.re', 'coefficient y real'], ['coefficients.y.im', 'coefficient y imaginary'],
      ['readout.row', 'fixed sample row', true], ['readout.column', 'fixed sample column', true]] as [string, string, boolean?][]) make(parent, path, label, integer);
    if (state.candidate.source.kind === 'gaussian') for (const [path, label] of [['source.waist_radius_m', 'waist radius / m'], ['source.center_x_m', 'center x / m'], ['source.center_y_m', 'center y / m']]) make(parent, path, label);
  }
  const index = state.candidate.elements.findIndex(item => item.id === state.selection), selected = state.candidate.elements[index];
  const inspectorKey = `${state.selection}:${index}:${selected?.kind}`;
  if (polarizationInspectorKey !== inspectorKey) {
    polarizationInspectorKey = inspectorKey; const parent = element('pl-inspector'); parent.replaceChildren();
    const heading = document.createElement('h3'); heading.textContent = selected?.id ?? 'source'; parent.append(heading);
    if (selected) { make(parent, `elements.${index}.axis_angle_rad`, 'axis θ / rad（+x toward +y）');
      if (selected.kind === 'linear_retarder') make(parent, `elements.${index}.retardance_rad`, 'perpendicular phase δ / rad'); }
  }
  element<HTMLSelectElement>('pl-source-kind').value = state.candidate.source.kind;
  for (const input of document.querySelectorAll<HTMLInputElement>('[data-pl-path]')) {
    const path = input.dataset.plPath!, invalid = Object.hasOwn(state.invalidEdits, path); input.classList.toggle('invalid', invalid); input.setAttribute('aria-invalid', String(invalid));
    if (document.activeElement === input) continue; let value: unknown = state.candidate;
    for (const key of path.split('.')) value = (value as Record<string, unknown>)[key];
    input.value = invalid ? state.invalidEdits[path] : String(value);
    paintNumeric(input, 'polarization', path, state, invalid);
  }
  const list = element('pl-elements'); list.replaceChildren();
  const source = document.createElement('button'); source.textContent = 'source / coefficients'; source.className = 'component'; source.addEventListener('click', () => polarizationController.select('source')); list.append(source);
  for (const [i, item] of state.candidate.elements.entries()) {
    const button = document.createElement('button'); button.className = `component${state.selection === item.id ? ' selected' : ''}`;
    button.dataset.testid = `pl-select-${item.id}`; button.textContent = `${i + 1}. ${item.id} · ${item.kind}\nθ=${item.axis_angle_rad} rad${item.kind === 'linear_retarder' ? `; δ=${item.retardance_rad} rad` : ''}`;
    button.addEventListener('click', () => polarizationController.select(item.id)); list.append(button);
  }
  element<HTMLButtonElement>('pl-add').disabled = state.candidate.elements.length >= 8;
  element<HTMLButtonElement>('pl-delete').disabled = index < 0; element<HTMLButtonElement>('pl-up').disabled = index <= 0;
  element<HTMLButtonElement>('pl-down').disabled = index < 0 || index >= state.candidate.elements.length - 1;
  element<HTMLButtonElement>('pl-qwp').disabled = selected?.kind !== 'linear_retarder'; element<HTMLButtonElement>('pl-hwp').disabled = selected?.kind !== 'linear_retarder';
}
function renderPolarizationSweep(sweep: DecodedPolarizationSweep | null, fresh: boolean): void {
  element('pl-sweep-status').textContent = !sweep ? '尚未完成掃描' : `${fresh ? '' : '先前掃描 · 已過期 · '}${sweep.status === 'complete' ? '完成' : 'FAILED / PARTIAL'} ${sweep.completedCount}/13${sweep.error ? ` · HTTP ${sweep.httpStatus} · ${sweep.error.message}` : ''}`;
  const svg = element<SVGSVGElement & HTMLElement>('pl-sweep-chart'), body = element('pl-sweep-rows'); svg.replaceChildren(); body.replaceChildren();
  if (!sweep) return;
  element('pl-sweep-identity').textContent = `request=${sweep.requestId}\nSHA=${sweep.experimentSha256}\nsweep SHA=${sweep.sweepSha256}\nselected=${sweep.selectedElementId}\noriginal=${JSON.stringify(sweep.experiment)}`;
  const ns = 'http://www.w3.org/2000/svg'; const add = (tag: string, attributes: Record<string, string>, text?: string) => {
    const node = document.createElementNS(ns, tag); Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
    if (text) node.textContent = text; svg.append(node); return node;
  };
  add('path', { d: 'M55 20V190H725', fill: 'none', stroke: '#8ba2b1' });
  add('text', { x: '55', y: '218' }, '−π/2 rad'); add('text', { x: '665', y: '218' }, '+π/2 rad');
  add('text', { x: '60', y: '16' }, 'original-incident ratio · common 0..1 display range · raw table retained');
  let segment: string[] = [];
  const finish = () => { if (segment.length > 1) add('polyline', { points: segment.join(' '), stroke: '#087f89', fill: 'none', 'pointer-events': 'none' }); segment = []; };
  for (const row of sweep.rows) {
    const value = row.incident_transmission_ratio, x = 55 + row.index / 12 * 670;
    if (value !== null && value >= 0 && value <= 1) {
      const y = 190 - value * 170; segment.push(`${x},${y}`);
      const point = add('circle', { cx: String(x), cy: String(y), r: '4', fill: '#087f89', tabindex: '0', role: 'button', 'data-testid': `pl-sweep-point-${row.index}` });
      point.addEventListener('click', () => polarizationController.selectSweepPoint(row.index));
      point.addEventListener('keydown', event => { if ((event as KeyboardEvent).key === 'Enter') polarizationController.selectSweepPoint(row.index); });
    } else finish();
    const tr = document.createElement('tr'); tr.dataset.index = String(row.index);
    for (const item of [row.index, row.axis_angle_rad, row.final_norm, value, row.total_delta]) { const td = document.createElement('td'); td.textContent = item === null ? 'null（未定義）' : String(item); tr.append(td); }
    tr.addEventListener('click', () => polarizationController.selectSweepPoint(row.index)); body.append(tr);
  }
  finish(); // No connection or invented marker beyond the genuine completed prefix.
}
function renderPolarization(state: PolarizationState): void {
  if (disposed || applyingDocument || mode !== 'polarization') return;
  element('pl-status').textContent = state.status; element('pl-status').dataset.status = state.status;
  element('pl-error').textContent = state.error ?? ''; element('pl-error').hidden = !state.error;
  element('pl-render-error').textContent = state.renderError ?? ''; element('pl-render-error').hidden = !state.renderError;
  const ready = !!state.validatedDraft && !state.pendingValidation && !Object.keys(state.invalidEdits).length && !operationGate.busy;
  element<HTMLButtonElement>('pl-simulate').disabled = !ready;
  element<HTMLButtonElement>('pl-sweep').disabled = !ready || !state.candidate.elements.some(item => item.id === state.selection && item.kind === 'linear_polarizer');
  element<HTMLButtonElement>('pl-apply-angle').disabled = operationGate.busy || state.selectedSweepIndex === null;
  element<HTMLButtonElement>('pl-retry-display').disabled = !state.completedNumerical || !!state.active || !state.validatedDraft;
  renderPolarizationFields(state);
  try {
    if (!state.currentResult && !(state.renderError && polarizationPublished)) detachPolarizationPresentation();
    if (state.validatedDraft) scene?.updatePolarizationExperiment(state.validatedDraft, state.selection);
    if (state.currentResult && !state.renderError && polarizationDisplayKey !== `${state.currentResult.requestId}:${polarizationLimits.min}:${polarizationLimits.max}:${polarizationScale}:${polarizationGain}`) {
      const prepared = preparePolarizationPresentation(state.currentResult);
      try { prepared.commit(); prepared.finalize(); } catch (error) { prepared.dispose(); throw error; }
    }
    if (polarizationPublished) renderPolarizationSample(state);
  } catch (error) { reportPresentation(error); }
  element('bench-label').textContent = state.currentResult ? '同一參考平面 · 完整原提交結果' : '同一參考平面 · 尚無目前附加結果';
  const effective = polarizationResources;
  element('pl-color-info').textContent = `目前顯示共同強度色階 ${effective?.limits.min ?? polarizationLimits.min}..${effective?.limits.max ?? polarizationLimits.max} amplitude-unit²；共同振幅刻度 ${effective?.commonAmplitudeScale ?? polarizationScale}，手動顯示 gain=${effective?.gain ?? polarizationGain}。${state.renderError ? '新顯示設定未發布；原顯示與刻度保留。' : ''}不修改光學結果。`;
  element('pl-result-status').textContent = state.currentResult ? '目前提交 · 完整結果' : state.completedNumerical && state.renderError ? '數值完成 · 顯示失敗；原結果保留，未自動重算' : state.lastResult ? '先前結果已過期 · 原提交分開保留' : '尚未完成模擬';
  const previous = element('pl-previous-result'); previous.hidden = !state.lastResult || state.currentResult === state.lastResult;
  if (state.lastResult) element('pl-previous-spec').textContent = `原 request=${state.lastResult.requestId}\n${JSON.stringify(state.lastResult.experiment, null, 2)}\n原 stages=${JSON.stringify(state.lastResult.stages)}`;
  renderPolarizationSweep(state.lastSweep, state.currentSweep === state.lastSweep);
  const selected = state.lastSweep?.rows.find(row => row.index === state.selectedSweepIndex);
  element('pl-sweep-selected').textContent = selected ? `選取真正計算列（未重算）=${JSON.stringify(selected)}` : '';
}
function polarizationSnapshot(): object {
  const state = polarizationController.state;
  const ownership = ownedSnapshot();
  const transientEstimate = state.candidate.grid.nx >= 1 && state.candidate.grid.nx <= 128 && state.candidate.grid.ny >= 1 && state.candidate.grid.ny <= 128
    && Number.isInteger(state.candidate.grid.nx) && Number.isInteger(state.candidate.grid.ny)
    ? estimateOwnedOperation('polarization', state.candidate.grid, ownership.retainedBytes) : null;
  const summary = (result: DecodedPolarizationResult | null) => result ? { requestId: result.requestId, experimentSha256: result.experimentSha256,
    experiment: structuredClone(result.experiment), orderedStageIds: [...result.orderedStageIds], stages: structuredClone(result.stages),
    readout: { ...result.readout }, intensityMax: [...result.intensityMax], shape: [result.experiment.grid.ny, result.experiment.grid.nx] } : null;
  return { candidate: structuredClone(state.candidate), validatedDraft: state.validatedDraft ? structuredClone(state.validatedDraft) : null,
    status: state.status, pendingValidation: state.pendingValidation, invalidEdits: { ...state.invalidEdits }, revision: state.revision, attachmentEpoch: state.attachmentEpoch,
    selection: state.selection, selectedStage: state.selectedStage, active: state.active ? structuredClone(state.active) : null, error: state.error, renderError: state.renderError,
    currentResult: summary(state.currentResult), lastResult: summary(state.lastResult), completedNumerical: summary(state.completedNumerical),
    lastSweep: state.lastSweep ? structuredClone(state.lastSweep) : null, currentSweep: state.currentSweep ? structuredClone(state.currentSweep) : null,
    selectedSweepIndex: state.selectedSweepIndex, selectedPixel: polarizationSelectedPixel ? { ...polarizationSelectedPixel } : null,
    colorLimits: { ...(polarizationResources?.limits ?? polarizationLimits) }, requestedDisplay: { limits: { ...polarizationLimits }, commonAmplitudeScale: polarizationScale, gain: polarizationGain },
    animation: polarizationPlayback.snapshot(),
    retainedBytes: ownership.retainedBytes,
    memory: { persistentBytes: ownership.retainedBytes, transientBytes: transientEstimate?.peakOwnedBytes ?? null,
      persistentBudget: OWNED_PERSISTENT_BUDGET_BYTES, transientBudget: OWNED_TRANSIENT_BUDGET_BYTES, phases: transientEstimate },
    trajectories: polarizationResources?.trajectories.map(trajectory => ({ stageId: trajectory.stageId, sample: structuredClone(trajectory.sample), dark: trajectory.dark,
      displayLimited: trajectory.displayLimited, renderable: trajectory.renderable, rawMarker: trajectoryMarker(trajectory.sample, polarizationPlayback.tau),
      commonAmplitudeScale: polarizationResources!.commonAmplitudeScale, gain: polarizationResources!.gain })) ?? [],
    budget: { ...ownedSnapshot(), persistent: OWNED_PERSISTENT_BUDGET_BYTES, transient: OWNED_TRANSIENT_BUDGET_BYTES,
      transientEstimate, sweepTransientEstimate: transientEstimate ? estimateOwnedOperation('polarization', state.candidate.grid, ownership.retainedBytes, 'sweep') : null,
      phasePolicy: 'conservative reachable owned buffers, computed from current actual retention; not measured whole-tab/GPU peak',
      includes: 'deduplicated scientific buffers; bounded result metadata charges; scalar sweeps; actual canvas stores; retained texture sources; geometry attribute/index backing buffers; trajectory F64; phase-wise incoming/decode/preparation overlap',
      excludes: 'JS object/string overhead; renderer caches/framebuffer; GPU/driver; whole heap/tab/process' } };
}
for (const item of POLARIZATION_PRESETS) { const option = document.createElement('option'); option.value = item.id; option.textContent = item.label; element('pl-preset').append(option); }
for (const item of COEFFICIENT_PRESETS) { const option = document.createElement('option'); option.value = item.id; option.textContent = item.label; element('pl-coefficients-preset').append(option); }
element('pl-preset').addEventListener('change', () => { void polarizationController.replaceCandidate(polarizationPreset(element<HTMLSelectElement>('pl-preset').value)); });
element('pl-coefficients-preset').addEventListener('change', () => {
  const spec = structuredClone(polarizationController.state.candidate);
  spec.coefficients = structuredClone(COEFFICIENT_PRESETS.find(item => item.id === element<HTMLSelectElement>('pl-coefficients-preset').value)!.coefficients);
  void polarizationController.replaceCandidate(spec);
});
element('pl-source-kind').addEventListener('change', () => {
  const spec = structuredClone(polarizationController.state.candidate), { amplitude, phase_rad } = spec.source;
  spec.source = element<HTMLSelectElement>('pl-source-kind').value === 'uniform' ? { kind: 'uniform', amplitude, phase_rad }
    : { kind: 'gaussian', amplitude, phase_rad, waist_radius_m: 50e-6, center_x_m: 0, center_y_m: 0 };
  void polarizationController.replaceCandidate(spec);
});
element('pl-add').addEventListener('click', () => {
  const spec = structuredClone(polarizationController.state.candidate); if (spec.elements.length >= 8) return;
  let id: string; do { id = `element${nextPolarizationId++}`; } while (spec.elements.some(item => item.id === id));
  spec.elements.push(element<HTMLSelectElement>('pl-add-kind').value === 'linear_retarder'
    ? { id, kind: 'linear_retarder', axis_angle_rad: 0, retardance_rad: Math.PI / 2 } : { id, kind: 'linear_polarizer', axis_angle_rad: 0 });
  void polarizationController.replaceCandidate(spec); polarizationController.select(id);
});
element('pl-delete').addEventListener('click', () => {
  const spec = structuredClone(polarizationController.state.candidate), index = spec.elements.findIndex(item => item.id === polarizationController.state.selection);
  if (index < 0) return; spec.elements.splice(index, 1); void polarizationController.replaceCandidate(spec);
});
for (const [button, direction] of [['pl-up', -1], ['pl-down', 1]] as const) element(button).addEventListener('click', () => {
  const spec = structuredClone(polarizationController.state.candidate), index = spec.elements.findIndex(item => item.id === polarizationController.state.selection), next = index + direction;
  if (index < 0 || next < 0 || next >= spec.elements.length) return;
  [spec.elements[index], spec.elements[next]] = [spec.elements[next], spec.elements[index]]; void polarizationController.replaceCandidate(spec);
});
for (const [button, delta] of [['pl-qwp', Math.PI / 2], ['pl-hwp', Math.PI]] as const) element(button).addEventListener('click', () => {
  const index = polarizationController.state.candidate.elements.findIndex(item => item.id === polarizationController.state.selection && item.kind === 'linear_retarder');
  if (index >= 0) void polarizationController.edit(`elements.${index}.retardance_rad`, String(delta));
});
element('pl-simulate').addEventListener('click', () => { void polarizationController.simulate(); });
element('pl-sweep').addEventListener('click', () => { void polarizationController.runSweep(); });
element('pl-apply-angle').addEventListener('click', () => { void polarizationController.applySelectedAngleAndSimulate(); });
element('pl-retry-display').addEventListener('click', () => { polarizationController.retryPresentation(); });
element('pl-tau').addEventListener('change', () => { try { polarizationPlayback.pause(); polarizationPlayback.setTau(Number(element<HTMLInputElement>('pl-tau').value)); } catch (error) { notice(String(error)); } });
element('pl-play').addEventListener('click', () => { polarizationPlayback.playing ? polarizationPlayback.pause() : polarizationPlayback.play(); });
element('pl-reset').addEventListener('click', () => polarizationPlayback.reset());
function changePolarizationDisplay(): void {
  try {
    const next = { min: Number(element<HTMLInputElement>('pl-color-min').value), max: Number(element<HTMLInputElement>('pl-color-max').value) };
    const scale = Number(element<HTMLInputElement>('pl-amplitude-scale').value), gain = Number(element<HTMLInputElement>('pl-display-gain').value);
    validateColorLimits(next); validateDisplayScale(scale, gain); polarizationLimits = next; polarizationScale = scale; polarizationGain = gain;
    polarizationController.reportRenderFailure(null);
  } catch (error) { notice(String(error)); }
}
for (const id of ['pl-color-min', 'pl-color-max', 'pl-amplitude-scale', 'pl-display-gain']) element(id).addEventListener('change', changePolarizationDisplay);
element('pl-auto-color').addEventListener('click', () => {
  const result = polarizationController.state.currentResult; if (!result) return;
  const maximum = Math.max(...result.intensityMax); polarizationLimits = { min: 0, max: maximum > 0 ? maximum : 1 };
  element<HTMLInputElement>('pl-color-min').value = '0'; element<HTMLInputElement>('pl-color-max').value = String(polarizationLimits.max);
  polarizationController.reportRenderFailure(null);
});
polarizationController.setResultPreparer(preparePolarizationPresentation);
polarizationController.setOperationAdmission((kind, experiment) => admitOperation('polarization', experiment.grid, kind));

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

function documentContext() {
  return { mode, token: [controller.state.revision, controller.state.attachmentEpoch,
    twoPathController.state.revision, twoPathController.state.attachmentEpoch,
    polarizationController.state.revision, polarizationController.state.attachmentEpoch].join(':') };
}
function currentDocumentDraft() {
  const state = mode === 'sequential' ? controller.state : mode === 'two_path' ? twoPathController.state : polarizationController.state;
  if (!state.validatedDraft || state.pendingValidation || Object.keys(state.invalidEdits).length) return null;
  return { mode, experiment: state.validatedDraft, revision: state.revision, attachmentEpoch: state.attachmentEpoch };
}
function prepareDocumentApplication(validated: ValidatedDocument): () => void {
  const doc = validated.document;
  const commit = doc.mode === 'sequential'
    ? controller.prepareValidatedSettings(doc.experiment, validated.experimentSha256)
    : doc.mode === 'two_path'
      ? twoPathController.prepareValidatedSettings(doc.experiment, validated.experimentSha256)
      : polarizationController.prepareValidatedSettings(doc.experiment, validated.experimentSha256);
  return () => {
    applyingDocument = true;
    try {
      commit();
      mode = doc.mode;
      // No DOM or presentation allocation occurs inside the scientific commit.
    } finally { applyingDocument = false; }
  };
}
function renderModeHelp(): void {
  document.querySelector<HTMLElement>('.bench-help')!.textContent = mode === 'polarization'
    ? 'Orbit / Pan / Zoom 與選取只改顯示；同一參考平面，示意間距無光學作用，沒有 z 拖曳。'
    : mode === 'two_path'
      ? 'Orbit / Pan / Zoom 與選取只改顯示；固定展開光路不可拖曳。虛線僅為指引。'
      : '左鍵旋轉（Orbit）・右鍵平移（Pan）・滾輪縮放（Zoom）・點擊選取；橘色控制球僅沿 z 軸拖曳。';
}
function presentDocumentApplication(): void {
  // Presentation is subsequent to the coherent settings commit and fails separately.
  app!.dataset.mode = mode; element<HTMLSelectElement>('mode').value = mode;
  try {
    detachPolarizationPresentation(); scene?.updateResult(null, limits); scene?.detachDualResult();
    dualPublished = null; dualSelectedPixel = null; dualDisplayKey = ''; displayedResult = null; displayKey = '';
    selectedPixel = null; priorDisplayKey = ''; inspectorKey = ''; dualFieldsKey = '';
    polarizationFieldsKey = ''; polarizationInspectorKey = '';
    for (const canvas of document.querySelectorAll<HTMLCanvasElement>('#intensity, #tp-result-area canvas')) { canvas.width = 0; canvas.height = 0; }
    element('intensity-holder').hidden = true; element('tp-current-content').replaceChildren(); element('tp-prior-images').replaceChildren();
    element('pick-choices').replaceChildren(); renderModeHelp();
    if (mode === 'sequential') render(controller.state);
    else if (mode === 'two_path') renderTwoPath(twoPathController.state);
    else renderPolarization(polarizationController.state);
  } catch (error) { reportPresentation(error); }
}
const modeLabel: Record<BenchMode, string> = { sequential: '順序光路', two_path: '兩路干涉', polarization: '理想偏振' };
function renderDocuments(): void {
  if (!documents || disposed) return;
  const state = documents.state, metadata = state.metadata[mode];
  const title = element<HTMLInputElement>('doc-title'), notes = element<HTMLTextAreaElement>('doc-notes');
  if (document.activeElement !== title) title.value = metadata.title;
  if (document.activeElement !== notes) notes.value = metadata.notes;
  const errors = [state.error, state.metadataErrors[mode]].filter(Boolean);
  element('doc-error').textContent = errors.join(' · '); element('doc-error').hidden = errors.length === 0;
  const labels = { idle: '設定檔只保存設定；模擬需要另行提交。', reading: '讀取設定檔中', validating: '驗證設定檔中',
    preview: '設定已驗證；請檢查並確認取代。', download_prepared: '下載已準備', download_requested: '已要求下載',
    restored: '設定已還原，尚未模擬', error: '設定檔未完成；請檢查錯誤。' };
  const current = mode === 'sequential' ? controller.state.currentResult : mode === 'two_path' ? twoPathController.state.currentResult : polarizationController.state.currentResult;
  element('doc-status').textContent = state.status === 'restored' && current
    ? '設定已還原；已有另行提交的模擬結果。' : labels[state.status];
  element('doc-status').dataset.status = state.status;
  element<HTMLButtonElement>('doc-export').disabled = !currentDocumentDraft() || !!state.metadataErrors[mode];
  const prepared = state.preparedDownload, link = element<HTMLAnchorElement>('doc-download');
  element('doc-download-area').hidden = !prepared;
  if (prepared) {
    link.href = prepared.url; link.download = prepared.filename;
    element('doc-download-label').textContent = `${modeLabel[prepared.document.mode]} · 已擷取的有效草稿版本 ${prepared.revision}（設定檔不包含結果）`;
  } else { link.removeAttribute('href'); link.removeAttribute('download'); }
  const preview = state.preview;
  element('doc-preview').hidden = !preview;
  element<HTMLInputElement>('doc-ack').checked = state.acknowledged;
  element<HTMLButtonElement>('doc-apply').disabled = !preview || !state.acknowledged || state.pending || operationGate.busy;
  if (preview) {
    const doc = preview.document, exp = doc.experiment;
    element('doc-preview-text').textContent = `模式：${modeLabel[doc.mode]}\n標題：${doc.metadata.title}\n備註：${doc.metadata.notes}\n` +
      `網格：${exp.grid.ny} × ${exp.grid.nx}；dx=${exp.grid.dx} m；dy=${exp.grid.dy} m\n波長：${exp.wavelength_m} m\n` +
      `完整設定（SI / rad；尚未模擬）：\n${JSON.stringify(exp, null, 2)}`;
  } else element('doc-preview-text').textContent = '';
}
documents = new ExperimentDocumentController({ context: documentContext, currentValidDraft: currentDocumentDraft,
  busy: () => operationGate.busy, prepareApply: prepareDocumentApplication,
  reservedBytes: () => scientificReservations,
  retainedBytes: () => { const own = ownedSnapshot(); return own.retainedBytes - own.documentBytes; } });
documents.subscribe(renderDocuments);
for (const id of ['doc-title', 'doc-notes']) element(id).addEventListener('input', () => {
  documents!.setMetadata(mode, { title: element<HTMLInputElement>('doc-title').value, notes: element<HTMLTextAreaElement>('doc-notes').value });
});
element('doc-export').addEventListener('click', () => { void documents!.exportCurrent(); });
element('doc-file').addEventListener('change', () => {
  const input = element<HTMLInputElement>('doc-file'), file = input.files?.[0]; input.value = '';
  if (file) void documents!.importFile(file);
});
element('doc-cancel').addEventListener('click', () => documents!.cancelImport());
element('doc-ack').addEventListener('change', () => documents!.acknowledgeReplacement(element<HTMLInputElement>('doc-ack').checked));
element('doc-apply').addEventListener('click', () => { if (documents!.applyImport()) { presentDocumentApplication(); renderDocuments(); } });
element('doc-download').addEventListener('click', () => documents!.markDownloadRequested());
element('doc-dismiss').addEventListener('click', () => documents!.dismissDownload());
element('mode').addEventListener('change', () => {
  controller.deactivate(); twoPathController.deactivate(); polarizationController.deactivate(); detachPolarizationPresentation();
  scene?.updateResult(null, limits); scene?.detachDualResult();
  const chosen = element<HTMLSelectElement>('mode').value;
  mode = chosen === 'polarization' ? 'polarization' : chosen === 'two_path' ? 'two_path' : 'sequential'; app!.dataset.mode = mode;
  dualPublished = null; dualSelectedPixel = null; dualDisplayKey = ''; displayedResult = null; displayKey = '';
  for (const canvas of document.querySelectorAll<HTMLCanvasElement>('#tp-result-area canvas')) { canvas.width = 0; canvas.height = 0; }
  element('tp-current-content').replaceChildren(); element('tp-prior-images').replaceChildren(); priorDisplayKey = '';
  const legacyCanvas = element<HTMLCanvasElement>('intensity'); legacyCanvas.width = 0; legacyCanvas.height = 0;
  element('intensity-holder').hidden = true;
  renderModeHelp();
  element('pick-choices').replaceChildren();
  if (mode === 'two_path') { renderTwoPath(twoPathController.state); void twoPathController.activate(); }
  else if (mode === 'polarization') { renderPolarization(polarizationController.state); void polarizationController.activate(); }
  else { render(controller.state); void controller.activate(); }
  documents!.contextChanged(); renderDocuments();
});
twoPathController.setResultPreparer(prepareDualPresentation);
controller.subscribe(render); twoPathController.subscribe(renderTwoPath); polarizationController.subscribe(renderPolarization);
for (const actor of [controller, twoPathController, polarizationController]) actor.subscribe(() => {
  if (!applyingDocument && !documents!.isApplying) { documents!.contextChanged(); renderDocuments(); }
});
operationGate.subscribe(() => {
  if (!operationGate.busy) scientificReservations = { persistent: 0, transient: 0 };
  renderDocuments();
  if (mode === 'sequential') element<HTMLButtonElement>('simulate').disabled = operationGate.busy || !controller.state.validatedDraft || controller.state.pendingValidation || !!Object.keys(controller.state.invalidEdits).length;
  else if (mode === 'polarization') {
    const state = polarizationController.state, ready = !operationGate.busy && !!state.validatedDraft && !state.pendingValidation && !Object.keys(state.invalidEdits).length;
    element<HTMLButtonElement>('pl-simulate').disabled = !ready;
    element<HTMLButtonElement>('pl-sweep').disabled = !ready || !state.candidate.elements.some(item => item.id === state.selection && item.kind === 'linear_polarizer');
  } else {
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
    polarization: polarizationSnapshot(),
    ownedMemory: ownedSnapshot(),
    documents: documents ? { state: structuredClone(documents.state), ownership: documents.ownershipSnapshot() } : null,
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
window.addEventListener('pagehide', () => { disposed = true; documents?.dispose(); polarizationPlayback.detach(); polarizationResources?.dispose(); scene?.dispose(); }, { once: true });
