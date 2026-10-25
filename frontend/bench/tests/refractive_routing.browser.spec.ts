/** Genuine production-browser W3 checks. Controls and test-owned clones are labelled. */
import { test, expect, chromium, type Page, type TestInfo, type Locator } from '@playwright/test';
import { createHash, randomUUID } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { createW2ResponseCapture } from './support/w2_response_capture';

const root = resolve('../..');
const evidence = resolve(root, process.env.W3_EVIDENCE_DIR ?? 'runs/w3_refractive_routing_implementation_01/browser');
const snapshot = (page: Page): Promise<any> => page.evaluate(() => window.__benchDebug.snapshot());
const routing = async (page: Page): Promise<any> => (await snapshot(page)).refractiveRouting;
const science = (path: string) => /\/api\/(?:v1|v2b|v2d|v2g|w1)\/(?:simulate|sweep)$/.test(path)
  || path === '/api/research/r03-fig2a/simulate' || path === '/api/w2/trace' || path === '/api/w3/trace';
const hash = (bytes: Buffer) => createHash('sha256').update(bytes).digest('hex');
function owned(info: TestInfo): string {
  const path = resolve(evidence, hash(Buffer.from(info.testId)).slice(0, 24));
  if (!existsSync(path)) mkdirSync(path, { recursive: true }); return path;
}
function save(info: TestInfo, name: string, value: unknown): void {
  writeFileSync(resolve(owned(info), name + '.json'), JSON.stringify(value, null, 2), { flag: 'wx' });
}
async function image(page: Page, info: TestInfo, name: string): Promise<void> {
  const bytes = await page.screenshot({ fullPage: false });
  writeFileSync(resolve(owned(info), name + '.png'), bytes, { flag: 'wx' });
}
async function frames(page: Page, count = 12): Promise<void> {
  await page.evaluate(count => new Promise<void>(done => { let n = 0; const next = () => ++n >= count ? done() : requestAnimationFrame(next); requestAnimationFrame(next); }), count);
}
/** Await this gesture's native completion; no polling, retry or timeout extension. */
async function nativeHorizontalScroll(region: Locator, input: () => Promise<void>): Promise<unknown> {
  const armed = await region.evaluate(el => {
    if (el.scrollWidth <= el.clientWidth) return false;
    if (!('onscrollend' in el)) throw new Error('The installed browser does not expose native scrollend.');
    const startLeft = el.scrollLeft;
    let sealed = false, lastInput = -1, ended: any = null;
    let resolveEnd!: (value: unknown) => void;
    const completed = new Promise(resolve => { resolveEnd = resolve; });
    const onInput = (event: Event) => {
      if (event instanceof KeyboardEvent && event.key !== 'ArrowRight') return;
      lastInput = event.timeStamp; ended = null;
    };
    const onEnd = (event: Event) => {
      if (event.target !== el || lastInput < 0 || event.timeStamp < lastInput || el.scrollLeft <= startLeft) return;
      ended = { method: 'native_scrollend_after_last_input', inputTime: lastInput, endTime: event.timeStamp, scrollLeft: el.scrollLeft, max: el.scrollWidth - el.clientWidth };
      if (sealed) resolveEnd(ended);
    };
    el.addEventListener('keydown', onInput); el.addEventListener('keyup', onInput); el.addEventListener('wheel', onInput, { passive: true }); el.addEventListener('scrollend', onEnd);
    (el as any).__w3NativeScroll = {
      seal: () => {
        sealed = true;
        // At the physical right boundary there is no further positive movement to await.
        if (el.scrollLeft >= el.scrollWidth - el.clientWidth) return Promise.resolve({ method: 'right_boundary_after_inputs', inputTime: lastInput, scrollLeft: el.scrollLeft, max: el.scrollWidth - el.clientWidth });
        if (ended?.inputTime === lastInput) return Promise.resolve(ended);
        return completed;
      },
      dispose: () => { el.removeEventListener('keydown', onInput); el.removeEventListener('keyup', onInput); el.removeEventListener('wheel', onInput); el.removeEventListener('scrollend', onEnd); delete (el as any).__w3NativeScroll; },
    };
    return true;
  });
  try { await input(); return armed ? await region.evaluate(el => (el as any).__w3NativeScroll.seal()) : null; }
  finally { if (armed) await region.evaluate(el => (el as any).__w3NativeScroll?.dispose()); }
}
async function ready(page: Page): Promise<void> {
  await expect(page.getByTestId('w3-trace')).toBeEnabled();
  await expect.poll(async () => (await routing(page)).status).toBe('ready');
}
async function load(page: Page, info: TestInfo): Promise<string[]> {
  const contextId = `context-${info.testId}-${randomUUID()}`, pageId = `page-${info.testId}-${randomUUID()}`;
  await page.route('**/*', route => new URL(route.request().url()).origin === 'http://127.0.0.1:8510'
    ? route.continue() : route.abort('blockedbyclient'));
  await page.addInitScript({ content: `window.__w3CaptureOwner=Object.freeze(${JSON.stringify({contextId,pageId})});window.__w3Capture=(${createW2ResponseCapture.toString()})(window.fetch.bind(window),window.__w3CaptureOwner,${JSON.stringify({endpoint:'/api/w3/trace',modelContract:'w3_ideal_refractive_routing_v1',messageType:'refractive_trace_result',cap:524288})});window.fetch=window.__w3Capture.fetch;` });
  const calls: string[] = [];
  page.on('request', request => { const path = new URL(request.url()).pathname; if (request.method() === 'POST' && science(path)) calls.push(path); });
  await page.goto('/'); await page.getByTestId('geometric-routing-workspace').click(); await page.getByTestId('routing-model').selectOption('w3'); await ready(page);
  expect((await routing(page)).active).toBe(true); expect(calls).toEqual([]); return calls;
}
async function preset(page: Page, value: 'A' | 'B' | 'C'): Promise<void> {
  await page.getByTestId('w3-preset').selectOption(value); await page.getByTestId('w3-load-preset').click(); await ready(page);
  expect((await routing(page)).currentResult).toBeNull();
}
async function select(page: Page, id: string): Promise<void> {
  await page.getByTestId(`w3-select-${id}`).click(); await expect(page.getByTestId('w3-tab-inspector')).toHaveAttribute('aria-selected', 'true');
}
async function edit(page: Page, field: string, text: string): Promise<void> {
  await page.getByTestId(`w3-${field}`).fill(text); await page.getByTestId(`w3-${field}`).blur(); await ready(page);
  expect((await routing(page)).currentResult).toBeNull(); expect((await routing(page)).display).toBeNull();
}
async function arm(page: Page, info: TestInfo): Promise<string> {
  const state = await routing(page), token = `${info.testId}-${await page.evaluate(() => crypto.randomUUID())}`;
  await page.evaluate(({ state, token }) => (window as any).__w3Capture.arm({ ...(window as any).__w3CaptureOwner, token,
    sceneSha256: state.validatedDigest, scene: state.candidate }), { state, token });
  return token;
}
async function trace(page: Page, info: TestInfo): Promise<any> {
  const token = await arm(page, info), waiting = page.waitForResponse(response => new URL(response.url()).pathname === '/api/w3/trace');
  await page.getByTestId('w3-trace').click(); const response = await waiting; expect(response.status()).toBe(200);
  const record = await page.evaluate(token => (window as any).__w3Capture.consume(token), token);
  const bytes = Buffer.from(record.base64, 'base64'), result = JSON.parse(bytes.toString('utf8'));
  expect(bytes.byteLength).toBeLessThanOrEqual(524288);
  await expect.poll(async () => (await routing(page)).currentRequestId).toBe(record.request.request_id);
  const state = await routing(page); expect(state.currentResult).toEqual(result);
  expect(result.scene).toEqual(record.request.scene); expect(result.scene_sha256).toBe(record.request.scene_sha256);
  expect(state.display.requestId).toBe(result.request_id); expect(state.display.sceneSha256).toBe(result.scene_sha256);
  expect(state.display.endpoints).toEqual(result.segments.map((segment: any) => ({ id: segment.id, start_m: segment.start_m, end_m: segment.end_m, medium_id: segment.medium_id })));
  expect(state.resultResource.retainedRawBytes).toBe(0); expect(state.resultResource.retainedResponseTextBytes).toBe(0);
  expect(state.ownedBytes).toBeLessThanOrEqual(4 * 1024 * 1024);
  expect((await snapshot(page)).ownedMemory.retainedBytes).toBeLessThanOrEqual(16 * 1024 * 1024);
  const name = `trace_${result.request_id}`;
  writeFileSync(resolve(owned(info), name + '.json'), bytes, { flag: 'wx' });
  save(info, name + '_identity', { request: record.request, bytes: bytes.length, sha256: hash(bytes), state,
    capture: await page.evaluate(() => (window as any).__w3Capture.snapshot()),
    instrumentation: 'One clone of original fetch response; clone/native buffering and base64/Node copies are test resources, excluded from app ownership.' });
  return result;
}
function close(actual: number, expected: number, scale = 1): void {
  expect(Math.abs(actual - expected)).toBeLessThanOrEqual(2e-13 * Math.max(scale, 1) + 2e-13 * Math.abs(expected));
}
function account(result: any): void {
  close(result.terminals.reduce((sum: number, terminal: any) => sum + terminal.relative_weight, 0), 1);
  expect(Math.abs(result.ledger.signed_residual)).toBeLessThanOrEqual(64 * Number.EPSILON);
}


async function source(page:Page,origin:number[],direction:number[]):Promise<void>{
 await select(page,'source');for(const [k,axis]of ['x','y','z'].entries())await page.getByTestId(`w3-source-origin-${axis}`).fill(String(origin[k]));
 for(const [k,axis]of ['x','y','z'].entries())await page.getByTestId(`w3-source-direction-${axis}`).fill(String(direction[k]));
 await page.getByTestId('w3-source-direction-z').blur();await ready(page);
}
async function event(page:Page,id:string):Promise<void>{await page.getByTestId('w3-tab-data').click();await page.getByTestId(`w3-event-${id}`).click();await expect(page.getByTestId('w3-selected-event')).toContainText(id);}
async function failure(page:Page):Promise<number>{const waiting=page.waitForResponse('**/api/w3/trace');await page.getByTestId('w3-trace').click();const response=await waiting;expect(response.status()).toBe(422);await expect(page.getByTestId('w3-error')).toBeVisible();expect((await routing(page)).currentResult).toBeNull();expect((await routing(page)).display).toBeNull();return response.status();}
async function numericAccess(page:Page,info:TestInfo,name:string,result:any):Promise<void>{
 const region=page.getByTestId('w3-events');await region.scrollIntoViewIfNeeded();
 const scalar=(v:number)=>Object.is(v,-0)?'-0':String(v);
 const expected=result.events.map((e:any)=>[`${e.id} / ${e.target.kind==='body_face'?e.target.body_id+'/'+e.target.face_id:e.target.element_id}`,e.branch_id,scalar(e.local_uv_m[0]),scalar(e.local_uv_m[1]),scalar(e.cumulative_length_m)]);
 expect(await region.locator('tbody tr').evaluateAll(rows=>rows.map(row=>[...row.querySelectorAll('td')].map(cell=>cell.textContent)))).toEqual(expected);
 const metrics=async()=>region.evaluate(el=>{const canvas=document.querySelector('[data-testid="bench-canvas"]')!.getBoundingClientRect(),rect=el.getBoundingClientRect(),last=el.querySelector('tbody tr:last-child td:last-child')!;
   const range=document.createRange();range.selectNodeContents(last);const text=range.getBoundingClientRect(),y=Math.max(rect.top+2,Math.min(rect.bottom-2,text.top+text.height/2));
   return{scrollLeft:el.scrollLeft,clientWidth:el.clientWidth,scrollWidth:el.scrollWidth,rootX:scrollX,rootWidth:document.documentElement.scrollWidth,viewport:innerWidth,canvas:canvas.toJSON(),whiteSpace:getComputedStyle(last).whiteSpace,lastValue:last.textContent,textLeft:text.left,textRight:text.right,containerLeft:rect.left,containerRight:rect.right,
    fullTextVisible:text.left>=rect.left&&text.right<=rect.right&&[text.left+1,text.right-1].every(x=>document.elementFromPoint(x,y)?.closest('td')===last)};});
 await region.evaluate(el=>{el.scrollLeft=0;});await region.focus();const before=await metrics();expect(before.clientWidth).toBeLessThanOrEqual(before.viewport);const firstCompletion=await nativeHorizontalScroll(region,()=>page.keyboard.press('ArrowRight'));const keyboard=await metrics();if(before.scrollWidth>before.clientWidth)expect(keyboard.scrollLeft).toBeGreaterThan(before.scrollLeft);else expect(keyboard.scrollLeft).toBe(0);
 const keyboardCompletion=await nativeHorizontalScroll(region,async()=>{for(let i=0;i<32;i++)await page.keyboard.press('ArrowRight');});const keyboardEnd=await metrics();expect(keyboardEnd.scrollLeft).toBeCloseTo(keyboardEnd.scrollWidth-keyboardEnd.clientWidth,0);expect(keyboardEnd.fullTextVisible).toBe(true);
 await region.evaluate(el=>{el.scrollLeft=0;});await region.hover();const pointerCompletion=await nativeHorizontalScroll(region,()=>page.mouse.wheel(10000,0));const pointer=await metrics();expect(pointer.scrollLeft).toBeCloseTo(pointer.scrollWidth-pointer.clientWidth,0);expect(pointer.fullTextVisible).toBe(true);expect(pointer.whiteSpace).toBe('nowrap');expect(pointer.lastValue).toBe(expected.at(-1)![4]);
 expect(pointer.rootWidth).toBeLessThanOrEqual(pointer.viewport+1);expect(pointer.rootX).toBe(before.rootX);expect(pointer.canvas).toEqual(before.canvas);expect(keyboardEnd.canvas).toEqual(before.canvas);expect((await routing(page)).currentResult).toEqual(result);save(info,name,{before,keyboard,keyboardEnd,pointer,expected,nativeCompletions:{first:firstCompletion,keyboard:keyboardCompletion,pointer:pointerCompletion}});
}

test('W3-B01 finite parallel slab has two certified interfaces and parallel displaced emergence',async({page},info)=>{
 await page.setViewportSize({width:1440,height:900});const calls=await load(page,info),r=await trace(page,info);
 expect(r.events.map((e:any)=>e.classification)).toEqual(['enter_refraction','exit_refraction','receiver_hit']);
 expect(r.events.slice(0,2).map((e:any)=>e.target.face_id)).toEqual(['z_min','z_max']);expect(r.segments.map((s:any)=>s.medium_id)).toEqual(['exterior','body:B1','exterior']);
 const theta=Math.PI/6,inside=Math.asin(Math.sin(theta)/1.5),entry=-.015+.04*Math.tan(theta),exit=entry+.03*Math.tan(inside);
 close(r.events[0].position_m[0],entry);close(r.events[1].position_m[0],exit);r.events[1].outgoing[0].direction.forEach((v:number,k:number)=>close(v,r.scene.source.direction[k]));
 const displacement=(entry+.03*Math.tan(theta)-r.events[1].position_m[0])*Math.cos(theta);close(displacement,.03*Math.sin(theta-inside)/Math.cos(inside));
 expect(r.terminals[0].category).toBe('detected');account(r);await event(page,'e0001');await expect(page.getByTestId('w3-selected-event')).toContainText('body:B1');
 const delta=r.events[1].position_m.map((v:number,k:number)=>v-r.events[0].position_m[k]),direction=r.events[0].incident_direction;
 const fromReturned=Math.hypot(delta[1]*direction[2]-delta[2]*direction[1],delta[2]*direction[0]-delta[0]*direction[2],delta[0]*direction[1]-delta[1]*direction[0])/Math.hypot(...direction);
 await expect(page.getByTestId('w3-slab-displacement')).toBeVisible();await expect(page.getByTestId('w3-slab-displacement-m')).toHaveText(String(fromReturned));await expect(page.getByTestId('w3-slab-displacement-mm')).toHaveText(String(fromReturned*1000));close(fromReturned,displacement);expect((await routing(page)).currentResult).toEqual(r);expect(calls).toHaveLength(1);
 await image(page,info,'parallel_slab');save(info,'independent_slab',{entry,exit,displacement,comparison:'Independent scalar Snell/slab construction at the declared angle; exact stored-input references belong to numerical gates.',calls,state:await routing(page)});expect(calls).toHaveLength(1);
});
test('W3-B02 finite prism pose and index edits change emergent direction and fixed receiver hit',async({page},info)=>{
 await page.setViewportSize({width:1440,height:900});const calls=await load(page,info);await preset(page,'B');const baseline=await trace(page,info),fixed=structuredClone(baseline.scene.elements[0]);
 await select(page,'B1');await edit(page,'interior-index','1.3');const higher=await trace(page,info);await preset(page,'B');await select(page,'B1');await edit(page,'rotation-y','10');const posed=await trace(page,info);
 for(const r of [baseline,higher,posed]){expect(r.scene.elements[0]).toEqual(fixed);expect(r.terminals[0].category).toBe('detected');account(r);}
 close(baseline.terminals[0].position_m[0],.006090605385328995);close(higher.terminals[0].position_m[0],-.004016576768008453);close(posed.terminals[0].position_m[0],.003614231619547034);
 expect(higher.events[1].outgoing[0].direction).not.toEqual(baseline.events[1].outgoing[0].direction);expect(posed.events[1].outgoing[0].direction).not.toEqual(baseline.events[1].outgoing[0].direction);
 await event(page,'e0002');await image(page,info,'prism_deviation');save(info,'fixed_receiver_variants',{baseline,higher,posed,calls});expect(calls).toHaveLength(3);
});
test('W3-B03 external entry internal TIR and later exit retain the correct media',async({page},info)=>{
 await page.setViewportSize({width:1440,height:900});const calls=await load(page,info);await preset(page,'C');const r=await trace(page,info);
 expect(r.events.map((e:any)=>e.classification)).toEqual(['enter_refraction','total_internal_reflection','exit_refraction','receiver_hit']);
 expect(r.events.slice(0,3).map((e:any)=>e.target.face_id)).toEqual(['z_min','hypotenuse','x_min']);expect(r.segments.map((s:any)=>s.medium_id)).toEqual(['exterior','body:B1','body:B1','exterior']);
 const tir=r.events[1];expect(tir.incident_medium_id).toBe('body:B1');expect(tir.outgoing[0].medium_id).toBe('body:B1');expect(tir.outgoing[0].branch_id).toBe(tir.branch_id);close(tir.incident_angle_rad,Math.PI/4);close(tir.outgoing_angle_rad,Math.PI/4);const [klo,khi]=tir.numerical_bounds.snell_discriminant_interval;expect(Number.isFinite(klo)&&Number.isFinite(khi)).toBe(true);expect(klo).toBeLessThanOrEqual(khi);expect(klo).toBeLessThanOrEqual(-1/8);expect(khi).toBeGreaterThanOrEqual(-1/8);expect(khi).toBeLessThan(0);
 expect(r.diagnostics.max_point_width_m).toBeLessThanOrEqual(1e-8);expect(r.diagnostics.max_direction_width).toBeLessThanOrEqual(1e-8);
 for(const e of r.events){for(const bounds of [e.numerical_bounds.position_intervals_m,e.numerical_bounds.incident_direction_intervals,...e.numerical_bounds.outgoing_direction_intervals.map((o:any)=>o.direction_intervals)])for(const [lo,hi]of bounds){expect(Number.isFinite(lo)&&Number.isFinite(hi)).toBe(true);expect(lo).toBeLessThanOrEqual(hi);expect(hi-lo).toBeLessThanOrEqual(1e-8);}}
 expect(tir).not.toHaveProperty('transmitted_angle_rad');expect(tir).not.toHaveProperty('critical_angle_rad');expect(r.terminals[0].category).toBe('detected');account(r);
 await event(page,'e0002');await expect(page.getByTestId('w3-selected-event')).toContainText('Reflected angle');await expect(page.getByTestId('w3-selected-event')).not.toContainText('Transmitted');await image(page,info,'prism_tir');save(info,'tir_media',{calls,state:await routing(page)});expect(calls).toHaveLength(1);
});
test('W3-B04 identities finite misses triangular ends and ambiguity never fabricate a route',async({page},info)=>{
 const calls=await load(page,info);await select(page,'B1');await edit(page,'interior-index','1');const equal=await trace(page,info);expect(equal.events.slice(0,2).map((e:any)=>[e.incident_medium_id,e.outgoing[0].medium_id])).toEqual([['exterior','body:B1'],['body:B1','exterior']]);
 equal.events[1].outgoing[0].direction.forEach((v:number,k:number)=>close(v,equal.scene.source.direction[k]));
 await preset(page,'C');await source(page,[.02,.04,.02],[0,1,0]);const ends=await trace(page,info);expect(ends.events.filter((e:any)=>e.target.kind==='body_face').map((e:any)=>e.target.face_id)).toEqual(['y_min','y_max']);
 await source(page,[.07,.04,.07],[0,1,0]);const miss=await trace(page,info);expect(miss.events.filter((e:any)=>e.target.kind==='body_face')).toEqual([]);expect(miss.terminals[0].category).toBe('escaped');
 await preset(page,'A');await select(page,'B1');await edit(page,'interior-index','1');await edit(page,'exterior-index','1.5');await source(page,[-.015,.08,-.04],[Math.sqrt(3)/2,0,.5]);const external=await trace(page,info);expect(external.events[0].classification).toBe('total_internal_reflection');expect(external.events[0].incident_medium_id).toBe('exterior');expect(external.events[0].outgoing[0].medium_id).toBe('exterior');
 await preset(page,'C');await select(page,'B1');await edit(page,'interior-index',String(Math.SQRT2));await failure(page);expect((await routing(page)).error).toContain('numerical_ambiguity');await image(page,info,'critical_ambiguity_no_route');
 save(info,'finite_and_ambiguity',{equal,ends,miss,external,calls,final:await routing(page)});expect(calls).toHaveLength(5);
});
test('W3-B05 pose index presets and repeated event IDs cannot attach stale inspection',async({page},info)=>{
 const calls=await load(page,info);await preset(page,'C');const first=await trace(page,info);await event(page,'e0002');const old=(await routing(page)).selectedEventIdentity;
 await edit(page,'interior-index','1.4');expect((await routing(page)).selectedEventIdentity).toBeNull();await expect(page.getByTestId('w3-selected-event')).toHaveText('No current event — trace the updated scene.');
 const second=await trace(page,info);expect(second.request_id).not.toBe(first.request_id);await event(page,'e0002');expect((await routing(page)).selectedEventIdentity.requestId).not.toBe(old.requestId);
 await page.getByTestId('w3-interior-index').fill('1e-');expect((await routing(page)).currentResult).toBeNull();expect((await routing(page)).selectedEventIdentity).toBeNull();expect((await routing(page)).display).toBeNull();await preset(page,'B');
 let release!:()=>void;const held=new Promise<void>(done=>{release=done;});await page.route('**/api/w3/trace',async route=>{const response=await route.fetch();await held;await route.fulfill({response});});
 const waiting=page.waitForRequest('**/api/w3/trace');await page.getByTestId('w3-trace').click();await waiting;await select(page,'B1');await page.getByTestId('w3-rotation-y').fill('5');await page.getByTestId('w3-rotation-y').blur();release();
 await expect.poll(async()=>(await snapshot(page)).resultRelease.busy).toBe(false);await ready(page);expect((await routing(page)).currentResult).toBeNull();expect((await routing(page)).display).toBeNull();expect(calls).toHaveLength(3);save(info,'stale_and_late',{old,calls,final:await routing(page),control:'Test-owned delayed delivery of one genuine backend response; no synthetic optical bytes.'});
});
test('W3-B06 camera selection opacity model switching and recovery remain noncomputing',async({page},info)=>{
 const calls=await load(page,info),r=await trace(page,info);for(const id of ['w3-top','w3-focus','w3-orbit','w3-reset'])await page.getByTestId(id).click();
 await select(page,'B1');await page.getByTestId('w3-normals').uncheck();await page.getByTestId('w3-angles').uncheck();await page.getByTestId('w3-opacity').focus();await page.keyboard.press('ArrowRight');await event(page,'e0001');
 const before=await routing(page);expect(before.currentRequestId).toBe(r.request_id);await page.getByTestId('routing-model').selectOption('w2');await expect(page.getByTestId('w2-trace')).toBeEnabled();const w2=(await snapshot(page)).geometricRouting.candidate;
 await page.getByTestId('routing-model').selectOption('w3');await ready(page);expect((await routing(page)).candidate).toEqual(before.candidate);expect((await routing(page)).currentResult).toBeNull();expect((await snapshot(page)).geometricRouting.candidate).toEqual(w2);expect(calls).toHaveLength(1);save(info,'passive_actions',{calls,before,after:await snapshot(page)});
});
test('W3-B07 caps escape weights and unsupported enclosures remain honest',async({page},info)=>{
 const calls=await load(page,info);await select(page,'B1');await page.getByTestId('w3-remove').click();await ready(page);await select(page,'D1');await page.getByTestId('w3-remove').click();await ready(page);const escaped=await trace(page,info);expect(escaped.limits.max_branches).toBe(63);expect(escaped.events).toEqual([]);expect(escaped.terminals[0].category).toBe('escaped');account(escaped);
 await preset(page,'A');await select(page,'B1');await edit(page,'position-x','.3');await edit(page,'position-z','.3');await source(page,[0,.08,0],[0,0,1]);await select(page,'D1');await page.getByTestId('w3-remove').click();await ready(page);
 for(const [i,z]of [[1,-.1],[2,.1]]){await page.getByTestId('w3-add-kind').selectOption('mirror');await page.getByTestId('w3-add').click();await ready(page);await edit(page,'position-x','0');await edit(page,'position-z',String(z));await edit(page,'rotation-y','0');}
 const capped=await trace(page,info);expect(capped.limits.max_branches).toBe(31);expect(capped.limits.max_records).toBe(128);expect(capped.status).toBe('incomplete');expect(capped.events).toHaveLength(32);expect(capped.terminals[0].reason).toBe('interaction_cap');expect(capped.ledger.truncated_weight).toBe(1);expect(capped.ledger.absorbed_weight).toBe(0);account(capped);expect(calls).toHaveLength(2);
 save(info,'caps_and_limits',{escaped,capped,calls,qualification:'This realizable exterior-mirror route proves bounded body-present counting. Exact alternating-interface step14 width stress is a separate shipped-core/reference gate, not an invented browser scene.'});
});
test('W3-B08 old modes documents R03 W1 and W2 preserve behavior and ownership',async({page},info)=>{
 const calls=await load(page,info);await page.getByTestId('ordinary-workspace').click();await expect(page.getByTestId('simulate')).toBeEnabled();await page.getByTestId('simulate').click();await expect.poll(async()=>(await snapshot(page)).currentResult?.requestId??null).not.toBeNull();
 await page.getByTestId('doc-toggle').click();await page.getByTestId('doc-title').fill('W3 preserved settings');await page.getByTestId('doc-notes').fill('Original documents remain settings only.');await page.getByTestId('doc-export').click();await expect(page.getByTestId('doc-download')).toBeVisible();
 for(const mode of ['two_path','polarization','polarized_two_path','sequential']){await page.getByTestId('mode').selectOption(mode);expect((await snapshot(page)).mode).toBe(mode);}
 await page.getByTestId('w1-view').click();await page.getByTestId('w1-load-example').click();await expect(page.getByTestId('simulate')).toBeEnabled();await page.getByTestId('simulate').click();await expect.poll(async()=>(await snapshot(page)).waveField.currentResult?.requestId??null).not.toBeNull();
 await page.getByTestId('research-workspace').click();await expect(page.getByTestId('r03-compute')).toBeEnabled();await page.getByTestId('r03-compute').click();await expect.poll(async()=>(await snapshot(page)).idealPolarization.currentResult?.requestId??null).not.toBeNull();
 await page.getByTestId('geometric-routing-workspace').click();await ready(page);await page.getByTestId('routing-model').selectOption('w2');await expect(page.getByTestId('w2-trace')).toBeEnabled();await page.getByTestId('w2-trace').click();await expect.poll(async()=>(await snapshot(page)).geometricRouting.currentRequestId).not.toBeNull();
 const labelPositions=()=>page.locator('.w2-label').evaluateAll(nodes=>nodes.filter(n=>!(n as HTMLElement).hidden).map(n=>({text:n.textContent,left:(n as HTMLElement).style.left,top:(n as HTMLElement).style.top})));
 const beforeW2Camera=await labelPositions();await page.getByTestId('w2-top').click();await frames(page);const afterW2Camera=await labelPositions();expect(beforeW2Camera.length).toBeGreaterThan(0);expect(afterW2Camera).not.toEqual(beforeW2Camera);

 await page.getByTestId('routing-model').selectOption('w3');await ready(page);await trace(page,info);const before=await snapshot(page);await select(page,'B1');await page.getByTestId('w3-interior-index').fill('-');const draft=(await routing(page)).candidate;
 await page.locator('.release-panel > summary').click();await page.getByTestId('release-results').click();const after=await snapshot(page);expect(after.refractiveRouting.numericalBytes).toBe(0);expect(after.geometricRouting.numericalBytes).toBe(0);expect(after.refractiveRouting.candidate).toEqual(draft);await expect(page.getByTestId('w3-interior-index')).toHaveValue('-');expect(after.documents.state).toEqual(before.documents.state);expect(after.ownedMemory.retainedBytes).toBeLessThan(before.ownedMemory.retainedBytes);save(info,'mixed_release',{before,after,calls});
});
test('W3-B09 real display loss recovers without another trace',async({page},info)=>{
 const calls=await load(page,info),r=await trace(page,info);await page.getByTestId('bench-canvas').evaluate(canvas=>{const ext=(canvas as HTMLCanvasElement).getContext('webgl2')!.getExtension('WEBGL_lose_context');if(!ext)throw new Error('Required WebGL context-loss control unavailable');(window as any).__w3LostContext=ext;ext.loseContext();});
 await expect.poll(async()=>(await routing(page)).completedRequestId).toBe(r.request_id);expect((await routing(page)).currentResult).toBeNull();await page.evaluate(()=>(window as any).__w3LostContext.restoreContext());await expect.poll(async()=>(await snapshot(page)).scene.contextLost).toBe(false);await page.getByTestId('w3-retry-display').click();await expect.poll(async()=>(await routing(page)).currentRequestId).toBe(r.request_id);expect((await routing(page)).currentResult).toEqual(r);expect(calls).toEqual(['/api/w3/trace']);save(info,'context_recovery',{calls,final:await snapshot(page)});
});
test('W3-B10 English layout at supported sizes preserves full numeric access',async({page},info)=>{
 const calls=await load(page,info),r=await trace(page,info);for(const [width,height]of [[1366,768],[1440,900],[1920,1080]]){await page.setViewportSize({width,height});await frames(page);const region=page.getByTestId('w3-events');await region.focus();await page.keyboard.press('ArrowRight');await region.hover();await page.mouse.wheel(180,0);await frames(page);const layout=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,english:!/\p{Script=Han}/u.test(document.body.innerText),cells:[...document.querySelectorAll('.w3-workspace td')].map(c=>({text:c.textContent,whiteSpace:getComputedStyle(c).whiteSpace})),canvas:document.querySelector('[data-testid="bench-canvas"]')!.getBoundingClientRect().toJSON()}));expect(layout.scrollWidth).toBeLessThanOrEqual(width+1);expect(layout.english).toBe(true);expect(layout.cells.length).toBeGreaterThan(0);expect(layout.cells.every(c=>c.whiteSpace==='nowrap')).toBe(true);expect(layout.canvas.width).toBeGreaterThan(300);expect(layout.canvas.height).toBeGreaterThan(250);expect((await routing(page)).currentResult).toEqual(r);await image(page,info,`layout_${width}x${height}`);save(info,`layout_${width}x${height}`,layout);await numericAccess(page,info,`access_${width}x${height}`,r);}
 expect(calls).toHaveLength(1);const profile=info.outputPath('w3-actual-zoom-profile');mkdirSync(resolve(profile,'Default'),{recursive:true});writeFileSync(resolve(profile,'Default/Preferences'),JSON.stringify({partition:{default_zoom_level:{x:Math.log(2)/Math.log(1.2)}}}),{flag:'wx'});
 const context=await chromium.launchPersistentContext(profile,{channel:'chrome',headless:true,viewport:null,deviceScaleFactor:undefined,baseURL:'http://127.0.0.1:8510',args:['--window-size=1440,900']});try{const zoomPage=context.pages()[0]??await context.newPage(),zoomCalls=await load(zoomPage,info);const zoomResult=await trace(zoomPage,info);const zoom=await zoomPage.evaluate(()=>({innerWidth,outerWidth,devicePixelRatio,scale:visualViewport?.scale,scrollWidth:document.documentElement.scrollWidth}));expect(zoom.devicePixelRatio).toBe(2);expect(zoom.scale).toBe(1);expect(zoom.innerWidth).toBeLessThan(740);expect(zoom.outerWidth).toBeGreaterThanOrEqual(1400);expect(zoom.scrollWidth).toBeLessThanOrEqual(zoom.innerWidth+1);const region=zoomPage.getByTestId('w3-events');await region.scrollIntoViewIfNeeded();await region.focus();await zoomPage.keyboard.press('ArrowRight');await region.hover();await zoomPage.mouse.wheel(250,0);await numericAccess(zoomPage,info,'actual_zoom_access',zoomResult);const cdp=await context.newCDPSession(zoomPage),shot=await cdp.send('Page.captureScreenshot',{format:'png',fromSurface:true,captureBeyondViewport:false});writeFileSync(resolve(owned(info),'actual_200percent.png'),Buffer.from(shot.data,'base64'),{flag:'wx'});save(info,'actual_zoom',{zoom,zoomCalls,method:'Actual Chrome content zoom in an isolated owned profile; no CSS/device/pinch emulation or user-profile changes.'});expect(zoomCalls).toHaveLength(1);}finally{await context.close();}
});
async function observeRendering(page:Page):Promise<any>{
 const raf=await page.evaluate(()=>new Promise<{intervalsMs:number[];meanMs:number;p50Ms:number;p95Ms:number;minMs:number;maxMs:number}>(done=>{const values:number[]=[];let previous:number|undefined;const frame=(now:number)=>{if(previous!==undefined)values.push(now-previous);previous=now;if(values.length===120){const sorted=[...values].sort((a,b)=>a-b);done({intervalsMs:values,meanMs:values.reduce((a,b)=>a+b,0)/values.length,p50Ms:sorted[59],p95Ms:sorted[113],minMs:sorted[0],maxMs:sorted.at(-1)!});}else requestAnimationFrame(frame);};requestAnimationFrame(frame);}));
 const state=await snapshot(page),labels=await page.evaluate(()=>({all:document.querySelectorAll('.w2-label').length,visible:[...document.querySelectorAll<HTMLElement>('.w2-label')].filter(el=>!el.hidden).length,body:document.querySelectorAll('.w3-body-label').length,event:document.querySelectorAll('.w3-event-label').length}));
 expect(raf.intervalsMs).toHaveLength(120);expect(raf.intervalsMs.every(n=>Number.isFinite(n)&&n>0)).toBe(true);
 return{raf,rendererMemory:state.scene.renderer,drawCalls:state.scene.geometricRouting.renderCalls,triangles:'NOT_EXPOSED by unchanged public snapshot',existingFrameObservations:state.scene.geometricRouting,ownedMemory:state.ownedMemory,w3:{numericalBytes:state.refractiveRouting.numericalBytes,renderingBytes:state.refractiveRouting.renderingBytes,stateBytes:state.refractiveRouting.stateBytes,domReservationBytes:state.refractiveRouting.domReservationBytes},labels,qualification:'Actual browser RAF intervals and renderer counters; no claim of whole-process heap, total GPU memory or universal frame rate.'};
}
test('W3-B11 normal speed recording shows edits explicit Trace deviation and TIR',async({browser},info)=>{
 const context=await browser.newContext({baseURL:'http://127.0.0.1:8510',viewport:{width:1440,height:900},recordVideo:{dir:resolve(owned(info),'recording'),size:{width:1440,height:900}}}),page=await context.newPage(),started=Date.now();
 try{const calls=await load(page,info),ownershipPhases:any[]=[{phase:'before',state:await routing(page)}];await preset(page,'B');await page.waitForTimeout(1500);const first=await trace(page,info);ownershipPhases.push({phase:'first',state:await routing(page)});await event(page,'e0002');await page.waitForTimeout(2500);await edit(page,'interior-index','1.3');await image(page,info,'recording_stale');await page.waitForTimeout(2500);const higher=await trace(page,info);ownershipPhases.push({phase:'higher',state:await routing(page)});await event(page,'e0002');await page.waitForTimeout(2500);await preset(page,'B');await select(page,'B1');await edit(page,'rotation-y','10');await page.waitForTimeout(2000);const posed=await trace(page,info);ownershipPhases.push({phase:'posed',state:await routing(page)});await event(page,'e0002');await page.getByTestId('w3-top').click();await page.waitForTimeout(2000);await page.getByTestId('w3-orbit').click();await preset(page,'C');await page.waitForTimeout(2000);const tir=await trace(page,info);ownershipPhases.push({phase:'tir',state:await routing(page)});await event(page,'e0002');await image(page,info,'recording_tir');const rendering=await observeRendering(page);await page.waitForTimeout(Math.max(0,42000-(Date.now()-started)));const final=await snapshot(page);expect(calls).toHaveLength(4);expect(tir.events[1].classification).toBe('total_internal_reflection');expect(final.scene.geometricRouting.rendererCount).toBe(1);expect(final.scene.geometricRouting.controlsCount).toBe(1);expect(final.scene.geometricRouting.rafCount).toBe(1);save(info,'recording_observations',{elapsedSeconds:(Date.now()-started)/1000,browser:browser.version(),first,higher,posed,tir,calls,rendering,ownershipPhases,final});}finally{await context.close();}
});
test('W3-C01 held actual W3 worker excludes all eleven computation kinds', async ({ page }, info) => {
  const directory = process.env.W3_HELD_DIR; test.skip(!directory, 'Requires a separately owned actual-worker hold child.');
  const calls = await load(page, info); await page.getByTestId('w3-trace').click();
  await expect.poll(() => { try { return JSON.parse(readFileSync(resolve(directory!, 'started.json'), 'utf8')).operation; } catch { return null; } }).toBe('refractive_routing');
  await expect(page.getByTestId('w3-trace')).toBeDisabled(); expect(calls).toHaveLength(1);
  const health = await fetch('http://127.0.0.1:8510/api/v1/health'); expect((await health.json() as any).busy).toBe(true);
  const requests = JSON.parse(readFileSync(process.env.W3_CONTENDER_FIXTURES!, 'utf8'));
  const responses = [];
  for (const item of requests) {
    const response = await fetch('http://127.0.0.1:8510' + item.path, { method: 'POST', headers: { Origin: 'http://127.0.0.1:8510', 'Content-Type': 'application/json' }, body: JSON.stringify(item.payload) });
    expect(response.status, item.path).toBe(409); responses.push({ path: item.path, status: response.status });
  }
  expect(responses).toHaveLength(11); writeFileSync(resolve(directory!, 'release.flag'), 'Release this task-owned worker.', { flag: 'wx' });
  await expect.poll(async () => (await routing(page)).currentRequestId).not.toBeNull();
  save(info, 'held_all_contenders', { calls, responses, final: await snapshot(page), completed: JSON.parse(readFileSync(resolve(directory!, 'completed.json'), 'utf8')) });
});

test('W3-C02 worker and encoding holds survive browser cancellation until actual completion', async ({ page, context }, info) => {
  const directory = process.env.W3_HELD_ENCODING_DIR; test.skip(!directory, 'Requires a separately owned actual-encoding hold child.');
  const calls = await load(page, info); await page.getByTestId('w3-trace').click();
  await expect.poll(() => existsSync(resolve(directory!, 'started.json'))).toBe(true); await context.close();
  expect((await (await fetch('http://127.0.0.1:8510/api/v1/health')).json() as any).busy).toBe(true);
  const requests = JSON.parse(readFileSync(process.env.W3_CONTENDER_FIXTURES!, 'utf8')), responses = [];
  for (const item of requests) {
    const response = await fetch('http://127.0.0.1:8510' + item.path, { method: 'POST', headers: { Origin: 'http://127.0.0.1:8510', 'Content-Type': 'application/json' }, body: JSON.stringify(item.payload) });
    expect(response.status, item.path).toBe(409); responses.push({ path: item.path, status: response.status });
  }
  expect(responses).toHaveLength(11);
  writeFileSync(resolve(directory!, 'release.flag'), 'Release this task-owned encoder.', { flag: 'wx' });
  await expect.poll(async () => (await (await fetch('http://127.0.0.1:8510/api/v1/health')).json() as any).busy).toBe(false);
  save(info, 'encoding_disconnect', { calls, responses, completed: JSON.parse(readFileSync(resolve(directory!, 'completed.json'), 'utf8')) }); expect(calls).toHaveLength(1);
});

test('W3-C03 foreign held worker permits noncomputing W3 validation only', async ({ page }, info) => {
  const directory = process.env.W3_FOREIGN_HELD_DIR; test.skip(!directory, 'Requires an owned older-operation hold child and declared valid request.');
  const requests = JSON.parse(readFileSync(process.env.W3_CONTENDER_FIXTURES!, 'utf8')), foreign = requests.find((item: any) => item.path === '/api/v1/simulate');
  const pending = fetch('http://127.0.0.1:8510' + foreign.path, { method: 'POST', headers: { Origin: 'http://127.0.0.1:8510', 'Content-Type': 'application/json' }, body: JSON.stringify(foreign.payload) });
  await expect.poll(() => existsSync(resolve(directory!, 'started.json'))).toBe(true);
  const calls = await load(page, info); const waiting = page.waitForResponse('**/api/w3/trace'); await page.getByTestId('w3-trace').click(); expect((await waiting).status()).toBe(409);
  await expect(page.getByTestId('w3-error')).toBeVisible(); expect((await routing(page)).currentResult).toBeNull();
  writeFileSync(resolve(directory!, 'release.flag'), 'Release this task-owned older operation.', { flag: 'wx' }); expect((await pending).status).toBe(200);
  await expect.poll(async () => (await (await fetch('http://127.0.0.1:8510/api/v1/health')).json() as any).busy).toBe(false);
  save(info, 'foreign_worker', { calls, final: await snapshot(page) });
});


test('W3-C04 malformed identity and display faults remain separate without optical replay',async({page},info)=>{
 const calls=await load(page,info);if(process.env.W3_TRANSPORT_FAULT){const waiting=page.waitForResponse('**/api/w3/trace');await page.getByTestId('w3-trace').click();expect((await waiting).status()).toBe(200);await expect(page.getByTestId('w3-error')).toBeVisible();const state=await routing(page);expect(state.currentResult).toBeNull();expect(state.display).toBeNull();expect(calls).toEqual(['/api/w3/trace']);save(info,'transport_fault',{calls,state,fault:process.env.W3_TRANSPORT_FAULT});return;}
 const token=await arm(page,info);await page.evaluate(()=>{const original=Element.prototype.append;let fired=false;Element.prototype.append=function(...nodes){if(!fired&&this.getAttribute('data-testid')==='w3-terminals'&&nodes.some(n=>n instanceof HTMLTableElement)){fired=true;Element.prototype.append=original;throw new Error('Controlled W3 result DOM preparation fault');}return original.apply(this,nodes);};});
 const waiting=page.waitForResponse('**/api/w3/trace');await page.getByTestId('w3-trace').click();expect((await waiting).status()).toBe(200);const captured=await page.evaluate(token=>(window as any).__w3Capture.consume(token),token),bytes=Buffer.from(captured.base64,'base64'),original=JSON.parse(bytes.toString('utf8'));writeFileSync(resolve(owned(info),'original_numerical_response.json'),bytes,{flag:'wx'});await expect.poll(async()=>(await routing(page)).completedRequestId).not.toBeNull();const completed=await routing(page);expect(completed.currentResult).toBeNull();expect(completed.renderError).toContain('Controlled');await page.getByTestId('w3-retry-display').click();await expect.poll(async()=>(await routing(page)).currentRequestId).toBe(completed.completedRequestId);expect((await routing(page)).currentResult).toEqual(original);expect(calls).toEqual(['/api/w3/trace']);save(info,'dom_display_failure',{before:completed,after:await routing(page),calls,classification:'Controlled DOM presentation failure; genuine numerical response retained without optical replay.'});
});
