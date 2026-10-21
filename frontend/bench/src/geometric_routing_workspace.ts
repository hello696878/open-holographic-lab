/** Integrated English W2 workspace. Only the Trace button requests geometric computation. */
import * as THREE from 'three';
import { NumericFieldBinding } from './numeric_fields';
import { createGeometricRoutingApparatus, prepareGeometricRoutingDisplay, type GeometricRoutingApparatus, type GeometricRoutingDisplay } from './geometric_routing_apparatus';
import { W2_PRESETS, W2_RETAINED_RESERVATION, assertGeometricScene, routingMetadataReservation, routingResourceBreakdown, type GeometricScene,
  routingStructuralEqual, type GeometricTraceResult, type RoutingKind, type RoutingSurfaceFrame } from './geometric_routing_contracts';
import { GeometricRoutingController, type GeometricRoutingPrepared, type GeometricRoutingState } from './geometric_routing_state';

export interface GeometricRoutingScenePort {
  showGeometricRoutingApparatus(group: THREE.Group): void;
  replaceGeometricRoutingApparatus(group: THREE.Group): void;
  hideGeometricRoutingApparatus(): void;
  fitGeometricRoutingApparatus(bounds: THREE.Box3, view: 'overview' | 'top' | 'focus'): void;
  setGeometricRoutingLabelUpdater(update: ((camera: THREE.PerspectiveCamera, width: number, height: number) => void) | null): void;
  assertGeometricRoutingReady(): void;
}
export interface GeometricRoutingWorkspaceOptions {
  admit(persistent: number, transient: number): void; readonly labelHost?: HTMLElement; readonly navigationHost?: HTMLElement;
}
export interface GeometricRoutingHitIdentity {
  readonly requestId: string; readonly sceneSha256: string; readonly hitId: string;
}
/** Resolve a presentation selection only against its current accepted trace. */
export function resolveCurrentRoutingHit(result: GeometricTraceResult | null, selection: GeometricRoutingHitIdentity | null): GeometricTraceResult['hits'][number] | null {
  if (!result || !selection || result.request_id !== selection.requestId || result.scene_sha256 !== selection.sceneSha256) return null;
  return result.hits.find(hit => hit.id === selection.hitId) ?? null;
}
function hitIdentity(result: GeometricTraceResult, hitId: string): GeometricRoutingHitIdentity {
  return Object.freeze({ requestId: result.request_id, sceneSha256: result.scene_sha256, hitId });
}
const names: Readonly<Record<RoutingKind, string>> = { mirror: 'Mirror', ideal_splitter_50_50: 'Ideal 50:50 Splitter', beam_stop: 'Beam Stop', receiver: 'Receiver' };
const units = ['X', 'Y', 'Z'] as const;
interface Field { readonly input: HTMLInputElement; readonly binding: NumericFieldBinding; readonly path: string; readonly scale: number; readonly value: () => number }
export const W2_DOM_RESERVATION_CAP = 1024 * 1024;
/** Explicit app-owned DOM/attribute/text reservation; excludes native DOM and engine heap. */
export function measureRoutingDOMReservation(roots: readonly Node[]): number {
  const seen = new Set<Node>(); let bytes = 4096;
  const visit = (node: Node): void => {
    if (seen.has(node)) return; seen.add(node); bytes += 256 + node.childNodes.length * 16;
    if (node.nodeType === 3) bytes += (node.nodeValue?.length ?? 0) * 2;
    if (node.nodeType === 1) {
      const element = node as Element & { value?: string };
      for (const attribute of Array.from(element.attributes)) bytes += 48 + (attribute.name.length + attribute.value.length) * 2;
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(element.tagName) && typeof element.value === 'string') bytes += element.value.length * 2;
    }
    for (const child of Array.from(node.childNodes)) visit(child);
  }; roots.forEach(visit); return bytes;
}
const numberText = (value: number): string => Object.is(value, -0) ? '-0' : String(value);
function span(text: string): HTMLSpanElement { const item = document.createElement('span'); item.textContent = text; return item; }

export class GeometricRoutingWorkspace {
  private active = false; private disposed = false; private mounted = false; private hasFramed = false;
  private apparatus: GeometricRoutingApparatus | null = null; private apparatusScene: GeometricScene | null = null;
  private apparatusFrames: readonly RoutingSurfaceFrame[] | null = null; private resource: GeometricRoutingDisplay | null = null;
  private readonly displays = new Set<GeometricRoutingDisplay>(); private readonly fields: Field[] = [];
  private selectedBranch: string | null = null; private selectedHitIdentity: GeometricRoutingHitIdentity | null = null; private editorIdentity = '';
  private resultIdentity: GeometricTraceResult | null = null; private resultCurrent = false; private readonly navigation: HTMLElement;
  private readonly unsubscribe: () => void; private readonly unsubscribeGate: () => void;
  constructor(readonly host: HTMLElement, readonly controller: GeometricRoutingController, private readonly scene: GeometricRoutingScenePort | null,
      private readonly options: GeometricRoutingWorkspaceOptions) {
    host.classList.add('w2-workspace'); host.hidden = true;
    const navigation = document.createElement('section'); navigation.className = 'w2-navigation'; navigation.setAttribute('aria-label', 'Geometric routing controls');
    navigation.innerHTML = `<div class="w2-heading"><div><span class="eyebrow">W2 / COMPUTED GEOMETRIC ROUTING</span><h2>Geometric Routing</h2><p>Finite ideal surfaces. Actual intersections. Explicit tracing.</p></div>
      <output data-testid="w2-status" class="w2-status" aria-live="polite">Draft / not traced</output></div>
      <div class="w2-actions"><label>Apparatus <select data-testid="w2-preset" aria-label="Routing apparatus preset"><option value="A">A / One-mirror fold</option><option value="B">B / Two-mirror fold</option><option value="C">C / Split and blocked branch</option></select></label>
      <button type="button" data-testid="w2-load-preset">Load Preset</button><button type="button" class="primary" data-testid="w2-trace">Trace</button>
      <div class="w2-camera-controls" role="group" aria-label="Routing camera"><button type="button" data-testid="w2-orbit">Orbit</button><button type="button" data-testid="w2-top">Top View</button><button type="button" data-testid="w2-focus">Focus</button><button type="button" data-testid="w2-reset">Reset View</button></div></div>
      <p class="w2-legend">Calculated ideal geometric paths / SI metres / right-handed Y-up. Amber and teal show branch identity. Glow and line thickness are visibility aids, not beam width or optical power.</p>
      <p class="error" role="alert" data-testid="w2-error" hidden></p><p class="error" role="alert" data-testid="w2-display-error" hidden></p>
      <button type="button" data-testid="w2-retry-display" hidden>Restore Display (No Recalculation)</button>`;
    this.navigation = navigation; if (options.navigationHost) { options.navigationHost.classList.add('w2-controls'); options.navigationHost.append(navigation); options.navigationHost.hidden = true; } else host.before(navigation);
    host.innerHTML = `<aside class="w2-left panel"><div class="w2-panel-heading"><span class="eyebrow">APPARATUS</span><h2>Finite Optical Elements</h2></div>
      <p class="w2-note">Hit order is calculated from geometry, independent of this list.</p><div data-testid="w2-components" class="w2-components"></div>
      <div class="w2-add-controls"><label>Add Element <select data-testid="w2-add-kind"><option value="mirror">Mirror</option><option value="ideal_splitter_50_50">Ideal 50:50 Splitter</option><option value="beam_stop">Beam Stop</option><option value="receiver">Receiver</option></select></label>
      <button type="button" data-testid="w2-add">Add Element</button><button type="button" data-testid="w2-remove">Remove Selected</button></div>
      <p class="w2-model-note">One explicit ray. Two-sided ideal planes. Housings and mounts are decorative and do not block rays. No diffraction, polarization or interference.</p>
      <p class="w2-document-note" data-testid="w2-documents-unsupported">Routing scene import/export is not supported in this slice. Existing experiment settings remain available in their original workspaces.</p></aside>
      <aside class="w2-right panel"><nav class="w2-tabs" role="tablist" aria-label="Routing inspection"><button type="button" id="w2-tab-inspector" data-testid="w2-tab-inspector" role="tab" aria-selected="true" aria-controls="w2-panel-inspector">Inspector</button>
      <button type="button" id="w2-tab-data" data-testid="w2-tab-data" role="tab" aria-selected="false" aria-controls="w2-panel-data" tabindex="-1">Trace Data</button></nav>
      <section id="w2-panel-inspector" role="tabpanel" aria-labelledby="w2-tab-inspector"><span class="eyebrow">SELECTED COMPONENT</span><h3 data-testid="w2-selected">Source</h3>
      <div data-testid="w2-editor" class="w2-editor-grid"></div><p class="w2-note">Changing one field preserves untouched SI components. X/Y/Z rotations apply actively in X, then Y, then Z order. Only Trace recomputes.</p>
      <div class="w2-selection-details" data-testid="w2-selected-hit"></div></section>
      <section id="w2-panel-data" role="tabpanel" aria-labelledby="w2-tab-data" hidden><output class="w2-result-state" data-testid="w2-result-state">No calculated result</output>
      <div class="w2-identity w2-table-scroll" tabindex="0" role="region" aria-label="Full result identity" data-testid="w2-identity"></div>
      <div class="w2-ledger" data-testid="w2-ledger"></div><p class="w2-note" data-testid="w2-accounting-note">Relative ray weights, not watts or irradiance. Computational truncation remains separate from absorption.</p>
      <label class="w2-branch-control">Inspect Branch <select data-testid="w2-branch" aria-label="Inspect calculated branch"><option value="">All branches</option></select></label>
      <div class="w2-table-scroll" role="region" tabindex="0" aria-label="Branch terminal outcomes, horizontally scrollable" data-testid="w2-terminals"></div>
      <div class="w2-table-scroll" role="region" tabindex="0" aria-label="Actual calculated hits, horizontally scrollable" data-testid="w2-hits"></div>
      <output class="w2-timings" data-testid="w2-timings"></output></section></aside>`;
    this.node('w2-load-preset').addEventListener('click', () => { const preset = this.node<HTMLSelectElement>('w2-preset').value as keyof typeof W2_PRESETS; this.hasFramed = false; void controller.setPreset(preset); });
    this.node('w2-trace').addEventListener('click', () => { void controller.trace(); });
    this.node('w2-add').addEventListener('click', () => { this.tab('inspector'); void controller.add(this.node<HTMLSelectElement>('w2-add-kind').value as RoutingKind); });
    this.node('w2-remove').addEventListener('click', () => { void controller.remove(); });
    this.node('w2-retry-display').addEventListener('click', () => { controller.retryPresentation(); });
    this.node<HTMLSelectElement>('w2-branch').addEventListener('change', event => { this.selectedBranch = (event.target as HTMLSelectElement).value || null; this.resource?.selectBranch(this.selectedBranch); this.updateResult(true); });
    for (const [id, view] of [['w2-orbit', 'overview'], ['w2-top', 'top'], ['w2-focus', 'focus'], ['w2-reset', 'overview']] as const) this.node(id).addEventListener('click', () => this.camera(view));
    for (const tab of ['inspector', 'data'] as const) {
      this.node(`w2-tab-${tab}`).addEventListener('click', () => this.tab(tab));
      this.node(`w2-tab-${tab}`).addEventListener('keydown', event => { if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return; event.preventDefault(); const next = event.key === 'Home' ? 'inspector' : event.key === 'End' ? 'data' : tab === 'inspector' ? 'data' : 'inspector'; this.tab(next); this.node(`w2-tab-${next}`).focus(); });
    }
    controller.bindPresentation(result => this.prepare(result)); this.unsubscribe = controller.subscribe(state => this.render(state)); this.unsubscribeGate = controller.gate.subscribe(() => this.render(controller.state));
  }
  private node<T extends HTMLElement = HTMLElement>(id: string): T {
    const node = this.host.querySelector<T>(`[data-testid="${id}"]`) ?? this.navigation.querySelector<T>(`[data-testid="${id}"]`);
    if (!node) throw new Error(`Missing Geometric Routing area: ${id}`); return node;
  }
  private tab(tab: 'inspector' | 'data'): void {
    for (const item of ['inspector', 'data'] as const) { const selected = item === tab, button = this.node<HTMLButtonElement>(`w2-tab-${item}`);
      button.setAttribute('aria-selected', String(selected)); button.tabIndex = selected ? 0 : -1; this.host.querySelector<HTMLElement>(`#w2-panel-${item}`)!.hidden = !selected; }
  }
  setActive(active: boolean): void {
    if (this.disposed || this.active === active) return; this.active = active; this.host.hidden = !active;
    if (this.options.navigationHost) this.options.navigationHost.hidden = !active; this.navigation.hidden = !active;
    if (active) void this.controller.activate(); else this.controller.deactivate(); this.render(this.controller.state);
  }
  selectElement(id: string): void { this.controller.select(id); this.tab('inspector'); }
  private syncApparatus(state: GeometricRoutingState): void {
    if (!this.active) { if (this.mounted) this.scene?.hideGeometricRoutingApparatus(); this.apparatus?.setLabelsVisible(false); this.mounted = false; this.scene?.setGeometricRoutingLabelUpdater(null); return; }
    const draft = state.validatedDraft ?? state.candidate;
    try { assertGeometricScene(draft); } catch { this.apparatus?.setDisplay(null); return; }
    if (!this.scene) throw new Error('The existing WebGL scene is unavailable. No substitute calculated path is displayed.');
    if (!this.apparatus || !routingStructuralEqual(this.apparatusScene, draft) || !routingStructuralEqual(this.apparatusFrames, state.surfaceFrames)) {
      // Reserve the static apparatus before constructing any replacement alongside the old one.
      this.options.admit(512 * 1024, 512 * 1024);
      const next = createGeometricRoutingApparatus(draft, { frames: state.surfaceFrames ?? undefined, labelHost: this.options.labelHost, onSelect: id => this.selectElement(id) }), previous = this.apparatus;
      try {
        if (this.mounted) this.scene.replaceGeometricRoutingApparatus(next.group); else this.scene.showGeometricRoutingApparatus(next.group);
        this.apparatus = next; this.apparatusScene = draft; this.apparatusFrames = state.surfaceFrames; this.mounted = true;
        if (this.resource && state.currentResult === this.resource.result) next.setDisplay(this.resource.group); previous?.dispose();
      } catch (error) { next.dispose(); throw error; }
    } else if (!this.mounted) { this.scene.showGeometricRoutingApparatus(this.apparatus.group); this.mounted = true; }
    this.apparatus.setLabelsVisible(true); this.scene.setGeometricRoutingLabelUpdater((camera, width, height) => this.apparatus?.updateLabels(camera, width, height));
    this.apparatus.select(state.selection);
    if (!this.hasFramed) { this.scene.fitGeometricRoutingApparatus(this.apparatus.framingBounds(), 'overview'); this.hasFramed = true; }
  }
  private render(state: GeometricRoutingState): void {
    if (this.disposed) return;
    if (!state.currentResult && this.resource) { this.apparatus?.setDisplay(null); this.drop(this.resource); this.resource = null; }
    this.syncApparatus(state);
    const busy = this.controller.gate.busy;
    this.node<HTMLButtonElement>('w2-trace').disabled = !this.active || busy || state.pendingValidation || !state.validatedDraft || Object.keys(state.invalidEdits).length > 0;
    this.node<HTMLButtonElement>('w2-add').disabled = state.candidate.elements.length >= 16;
    this.node<HTMLButtonElement>('w2-remove').disabled = state.selection === 'source';
    const status = state.active ? 'Tracing / worker occupied' : state.pendingValidation ? 'Validating draft / no trace' : state.error || Object.keys(state.invalidEdits).length ? 'Invalid draft / not traced'
      : state.currentResult ? state.currentResult.status === 'complete' ? 'Calculated / complete' : 'Trace incomplete / limit reached'
      : state.lastResult || state.completedNumerical ? 'Draft changed / previous result detached' : !state.validatedDraft ? 'Draft not validated / review inputs' : 'Ready / press Trace';
    this.node('w2-status').textContent = status;
    const invalid = Object.keys(state.invalidEdits).length ? 'Enter a complete finite number. Invalid text is preserved.' : null;
    this.node('w2-error').hidden = !state.error && !invalid; this.node('w2-error').textContent = state.error ?? invalid ?? '';
    this.node('w2-display-error').hidden = !state.renderError; this.node('w2-display-error').textContent = state.renderError ?? '';
    this.node<HTMLButtonElement>('w2-retry-display').hidden = !this.controller.canRetryPresentation;
    this.node<HTMLButtonElement>('w2-retry-display').disabled = busy;
    this.componentList(state); this.editor(state); this.updateResult();
    if (this.ownedDOMBytes() > W2_DOM_RESERVATION_CAP) throw new Error('Routing inspector DOM exceeds its bounded 1 MiB app-owned reservation; no successful display was published.');
  }
  private componentList(state: GeometricRoutingState): void {
    const host = this.node('w2-components'), identity = state.candidate.elements.map(element => `${element.id}:${element.kind}`).join('|');
    if (host.dataset.identity !== identity) {
      host.replaceChildren(); host.dataset.identity = identity;
      const entries = [{ id: 'source', title: 'Laser Source', kind: 'One explicit ray' }, ...state.candidate.elements.map(element => ({ id: element.id, title: names[element.kind], kind: element.id }))];
      for (const entry of entries) { const button = document.createElement('button'); button.type = 'button'; button.className = 'w2-component'; button.dataset.testid = `w2-select-${entry.id}`; button.dataset.elementId = entry.id;
        const title = document.createElement('strong'); title.textContent = entry.title; button.append(title, span(entry.kind)); button.addEventListener('click', () => this.selectElement(entry.id)); host.append(button); }
    }
    for (const button of host.querySelectorAll<HTMLButtonElement>('button')) { const selected = button.dataset.elementId === state.selection; button.classList.toggle('selected', selected); button.setAttribute('aria-pressed', String(selected)); }
  }
  private editor(state: GeometricRoutingState): void {
    const index = state.candidate.elements.findIndex(element => element.id === state.selection), element = state.candidate.elements[index];
    const identity = `${state.selection}/${element?.aperture.kind ?? 'source'}/${index}`;
    if (this.editorIdentity !== identity) {
      this.editorIdentity = identity; const host = this.node('w2-editor'); host.replaceChildren(); this.fields.length = 0;
      this.node('w2-selected').textContent = state.selection === 'source' ? 'Laser Source / one explicit ray' : `${element.id} / ${names[element.kind]}`;
      const add = (label: string, id: string, path: string, value: () => number, scale = 1) => {
        const row = document.createElement('label'); row.textContent = label; const input = document.createElement('input'); input.type = 'text'; input.inputMode = 'decimal'; input.autocomplete = 'off'; input.dataset.testid = id; input.setAttribute('aria-label', label);
        const binding = new NumericFieldBinding(), field: Field = { input, binding, path, scale, value }; this.fields.push(field); row.append(input); host.append(row);
        input.addEventListener('input', () => { const current = this.controller.state, authoritative = value(); if (!binding.shouldEdit(input.value, path, current.revision, authoritative)) return; void this.controller.edit(path, input.value, scale); });
        input.addEventListener('change', () => { const current = this.controller.state, authoritative = value(); if (!binding.shouldEdit(input.value, path, current.revision, authoritative)) return; void this.controller.edit(path, input.value, scale); });
      };
      if (state.selection === 'source') {
        units.forEach((axis, k) => add(`${axis} position / m`, `w2-source-origin-${axis.toLowerCase()}`, `source.origin_m.${k}`, () => this.controller.state.candidate.source.origin_m[k]));
        units.forEach((axis, k) => add(`${axis} direction / unit vector`, `w2-source-direction-${axis.toLowerCase()}`, `source.direction.${k}`, () => this.controller.state.candidate.source.direction[k]));
      } else {
        const current = () => this.controller.state.candidate.elements.find(item => item.id === state.selection)!;
        units.forEach((axis, k) => add(`${axis} position / m`, `w2-position-${axis.toLowerCase()}`, `elements.${index}.pose.position_m.${k}`, () => current().pose.position_m[k]));
        units.forEach((axis, k) => add(`${axis} rotation / deg`, `w2-rotation-${axis.toLowerCase()}`, `elements.${index}.pose.rotation_xyz_rad.${k}`, () => current().pose.rotation_xyz_rad[k], Math.PI / 180));
        const label = document.createElement('label'); label.textContent = 'Finite aperture'; const select = document.createElement('select'); select.dataset.testid = 'w2-aperture-kind';
        for (const [value, title] of [['disk', 'Circular Disk'], ['rectangle', 'Rectangle']]) { const option = document.createElement('option'); option.value = value; option.textContent = title; select.append(option); } select.value = element.aperture.kind;
        select.addEventListener('change', () => { void this.controller.changeAperture(select.value as 'disk' | 'rectangle'); }); label.append(select); host.append(label);
        if (element.aperture.kind === 'disk') add('Radius / m', 'w2-radius', `elements.${index}.aperture.radius_m`, () => (current().aperture as { radius_m: number }).radius_m);
        else { add('Full width / m', 'w2-width', `elements.${index}.aperture.width_m`, () => (current().aperture as { width_m: number }).width_m); add('Full height / m', 'w2-height', `elements.${index}.aperture.height_m`, () => (current().aperture as { height_m: number }).height_m); }
      }
    }
    for (const field of this.fields) {
      const value = field.value(), text = state.invalidEdits[field.path] ?? numberText(value / field.scale);
      if (document.activeElement !== field.input && field.input.value !== text) field.input.value = text;
      field.binding.paint(field.input.value, field.path, state.revision, value); field.input.setAttribute('aria-invalid', String(Object.hasOwn(state.invalidEdits, field.path)));
    }
  }
  private camera(view: 'overview' | 'top' | 'focus'): void {
    try { if (!this.active || !this.apparatus || !this.scene) return; const bounds = this.apparatus.framingBounds(view === 'focus' ? this.controller.state.selection : undefined);
      if (view !== 'focus' && this.resource) bounds.union(this.resource.framingBounds()); this.scene.fitGeometricRoutingApparatus(bounds, view);
    } catch (error) { this.controller.reportPresentationFailure(String(error)); }
  }
  private prepare(result: GeometricTraceResult): GeometricRoutingPrepared {
    if (!this.active || !this.scene) throw new Error('Geometric Routing is not attached to the active bench.');
    this.syncApparatus(this.controller.state); if (!this.apparatus) throw new Error('The validated geometric apparatus is unavailable.'); this.scene.assertGeometricRoutingReady();
    const next = prepareGeometricRoutingDisplay(result), previous = this.resource;
    try {
      if (routingResourceBreakdown(result).retainedBytes + next.ownedBytes + this.apparatus.ownedBytes + this.controller.ownedStateBytes() + W2_DOM_RESERVATION_CAP > W2_RETAINED_RESERVATION) throw new Error('Routing records, inspector and display exceed the approved 2 MiB reservation.');
      const incomingDOM = Math.max(0, W2_DOM_RESERVATION_CAP - this.ownedDOMBytes());
      this.options.admit(next.ownedBytes + incomingDOM, next.ownedBytes + W2_DOM_RESERVATION_CAP); this.displays.add(next);
    } catch (error) { next.dispose(); throw error; }
    let committed = false, closed = false;
    return {
      commit: () => { if (closed || !this.active || this.resource !== previous) throw new Error('Routing display destination changed during preparation.');
        this.scene!.assertGeometricRoutingReady(); this.apparatus!.setDisplay(next.group); this.resource = next; committed = true; this.selectedBranch = null;
        const hit = result.hits.at(-1); this.selectedHitIdentity = hit ? hitIdentity(result, hit.id) : null; },
      dispose: () => { if (closed) return; closed = true; if (committed && this.resource === next) { this.resource = previous; this.apparatus?.setDisplay(previous?.group ?? null); } this.drop(next); },
      finalize: () => { if (closed) return; closed = true; if (previous && previous !== next) this.drop(previous); this.tab('data'); this.camera('overview'); },
    };
  }
  private drop(resource: GeometricRoutingDisplay): void { resource.dispose(); this.displays.delete(resource); }
  private updateResult(force = false): void {
    const state = this.controller.state, current = !!state.currentResult, result = state.currentResult ?? state.completedNumerical ?? state.lastResult;
    if (!resolveCurrentRoutingHit(state.currentResult, this.selectedHitIdentity)) this.selectedHitIdentity = null;
    this.showHit();
    if (!force && result === this.resultIdentity && current === this.resultCurrent) return; this.resultIdentity = result; this.resultCurrent = current;
    this.node('w2-result-state').textContent = result ? `${current ? 'Current' : state.completedNumerical === result ? 'Numerical result / display detached' : 'Previous trace — does not match the current draft'} / ${result.status === 'incomplete' ? 'Trace incomplete — limit reached' : 'Complete bounded trace'}` : 'No calculated result';
    const identity = this.node('w2-identity'); identity.replaceChildren(); const ledger = this.node('w2-ledger'); ledger.replaceChildren();
    const branchSelect = this.node<HTMLSelectElement>('w2-branch'); branchSelect.replaceChildren(); const all = document.createElement('option'); all.value = ''; all.textContent = 'All branches'; branchSelect.append(all);
    this.node('w2-terminals').replaceChildren(); this.node('w2-hits').replaceChildren();
    if (!result) { this.node('w2-timings').textContent = ''; return; }
    if (this.selectedBranch && !result.branches.some(branch => branch.id === this.selectedBranch)) this.selectedBranch = null;
    for (const [title, value] of [['Request', result.request_id], ['Scene SHA256', result.scene_sha256], ['Model', result.model_contract]]) { const row = document.createElement('p'); row.append(span(`${title}: `), span(value)); identity.append(row); }
    for (const [title, value] of [['Detected', result.ledger.detected_weight], ['Absorbed', result.ledger.absorbed_weight], ['Escaped', result.ledger.escaped_weight], ['Truncated', result.ledger.truncated_weight]] as const) {
      const card = document.createElement('label'); card.append(span(title)); const number = document.createElement('output'); number.textContent = numberText(value); number.dataset.testid = `w2-weight-${title.toLowerCase()}`; card.append(number); ledger.append(card);
    }
    this.node('w2-accounting-note').textContent = `Input weight ${result.ledger.input_weight}; signed residual ${numberText(result.ledger.signed_residual)}. Relative ray weights, not watts or irradiance. Escaped means outside the 1 m source-centered trace region. Truncation is not absorption.`;
    for (const branch of result.branches) { const option = document.createElement('option'); option.value = branch.id; option.textContent = `${branch.id} / ${branch.outcome} / weight ${branch.relative_weight}`; branchSelect.append(option); }
    branchSelect.value = this.selectedBranch ?? '';
    const table = (host: HTMLElement, headers: string[], rows: (string | HTMLElement)[][]) => {
      const table = document.createElement('table'), head = document.createElement('thead'), tr = document.createElement('tr'); for (const title of headers) { const th = document.createElement('th'); th.scope = 'col'; th.textContent = title; tr.append(th); } head.append(tr); table.append(head);
      const body = document.createElement('tbody'); for (const row of rows) { const tr = document.createElement('tr'); for (const value of row) { const td = document.createElement('td'); td.className = 'w2-scalar'; if (typeof value === 'string') td.textContent = value; else td.append(value); tr.append(td); } body.append(tr); } table.append(body); host.append(table);
    };
    const terminals = result.terminals.filter(terminal => !this.selectedBranch || terminal.branch_id === this.selectedBranch);
    table(this.node('w2-terminals'), ['Branch', 'Parent', 'Outcome', 'Weight', 'Distance / m', 'Reason'], terminals.map(terminal => [terminal.branch_id, result.branches.find(branch => branch.id === terminal.branch_id)?.parent_id ?? '—', terminal.category, numberText(terminal.relative_weight), numberText(terminal.cumulative_length_m), terminal.reason]));
    const hits = result.hits.filter(hit => !this.selectedBranch || hit.branch_id === this.selectedBranch);
    table(this.node('w2-hits'), ['Hit / Element', 'Branch', 'u / m', 'v / m', 'Distance / m'], hits.map(hit => {
      const button = document.createElement('button'); button.type = 'button'; button.dataset.testid = `w2-hit-${hit.id}`; button.textContent = `${hit.id} / ${hit.element_id}`; button.disabled = !current;
      button.addEventListener('click', () => {
        const selection = hitIdentity(result, hit.id); if (!resolveCurrentRoutingHit(this.controller.state.currentResult, selection)) return;
        this.selectedHitIdentity = selection; this.resource?.selectHit(hit.id); this.controller.select(hit.element_id); this.showHit(); this.tab('inspector');
      });
      return [button, hit.branch_id, numberText(hit.local_uv_m[0]), numberText(hit.local_uv_m[1]), numberText(hit.cumulative_length_m)];
    }));
    const timings = state.timings;
    this.node('w2-timings').textContent = timings ? `HTTP + decode ${numberText(timings.httpAndDecodeMs)} ms; decode ${numberText(timings.decodeMs)} ms; display preparation ${numberText(timings.attachmentMs)} ms. CPU observations, not GPU timing.` : '';
  }
  private showHit(): void {
    const result = this.controller.state.currentResult, hit = resolveCurrentRoutingHit(result, this.selectedHitIdentity), host = this.node('w2-selected-hit'); host.replaceChildren();
    if (!result || !hit) { host.textContent = 'No current hit — trace the updated scene.'; return; }
    const title = document.createElement('h3'); title.textContent = `Current Calculated Hit / ${hit.id} / ${hit.element_id}`; host.append(title);
    const readout = document.createElement('div'); readout.className = 'w2-table-scroll'; readout.tabIndex = 0; readout.setAttribute('role', 'region'); readout.setAttribute('aria-label', 'Full calculated hit values');
    const values = [`Request: ${result.request_id}`, `Scene SHA256: ${result.scene_sha256}`, `Position / m: (${hit.position_m.map(numberText).join(', ')})`, `Receiver/surface local UV / m: (${hit.local_uv_m.map(numberText).join(', ')})`, `Incident direction: (${hit.incident_direction.map(numberText).join(', ')})`, `Cumulative geometric distance / m: ${numberText(hit.cumulative_length_m)}`, `Incoming relative weight: ${numberText(hit.incoming_weight)}`];
    values.forEach(value => { const p = document.createElement('p'); p.className = 'w2-scalar'; p.textContent = value; readout.append(p); }); host.append(readout); this.resource?.selectHit(hit.id);
  }
  numericalOwners(): readonly (GeometricTraceResult | null)[] { return this.controller.numericalOwners(); }
  ownedNumericalBytes(): number { return this.controller.ownedNumericalBytes(); }
  ownedDOMBytes(): number { return measureRoutingDOMReservation([this.host, this.navigation]) + this.fields.reduce((sum, field) => sum + 256 + field.path.length * 2 + field.input.value.length * 2, 0); }
  ownedRenderingBytes(): number { return this.ownedDOMBytes() + (this.selectedHitIdentity ? routingMetadataReservation(this.selectedHitIdentity) : 0) + (this.apparatus?.ownedBytes ?? 0) + [...this.displays].reduce((sum, resource) => sum + resource.ownedBytes, 0); }
  ownedBytes(): number { return this.ownedNumericalBytes() + this.ownedRenderingBytes() + this.controller.ownedStateBytes(); }
  releaseResults(): boolean {
    if (!this.controller.releaseResults()) return false; this.apparatus?.setDisplay(null); for (const resource of this.displays) resource.dispose(); this.displays.clear(); this.resource = null; this.selectedBranch = null; this.selectedHitIdentity = null; this.updateResult(true); return true;
  }
  snapshot(): object {
    const state = this.controller.state, result = state.currentResult ?? state.completedNumerical ?? state.lastResult;
    return { active: this.active, mounted: this.mounted, revision: state.revision, attachmentEpoch: state.attachmentEpoch, selection: state.selection,
      status: state.status, error: state.error, renderError: state.renderError, canRetryPresentation: this.controller.canRetryPresentation,
      candidate: state.candidate, validatedDigest: state.validatedDigest, currentRequestId: state.currentResult?.request_id ?? null,
      previousRequestId: state.lastResult?.request_id ?? null, completedRequestId: state.completedNumerical?.request_id ?? null,
      currentResult: state.currentResult, selectedBranch: this.selectedBranch, selectedHit: this.selectedHitIdentity?.hitId ?? null, selectedHitIdentity: this.selectedHitIdentity, timings: state.timings,
      numericalBytes: this.ownedNumericalBytes(), renderingBytes: this.ownedRenderingBytes(), stateBytes: this.controller.ownedStateBytes(), domReservationBytes: this.ownedDOMBytes(), ownedBytes: this.ownedBytes(),
      resultResource: result ? routingResourceBreakdown(result) : null, apparatus: this.apparatus?.snapshot() ?? null, display: this.resource?.snapshot() ?? null };
  }
  dispose(): void {
    if (this.disposed) return; this.disposed = true; this.unsubscribe(); this.unsubscribeGate(); this.controller.bindPresentation(null);
    if (this.mounted) this.scene?.hideGeometricRoutingApparatus(); this.scene?.setGeometricRoutingLabelUpdater(null);
    for (const resource of this.displays) resource.dispose(); this.displays.clear(); this.resource = null; this.apparatus?.dispose(); this.apparatus = null; this.navigation.remove(); this.host.replaceChildren();
  }
}
