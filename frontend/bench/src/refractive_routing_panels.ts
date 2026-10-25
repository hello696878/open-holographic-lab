/** W3 child controls inside the existing Geometric Routing workspace. */
import * as THREE from 'three';
import { NumericFieldBinding } from './numeric_fields';
import { routingMetadataReservation, routingStructuralEqual, type RoutingKind } from './geometric_routing_contracts';
import { measureRoutingDOMReservation, type GeometricRoutingScenePort } from './geometric_routing_workspace';
import { createRefractiveRoutingApparatus, prepareRefractiveRoutingDisplay, type RefractiveRoutingApparatus, type RefractiveRoutingDisplay } from './refractive_routing_apparatus';
import { W3_PRESETS, W3_RETAINED_RESERVATION, W3_DISCLAIMER, assertRefractiveScene, refractiveResourceBreakdown,
  type RefractiveScene, type RefractiveTraceResult, type RefractiveValidationReply } from './refractive_routing_contracts';
import { RefractiveRoutingController, type RefractiveRoutingPrepared, type RefractiveRoutingState } from './refractive_routing_state';

export interface RefractiveRoutingPanelsOptions {
  admit(persistent: number, transient: number): void; readonly labelHost?: HTMLElement; readonly navigationHost?: HTMLElement;
}
export interface RefractiveRoutingEventIdentity {
  readonly requestId: string; readonly sceneSha256: string; readonly model: string; readonly branchId: string; readonly eventId: string;
}
/** Resolve a presentation selection only against its current accepted trace. */
export function resolveCurrentRoutingEvent(result: RefractiveTraceResult | null, selection: RefractiveRoutingEventIdentity | null): RefractiveTraceResult['events'][number] | null {
  if (!result || !selection || result.request_id !== selection.requestId || result.scene_sha256 !== selection.sceneSha256) return null;
  if (result.model_contract !== selection.model) return null; return result.events.find(hit => hit.id === selection.eventId && hit.branch_id === selection.branchId) ?? null;
}
function hitIdentity(result: RefractiveTraceResult, hitId: string): RefractiveRoutingEventIdentity {
  return Object.freeze({ requestId: result.request_id, sceneSha256: result.scene_sha256, model: result.model_contract, branchId: result.events.find(e=>e.id===hitId)!.branch_id, eventId: hitId });
}
export interface ParallelBlockDisplacement {
  readonly model: string; readonly requestId: string; readonly sceneSha256: string; readonly branchId: string;
  readonly bodyId: string; readonly entryEventId: string; readonly exitEventId: string; readonly displacement_m: number;
}
/** Geometric perpendicular offset from current returned points; no optical solution or fitted planning value. */
export function deriveCurrentParallelBlockDisplacement(result: RefractiveTraceResult | null, selection: RefractiveRoutingEventIdentity | null): ParallelBlockDisplacement | null {
  if (!result || !selection || !resolveCurrentRoutingEvent(result,selection)) return null;
  const body=result.scene.bodies[0]; if(result.scene.bodies.length!==1 || body.kind!=='rectangular_block') return null;
  const events=result.events.filter(e=>e.branch_id===selection.branchId && e.target.kind==='body_face' && e.target.body_id===body.id);
  if(events.length!==2) return null; const [entry,exit]=events;
  if(entry.classification!=='enter_refraction' || exit.classification!=='exit_refraction' || entry.target.kind!=='body_face' || exit.target.kind!=='body_face' || entry.outgoing.length!==1 || exit.outgoing.length!==1) return null;
  const pair=/^([xyz])_(min|max)$/.exec(entry.target.face_id);
  if(!pair || exit.target.face_id!==`${pair[1]}_${pair[2]==='min'?'max':'min'}` || entry.incident_medium_id!==result.scene.exterior_medium.id || exit.outgoing[0].medium_id!==result.scene.exterior_medium.id || entry.incident_refractive_index!==exit.outgoing[0].refractive_index) return null;
  const incoming=entry.incident_direction,emergent=exit.outgoing[0].direction;
  const cross=(a:readonly number[],b:readonly number[]):[number,number,number]=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
  const norm=Math.hypot(...incoming),outNorm=Math.hypot(...emergent);
  // Qualification of a display-derived parallel-line metric, not a numerical repair/admission rule.
  if(!Number.isFinite(norm) || !Number.isFinite(outNorm) || norm===0 || outNorm===0 || incoming.reduce((s,v,k)=>s+v*emergent[k],0)<=0 || Math.hypot(...cross(incoming,emergent))>128*Number.EPSILON*norm*outNorm) return null;
  const delta=exit.position_m.map((v,k)=>v-entry.position_m[k]);
  const displacement_m=Math.hypot(...cross(delta,incoming))/norm;
  if(!Number.isFinite(displacement_m)) return null;
  return Object.freeze({model:result.model_contract,requestId:result.request_id,sceneSha256:result.scene_sha256,branchId:selection.branchId,bodyId:body.id,entryEventId:entry.id,exitEventId:exit.id,displacement_m});
}
const names: Readonly<Record<RoutingKind, string>> = { mirror: 'Mirror', ideal_splitter_50_50: 'Ideal 50:50 Splitter', beam_stop: 'Beam Stop', receiver: 'Receiver' };
const units = ['X', 'Y', 'Z'] as const;
interface Field { readonly input: HTMLInputElement; readonly binding: NumericFieldBinding; readonly path: string; readonly scale: number; readonly value: () => number }
export const W3_DOM_RESERVATION_CAP = 1024 * 1024;
const numberText = (value: number): string => Object.is(value, -0) ? '-0' : String(value);
function span(text: string): HTMLSpanElement { const item = document.createElement('span'); item.textContent = text; return item; }

export class RefractiveRoutingPanels {
  private active = false; private disposed = false; private mounted = false; private hasFramed = false;
  private apparatus: RefractiveRoutingApparatus | null = null; private apparatusScene: RefractiveScene | null = null;
  private apparatusFrames: RefractiveValidationReply | null = null; private resource: RefractiveRoutingDisplay | null = null;
  private readonly displays = new Set<RefractiveRoutingDisplay>(); private readonly fields: Field[] = [];
  private selectedBranch: string | null = null; private selectedEventIdentity: RefractiveRoutingEventIdentity | null = null; private editorIdentity = '';
  private resultIdentity: RefractiveTraceResult | null = null; private resultCurrent = false; private readonly navigation: HTMLElement; private showNormals=true; private showAngles=true; private opacity=.18;
  private readonly unsubscribe: () => void; private readonly unsubscribeGate: () => void;
  constructor(readonly host: HTMLElement, readonly controller: RefractiveRoutingController, private readonly scene: GeometricRoutingScenePort | null,
      private readonly options: RefractiveRoutingPanelsOptions) {
    host.classList.add('w2-workspace','w3-workspace'); host.hidden = true;
    const navigation = document.createElement('section'); navigation.className = 'w2-navigation w3-navigation'; navigation.setAttribute('aria-label', 'Geometric routing controls');
    navigation.innerHTML = `<div class="w2-heading"><div><span class="eyebrow">W3 / IDEAL REFRACTIVE ROUTING</span><h2>Geometric Routing</h2><p>One closed transparent body. Calculated finite interfaces.</p></div>
      <output data-testid="w3-status" class="w2-status" aria-live="polite">Draft / not traced</output></div>
      <div class="w2-actions"><label>Apparatus <select data-testid="w3-preset" aria-label="Routing apparatus preset"><option value="A">A / Parallel slab</option><option value="B">B / Prism deviation</option><option value="C">C / Prism with internal TIR</option></select></label>
      <button type="button" data-testid="w3-load-preset">Load Preset</button><button type="button" class="primary" data-testid="w3-trace">Trace</button>
      <div class="w2-camera-controls" role="group" aria-label="Routing camera"><button type="button" data-testid="w3-orbit">Orbit</button><button type="button" data-testid="w3-top">Top View</button><button type="button" data-testid="w3-focus">Focus</button><button type="button" data-testid="w3-reset">Reset View</button></div></div>
      <p class="w2-legend">Ideal route weights; Fresnel losses are not modeled. SI metres / right-handed Y-up. Amber: exterior; teal: body. Color and thickness identify routes/media, not dispersion, beam width or optical power.</p>
      <p class="error" role="alert" data-testid="w3-error" hidden></p><p class="error" role="alert" data-testid="w3-display-error" hidden></p>
      <button type="button" data-testid="w3-retry-display" hidden>Restore Display (No Recalculation)</button>`;
    this.navigation = navigation; if (options.navigationHost) { options.navigationHost.classList.add('w2-controls'); options.navigationHost.append(navigation); options.navigationHost.hidden = true; } else host.before(navigation);
    host.innerHTML = `<aside class="w2-left panel"><div class="w2-panel-heading"><span class="eyebrow">APPARATUS</span><h2>Finite Optical Elements</h2></div>
      <p class="w2-note">Hit order is calculated from geometry, independent of this list.</p><div data-testid="w3-components" class="w2-components"></div>
      <div class="w2-add-controls"><label>Add Element <select data-testid="w3-add-kind"><option value="mirror">Mirror</option><option value="ideal_splitter_50_50">Ideal 50:50 Splitter</option><option value="beam_stop">Beam Stop</option><option value="receiver">Receiver</option></select></label>
      <button type="button" data-testid="w3-add">Add Element</button><button type="button" data-testid="w3-remove">Remove Selected</button></div>
      <p class="w2-model-note">One outside source. At most one closed body. All side and end faces are optical. Mounts are decorative. No dispersion, Fresnel branches or wave propagation.</p>
      <p class="w2-document-note" data-testid="w3-documents-unsupported">Routing scene import/export is not supported in this slice. Existing experiment settings remain available in their original workspaces.</p></aside>
      <aside class="w2-right panel"><nav class="w2-tabs" role="tablist" aria-label="Routing inspection"><button type="button" id="w3-tab-inspector" data-testid="w3-tab-inspector" role="tab" aria-selected="true" aria-controls="w3-panel-inspector">Inspector</button>
      <button type="button" id="w3-tab-data" data-testid="w3-tab-data" role="tab" aria-selected="false" aria-controls="w3-panel-data" tabindex="-1">Trace Data</button></nav>
      <section id="w3-panel-inspector" role="tabpanel" aria-labelledby="w3-tab-inspector"><span class="eyebrow">SELECTED COMPONENT</span><h3 data-testid="w3-selected">Source</h3>
      <section data-testid="w3-slab-displacement" class="w2-result-state" hidden></section>
      <div data-testid="w3-editor" class="w2-editor-grid"></div><p class="w2-note">Changing one field preserves untouched SI components. X/Y/Z rotations apply actively in X, then Y, then Z order. Only Trace recomputes.</p>
      <div class="w2-selection-details" data-testid="w3-selected-event"></div></section>
      <section id="w3-panel-data" role="tabpanel" aria-labelledby="w3-tab-data" hidden><output class="w2-result-state" data-testid="w3-result-state">No calculated result</output>
      <div class="w2-identity w2-table-scroll" tabindex="0" role="region" aria-label="Full result identity" data-testid="w3-identity"></div>
      <div class="w2-ledger" data-testid="w3-ledger"></div><p class="w2-note" data-testid="w3-accounting-note">Relative ray weights, not watts or irradiance. Computational truncation remains separate from absorption.</p>
      <label class="w2-branch-control">Inspect Branch <select data-testid="w3-branch" aria-label="Inspect calculated branch"><option value="">All branches</option></select></label>
      <div class="w2-table-scroll" role="region" tabindex="0" aria-label="Branch terminal outcomes, horizontally scrollable" data-testid="w3-terminals"></div>
      <div class="w2-table-scroll" role="region" tabindex="0" aria-label="Actual calculated hits, horizontally scrollable" data-testid="w3-events"></div>
      <output class="w2-timings" data-testid="w3-timings"></output></section></aside>`;
    this.node('w3-load-preset').addEventListener('click', () => { const preset = this.node<HTMLSelectElement>('w3-preset').value as keyof typeof W3_PRESETS; this.hasFramed = false; void controller.setPreset(preset); });
    this.node('w3-trace').addEventListener('click', () => { void controller.trace(); });
    this.node('w3-add').addEventListener('click', () => { this.tab('inspector'); void controller.add(this.node<HTMLSelectElement>('w3-add-kind').value as RoutingKind); });
    this.node('w3-remove').addEventListener('click', () => { void (controller.state.candidate.bodies.some(b=>b.id===controller.state.selection)?controller.removeBody():controller.remove()); });
    this.installViewControls(); this.node('w3-retry-display').addEventListener('click', () => { controller.retryPresentation(); });
    this.node<HTMLSelectElement>('w3-branch').addEventListener('change', event => { this.selectedBranch = (event.target as HTMLSelectElement).value || null;  this.updateResult(true); });
    for (const [id, view] of [['w3-orbit', 'overview'], ['w3-top', 'top'], ['w3-focus', 'focus'], ['w3-reset', 'overview']] as const) this.node(id).addEventListener('click', () => this.camera(view));
    for (const tab of ['inspector', 'data'] as const) {
      this.node(`w3-tab-${tab}`).addEventListener('click', () => this.tab(tab));
      this.node(`w3-tab-${tab}`).addEventListener('keydown', event => { if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return; event.preventDefault(); const next = event.key === 'Home' ? 'inspector' : event.key === 'End' ? 'data' : tab === 'inspector' ? 'data' : 'inspector'; this.tab(next); this.node(`w3-tab-${next}`).focus(); });
    }
    controller.bindPresentation(result => this.prepare(result)); this.unsubscribe = controller.subscribe(state => this.render(state)); this.unsubscribeGate = controller.gate.subscribe(() => this.render(controller.state));
  }
  private node<T extends HTMLElement = HTMLElement>(id: string): T {
    const node = this.host.querySelector<T>(`[data-testid="${id}"]`) ?? this.navigation.querySelector<T>(`[data-testid="${id}"]`);
    if (!node) throw new Error(`Missing Geometric Routing area: ${id}`); return node;
  }
  private tab(tab: 'inspector' | 'data'): void {
    for (const item of ['inspector', 'data'] as const) { const selected = item === tab, button = this.node<HTMLButtonElement>(`w3-tab-${item}`);
      button.setAttribute('aria-selected', String(selected)); button.tabIndex = selected ? 0 : -1; this.host.querySelector<HTMLElement>(`#w3-panel-${item}`)!.hidden = !selected; }
  }
  setActive(active: boolean): void {
    if (this.disposed || this.active === active) return; this.active = active; this.host.hidden = !active;
    if (this.options.navigationHost) this.options.navigationHost.hidden = !active; this.navigation.hidden = !active;
    if (active) void this.controller.activate(); else this.controller.deactivate(); this.render(this.controller.state);
  }
  selectElement(id: string): void { this.controller.select(id); this.tab('inspector'); }
  private syncApparatus(state: RefractiveRoutingState): void {
    if (!this.active) {
      // An inactive W3 gate subscriber must not clear the active W2 label owner.
      if (this.mounted) { this.scene?.hideGeometricRoutingApparatus(); this.scene?.setGeometricRoutingLabelUpdater(null); }
      this.apparatus?.setLabelsVisible(false); this.mounted = false; return;
    }
    const draft = state.validatedDraft ?? state.candidate;
    try { assertRefractiveScene(draft); } catch { this.apparatus?.setDisplay(null); return; }
    if (!this.scene) throw new Error('The existing WebGL scene is unavailable. No substitute calculated path is displayed.');
    if (!this.apparatus || !routingStructuralEqual(this.apparatusScene, draft) || !routingStructuralEqual(this.apparatusFrames, state.validation)) {
      // Reserve the static apparatus before constructing any replacement alongside the old one.
      this.options.admit(768 * 1024, 768 * 1024);
      const next = createRefractiveRoutingApparatus(draft, state.validation, { labelHost: this.options.labelHost, onSelect: id => this.selectElement(id) }), previous = this.apparatus;
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
  private render(state: RefractiveRoutingState): void {
    if (this.disposed) return;
    if (!state.currentResult && this.resource) { this.apparatus?.setDisplay(null); this.drop(this.resource); this.resource = null; }
    this.syncApparatus(state);
    const busy = this.controller.gate.busy;
    this.node<HTMLButtonElement>('w3-trace').disabled = !this.active || busy || state.pendingValidation || !state.validatedDraft || Object.keys(state.invalidEdits).length > 0;
    const bodyFaces = state.candidate.bodies.length ? state.candidate.bodies[0].kind === 'rectangular_block' ? 6 : 5 : 0;
    this.node<HTMLButtonElement>('w3-add').disabled = state.candidate.elements.length + bodyFaces >= 16;
    this.node<HTMLButtonElement>('w3-remove').disabled = state.selection === 'source';
    const status = state.active ? 'Tracing / worker occupied' : state.pendingValidation ? 'Validating draft / no trace' : state.error || Object.keys(state.invalidEdits).length ? 'Invalid draft / not traced'
      : state.currentResult ? state.currentResult.status === 'complete' ? 'Calculated / complete' : 'Trace incomplete / limit reached'
      : state.lastResult || state.completedNumerical ? 'Draft changed / previous result detached' : !state.validatedDraft ? 'Draft not validated / review inputs' : 'Ready / press Trace';
    this.node('w3-status').textContent = status;
    const invalid = Object.keys(state.invalidEdits).length ? 'Enter a complete finite number. Invalid text is preserved.' : null;
    this.node('w3-error').hidden = !state.error && !invalid; this.node('w3-error').textContent = state.error ?? invalid ?? '';
    this.node('w3-display-error').hidden = !state.renderError; this.node('w3-display-error').textContent = state.renderError ?? '';
    this.node<HTMLButtonElement>('w3-retry-display').hidden = !this.controller.canRetryPresentation;
    this.node<HTMLButtonElement>('w3-retry-display').disabled = busy;
    this.componentList(state); this.editor(state); this.updateResult();
    if (this.ownedDOMBytes() > W3_DOM_RESERVATION_CAP) throw new Error('Routing inspector DOM exceeds its bounded 1 MiB app-owned reservation; no successful display was published.');
  }
  private componentList(state: RefractiveRoutingState): void {
    const host = this.node('w3-components'), identity = state.candidate.bodies.map(b=>`${b.id}:${b.kind}`).join('|')+state.candidate.elements.map(element => `${element.id}:${element.kind}`).join('|');
    if (host.dataset.identity !== identity) {
      host.replaceChildren(); host.dataset.identity = identity;
      const entries = [{ id: 'source', title: 'Laser Source', kind: 'One outside ray' }, ...state.candidate.bodies.map(body=>({id:body.id,title:'Transparent Body',kind:`${body.id} / ${body.kind}`})), ...state.candidate.elements.map(element => ({ id: element.id, title: names[element.kind], kind: element.id }))];
      for (const entry of entries) { const button = document.createElement('button'); button.type = 'button'; button.className = 'w2-component'; button.dataset.testid = `w3-select-${entry.id}`; button.dataset.elementId = entry.id;
        const title = document.createElement('strong'); title.textContent = entry.title; button.append(title, span(entry.kind)); button.addEventListener('click', () => this.selectElement(entry.id)); host.append(button); }
    }
    for (const button of host.querySelectorAll<HTMLButtonElement>('button')) { const selected = button.dataset.elementId === state.selection; button.classList.toggle('selected', selected); button.setAttribute('aria-pressed', String(selected)); }
  }
  private editor(state: RefractiveRoutingState): void {
    const body=state.candidate.bodies.find(b=>b.id===state.selection), index=state.candidate.elements.findIndex(e=>e.id===state.selection), item=state.candidate.elements[index];
    const identity=`${state.selection}/${body?.kind??item?.aperture.kind??'source'}/${index}`;
    if(this.editorIdentity!==identity){this.editorIdentity=identity;const host=this.node('w3-editor');host.replaceChildren();this.fields.length=0;
      this.node('w3-selected').textContent=body?`${body.id} / ${body.kind==='rectangular_block'?'Rectangular Block':'Right Triangular Prism'}`:state.selection==='source'?'Laser Source / one outside ray':`${item.id} / ${names[item.kind]}`;
      const add=(label:string,id:string,path:string,value:()=>number,scale=1)=>{const row=document.createElement('label');row.textContent=label;const input=document.createElement('input');input.type='text';input.inputMode='decimal';input.autocomplete='off';input.dataset.testid=id;input.setAttribute('aria-label',label);const binding=new NumericFieldBinding();this.fields.push({input,binding,path,scale,value});row.append(input);host.append(row);const edit=()=>{const current=this.controller.state;if(binding.shouldEdit(input.value,path,current.revision,value()))void this.controller.edit(path,input.value,scale);};input.addEventListener('input',edit);input.addEventListener('change',edit);};
      if(body){const shapeLabel=document.createElement('label');shapeLabel.textContent='Transparent body shape';const shape=document.createElement('select');shape.dataset.testid='w3-body-shape';for(const [value,text]of [['rectangular_block','Rectangular Block'],['right_triangular_prism','Right Triangular Prism']]){const option=document.createElement('option');option.value=value;option.textContent=text;shape.append(option);}shape.value=body.kind;shape.addEventListener('change',()=>void this.controller.changeBodyKind(shape.value as typeof body.kind));shapeLabel.append(shape);host.append(shapeLabel);
        const current=()=>this.controller.state.candidate.bodies[0];units.forEach((axis,k)=>add(`${axis} position / m`,`w3-position-${axis.toLowerCase()}`,`bodies.0.pose.position_m.${k}`,()=>current().pose.position_m[k]));units.forEach((axis,k)=>add(`${axis} rotation / deg`,`w3-rotation-${axis.toLowerCase()}`,`bodies.0.pose.rotation_xyz_rad.${k}`,()=>current().pose.rotation_xyz_rad[k],Math.PI/180));
        for(const key of Object.keys(body.shape))add(key.replaceAll('_',' '),`w3-${key}`,`bodies.0.shape.${key}`,()=>(current().shape as unknown as Record<string,number>)[key]);
        add('Exterior refractive index','w3-exterior-index','exterior_medium.refractive_index',()=>this.controller.state.candidate.exterior_medium.refractive_index);add('Interior refractive index','w3-interior-index','bodies.0.interior_medium.refractive_index',()=>current().interior_medium.refractive_index);
        const note=document.createElement('p');note.className='w3-index-note';note.textContent='Ideal constant indices; no material or dispersion database. All finite side and end faces are optical.';host.append(note);
      }else if(state.selection==='source'){units.forEach((axis,k)=>add(`${axis} position / m`,`w3-source-origin-${axis.toLowerCase()}`,`source.origin_m.${k}`,()=>this.controller.state.candidate.source.origin_m[k]));units.forEach((axis,k)=>add(`${axis} direction / unit vector`,`w3-source-direction-${axis.toLowerCase()}`,`source.direction.${k}`,()=>this.controller.state.candidate.source.direction[k]));}
      else{const current=()=>this.controller.state.candidate.elements.find(e=>e.id===state.selection)!;units.forEach((axis,k)=>add(`${axis} position / m`,`w3-position-${axis.toLowerCase()}`,`elements.${index}.pose.position_m.${k}`,()=>current().pose.position_m[k]));units.forEach((axis,k)=>add(`${axis} rotation / deg`,`w3-rotation-${axis.toLowerCase()}`,`elements.${index}.pose.rotation_xyz_rad.${k}`,()=>current().pose.rotation_xyz_rad[k],Math.PI/180));if(item.aperture.kind==='disk')add('Radius / m','w3-radius',`elements.${index}.aperture.radius_m`,()=>(current().aperture as {radius_m:number}).radius_m);else{add('Full width / m','w3-width',`elements.${index}.aperture.width_m`,()=>(current().aperture as {width_m:number}).width_m);add('Full height / m','w3-height',`elements.${index}.aperture.height_m`,()=>(current().aperture as {height_m:number}).height_m);}}
    }
    for(const f of this.fields){const value=f.value(),text=state.invalidEdits[f.path]??numberText(value/f.scale);if(document.activeElement!==f.input&&f.input.value!==text)f.input.value=text;f.binding.paint(f.input.value,f.path,state.revision,value);f.input.setAttribute('aria-invalid',String(Object.hasOwn(state.invalidEdits,f.path)));}
  }
  private installViewControls():void{
    const box=document.createElement('div');box.className='w3-view-controls';box.innerHTML=`<label><input type="checkbox" data-testid="w3-normals" checked>Normals</label><label><input type="checkbox" data-testid="w3-angles" checked>Angles</label><label>Body opacity <input type="range" min="0.05" max="0.5" step="0.01" value="0.18" data-testid="w3-opacity"></label>`;this.navigation.append(box);
    const apply=()=>{this.showNormals=this.node<HTMLInputElement>('w3-normals').checked;this.showAngles=this.node<HTMLInputElement>('w3-angles').checked;this.opacity=Number(this.node<HTMLInputElement>('w3-opacity').value);this.apparatus?.setOpacity(this.opacity);this.resource?.setAnnotations(this.showNormals,this.showAngles);};box.addEventListener('change',apply);box.addEventListener('input',apply);
  }
  private camera(view: 'overview' | 'top' | 'focus'): void {
    try { if (!this.active || !this.apparatus || !this.scene) return; const bounds = this.apparatus.framingBounds(view === 'focus' ? this.controller.state.selection : undefined);
      if (view !== 'focus' && this.resource) bounds.union(this.resource.framingBounds()); this.scene.fitGeometricRoutingApparatus(bounds, view);
    } catch (error) { this.controller.reportPresentationFailure(String(error)); }
  }
  private prepare(result: RefractiveTraceResult): RefractiveRoutingPrepared {
    if (!this.active || !this.scene) throw new Error('Geometric Routing is not attached to the active bench.');
    this.syncApparatus(this.controller.state); if (!this.apparatus) throw new Error('The validated geometric apparatus is unavailable.'); this.scene.assertGeometricRoutingReady();
    const next = prepareRefractiveRoutingDisplay(result, { labelHost: this.options.labelHost }), previous = this.resource;
    try {
      if (this.controller.ownedNumericalBytes() + next.ownedBytes + this.apparatus.ownedBytes + this.controller.ownedStateBytes() + W3_DOM_RESERVATION_CAP > W3_RETAINED_RESERVATION) throw new Error('Routing records, inspector and display exceed the approved 4 MiB reservation.');
      const incomingDOM = Math.max(0, W3_DOM_RESERVATION_CAP - this.ownedDOMBytes());
      this.options.admit(next.ownedBytes + incomingDOM, next.ownedBytes + W3_DOM_RESERVATION_CAP); this.displays.add(next);
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
  private drop(resource: RefractiveRoutingDisplay): void { resource.dispose(); this.displays.delete(resource); }
  private updateResult(force = false): void {
    const state = this.controller.state, current = !!state.currentResult, result = state.currentResult ?? state.completedNumerical ?? state.lastResult;
    if (!resolveCurrentRoutingEvent(state.currentResult, this.selectedEventIdentity)) this.selectedEventIdentity = null;
    this.showHit();
    if (!force && result === this.resultIdentity && current === this.resultCurrent) return; this.resultIdentity = result; this.resultCurrent = current;
    this.node('w3-result-state').textContent = result ? `${current ? 'Current' : state.completedNumerical === result ? 'Numerical result / display detached' : 'Previous trace — does not match the current draft'} / ${result.status === 'incomplete' ? 'Trace incomplete — limit reached' : 'Complete bounded trace'}` : 'No calculated result';
    const identity = this.node('w3-identity'); identity.replaceChildren(); const ledger = this.node('w3-ledger'); ledger.replaceChildren();
    const branchSelect = this.node<HTMLSelectElement>('w3-branch'); branchSelect.replaceChildren(); const all = document.createElement('option'); all.value = ''; all.textContent = 'All branches'; branchSelect.append(all);
    this.node('w3-terminals').replaceChildren(); this.node('w3-events').replaceChildren();
    if (!result) { this.node('w3-timings').textContent = ''; return; }
    if (this.selectedBranch && !result.branches.some(branch => branch.id === this.selectedBranch)) this.selectedBranch = null;
    for (const [title, value] of [['Request', result.request_id], ['Scene SHA256', result.scene_sha256], ['Model', result.model_contract]]) { const row = document.createElement('p'); row.append(span(`${title}: `), span(value)); identity.append(row); }
    for (const [title, value] of [['Detected', result.ledger.detected_weight], ['Absorbed', result.ledger.absorbed_weight], ['Escaped', result.ledger.escaped_weight], ['Truncated', result.ledger.truncated_weight]] as const) {
      const card = document.createElement('label'); card.append(span(title)); const number = document.createElement('output'); number.textContent = numberText(value); number.dataset.testid = `w3-weight-${title.toLowerCase()}`; card.append(number); ledger.append(card);
    }
    this.node('w3-accounting-note').textContent = `Input weight ${result.ledger.input_weight}; signed residual ${numberText(result.ledger.signed_residual)}. Relative ray weights, not watts or irradiance. Escaped means outside the 1 m source-centered trace region. Truncation is not absorption.`;
    for (const branch of result.branches) { const option = document.createElement('option'); option.value = branch.id; option.textContent = `${branch.id} / ${branch.outcome} / weight ${branch.relative_weight}`; branchSelect.append(option); }
    branchSelect.value = this.selectedBranch ?? '';
    const table = (host: HTMLElement, headers: string[], rows: (string | HTMLElement)[][]) => {
      const table = document.createElement('table'), head = document.createElement('thead'), tr = document.createElement('tr'); for (const title of headers) { const th = document.createElement('th'); th.scope = 'col'; th.textContent = title; tr.append(th); } head.append(tr); table.append(head);
      const body = document.createElement('tbody'); for (const row of rows) { const tr = document.createElement('tr'); for (const value of row) { const td = document.createElement('td'); td.className = 'w2-scalar'; if (typeof value === 'string') td.textContent = value; else td.append(value); tr.append(td); } body.append(tr); } table.append(body); host.append(table);
    };
    const terminals = result.terminals.filter(terminal => !this.selectedBranch || terminal.branch_id === this.selectedBranch);
    table(this.node('w3-terminals'), ['Branch', 'Parent', 'Outcome', 'Weight', 'Distance / m', 'Reason'], terminals.map(terminal => [terminal.branch_id, result.branches.find(branch => branch.id === terminal.branch_id)?.parent_id ?? '—', terminal.category, numberText(terminal.relative_weight), numberText(terminal.cumulative_length_m), terminal.reason]));
    const hits = result.events.filter(hit => !this.selectedBranch || hit.branch_id === this.selectedBranch);
    table(this.node('w3-events'), ['Event / Body / Face', 'Branch', 'u / m', 'v / m', 'Distance / m'], hits.map(hit => {
      const button = document.createElement('button'); button.type = 'button'; button.dataset.testid = `w3-event-${hit.id}`; button.textContent = `${hit.id} / ${hit.target.kind==='body_face'?hit.target.body_id+'/'+hit.target.face_id:hit.target.element_id}`; button.disabled = !current;
      button.addEventListener('click', () => {
        const selection = hitIdentity(result, hit.id); if (!resolveCurrentRoutingEvent(this.controller.state.currentResult, selection)) return;
        this.selectedEventIdentity = selection; this.resource?.selectEvent(hit.id); this.controller.select(hit.target.kind==='body_face'?hit.target.body_id:hit.target.element_id); this.showHit(); this.tab('inspector'); if(deriveCurrentParallelBlockDisplacement(result,selection)) this.node('w3-slab-displacement').closest<HTMLElement>('.w2-right')!.scrollTop=0;
      });
      return [button, hit.branch_id, numberText(hit.local_uv_m[0]), numberText(hit.local_uv_m[1]), numberText(hit.cumulative_length_m)];
    }));
    const timings = state.timings;
    this.node('w3-timings').textContent = timings ? `HTTP + decode ${numberText(timings.httpAndDecodeMs)} ms; decode ${numberText(timings.decodeMs)} ms; display preparation ${numberText(timings.attachmentMs)} ms. CPU observations, not GPU timing.` : '';
  }
  private showHit(): void {
    const result = this.controller.state.currentResult, hit = resolveCurrentRoutingEvent(result, this.selectedEventIdentity), host = this.node('w3-selected-event'); host.replaceChildren();
    const summary=this.node('w3-slab-displacement'); summary.replaceChildren(); summary.hidden=true;
    if (!result || !hit) { this.apparatus?.selectFace(null,null); host.textContent = 'No current event — trace the updated scene.'; return; }
    this.apparatus?.selectFace(hit.target.kind==='body_face'?hit.target.body_id:null,hit.target.kind==='body_face'?hit.target.face_id:null);
    const measurement=deriveCurrentParallelBlockDisplacement(result,this.selectedEventIdentity);
    if(measurement){
      const heading=document.createElement('h3'); heading.textContent='Parallel-block displacement'; summary.append(heading);
      const values=document.createElement('div'); values.className='w2-table-scroll'; values.tabIndex=0; values.setAttribute('role','region'); values.setAttribute('aria-label','Full current perpendicular displacement values');
      for(const [unit,value] of [['mm',measurement.displacement_m*1000],['m',measurement.displacement_m]] as const){const row=document.createElement('p');row.className='w2-scalar';row.append(span(`Perpendicular / ${unit}: `));const output=document.createElement('output');output.dataset.testid=`w3-slab-displacement-${unit}`;output.textContent=numberText(value);row.append(output);values.append(row);}
      summary.append(values);const note=document.createElement('p');note.className='w2-note';note.textContent=`Current ${measurement.bodyId}: ${measurement.entryEventId} → ${measurement.exitEventId}. Geometric offset perpendicular to the incoming line, derived from returned entry/exit positions.`;summary.append(note);summary.hidden=false;
    }
    const title = document.createElement('h3'); title.textContent = `Current Calculated Event / ${hit.id} / ${hit.target.kind==='body_face'?hit.target.body_id+'/'+hit.target.face_id:hit.target.element_id}`; host.append(title);
    const readout = document.createElement('div'); readout.className = 'w2-table-scroll'; readout.tabIndex = 0; readout.setAttribute('role', 'region'); readout.setAttribute('aria-label', 'Full calculated hit values');
    const values = [ W3_DISCLAIMER, `Classification: ${hit.classification}`, `Incident medium: ${hit.incident_medium_id} / n=${hit.incident_refractive_index}`, `Outgoing media: ${hit.outgoing.map(o=>`${o.medium_id} / n=${o.refractive_index}`).join('; ')||'none'}`, ...hit.outgoing.map(o=>`Outgoing ${o.branch_id}: (${o.direction.map(numberText).join(', ')}) / ideal weight ${numberText(o.relative_weight)}`), ...(hit.outward_normal?[`Outward normal: (${hit.outward_normal.map(numberText).join(', ')})`, `Local basis: ${JSON.stringify(hit.local_basis)}`, `Incidence / deg: ${numberText(hit.incident_angle_rad!*180/Math.PI)}`, `${hit.classification==='total_internal_reflection'?'Reflected':'Refracted'} angle / deg: ${numberText(hit.outgoing_angle_rad!*180/Math.PI)}`, `K interval: ${JSON.stringify(hit.numerical_bounds.snell_discriminant_interval)}`]:[]),`Model: ${result.model_contract}`, `Request: ${result.request_id}`, `Scene SHA256: ${result.scene_sha256}`, `Branch: ${hit.branch_id}`, `Position / m: (${hit.position_m.map(numberText).join(', ')})`, `Receiver/surface local UV / m: (${hit.local_uv_m.map(numberText).join(', ')})`, `Incident direction: (${hit.incident_direction.map(numberText).join(', ')})`, `Cumulative geometric distance / m: ${numberText(hit.cumulative_length_m)}`, `Incoming relative weight: ${numberText(hit.incoming_weight)}`];
    values.forEach(value => { const p = document.createElement('p'); p.className = 'w2-scalar'; p.textContent = value; readout.append(p); }); host.append(readout); this.resource?.selectEvent(hit.id);
  }
  numericalOwners(): readonly (RefractiveTraceResult | null)[] { return this.controller.numericalOwners(); }
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
      resultResource: result ? refractiveResourceBreakdown(result) : null, apparatus: this.apparatus?.snapshot() ?? null, display: this.resource?.snapshot() ?? null };
  }
  dispose(): void {
    if (this.disposed) return; this.disposed = true; this.unsubscribe(); this.unsubscribeGate(); this.controller.bindPresentation(null);
    if (this.mounted) this.scene?.hideGeometricRoutingApparatus(); this.scene?.setGeometricRoutingLabelUpdater(null);
    for (const resource of this.displays) resource.dispose(); this.displays.clear(); this.resource = null; this.apparatus?.dispose(); this.apparatus = null; this.navigation.remove(); this.host.replaceChildren();
  }
}
