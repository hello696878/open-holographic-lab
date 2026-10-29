/** W4 child controls inside the existing Geometric Routing workspace. */
import * as THREE from 'three';
import { NumericFieldBinding } from './numeric_fields';
import { routingMetadataReservation, routingStructuralEqual, stringifyRoutingJSON, type RoutingKind } from './geometric_routing_contracts';
import { measureRoutingDOMReservation, type GeometricRoutingScenePort } from './geometric_routing_workspace';
import { createFresnelRoutingApparatus, prepareFresnelRoutingDisplay, type FresnelRoutingApparatus, type FresnelRoutingDisplay } from './fresnel_routing_apparatus';
import { W4_PRESETS, W4_RETAINED_RESERVATION, W4_DISCLAIMER, assertFresnelScene, fresnelResourceBreakdown,
  type FresnelScene, type FresnelTraceResult, type FresnelValidationReply } from './fresnel_routing_contracts';
import { FresnelRoutingController, type FresnelRoutingPrepared, type FresnelRoutingState } from './fresnel_routing_state';

export interface FresnelRoutingPanelsOptions {
  admit(persistent: number, transient: number): void; readonly labelHost?: HTMLElement; readonly navigationHost?: HTMLElement;
}
export interface FresnelRoutingEventIdentity {
  readonly requestId: string; readonly sceneSha256: string; readonly model: string; readonly branchId: string; readonly eventId: string;
}
/** Resolve a presentation selection only against its current accepted trace. */
export function resolveCurrentRoutingEvent(result: FresnelTraceResult | null, selection: FresnelRoutingEventIdentity | null): FresnelTraceResult['events'][number] | null {
  if (!result || !selection || result.request_id !== selection.requestId || result.scene_sha256 !== selection.sceneSha256) return null;
  if (result.model_contract !== selection.model) return null; return result.events.find(hit => hit.id === selection.eventId && hit.branch_id === selection.branchId) ?? null;
}
function hitIdentity(result: FresnelTraceResult, hitId: string): FresnelRoutingEventIdentity {
  return Object.freeze({ requestId: result.request_id, sceneSha256: result.scene_sha256, model: result.model_contract, branchId: result.events.find(e=>e.id===hitId)!.branch_id, eventId: hitId });
}
const names: Readonly<Record<RoutingKind, string>> = { mirror: 'Mirror', ideal_splitter_50_50: 'Ideal 50:50 Splitter', beam_stop: 'Beam Stop', receiver: 'Receiver' };
const units = ['X', 'Y', 'Z'] as const;
interface Field { readonly input: HTMLInputElement; readonly binding: NumericFieldBinding; readonly path: string; readonly scale: number; readonly value: () => number }
export const W4_DOM_RESERVATION_CAP = 1024 * 1024;
const numberText = (value: number): string => Object.is(value, -0) ? '-0' : String(value);
function span(text: string): HTMLSpanElement { const item = document.createElement('span'); item.textContent = text; return item; }

export class FresnelRoutingPanels {
  private active = false; private disposed = false; private mounted = false; private hasFramed = false;
  private apparatus: FresnelRoutingApparatus | null = null; private apparatusScene: FresnelScene | null = null;
  private apparatusFrames: FresnelValidationReply | null = null; private resource: FresnelRoutingDisplay | null = null;
  private readonly displays = new Set<FresnelRoutingDisplay>(); private readonly fields: Field[] = [];
  private selectedBranch: string | null = null; private selectedEventIdentity: FresnelRoutingEventIdentity | null = null; private editorIdentity = '';
  private resultIdentity: FresnelTraceResult | null = null; private resultCurrent = false; private readonly navigation: HTMLElement; private showNormals=true; private showAngles=true; private opacity=.18;
  private readonly unsubscribe: () => void; private readonly unsubscribeGate: () => void;
  constructor(readonly host: HTMLElement, readonly controller: FresnelRoutingController, private readonly scene: GeometricRoutingScenePort | null,
      private readonly options: FresnelRoutingPanelsOptions) {
    host.classList.add('w2-workspace','w4-workspace'); host.hidden = true;
    const navigation = document.createElement('section'); navigation.className = 'w2-navigation w4-navigation w4-workspace'; navigation.setAttribute('aria-label', 'Geometric routing controls');
    navigation.innerHTML = `<div class="w2-heading"><div><span class="eyebrow">W4 / FRESNEL POWER ROUTING</span><h2>Geometric Routing</h2><p>Actual reflected / transmitted branches. Carried polarization. Explicit tracing.</p></div>
      <output data-testid="w4-status" class="w2-status" aria-live="polite">Draft / not traced</output></div>
      <div class="w2-actions"><label>Apparatus <select data-testid="w4-preset" aria-label="Routing apparatus preset"><option value="A">Normal Slab</option><option value="B">Refracting Prism</option><option value="C">TIR Prism</option></select></label>
      <button type="button" data-testid="w4-load-preset">Load Preset</button>
      <label>Source Polarization <select data-testid="w4-polarization" aria-label="Source Polarization"><option value="unpolarized">Unpolarized</option><option value="linear_e1">Linear Along Source e1 (+X)</option><option value="linear_e2">Linear Along Source e2 (+Y)</option><option value="linear_45">Linear at 45° (e1 + e2)</option></select></label>
      <button type="button" class="primary" data-testid="w4-trace">Trace</button>
      <div class="w2-camera-controls" role="group" aria-label="Routing camera"><button type="button" data-testid="w4-orbit">Orbit</button><button type="button" data-testid="w4-top">Top View</button><button type="button" data-testid="w4-focus">Focus</button><button type="button" data-testid="w4-reset">Reset View</button></div></div>
      <p class="w2-legend">Each ray retains its polarization coherency state. Different paths are added incoherently; no coherent multipath interference is modeled. Orange R / teal T. Line width is a visibility aid, not beam diameter, irradiance or watts.</p>
      <p class="error" role="alert" data-testid="w4-error" hidden></p><p class="error" role="alert" data-testid="w4-display-error" hidden></p>
      <button type="button" data-testid="w4-retry-display" hidden>Restore Display (No Recalculation)</button>`;
    this.navigation = navigation; if (options.navigationHost) { options.navigationHost.classList.add('w2-controls'); options.navigationHost.append(navigation); options.navigationHost.hidden = true; } else host.before(navigation);
    host.innerHTML = `<aside class="w2-left panel"><div class="w2-panel-heading"><span class="eyebrow">APPARATUS</span><h2>Finite Optical Elements</h2></div>
      <p class="w2-note">Hit order is calculated from geometry, independent of this list.</p><div data-testid="w4-components" class="w2-components"></div>
      <div class="w2-add-controls"><label>Add Element <select data-testid="w4-add-kind"><option value="beam_stop">Beam Stop</option><option value="receiver">Receiver</option></select></label>
      <button type="button" data-testid="w4-add">Add Element</button><button type="button" data-testid="w4-remove">Remove Selected</button></div>
      <p class="w2-model-note">One fixed-frame source, at most one finite closed body and four receivers / beam stops. All side and end faces are optical. Mounts are decorative. No coatings, dispersion, wave propagation or coherent path interference.</p>
      <p class="w2-document-note" data-testid="w4-documents-unsupported">Routing scene import/export is not supported in this slice. Existing experiment settings remain available in their original workspaces.</p></aside>
      <aside class="w2-right panel"><nav class="w2-tabs" role="tablist" aria-label="Routing inspection"><button type="button" id="w4-tab-inspector" data-testid="w4-tab-inspector" role="tab" aria-selected="true" aria-controls="w4-panel-inspector">Inspector</button>
      <button type="button" id="w4-tab-data" data-testid="w4-tab-data" role="tab" aria-selected="false" aria-controls="w4-panel-data" tabindex="-1">Trace Data</button></nav>
      <section id="w4-panel-inspector" role="tabpanel" aria-labelledby="w4-tab-inspector"><span class="eyebrow">SELECTED COMPONENT</span><h3 data-testid="w4-selected">Source</h3>
      <section data-testid="w4-slab-displacement" class="w2-result-state" hidden></section>
      <div data-testid="w4-editor" class="w2-editor-grid"></div><p class="w2-note">Changing one field preserves untouched SI components. X/Y/Z rotations apply actively in X, then Y, then Z order. Only Trace recomputes.</p>
      <div class="w2-selection-details" data-testid="w4-selected-event"></div></section>
      <section id="w4-panel-data" role="tabpanel" aria-labelledby="w4-tab-data" hidden><output class="w2-result-state" data-testid="w4-result-state">No calculated result</output>
      <div class="w2-identity w2-table-scroll" tabindex="0" role="region" aria-label="Full result identity" data-testid="w4-identity"></div>
      <div class="w2-ledger" data-testid="w4-ledger"></div><p class="w2-note" data-testid="w4-accounting-note">Source-relative power, not watts or irradiance. Unresolved power is not absorption.</p>
      <label class="w2-branch-control">Inspect Branch <select data-testid="w4-branch" aria-label="Inspect calculated branch"><option value="">All branches</option></select></label>
      <div class="w4-readout w2-table-scroll" role="region" tabindex="0" aria-label="Complete selected branch power state" data-testid="w4-branch-state"></div>
      <div class="w2-table-scroll" role="region" tabindex="0" aria-label="Branch terminal outcomes, horizontally scrollable" data-testid="w4-terminals"></div>
      <div class="w2-table-scroll" role="region" tabindex="0" aria-label="Actual calculated hits, horizontally scrollable" data-testid="w4-events"></div>
      <output class="w2-timings" data-testid="w4-timings"></output></section></aside>`;
    this.node('w4-load-preset').addEventListener('click', () => { const preset = this.node<HTMLSelectElement>('w4-preset').value as keyof typeof W4_PRESETS; this.hasFramed = false; void controller.setPreset(preset); });
    this.node('w4-trace').addEventListener('click', () => { void controller.trace(); });
    this.node<HTMLSelectElement>('w4-polarization').addEventListener('change', event => { void controller.setPolarization((event.target as HTMLSelectElement).value as FresnelScene['source']['polarization']); });
    this.node('w4-add').addEventListener('click', () => { this.tab('inspector'); void controller.add(this.node<HTMLSelectElement>('w4-add-kind').value as RoutingKind); });
    this.node('w4-remove').addEventListener('click', () => { void (controller.state.candidate.bodies.some(b=>b.id===controller.state.selection)?controller.removeBody():controller.remove()); });
    this.installViewControls(); this.node('w4-retry-display').addEventListener('click', () => { controller.retryPresentation(); });
    this.node<HTMLSelectElement>('w4-branch').addEventListener('change', event => { this.selectedBranch = (event.target as HTMLSelectElement).value || null; this.resource?.selectBranch(this.selectedBranch); this.updateResult(true); });
    for (const [id, view] of [['w4-orbit', 'overview'], ['w4-top', 'top'], ['w4-focus', 'focus'], ['w4-reset', 'overview']] as const) this.node(id).addEventListener('click', () => this.camera(view));
    for (const tab of ['inspector', 'data'] as const) {
      this.node(`w4-tab-${tab}`).addEventListener('click', () => this.tab(tab));
      this.node(`w4-tab-${tab}`).addEventListener('keydown', event => { if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return; event.preventDefault(); const next = event.key === 'Home' ? 'inspector' : event.key === 'End' ? 'data' : tab === 'inspector' ? 'data' : 'inspector'; this.tab(next); this.node(`w4-tab-${next}`).focus(); });
    }
    controller.bindPresentation(result => this.prepare(result)); this.unsubscribe = controller.subscribe(state => this.render(state)); this.unsubscribeGate = controller.gate.subscribe(() => this.render(controller.state));
  }
  private node<T extends HTMLElement = HTMLElement>(id: string): T {
    const node = this.host.querySelector<T>(`[data-testid="${id}"]`) ?? this.navigation.querySelector<T>(`[data-testid="${id}"]`);
    if (!node) throw new Error(`Missing Geometric Routing area: ${id}`); return node;
  }
  private tab(tab: 'inspector' | 'data'): void {
    for (const item of ['inspector', 'data'] as const) { const selected = item === tab, button = this.node<HTMLButtonElement>(`w4-tab-${item}`);
      button.setAttribute('aria-selected', String(selected)); button.tabIndex = selected ? 0 : -1; this.host.querySelector<HTMLElement>(`#w4-panel-${item}`)!.hidden = !selected; }
  }
  setActive(active: boolean): void {
    if (this.disposed || this.active === active) return; this.active = active; this.host.hidden = !active;
    if (this.options.navigationHost) this.options.navigationHost.hidden = !active; this.navigation.hidden = !active;
    if (active) void this.controller.activate(); else this.controller.deactivate(); this.render(this.controller.state);
  }
  selectElement(id: string): void { this.controller.select(id); this.tab('inspector'); }
  private syncApparatus(state: FresnelRoutingState): void {
    if (!this.active) {
      // An inactive W4 gate subscriber must not clear the active W2 label owner.
      if (this.mounted) { this.scene?.hideGeometricRoutingApparatus(); this.scene?.setGeometricRoutingLabelUpdater(null); }
      this.apparatus?.setLabelsVisible(false); this.mounted = false; return;
    }
    const draft = state.validatedDraft ?? state.candidate;
    try { assertFresnelScene(draft); } catch { this.apparatus?.setDisplay(null); return; }
    if (!this.scene) throw new Error('The existing WebGL scene is unavailable. No substitute calculated path is displayed.');
    if (!this.apparatus || !routingStructuralEqual(this.apparatusScene, draft) || !routingStructuralEqual(this.apparatusFrames, state.validation)) {
      // Reserve the static apparatus before constructing any replacement alongside the old one.
      this.options.admit(768 * 1024, 768 * 1024);
      const next = createFresnelRoutingApparatus(draft, state.validation, { labelHost: this.options.labelHost, onSelect: id => this.selectElement(id) }), previous = this.apparatus;
      try {
        if (this.mounted) this.scene.replaceGeometricRoutingApparatus(next.group); else this.scene.showGeometricRoutingApparatus(next.group);
        this.apparatus = next; this.apparatusScene = draft; this.apparatusFrames = state.validation; this.mounted = true;
        if (this.resource && state.currentResult === this.resource.result) next.setDisplay(this.resource.group); previous?.dispose();
      } catch (error) { next.dispose(); throw error; }
    } else if (!this.mounted) { this.scene.showGeometricRoutingApparatus(this.apparatus.group); this.mounted = true; }
    this.apparatus.setLabelsVisible(true); this.scene.setGeometricRoutingLabelUpdater((camera, width, height) => { this.apparatus?.updateLabels(camera,width,height); this.resource?.updateLabels(camera,width,height); });
    this.apparatus.select(state.selection); this.apparatus.setOpacity(this.opacity); this.resource?.setAnnotations(this.showNormals,this.showAngles);
    if (!this.hasFramed) { this.scene.fitGeometricRoutingApparatus(this.apparatus.framingBounds(), 'overview'); this.hasFramed = true; }
  }
  private render(state: FresnelRoutingState): void {
    if (this.disposed) return;
    if (!state.currentResult && this.resource) { this.apparatus?.setDisplay(null); this.drop(this.resource); this.resource = null; }
    this.syncApparatus(state);
    const busy = this.controller.gate.busy;
    this.node<HTMLButtonElement>('w4-trace').disabled = !this.active || busy || state.pendingValidation || this.controller.hasPendingRead || !state.validatedDraft || Object.keys(state.invalidEdits).length > 0;
    this.node<HTMLButtonElement>('w4-add').disabled = state.candidate.elements.length >= 4;
    this.node<HTMLButtonElement>('w4-remove').disabled = state.selection === 'source';
    const status = state.active ? 'Tracing / worker occupied' : state.pendingValidation ? 'Validating draft / no trace' : state.error || Object.keys(state.invalidEdits).length ? 'Invalid draft / not traced'
      : state.currentResult ? state.currentResult.status === 'complete' ? 'Calculated / complete' : 'Trace incomplete / unresolved power remains'
      : state.lastResult || state.completedNumerical ? 'Draft changed / previous result detached' : !state.validatedDraft ? 'Draft not validated / review inputs' : 'Ready / press Trace';
    this.node('w4-status').textContent = status;
    const invalid = Object.keys(state.invalidEdits).length ? 'Enter a complete finite number. Invalid text is preserved.' : null;
    this.node('w4-error').hidden = !state.error && !invalid; this.node('w4-error').textContent = state.error ?? invalid ?? '';
    this.node('w4-display-error').hidden = !state.renderError; this.node('w4-display-error').textContent = state.renderError ?? '';
    this.node<HTMLButtonElement>('w4-retry-display').hidden = !this.controller.canRetryPresentation;
    this.node<HTMLButtonElement>('w4-retry-display').disabled = busy;
    this.componentList(state); this.editor(state); this.updateResult();
    if (this.ownedDOMBytes() > W4_DOM_RESERVATION_CAP) throw new Error('Routing inspector DOM exceeds its bounded 1 MiB app-owned reservation; no successful display was published.');
  }
  private componentList(state: FresnelRoutingState): void {
    const host = this.node('w4-components'), identity = state.candidate.bodies.map(b=>`${b.id}:${b.kind}`).join('|')+state.candidate.elements.map(element => `${element.id}:${element.kind}`).join('|');
    if (host.dataset.identity !== identity) {
      host.replaceChildren(); host.dataset.identity = identity;
      const entries = [{ id: 'source', title: 'Laser Source', kind: 'One outside ray' }, ...state.candidate.bodies.map(body=>({id:body.id,title:'Transparent Body',kind:`${body.id} / ${body.kind}`})), ...state.candidate.elements.map(element => ({ id: element.id, title: names[element.kind], kind: element.id }))];
      for (const entry of entries) { const button = document.createElement('button'); button.type = 'button'; button.className = 'w2-component'; button.dataset.testid = `w4-select-${entry.id}`; button.dataset.elementId = entry.id;
        const title = document.createElement('strong'); title.textContent = entry.title; button.append(title, span(entry.kind)); button.addEventListener('click', () => this.selectElement(entry.id)); host.append(button); }
    }
    for (const button of host.querySelectorAll<HTMLButtonElement>('button')) { const selected = button.dataset.elementId === state.selection; button.classList.toggle('selected', selected); button.setAttribute('aria-pressed', String(selected)); }
  }
  private editor(state: FresnelRoutingState): void {
    const body=state.candidate.bodies.find(b=>b.id===state.selection), index=state.candidate.elements.findIndex(e=>e.id===state.selection), item=state.candidate.elements[index];
    const identity=`${state.selection}/${body?.kind??item?.aperture.kind??'source'}/${index}`;
    if(this.editorIdentity!==identity){this.editorIdentity=identity;const host=this.node('w4-editor');host.replaceChildren();this.fields.length=0;
      this.node('w4-selected').textContent=body?`${body.id} / ${body.kind==='rectangular_block'?'Rectangular Block':'Right Triangular Prism'}`:state.selection==='source'?'Laser Source / one outside ray':`${item.id} / ${names[item.kind]}`;
      const add=(label:string,id:string,path:string,value:()=>number,scale=1)=>{const row=document.createElement('label');row.textContent=label;const input=document.createElement('input');input.type='text';input.inputMode='decimal';input.autocomplete='off';input.dataset.testid=id;input.setAttribute('aria-label',label);const binding=new NumericFieldBinding();this.fields.push({input,binding,path,scale,value});row.append(input);host.append(row);const edit=()=>{const current=this.controller.state;if(binding.shouldEdit(input.value,path,current.revision,value()))void this.controller.edit(path,input.value,scale);};input.addEventListener('input',edit);input.addEventListener('change',edit);};
      if(body){const shapeLabel=document.createElement('label');shapeLabel.textContent='Transparent body shape';const shape=document.createElement('select');shape.dataset.testid='w4-body-shape';for(const [value,text]of [['rectangular_block','Rectangular Block'],['right_triangular_prism','Right Triangular Prism']]){const option=document.createElement('option');option.value=value;option.textContent=text;shape.append(option);}shape.value=body.kind;shape.addEventListener('change',()=>void this.controller.changeBodyKind(shape.value as typeof body.kind));shapeLabel.append(shape);host.append(shapeLabel);
        const current=()=>this.controller.state.candidate.bodies[0];units.forEach((axis,k)=>add(`${axis} position / m`,`w4-position-${axis.toLowerCase()}`,`bodies.0.pose.position_m.${k}`,()=>current().pose.position_m[k]));units.forEach((axis,k)=>add(`${axis} rotation / deg`,`w4-rotation-${axis.toLowerCase()}`,`bodies.0.pose.rotation_xyz_rad.${k}`,()=>current().pose.rotation_xyz_rad[k],Math.PI/180));
        for(const key of Object.keys(body.shape))add(key.replaceAll('_',' '),`w4-${key}`,`bodies.0.shape.${key}`,()=>(current().shape as unknown as Record<string,number>)[key]);
        add('Exterior refractive index','w4-exterior-index','exterior_medium.refractive_index',()=>this.controller.state.candidate.exterior_medium.refractive_index);add('Interior refractive index','w4-interior-index','bodies.0.interior_medium.refractive_index',()=>current().interior_medium.refractive_index);
        const note=document.createElement('p');note.className='w4-index-note';note.textContent='Ideal constant indices; no material or dispersion database. All finite side and end faces are optical.';host.append(note);
      }else if(state.selection==='source'){
        const source=document.createElement('p');source.textContent='Source frame: e1 = +X, e2 = +Y; propagation = +Z. Fixed by this preset, not by the camera.';host.append(source);
        const label=document.createElement('label');label.textContent='Source Polarization';const select=document.createElement('select');select.dataset.testid='w4-source-polarization';
        for(const [value,title]of [['unpolarized','Unpolarized'],['linear_e1','Linear Along Source e1 (+X)'],['linear_e2','Linear Along Source e2 (+Y)'],['linear_45','Linear at 45° (e1 + e2)']]){const option=document.createElement('option');option.value=value;option.textContent=title;select.append(option);}select.value=state.candidate.source.polarization;select.addEventListener('change',()=>void this.controller.setPolarization(select.value as FresnelScene['source']['polarization']));label.append(select);host.append(label);
        const position=document.createElement('p');position.className='w4-scalar';position.textContent=`Preset source position / m: (${state.candidate.source.origin_m.join(', ')})`;host.append(position);
      }
      else{const current=()=>this.controller.state.candidate.elements.find(e=>e.id===state.selection)!;const apertureLabel=document.createElement('label');apertureLabel.textContent='Finite aperture';const aperture=document.createElement('select');aperture.dataset.testid='w4-aperture';for(const kind of ['disk','rectangle']){const option=document.createElement('option');option.value=kind;option.textContent=kind==='disk'?'Disk':'Rectangle';aperture.append(option);}aperture.value=item.aperture.kind;aperture.addEventListener('change',()=>void this.controller.changeAperture(aperture.value as 'disk'|'rectangle'));apertureLabel.append(aperture);host.append(apertureLabel);units.forEach((axis,k)=>add(`${axis} position / m`,`w4-position-${axis.toLowerCase()}`,`elements.${index}.pose.position_m.${k}`,()=>current().pose.position_m[k]));units.forEach((axis,k)=>add(`${axis} rotation / deg`,`w4-rotation-${axis.toLowerCase()}`,`elements.${index}.pose.rotation_xyz_rad.${k}`,()=>current().pose.rotation_xyz_rad[k],Math.PI/180));if(item.aperture.kind==='disk')add('Radius / m','w4-radius',`elements.${index}.aperture.radius_m`,()=>(current().aperture as {radius_m:number}).radius_m);else{add('Full width / m','w4-width',`elements.${index}.aperture.width_m`,()=>(current().aperture as {width_m:number}).width_m);add('Full height / m','w4-height',`elements.${index}.aperture.height_m`,()=>(current().aperture as {height_m:number}).height_m);}}
    }
    this.node<HTMLSelectElement>('w4-polarization').value=state.candidate.source.polarization;
    const polarization=this.host.querySelector<HTMLSelectElement>('[data-testid="w4-source-polarization"]');if(polarization)polarization.value=state.candidate.source.polarization;
    for(const f of this.fields){const value=f.value(),text=state.invalidEdits[f.path]??numberText(value/f.scale);if(document.activeElement!==f.input&&f.input.value!==text)f.input.value=text;f.binding.paint(f.input.value,f.path,state.revision,value);f.input.setAttribute('aria-invalid',String(Object.hasOwn(state.invalidEdits,f.path)));}
  }
  private installViewControls():void{
    const box=document.createElement('div');box.className='w4-view-controls';box.innerHTML=`<label><input type="checkbox" data-testid="w4-normals" checked>Normals</label><label><input type="checkbox" data-testid="w4-angles" checked>Angles</label><label>Body opacity <input type="range" min="0.05" max="0.5" step="0.01" value="0.18" data-testid="w4-opacity"></label>`;this.navigation.append(box);
    const apply=()=>{this.showNormals=this.node<HTMLInputElement>('w4-normals').checked;this.showAngles=this.node<HTMLInputElement>('w4-angles').checked;this.opacity=Number(this.node<HTMLInputElement>('w4-opacity').value);this.apparatus?.setOpacity(this.opacity);this.resource?.setAnnotations(this.showNormals,this.showAngles);};box.addEventListener('change',apply);box.addEventListener('input',apply);
  }
  private camera(view: 'overview' | 'top' | 'focus'): void {
    try { if (!this.active || !this.apparatus || !this.scene) return; const bounds = this.apparatus.framingBounds(view === 'focus' ? this.controller.state.selection : undefined);
      if (view !== 'focus' && this.resource) bounds.union(this.resource.framingBounds()); this.scene.fitGeometricRoutingApparatus(bounds, view);
    } catch (error) { this.controller.reportPresentationFailure(String(error)); }
  }
  private prepare(result: FresnelTraceResult): FresnelRoutingPrepared {
    if (!this.active || !this.scene) throw new Error('Geometric Routing is not attached to the active bench.');
    this.syncApparatus(this.controller.state); if (!this.apparatus) throw new Error('The validated geometric apparatus is unavailable.'); this.scene.assertGeometricRoutingReady();
    // Shared unit geometry/materials bound64 returned routes plus32 markers below128KiB.
    // Reserve before factory allocation; the actual resource is measured again below.
    this.options.admit(128*1024+Math.max(0,W4_DOM_RESERVATION_CAP-this.ownedDOMBytes()),128*1024+W4_DOM_RESERVATION_CAP);
    const next = prepareFresnelRoutingDisplay(result, { labelHost: this.options.labelHost }), previous = this.resource;
    if(next.ownedBytes>128*1024){next.dispose();throw new Error('W4 display exceeds its preallocated128KiB ownership bound.');}
    try {
      if (this.controller.ownedNumericalBytes() + next.ownedBytes + this.apparatus.ownedBytes + this.controller.ownedStateBytes() + W4_DOM_RESERVATION_CAP > W4_RETAINED_RESERVATION) throw new Error('Routing records, inspector and display exceed the approved 4 MiB reservation.');
      const incomingDOM = Math.max(0, W4_DOM_RESERVATION_CAP - this.ownedDOMBytes());
      this.options.admit(next.ownedBytes + incomingDOM, next.ownedBytes + W4_DOM_RESERVATION_CAP); this.displays.add(next);
    } catch (error) { next.dispose(); throw error; }
    let committed = false, closed = false;
    return {
      commit: () => { if (closed || !this.active || this.resource !== previous) throw new Error('Routing display destination changed during preparation.');
        this.scene!.assertGeometricRoutingReady(); this.apparatus!.setDisplay(next.group); this.resource = next; next.setAnnotations(this.showNormals,this.showAngles); committed = true; this.selectedBranch = null;
        const hit = result.events.find(e=>e.classification==='total_internal_reflection')??result.events.find(e=>e.target.kind==='body_face')??result.events.at(-1); this.selectedEventIdentity = hit ? hitIdentity(result, hit.id) : null; },
      dispose: () => { if (closed) return; closed = true; if (committed && this.resource === next) { this.resource = previous; this.apparatus?.setDisplay(previous?.group ?? null); } this.drop(next); },
      finalize: () => { if (closed) return; closed = true; if (previous && previous !== next) this.drop(previous); this.tab('data'); this.camera('overview'); },
    };
  }
  private drop(resource: FresnelRoutingDisplay): void { resource.dispose(); this.displays.delete(resource); }
  private updateResult(force=false):void{
    const state=this.controller.state,current=!!state.currentResult,result=state.currentResult??state.completedNumerical??state.lastResult;
    if(!resolveCurrentRoutingEvent(state.currentResult,this.selectedEventIdentity))this.selectedEventIdentity=null;
    this.showHit();if(!force&&result===this.resultIdentity&&current===this.resultCurrent)return;this.resultIdentity=result;this.resultCurrent=current;
    this.node('w4-result-state').textContent=result?`${current?'Current':state.completedNumerical===result?'Numerical result / display detached':'Previous trace — not current'} / ${result.status==='incomplete'?'Incomplete — unresolved power remains':'Complete bounded trace'}`:'No current result — press Trace explicitly';
    for(const id of ['w4-identity','w4-ledger','w4-terminals','w4-events','w4-branch-state'])this.node(id).replaceChildren();
    const choices=this.node<HTMLSelectElement>('w4-branch');choices.replaceChildren();const all=document.createElement('option');all.value='';all.textContent='All branches';choices.append(all);
    if(!result){this.node('w4-timings').textContent='';return;}
    if(!result.branches.some(b=>b.id===this.selectedBranch))this.selectedBranch=null;
    const identity=this.node('w4-identity');for(const [key,value]of [['Model',result.model_contract],['Request',result.request_id],['Scene SHA-256',result.scene_sha256]]){const row=document.createElement('p');row.className='w4-scalar';row.textContent=`${key}: ${value}`;identity.append(row);}
    const ledger=this.node('w4-ledger');for(const [label,key]of [['Input','input_power'],['Receiver Leaves','detected_power'],['Beam-Stop Absorption','stopped_power'],['Escaped Leaves','escaped_power'],['Unresolved at Limit','unresolved_power'],['Signed Residual','signed_residual']] as const){const card=document.createElement('label');card.append(span(label));const output=document.createElement('output');output.className='w4-scalar';output.dataset.testid=`w4-${key}`;output.textContent=numberText(result.ledger[key]);card.append(output);ledger.append(card);}
    this.node('w4-accounting-note').textContent='Receiver total — incoherent path sum. A split parent is not another detected contribution. Unresolved power is not absorption. A finite traversal is not the infinite-series slab solution or a coherent etalon.';
    for(const total of result.ledger.receiver_totals){const p=document.createElement('p');p.className='w4-scalar';p.textContent=`${total.element_id} / Receiver total — incoherent path sum: ${numberText(total.power_fraction)}`;p.dataset.testid=`w4-receiver-${total.element_id}`;ledger.append(p);}
    for(const b of result.branches){const option=document.createElement('option');option.value=b.id;option.textContent=`${b.id} / ${b.outcome} / Power / Source ${numberText(b.initial_state.power_fraction)}`;choices.append(option);}choices.value=this.selectedBranch??'';
    const selected=result.branches.find(b=>b.id===this.selectedBranch),branchState=this.node('w4-branch-state');
    if(selected){const s=selected.initial_state;for(const [label,value]of [['Current Branch',`${selected.id} / ${selected.outcome}`],['Medium / index',`${s.medium_id} / ${numberText(s.refractive_index)}`],['Power / Source',numberText(s.power_fraction)],['C00, C11, Re(C01), Im(C01)',s.C.map(numberText).join(', ')],['Direction',s.direction.map(numberText).join(', ')],['e1',s.frame.e1.map(numberText).join(', ')],['e2',s.frame.e2.map(numberText).join(', ')],['khat',s.frame.khat.map(numberText).join(', ')]]){const p=document.createElement('p');p.className='w4-scalar';p.textContent=`${label}: ${value}`;branchState.append(p);}}
    const table=(host:HTMLElement,headers:string[],rows:(string|HTMLElement)[][])=>{const table=document.createElement('table'),head=document.createElement('thead'),tr=document.createElement('tr');for(const title of headers){const th=document.createElement('th');th.scope='col';th.textContent=title;tr.append(th);}head.append(tr);table.append(head);const body=document.createElement('tbody');for(const values of rows){const tr=document.createElement('tr');for(const value of values){const td=document.createElement('td');td.className='w4-scalar';if(typeof value==='string')td.textContent=value;else td.append(value);tr.append(td);}body.append(tr);}table.append(body);host.append(table);};
    table(this.node('w4-terminals'),['Leaf','Receiver / Stop','Category','Power / Source','Reason'],result.terminals.filter(t=>!this.selectedBranch||t.branch_id===this.selectedBranch).map(t=>[t.branch_id,t.element_id??'—',t.category,numberText(t.state.power_fraction),t.reason]));
    table(this.node('w4-events'),['Event / Face','Branch','Class','Local R','Local T','Incoming / Source'],result.events.filter(e=>!this.selectedBranch||e.branch_id===this.selectedBranch).map(e=>{const button=document.createElement('button');button.type='button';button.dataset.testid=`w4-event-${e.id}`;button.textContent=`${e.id} / ${e.target.kind==='body_face'?`${e.target.body_id}/${e.target.face_id}`:e.target.element_id}`;button.disabled=!current;button.addEventListener('click',()=>{const selection=hitIdentity(result,e.id);if(!resolveCurrentRoutingEvent(this.controller.state.currentResult,selection))return;this.selectedEventIdentity=selection;this.resource?.selectEvent(e.id);this.controller.select((e.target.kind==='body_face'?e.target.body_id:e.target.element_id)!);this.showHit();this.tab('inspector');});return[button,e.branch_id,e.classification,e.interface?numberText(e.interface.power_fractions.R_incident):'—',e.interface?numberText(e.interface.power_fractions.T_incident):'—',numberText(e.incident_state.power_fraction)];}));
    const times=state.timings;this.node('w4-timings').textContent=times?`HTTP + decode ${numberText(times.httpAndDecodeMs)} ms; decode ${numberText(times.decodeMs)} ms; display preparation ${numberText(times.attachmentMs)} ms. CPU observations, not GPU timing.`:'';
  }
  private showHit():void{
    const result=this.controller.state.currentResult,e=resolveCurrentRoutingEvent(result,this.selectedEventIdentity),host=this.node('w4-selected-event');host.replaceChildren();this.node('w4-slab-displacement').hidden=true;
    if(!result||!e){this.apparatus?.selectFace(null,null);host.textContent='No current event — trace the updated scene.';return;}
    this.apparatus?.selectFace(e.target.kind==='body_face'?e.target.body_id:null,e.target.kind==='body_face'?e.target.face_id:null);
    const heading=document.createElement('h3');heading.textContent=`Current Interface / ${e.id}`;host.append(heading);
    const readout=document.createElement('div');readout.className='w4-readout w2-table-scroll';readout.tabIndex=0;readout.setAttribute('role','region');readout.setAttribute('aria-label','Complete current interface values, horizontally scrollable');
    const add=(label:string,value:string)=>{const p=document.createElement('p');p.className='w4-scalar';const valueNode=span(value);if(['R_s','R_p','T_s','T_p','R_incident','T_incident'].includes(label))valueNode.dataset.testid=`w4-interface-${label}`;p.append(span(`${label}: `),valueNode);readout.append(p);};
    add('Model',result.model_contract);add('Request',result.request_id);add('Scene SHA-256',result.scene_sha256);add('Branch / Event',`${e.branch_id} / ${e.id}`);add('Class',e.classification);
    const showState=(title:string,s:typeof e.incident_state)=>{const h=document.createElement('h4');h.textContent=title;readout.append(h);add('Medium / index',`${s.medium_id} / ${numberText(s.refractive_index)}`);add('Power / Source',numberText(s.power_fraction));add('C00, C11, Re(C01), Im(C01)',s.C.map(numberText).join(', '));for(const key of ['e1','e2','khat'] as const)add(key,s.frame[key].map(numberText).join(', '));const raw=[s.power_fraction,s.C[0]-s.C[1],2*s.C[2],-2*s.C[3]];add('Raw Stokes',raw.map(numberText).join(', '));add('Normalized Stokes',s.power_fraction===0?'null':raw.map((v,k)=>numberText(k===0?1:v/s.power_fraction)).join(', '));add('DoP',s.power_fraction===0?'null':numberText(Math.hypot(...raw.slice(1))/s.power_fraction));};
    showState('Incident State',e.incident_state);
    const f=e.interface;if(f){add('Candidate Transmission Medium',f.transmission_medium_id);add('Incidence / deg',numberText(f.incident_angle_rad*180/Math.PI));add('Transmitted / deg',f.transmitted_angle_rad===null?'Not applicable — no propagating transmitted ray':numberText(f.transmitted_angle_rad*180/Math.PI));
      const h=document.createElement('h4');h.textContent='Local Interface Fractions — relative to arriving power';readout.append(h);for(const key of ['R_s','R_p','T_s','T_p','R_incident','T_incident'] as const)add(key,numberText(f.power_fractions[key]));const a=document.createElement('h4');a.textContent='Electric-Field Coefficients — real, imaginary';readout.append(a);for(const key of ['r_s','r_p','t_s','t_p'] as const)add(key,f.coefficients[key]?.map(numberText).join(', ')??'Not applicable');add('Transmission power flux factor',f.coefficients.flux_factor===null?'Not applicable':numberText(f.coefficients.flux_factor));
      if(e.classification==='total_internal_reflection')add('Total Internal Reflection','No propagating transmitted branch. Reflected state retains the incident medium and s/p phase difference.');
      for(const leg of f.legs){add(leg.kind==='R'?'Reflected Child':'Transmitted Child',`${leg.branch_id??'—'} / ${leg.disposition}`);if(leg.state)showState(`${leg.kind} cumulative state — attenuation already included`,leg.state);}
      add('Local Signed Residual',numberText(f.local_signed_residual));}
    host.append(readout);const detail=document.createElement('details'),summary=document.createElement('summary'),pre=document.createElement('pre');summary.textContent='Numerical Certificates';pre.className='w4-scalar';pre.textContent=stringifyRoutingJSON({geometry:e.numerical_bounds,interface:f?.numerical_bounds??null,incident:e.incident_state.numerical_bounds});detail.className='w4-certificates w2-table-scroll';detail.tabIndex=0;detail.append(summary,pre);host.append(detail);this.resource?.selectEvent(e.id);
  }
  numericalOwners(): readonly (FresnelTraceResult | null)[] { return this.controller.numericalOwners(); }
  ownedNumericalBytes(): number { return this.controller.ownedNumericalBytes(); }
  ownedDOMBytes(): number { return measureRoutingDOMReservation([this.host, this.navigation]) + this.fields.reduce((sum, field) => sum + 256 + field.path.length * 2 + field.input.value.length * 2, 0); }
  ownedRenderingBytes(): number { return this.ownedDOMBytes() + (this.selectedEventIdentity ? routingMetadataReservation(this.selectedEventIdentity) : 0) + (this.apparatus?.ownedBytes ?? 0) + [...this.displays].reduce((sum, resource) => sum + resource.ownedBytes, 0); }
  ownedBytes(): number { return this.ownedNumericalBytes() + this.ownedRenderingBytes() + this.controller.ownedStateBytes(); }
  releaseResults(): boolean {
    if (!this.controller.releaseResults()) return false; this.apparatus?.setDisplay(null); for (const resource of this.displays) resource.dispose(); this.displays.clear(); this.resource = null; this.selectedBranch = null; this.selectedEventIdentity = null; this.updateResult(true); return true;
  }
  snapshot(): object {
    const state = this.controller.state, result = state.currentResult ?? state.completedNumerical ?? state.lastResult;
    return { active: this.active, mounted: this.mounted, revision: state.revision, attachmentEpoch: state.attachmentEpoch, selection: state.selection,
      status: state.status, error: state.error, renderError: state.renderError, canRetryPresentation: this.controller.canRetryPresentation,
      candidate: state.candidate, validatedDigest: state.validatedDigest, currentRequestId: state.currentResult?.request_id ?? null,
      previousRequestId: state.lastResult?.request_id ?? null, completedRequestId: state.completedNumerical?.request_id ?? null,
      currentResult: state.currentResult, selectedBranch: this.selectedBranch, selectedEvent: this.selectedEventIdentity?.eventId ?? null, selectedEventIdentity: this.selectedEventIdentity, timings: state.timings,
      numericalBytes: this.ownedNumericalBytes(), renderingBytes: this.ownedRenderingBytes(), stateBytes: this.controller.ownedStateBytes(), domReservationBytes: this.ownedDOMBytes(), ownedBytes: this.ownedBytes(),
      resultResource: result ? fresnelResourceBreakdown(result) : null, apparatus: this.apparatus?.snapshot() ?? null, display: this.resource?.snapshot() ?? null };
  }
  dispose(): void {
    if (this.disposed) return; this.disposed = true; this.unsubscribe(); this.unsubscribeGate(); this.controller.bindPresentation(null);
    if (this.mounted) this.scene?.hideGeometricRoutingApparatus(); this.scene?.setGeometricRoutingLabelUpdater(null);
    for (const resource of this.displays) resource.dispose(); this.displays.clear(); this.resource = null; this.apparatus?.dispose(); this.apparatus = null; this.navigation.remove(); this.host.replaceChildren();
  }
}
