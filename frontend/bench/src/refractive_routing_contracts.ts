/** Closed W3 transport. Geometry and Snell/TIR calculations belong exclusively to Python. */
import { readBoundedResponse } from './contracts';
import { W2_MODEL, W2_LIMITS, assertGeometricScene, decodeGeometricTrace, parseRoutingJSON, routingMetadataReservation,
  routingStructuralEqual, stringifyRoutingJSON, type RoutingVector, type RoutingUV, type RoutingElement,
  type RoutingSurfaceFrame, type RoutingCategory, type RoutingResourceBreakdown } from './geometric_routing_contracts';

export const W3_MODEL = 'w3_ideal_refractive_routing_v1' as const;
export const W3_WEIGHT_MODEL = 'ideal_route_weights_no_fresnel_v1' as const;
export const W3_DISCLAIMER = 'Ideal route weights; Fresnel losses are not modeled.';
export const W3_REQUEST_CAP = 32768, W3_RESPONSE_CAP = 524288;
export const W3_RETAINED_RESERVATION = 4194304, W3_TRANSIENT_RESERVATION = 8388608;
export const W3_LIMITS = Object.freeze({ max_bodies: 1, max_body_faces: 6, max_legacy_elements: 16, max_total_optical_faces: 16,
  max_interactions: 32, max_branches: 31, max_records: 128, max_events: 64, max_segments: 128, trace_radius_m: 1, max_distance_m: 10 });
export const W3_NO_BODY_LIMITS = Object.freeze({ ...W3_LIMITS, max_branches: 63, max_records: 256, max_events: 128, max_segments: 256 });
export interface RefractiveMedium { readonly id: string; readonly refractive_index: number }
export interface RefractiveBody {
  readonly id: string; readonly kind: 'rectangular_block' | 'right_triangular_prism';
  readonly pose: Readonly<{ position_m: RoutingVector; rotation_xyz_rad: RoutingVector }>;
  readonly shape: Readonly<{ width_x_m: number; height_y_m: number; depth_z_m: number } | { leg_x_m: number; leg_z_m: number; height_y_m: number }>;
  readonly interior_medium: RefractiveMedium;
}
export interface RefractiveScene {
  readonly schema_version: 1; readonly model_contract: typeof W3_MODEL;
  readonly source: Readonly<{ id: 'source'; origin_m: RoutingVector; direction: RoutingVector; relative_weight: 1 }>;
  readonly exterior_medium: RefractiveMedium; readonly bodies: readonly RefractiveBody[]; readonly elements: readonly RoutingElement[];
}
export interface RefractiveFace {
  readonly body_id: string; readonly face_id: string; readonly vertices_m: readonly RoutingVector[];
  readonly plane_covector: RoutingVector; readonly outward_normal: RoutingVector; readonly local_origin_m: RoutingVector;
  readonly local_basis: Readonly<{ u: RoutingVector; v: RoutingVector }>;
  readonly numerical_bounds: Readonly<{ vertex_intervals_m: readonly (readonly RoutingUV[])[]; covector_intervals: readonly RoutingUV[];
    normal_intervals: readonly RoutingUV[]; basis_u_intervals: readonly RoutingUV[]; basis_v_intervals: readonly RoutingUV[] }>;
}
export interface RefractiveValidationRequest { readonly request_id: string; readonly scene: RefractiveScene }
export interface RefractiveTraceRequest extends RefractiveValidationRequest { readonly scene_sha256: string }
export interface RefractiveValidationReply extends RefractiveTraceRequest {
  readonly protocol_version: 1; readonly message_type: 'refractive_scene_validation'; readonly model_contract: typeof W3_MODEL;
  readonly weight_model: typeof W3_WEIGHT_MODEL; readonly media: readonly RefractiveMedium[]; readonly body_faces: readonly RefractiveFace[];
  readonly legacy_surface_frames: readonly RoutingSurfaceFrame[]; readonly limits: typeof W3_LIMITS | typeof W3_NO_BODY_LIMITS;
}
export interface RefractiveOutgoing { readonly branch_id: string; readonly direction: RoutingVector; readonly medium_id: string; readonly refractive_index: number; readonly relative_weight: number }
export interface RefractiveBranch {
  readonly id: string; readonly parent_id: string | null; readonly parent_event_id: string | null; readonly origin_m: RoutingVector;
  readonly initial_direction: RoutingVector; readonly initial_medium_id: string; readonly initial_refractive_index: number; readonly relative_weight: number;
  readonly start_cumulative_m: number; readonly start_interaction_count: number; readonly outcome: RoutingCategory | 'split';
}
export interface RefractiveSegment {
  readonly id: string; readonly branch_id: string; readonly start_m: RoutingVector; readonly end_m: RoutingVector; readonly direction: RoutingVector;
  readonly medium_id: string; readonly refractive_index: number; readonly relative_weight: number; readonly length_m: number; readonly cumulative_end_m: number; readonly event_id: string | null;
}
export type RefractiveClassification = 'enter_refraction' | 'exit_refraction' | 'total_internal_reflection' | 'mirror_reflection' | 'ideal_split' | 'stop_hit' | 'receiver_hit';
export interface RefractiveEvent {
  readonly id: string; readonly segment_id: string; readonly branch_id: string;
  readonly target: Readonly<{ kind: 'body_face'; body_id: string; face_id: string } | { kind: 'element'; element_id: string }>;
  readonly classification: RefractiveClassification; readonly position_m: RoutingVector; readonly local_uv_m: RoutingUV;
  readonly incident_direction: RoutingVector; readonly incident_medium_id: string; readonly incident_refractive_index: number;
  readonly incoming_weight: number; readonly outgoing: readonly RefractiveOutgoing[]; readonly segment_length_m: number; readonly cumulative_length_m: number;
  readonly outward_normal?: RoutingVector; readonly local_basis?: Readonly<{ u: RoutingVector; v: RoutingVector }>;
  readonly incident_angle_rad?: number; readonly outgoing_angle_rad?: number;
  readonly numerical_bounds: Readonly<{ t_parameter_interval_m: RoutingUV; position_intervals_m: readonly RoutingUV[]; local_uv_intervals_m: readonly RoutingUV[];
    incident_direction_intervals: readonly RoutingUV[]; outgoing_direction_intervals: readonly Readonly<{ branch_id: string; direction_intervals: readonly RoutingUV[] }>[];
    cumulative_length_interval_m: RoutingUV; plane_residual_m: number; snell_discriminant_interval?: RoutingUV; incident_side_interval?: RoutingUV;
    outgoing_side_interval?: RoutingUV; body_halfspace_intervals_m?: readonly RoutingUV[] }>;
}
export interface RefractiveTerminal {
  readonly branch_id: string; readonly category: RoutingCategory; readonly element_id: string | null; readonly event_id: string | null;
  readonly position_m: RoutingVector; readonly medium_id: string; readonly refractive_index: number; readonly cumulative_length_m: number;
  readonly relative_weight: number; readonly reason: 'receiver_hit' | 'stop_hit' | 'domain_exit' | 'interaction_cap' | 'distance_cap' | 'branch_cap' | 'record_cap';
}
export interface RefractiveTraceResult extends Omit<RefractiveValidationReply, 'message_type'> {
  readonly message_type: 'refractive_trace_result'; readonly status: 'complete' | 'incomplete';
  readonly branches: readonly RefractiveBranch[]; readonly segments: readonly RefractiveSegment[]; readonly events: readonly RefractiveEvent[]; readonly terminals: readonly RefractiveTerminal[];
  readonly ledger: Readonly<{ input_weight: number; detected_weight: number; absorbed_weight: number; escaped_weight: number; truncated_weight: number; signed_residual: number }>;
  readonly diagnostics: Readonly<Record<string, number | string>>;
}
export interface RefractiveRoutingAPI { validate(request: RefractiveValidationRequest): Promise<unknown>; trace(request: RefractiveTraceRequest): Promise<ArrayBuffer> }
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/, sha = /^[0-9a-f]{64}$/, id = /^[A-Za-z][A-Za-z0-9_-]{0,31}$/, branchId = /^r0(?:\.[TR]){0,31}$/;
const categories = ['detected', 'absorbed', 'escaped', 'resource_truncated'] as const;
const validationKeys = ['protocol_version','message_type','model_contract','request_id','scene_sha256','scene','weight_model','media','body_faces','legacy_surface_frames','limits'];
const commonBounds = ['t_parameter_interval_m','position_intervals_m','local_uv_intervals_m','incident_direction_intervals','outgoing_direction_intervals','cumulative_length_interval_m','plane_residual_m'];
const eventKeys = ['id','segment_id','branch_id','target','classification','position_m','local_uv_m','incident_direction','incident_medium_id','incident_refractive_index','incoming_weight','outgoing','segment_length_m','cumulative_length_m','numerical_bounds'];
function fail(message: string): never { throw new Error(`W3 protocol: ${message}`); }
function obj(value: unknown, name: string): Record<string, unknown> { if (!value || typeof value !== 'object' || Array.isArray(value)) fail(`${name}: expected object`); return value as Record<string, unknown>; }
function keys(value: unknown, expected: readonly string[], name: string): void { const actual = Object.keys(obj(value,name)); if (actual.length !== expected.length || actual.some(k=>!expected.includes(k))) fail(`${name}: incorrect closed keys`); }
function finite(value: unknown, name: string, min = -Infinity, max = Infinity): number { if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) fail(`${name}: unsupported finite number`); return value; }
function array(value: unknown, name: string, max: number): unknown[] { if (!Array.isArray(value) || value.length > max) fail(`${name}: count/array`); return value; }
function vector(value: unknown, name: string, size = 3): readonly number[] { const v = array(value,name,size); if (v.length !== size) fail(`${name}: vector length`); return v.map(x=>finite(x,name)); }
function unit(value: unknown, name: string, tolerance = 128 * Number.EPSILON): void { if (Math.abs(Math.hypot(...vector(value,name))-1)>tolerance) fail(`${name}: nonunit vector`); }
function text(value: unknown, name: string, pattern: RegExp): string { if (typeof value !== 'string' || !pattern.test(value)) fail(`${name}: identity`); return value; }
function same(a: unknown,b: unknown,name: string): void { if (!routingStructuralEqual(a,b)) fail(`${name}: identity mismatch`); }
function near(a:number,b:number): boolean { return Math.abs(a-b)<=2e-13*Math.max(1,Math.abs(a),Math.abs(b)); }
function enclosure(value: unknown, actual: number, name: string, maxWidth = Infinity): void { const v=vector(value,name,2); if(v[0]>actual||v[1]<actual||v[0]>v[1]||v[1]-v[0]>maxWidth)fail(`${name}: enclosure`); }
function vectorBounds(value: unknown, actual: readonly number[], name: string, maxWidth=Infinity): void { const v=array(value,name,actual.length); if(v.length!==actual.length)fail(`${name}: enclosure count`); v.forEach((x,k)=>enclosure(x,actual[k],name,maxWidth)); }
function freeze<T>(value:T):T { if(value&&typeof value==='object'&&!Object.isFrozen(value)){Object.values(value).forEach(freeze);Object.freeze(value);}return value; }
export function freezeRefractiveDraft(value:RefractiveScene):RefractiveScene{return freeze(structuredClone(value));}
export function assertRefractiveScene(value:unknown):asserts value is RefractiveScene {
  keys(value,['schema_version','model_contract','source','exterior_medium','bodies','elements'],'scene'); const s=value as RefractiveScene;
  if(s.schema_version!==1||s.model_contract!==W3_MODEL)fail('scene model/version');
  // Reuse the unchanged public W2 DTO admission for the exact exterior fields, not optical execution.
  assertGeometricScene({schema_version:1,model_contract:W2_MODEL,source:s.source,elements:s.elements});
  keys(s.exterior_medium,['id','refractive_index'],'exterior medium');if(s.exterior_medium.id!=='exterior')fail('exterior identity'); finite(s.exterior_medium.refractive_index,'exterior index',1,2.5);
  const bodies=array(s.bodies,'bodies',1), ids=new Set(['source',...s.elements.map(e=>e.id)]);let faces=0;
  for(const item of bodies){ keys(item,['id','kind','pose','shape','interior_medium'],'body'); const b=item as RefractiveBody;text(b.id,'body ID',id);if(ids.has(b.id))fail('duplicate body ID');ids.add(b.id);
    keys(b.pose,['position_m','rotation_xyz_rad'],'body pose');vector(b.pose.position_m,'body position').forEach(v=>finite(v,'body position',-10,10));vector(b.pose.rotation_xyz_rad,'body rotation').forEach(v=>finite(v,'body rotation',-Math.PI,Math.PI));
    const names=b.kind==='rectangular_block'?['width_x_m','height_y_m','depth_z_m']:b.kind==='right_triangular_prism'?['leg_x_m','leg_z_m','height_y_m']:fail('body kind');
    keys(b.shape,names,'body dimensions');Object.values(b.shape).forEach(v=>finite(v,'body dimension',1e-4,.25));faces+=b.kind==='rectangular_block'?6:5;
    keys(b.interior_medium,['id','refractive_index'],'interior medium');if(b.interior_medium.id!==`body:${b.id}`)fail('interior identity');finite(b.interior_medium.refractive_index,'interior index',1,2.5);
  }if(faces+s.elements.length>16)fail('total finite face cap');
}
export function freezeRefractiveScene(value:RefractiveScene):RefractiveScene{assertRefractiveScene(value);return freezeRefractiveDraft(value);}
function metadata(value:unknown,submitted:RefractiveValidationRequest,type:string):RefractiveValidationReply {
  const r=obj(value,'reply');text(submitted.request_id,'request UUID',uuid);assertRefractiveScene(submitted.scene);
  if(r.protocol_version!==1||r.message_type!==type||r.model_contract!==W3_MODEL||r.weight_model!==W3_WEIGHT_MODEL||r.request_id!==submitted.request_id)fail('reply identity');
  text(r.scene_sha256,'scene digest',sha);assertRefractiveScene(r.scene);same(r.scene,submitted.scene,'scene echo');const reply=r as unknown as RefractiveValidationReply;
  same(reply.limits,reply.scene.bodies.length?W3_LIMITS:W3_NO_BODY_LIMITS,'active limits');
  same(reply.media,[reply.scene.exterior_medium,...reply.scene.bodies.map(b=>b.interior_medium)],'complete medium registry');
  const expected=new Map(reply.scene.bodies.flatMap(b=>(b.kind==='rectangular_block'?['x_min','x_max','y_min','y_max','z_min','z_max']:['x_min','z_min','hypotenuse','y_min','y_max']).map(face=>[`${b.id}/${face}`,b]))),seen=new Set<string>();
  for(const item of array(reply.body_faces,'body faces',6)){keys(item,['body_id','face_id','vertices_m','plane_covector','outward_normal','local_origin_m','local_basis','numerical_bounds'],'body face');const f=item as RefractiveFace,key=`${f.body_id}/${f.face_id}`;const body=expected.get(key);if(!body||seen.has(key))fail('body face identity');seen.add(key);
    const n=body.kind==='right_triangular_prism'&&['y_min','y_max'].includes(f.face_id)?3:4;if(array(f.vertices_m,'face vertices',4).length!==n)fail('finite polygon vertices');f.vertices_m.forEach(v=>vector(v,'face vertex'));vector(f.plane_covector,'face covector');if(Math.hypot(...f.plane_covector)===0)fail('zero covector');unit(f.outward_normal,'outward normal');vector(f.local_origin_m,'face anchor');
    keys(f.local_basis,['u','v'],'local basis');unit(f.local_basis.u,'basis u');unit(f.local_basis.v,'basis v');
    keys(f.numerical_bounds,['vertex_intervals_m','covector_intervals','normal_intervals','basis_u_intervals','basis_v_intervals'],'face bounds');if(array(f.numerical_bounds.vertex_intervals_m,'vertex bounds',4).length!==n)fail('vertex bound count');
    f.vertices_m.forEach((v,k)=>vectorBounds(f.numerical_bounds.vertex_intervals_m[k],v,'vertex bounds'));vectorBounds(f.numerical_bounds.covector_intervals,f.plane_covector,'covector bounds');vectorBounds(f.numerical_bounds.normal_intervals,f.outward_normal,'normal bounds');vectorBounds(f.numerical_bounds.basis_u_intervals,f.local_basis.u,'u bounds');vectorBounds(f.numerical_bounds.basis_v_intervals,f.local_basis.v,'v bounds');
  }if(seen.size!==expected.size)fail('missing body face');same([...seen],[...expected.keys()],'canonical body face order');
  const frameIds=new Set(reply.scene.elements.map(e=>e.id));if(array(reply.legacy_surface_frames,'legacy frames',16).length!==frameIds.size)fail('legacy frame count');
  for(const f of reply.legacy_surface_frames){keys(f,['element_id','u','v','n'],'legacy frame');if(!frameIds.delete(f.element_id))fail('legacy frame identity');[f.u,f.v,f.n].forEach(v=>unit(v,'legacy frame',64*Number.EPSILON));
    const dot=(a:RoutingVector,b:RoutingVector)=>a.reduce((s,v,k)=>s+v*b[k],0);if([dot(f.u,f.v),dot(f.u,f.n),dot(f.v,f.n)].some(v=>Math.abs(v)>64*Number.EPSILON))fail('legacy frame orthogonality');const cross=[f.u[1]*f.v[2]-f.u[2]*f.v[1],f.u[2]*f.v[0]-f.u[0]*f.v[2],f.u[0]*f.v[1]-f.u[1]*f.v[0]];if(cross.some((v,k)=>Math.abs(v-f.n[k])>64*Number.EPSILON))fail('legacy frame handedness');}
  return reply;
}
export function validateRefractiveValidation(value:unknown,request:RefractiveValidationRequest):RefractiveValidationReply {keys(value,validationKeys,'validation reply');return freeze(metadata(value,request,'refractive_scene_validation'));}
const charges=new WeakMap<RefractiveTraceResult,RoutingResourceBreakdown>();
export function decodeRefractiveTrace(bytes:ArrayBuffer,request:RefractiveTraceRequest,validated?:RefractiveValidationReply):RefractiveTraceResult {
  if(!(bytes instanceof ArrayBuffer)||bytes.byteLength<2||bytes.byteLength>W3_RESPONSE_CAP)fail('response byte cap/length');let value:unknown;try{value=parseRoutingJSON(new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(bytes));}catch(error){fail(`invalid JSON/UTF-8: ${String(error)}`);}
  keys(value,[...validationKeys,'status','branches','segments','events','terminals','ledger','diagnostics'],'trace reply');const r=metadata(value,request,'refractive_trace_result') as unknown as RefractiveTraceResult;
  text(request.scene_sha256,'submitted digest',sha);same(r.scene_sha256,request.scene_sha256,'trace digest');
  if(validated)for(const k of ['scene_sha256','scene','media','body_faces','legacy_surface_frames','limits','weight_model'] as const)same(r[k],validated[k],`validated ${k}`);
  if(!['complete','incomplete'].includes(r.status))fail('trace status'); const bodyPresent=!!r.scene.bodies.length, limits=r.limits;
  array(r.branches,'branches',limits.max_branches);array(r.segments,'segments',limits.max_segments);array(r.events,'events',limits.max_events);array(r.terminals,'terminals',limits.max_branches);
  if(!r.branches.length||r.segments.length+r.events.length>limits.max_records)fail('root/combined cap');
  const media=new Map(r.media.map(m=>[m.id,m.refractive_index])),branches=new Map<string,RefractiveBranch>(),segments=new Map<string,RefractiveSegment>(),events=new Map<string,RefractiveEvent>(),terminals=new Map<string,RefractiveTerminal>();
  const medium=(mid:unknown,index:unknown)=>{if(typeof mid!=='string'||media.get(mid)!==index)fail('medium/index graph');};
  for(const b of r.branches){keys(b,['id','parent_id','parent_event_id','origin_m','initial_direction','initial_medium_id','initial_refractive_index','relative_weight','start_cumulative_m','start_interaction_count','outcome'],'branch');text(b.id,'branch',branchId);if(branches.has(b.id))fail('duplicate branch');vector(b.origin_m,'branch origin');unit(b.initial_direction,'branch direction');medium(b.initial_medium_id,b.initial_refractive_index);finite(b.relative_weight,'branch weight',Number.MIN_VALUE,1);finite(b.start_cumulative_m,'start distance',0,10);if(!Number.isInteger(b.start_interaction_count)||b.start_interaction_count<0||b.start_interaction_count>32)fail('interaction count');if(![...categories,'split'].includes(b.outcome))fail('branch outcome');
    if(b.id==='r0'){if(branches.size||b.parent_id!==null||b.parent_event_id!==null||b.relative_weight!==1||b.start_cumulative_m!==0||b.start_interaction_count!==0)fail('root identity');same(b.origin_m,r.scene.source.origin_m,'source origin');same(b.initial_direction,r.scene.source.direction,'source direction');medium(b.initial_medium_id,r.scene.exterior_medium.refractive_index);if(b.initial_medium_id!=='exterior')fail('source medium');}
    else if(!b.parent_id||!branches.has(b.parent_id)||!b.parent_event_id||![`${b.parent_id}.T`,`${b.parent_id}.R`].includes(b.id))fail('branch parent/order');branches.set(b.id,b);
  }
  for(const [i,s]of r.segments.entries()){keys(s,['id','branch_id','start_m','end_m','direction','medium_id','refractive_index','relative_weight','length_m','cumulative_end_m','event_id'],'segment');if(s.id!==`s${String(i+(bodyPresent?1:0)).padStart(4,'0')}`||segments.has(s.id)||!branches.has(s.branch_id))fail('segment identity');vector(s.start_m,'start');vector(s.end_m,'end');unit(s.direction,'segment direction');medium(s.medium_id,s.refractive_index);finite(s.relative_weight,'segment weight',Number.MIN_VALUE,1);finite(s.length_m,'segment length',Number.MIN_VALUE,10);finite(s.cumulative_end_m,'cumulative distance',0,10+2e-12);if(!near(Math.hypot(...s.end_m.map((v,k)=>v-s.start_m[k])),s.length_m))fail('segment geometric length');
    if(s.end_m.some((v,k)=>!near(v-s.start_m[k],s.direction[k]*s.length_m/Math.hypot(...s.direction))))fail('segment endpoint/direction consistency');for(const p of [s.start_m,s.end_m])if(Math.hypot(...p.map((v,k)=>v-r.scene.source.origin_m[k]))>1+2e-12)fail('segment domain bound');segments.set(s.id,s);}
  const faces=new Map(r.body_faces.map(f=>[`${f.body_id}/${f.face_id}`,f])),elements=new Map(r.scene.elements.map(e=>[e.id,e]));
  for(const [i,e]of r.events.entries()){
    const dielectric=e.target?.kind==='body_face';keys(e,[...eventKeys,...(dielectric?['outward_normal','local_basis','incident_angle_rad','outgoing_angle_rad']:[])],'event');if(e.id!==`${bodyPresent?'e':'h'}${String(i+(bodyPresent?1:0)).padStart(4,'0')}`||events.has(e.id))fail('event identity');const s=segments.get(e.segment_id);if(!s||s.event_id!==e.id||s.branch_id!==e.branch_id)fail('event segment');same(e.position_m,s.end_m,'event position');same(e.incident_direction,s.direction,'event incident direction');if(e.segment_length_m!==s.length_m||e.cumulative_length_m!==s.cumulative_end_m||e.incoming_weight!==s.relative_weight)fail('event distance/weight');medium(e.incident_medium_id,e.incident_refractive_index);if(e.incident_medium_id!==s.medium_id||e.incident_refractive_index!==s.refractive_index)fail('incident medium');vector(e.local_uv_m,'local UV',2);
    const bound=e.numerical_bounds;keys(bound,[...commonBounds,...(dielectric?['snell_discriminant_interval','incident_side_interval','outgoing_side_interval','body_halfspace_intervals_m']:[])],'event bounds');enclosure(bound.t_parameter_interval_m,(s.end_m.findIndex((v,k)=>v!==s.start_m[k])<0?0:s.length_m/Math.hypot(...s.direction)),'t interval');if(bound.t_parameter_interval_m[0]<=0)fail('event is not certified strictly forward');vectorBounds(bound.position_intervals_m,e.position_m,'position bounds',bodyPresent?1e-8:Infinity);vectorBounds(bound.local_uv_intervals_m,e.local_uv_m,'UV bounds');vectorBounds(bound.incident_direction_intervals,e.incident_direction,'incident bounds',bodyPresent?1e-8:Infinity);enclosure(bound.cumulative_length_interval_m,e.cumulative_length_m,'distance interval');finite(bound.plane_residual_m,'signed plane residual');
    const outgoing=array(e.outgoing,'outgoing',2);if(array(bound.outgoing_direction_intervals,'outgoing bounds',2).length!==outgoing.length)fail('outgoing bound count');
    e.outgoing.forEach((o,k)=>{keys(o,['branch_id','direction','medium_id','refractive_index','relative_weight'],'outgoing');text(o.branch_id,'outgoing branch',branchId);unit(o.direction,'outgoing direction');medium(o.medium_id,o.refractive_index);finite(o.relative_weight,'outgoing weight',Number.MIN_VALUE,1);const b=bound.outgoing_direction_intervals[k];keys(b,['branch_id','direction_intervals'],'outgoing bounds');if(b.branch_id!==o.branch_id)fail('outgoing bounds identity');vectorBounds(b.direction_intervals,o.direction,'outgoing enclosure',bodyPresent?1e-8:Infinity);});
    if(dielectric){keys(e.target,['kind','body_id','face_id'],'body target');const f=faces.get(`${e.target.body_id}/${e.target.face_id}`);if(!f)fail('foreign body face');same(e.outward_normal,f.outward_normal,'returned outward normal');same(e.local_basis,f.local_basis,'returned local basis');finite(e.incident_angle_rad,'incidence angle',0,Math.PI/2+1e-14);finite(e.outgoing_angle_rad,'outgoing angle',0,Math.PI/2+1e-14);if(!['enter_refraction','exit_refraction','total_internal_reflection'].includes(e.classification)||outgoing.length!==1)fail('dielectric cardinality/class');const o=e.outgoing[0],bodyMedium=`body:${e.target.body_id}`;if(o.branch_id!==e.branch_id||o.relative_weight!==e.incoming_weight)fail('dielectric branch/weight');
      const ki=vector(bound.snell_discriminant_interval,'K interval',2),inc=vector(bound.incident_side_interval,'incident side',2),out=vector(bound.outgoing_side_interval,'outgoing side',2);if(ki[0]>ki[1]||inc[0]>inc[1]||out[0]>out[1])fail('ordered intervals');
      if(e.classification==='enter_refraction'){if(e.incident_medium_id!=='exterior'||o.medium_id!==bodyMedium||ki[0]<=0||inc[1]>=0||out[1]>=0)fail('enter medium/side/discriminant');}
      else if(e.classification==='exit_refraction'){if(e.incident_medium_id!==bodyMedium||o.medium_id!=='exterior'||ki[0]<=0||inc[0]<=0||out[0]<=0)fail('exit medium/side/discriminant');}
      else if(o.medium_id!==e.incident_medium_id||ki[1]>=0||!(e.incident_medium_id===bodyMedium?inc[0]>0&&out[1]<0:e.incident_medium_id==='exterior'&&inc[1]<0&&out[0]>0))fail('TIR must retain incident medium/certified incident-side reflection');
      if(array(bound.body_halfspace_intervals_m,'body halfspaces',6).length!==r.body_faces.length)fail('halfspace count');bound.body_halfspace_intervals_m!.forEach((x,k)=>{const v=vector(x,'halfspace interval',2);if(v[0]>v[1])fail('body halfspace order');if(r.body_faces[k]===f){if(v[0]>0||v[1]<0)fail('target face boundary enclosure');}else if(v[1]>=0)fail('non-target face is not certified strictly inside');});
    }else{keys(e.target,['kind','element_id'],'element target');if(e.target.kind!=='element')fail('unsupported event target kind');const item=elements.get(e.target.element_id),classification={mirror:'mirror_reflection',ideal_splitter_50_50:'ideal_split',beam_stop:'stop_hit',receiver:'receiver_hit'}[item?.kind??'receiver'];if(!item||e.classification!==classification||e.incident_medium_id!=='exterior'||e.outgoing.some(o=>o.medium_id!=='exterior'))fail('legacy target/class/medium');if(item.kind==='mirror'&&(outgoing.length!==1||e.outgoing[0].branch_id!==e.branch_id||e.outgoing[0].relative_weight!==e.incoming_weight))fail('mirror outgoing');if(['receiver','beam_stop'].includes(item.kind)&&outgoing.length)fail('terminal outgoing');if(item.kind==='ideal_splitter_50_50'&&(outgoing.length!==0&&outgoing.length!==2||outgoing.length===2&&e.outgoing.some((o,k)=>o.branch_id!==`${e.branch_id}.${k?'R':'T'}`||o.relative_weight!==e.incoming_weight*.5)))fail('split pair');}
    events.set(e.id,e);
  }
  for(const s of r.segments)if(s.event_id!==null&&!events.has(s.event_id))fail('segment missing event');
  for(const t of r.terminals){keys(t,['branch_id','category','element_id','event_id','position_m','medium_id','refractive_index','cumulative_length_m','relative_weight','reason'],'terminal');const b=branches.get(t.branch_id);if(!b||b.outcome!==t.category||terminals.has(t.branch_id)||!categories.includes(t.category)||t.relative_weight!==b.relative_weight)fail('terminal branch/category/weight');vector(t.position_m,'terminal position');medium(t.medium_id,t.refractive_index);finite(t.cumulative_length_m,'terminal distance',0,10+2e-12);const e=t.event_id===null?null:events.get(t.event_id);if(t.event_id!==null&&!e)fail('terminal event');if(e){same(t.position_m,e.position_m,'terminal event position');if(t.cumulative_length_m!==e.cumulative_length_m)fail('terminal event distance');if(t.element_id!==(e.target.kind==='element'?e.target.element_id:null))fail('terminal target');}else if(t.element_id!==null)fail('terminal element without event');
    if(t.category==='detected'||t.category==='absorbed'){if(!e||e.classification!==(t.category==='detected'?'receiver_hit':'stop_hit')||t.reason!==e.classification)fail('fabricated detected/absorbed');}else if(t.category==='escaped'){if(e||t.reason!=='domain_exit'||!near(Math.hypot(...t.position_m.map((v,k)=>v-r.scene.source.origin_m[k])),1))fail('escape identity/domain');}else if(!['interaction_cap','distance_cap','branch_cap','record_cap'].includes(t.reason))fail('truncation reason');terminals.set(t.branch_id,t);
  }
  for(const b of r.branches){let point=b.origin_m,direction=b.initial_direction,mid=b.initial_medium_id,index=b.initial_refractive_index,length=b.start_cumulative_m,count=b.start_interaction_count;const path=r.segments.filter(s=>s.branch_id===b.id);
    for(const [k,s]of path.entries()){same(s.start_m,point,'path start');same(s.direction,direction,'path direction');if(s.medium_id!==mid||s.refractive_index!==index||s.relative_weight!==b.relative_weight||!near(length+s.length_m,s.cumulative_end_m))fail('path medium/weight/length');point=s.end_m;length=s.cumulative_end_m;if(s.event_id!==null){const e=events.get(s.event_id)!;if(++count>32)fail('interaction reset');if(['enter_refraction','exit_refraction','total_internal_reflection','mirror_reflection'].includes(e.classification)){const o=e.outgoing[0];direction=o.direction;mid=o.medium_id;index=o.refractive_index;}else if(k!==path.length-1)fail('path continues after terminal/split');}else if(k!==path.length-1)fail('path after endpoint');}
    if(b.parent_id){const e=events.get(b.parent_event_id!),parent=branches.get(b.parent_id),o=e?.outgoing.find(o=>o.branch_id===b.id);if(!e||!parent||parent.outcome!=='split'||e.classification!=='ideal_split'||!o)fail('child split graph');same(b.origin_m,e.position_m,'child origin');same(b.initial_direction,o.direction,'child direction');if(b.relative_weight!==o.relative_weight||b.initial_medium_id!==o.medium_id||b.initial_refractive_index!==o.refractive_index||b.start_cumulative_m!==e.cumulative_length_m||b.start_interaction_count!==parent.start_interaction_count+r.events.filter(x=>x.branch_id===parent.id).length)fail('child inherited state');}
    const t=terminals.get(b.id),last=path.at(-1)?.event_id?events.get(path.at(-1)!.event_id!):null;if(b.outcome==='split'){if(t||last?.classification!=='ideal_split'||last.outgoing.length!==2||!branches.has(`${b.id}.T`)||!branches.has(`${b.id}.R`))fail('split leaves');}else{if(!t)fail('missing leaf');same(t.position_m,point,'terminal endpoint');if(!near(t.cumulative_length_m,length)||t.medium_id!==mid||t.refractive_index!==index)fail('terminal final medium/distance');if(t.reason==='interaction_cap'&&count!==32)fail('early interaction truncation');if(t.reason==='distance_cap'&&!near(length,10))fail('early distance truncation');if(t.category==='escaped'&&(!path.length||path.at(-1)!.event_id!==null))fail('escaped without endpoint');}
  }
  keys(r.ledger,['input_weight','detected_weight','absorbed_weight','escaped_weight','truncated_weight','signed_residual'],'ledger');const sums=categories.map(c=>r.terminals.filter(t=>t.category===c).reduce((s,t)=>s+t.relative_weight,0));if(r.ledger.input_weight!==1)fail('input weight');['detected_weight','absorbed_weight','escaped_weight','truncated_weight'].forEach((k,i)=>{if(finite((r.ledger as unknown as Record<string,number>)[k],k,0,1)!==sums[i])fail('leaf ledger');});const residual=1-sums.reduce((a,b)=>a+b,0);if(r.ledger.signed_residual!==residual||Math.abs(residual)>64*Number.EPSILON)fail('lost terminal weight');if((r.status==='incomplete')!==r.terminals.some(t=>t.category==='resource_truncated'))fail('status truncation');
  const diagnosticKeys=bodyPresent?['predicate_policy','max_direction_norm_residual','max_frame_residual','max_plane_residual_m','max_point_width_m','max_direction_width']:['predicate_policy','max_direction_norm_residual','max_frame_orthogonality_residual','max_plane_residual_m','max_point_error_bound_m'];keys(r.diagnostics,diagnosticKeys,'diagnostics');if(r.diagnostics.predicate_policy!==(bodyPresent?'binary64_closed_body_outward_v1':'binary64_outward_intervals_v1'))fail('predicate policy');Object.entries(r.diagnostics).filter(([k])=>k!=='predicate_policy').forEach(([k,v])=>finite(v,k,0));
  if(!bodyPresent){const oldScene={schema_version:1 as const,model_contract:W2_MODEL,source:r.scene.source,elements:r.scene.elements};const old={protocol_version:1,message_type:'trace_result',model_contract:W2_MODEL,request_id:r.request_id,scene_sha256:r.scene_sha256,scene:oldScene,surface_frames:r.legacy_surface_frames,limits:W2_LIMITS,status:r.status,
    branches:r.branches.map(({initial_medium_id:_a,initial_refractive_index:_b,parent_event_id,...rest})=>({...rest,parent_hit_id:parent_event_id})),segments:r.segments.map(({medium_id:_a,refractive_index:_b,event_id,...rest})=>({...rest,hit_id:event_id})),
    hits:r.events.map(({target,classification:_a,incident_medium_id:_b,incident_refractive_index:_c,numerical_bounds,outgoing,...rest})=>({...rest,element_id:target.kind==='element'?target.element_id:fail('empty-body face'),outgoing:outgoing.map(({medium_id:_d,refractive_index:_e,...o})=>o),numerical_bounds:{t_parameter_interval_m:numerical_bounds.t_parameter_interval_m,position_intervals_m:numerical_bounds.position_intervals_m,local_uv_intervals_m:numerical_bounds.local_uv_intervals_m,plane_residual_m:numerical_bounds.plane_residual_m}})),
    terminals:r.terminals.map(({medium_id:_a,refractive_index:_b,event_id,...rest})=>({...rest,hit_id:event_id})),ledger:r.ledger,diagnostics:r.diagnostics};decodeGeometricTrace(new TextEncoder().encode(stringifyRoutingJSON(old)).buffer,{request_id:r.request_id,scene_sha256:r.scene_sha256,scene:oldScene});}
  finite(r.diagnostics.max_direction_norm_residual,'direction residual',0,128*Number.EPSILON);if(bodyPresent){finite(r.diagnostics.max_point_width_m,'point enclosure width',0,1e-8);finite(r.diagnostics.max_direction_width,'direction enclosure width',0,1e-8);}
  freeze(r);charges.set(r,charge(r,bytes.byteLength));return r;
}
/** Conservative app-owned metadata charges; not whole engine heap or GPU allocation. */
function charge(value:unknown,wireBytes:number):RoutingResourceBreakdown{let scalarBytes=0,stringBytes=0,containerReservationBytes=4096;const seen=new Set<object>();const visit=(v:unknown):void=>{if(typeof v==='number'||typeof v==='boolean'||v===null)scalarBytes+=8;else if(typeof v==='string')stringBytes+=v.length*2;else if(v&&typeof v==='object'&&!seen.has(v)){seen.add(v);if(Array.isArray(v)){containerReservationBytes+=64+v.length*16;v.forEach(visit);}else{const entries=Object.entries(v);containerReservationBytes+=96+entries.length*24;entries.forEach(([key,x])=>{stringBytes+=key.length*2;visit(x);});}}};visit(value);return Object.freeze({wireBytes,scalarBytes,stringBytes,containerReservationBytes,retainedBytes:scalarBytes+stringBytes+containerReservationBytes,retainedRawBytes:0,retainedResponseTextBytes:0});}
export function refractiveResourceBreakdown(result:RefractiveTraceResult):RoutingResourceBreakdown{return charges.get(result)??charge(result,0);}
export function refractiveOwnedResults(results:readonly(RefractiveTraceResult|null)[]):number{return [...new Set(results.filter((r):r is RefractiveTraceResult=>!!r))].reduce((n,r)=>n+refractiveResourceBreakdown(r).retainedBytes,0);}
export function createRefractiveRoutingFetchAPI(fetchImpl:typeof fetch=globalThis.fetch.bind(globalThis)):RefractiveRoutingAPI {
  const post=async(endpoint:'validate'|'trace',request:RefractiveValidationRequest):Promise<ArrayBuffer>=>{text(request.request_id,'request UUID',uuid);const body=stringifyRoutingJSON(request);if(new TextEncoder().encode(body).byteLength>W3_REQUEST_CAP)fail('request byte cap');const response=await fetchImpl(`/api/w3/${endpoint}`,{method:'POST',credentials:'same-origin',redirect:'error',headers:{'Content-Type':'application/json',Accept:'application/json'},body});if(!response.ok){let message=`HTTP ${response.status}`;try{const raw=parseRoutingJSON(new TextDecoder('utf-8',{fatal:true}).decode(await readBoundedResponse(response,W3_REQUEST_CAP)));keys(raw,['protocol_version','message_type','request_id','model_contract','error'],'error');const e=raw as Record<string,unknown>;if(e.protocol_version!==1||e.message_type!=='refractive_routing_error'||e.model_contract!==W3_MODEL||e.request_id!==request.request_id)fail('error identity');keys(e.error,['code','message'],'error detail');const detail=e.error as Record<string,unknown>;if(typeof detail.code!=='string'||typeof detail.message!=='string'||detail.message.length>300)fail('error detail');message+=`: ${detail.code}: ${detail.message}`;}catch{/* Actual HTTP status remains visible for malformed error envelopes. */}throw new Error(message);}if(response.headers.get('content-type')?.split(';',1)[0].trim()!=='application/json'){await response.body?.cancel('W3 content type');fail('HTTP content type');}return readBoundedResponse(response,W3_RESPONSE_CAP);};
  return{async validate(request){return parseRoutingJSON(new TextDecoder('utf-8',{fatal:true}).decode(await post('validate',request)));},trace(request){return post('trace',request);}};
}

const receiver=(position:RoutingVector,y=0):RoutingElement=>({id:'D1',kind:'receiver',pose:{position_m:position,rotation_xyz_rad:[0,y,0]},aperture:{kind:'disk',radius_m:.01}});
const prism=(n:number):RefractiveBody=>({id:'B1',kind:'right_triangular_prism',pose:{position_m:[0,.08,0],rotation_xyz_rad:[0,0,0]},shape:{leg_x_m:.08,leg_z_m:.08,height_y_m:.04},interior_medium:{id:'body:B1',refractive_index:n}});
const preset=(source:RefractiveScene['source'],body:RefractiveBody,element:RoutingElement):RefractiveScene=>freezeRefractiveScene({schema_version:1,model_contract:W3_MODEL,source,exterior_medium:{id:'exterior',refractive_index:1},bodies:[body],elements:[element]});
const straight={id:'source' as const,origin_m:[.02,.08,-.04] as RoutingVector,direction:[0,0,1] as RoutingVector,relative_weight:1 as const};
/** Literal frozen APPARATUS_PRESETS.json inputs. Receiver positions never follow trace output. */
export const W3_PRESETS=Object.freeze({
  A:preset({id:'source',origin_m:[-.015,.08,-.04],direction:[.49999999999999994,0,.8660254037844387],relative_weight:1},{id:'B1',kind:'rectangular_block',pose:{position_m:[0,.08,.015],rotation_xyz_rad:[0,0,0]},shape:{width_x_m:.12,height_y_m:.08,depth_z_m:.03},interior_medium:{id:'body:B1',refractive_index:1.5}},receiver([.07066213671244954,.08,.12])),
  B:preset(straight,prism(1.2),receiver([0,.08,.12])),C:preset(straight,prism(1.5),receiver([-.04,.08,.06],Math.PI/2)),
});
