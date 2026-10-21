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
import { type SupportedBenchMode, type SupportedValidatedDocument } from './experiment_documents';
import { PolarizedTwoPathController, type PolarizedTwoPathState } from './polarized_two_path_state';
import type { DecodedPolarizedTwoPathResult, DecodedPolarizedTwoPathSweep } from './polarized_two_path_contracts';
import { POLARIZED_TWO_PATH_PRESETS, polarizedTwoPathPreset } from './polarized_two_path_presets';
import { ownedScientificBytes4, estimatePolarizedTwoPathOperation, preparePolarizedTwoPathResources,
  type PolarizedTwoPathResources } from './polarized_two_path_display';
import { R03Controller } from './r03_fig2a_state';
import { R03Workspace } from './r03_fig2a_workspace';
import { WaveFieldController } from './wave_field_state';
import { WaveFieldWorkspace } from './wave_field_workspace';
import { W1_EXAMPLE } from './wave_field_contracts';
import { GeometricRoutingController } from './geometric_routing_state';
import { GeometricRoutingWorkspace } from './geometric_routing_workspace';
import { W2_PRESETS } from './geometric_routing_contracts';

const app = document.querySelector<HTMLDivElement>('#app');
if (!app) throw new Error('Application container is missing.');
app.innerHTML = `
  <header class="app-header"><div><span class="eyebrow">OPEN HOLOGRAPHIC LAB / FOUR EXPERIMENT MODES</span><h1>Open Holographic Lab</h1></div>
    <div class="header-detail">Monochromatic · Scalar · Aligned Forward Optics<br><span>Local Operation / Explicit Submission</span></div></header>
  <main>
    <nav class="workspace-navigation" aria-label="Workspaces"><button id="ordinary-workspace" data-testid="ordinary-workspace" class="selected">Optical Experiments</button>
      <button id="research-workspace" data-testid="research-workspace">Ideal Statistical Polarization</button>
      <button id="geometric-routing-workspace" data-testid="geometric-routing-workspace">Geometric Routing</button></nav>
    <section class="toolbar" aria-label="Experiment Controls">
      <label>Mode <select id="mode" data-testid="mode"><option value="sequential">Sequential Optics</option><option value="two_path">Two-Path Interference</option><option value="polarization">Jones Polarization</option><option value="polarized_two_path">Polarized Interference</option></select></label>
      <label class="sequential-only">Load Preset <select id="preset" data-testid="preset"></select></label>
      <button id="simulate" class="primary sequential-only" data-testid="simulate">Simulate</button>
      <button id="w1-view" class="sequential-only" data-testid="w1-view" aria-pressed="false">Computed Sections</button>
      <output id="status" class="sequential-only" data-testid="status" aria-live="polite"></output>
      <button id="tp-simulate" class="primary two-path-only" data-testid="tp-simulate">Simulate</button>
      <button id="tp-sweep" class="two-path-only" data-testid="tp-sweep">Phase Sweep (17 points)</button>
      <output id="tp-status" class="two-path-only" data-testid="tp-status" aria-live="polite"></output>
      <button id="pl-simulate" class="primary polarization-only" data-testid="pl-simulate">Simulate</button>
      <button id="pl-sweep" class="polarization-only" data-testid="pl-sweep">Analyzer Sweep (13 points)</button>
      <output id="pl-status" class="polarization-only" data-testid="pl-status" aria-live="polite"></output>
      <button id="pt-simulate" class="primary polarized-two-path-only" data-testid="pt-simulate">Simulate</button>
      <button id="pt-sweep" class="polarized-two-path-only" data-testid="pt-sweep">Phase Sweep (17 points)</button>
      <output id="pt-status" class="polarized-two-path-only" data-testid="pt-status" aria-live="polite"></output>
    </section>
    <details class="panel release-panel"><summary>Release Results · Keep Settings and Documents</summary>
      <p>Removes current and previous results, sweeps, readouts, and images across all modes. Preserves experiment drafts, invalid input text, camera views, import previews, and prepared settings downloads. Unavailable during computation.</p>
      <button id="release-results" data-testid="release-results">Release Results</button>
      <output id="release-status" data-testid="release-status" aria-live="polite"></output></details>
    <section id="r03-workspace" data-testid="r03-workspace" hidden></section>
    <p id="error" class="error" data-testid="error" role="alert" hidden></p>
    <p id="render-error" class="error" data-testid="render-error" role="alert" hidden></p>
    <details id="documents" class="panel document-panel" data-testid="documents">
      <summary data-testid="doc-toggle">Experiment Settings · Export Draft / Import Settings</summary>
      <p class="muted">Each file stores settings for one experiment, without results or sweeps. Drafts are not saved automatically; export them to keep a copy.</p>
      <div class="document-fields">
        <label>Document Title <input id="doc-title" data-testid="doc-title" type="text" autocomplete="off"></label>
        <label>Notes <textarea id="doc-notes" data-testid="doc-notes" rows="2"></textarea></label>
      </div>
      <div class="document-actions">
        <button id="doc-export" data-testid="doc-export">Export Valid Draft</button>
        <label>Import Settings <input id="doc-file" data-testid="doc-file" type="file" accept=".json,application/json"></label>
        <button id="doc-cancel" data-testid="doc-cancel">Cancel Import</button>
      </div>
      <output id="doc-status" data-testid="doc-status" aria-live="polite"></output>
      <p id="doc-error" data-testid="doc-error" class="error" role="alert" hidden></p>
      <div id="doc-download-area" data-testid="doc-download-area" hidden><p id="doc-download-label"></p>
        <a id="doc-download" data-testid="doc-download">Download Settings</a>
        <button id="doc-dismiss" data-testid="doc-dismiss">Dismiss Download Link</button>
      </div>
      <div id="doc-preview" data-testid="doc-preview" hidden>
        <h3>Settings Preview</h3><pre id="doc-preview-text" data-testid="doc-preview-text"></pre>
        <label class="document-ack"><input id="doc-ack" data-testid="doc-ack" type="checkbox">I understand that this replaces the mode's current settings, including edits that have not been exported.</label>
        <button id="doc-apply" data-testid="doc-apply" class="primary" disabled>Replace Settings and Apply</button>
      </div>
    </details>
    <section id="w2-controls" data-testid="w2-controls" hidden></section>
    <section class="workspace">
      <section id="w2-workspace" data-testid="w2-workspace" hidden></section>
      <aside class="panel components"><h2>Optical Train</h2><p class="muted">Elements act in the listed order. Distinct IDs are preserved at shared positions.</p>
        <div id="components" data-testid="components"></div>
        <div class="add-controls"><select id="add-kind" data-testid="add-kind" aria-label="Element Type to Add">
          <option value="thin_lens">Thin Lens</option><option value="circular_aperture">Circular Aperture</option><option value="rectangular_aperture">Rectangular Aperture</option></select>
          <button id="add" data-testid="add">Add Element</button><button id="delete" data-testid="delete">Delete Selected Element</button></div>
        <details class="sampling" open><summary>Sampling and Wavelength</summary><div id="general-fields"></div></details>
      </aside>
      <aside class="panel two-path-controls two-path-only"><h2>Two-Path Parameters</h2>
        <label>Preset <select id="tp-preset" data-testid="tp-preset"></select></label>
        <label>Source <select id="tp-source-kind" data-testid="tp-source-kind"><option value="uniform">Uniform</option><option value="gaussian">Gaussian</option></select></label>
        <div id="tp-fields" class="tp-fields"></div>
        <div class="phase-buttons"><button id="tp-phase-0" data-testid="tp-phase-0">0 rad</button><button id="tp-phase-halfpi" data-testid="tp-phase-halfpi">π/2 rad</button><button id="tp-phase-pi" data-testid="tp-phase-pi">π rad</button></div>
        <p id="tp-phase-note" class="muted"></p><p class="muted">Edits validate the draft only. Simulations and sweeps require separate submissions. Browser phase −0 is represented as +0; nonzero phases are not wrapped.</p>
      </aside>
      <aside class="panel polarization-only polarization-controls"><h2>Input and Ordered Elements</h2>
        <label>Preset <select id="pl-preset" data-testid="pl-preset"></select></label>
        <label>Source <select id="pl-source-kind" data-testid="pl-source-kind"><option value="uniform">Uniform</option><option value="gaussian">Gaussian at waist</option></select></label>
        <label>Complex Coefficient Preset <select id="pl-coefficients-preset" data-testid="pl-coefficients-preset"></select></label>
        <div id="pl-fields"></div><div id="pl-elements" data-testid="pl-elements"></div>
        <div class="add-controls"><select id="pl-add-kind" data-testid="pl-add-kind" aria-label="Polarization Element Type"><option value="linear_polarizer">Linear Polarizer</option><option value="linear_retarder">Linear Retarder</option></select>
          <button id="pl-add" data-testid="pl-add">Add Element</button><button id="pl-delete" data-testid="pl-delete">Delete Selected Element</button>
          <button id="pl-up" data-testid="pl-up">Move Selected Earlier</button><button id="pl-down" data-testid="pl-down">Move Selected Later</button></div>
      </aside>
      <aside class="panel polarized-two-path-only pt-controls"><h2>Polarized Interference · Input and Settings</h2>
        <label>Preset <select id="pt-preset" data-testid="pt-preset"></select></label>
        <label>Source <select id="pt-source-kind" data-testid="pt-source-kind"><option value="uniform">Uniform</option><option value="gaussian">Gaussian</option></select></label>
        <label>Complex Coefficient Preset <select id="pt-coefficients-preset" data-testid="pt-coefficients-preset"></select></label>
        <div id="pt-fields"></div>
        <label class="document-ack"><input type="checkbox" id="pt-analyzer-enabled" data-testid="pt-analyzer-enabled">Apply the Same Downstream Analyzer to Both Outputs</label>
        <div class="phase-buttons"><button id="pt-phase-0" data-testid="pt-phase-0">0 rad</button><button id="pt-phase-halfpi" data-testid="pt-phase-halfpi">π/2 rad</button><button id="pt-phase-pi" data-testid="pt-phase-pi">π rad</button></div>
        <p class="muted">The source is sampled at z=0; its Gaussian waist position may be positive or negative. Coefficients are not normalized. The arm 1 extra phase acts on both x/y components. The analyzer angle is retained when disabled.</p>
      </aside>
      <section class="bench-panel"><div class="bench-heading"><h2>3D Optical Bench</h2><span id="bench-label">Awaiting Draft Validation</span></div>
        <div id="bench" data-testid="bench-host"></div>
        <div id="w1-bench-controls" class="w1-bench-controls" data-testid="w1-bench-controls" hidden></div>
        <div class="camera-controls" aria-label="Camera Controls"><button id="reset-view" data-testid="reset-view">Reset View</button>
          <button id="zoom-in" data-testid="zoom-in" aria-label="Zoom In">＋</button><button id="zoom-out" data-testid="zoom-out" aria-label="Zoom Out">−</button>
          <button data-pan="-1,0" data-testid="pan-left" aria-label="Pan Left">←</button><button data-pan="1,0" aria-label="Pan Right">→</button>
          <button data-pan="0,1" aria-label="Pan Up">↑</button><button data-pan="0,-1" aria-label="Pan Down">↓</button></div>
        <p class="bench-help">Left-drag to orbit · Right-drag to pan · Scroll to zoom · Click to select<br>
          Orange handles drag along z only. Release to validate; invalid positions are rejected. Dashed lines are axis guides.</p>
        <output id="notice" data-testid="notice" aria-live="polite"></output>
        <div id="pick-choices" aria-label="Overlapping Element Selection"></div>
        <p class="scale-note">Schematic scale: 1 transverse unit = 1 mm; 1 longitudinal unit = 10 mm. Lens housings do not define a physical aperture.</p>
        <p class="w2-bench-caption">Uniform SI geometry · +Y up · Paths end at calculated terminal points<br>Line thickness is a visibility aid; housings do not obstruct rays.</p>
      </section>
      <aside class="panel inspector"><h2>Element Properties</h2><div id="inspector" data-testid="inspector"></div>
        <p class="muted">Edits validate the draft only. Press Simulate for a new result. Camera views and color limits do not change the experiment.</p></aside>
      <aside class="panel two-path-note two-path-only"><h2>Ideal Unfolded Schematic</h2><div id="tp-topology"></div>
        <p class="muted">Dashed lines are guides, not a calculated volume beam. Displayed lengths and spacing identify elements; only the numerical L₀/L₁ values govern propagation.</p>
        <p class="muted">Outputs are measured immediately after B†. Display separation adds no propagation. Both outputs use the same transverse coordinates, without mirror-reflection flips.</p>
        <p class="muted">The extra phase is an independent arm 1 phase. Propagation already includes carrier phase and diffraction; no second carrier or mirror-displacement rule is added.</p></aside>
      <aside class="panel polarization-only"><h2>Selected Element Properties</h2><div id="pl-inspector"></div>
        <button id="pl-qwp" data-testid="pl-qwp">QWP: δ=π/2 rad</button><button id="pl-hwp" data-testid="pl-hwp">HWP: δ=π rad</button>
        <p class="muted">Ideal ordered actions share one reference plane. Schematic spacing and housings add no propagation, thickness, or optical phase. The Gaussian waist position is fixed at zero; there is no physical z control.</p>
        <p class="muted">x/y are polarization components, not optical ports. Coefficients are not automatically normalized; numerical inputs preserve full radian and SI values. Edits validate only; submit explicitly to calculate.</p></aside>
      <aside class="panel polarized-two-path-only pt-arm-controls"><h2>Ordered Terminal Actions in Each Arm</h2><div id="pt-arms"></div><div id="pt-topology"></div>
        <p class="muted">Each arm propagates once, then applies up to two listed actions in order. QWP/HWP presets set only the retarder δ. Schematic positions add no propagation, reflection, or phase.</p>
        <p class="muted">B → arm 0/1 → B†. Both outputs share transverse coordinates. The 3D view shows the selected raw or analyzed port pair; the panel retains all available images.</p></aside>
    </section>
    <section id="w1-workspace" class="w1-workspace sequential-only" data-testid="w1-workspace"></section>
    <section class="result-panel panel sequential-only"><div class="result-heading"><h2>Observation Results</h2><strong id="result-status" data-testid="result-status">No Simulation Submitted</strong></div>
      <div class="results"><div><div class="color-controls"><label>Display Minimum <input id="color-min" data-testid="color-min" type="text" inputmode="decimal" value="0"></label>
          <label>Display Maximum <input id="color-max" data-testid="color-max" type="text" inputmode="decimal" value="10"></label>
          <button id="auto-color" data-testid="auto-color">Auto Range (No Recalculation)</button></div>
        <p id="color-info" data-testid="color-info">Shared Range 0–10 amplitude-unit²</p><p id="color-error" class="error" hidden></p>
        <div id="intensity-holder" class="intensity-holder" hidden><canvas id="intensity" data-testid="intensity-canvas" aria-label="Raw Intensity Grayscale"></canvas></div>
        <p id="pixel-readout" data-testid="pixel-readout">Click the intensity image or 3D observation plane to inspect a raw float64 pixel.</p>
      </div><div class="result-details"><p id="result-identity" data-testid="result-identity" class="monospace">—</p>
        <p id="result-spec" data-testid="result-spec">—</p><p id="raw-max" data-testid="raw-max">—</p>
        <p id="saturation" data-testid="saturation" class="warning" hidden></p>
        <label>Stage <select id="stage" data-testid="stage"></select></label>
        <p id="stage-note" data-testid="stage-note">The stage table appears after a completed simulation.</p>
        <div class="table-scroll"><table><thead><tr><th>Stage</th><th>z / mm</th><th>norm</th><th>Δnorm</th><th>Ratio</th></tr></thead><tbody id="stages" data-testid="stages"></tbody></table></div>
        <p class="muted">norm: amplitude-unit²·m². Ratios undefined for zero incident norm are shown as null.</p></div></div>
    </section>
    <section id="tp-result-area" class="result-panel panel two-path-only">
      <div class="result-heading"><h2>Immediate Two-Port Outputs</h2><strong id="tp-result-status" data-testid="tp-result-status">No Simulation Submitted</strong></div>
      <p id="tp-error" data-testid="tp-error" class="error" hidden></p><p id="tp-render-error" data-testid="tp-render-error" class="error" hidden></p>
      <div class="color-controls"><label>Shared Minimum <input id="tp-color-min" data-testid="tp-color-min" value="0"></label><label>Shared Maximum <input id="tp-color-max" data-testid="tp-color-max" value="1"></label>
        <button id="tp-auto-color" data-testid="tp-auto-color">Shared Auto Range (No Recalculation)</button></div>
      <p id="tp-color-info" class="muted"></p><p id="tp-color-error" class="error" hidden></p>
      <div id="tp-current-content"></div>
      <details id="tp-previous-result" data-testid="tp-previous-result" hidden><summary>Previous Completed Result · Separate from Current Draft</summary><pre id="tp-previous-spec"></pre><div id="tp-prior-images" class="dual-images"></div></details>
      <p class="muted">Both ports share transverse coordinates. Norm is measured in amplitude-unit²·m², not watts. Tiny residuals and signed differences are preserved; ratios for zero input are null.</p>
    </section>
    <section class="panel result-panel two-path-only"><div class="result-heading"><h2>Calculated Phase Sweep</h2><strong id="tp-sweep-status" data-testid="tp-sweep-status">No Sweep Submitted</strong></div>
      <p class="muted">17 actual calculations, with separate calls at 0 and 2π. Clicking a marker inspects that row without simulating. Connecting lines are visual interpolation only.</p>
      <div class="color-controls"><label>Chart Shared Minimum <input id="tp-chart-min" value="0"></label><label>Chart Shared Maximum <input id="tp-chart-max" value="1"></label><button id="tp-chart-range">Apply Chart Range (No Recalculation)</button></div>
      <svg id="tp-sweep-chart" data-testid="tp-sweep-chart" viewBox="0 0 760 230" role="img" aria-label="Calculated Two-Port Input Ratios"></svg>
      <p id="tp-sweep-identity" class="monospace"></p><p id="tp-sweep-selected" class="monospace"></p>
      <button id="tp-simulate-phase" data-testid="tp-simulate-phase" disabled>Simulate Selected Phase (Original Sweep Source and Lengths)</button>
      <div class="table-scroll"><table><thead><tr><th>phase / rad</th><th>input norm</th><th>port 0 norm</th><th>port 1 norm</th><th>η0</th><th>η1</th><th>total ratio</th><th>total Δ</th></tr></thead><tbody id="tp-sweep-rows" data-testid="tp-sweep-rows"></tbody></table></div>
    </section>
    <section class="panel result-panel polarization-only" id="pl-result-area"><div class="result-heading"><h2>Jones Polarization · Calculated Fields and Fixed Samples</h2><strong id="pl-result-status" data-testid="pl-result-status">Not Submitted</strong></div>
      <p id="pl-error" data-testid="pl-error" class="error" hidden></p><p id="pl-render-error" data-testid="pl-render-error" class="error" hidden></p>
      <div class="color-controls"><label>Shared Intensity Minimum <input id="pl-color-min" data-testid="pl-color-min" value="0"></label><label>Shared Intensity Maximum <input id="pl-color-max" data-testid="pl-color-max" value="10"></label>
        <button id="pl-auto-color" data-testid="pl-auto-color">Shared Auto Range (No Recalculation)</button><button id="pl-retry-display" data-testid="pl-retry-display">Retry Display (No Recalculation)</button></div>
      <p id="pl-color-info" class="muted"></p><div id="pl-current-content"></div>
      <details id="pl-previous-result" data-testid="pl-previous-result" hidden><summary>Previous Result · Original Submission Kept Separate</summary><pre id="pl-previous-spec"></pre></details>
      <div class="color-controls"><label>Shared τ / rad <input id="pl-tau" data-testid="pl-tau" value="0"></label><button id="pl-play" data-testid="pl-play">Play / Pause τ</button><button id="pl-reset" data-testid="pl-reset">Pause and Reset τ=0</button>
        <label>Shared Amplitude Scale / amplitude-unit <input id="pl-amplitude-scale" data-testid="pl-amplitude-scale" value="1"></label><label>Display Gain (1..1e18)<input id="pl-display-gain" data-testid="pl-display-gain" value="1"></label></div>
      <p class="muted">View the transverse plane along +z: +x right, +y down, with equal axis scales. Re([Ux,Uy] exp(−iτ)) preserves common phase. τ is a dimensionless illustration, not a physical frame rate. Display gain changes presentation only; all stages share one scale.</p>
    </section>
    <section class="panel result-panel polarization-only"><div class="result-heading"><h2>Calculated Analyzer-Angle Sweep</h2><strong id="pl-sweep-status" data-testid="pl-sweep-status">No Sweep Submitted</strong></div>
      <p class="muted">13 complete sequence calculations, each starting from the original input. −90° and +90° are calculated separately. Selection does not recalculate; lines are visual interpolation only. On failure, only the completed prefix is shown.</p>
      <svg id="pl-sweep-chart" data-testid="pl-sweep-chart" viewBox="0 0 760 230" role="img" aria-label="Calculated Angle Sweep"></svg>
      <p id="pl-sweep-identity" data-testid="pl-sweep-identity" class="monospace"></p><p id="pl-sweep-selected" class="monospace"></p>
      <button id="pl-apply-angle" data-testid="pl-apply-angle" disabled>Apply Selected Angle and Simulate (Original Sweep Settings)</button>
      <div class="table-scroll"><table><thead><tr><th>index</th><th>θ / rad</th><th>final norm</th><th>Original-Incident Ratio</th><th>signed Δnorm</th></tr></thead><tbody id="pl-sweep-rows" data-testid="pl-sweep-rows"></tbody></table></div>
    </section>
    <section class="panel result-panel polarized-two-path-only" id="pt-result-area"><div class="result-heading"><h2>Polarized Interference · Raw and Analyzed Outputs</h2><strong id="pt-result-status" data-testid="pt-result-status">Not Submitted</strong></div>
      <p id="pt-error" data-testid="pt-error" class="error" hidden></p><p id="pt-render-error" data-testid="pt-render-error" class="error" hidden></p>
      <div class="color-controls"><label>Shared Intensity Minimum <input id="pt-color-min" data-testid="pt-color-min" value="0"></label><label>Shared Intensity Maximum <input id="pt-color-max" data-testid="pt-color-max" value="1"></label>
        <button id="pt-auto-color" data-testid="pt-auto-color">Auto Range All Images (No Recalculation)</button><button id="pt-retry-display" data-testid="pt-retry-display">Retry Complete Display (No Recalculation)</button>
        <label>3D Port-Pair View <select id="pt-view" data-testid="pt-view"><option value="raw">Raw</option><option value="analyzed">Analyzed</option></select></label></div>
      <p id="pt-color-info" class="muted"></p><div id="pt-current-content"></div>
      <details id="pt-previous-result" data-testid="pt-previous-result" hidden><summary>Previous Result · Original Submission Retained</summary><pre id="pt-previous-spec"></pre></details>
      <p class="muted">Intensity is raw float64. Norm uses amplitude-unit²·m², not watts. Original-incident and downstream transmission ratios use different denominators. null indicates an undefined zero-denominator ratio; signed losses and tiny residuals are not clipped.</p></section>
    <section class="panel result-panel polarized-two-path-only"><div class="result-heading"><h2>Polarized Interference · Calculated Phase Sweep</h2><strong id="pt-sweep-status" data-testid="pt-sweep-status">No Sweep Submitted</strong></div>
      <p class="muted">The complete model is called separately for 17 phases, including distinct calculations at 0 and 2π. With the analyzer enabled, every point retains all raw/analyzed scalars. Lines are interpolation only; on failure, only the completed prefix is shown.</p>
      <svg id="pt-sweep-chart" data-testid="pt-sweep-chart" viewBox="0 0 760 230" role="img" aria-label="Calculated Polarized-Interference Phase Sweep"></svg>
      <p id="pt-sweep-identity" data-testid="pt-sweep-identity" class="monospace"></p><p id="pt-sweep-selected" data-testid="pt-sweep-selected" class="monospace"></p>
      <button id="pt-simulate-phase" data-testid="pt-simulate-phase" disabled>Apply Selected Phase and Simulate (Complete Original Sweep Settings)</button>
      <div class="table-scroll"><table><thead><tr><th>index</th><th>phase / rad</th><th>raw η0</th><th>raw η1</th><th>analyzed η0</th><th>analyzed η1</th><th>Complete Scalar Record</th></tr></thead><tbody id="pt-sweep-rows" data-testid="pt-sweep-rows"></tbody></table></div></section>
    <footer class="model-note"><strong>Model Limitations</strong> Periodic sampled window. Gaussian and ideal thin-lens models are paraxial; hard apertures use discrete center sampling.
      No sampling-accuracy guarantee, ray tracing, volume-beam model, calibrated watts, or hardware control. Intensity uses arbitrary amplitude-unit².</footer>
  </main>`;

function element<T extends HTMLElement>(id: string): T {
  const found = document.getElementById(id);
  if (!found) throw new Error(`Missing ${id}`);
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
const polarizedTwoPathController = new PolarizedTwoPathController(polarizedTwoPathPreset('identical'), undefined, undefined, operationGate);
const idealController = new R03Controller(undefined, undefined, undefined, operationGate);
let researchActive = false;
let idealWorkspace: R03Workspace | null = null;
let waveController: WaveFieldController | null = null;
let waveWorkspace: WaveFieldWorkspace | null = null;
let routingActive = false;
let routingController: GeometricRoutingController | null = null;
let routingWorkspace: GeometricRoutingWorkspace | null = null;
let mode: SupportedBenchMode = 'sequential';
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
let documents: ExperimentDocumentController<SupportedBenchMode> | null = null;
let scientificReservations = { persistent: 0, transient: 0 };
const numericBindings = new WeakMap<HTMLInputElement, NumericFieldBinding>();
const resultCanvasCallbacks = new WeakMap<HTMLCanvasElement, (event: MouseEvent) => void>();
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
let polarizedTwoPathLimits: ColorLimits = { min: 0, max: 1 };
let polarizedTwoPathPublished: DecodedPolarizedTwoPathResult | null = null;
let polarizedTwoPathResources: PolarizedTwoPathResources | null = null;
let polarizedTwoPathDisplayKey = '', polarizedTwoPathFieldsKey = '', polarizedTwoPathArmsKey = '', nextPolarizedTwoPathId = 1;
let polarizedTwoPathSelectedPixel: { view: 'raw' | 'analyzed'; port: 0 | 1; row: number; column: number; intensity: number; x_m: number; y_m: number; requestId: string } | null = null;
let resultAttachmentGeneration = 0, releasedResultsCount = 0;

function notice(text: string): void { element('notice').textContent = text; }
function bindResultCanvas(canvas: HTMLCanvasElement, callback: (event: MouseEvent) => void): void {
  resultCanvasCallbacks.set(canvas, callback); canvas.addEventListener('click', callback);
}
function dropResultCanvases(host: ParentNode): void {
  for (const canvas of host.querySelectorAll<HTMLCanvasElement>('canvas')) {
    const callback = resultCanvasCallbacks.get(canvas); if (callback) canvas.removeEventListener('click', callback);
    resultCanvasCallbacks.delete(canvas); canvas.width = 0; canvas.height = 0;
  }
}

function reportPresentation(error: unknown): void {
  const message = error instanceof Error ? error.message : String(error);
  if (routingActive) { routingController?.reportPresentationFailure(message); return; }
  if (researchActive) { if (idealController.state.renderError !== message) idealController.reportRenderFailure(message); return; }
  if (mode === 'sequential' && waveController?.enabled) { waveController.reportPresentationFailure(message); return; }
  if (mode === 'polarized_two_path') { if (polarizedTwoPathController.state.renderError !== message) polarizedTwoPathController.reportRenderFailure(message); }
  else if (mode === 'polarization') { if (polarizationController.state.renderError !== message) polarizationController.reportRenderFailure(message); }
  else if (mode === 'two_path') {
    if (twoPathController.state.renderError !== message) twoPathController.reportRenderFailure(message);
  } else if (controller.state.renderError !== message) controller.reportRenderFailure(message);
}

try {
  scene = new BenchScene(element('bench'), {
    select(ids) {
      if (routingActive) { routingController?.select(ids[0]); return; }
      if (researchActive) { idealController.select(ids[0]); return; }
      if (mode === 'polarized_two_path') { polarizedTwoPathController.select(ids[0]); return; }
      if (mode === 'polarization') { polarizationController.select(ids[0]); return; }
      if (mode === 'two_path') { twoPathController.select(ids[0]); return; }
      controller.select(ids[0]);
      const choices = element('pick-choices');
      choices.replaceChildren();
      if (ids.length > 1) {
        choices.append(document.createTextNode('Multiple elements lie along this line of sight:'));
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
    polarizedTwoPathPixel: (view, port, row, column) => showPolarizedTwoPathPixel(polarizedTwoPathController.state.currentResult, view, port, row, column),
    commitZ(id, z_m) {
      const spec = cloneExperiment(controller.state.candidate);
      const component = spec.components.find((item) => item.id === id);
      if (component) component.z_m = z_m;
      else if (spec.observation.id === id) spec.observation.z_m = z_m;
      controller.replaceCandidate(spec);
    },
    notice,
    presentationFailure(message) {
      if (routingActive) { if (message) routingController?.invalidatePresentation(message);
        else routingController?.reportPresentationFailure('WebGL2 has recovered. Restore the calculated display explicitly; tracing will not be repeated.'); return; }
      if (researchActive) { if (message) idealController.invalidatePresentation(message);
        else idealController.reportRenderFailure(idealController.canRetryPresentation ? 'WebGL2 has recovered. Explicitly restore the calculated display; no computation will be repeated.' : null); return; }
      if (mode === 'sequential' && waveController?.enabled) {
        waveController.reportPresentationFailure(message ?? (waveController.canRetryPresentation
          ? 'WebGL2 has recovered. Explicitly rebuild the calculated display; propagation will not be repeated.' : null)); return;
      }
      if (mode === 'polarized_two_path') {
        if (message) polarizedTwoPathController.invalidatePresentation(message);
        else polarizedTwoPathController.reportRenderFailure(null);
      } else if (mode === 'polarization') {
        if (message) { polarizationPlayback.detach(); polarizationController.invalidatePresentation(message); }
        else polarizationController.reportRenderFailure(null);
      } else if (mode === 'two_path') twoPathController.reportRenderFailure(message);
      else controller.reportRenderFailure(message);
    },
  });
} catch (error) {
  element('bench').classList.add('unavailable');
  element('bench').textContent = 'WebGL2 3D display is unavailable. Check browser settings. No substitute beam or fabricated result has been generated.';
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
  notice('Preset loaded and submitted for validation. Press Simulate explicitly to calculate.');
});
element('simulate').addEventListener('click', () => { if (waveController?.enabled) void waveController.simulate(); else void controller.simulate(); });
element('w1-view').addEventListener('click', () => waveController?.setContext(!waveController.enabled, mode === 'sequential' && !researchActive && !routingActive));
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

function paintNumeric(input: HTMLInputElement, benchMode: SupportedBenchMode, path: string,
    state: { candidate: unknown; revision: number; attachmentEpoch: number }, invalid: boolean): void {
  let binding = numericBindings.get(input);
  if (!binding) { binding = new NumericFieldBinding(); numericBindings.set(input, binding); }
  if (invalid) binding.clear();
  else binding.paint(input.value, `${benchMode}.${path}`, `${state.revision}:${state.attachmentEpoch}`, readPath(state.candidate, path));
}

function shouldEditNumeric(input: HTMLInputElement, benchMode: SupportedBenchMode, path: string,
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
numberField(general, 'wavelength_m', 'λ Wavelength / nm', 1e-9);
numberField(general, 'grid.nx', 'Nx Samples Along x / 1', 1, true);
numberField(general, 'grid.ny', 'Ny Samples Along y / 1', 1, true);
numberField(general, 'grid.dx', 'dx Pixel Pitch / µm', 1e-6);
numberField(general, 'grid.dy', 'dy Pixel Pitch / µm', 1e-6);

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
      label.textContent = 'Source';
      const kind = document.createElement('select');
      kind.dataset.testid = 'source-kind';
      for (const [value, text] of [['gaussian', 'Gaussian'], ['uniform', 'Uniform']]) {
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
      numberField(parent, 'source.amplitude', 'Amplitude / amplitude-unit');
      numberField(parent, 'source.phase_rad', 'Phase / rad');
      if (spec.source.kind === 'gaussian') {
        numberField(parent, 'source.waist_radius_m', 'Waist Radius w₀ / µm', 1e-6);
        numberField(parent, 'source.waist_z_m', 'Waist Position z₀ / mm', 1e-3);
        numberField(parent, 'source.center_x_m', 'Gaussian Center x / µm', 1e-6);
        numberField(parent, 'source.center_y_m', 'Gaussian Center y / µm', 1e-6);
      }
    } else if (index >= 0) {
      const component = spec.components[index];
      numberField(parent, `components.${index}.z_m`, 'Position z / mm', 1e-3);
      if (component.kind === 'thin_lens') numberField(parent, `components.${index}.focal_length_m`, 'Focal Length f (Signed) / mm', 1e-3);
      if (component.kind === 'circular_aperture') numberField(parent, `components.${index}.radius_m`, 'Radius / µm', 1e-6);
      if (component.kind === 'rectangular_aperture') {
        numberField(parent, `components.${index}.width_m`, 'Full Width / µm', 1e-6);
        numberField(parent, `components.${index}.height_m`, 'Full Height / µm', 1e-6);
      }
      const note = document.createElement('p');
      note.className = 'muted';
      note.textContent = 'Elements remain aligned, with no rotation or x/y translation. Equal z positions are allowed; order must be preserved.';
      parent.append(note);
    } else if (state.selection === spec.observation.id) {
      numberField(parent, 'observation.z_m', 'Observation Position z / mm', 1e-3);
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
    { id: 'source', name: `Source · ${state.candidate.source.kind}`, z_m: 0 },
    ...state.candidate.components.map((item, index) => ({ id: item.id, name: `${index + 1}. ${item.kind === 'thin_lens' ? 'Thin Lens' : item.kind === 'circular_aperture' ? 'Circular Aperture' : 'Rectangular Aperture'}`, z_m: item.z_m })),
    { id: state.candidate.observation.id, name: 'Observation Plane', z_m: state.candidate.observation.z_m },
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
  output.textContent = `row=${row}, column=${column}; x=${coordinates.x_m.toPrecision(17)} m, y=${coordinates.y_m.toPrecision(17)} m; I=${intensity.toPrecision(17)} amplitude-unit²`;
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
    ? 'The observation-plane field is recorded; the image above shows raw intensity.' : 'No field was recorded at this stage; only scalars are shown. Selection does not rerun the simulation.';
});

function renderResult(state: BenchState): void {
  const result = state.lastResult;
  const status = element('result-status');
  if (!result) { status.textContent = 'No Completed Simulation'; return; }
  status.textContent = state.currentResult
    ? state.renderError ? 'Computation Complete; 3D Display Failed; Raw Result Retained' : 'Completed Result for Current Draft'
    : 'Previous Completed Result · Stale Result, Separate from Current Draft';
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
    element('result-spec').textContent = `Original Submission: λ=${(spec.wavelength_m * 1e9).toPrecision(7)} nm; ${spec.grid.ny}×${spec.grid.nx}; Observation z=${(spec.observation.z_m * 1000).toPrecision(7)} mm; ${spec.components.length} Elements.`;
    element('raw-max').textContent = `Raw Maximum Intensity: ${result.intensityMax.toPrecision(17)} amplitude-unit²`;
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
  element('color-info').textContent = `Shared Range ${limits.min}–${limits.max} amplitude-unit²; Changes display colors only, not numerical values.`;
  const saturation = element('saturation');
  saturation.hidden = result.intensityMax <= limits.max;
  saturation.textContent = `Display Saturation: Raw Maximum ${result.intensityMax.toPrecision(8)} exceeds maximum ${limits.max}; High values appear white; raw readouts are preserved.`;
}

function sequentialBenchLabel(state: BenchState): string {
  return state.pendingValidation ? 'Validating Edits; Previous Result Detached'
    : Object.keys(state.invalidEdits).length ? 'Invalid Input; Previous Result Detached'
      : state.currentResult ? 'Intensity for Current Submission' : 'Draft Validated; No Current Result';
}
function render(state: BenchState): void {
  if (disposed || applyingDocument || researchActive || routingActive || mode !== 'sequential') return;
  const statusText: Record<string, string> = { idle: 'Not Yet Validated', validating: 'Validating Draft', ready: 'Draft Validated', simulating: 'Computing; No Automatic Retry', error: 'Check Error Details' };
  element('status').textContent = statusText[state.status] ?? state.status;
  element('status').dataset.status = state.status;
  element<HTMLButtonElement>('simulate').disabled = !state.validatedDraft || state.pendingValidation
    || !!state.active || operationGate.busy || Object.keys(state.invalidEdits).length > 0;
  element('error').hidden = !state.error; element('error').textContent = state.error ?? '';
  element('render-error').hidden = !state.renderError; element('render-error').textContent = state.renderError ?? '';
  renderInspector(state);
  renderComponents(state);
  element('bench-label').textContent = sequentialBenchLabel(state);
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

function dualValue(value: number | null): string { return value === null ? 'null (undefined)' : value.toPrecision(17); }

function showDualPixel(result: DecodedTwoPathResult | null, port: 0 | 1, row: number, column: number): void {
  if (!result || !Number.isInteger(row) || !Number.isInteger(column) || row < 0 || column < 0
      || row >= result.experiment.grid.ny || column >= result.experiment.grid.nx) return;
  const intensity = result.ports[port].intensity[row * result.experiment.grid.nx + column];
  dualSelectedPixel = { port, row, column, x_m: result.x[column], y_m: result.y[row], intensity, requestId: result.requestId };
  const output = document.getElementById('tp-pixel-readout');
  if (!output) return;
  output.textContent = `port_${port} · row=${row}, column=${column}; x=${result.x[column].toPrecision(17)} m, y=${result.y[row].toPrecision(17)} m; I=${intensity.toPrecision(17)} amplitude-unit²`;
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
  local('tp-result-spec').textContent = `Complete Original Submission (SI / rad)\n${JSON.stringify(result.experiment, null, 2)}`;
  local('tp-fractions').textContent = `Original-Input Ratio η0=${dualValue(result.diagnostics.output_fractions[0])}; η1=${dualValue(result.diagnostics.output_fractions[1])}; total=${dualValue(result.diagnostics.total_output_ratio)}`;
  for (const port of [0, 1] as const) {
    const holder = local('tp-holder-' + port), canvas = canvases[port];
    holder.style.aspectRatio = String(result.experiment.grid.nx * result.experiment.grid.dx / (result.experiment.grid.ny * result.experiment.grid.dy));
    holder.append(canvas);
    bindResultCanvas(canvas, event => {
      if (dualPublished !== result || !twoPathController.state.currentResult) return;
      const rect = canvas.getBoundingClientRect();
      const pixel = pixelFromUV(result.experiment.grid, (event.clientX - rect.left) / rect.width, 1 - (event.clientY - rect.top) / rect.height);
      if (pixel) showDualPixel(result, port, pixel.row, pixel.column);
    });
    const maximum = local('tp-raw-max-' + port), max = result.ports[port].intensityMax;
    maximum.dataset.value = String(max);
    maximum.textContent = `raw max=${max.toPrecision(17)} amplitude-unit²${max > dualLimits.max ? ' · Display Saturated; Raw Values Retained' : ''}`;
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
  const generation = resultAttachmentGeneration;
  if (!scene) throw new Error('Computation is complete; the WebGL2 two-port display is unavailable. No recalculation was performed.');
  const numericalBytes = ownedSnapshot(result).retainedBytes;
  const imageBytes = 16 * result.experiment.grid.nx * result.experiment.grid.ny;
  if (numericalBytes + imageBytes + 128 * 1024 > OWNED_PERSISTENT_BUDGET_BYTES) throw new Error('Two-port preparation exceeds the app-owned persistent data budget.');
  const retained = ownedSnapshot().retainedBytes + 128 * 1024;
  if (estimateDualOperationBytes(result.experiment.grid, retained).peakOwnedBytes > OWNED_TRANSIENT_BUDGET_BYTES) {
    throw new Error('Two-port preparation exceeds the app-owned transient data budget.');
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
      if (generation !== resultAttachmentGeneration) throw new Error('Released or detached two-path presentation');
      committed = true;
      scenePrepared.commit();
      host.replaceChildren(content); host.hidden = false;
      dualPublished = result; dualDisplayKey = `${result.requestId}:${dualLimits.min}:${dualLimits.max}`;
      showDualPixel(result, 0, Math.floor(result.experiment.grid.ny / 2), Math.floor(result.experiment.grid.nx / 2));
    },
    finalize() {
      scenePrepared.finalize();
      for (const node of oldChildren) if (node instanceof HTMLElement) {
        dropResultCanvases(node);
      }
    },
    dispose() {
      scenePrepared.dispose();
      if (committed && generation === resultAttachmentGeneration) { host.replaceChildren(...oldChildren); dualPublished = previous; dualDisplayKey = previousKey; }
      dropResultCanvases(content);
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
      ['grid.dx', 'dx / µm', 1e-6], ['grid.dy', 'dy / µm', 1e-6], ['source.amplitude', 'Amplitude / amplitude-unit', 1], ['source.phase_rad', 'Source Phase / rad', 1],
    ];
    if (source.kind === 'gaussian') fields.push(['source.waist_radius_m', 'Waist Radius w₀ / µm', 1e-6], ['source.waist_z_m', 'Waist Position / mm', 1e-3],
      ['source.center_x_m', 'Center x / µm', 1e-6], ['source.center_y_m', 'Center y / µm', 1e-6]);
    fields.push(['two_arm_spec.arm_0_distance_m', 'L₀ Propagation / mm', 1e-3], ['two_arm_spec.arm_1_distance_m', 'L₁ Propagation / mm', 1e-3],
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
  element('tp-phase-note').textContent = `extra phase=${phi.toPrecision(17)} rad; degrees=${(phi * 180 / Math.PI).toPrecision(8)}°(For reference only; degrees are not submitted)`;
}

function renderSweep(sweep: DecodedTwoPathSweep | null, fresh: boolean): void {
  const status = element('tp-sweep-status'), svg = element<SVGSVGElement & HTMLElement>('tp-sweep-chart');
  status.textContent = !sweep ? 'No Completed Sweep' : `${fresh ? '' : 'Previous Sweep · Stale Result · '}${sweep.status === 'failed' ? 'FAILED / PARTIAL' : 'Complete'} ${sweep.completedCount}/${sweep.requestedCount}${sweep.error ? ` · HTTP ${sweep.httpStatus} · ${sweep.error.message}` : ''}`;
  status.classList.toggle('warning', !!sweep && (!fresh || sweep.status === 'failed'));
  svg.replaceChildren(); const body = element('tp-sweep-rows'); body.replaceChildren();
  if (!sweep) return;
  element('tp-sweep-identity').textContent = `request=${sweep.requestId}\nSHA-256=${sweep.fixedExperimentSha256}\nOriginal Fixed Submission=${JSON.stringify(sweep.fixedExperiment)}`;
  const add = (tag: string, attributes: Record<string, string>, text?: string) => {
    const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
    if (text !== undefined) node.textContent = text;
    svg.append(node); return node;
  };
  add('path', { d: 'M55 20V190H725', fill: 'none', stroke: '#8ba2b1' });
  add('text', { x: '55', y: '218', fill: '#526e80' }, '0 rad');
  add('text', { x: '660', y: '218', fill: '#526e80' }, '2π rad');
  add('text', { x: '65', y: '16', fill: '#526e80' }, `Original-Input Ratio · Shared ${chartRange.min}–${chartRange.max} · Lines Are Interpolation Only`);
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
    if (points.some(point => point.outOfRange)) add('text', { x: '60', y: String(35 + port * 16), fill: color }, `port ${port} has values outside the display range; raw table values are retained`);
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
  if (disposed || applyingDocument || researchActive || routingActive || mode !== 'two_path') return;
  element('tp-status').textContent = state.status; element('tp-status').dataset.status = state.status;
  element('tp-error').hidden = !state.error; element('tp-error').textContent = state.error ?? '';
  element('tp-render-error').hidden = !state.renderError; element('tp-render-error').textContent = state.renderError ?? '';
  const ready = !!state.validatedDraft && !state.pendingValidation && !Object.keys(state.invalidEdits).length && !operationGate.busy;
  element<HTMLButtonElement>('tp-simulate').disabled = !ready;
  element<HTMLButtonElement>('tp-sweep').disabled = !ready || state.candidate.grid.nx > 128 || state.candidate.grid.ny > 128;
  element<HTMLButtonElement>('tp-simulate-phase').disabled = operationGate.busy || state.selectedSweepIndex === null;
  renderDualFields(state);
  element('bench-label').textContent = state.currentResult ? 'Immediate Two-Port Outputs · Original Submission' : 'Ideal Unfolded Schematic · No Current Two-Port Result';
  try {
    if (!state.currentResult) {
      scene?.detachDualResult(); dualPublished = null; dualDisplayKey = ''; dualSelectedPixel = null;
      dropResultCanvases(element('tp-current-content'));
      element('tp-current-content').replaceChildren();
    }
    if (state.validatedDraft) scene?.updateTwoPathExperiment(state.validatedDraft, state.selection);
    if (state.currentResult && dualDisplayKey !== `${state.currentResult.requestId}:${dualLimits.min}:${dualLimits.max}`) {
      const prepared = prepareDualPresentation(state.currentResult);
      try { prepared.commit(); prepared.finalize(); } catch (error) { prepared.dispose(); throw error; }
    }
  } catch (error) { reportPresentation(error); }
  element('tp-color-info').textContent = `Shared Range ${dualLimits.min}–${dualLimits.max} amplitude-unit²; Does not change automatically with results or sweeps.`;
  element('tp-result-status').textContent = state.currentResult ? state.renderError ? 'Computation Complete · Display Failure' : 'Complete Two-Port Result for Current Submission'
    : state.completedNumerical && state.renderError ? 'Computation Complete · Display Preparation Failed; No Partial Display Published' : state.lastResult ? 'Stale Result · Retained Under Original Submission' : 'No Completed Simulation';
  const previous = element('tp-previous-result'); previous.hidden = !state.lastResult || state.currentResult === state.lastResult;
  if (state.lastResult) element('tp-previous-spec').textContent = `Original request=${state.lastResult.requestId}\n${JSON.stringify(state.lastResult.experiment, null, 2)}\nOriginal maxima=${state.lastResult.ports.map(p => p.intensityMax)}\nOriginal diagnostics=${JSON.stringify(state.lastResult.diagnostics)}`;
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
  element('tp-sweep-selected').textContent = selected ? `Selected Calculated Row (No Recalculation)=${JSON.stringify(selected)}` : '';
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
function ownedSnapshot(additional: DecodedPolarizationResult | DecodedTwoPathResult | DecodedPolarizedTwoPathResult | null = null): {
  scientificBytes: number; canvasBytes: number; textureBytes: number; trajectoryBytes: number; geometryBytes: number; documentBytes: number; idealWorkspaceBytes: number; waveFieldBytes: number; geometricRoutingBytes: number; sharedGeometryAliasBytes: number; retainedBytes: number;
} {
  const sceneResults = scene?.ownedNumericalResults();
  const scientificBytes = ownedScientificBytes4({ sequential: [controller.state.lastResult, displayedResult, sceneResults?.sequential ?? null],
    dual: [twoPathController.state.lastResult, twoPathController.state.completedNumerical, dualPublished, sceneResults?.dual ?? null,
      additional && 'ports' in additional ? additional : null],
    polarization: [polarizationController.state.lastResult, polarizationController.state.completedNumerical, polarizationPublished, sceneResults?.polarization ?? null,
      additional && 'incidentIntensity' in additional ? additional : null],
    polarizedTwoPath: [polarizedTwoPathController.state.lastResult, polarizedTwoPathController.state.completedNumerical,
      polarizedTwoPathPublished, sceneResults?.polarizedTwoPath ?? null, additional && 'rawPorts' in additional ? additional : null],
    sweeps: [twoPathController.state.lastSweep, polarizationController.state.lastSweep, polarizedTwoPathController.state.lastSweep] });
  const canvasBytes = [...document.querySelectorAll<HTMLCanvasElement>('#intensity, #tp-result-area canvas, #pl-result-area canvas, #pt-result-area canvas')]
    .reduce((n, canvas) => n + canvas.width * canvas.height * 4, 0);
  const textureBuffers = new Set<ArrayBufferLike>(scene?.ownedTextureBuffers() ?? []);
  for (const texture of polarizationResources?.textures ?? []) textureBuffers.add((texture.image.data as Uint8Array).buffer);
  for (const texture of polarizedTwoPathResources?.textures ?? []) textureBuffers.add((texture.image.data as Uint8Array).buffer);
  const textureBytes = [...textureBuffers].reduce((n, buffer) => n + buffer.byteLength, 0);
  const trajectoryBytes = polarizationResources?.trajectories.reduce((n, trajectory) => n + trajectory.points.byteLength, 0) ?? 0;
  const geometryBytes = scene?.ownedGeometryBuffers().reduce((n, buffer) => n + buffer.byteLength, 0) ?? 0;
  const documentBytes = documents?.ownershipSnapshot().retainedBytes ?? 0;
  const idealWorkspaceBytes = idealWorkspace?.ownedBytes() ?? 0;
  // Both apparatus factories borrow Three's one global Sprite quad. R03 already
  // charges those backing buffers while its labels exist; charge their W1 alias
  // only when R03 is absent. Neither factory owns or disposes that shared quad.
  const idealApparatus = (idealWorkspace?.snapshot() as { apparatus?: { borrowedGeometryCount?: number } } | undefined)?.apparatus;
  const sharedGeometryAliasBytes = (idealApparatus?.borrowedGeometryCount ?? 0) > 0
    ? waveWorkspace?.borrowedGeometryBytes() ?? 0 : 0;
  const waveFieldBytes = (waveWorkspace?.ownedBytes() ?? 0) - sharedGeometryAliasBytes;
  const geometricRoutingBytes = (routingController?.ownedNumericalBytes() ?? 0) + (routingController?.ownedStateBytes() ?? 0) + (routingWorkspace?.ownedRenderingBytes() ?? 0);
  return { scientificBytes, canvasBytes, textureBytes, trajectoryBytes, geometryBytes, documentBytes, idealWorkspaceBytes, waveFieldBytes, geometricRoutingBytes, sharedGeometryAliasBytes,
    retainedBytes: scientificBytes + canvasBytes + textureBytes + trajectoryBytes + geometryBytes + documentBytes + idealWorkspaceBytes + waveFieldBytes + geometricRoutingBytes };
}
function admitOperation(kind: SupportedBenchMode, grid: Experiment['grid'], operation: 'single' | 'sweep' = 'single', analyzerEnabled = false): void {
  const bytes = ownedSnapshot().retainedBytes, estimate = kind === 'polarized_two_path'
    ? estimatePolarizedTwoPathOperation(grid, analyzerEnabled, bytes, operation) : estimateOwnedOperation(kind, grid, bytes, operation);
  // Before any HTTP allocation, conservatively reserve a distinct successful
  // completion alongside all actual old owners. A scene/canvas preparation
  // failure may retain different sequential results, so replacement cannot be
  // assumed to release those buffers. No owner is discarded to make room.
  const projectedPersistent = kind === 'polarized_two_path' ? estimatePolarizedTwoPathOperation(grid, analyzerEnabled, bytes, operation).persistentProjection
    : bytes + (operation === 'sweep' ? 65536 : estimate.payloadBytes + 16384);
  const docReservation = documents?.ownershipSnapshot();
  assertOwnedBudgets(projectedPersistent + (docReservation?.projectedPersistentBytes ?? 0),
    estimate.peakOwnedBytes + (docReservation?.transientReservedBytes ?? 0));
  scientificReservations = { persistent: projectedPersistent - bytes, transient: Math.max(0, estimate.peakOwnedBytes - bytes) };
}

function detachPolarizationPresentation(): void {
  polarizationPlayback.detach(); scene?.setFrameCallback(null); scene?.detachPolarizationResult();
  polarizationResources?.dispose(); polarizationResources = null; polarizationPublished = null; polarizationDisplayKey = '';
  polarizationSelectedPixel = null; dropResultCanvases(element('pl-current-content')); element('pl-current-content').replaceChildren();
}
function showPolarizationPixel(result: DecodedPolarizationResult | null, view: 0 | 1, row: number, column: number): void {
  if (!result || !Number.isInteger(row) || !Number.isInteger(column) || row < 0 || column < 0
      || row >= result.experiment.grid.ny || column >= result.experiment.grid.nx) return;
  const intensity = (view === 0 ? result.incidentIntensity : result.finalIntensity)[row * result.experiment.grid.nx + column];
  polarizationSelectedPixel = { view, row, column, intensity, x_m: result.x[column], y_m: result.y[row], requestId: result.requestId };
  const output = document.getElementById('pl-pixel-readout');
  if (output) output.textContent = `${view === 0 ? 'incident' : 'final'} intensity pixel row=${row}, column=${column}; x=${result.x[column]}, y=${result.y[row]} m; I=${intensity} amplitude-unit². The fixed complex sample is unchanged.`;
}
function polarizationContent(result: DecodedPolarizationResult, resources: PolarizationResources): HTMLDivElement {
  const content = document.createElement('div');
  content.innerHTML = `<p id="pl-identity" data-testid="pl-identity" class="monospace"></p><pre id="pl-result-spec"></pre>
    <div class="dual-images"><div><h3>Incident Intensity</h3><div class="intensity-holder" id="pl-holder-0"></div><p id="pl-max-0" data-testid="pl-max-0"></p></div>
    <div><h3>Final Intensity</h3><div class="intensity-holder" id="pl-holder-1"></div><p id="pl-max-1" data-testid="pl-max-1"></p></div></div>
    <p id="pl-pixel-readout" data-testid="pl-pixel-readout" class="monospace"></p>
    <label>Submitted Stage <select id="pl-stage" data-testid="pl-stage"></select></label><p id="pl-stage-note" data-testid="pl-stage-note"></p>
    <pre id="pl-sample" data-testid="pl-sample"></pre><div id="pl-trajectories" data-testid="pl-trajectories" class="polarization-trajectories"></div>
    <div class="table-scroll"><table><thead><tr><th>stage</th><th>actual norm</th><th>signed Δnorm</th><th>adjacent ratio</th><th>original-incident ratio</th></tr></thead><tbody id="pl-stages" data-testid="pl-stages"></tbody></table></div>`;
  const local = <T extends HTMLElement>(id: string) => content.querySelector<T>(`#${id}`)!;
  local('pl-identity').textContent = `request=${result.requestId}\nSHA-256=${result.experimentSha256}`;
  local('pl-result-spec').textContent = `Complete Original Submission / SI / rad\n${JSON.stringify(result.experiment, null, 2)}`;
  for (const view of [0, 1] as const) {
    const holder = local('pl-holder-' + view), canvas = resources.canvases[view];
    holder.style.aspectRatio = String(result.experiment.grid.nx * result.experiment.grid.dx / (result.experiment.grid.ny * result.experiment.grid.dy));
    holder.append(canvas); local('pl-max-' + view).textContent = `raw max=${result.intensityMax[view]} amplitude-unit²${result.intensityMax[view] > polarizationLimits.max ? ' · Display Saturated; Raw Values Retained' : ''}`;
    local('pl-max-' + view).dataset.value = String(result.intensityMax[view]);
    bindResultCanvas(canvas, event => {
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
      const cell = document.createElement('td'); cell.textContent = value === null ? 'null (undefined)' : String(value); tr.append(cell);
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
    note.textContent = trajectory.dark ? 'no defined polarization state at this sample (exact zero)'
      : trajectory.displayLimited ? 'Nonzero sample · Display-scale/precision limitation; raw complex values are retained.' : 'Nonzero sample · Shared scale · Purple marks τ=0; orange advances with increasing τ.';
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
  const generation = resultAttachmentGeneration;
  if (!scene) throw new Error('Computation is complete; WebGL2 is unavailable. No recalculation was performed.');
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
      if (closed || generation !== resultAttachmentGeneration) throw new Error('Polarization presentation transaction closed or released');
      committed = true;
      prepared.commit(); host.replaceChildren(content); polarizationPublished = result; polarizationResources = resources;
      polarizationDisplayKey = `${result.requestId}:${polarizationLimits.min}:${polarizationLimits.max}:${polarizationScale}:${polarizationGain}`;
      polarizationPlayback.bind(updatePolarizationMarkers); scene!.setFrameCallback(time => polarizationPlayback.tick(time));
      showPolarizationPixel(result, 0, result.readout.row, result.readout.column);
    },
    dispose() {
      if (closed) return; closed = true; prepared.dispose(); dropResultCanvases(content); resources.dispose();
      if (committed && generation === resultAttachmentGeneration) { host.replaceChildren(...oldNodes); polarizationPublished = previous; polarizationResources = oldResources; polarizationDisplayKey = previousKey;
        polarizationPlayback.detach(); if (previous && oldResources) polarizationPlayback.bind(updatePolarizationMarkers); }
    },
    finalize() { if (closed) return; closed = true; prepared.finalize(); for (const node of oldNodes) if (node instanceof HTMLElement) dropResultCanvases(node); oldResources?.dispose(); },
  };
}
function renderPolarizationSample(state: PolarizationState): void {
  const result = polarizationPublished; if (!result) return;
  const stage = result.stages.find(item => item.stage_id === state.selectedStage) ?? result.stages[0];
  const trajectory = polarizationResources?.trajectories.find(item => item.stageId === stage.stage_id);
  element<HTMLSelectElement>('pl-stage').value = stage.stage_id;
  element('pl-sample').textContent = `Fixed Complex Sample request=${result.requestId}\nstage=${stage.stage_id}; row=${result.readout.row}, column=${result.readout.column}\nx=${result.readout.x_m} m; y=${result.readout.y_m} m\nUx={re:${stage.sample.x.re}, im:${stage.sample.x.im}}\nUy={re:${stage.sample.y.re}, im:${stage.sample.y.im}}`;
  element('pl-stage-note').textContent = `${trajectory?.dark ? 'no defined polarization state at this sample (exact zero)' : trajectory?.displayLimited ? 'Nonzero sample · Display-scale/precision limitation; raw values are retained.' : 'Nonzero sample · Common phase is preserved.'} actual norm=${stage.norm}; signed Δ=${stage.delta_norm}; adjacent ratio=${stage.adjacent_transmission_ratio}; original-incident ratio=${stage.incident_transmission_ratio}. null=undefined. Ratios do not establish causation or hardware efficiency.`;
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
    if (selected) { make(parent, `elements.${index}.axis_angle_rad`, 'axis θ / rad(+x toward +y)');
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
  element('pl-sweep-status').textContent = !sweep ? 'No Completed Sweep' : `${fresh ? '' : 'Previous Sweep · Stale Result · '}${sweep.status === 'complete' ? 'Complete' : 'FAILED / PARTIAL'} ${sweep.completedCount}/13${sweep.error ? ` · HTTP ${sweep.httpStatus} · ${sweep.error.message}` : ''}`;
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
    for (const item of [row.index, row.axis_angle_rad, row.final_norm, value, row.total_delta]) { const td = document.createElement('td'); td.textContent = item === null ? 'null (undefined)' : String(item); tr.append(td); }
    tr.addEventListener('click', () => polarizationController.selectSweepPoint(row.index)); body.append(tr);
  }
  finish(); // No connection or invented marker beyond the genuine completed prefix.
}
function renderPolarization(state: PolarizationState): void {
  if (disposed || applyingDocument || researchActive || routingActive || mode !== 'polarization') return;
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
  element('bench-label').textContent = state.currentResult ? 'Same Reference Plane · Complete Original Result' : 'Same Reference Plane · No Current Attached Result';
  const effective = polarizationResources;
  element('pl-color-info').textContent = `Displayed Shared Intensity Range ${effective?.limits.min ?? polarizationLimits.min}..${effective?.limits.max ?? polarizationLimits.max} amplitude-unit²; Shared Amplitude Scale ${effective?.commonAmplitudeScale ?? polarizationScale}, Manual Display Gain=${effective?.gain ?? polarizationGain}.${state.renderError ? 'New display settings were not published; the previous display and scale are retained.' : ''}Optical results are unchanged.`;
  element('pl-result-status').textContent = state.currentResult ? 'Current Submission · Complete Result' : state.completedNumerical && state.renderError ? 'Computation Complete · Display Failed; Original Result Retained; No Automatic Recalculation' : state.lastResult ? 'Stale Result · Original Submission Retained Separately' : 'No Completed Simulation';
  const previous = element('pl-previous-result'); previous.hidden = !state.lastResult || state.currentResult === state.lastResult;
  if (state.lastResult) element('pl-previous-spec').textContent = `Original request=${state.lastResult.requestId}\n${JSON.stringify(state.lastResult.experiment, null, 2)}\nOriginal stages=${JSON.stringify(state.lastResult.stages)}`;
  renderPolarizationSweep(state.lastSweep, state.currentSweep === state.lastSweep);
  const selected = state.lastSweep?.rows.find(row => row.index === state.selectedSweepIndex);
  element('pl-sweep-selected').textContent = selected ? `Selected Calculated Row (No Recalculation)=${JSON.stringify(selected)}` : '';
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
  if (!Number.isFinite(next.min) || !Number.isFinite(next.max) || next.max <= next.min) { notice('Chart limits must be finite, with minimum less than maximum.'); return; }
  chartRange = next; renderSweep(twoPathController.state.lastSweep, twoPathController.state.currentSweep === twoPathController.state.lastSweep);
});

function detachPolarizedTwoPathPresentation(): void {
  scene?.detachPolarizedTwoPathResult(); polarizedTwoPathResources?.dispose(); polarizedTwoPathResources = null;
  polarizedTwoPathPublished = null; polarizedTwoPathDisplayKey = ''; polarizedTwoPathSelectedPixel = null;
  dropResultCanvases(element('pt-current-content')); element('pt-current-content').replaceChildren();
}
function showPolarizedTwoPathPixel(result: DecodedPolarizedTwoPathResult | null, view: 'raw' | 'analyzed', port: 0 | 1, row: number, column: number): void {
  if (!result || !Number.isInteger(row) || !Number.isInteger(column) || row < 0 || column < 0
      || row >= result.experiment.grid.ny || column >= result.experiment.grid.nx) return;
  const ports = view === 'raw' ? result.rawPorts : result.analyzedPorts; if (!ports) return;
  const intensity = ports[port].intensity[row * result.experiment.grid.nx + column];
  polarizedTwoPathSelectedPixel = { view, port, row, column, intensity, x_m: result.x[column], y_m: result.y[row], requestId: result.requestId };
  const output = document.getElementById('pt-pixel-readout'); if (!output) return;
  output.textContent = `${view} port_${port} · row=${row}, column=${column}; x=${result.x[column].toPrecision(17)} m; y=${result.y[row].toPrecision(17)} m; I=${intensity.toPrecision(17)} amplitude-unit²`;
  Object.assign(output.dataset, { view, port: String(port), row: String(row), column: String(column), intensity: String(intensity), requestId: result.requestId });
}
function polarizedTwoPathContent(result: DecodedPolarizedTwoPathResult, resources: PolarizedTwoPathResources): HTMLDivElement {
  const content = document.createElement('div');
  content.innerHTML = `<div class="dual-results"><div class="dual-images" id="pt-images"></div><div class="result-details">
    <p id="pt-result-identity" data-testid="pt-result-identity" class="monospace"></p><pre id="pt-result-spec" data-testid="pt-result-spec"></pre>
    <div class="table-scroll"><table><thead><tr><th>checkpoint</th><th>port 0 norm</th><th>port 1 norm</th><th>total</th></tr></thead><tbody id="pt-norms" data-testid="pt-norms"></tbody></table></div>
    <pre id="pt-diagnostics" data-testid="pt-diagnostics"></pre><pre id="pt-analysis" data-testid="pt-analysis"></pre></div></div>
    <p id="pt-pixel-readout" data-testid="pt-pixel-readout" class="monospace"></p>`;
  const local = (id: string) => content.querySelector<HTMLElement>(`#${id}`)!;
  local('pt-result-identity').textContent = `request=${result.requestId}\nSHA-256=${result.experimentSha256}`;
  local('pt-result-spec').textContent = `Complete Original Submission (SI / rad)\n${JSON.stringify(result.experiment, null, 2)}`;
  const generation = resultAttachmentGeneration;
  for (const [index, canvas] of resources.canvases.entries()) {
    const view = index < 2 ? 'raw' : 'analyzed', port = (index % 2) as 0 | 1;
    const card = document.createElement('div'), title = document.createElement('h3'); title.textContent = `${view} · port ${port}`;
    const holder = document.createElement('div'); holder.className = 'intensity-holder';
    holder.style.aspectRatio = String(result.experiment.grid.nx * result.experiment.grid.dx / (result.experiment.grid.ny * result.experiment.grid.dy));
    canvas.dataset.testid = `pt-intensity-${view}-${port}`; holder.append(canvas);
    bindResultCanvas(canvas, event => {
      if (generation !== resultAttachmentGeneration || polarizedTwoPathPublished !== result || !polarizedTwoPathController.state.currentResult) return;
      const rect = canvas.getBoundingClientRect();
      const pixel = pixelFromUV(result.experiment.grid, (event.clientX - rect.left) / rect.width, 1 - (event.clientY - rect.top) / rect.height);
      if (pixel) showPolarizedTwoPathPixel(result, view, port, pixel.row, pixel.column);
    });
    const maximum = document.createElement('p'), value = result.intensityMax[index]; maximum.dataset.testid = `pt-max-${view}-${port}`; maximum.dataset.value = String(value);
    maximum.textContent = `Raw max=${value.toPrecision(17)} amplitude-unit²${value > resources.limits.max ? ' · Display Saturated; Raw Values Retained' : ''}`;
    maximum.classList.toggle('warning', value > resources.limits.max); card.append(title, holder, maximum); local('pt-images').append(card);
  }
  if (!result.analyzedPorts) {
    const absent = document.createElement('p'); absent.dataset.testid = 'pt-analysis-absent'; absent.textContent = `Analyzer disabled: no analyzed images or measurements; retained angle=${result.analysis.axis_angle_rad} rad.`;
    local('pt-images').append(absent);
  }
  for (const checkpoint of ['inputs', 'split', 'propagated', 'elements', 'combiner', 'outputs'] as const) {
    const row = document.createElement('tr');
    for (const value of [checkpoint, ...result.norms[checkpoint].map(dualValue), dualValue(result.diagnostics[`${checkpoint}_total`])]) {
      const cell = document.createElement('td'); cell.textContent = value; row.append(cell);
    } local('pt-norms').append(row);
  }
  local('pt-diagnostics').textContent = `Public Diagnostics (Signed Values and null Preserved)\n${JSON.stringify(result.diagnostics, null, 2)}\nOrdered Action Norms=${JSON.stringify(result.norms.arm_action_norms)}`;
  local('pt-analysis').textContent = `Separate Downstream Measurement (Raw Data Unchanged)\noriginal_input_ratio denominator=original incident norm; raw_output_ratio denominator=that raw port norm\n${JSON.stringify(result.analysis, null, 2)}`;
  return content;
}
function preparePolarizedTwoPathPresentation(result: DecodedPolarizedTwoPathResult): { commit(): void; dispose(): void; finalize(): void } {
  if (!scene) throw new Error('Complete numerical measurements are available; WebGL2 display is unavailable. No recalculation was performed.');
  const generation = resultAttachmentGeneration, estimate = estimatePolarizedTwoPathOperation(result.experiment.grid, result.experiment.analyzer.enabled, ownedSnapshot().retainedBytes);
  const images = result.analyzedPorts ? 4 : 2;
  assertOwnedBudgets(ownedSnapshot(result).retainedBytes + 8 * images * result.experiment.grid.nx * result.experiment.grid.ny + 131072, estimate.peakOwnedBytes);
  const resources = preparePolarizedTwoPathResources(result, polarizedTwoPathLimits);
  let content: HTMLDivElement, prepared: ReturnType<BenchScene['preparePolarizedTwoPathResult']>;
  const view = result.analyzedPorts ? polarizedTwoPathController.state.viewSelection : 'raw';
  try { content = polarizedTwoPathContent(result, resources); prepared = scene.preparePolarizedTwoPathResult(result, resources.textures, view); }
  catch (error) { resources.dispose(); throw error; }
  const host = element('pt-current-content'), oldNodes = Array.from(host.childNodes), previous = polarizedTwoPathPublished,
    oldResources = polarizedTwoPathResources, previousKey = polarizedTwoPathDisplayKey, previousPixel = polarizedTwoPathSelectedPixel;
  let committed = false, closed = false;
  return {
    commit() {
      if (closed || generation !== resultAttachmentGeneration) throw new Error('Released or detached polarized two-path presentation');
      committed = true;
      prepared.commit(); host.replaceChildren(content); polarizedTwoPathPublished = result; polarizedTwoPathResources = resources;
      polarizedTwoPathDisplayKey = `${result.requestId}:${resources.limits.min}:${resources.limits.max}`;
      showPolarizedTwoPathPixel(result, view, 0, Math.floor(result.experiment.grid.ny / 2), Math.floor(result.experiment.grid.nx / 2));
    },
    dispose() {
      if (closed) return; closed = true; prepared.dispose(); dropResultCanvases(content); resources.dispose();
      if (committed && generation === resultAttachmentGeneration) { host.replaceChildren(...oldNodes); polarizedTwoPathPublished = previous;
        polarizedTwoPathResources = oldResources; polarizedTwoPathDisplayKey = previousKey; polarizedTwoPathSelectedPixel = previousPixel; }
    },
    finalize() { if (closed) return; closed = true; prepared.finalize(); for (const node of oldNodes) if (node instanceof HTMLElement) dropResultCanvases(node); oldResources?.dispose(); },
  };
}
function renderPolarizedTwoPathFields(state: PolarizedTwoPathState): void {
  const make = (parent: HTMLElement, path: string, label: string, integer = false) => {
    const wrapper = document.createElement('label'); wrapper.className = 'number-field'; wrapper.textContent = label;
    const input = document.createElement('input'); input.type = 'text'; input.inputMode = integer ? 'numeric' : 'decimal';
    input.dataset.ptPath = path; input.dataset.testid = `pt-edit-${path.replaceAll('.', '-')}`;
    input.addEventListener('input', () => {
      if (shouldEditNumeric(input, 'polarized_two_path', path, polarizedTwoPathController.state)) void polarizedTwoPathController.edit(path, input.value, 1, integer);
    }); wrapper.append(input); parent.append(wrapper);
  };
  if (polarizedTwoPathFieldsKey !== state.candidate.source.kind) {
    polarizedTwoPathFieldsKey = state.candidate.source.kind; const parent = element('pt-fields'); parent.replaceChildren();
    for (const [path, label, integer] of [['wavelength_m', 'λ / m'], ['grid.nx', 'Nx (max128)', true], ['grid.ny', 'Ny (max128)', true],
      ['grid.dx', 'dx / m'], ['grid.dy', 'dy / m'], ['source.amplitude', 'scalar amplitude'], ['source.phase_rad', 'source phase / rad'],
      ['coefficients.x.re', 'coefficient x real'], ['coefficients.x.im', 'coefficient x imaginary'], ['coefficients.y.re', 'coefficient y real'], ['coefficients.y.im', 'coefficient y imaginary'],
      ['arm_0.distance_m', 'arm 0 propagation / m'], ['arm_1.distance_m', 'arm 1 propagation / m'], ['relative_phase_rad', 'arm 1 extra phase / rad'],
      ['analyzer.axis_angle_rad', 'shared analyzer axis / rad (Retained When Disabled)']] as [string, string, boolean?][]) make(parent, path, label, integer);
    if (state.candidate.source.kind === 'gaussian') for (const [path, label] of [['source.waist_radius_m', 'waist radius / m'],
      ['source.waist_z_m', 'signed waist position / m'], ['source.center_x_m', 'center x / m'], ['source.center_y_m', 'center y / m']]) make(parent, path, label);
  }
  const armsKey = JSON.stringify([state.candidate.arm_0.actions.map(action => [action.id, action.kind]), state.candidate.arm_1.actions.map(action => [action.id, action.kind])]);
  if (polarizedTwoPathArmsKey !== armsKey) {
    polarizedTwoPathArmsKey = armsKey; const host = element('pt-arms'); host.replaceChildren();
    for (const port of [0, 1] as const) {
      const key = port === 0 ? 'arm_0' : 'arm_1', arm = state.candidate[key], block = document.createElement('section');
      const title = document.createElement('h3'); title.textContent = `arm ${port} · Ordered Terminal Actions`; block.append(title);
      for (const [index, action] of arm.actions.entries()) {
        const card = document.createElement('div'); card.className = 'pt-action';
        const select = document.createElement('button'); select.dataset.testid = `pt-select-${action.id}`; select.textContent = `${index + 1}. ${action.id} · ${action.kind}`;
        select.addEventListener('click', () => polarizedTwoPathController.select(action.id)); card.append(select);
        make(card, `${key}.actions.${index}.axis_angle_rad`, 'axis θ / rad(+x toward +y)');
        if (action.kind === 'linear_retarder') {
          make(card, `${key}.actions.${index}.retardance_rad`, 'perpendicular phase δ / rad');
          for (const [kind, phase] of [['qwp', Math.PI / 2], ['hwp', Math.PI]] as const) {
            const button = document.createElement('button'); button.dataset.testid = `pt-${kind}-${action.id}`; button.textContent = `${kind.toUpperCase()}: δ=${phase} rad`;
            button.addEventListener('click', () => void polarizedTwoPathController.edit(`${key}.actions.${index}.retardance_rad`, String(phase))); card.append(button);
          }
        }
        for (const direction of ['up', 'down', 'delete'] as const) {
          const button = document.createElement('button'); button.dataset.testid = `pt-${direction}-${action.id}`;
          button.textContent = direction === 'up' ? 'Earlier' : direction === 'down' ? 'Later' : 'Delete';
          button.disabled = direction === 'up' && index === 0 || direction === 'down' && index === arm.actions.length - 1;
          button.addEventListener('click', () => {
            const spec = structuredClone(polarizedTwoPathController.state.candidate), actions = spec[key].actions, current = actions.findIndex(item => item.id === action.id);
            if (current < 0) return;
            if (direction === 'delete') actions.splice(current, 1);
            else { const target = current + (direction === 'up' ? -1 : 1); if (target < 0 || target >= actions.length) return;
              [actions[current], actions[target]] = [actions[target], actions[current]]; }
            void polarizedTwoPathController.replaceCandidate(spec);
          }); card.append(button);
        } block.append(card);
      }
      const kinds = document.createElement('select'); kinds.dataset.testid = `pt-add-kind-${port}`;
      for (const [value, text] of [['linear_polarizer', 'Linear Polarizer'], ['linear_retarder', 'Linear Retarder']]) {
        const option = document.createElement('option'); option.value = value; option.textContent = text; kinds.append(option);
      }
      const add = document.createElement('button'); add.dataset.testid = `pt-add-${port}`; add.textContent = `Add Arm ${port} Action`; add.disabled = arm.actions.length >= 2;
      add.addEventListener('click', () => {
        const spec = structuredClone(polarizedTwoPathController.state.candidate); if (spec[key].actions.length >= 2) return;
        let id: string; do { id = `action${nextPolarizedTwoPathId++}`; } while ([...spec.arm_0.actions, ...spec.arm_1.actions].some(item => item.id === id));
        spec[key].actions.push(kinds.value === 'linear_retarder' ? { id, kind: 'linear_retarder', axis_angle_rad: 0, retardance_rad: Math.PI / 2 }
          : { id, kind: 'linear_polarizer', axis_angle_rad: 0 }); void polarizedTwoPathController.replaceCandidate(spec);
      }); block.append(kinds, add); host.append(block);
    }
  }
  element<HTMLSelectElement>('pt-source-kind').value = state.candidate.source.kind;
  element<HTMLInputElement>('pt-analyzer-enabled').checked = state.candidate.analyzer.enabled;
  for (const input of document.querySelectorAll<HTMLInputElement>('[data-pt-path]')) {
    const path = input.dataset.ptPath!, invalid = Object.hasOwn(state.invalidEdits, path); input.classList.toggle('invalid', invalid); input.setAttribute('aria-invalid', String(invalid));
    if (document.activeElement !== input) { input.value = invalid ? state.invalidEdits[path] : String(readPath(state.candidate, path)); paintNumeric(input, 'polarized_two_path', path, state, invalid); }
  }
  const topology = element('pt-topology'); topology.replaceChildren();
  for (const [id, label] of [['input', 'input / coefficients'], ['splitter', 'B'], ['arm_0', `arm 0 · ${state.candidate.arm_0.distance_m} m`],
    ['arm_1', `arm 1 · ${state.candidate.arm_1.distance_m} m · extra phase=${state.candidate.relative_phase_rad} rad`], ['combiner', 'B†'], ['analyzer', `analyzer ${state.candidate.analyzer.enabled ? 'enabled' : 'disabled'} · ${state.candidate.analyzer.axis_angle_rad} rad`], ['port_0', 'port 0'], ['port_1', 'port 1']]) {
    const button = document.createElement('button'); button.dataset.testid = `pt-select-${id}`; button.className = `component${id === state.selection ? ' selected' : ''}`;
    button.textContent = label; button.addEventListener('click', () => polarizedTwoPathController.select(id)); topology.append(button);
  }
}
function renderPolarizedTwoPathSweep(sweep: DecodedPolarizedTwoPathSweep | null, fresh: boolean): void {
  element('pt-sweep-status').textContent = !sweep ? 'No Completed Sweep' : `${fresh ? '' : 'Previous Sweep · Stale Result · '}${sweep.status === 'complete' ? 'Complete' : 'FAILED / PARTIAL'} ${sweep.completedCount}/17${sweep.error ? ` · HTTP ${sweep.httpStatus} · ${sweep.error.message}` : ''}`;
  const svg = element<SVGSVGElement & HTMLElement>('pt-sweep-chart'), body = element('pt-sweep-rows'); svg.replaceChildren(); body.replaceChildren();
  element('pt-sweep-identity').textContent = ''; element('pt-sweep-selected').textContent = ''; if (!sweep) return;
  element('pt-sweep-identity').textContent = `request=${sweep.requestId}\nfixed SHA=${sweep.fixedExperimentSha256}\nsweep SHA=${sweep.sweepSha256}\nOriginal Fixed Submission=${JSON.stringify(sweep.fixedExperiment)}`;
  const ns = 'http://www.w3.org/2000/svg', add = (tag: string, attrs: Record<string, string>, text?: string) => {
    const node = document.createElementNS(ns, tag); Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== undefined) node.textContent = text; svg.append(node); return node;
  };
  add('path', { d: 'M55 20V190H725', fill: 'none', stroke: '#8ba2b1' }); add('text', { x: '55', y: '218' }, '0 rad'); add('text', { x: '660', y: '218' }, '2π rad');
  add('text', { x: '60', y: '16' }, 'Original-Incident Ratio · Shared 0..1 Display Range; Out-of-Range/null Values Remain in the Table');
  for (const [series, color] of [['raw0', '#087f89'], ['raw1', '#9665a8'], ['analyzed0', '#c08028'], ['analyzed1', '#405cbd']] as const) {
    const port = series.endsWith('0') ? 0 : 1; let segment: string[] = [];
    const finish = () => { if (segment.length > 1) add('polyline', { points: segment.join(' '), stroke: color, fill: 'none', 'pointer-events': 'none' }); segment = []; };
    for (const row of sweep.rows) {
      const value = series.startsWith('raw') ? row.diagnostics.output_fractions[port] : row.analysis.ports?.[port].original_input_ratio ?? null;
      if (value === null || value < 0 || value > 1) { finish(); continue; }
      const x = 55 + row.index / 16 * 670, y = 190 - value * 170; segment.push(`${x},${y}`);
      const point = add('circle', { cx: String(x), cy: String(y), r: '4', fill: color, tabindex: '0', role: 'button', 'data-testid': `pt-sweep-point-${series}-${row.index}`, 'aria-label': `${series} phase ${row.phase_rad} fraction ${value}` });
      point.addEventListener('click', () => polarizedTwoPathController.selectSweepPoint(row.index));
      point.addEventListener('keydown', event => { if ((event as KeyboardEvent).key === 'Enter') polarizedTwoPathController.selectSweepPoint(row.index); });
    } finish();
  }
  for (const row of sweep.rows) {
    const tr = document.createElement('tr'); tr.dataset.index = String(row.index);
    for (const value of [String(row.index), dualValue(row.phase_rad), ...row.diagnostics.output_fractions.map(dualValue),
      dualValue(row.analysis.ports?.[0].original_input_ratio ?? null), dualValue(row.analysis.ports?.[1].original_input_ratio ?? null), JSON.stringify(row)]) {
      const td = document.createElement('td'); td.textContent = value; tr.append(td);
    } tr.addEventListener('click', () => polarizedTwoPathController.selectSweepPoint(row.index)); body.append(tr);
  }
}
function renderPolarizedTwoPath(state: PolarizedTwoPathState): void {
  if (disposed || applyingDocument || researchActive || routingActive || mode !== 'polarized_two_path') return;
  element('pt-status').textContent = state.status; element('pt-status').dataset.status = state.status;
  element('pt-error').textContent = state.error ?? ''; element('pt-error').hidden = !state.error;
  element('pt-render-error').textContent = state.renderError ?? ''; element('pt-render-error').hidden = !state.renderError;
  const ready = !!state.validatedDraft && !state.pendingValidation && !state.pendingSweepValidation && !Object.keys(state.invalidEdits).length && !operationGate.busy;
  element<HTMLButtonElement>('pt-simulate').disabled = !ready; element<HTMLButtonElement>('pt-sweep').disabled = !ready;
  element<HTMLButtonElement>('pt-simulate-phase').disabled = operationGate.busy || state.pendingSweepValidation || state.selectedSweepIndex === null;
  element<HTMLButtonElement>('pt-retry-display').disabled = !state.completedNumerical || !!state.active || !state.validatedDraft;
  renderPolarizedTwoPathFields(state);
  try {
    if (!state.currentResult && !(state.renderError && polarizedTwoPathPublished)) detachPolarizedTwoPathPresentation();
    if (state.validatedDraft && !state.renderError) scene?.updatePolarizedTwoPathExperiment(state.validatedDraft, state.selection);
    if (state.currentResult && !state.renderError && polarizedTwoPathDisplayKey !== `${state.currentResult.requestId}:${polarizedTwoPathLimits.min}:${polarizedTwoPathLimits.max}`) {
      const prepared = preparePolarizedTwoPathPresentation(state.currentResult);
      try { prepared.commit(); prepared.finalize(); } catch (error) { prepared.dispose(); throw error; }
    }
    if (polarizedTwoPathPublished) scene?.selectPolarizedTwoPathView(polarizedTwoPathPublished.analyzedPorts ? state.viewSelection : 'raw');
  } catch (error) { reportPresentation(error); }
  const view = element<HTMLSelectElement>('pt-view'); view.disabled = !state.currentResult;
  view.querySelector<HTMLOptionElement>('option[value="analyzed"]')!.disabled = !state.currentResult?.analyzedPorts;
  view.value = state.currentResult?.analyzedPorts ? state.viewSelection : 'raw';
  element('bench-label').textContent = polarizedTwoPathPublished ? `Polarized Interference ${view.value} · request=${polarizedTwoPathPublished.requestId}` : 'Ideal Polarized-Interference Schematic · No Current Result';
  const effective = polarizedTwoPathResources?.limits ?? polarizedTwoPathLimits;
  element('pt-color-info').textContent = `Shared Range for All Raw/Analyzed Images ${effective.min}..${effective.max} amplitude-unit²; The range changes only when Shared Auto Range is explicitly requested.${state.renderError ? 'The new display was not published; the previous complete display is retained.' : ''}`;
  element('pt-result-status').textContent = state.currentResult ? state.renderError ? 'Complete Numerical Measurements · New Display Failed; Previous Display Retained' : 'Current Submission · Complete Raw / Optional Analyzed Result'
    : state.completedNumerical && state.renderError ? 'Complete Numerical Measurements · Display Failed; No Partial Display Published' : state.lastResult ? 'Stale Result · Original Submission Retained Separately' : 'No Completed Simulation / Results Released';
  const previous = element('pt-previous-result'); previous.hidden = !state.lastResult || state.currentResult === state.lastResult;
  element('pt-previous-spec').textContent = state.lastResult ? `Original request=${state.lastResult.requestId}\n${JSON.stringify(state.lastResult.experiment, null, 2)}\nOriginal norms=${JSON.stringify(state.lastResult.norms)}\nOriginal analysis=${JSON.stringify(state.lastResult.analysis)}` : '';
  renderPolarizedTwoPathSweep(state.lastSweep, state.currentSweep === state.lastSweep);
  const selected = state.lastSweep?.rows.find(row => row.index === state.selectedSweepIndex);
  element('pt-sweep-selected').textContent = selected ? `Calculated Row (Selection Does Not Recalculate)=${JSON.stringify(selected)}` : '';
}
function polarizedTwoPathSnapshot(): object {
  const state = polarizedTwoPathController.state;
  const summary = (result: DecodedPolarizedTwoPathResult | null) => result ? { requestId: result.requestId, experimentSha256: result.experimentSha256,
    experiment: structuredClone(result.experiment), norms: structuredClone(result.norms), diagnostics: structuredClone(result.diagnostics), analysis: structuredClone(result.analysis),
    intensityMax: [...result.intensityMax], rawPorts: result.rawPorts.map(port => ({ id: port.id, intensityMax: port.intensityMax })),
    analyzedPorts: result.analyzedPorts?.map(port => ({ id: port.id, intensityMax: port.intensityMax })) ?? null, shape: [result.experiment.grid.ny, result.experiment.grid.nx] } : null;
  return { candidate: structuredClone(state.candidate), validatedDraft: state.validatedDraft ? structuredClone(state.validatedDraft) : null,
    revision: state.revision, attachmentEpoch: state.attachmentEpoch, resultGeneration: polarizedTwoPathController.resultGeneration,
    pendingValidation: state.pendingValidation, pendingSweepValidation: state.pendingSweepValidation, invalidEdits: { ...state.invalidEdits }, selection: state.selection,
    status: state.status, active: state.active ? structuredClone(state.active) : null, error: state.error, renderError: state.renderError,
    viewSelection: state.viewSelection, currentResult: summary(state.currentResult), lastResult: summary(state.lastResult), completedNumerical: summary(state.completedNumerical),
    lastSweep: state.lastSweep ? structuredClone(state.lastSweep) : null, currentSweep: state.currentSweep ? structuredClone(state.currentSweep) : null,
    selectedSweepIndex: state.selectedSweepIndex, selectedPixel: polarizedTwoPathSelectedPixel ? { ...polarizedTwoPathSelectedPixel } : null,
    colorLimits: { ...(polarizedTwoPathResources?.limits ?? polarizedTwoPathLimits) }, requestedColorLimits: { ...polarizedTwoPathLimits },
    resourceRoles: polarizedTwoPathResources?.textures.length ?? 0, ownership: ownedSnapshot() };
}
for (const item of POLARIZED_TWO_PATH_PRESETS) { const option = document.createElement('option'); option.value = item.id; option.textContent = item.label; element('pt-preset').append(option); }
for (const item of COEFFICIENT_PRESETS) { const option = document.createElement('option'); option.value = item.id; option.textContent = item.label; element('pt-coefficients-preset').append(option); }
element('pt-preset').addEventListener('change', () => void polarizedTwoPathController.replaceCandidate(polarizedTwoPathPreset(element<HTMLSelectElement>('pt-preset').value)));
element('pt-coefficients-preset').addEventListener('change', () => { const spec = structuredClone(polarizedTwoPathController.state.candidate);
  spec.coefficients = structuredClone(COEFFICIENT_PRESETS.find(item => item.id === element<HTMLSelectElement>('pt-coefficients-preset').value)!.coefficients); void polarizedTwoPathController.replaceCandidate(spec); });
element('pt-source-kind').addEventListener('change', () => { const spec = structuredClone(polarizedTwoPathController.state.candidate), { amplitude, phase_rad } = spec.source;
  spec.source = element<HTMLSelectElement>('pt-source-kind').value === 'uniform' ? { kind: 'uniform', amplitude, phase_rad }
    : { kind: 'gaussian', amplitude, phase_rad, waist_radius_m: 50e-6, waist_z_m: 0, center_x_m: 0, center_y_m: 0 }; void polarizedTwoPathController.replaceCandidate(spec); });
element('pt-analyzer-enabled').addEventListener('change', () => { const spec = structuredClone(polarizedTwoPathController.state.candidate);
  spec.analyzer.enabled = element<HTMLInputElement>('pt-analyzer-enabled').checked; void polarizedTwoPathController.replaceCandidate(spec); });
for (const [id, phase] of [['pt-phase-0', 0], ['pt-phase-halfpi', Math.PI / 2], ['pt-phase-pi', Math.PI]] as const) element(id).addEventListener('click', () => void polarizedTwoPathController.edit('relative_phase_rad', String(phase)));
element('pt-simulate').addEventListener('click', () => void polarizedTwoPathController.simulate());
element('pt-sweep').addEventListener('click', () => void polarizedTwoPathController.runSweep());
element('pt-simulate-phase').addEventListener('click', () => void polarizedTwoPathController.applySelectedPhaseAndSimulate());
element('pt-retry-display').addEventListener('click', () => void polarizedTwoPathController.retryPresentation());
element('pt-view').addEventListener('change', () => { try { polarizedTwoPathController.selectView(element<HTMLSelectElement>('pt-view').value === 'analyzed' ? 'analyzed' : 'raw'); } catch (error) { notice(String(error)); } });
for (const id of ['pt-color-min', 'pt-color-max']) element(id).addEventListener('change', () => { try {
  const next = { min: Number(element<HTMLInputElement>('pt-color-min').value), max: Number(element<HTMLInputElement>('pt-color-max').value) };
  validateColorLimits(next); polarizedTwoPathLimits = next; polarizedTwoPathController.reportRenderFailure(null);
} catch (error) { notice(String(error)); } });
element('pt-auto-color').addEventListener('click', () => { const result = polarizedTwoPathController.state.currentResult; if (!result) return;
  const maximum = Math.max(...result.intensityMax); polarizedTwoPathLimits = { min: 0, max: maximum > 0 ? maximum : 1 };
  element<HTMLInputElement>('pt-color-min').value = '0'; element<HTMLInputElement>('pt-color-max').value = String(polarizedTwoPathLimits.max); polarizedTwoPathController.reportRenderFailure(null); });
polarizedTwoPathController.setResultPreparer(preparePolarizedTwoPathPresentation);
polarizedTwoPathController.setOperationAdmission((kind, experiment) => admitOperation('polarized_two_path', experiment.grid, kind, experiment.analyzer.enabled));

element('release-results').addEventListener('click', () => {
  // Recheck actual numerical ownership on execution, including programmatic clicks.
  if (operationGate.busy || [controller, twoPathController, polarizationController, polarizedTwoPathController, idealController].some(actor => !!actor.state.active)) {
    element('release-status').textContent = 'Computation is still active; no results were released.'; return;
  }
  ++resultAttachmentGeneration; applyingDocument = true;
  try {
    for (const actor of [controller, twoPathController, polarizationController, polarizedTwoPathController]) actor.releaseResults();
    idealWorkspace?.releaseResults(); waveWorkspace?.releaseResults(); routingWorkspace?.releaseResults();
    scene?.releaseRetainedResults(); polarizationPlayback.detach(); polarizationResources?.dispose(); polarizedTwoPathResources?.dispose();
    polarizationResources = null; polarizedTwoPathResources = null; polarizationPublished = null; polarizedTwoPathPublished = null;
    displayedResult = null; dualPublished = null; selectedPixel = null; dualSelectedPixel = null; polarizationSelectedPixel = null; polarizedTwoPathSelectedPixel = null;
    displayKey = ''; dualDisplayKey = ''; priorDisplayKey = ''; polarizationDisplayKey = ''; polarizedTwoPathDisplayKey = '';
    for (const id of ['tp-result-area', 'pl-result-area', 'pt-result-area']) dropResultCanvases(element(id));
    element<HTMLCanvasElement>('intensity').width = 0; element<HTMLCanvasElement>('intensity').height = 0;
    for (const id of ['tp-current-content', 'tp-prior-images', 'pl-current-content', 'pt-current-content', 'stages', 'stage', 'tp-sweep-rows', 'pl-sweep-rows', 'pt-sweep-rows',
      'tp-sweep-chart', 'pl-sweep-chart', 'pt-sweep-chart', 'pick-choices']) element(id).replaceChildren();
    for (const id of ['result-identity', 'result-spec', 'pixel-readout', 'raw-max', 'stage-note', 'tp-previous-spec', 'pl-previous-spec', 'pt-previous-spec',
      'tp-sweep-identity', 'pl-sweep-identity', 'pt-sweep-identity', 'tp-sweep-selected', 'pl-sweep-selected', 'pt-sweep-selected']) element(id).textContent = '';
    for (const id of ['tp-previous-result', 'pl-previous-result', 'pt-previous-result', 'intensity-holder', 'saturation']) element(id).hidden = true;
    ++releasedResultsCount;
  } finally { applyingDocument = false; }
  element('release-status').textContent = 'Retained results were released across all modes. Settings, invalid edits, camera views, and documents are preserved. No simulation has been rerun.';
  element('result-status').textContent = 'Results Released · No New Simulation';
  if (mode === 'sequential') render(controller.state); else if (mode === 'two_path') renderTwoPath(twoPathController.state);
  else if (mode === 'polarization') renderPolarization(polarizationController.state); else renderPolarizedTwoPath(polarizedTwoPathController.state);
  renderDocuments();
});

function documentContext() {
  return { mode, token: [controller.state.revision, controller.state.attachmentEpoch,
    twoPathController.state.revision, twoPathController.state.attachmentEpoch,
    polarizationController.state.revision, polarizationController.state.attachmentEpoch,
    polarizedTwoPathController.state.revision, polarizedTwoPathController.state.attachmentEpoch].join(':') };
}
function currentDocumentDraft() {
  const state = mode === 'sequential' ? controller.state : mode === 'two_path' ? twoPathController.state
    : mode === 'polarization' ? polarizationController.state : polarizedTwoPathController.state;
  if (!state.validatedDraft || state.pendingValidation || Object.keys(state.invalidEdits).length) return null;
  return { mode, experiment: state.validatedDraft, revision: state.revision, attachmentEpoch: state.attachmentEpoch };
}
function prepareDocumentApplication(validated: SupportedValidatedDocument): () => void {
  const doc = validated.document;
  const commit = doc.mode === 'sequential'
    ? controller.prepareValidatedSettings(doc.experiment, validated.experimentSha256)
    : doc.mode === 'two_path'
      ? twoPathController.prepareValidatedSettings(doc.experiment, validated.experimentSha256)
      : doc.mode === 'polarization' ? polarizationController.prepareValidatedSettings(doc.experiment, validated.experimentSha256)
        : polarizedTwoPathController.prepareValidatedSettings(doc.experiment, validated.experimentSha256);
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
  document.querySelector<HTMLElement>('.bench-help')!.textContent = mode === 'polarized_two_path'
    ? 'Orbit, pan, zoom, and selection affect presentation only. Positions in the ideal unfolded schematic add no propagation; switching raw/analyzed views does not recalculate.'
    : mode === 'polarization'
    ? 'Orbit, pan, zoom, and selection affect presentation only. All actions share one reference plane; schematic spacing has no optical effect. z dragging is unavailable.'
    : mode === 'two_path'
      ? 'Orbit, pan, zoom, and selection affect presentation only. The fixed unfolded train cannot be dragged. Dashed lines are guides only.'
      : 'Left-drag to orbit · Right-drag to pan · Scroll to zoom · Click to select; Orange handles drag along z only.';
}
function presentDocumentApplication(): void {
  // Presentation is subsequent to the coherent settings commit and fails separately.
  app!.dataset.mode = mode; element<HTMLSelectElement>('mode').value = mode;
  waveWorkspace?.setActive(!researchActive && !routingActive && mode === 'sequential');
  try {
    ++resultAttachmentGeneration; detachPolarizedTwoPathPresentation();
    detachPolarizationPresentation(); scene?.updateResult(null, limits); scene?.detachDualResult();
    dualPublished = null; dualSelectedPixel = null; dualDisplayKey = ''; displayedResult = null; displayKey = '';
    selectedPixel = null; priorDisplayKey = ''; inspectorKey = ''; dualFieldsKey = '';
    polarizationFieldsKey = ''; polarizationInspectorKey = '';
    polarizedTwoPathFieldsKey = ''; polarizedTwoPathArmsKey = '';
    dropResultCanvases(element('tp-result-area'));
    element<HTMLCanvasElement>('intensity').width = 0; element<HTMLCanvasElement>('intensity').height = 0;
    element('intensity-holder').hidden = true; element('tp-current-content').replaceChildren(); element('tp-prior-images').replaceChildren();
    element('pick-choices').replaceChildren(); renderModeHelp();
    if (mode === 'sequential') render(controller.state);
    else if (mode === 'two_path') renderTwoPath(twoPathController.state);
    else if (mode === 'polarization') renderPolarization(polarizationController.state);
    else renderPolarizedTwoPath(polarizedTwoPathController.state);
  } catch (error) { reportPresentation(error); }
}
const modeLabel: Record<SupportedBenchMode, string> = { sequential: 'Sequential Optics', two_path: 'Two-Path Interference', polarization: 'Jones Polarization', polarized_two_path: 'Polarized Interference' };
function renderDocuments(): void {
  if (!documents || disposed) return;
  const state = documents.state, metadata = state.metadata[mode];
  const title = element<HTMLInputElement>('doc-title'), notes = element<HTMLTextAreaElement>('doc-notes');
  if (document.activeElement !== title) title.value = metadata.title;
  if (document.activeElement !== notes) notes.value = metadata.notes;
  const errors = [state.error, state.metadataErrors[mode]].filter(Boolean);
  element('doc-error').textContent = errors.join(' · '); element('doc-error').hidden = errors.length === 0;
  const labels = { idle: 'Settings files contain settings only. Submit simulations separately.', reading: 'Reading Settings File', validating: 'Validating Settings File',
    preview: 'Settings validated. Review and confirm replacement.', download_prepared: 'Download Prepared', download_requested: 'Download Requested',
    restored: 'Settings Restored; Simulation Not Run', error: 'Settings operation incomplete. Check error details.' };
  const current = mode === 'sequential' ? controller.state.currentResult : mode === 'two_path' ? twoPathController.state.currentResult
    : mode === 'polarization' ? polarizationController.state.currentResult : polarizedTwoPathController.state.currentResult;
  element('doc-status').textContent = state.status === 'restored' && current
    ? 'Settings restored; a separately submitted simulation result is available.' : labels[state.status];
  element('doc-status').dataset.status = state.status;
  element<HTMLButtonElement>('doc-export').disabled = !currentDocumentDraft() || !!state.metadataErrors[mode];
  const prepared = state.preparedDownload, link = element<HTMLAnchorElement>('doc-download');
  element('doc-download-area').hidden = !prepared;
  if (prepared) {
    link.href = prepared.url; link.download = prepared.filename;
    element('doc-download-label').textContent = `${modeLabel[prepared.document.mode]} · Captured Valid Draft Revision ${prepared.revision} (Settings File Excludes Results)`;
  } else { link.removeAttribute('href'); link.removeAttribute('download'); }
  const preview = state.preview;
  element('doc-preview').hidden = !preview;
  element<HTMLInputElement>('doc-ack').checked = state.acknowledged;
  element<HTMLButtonElement>('doc-apply').disabled = !preview || !state.acknowledged || state.pending || operationGate.busy;
  if (preview) {
    const doc = preview.document, exp = doc.experiment;
    element('doc-preview-text').textContent = `Mode: ${modeLabel[doc.mode]}\nTitle: ${doc.metadata.title}\nNotes: ${doc.metadata.notes}\n` +
      `Grid: ${exp.grid.ny} × ${exp.grid.nx}; dx=${exp.grid.dx} m; dy=${exp.grid.dy} m\nWavelength: ${exp.wavelength_m} m\n` +
      `Complete Settings (SI / rad; Simulation Not Run): \n${JSON.stringify(exp, null, 2)}`;
  } else element('doc-preview-text').textContent = '';
}
documents = new ExperimentDocumentController<SupportedBenchMode>({ context: documentContext, currentValidDraft: currentDocumentDraft,
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
  ++resultAttachmentGeneration;
  controller.deactivate(); twoPathController.deactivate(); polarizationController.deactivate(); polarizedTwoPathController.deactivate();
  detachPolarizationPresentation(); detachPolarizedTwoPathPresentation();
  scene?.updateResult(null, limits); scene?.detachDualResult();
  const chosen = element<HTMLSelectElement>('mode').value;
  mode = chosen === 'polarized_two_path' ? 'polarized_two_path' : chosen === 'polarization' ? 'polarization' : chosen === 'two_path' ? 'two_path' : 'sequential'; app!.dataset.mode = mode;
  waveWorkspace?.setActive(!researchActive && !routingActive && mode === 'sequential');
  dualPublished = null; dualSelectedPixel = null; dualDisplayKey = ''; displayedResult = null; displayKey = '';
  dropResultCanvases(element('tp-result-area'));
  element('tp-current-content').replaceChildren(); element('tp-prior-images').replaceChildren(); priorDisplayKey = '';
  const legacyCanvas = element<HTMLCanvasElement>('intensity'); legacyCanvas.width = 0; legacyCanvas.height = 0;
  element('intensity-holder').hidden = true;
  renderModeHelp();
  element('pick-choices').replaceChildren();
  if (mode === 'two_path') { renderTwoPath(twoPathController.state); void twoPathController.activate(); }
  else if (mode === 'polarization') { renderPolarization(polarizationController.state); void polarizationController.activate(); }
  else if (mode === 'polarized_two_path') { renderPolarizedTwoPath(polarizedTwoPathController.state); void polarizedTwoPathController.activate(); }
  else { render(controller.state); void controller.activate(); }
  documents!.contextChanged(); renderDocuments();
});
twoPathController.setResultPreparer(prepareDualPresentation);
controller.subscribe(render); twoPathController.subscribe(renderTwoPath); polarizationController.subscribe(renderPolarization); polarizedTwoPathController.subscribe(renderPolarizedTwoPath);
for (const actor of [controller, twoPathController, polarizationController, polarizedTwoPathController]) actor.subscribe(() => {
  if (!applyingDocument && !documents!.isApplying) { documents!.contextChanged(); renderDocuments(); }
});
operationGate.subscribe(() => {
  if (!operationGate.busy) scientificReservations = { persistent: 0, transient: 0 };
  renderDocuments();
  element<HTMLButtonElement>('release-results').disabled = operationGate.busy;
  if (mode === 'sequential') element<HTMLButtonElement>('simulate').disabled = operationGate.busy || !controller.state.validatedDraft || controller.state.pendingValidation || !!Object.keys(controller.state.invalidEdits).length;
  else if (mode === 'polarization') {
    const state = polarizationController.state, ready = !operationGate.busy && !!state.validatedDraft && !state.pendingValidation && !Object.keys(state.invalidEdits).length;
    element<HTMLButtonElement>('pl-simulate').disabled = !ready;
    element<HTMLButtonElement>('pl-sweep').disabled = !ready || !state.candidate.elements.some(item => item.id === state.selection && item.kind === 'linear_polarizer');
  } else if (mode === 'polarized_two_path') {
    const state = polarizedTwoPathController.state, ready = !operationGate.busy && !state.pendingSweepValidation && !!state.validatedDraft && !state.pendingValidation && !Object.keys(state.invalidEdits).length;
    element<HTMLButtonElement>('pt-simulate').disabled = !ready; element<HTMLButtonElement>('pt-sweep').disabled = !ready;
  } else {
    const state = twoPathController.state; const ready = !operationGate.busy && !!state.validatedDraft && !state.pendingValidation && !Object.keys(state.invalidEdits).length;
    element<HTMLButtonElement>('tp-simulate').disabled = !ready; element<HTMLButtonElement>('tp-sweep').disabled = !ready || state.candidate.grid.nx > 128 || state.candidate.grid.ny > 128;
  }
});
function admitIdeal(extraPersistent: number, extraTransient: number): void {
  const own = ownedSnapshot().retainedBytes, reservation = documents?.ownershipSnapshot();
  assertOwnedBudgets(own + extraPersistent + (reservation?.projectedPersistentBytes ?? 0),
    own + extraTransient + (reservation?.transientReservedBytes ?? 0));
}
idealWorkspace = new R03Workspace(element('r03-workspace'), idealController, scene, { admit: admitIdeal,
  chrome: { navigation: app.querySelector<HTMLElement>('.workspace-navigation')!, releaseButton: element<HTMLButtonElement>('release-results'), releaseStatus: element('release-status') },
  reserveOperation(persistent, transient) { admitIdeal(persistent, transient); scientificReservations = { persistent, transient }; } });
waveController = new WaveFieldController(controller, { admit: admitIdeal,
  reserveOperation(persistent, transient) { admitIdeal(persistent, transient); scientificReservations = { persistent, transient }; } });
// The dock belongs to the existing three-column bench, not a second dashboard.
app.querySelector<HTMLElement>('.workspace')!.append(element('w1-workspace'));
waveController.subscribe(() => {
  const active = waveController!.enabled && mode === 'sequential' && !researchActive && !routingActive;
  app!.dataset.computedSections = String(active); element('w1-view').setAttribute('aria-pressed', String(active));
  if (active) { element('bench-label').textContent = waveController!.state.currentResult ? 'Computed Sections · Shared Range · Sparse Physical Planes' : 'No Field Attached · Press Simulate Explicitly'; }
  else if (!researchActive && !routingActive && mode === 'sequential') element('bench-label').textContent = sequentialBenchLabel(controller.state);
});
waveWorkspace = new WaveFieldWorkspace(element('w1-workspace'), scene, waveController, { admit: admitIdeal,
  cursorHost: element('w1-bench-controls'), editorHost: element('inspector'),
  loadExample: () => { controller.select('source'); void controller.replaceCandidate(cloneExperiment(W1_EXAMPLE)); }, select: id => controller.select(id) });
waveWorkspace.setActive(true);
app.querySelector<HTMLElement>('.workspace')!.append(element('w2-workspace'));
function ensureRoutingWorkspace(): void {
  if (routingWorkspace) return;
  // Static module code/preset constants are not a browser-heap measurement.
  // Instantiate and admit W2's owned state/DOM only when it is first requested.
  admitIdeal(512 * 1024, 512 * 1024);
  routingController = new GeometricRoutingController(W2_PRESETS.A, { gate: operationGate, admit: admitIdeal,
    reserveOperation(persistent, transient) { admitIdeal(persistent, transient); scientificReservations = { persistent, transient }; } });
  routingWorkspace = new GeometricRoutingWorkspace(element('w2-workspace'), routingController, scene, { admit: admitIdeal,
    labelHost: element('bench'), navigationHost: element('w2-controls') });
  routingController.subscribe(() => {
    if (routingActive) element('bench-label').textContent = routingController!.state.currentResult
      ? 'Computed Geometric Routes · Uniform SI Scale · Visibility-Aid Lines'
      : 'No Current Route · Press Trace Explicitly';
  });
}
function switchWorkspace(target: 'ordinary' | 'research' | 'geometric_routing'): void {
  const previous = routingActive ? 'geometric_routing' : researchActive ? 'research' : 'ordinary';
  if (previous === target) return;
  if (target === 'geometric_routing') {
    try { ensureRoutingWorkspace(); }
    catch (error) { element('render-error').textContent = String(error); element('render-error').hidden = false; return; }
  }
  if (previous === 'geometric_routing') routingWorkspace!.setActive(false);
  if (previous === 'research') idealWorkspace!.leave();
  if (previous === 'ordinary') {
    waveWorkspace?.setActive(false);
    for (const actor of [controller, twoPathController, polarizationController, polarizedTwoPathController]) actor.deactivate();
    polarizationPlayback.detach(); scene?.setFrameCallback(null);
  }
  researchActive = target === 'research'; routingActive = target === 'geometric_routing'; app!.dataset.workspace = target;
  const headerDetail = app!.querySelector<HTMLElement>('.header-detail')!;
  headerDetail.firstChild!.nodeValue = routingActive ? 'Geometric Rays · Finite Ideal Surfaces' : 'Monochromatic · Scalar · Aligned Forward Optics';
  headerDetail.querySelector('span')!.textContent = routingActive ? 'Relative Weights · Explicit Trace' : 'Local Operation / Explicit Submission';
  element('research-workspace').classList.toggle('selected', researchActive);
  element('geometric-routing-workspace').classList.toggle('selected', routingActive);
  element('ordinary-workspace').classList.toggle('selected', target === 'ordinary');
  if (researchActive) idealWorkspace!.enter();
  else if (routingActive) { routingWorkspace!.setActive(true); element('bench-label').textContent = 'No Current Route · Press Trace Explicitly'; }
  else {
    waveWorkspace?.setActive(mode === 'sequential');
    if (mode === 'sequential') { render(controller.state); void controller.validateInitial(); }
    else if (mode === 'two_path') { renderTwoPath(twoPathController.state); void twoPathController.activate(); }
    else if (mode === 'polarization') { renderPolarization(polarizationController.state); void polarizationController.activate(); }
    else { renderPolarizedTwoPath(polarizedTwoPathController.state); void polarizedTwoPathController.activate(); }
  }
}
element('research-workspace').addEventListener('click', () => switchWorkspace('research'));
element('ordinary-workspace').addEventListener('click', () => switchWorkspace('ordinary'));
element('geometric-routing-workspace').addEventListener('click', () => switchWorkspace('geometric_routing'));
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
    workspace: routingActive ? 'geometric_routing' : researchActive ? 'research' : 'ordinary',
    geometricRouting: routingWorkspace?.snapshot() ?? null,
    idealPolarization: idealWorkspace?.snapshot() ?? null,
    waveField: waveWorkspace?.snapshot() ?? null,
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
    polarizedTwoPath: polarizedTwoPathSnapshot(),
    resultRelease: { count: releasedResultsCount, generation: resultAttachmentGeneration, busy: operationGate.busy },
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
      polarizedTwoPathPixelWorld: (port: 0 | 1, row: number, column: number) => { x: number; y: number; z: number } | null;
    };
  }
}
Object.defineProperty(window, '__benchDebug', { value: Object.freeze({
  snapshot: stateSnapshot,
  worldToClient: (x: number, y: number, z: number) => scene?.worldToClient(x, y, z) ?? null,
  dualPixelWorld: (port: 0 | 1, row: number, column: number) => scene?.dualPixelWorld(port, row, column) ?? null,
  polarizedTwoPathPixelWorld: (port: 0 | 1, row: number, column: number) => scene?.polarizedTwoPathPixelWorld(port, row, column) ?? null,
}), writable: false, configurable: false });
window.addEventListener('pagehide', () => { disposed = true; routingWorkspace?.dispose(); waveWorkspace?.dispose(); idealWorkspace?.dispose(); documents?.dispose(); polarizationPlayback.detach(); polarizationResources?.dispose(); polarizedTwoPathResources?.dispose(); scene?.dispose(); }, { once: true });
