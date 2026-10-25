/** W3 presentation of authoritative returned polygons and paths; no optical solver. */
import * as THREE from 'three';
import { createGeometricRoutingApparatus, W2_WORLD_SCALE, type GeometricRoutingApparatus } from './geometric_routing_apparatus';
import { W2_MODEL, type RoutingVector } from './geometric_routing_contracts';
import { assertRefractiveScene, type RefractiveScene, type RefractiveValidationReply, type RefractiveTraceResult, type RefractiveEvent } from './refractive_routing_contracts';

const point=(v:RoutingVector)=>new THREE.Vector3(...v).multiplyScalar(W2_WORLD_SCALE);
interface Owner { group:THREE.Group; geometries:Set<THREE.BufferGeometry>; materials:Set<THREE.Material>; disposed:boolean }
const owner=():Owner=>({group:new THREE.Group(),geometries:new Set(),materials:new Set(),disposed:false});
function geometry<T extends THREE.BufferGeometry>(o:Owner,g:T):T{o.geometries.add(g);return g;}
function material<T extends THREE.Material>(o:Owner,m:T):T{o.materials.add(m);return m;}
function bytes(o:Owner):number{const buffers=new Set<ArrayBufferLike>();for(const g of o.geometries){if(g.index)buffers.add(g.index.array.buffer);for(const a of Object.values(g.attributes))buffers.add(a instanceof THREE.InterleavedBufferAttribute?a.data.array.buffer:a.array.buffer);}let nodes=0;o.group.traverse(()=>nodes++);return [...buffers].reduce((n,b)=>n+b.byteLength,0)+nodes*384+o.materials.size*256;}
function dispose(o:Owner):void{if(o.disposed)return;o.disposed=true;o.group.removeFromParent();o.group.clear();o.geometries.forEach(g=>g.dispose());o.materials.forEach(m=>m.dispose());o.geometries.clear();o.materials.clear();}
function segment(o:Owner,from:RoutingVector,to:RoutingVector,color:string,radius=.009):THREE.Mesh{
  const a=point(from),b=point(to),delta=b.clone().sub(a),length=delta.length();
  const g=geometry(o,new THREE.CylinderGeometry(radius,radius,length,8)),m=material(o,new THREE.MeshBasicMaterial({color,toneMapped:false}));
  const mesh=new THREE.Mesh(g,m);mesh.position.copy(a).add(b).multiplyScalar(.5);if(length)mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),delta.multiplyScalar(1/length));mesh.renderOrder=4;o.group.add(mesh);return mesh;
}
export interface RefractiveRoutingApparatus {
  readonly group:THREE.Group;readonly ownedBytes:number;
  select(id:string):void;setDisplay(group:THREE.Group|null):void;setOpacity(value:number):void;
  selectFace(bodyId:string|null,faceId:string|null):void;
  setLabelsVisible(value:boolean):void;updateLabels(camera:THREE.PerspectiveCamera,width:number,height:number):void;
  framingBounds(id?:string):THREE.Box3;snapshot():object;dispose():void;
}
export function createRefractiveRoutingApparatus(scene:RefractiveScene,validation:RefractiveValidationReply|null,options:{labelHost?:HTMLElement;onSelect?:(id:string)=>void}={}):RefractiveRoutingApparatus{
  assertRefractiveScene(scene);const o=owner();o.group.name='W3 mounted finite dielectric apparatus';o.group.userData.w3Apparatus=true;
  const base:GeometricRoutingApparatus=createGeometricRoutingApparatus({schema_version:1,model_contract:W2_MODEL,source:scene.source,elements:scene.elements},{frames:validation?.legacy_surface_frames,labelHost:options.labelHost,onSelect:options.onSelect});o.group.add(base.group);
  const glass=material(o,new THREE.MeshStandardMaterial({color:'#68d6d0',transparent:true,opacity:.18,roughness:.16,metalness:.05,side:THREE.DoubleSide,depthWrite:false}));
  const edgeMaterial=material(o,new THREE.LineBasicMaterial({color:'#76d6cc',transparent:true,opacity:.8}));
  const selectedFaceMaterial=material(o,new THREE.LineBasicMaterial({color:'#fff0a5',depthTest:false}));
  const bodyGroup=new THREE.Group();bodyGroup.name='Validated finite optical body faces';o.group.add(bodyGroup);const faces:Record<string,unknown>[]=[];
  const faceHighlights=new Map<string,THREE.LineSegments>();let selectedFace:string|null=null,selected='source',display:THREE.Group|null=null,labelsVisible=true;
  let label:HTMLButtonElement|null=null;let bodyAnchor:THREE.Vector3|null=null;
  try{
    for(const face of validation?.body_faces??[]){
      const positions:number[]=[],normals:number[]=[];for(const v of face.vertices_m){positions.push(...point(v).toArray());normals.push(...face.outward_normal);}
      const g=geometry(o,new THREE.BufferGeometry());g.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));g.setAttribute('normal',new THREE.Float32BufferAttribute(normals,3));g.setIndex(face.vertices_m.length===3?[0,1,2]:[0,1,2,0,2,3]);
      const mesh=new THREE.Mesh(g,glass);mesh.userData={w3BodyId:face.body_id,w3FaceId:face.face_id,opticalAuthority:false};mesh.renderOrder=1;bodyGroup.add(mesh);
      const edges=geometry(o,new THREE.BufferGeometry());const ends:number[]=[];face.vertices_m.forEach((v,k)=>ends.push(...point(v).toArray(),...point(face.vertices_m[(k+1)%face.vertices_m.length]).toArray()));edges.setAttribute('position',new THREE.Float32BufferAttribute(ends,3));bodyGroup.add(new THREE.LineSegments(edges,edgeMaterial));
      const highlight=new THREE.LineSegments(edges,selectedFaceMaterial);highlight.visible=false;highlight.renderOrder=9;bodyGroup.add(highlight);faceHighlights.set(`${face.body_id}/${face.face_id}`,highlight);
      faces.push({bodyId:face.body_id,faceId:face.face_id,vertices_m:face.vertices_m,outwardNormal:face.outward_normal,renderTriangles:face.vertices_m.length-2});
    }
    if(scene.bodies.length&&validation){const body=scene.bodies[0],bounds=new THREE.Box3().setFromObject(bodyGroup),center=bounds.getCenter(new THREE.Vector3()),size=bounds.getSize(new THREE.Vector3());bodyAnchor=new THREE.Vector3(center.x,bounds.max.y+.3,center.z);
      // The mount is decorative. Its geometry never enters any optical record.
      const floor=scene.source.origin_m[1]*10-.8,baseHeight=.08,postHeight=Math.max(.08,bounds.min.y-floor-baseHeight);
      const steel=material(o,new THREE.MeshStandardMaterial({color:'#7f959d',metalness:.75,roughness:.35})),dark=material(o,new THREE.MeshStandardMaterial({color:'#263940',metalness:.5,roughness:.4}));
      const mount=new THREE.Mesh(geometry(o,new THREE.BoxGeometry(Math.max(.5,size.x*.8),baseHeight,.42)),dark);mount.position.set(center.x,floor+baseHeight*.5,center.z);mount.userData.w3DecorativeMount=true;o.group.add(mount);
      const post=new THREE.Mesh(geometry(o,new THREE.CylinderGeometry(.045,.045,postHeight,12)),steel);post.position.set(center.x,floor+baseHeight+postHeight*.5,center.z);post.userData.w3DecorativeMount=true;o.group.add(post);
      if(options.labelHost){label=document.createElement('button');label.type='button';label.className='w2-label w3-body-label';label.dataset.testid=`w3-body-label-${body.id}`;label.textContent=`${body.id} / ${body.kind==='rectangular_block'?'PARALLEL SLAB':'RIGHT TRIANGULAR PRISM'}`;label.setAttribute('aria-label',`Select ${body.id} transparent body`);label.hidden=true;label.addEventListener('click',()=>options.onSelect?.(body.id));options.labelHost.append(label);}
    }
  }catch(error){base.dispose();label?.remove();dispose(o);throw error;}
  const own=bytes(o)+(label?1024:0);if(own+base.ownedBytes>768*1024){base.dispose();label?.remove();dispose(o);throw new Error('W3 apparatus exceeds its bounded display reservation.');}
  return{group:o.group,get ownedBytes(){return o.disposed?0:own+base.ownedBytes;},
    select(id){if(scene.bodies.some(b=>b.id===id)){selected=id;base.select('source');edgeMaterial.color.set('#b5fff0');label?.classList.add('selected');label?.setAttribute('aria-pressed','true');}else{base.select(id);selected=id;edgeMaterial.color.set('#76d6cc');label?.classList.remove('selected');label?.setAttribute('aria-pressed','false');}},
    setDisplay(group){if(o.disposed)throw new Error('W3 apparatus disposed');if(display===group)return;display?.removeFromParent();display=group;if(group)o.group.add(group);},
    setOpacity(value){if(!Number.isFinite(value)||value<.05||value>.5)throw new Error('Body opacity must be within [0.05,0.5]');glass.opacity=value;},
    selectFace(bodyId,faceId){const key=bodyId!==null&&faceId!==null?`${bodyId}/${faceId}`:null;if(key&&!faceHighlights.has(key))throw new Error('Unknown validated body face');selectedFace=key;faceHighlights.forEach((line,id)=>{line.visible=id===key;});},
    setLabelsVisible(value){labelsVisible=value;base.setLabelsVisible(value);if(!value&&label)label.hidden=true;},
    updateLabels(camera,width,height){base.updateLabels(camera,width,height);if(!label||!bodyAnchor)return;const projected=bodyAnchor.clone().project(camera);label.hidden=!labelsVisible||projected.z< -1||projected.z>1||width<80;if(!label.hidden){label.style.width='190px';label.style.left=`${Math.max(8,Math.min(width-198,(projected.x+1)*width/2-95))}px`;label.style.top=`${Math.max(8,Math.min(height-34,(1-projected.y)*height/2))}px`;}},
    framingBounds(id){if(id&&scene.bodies.some(b=>b.id===id))return new THREE.Box3().setFromObject(bodyGroup,true);const bounds=base.framingBounds(id);if(!id)bounds.union(new THREE.Box3().setFromObject(bodyGroup,true));return bounds;},
    snapshot(){return{selected,selectedFace,disposed:o.disposed,bodyFaces:faces,bodyVisible:faces.length>0,opacity:glass.opacity,ownedBytes:o.disposed?0:own+base.ownedBytes,worldMapping:'10 * SI metres, right-handed Y-up, isotropic',geometryAuthority:'validated returned polygons; triangulation is display only',opticalPicking:false,base:base.snapshot()};},
    dispose(){if(o.disposed)return;label?.remove();display?.removeFromParent();display=null;base.dispose();dispose(o);},
  };
}
export interface RefractiveRoutingDisplay {
  readonly group:THREE.Group;readonly result:RefractiveTraceResult;readonly ownedBytes:number;
  selectEvent(id:string|null):void;setAnnotations(normals:boolean,angles:boolean):void;updateLabels(camera:THREE.PerspectiveCamera,width:number,height:number):void;
  framingBounds():THREE.Box3;snapshot():object;dispose():void;
}
export function prepareRefractiveRoutingDisplay(result:RefractiveTraceResult,options:{labelHost?:HTMLElement}={}):RefractiveRoutingDisplay{
  const o=owner();o.group.name='W3 returned medium-aware calculated paths';const markers=new Map<string,THREE.Mesh>();const normalGroup=new THREE.Group();o.group.add(normalGroup);
  let selected:RefractiveEvent|null=null,showNormals=true,showAngles=true;let label:HTMLDivElement|null=null;
  const normalGeometry=geometry(o,new THREE.BufferGeometry());normalGeometry.setAttribute('position',new THREE.Float32BufferAttribute(new Float32Array(6),3));
  const normalLine=new THREE.Line(normalGeometry,material(o,new THREE.LineBasicMaterial({color:'#d7e5eb',depthTest:false})));normalLine.renderOrder=8;normalLine.visible=false;normalGroup.add(normalLine);
  try{
    for(const s of result.segments){const route=segment(o,s.start_m,s.end_m,s.medium_id==='exterior'?'#eab35c':'#57e3c7',.011);route.userData={w3SegmentId:s.id,w3MediumId:s.medium_id,w3BranchId:s.branch_id};}
    const sphere=geometry(o,new THREE.SphereGeometry(.028,10,6)),mat=material(o,new THREE.MeshBasicMaterial({color:'#d9fff4',toneMapped:false}));
    for(const e of result.events){const mesh=new THREE.Mesh(sphere,mat);mesh.position.copy(point(e.position_m));mesh.userData={w3EventId:e.id,w3Classification:e.classification};mesh.renderOrder=5;o.group.add(mesh);markers.set(e.id,mesh);}
    if(options.labelHost){label=document.createElement('div');label.className='w2-label w3-event-label';label.dataset.testid='w3-scene-event';label.hidden=true;options.labelHost.append(label);}
  }catch(error){label?.remove();dispose(o);throw error;}
  const redraw=()=>{normalLine.visible=!!selected?.outward_normal&&showNormals;if(!selected?.outward_normal)return;if(showNormals){const start=point(selected.position_m),end=start.clone().addScaledVector(new THREE.Vector3(...selected.outward_normal),.3);const values=normalGeometry.getAttribute('position') as THREE.BufferAttribute;values.setXYZ(0,start.x,start.y,start.z);values.setXYZ(1,end.x,end.y,end.z);values.needsUpdate=true;normalGeometry.computeBoundingSphere();}
    if(label){const type=selected.classification==='total_internal_reflection'?'TIR':'Refraction';label.textContent=`${selected.id} / ${type} · θ in ${(selected.incident_angle_rad!*180/Math.PI).toPrecision(7)}° · ${selected.classification==='total_internal_reflection'?'reflected':'refracted'} ${(selected.outgoing_angle_rad!*180/Math.PI).toPrecision(7)}°`;label.hidden=!showAngles;}};
  // Repeated passive annotation changes reuse/dispose their owned primitive immediately.
  const initial=bytes(o);return{group:o.group,result,get ownedBytes(){return o.disposed?0:bytes(o)+(label?1024:0);},
    selectEvent(id){const next=id===null?null:result.events.find(e=>e.id===id);if(id!==null&&!next)throw new Error('Unknown current W3 event');selected=next??null;markers.forEach((m,key)=>m.scale.setScalar(key===id?1.7:1));if(label)label.hidden=true;redraw();},
    setAnnotations(normals,angles){showNormals=normals;showAngles=angles;redraw();},
    updateLabels(camera,width,height){if(!label||!selected?.outward_normal||!showAngles)return;const p=point(selected.position_m).project(camera);label.hidden=p.z< -1||p.z>1;if(!label.hidden){label.style.maxWidth=`${Math.max(100,width-24)}px`;label.style.left=`${Math.max(8,Math.min(width-285,(p.x+1)*width/2+14))}px`;label.style.top=`${Math.max(8,Math.min(height-35,(1-p.y)*height/2-35))}px`;}},
    framingBounds(){return new THREE.Box3().setFromObject(o.group,true);},
    snapshot(){return{requestId:result.request_id,model:result.model_contract,sceneSha256:result.scene_sha256,selectedEvent:selected?.id??null,showNormals,showAngles,segmentCount:result.segments.length,eventCount:result.events.length,ownedBytes:o.disposed?0:bytes(o)+(label?1024:0),initialOwnedBytes:initial,endpoints:result.segments.map(s=>({id:s.id,start_m:s.start_m,end_m:s.end_m,medium_id:s.medium_id})),thickness:'visibility aid, not beam width or optical power'};},
    dispose(){label?.remove();dispose(o);},
  };
}
