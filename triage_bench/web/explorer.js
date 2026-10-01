'use strict';
const $ = s => document.querySelector(s);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const json = v => esc(JSON.stringify(v, null, 2));
const pct = n => n == null ? 'Not recorded' : (n * 100).toFixed(1) + '%';
const pretty = v => String(v ?? '').replaceAll('_', ' ');
const fieldNames = {initial_owner:'First investigating team',priority:'Incident priority',next_check:'Next diagnostic check',insufficient_evidence:'Insufficient evidence?'};
const fieldName = f => fieldNames[f] || pretty(f);
const splitName = s => ({train:'Training',validation:'Validation',test:'Held-out test',challenge:'Paired challenges'}[s] || s);
const chapters = [
 ['overview','The study','Start with four decisions and a fictional policy.'],
 ['data','Data atlas','Explore the splits, families and paired challenges.'],
 ['models','Rules, ML & Jev','Follow how each approach produces a decision.'],
 ['transform','What changed','Inspect the original and focused Jev inputs.'],
 ['results','Results','Compare overall scores, fields and scenario families.'],
 ['cases','Case workbench','Trace a saved prediction to its evidence and request.'],
 ['sandbox','Evidence sandbox','Change synthetic evidence and run the local approaches.'],
 ['next','Next experiment','Keep development cases apart from the final evaluation.']
];
const presets = [
 ['validation','NS-b073aba91088','A radio fault, overlooked','See how clearer task definitions changed Jev’s owner and next check.'],
 ['validation','NS-847827ec5900','The priority boundary','Inspect the original ML features and the revised impact-only classifier.'],
 ['validation','NS-f53e2040618c','Maintenance does not explain everything','Focused Jev improves. Revised ML assigns the wrong domain.'],
 ['validation','NS-bed90468cf79','An ML regression','Inspect the features behind a new power-domain error.'],
 ['test','NS-50f2d4fcb9b6','A change or a radio diagnostic?','Both Jev versions choose a different check from the reference.'],
 ['challenge','NS-7f0e4cde2d4f-b','An optical fault on the wrong path','Compare the paired graphs. Focused Jev gives a wrong owner 99% probability.']
];
let state = {page:'overview', split:'validation', id:'NS-b073aba91088', model:'jev_focused', field:'initial_owner',
 atlasSplit:'validation', atlasModel:'jev_focused', resultSplit:'test', metric:'all_fields_accuracy',
 filter:'all', family:'all', caseTab:'evidence', reveal:true, tour:false, case:null, microscope:null, lensSearch:'', lensGroup:'all', lensLimit:15, version:0, sandboxDraft:null, sandboxResult:null};
let study;
async function api(path, data) {
 const response = await fetch(path, data ? {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)} : {});
 const body = await response.json();
 if (!response.ok) throw new Error(body.error || 'The request failed.');
 return body;
}
function toast(message) { $('#toast').textContent = message; $('#toast').classList.add('show'); setTimeout(()=>$('#toast').classList.remove('show'),4000); }
function options(values, current, label = v => v) {return values.map(v=>`<option value="${esc(v)}" ${v===current?'selected':''}>${esc(label(v))}</option>`).join('');}
function button(text, action, attrs='', cls='') {return `<button class="${cls}" data-action="${action}" ${['model','field','case-tab'].includes(action)?`aria-pressed="${cls.split(' ').includes('active')}"`:''} ${attrs}>${text}</button>`;}
function codeBlock(value) {return `<pre>${json(value)}</pre>`;}
function title(kicker, heading, lead) {return `<div class="eyebrow">${kicker}</div><h1 class="chapter-title">${heading}</h1><p class="lead">${lead}</p>`;}
function notice(text, warn=false) {return `<div class="notice ${warn?'warn':''}">${text}</div>`;}
function scrollToContent(element) {element.scrollIntoView({behavior:window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches?'auto':'smooth',block:'start'});}
function familyCases(split) {return study.splits[split].families.flatMap(f=>f.cases.map(c=>({...c,family:f.name})));}
function caseLink(p) {return button(`<span><b>${esc(p[2])}</b><span>${esc(p[3])}</span></span><span class="right">↗</span>`, 'preset',`data-split="${p[0]}" data-id="${p[1]}"`,'case-link');}
function syncLocation(push=false) {
 const url=new URL(location.href);
 url.hash=state.page;
 for(const [key,value]of Object.entries({split:state.split,case:state.id,model:state.model,field:state.field,view:state.caseTab}))url.searchParams.set(key,value);
 const saved=Object.fromEntries(['page','split','id','model','field','caseTab','atlasSplit','atlasModel','resultSplit','metric','filter','family','reveal','tour'].map(k=>[k,state[k]]));
 history[push&&url.href!==location.href?'pushState':'replaceState']({inspection:saved},'',url);
}
function route(page, push=true) {
 captureSandbox();
 state.page = chapters.some(c=>c[0]===page) ? page : 'overview';
 if(state.page!=='cases'&&state.family!=='all'&&!familyCases(state.split).some(c=>c.id===state.id&&c.family===state.family))state.family='all';
 syncLocation(push);render();window.scrollTo(0,0);$('#main').focus({preventScroll:true});
}
function tourBanner() {
 if(!state.tour)return '';
 const i=chapters.findIndex(c=>c[0]===state.page);
 return `<div class="tour-note"><span><b>Guided tour · ${i+1} / ${chapters.length}</b><br>${chapters[i][2]}</span><div class="tour-progress">${chapters.map((_,j)=>`<i class="${j<=i?'done':''}"></i>`).join('')}</div>${button('Exit tour','exit-tour','','small-button')}</div>`;
}
function render(capture=true) {
 if(capture)captureSandbox();syncLocation();
 $('#navigation').innerHTML=chapters.map((c,i)=>`<a href="#${c[0]}" data-page="${c[0]}" class="${state.page===c[0]?'active':''}" ${state.page===c[0]?'aria-current="page"':''}><span class="number">0${i+1}</span>${c[1]}</a>`).join('');
 const index=chapters.findIndex(c=>c[0]===state.page);
 $('#breadcrumb').textContent='The study / '+chapters[index][1];
 $('#chapter-select').innerHTML=options(chapters.map(c=>c[0]),state.page,v=>`${chapters.findIndex(c=>c[0]===v)+1} / 8 · ${chapters.find(c=>c[0]===v)[1]}`);
 $('#tour').textContent=state.tour?'Restart guided tour':'Start guided tour';
 const views={overview:overviewView,data:dataView,models:modelsView,transform:transformView,results:resultsView,cases:caseView,sandbox:sandboxView,next:nextView};
 $('#main').innerHTML=tourBanner()+views[state.page]();
 document.querySelectorAll('.table-wrap').forEach(wrap=>{
  wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label','Scrollable comparison table');
 if(wrap.scrollWidth>wrap.clientWidth)wrap.insertAdjacentHTML('beforebegin','<p class="table-hint">Scroll sideways to see all columns →</p>');
 });
 const comparisonURL='/?run='+(study.runs[state.split]?.id||study.runs.validation?.id||'')+'&case='+state.id;
 $('#comparison-link').href=comparisonURL;$('#top-comparison-link').href=comparisonURL;
 $('#chapter-footer').innerHTML=`<span>${index?button('← '+chapters[index-1][1],'page',`data-page="${chapters[index-1][0]}"`):'Northstar Telecom · Synthetic study'}</span><span>${index<chapters.length-1?button(chapters[index+1][1]+' →','page',`data-page="${chapters[index+1][0]}"`,'primary'):button('Return to the workbench','page','data-page="cases"','primary')}</span>`;
 if(state.page==='cases' && state.caseTab==='inside' && ['ml','ml_structured'].includes(state.model) && !state.microscope) loadMicroscope();
}
function overviewView() {
 const splits=study.splits, results=study.runs.test?.providers;
 return `<div class="hero"><div><div class="eyebrow">An interactive study · Northstar Telecom</div><h1>Look inside<br>the decision.</h1><p>I am comparing rules, a trained ML classifier and Jev on synthetic network incidents to understand where each fails and which changes help.</p><div class="actions">${button('Take the guided tour →','tour','','primary')}${button('Inspect a failure','preset','data-split="challenge" data-id="NS-7f0e4cde2d4f-b"')}</div><div class="subtle">Explore the saved experiments. The sandbox runs locally.</div></div><div class="orbit"><div class="orbit-title">FOUR DECISIONS, ONE POLICY</div><div class="orbit-line"><span class="symbol">01</span><div><b>Who investigates first?</b><small>RAN, transport, power, core or NOC</small></div></div><div class="orbit-line"><span class="symbol">02</span><div><b>How urgent is the incident?</b><small>Priority from impact status and affected sites</small></div></div><div class="orbit-line"><span class="symbol">03</span><div><b>What do I check next?</b><small>A diagnostic action to gather or test evidence</small></div></div><div class="orbit-line"><span class="symbol">04</span><div><b>Is the evidence sufficient?</b><small>Can I justify an initial investigating team?</small></div></div></div></div>
 <div class="grid four"><div class="card"><span class="stat-label">Synthetic packets</span><span class="stat">${Object.values(splits).reduce((n,s)=>n+s.records,0).toLocaleString()}</span><span class="subtle">Templates and generated variations</span></div><div class="card"><span class="stat-label">Training families</span><span class="stat">${splits.train.families.length}</span><span class="subtle">${splits.train.records} packets fit the ML models</span></div><div class="card"><span class="stat-label">Paired challenges</span><span class="stat">${splits.challenge.records/2}</span><span class="subtle">One factor changes in each pair</span></div><div class="card highlight"><span class="stat-label">Focused Jev · held-out check</span><span class="stat">${pct(results?.jev_focused?.metrics.all_fields_accuracy)}</span><span class="subtle">All four decisions correct, test set</span></div></div>
 <p class="subtle">These inputs already describe abnormalities. Raw KPI time-series detection needs a separate experiment.</p><div class="section-head"><h2>Follow the evidence</h2><span class="subtle">Every stage is inspectable</span></div><div class="pipeline">${button('01 · Incident packet<span>Observations, impact, topology</span>','page','data-page="data"')}<span class="arrow">→</span>${button('02 · Decision methods<span>Rules, fitted weights or Jev</span>','page','data-page="models"')}<span class="arrow">→</span>${button('03 · What changed<span>Original or focused evidence</span>','page','data-page="transform"')}<span class="arrow">→</span>${button('04 · Prediction & reference<span>Probabilities, errors, paired cases</span>','page','data-page="cases"')}</div>
 <div class="section-head"><h2>Start with a revealing case</h2></div><div class="grid two"><div class="case-links">${presets.slice(0,3).map(caseLink).join('')}</div><div class="case-links">${presets.slice(3).map(caseLink).join('')}</div></div>
 ${notice('These are teaching scenarios, not a validated sample of a real telecom network. High scores show agreement with this synthetic policy and its reference decisions. They do not measure operational readiness.')}`;
}
function dataView() {
 const split=state.atlasSplit, ds=study.splits[split];
 const descriptions={train:'ML learns its vocabulary and coefficients from these 600 packets and their separate answer keys. Jev does not receive these reference answers.',validation:'These 11 families provided the failure cases used to develop experiment 2. The learning set is the first packet from each family, a subset of validation.',test:'These 11 families did not fit the ML models or select experiment 2 changes. A small earlier run had exposed five packets; this is not a pristine unseen benchmark.',challenge:'Twelve pairs test sensitivity to a changed fact: impact, evidence age, maintenance scope or topology. The two packets in a pair share most of their evidence.'};
 return title('02 · Data atlas','Scenarios, families and packets.','Written scenarios define the evidence and reference decisions. A generator varies counts, timestamps, identifiers and presentation. Twenty packets in a regular family share the same central scenario.')+
 `<div class="grid four">${Object.entries(study.splits).map(([s,d])=>`<div class="card ${s===split?'highlight':''}"><span class="stat-label">${splitName(s)}</span><span class="stat">${d.records}<small> packets</small></span><span class="subtle">${d.families.length} ${s==='challenge'?'archetypes':'families'}</span>${button('Explore','atlas-split',`data-split="${s}"`,'small-button margin-top')}</div>`).join('')}</div>
 <div class="controls"><label>Dataset<select id="atlas-split">${options(Object.keys(study.splits),split,splitName)}</select></label><label>Colour by recorded approach<select id="atlas-model">${options(Object.keys(study.providers),state.atlasModel,v=>study.providers[v])}</select></label></div>
 ${notice(esc(descriptions[split]))}<div class="section-head"><h2>${pretty(split)} families</h2><div class="legend"><span><i class="swatch"></i>All four correct</span><span><i class="swatch wrong"></i>At least one wrong</span><span><i class="swatch neutral"></i>No result</span></div></div>
 <p class="subtle">Each square is a packet. Click to inspect it. ${split==='validation'?'The outlined square in each family belongs to the 11-packet learning set.':''} ${split==='challenge'?'Consecutive A/B packets form a pair.':''}</p>
 <div class="family-grid">${ds.families.map(f=>`<section class="card family"><h3>${esc(split==='challenge'?challengeName(f):pretty(f.name))}</h3><span class="subtle">${f.cases.length} packets ${split==='challenge'?'· '+new Set(f.cases.map(c=>c.pair_id)).size+' pairs':''}</span><div class="dots">${f.cases.map(c=>{const o=c.outcomes[state.atlasModel];return button(o?(o.correct?'✓':'×'):'·', 'atlas-case',`data-split="${split}" data-id="${c.id}" aria-label="Inspect ${c.id}: ${o?(o.correct?'all four correct':'incorrect '+pretty(o.wrong_fields.join(', '))):'no recorded prediction'}" title="${c.id}: ${o?(o.correct?'all four correct':pretty(o.wrong_fields.join(', '))):'no recorded prediction'}"`,'dot '+(o?(o.correct?'correct':'wrong'):'')+(split==='validation'&&study.learning_ids.includes(c.id)?' learning':''));}).join('')}</div></section>`).join('')}</div>
 <div class="grid two margin-top"><section class="card"><h3>What does “authored” mean?</h3><p>I wrote the evidence, intended investigating domain and next check using AI-assisted templates. Software generated variations and derived priority from the policy. These are constructed examples, not observations from a live network.</p>${button('Inspect an example input →','atlas-example','','small-button')}</section><section class="card"><h3>Inputs and answer keys stay separate</h3><p>Inputs contain observations, impact, topology and change context. A separate key contains the family, accepted answers and rationale. The explorer joins them for inspection. Inference receives the allowlisted input state.</p><p>A held-out family was not used to fit or select the change being evaluated. Variations within a family are correlated. Recurring phrases and policy patterns can still make these tests easier than real incidents.</p></section></div>`;
}
function challengeName(f) {
 const names={'challenge-archetype-0':'Impact count · 9 vs 10 sites','challenge-archetype-1':'Fresh vs stale measurement','challenge-archetype-2':'Maintenance · wording invariance','challenge-archetype-3':'Shared vs unrelated dependency'};
 return names[f.name]||pretty(f.name);
}
function pairedView(c) {
 if(!c.paired)return '';
 const p=c.paired;
 const diffs=[];
 function diff(a,b,path='input') {
  if(JSON.stringify(a)===JSON.stringify(b))return;
  if(a&&b&&typeof a==='object'&&typeof b==='object'&&!Array.isArray(a)&&!Array.isArray(b)) {
   for(const key of new Set([...Object.keys(a),...Object.keys(b)]))diff(a[key],b[key],path+'.'+key);
  } else diffs.push({field:path,this_case:a,paired_case:b});
 }
 diff(c.input,p.input);
 const isGraph=c.reference.changed_path==='input.topology';
 return `<div class="section-head"><h2>Inspect the controlled change</h2><span class="subtle">${esc(c.reference.pair_id)} · ${esc(pretty(c.reference.pair_kind))}</span></div><div class="grid two"><section class="card paired-card"><h3>This packet · ${esc(c.id)}</h3>${isGraph?graph(c.input):codeBlock(diffs.map(d=>({field:d.field,value:d.this_case})))}${state.reveal?`<p>Reference: ${esc(Object.keys(study.fields).map(f=>fieldName(f)+': '+pretty(c.reference.labels[f])).join(' · '))}</p>`:''}</section><section class="card paired-card"><h3>Paired packet · ${esc(p.id)}</h3>${isGraph?graph(p.input):codeBlock(diffs.map(d=>({field:d.field,value:d.paired_case})))}${state.reveal?`<p>Reference: ${esc(Object.keys(study.fields).map(f=>fieldName(f)+': '+pretty(p.reference.labels[f])).join(' · '))}</p>`:''}${button('Inspect this partner','partner',`data-id="${p.id}"`,'small-button')}</section></div><details><summary>Exact changed input fields</summary>${codeBlock(diffs)}</details>`;
}
function modelsView() {
 const original=study.runs.validation?.providers.ml?.metadata.training;
 const revised=study.runs.validation?.providers.ml_structured?.metadata.training;
 return title('03 · Decision methods','Three ways to make the same decision.','Each approach selects the same four fields under the Northstar policy. The two local ML variants fit the same training set. Jev uses a hosted checkpoint without additional training in this study.')+
 `<div class="grid three"><section class="card"><div class="eyebrow">Rules · explicit branches</div><h2>Match words. Apply impact policy.</h2><p>A simple keyword router searches observation text in order: power, core, transport, RAN. Recovery and uncertainty branches run first. Priority follows the exact impact rule.</p><div class="chips"><span class="chip">No fitting</span><span class="chip">First matching group wins</span></div><p>It can match a domain word in a healthy observation. It does not compute graph dependencies.</p>${button('Follow a rule trace','inspect-model','data-model="baseline"','small-button')}</section>
 <section class="card"><div class="eyebrow">ML · fitted coefficients</div><h2>Learn from 600 labelled packets.</h2><p>Experiment 1 turns the original state into TF-IDF word features. Four logistic classifiers learn weights for owner, priority, next check and evidence sufficiency.</p><p>TF-IDF weights words by their frequency in a packet and rarity across training packets. Logistic regression learns how those features score each choice.</p><p>Experiment 2 adds character features and structured impact. Its priority classifier sees only impact status and count band.</p><div class="chips"><span class="chip">Train-only fitting</span><span class="chip">Uncalibrated probabilities</span></div>${button('Open the ML microscope','inspect-model','data-model="ml_structured"','small-button')}<details><summary>Original training configuration</summary>${codeBlock(original)}</details><details><summary>Revised training configuration</summary>${codeBlock(revised)}</details></section>
 <section class="card dark"><div class="eyebrow" style="color:var(--lime)">Jev · hosted choice model</div><h2>Supply state and questions.</h2><p>Jev 1.13.0 receives a policy, an incident state and four choice questions. Each question defines its valid choices. I did not supply any reference answers in the request.</p><p>Experiment 2 changes the evidence representation and question definitions. The checkpoint and policy stay fixed.</p><div class="chips"><span class="chip">Exact payload visible</span><span class="chip">Saved response visible</span></div>${button('Inspect Jev’s request','page','data-page="transform"','small-button')}</section></div>
 <div class="section-head"><h2>The policy supplies the decision contract</h2></div><section class="card"><p>“Initial owner” means the first investigating team, not a proven root cause. A directly observed radio malfunction can justify a radio diagnostic while the exact cause remains unknown. If impact is degraded at 18 sites, priority is P2 regardless of the owner.</p><details><summary>Read the complete policy</summary><pre>${esc(study.policy)}</pre></details><div class="table-wrap"><table><thead><tr><th>Decision</th><th>Choices</th><th>What the app exposes</th></tr></thead><tbody>${Object.entries(study.fields).map(([f,choices])=>`<tr><td>${esc(fieldName(f))}</td><td>${esc(Object.keys(choices).join(' · '))}</td><td>${f==='priority'?'Structured impact and the threshold rule':'Evidence, task criteria and class probabilities'}</td></tr>`).join('')}</tbody></table></div></section>
 ${notice('The ML microscope reconstructs the fitted classifier’s score from active features and weights. These contributions are not causal explanations. Jev’s hosted weights, activations and internal reasoning are not available; the app exposes its input and returned output.')}`;
}
function caseToolbar() {
 const cases=matchingCases(),index=cases.findIndex(c=>c.id===state.id),filtered=state.page==='cases';
 const filters={all:'All cases',wrong:'At least one wrong decision',high:'Wrong at ≥80% probability',regression:'ML: newly incorrect decision'};
 const stepper=`<div class="case-stepper">${button('← Previous','step-case','data-direction="-1" '+(index<=0?'disabled':''),'small-button')}<span class="subtle">${index>=0?`${index+1} / ${cases.length}`:`0 / ${cases.length}`} packets</span>${button('Next →','step-case','data-direction="1" '+(index<0||index>=cases.length-1?'disabled':''),'small-button')}</div>`;
 return `<details class="case-selection" ${state.caseTab==='evidence'||state.page!=='cases'?'open':''}><summary>Choose a packet<span>${esc(splitName(state.split))} · ${esc(challengeName({name:state.case?.reference.incident_family_id||''}))}${filtered&&state.filter!=='all'?' · '+esc(filters[state.filter]):''}</span></summary><div class="case-toolbar"><label>Dataset<select id="case-split">${options(Object.keys(study.splits),state.split,splitName)}</select></label><label>Scenario family<select id="case-family">${options(['all',...study.splits[state.split].families.map(f=>f.name)],state.family,v=>v==='all'?'All families':challengeName({name:v}))}</select></label><label class="case-picker">Packet<select id="case-id" ${cases.length?'':'disabled'}>${cases.length?options(cases.map(c=>c.id),state.id,v=>`${cases.findIndex(c=>c.id===v)+1} · ${v}`):'<option>No matching packets</option>'}</select></label>${filtered?`<details class="failure-filters" ${state.filter!=='all'?'open':''}><summary>Failure filters · ${esc(study.providers[state.model])}</summary><div class="controls"><label>Filter approach<select id="filter-model">${options(Object.keys(study.providers),state.model,v=>study.providers[v])}</select></label><label>Case filter<select id="case-filter">${options(['all','wrong','high','regression'],state.filter,v=>filters[v])}</select></label></div></details>`:''}</div></details>${stepper}${!cases.length?`<div class="filter-empty">No packets match these filters. The previously opened evidence remains below. ${button('Clear filters','clear-filters','','small-button')}</div>`:''}`;
}
function matchingCases() {
 return familyCases(state.split).filter(c=>{
  if(state.family!=='all'&&c.family!==state.family)return false;
  if(state.page!=='cases')return true;
  if(state.filter==='all')return true;
  const m=c.outcomes[state.model];
  if(state.filter==='wrong')return m&&!m.correct;
  if(state.filter==='high')return m?.high_probability_wrong;
  if(state.filter==='regression')return c.outcomes.ml&&c.outcomes.ml_structured&&c.outcomes.ml_structured.wrong_fields.some(f=>!c.outcomes.ml.wrong_fields.includes(f));
  return true;
 });
}
async function applyCaseFilters() {
 const cases=matchingCases();
 if(cases.length&&!cases.some(c=>c.id===state.id))await selectCase(state.split,cases[0].id,state.page);
 else render();
}
function transformView() {
 const c=state.case;if(!c)return '<div class="loading">Loading the case…</div>';
 const original=c.requests.jev, focused=c.requests.jev_focused;
 return title('04 · Experiment 2','Make the task and evidence explicit.','Validation failures guided changes to the input representation and question definitions. This comparison shows the combined revision; it does not isolate the effect of each change.')+caseToolbar()+
 `<div class="grid two"><section class="card"><div class="experiment-stamp">EXPERIMENT 1 · ORIGINAL</div><h2>Policy + complete packet</h2><p>The state includes the ticket summary, observation reports, impact, topology and operator note. Questions use short task definitions.</p><div class="chips"><span class="chip">${original.utf8_bytes.toLocaleString()} request bytes</span><span class="chip">${original.matches_saved_request===true?'Matches saved request':original.matches_saved_request===false?'Reconstruction differs':'No saved request for this case'}</span></div><details><summary>Inspect original packet</summary>${codeBlock(c.input)}</details></section>
 <section class="card highlight"><div class="experiment-stamp">EXPERIMENT 2 · FOCUSED</div><h2>Policy + compact evidence</h2><p>The compact request retains evidence, impact, topology and change context. It adds the count band and report age, removes duplicate prose and defines each decision more precisely.</p><div class="chips"><span class="chip">${focused.utf8_bytes.toLocaleString()} request bytes</span><span class="chip">${focused.matches_saved_request===true?'Matches saved request':focused.matches_saved_request===false?'Reconstruction differs':'No saved request for this case'}</span></div><details><summary>Inspect transformed packet</summary>${codeBlock(c.compact)}</details></section></div>
 <div class="section-head"><h2>Trace the transformation</h2></div><div class="table-wrap"><table><thead><tr><th>Source</th><th>Change</th><th>Why it may help</th></tr></thead><tbody><tr><td>service_impact.affected_sites</td><td>Add ${esc(c.compact.service_impact.affected_sites_band)}</td><td>Make the 9/10-site policy boundary explicit.</td></tr><tr><td>decision_timestamp − observed_at</td><td>Add report_age_minutes = ${esc(c.compact.observations[0].report_age_minutes)}</td><td>Remove timestamp arithmetic. This still does not establish measurement freshness.</td></tr><tr><td>ticket + operator note + source wrapper</td><td>Remove duplicate prose and top-level identifiers</td><td>Reduce repeated statements. Topology node identifiers remain.</td></tr><tr><td>observations, topology, change_record</td><td>Retain the evidence and its context</td><td>Preserve facts needed for routing and maintenance checks.</td></tr><tr><td>Choice questions</td><td>Define first investigator, diagnostics and uncertainty</td><td>Distinguish unknown root cause from insufficient evidence to start a domain investigation.</td></tr></tbody></table></div>
 <div class="controls"><label>Inspect a question<select id="decision-field">${options(Object.keys(study.fields),state.field,fieldName)}</select></label></div><div class="grid two"><section class="card"><h3>Original question</h3>${codeBlock(original.body.questions[state.field])}</section><section class="card"><h3>Focused question</h3>${codeBlock(focused.body.questions[state.field])}</section></div>
 <div class="grid two margin-top"><section class="card"><h3>Exact original request</h3><p>Policy text + state + questions + checkpoint. No answer key.</p>${button('Download request JSON','download','data-kind="original-request"','small-button')} ${button('Copy request JSON','copy-json','data-kind="original-request"','small-button')}<details><summary>Inspect complete payload</summary>${codeBlock(original.body)}</details><div class="hash">State SHA-256: ${original.state_sha256}</div></section><section class="card"><h3>Exact focused request</h3><p>More explicit questions can increase total request length even when the evidence packet is shorter.</p>${button('Download request JSON','download','data-kind="focused-request"','small-button')} ${button('Copy request JSON','copy-json','data-kind="focused-request"','small-button')}<details><summary>Inspect complete payload</summary>${codeBlock(focused.body)}</details><div class="hash">State SHA-256: ${focused.state_sha256}</div></section></div>
 ${notice('Report age describes when a report arrived. A recent report can describe an old measurement. Neither experiment computes whether an affected site actually depends on an observed faulty node. These are candidates for the next transformation, not changes already evaluated.',true)}
 <div class="actions">${button('See this case’s decisions →','page','data-page="cases"','primary')}${button('See the scheduler example','preset','data-split="validation" data-id="NS-b073aba91088"')}</div>`;
}
function resultsView() {
 const run=study.runs[state.resultSplit];
 if(!run)return title('05 · Results','Saved results are unavailable.','Run the documented comparisons to populate this view. Missing results are never filled in.')+notice('The explorer found no saved full run for this split.',true);
 const labels={all_fields_accuracy:'All four decisions',semantic_decisions_accuracy:'Three semantic decisions',with_software_priority_accuracy:'With software priority',pair_all_fields_accuracy:'Both packets in each pair',initial_owner:'Initial owner',priority:'Priority',next_check:'Next check',insufficient_evidence:'Evidence sufficiency'};
 const value=m=>state.metric in study.fields?m.fields[state.metric].accuracy:m[state.metric];
 const n=run.count;
 const summary=state.metric==='pair_all_fields_accuracy'?'A pair passes only when both packets have all four decisions correct.':state.metric==='with_software_priority_accuracy'?'A separately scored alternative replaces priority with the exact policy rule and retains the three model decisions. It does not modify saved predictions.':state.metric==='semantic_decisions_accuracy'?'Owner, next check and evidence sufficiency must all match. Priority is excluded.':`Errors and missing responses count as failures. ${state.resultSplit==='challenge'?'Each pair contains two closely matched packets.':'Each regular family contributes 20 correlated variations.'}`;
 return title('05 · Saved results','Gains vary across evaluation sets.','Focused Jev reaches 100% on the validation set used to develop the changes. Its test and paired-challenge errors point to further changes, which need new families for evaluation.')+
 `<div class="controls"><label>Evaluation set<select id="result-split">${options(['validation','test','challenge'],state.resultSplit,splitName)}</select></label><label>Score<select id="result-metric">${options(Object.keys(labels).filter(v=>v!=='pair_all_fields_accuracy'||state.resultSplit==='challenge'),state.metric,v=>labels[v])}</select></label></div>${notice(summary)}
 <div class="grid two"><section class="card"><div class="experiment-stamp">EXPERIMENT 2 · FULL COMPARISON</div><h2>${esc(labels[state.metric])}</h2><div class="comparison-bars">${Object.entries(study.providers).map(([p,name])=>{const m=run.providers[p]?.metrics,v=m?value(m):null;return `<div class="bar-row"><span>${esc(name)}</span><div class="bar-track"><div class="bar-fill ${p==='baseline'?'rules':p.startsWith('ml')?'ml':'jev'}" style="width:${v==null?0:v*100}%"></div></div><span class="bar-value">${pct(v)}</span></div>`;}).join('')}</div><p>${n} packets · ${study.splits[state.resultSplit].families.length} ${state.resultSplit==='challenge'?'archetypes · 12 pairs':'families'}</p><div class="hash">Saved run ${run.id}<br>Inputs SHA-256: ${run.providers.jev_focused?.metadata.input_sha256 || 'unavailable'}</div></section>
 <section class="card"><h2>Changes and remaining errors</h2><p>The first 220-packet validation run scored ${pct(study.runs.initial?.providers.jev?.metrics.all_fields_accuracy)} for Jev. It included five response-validation failures. A fresh original-request run scored ${pct(study.runs.validation?.providers.jev?.metrics.all_fields_accuracy)}.</p><p>Experiment 2 changes several inputs at once. The gain supports further study, but it does not tell me which individual transformation caused it.</p><p>Revised ML fixes the learned priority problem. It also introduces owner and next-check regressions on validation, then performs better on the test families.</p><div class="actions">${button('Inspect the ML regression','preset','data-split="validation" data-id="NS-bed90468cf79"','small-button')}${button('Inspect the test failure','preset','data-split="test" data-id="NS-50f2d4fcb9b6"','small-button')}</div></section></div>
 <div class="section-head"><h2>First experiment · initial validation run</h2><span class="subtle">220 packets · original approaches</span></div><div class="grid three">${['baseline','ml','jev'].map(p=>{const m=study.runs.initial?.providers[p]?.metrics;return `<section class="card"><h3>${esc(study.providers[p])}</h3><span class="stat">${pct(m?.all_fields_accuracy)}</span><p>All four correct · ${m?.failed_records??'unrecorded'} failed responses</p><div class="subtle">Owner ${pct(m?.fields.initial_owner.accuracy)} · Priority ${pct(m?.fields.priority.accuracy)}<br>Next check ${pct(m?.fields.next_check.accuracy)} · Evidence ${pct(m?.fields.insufficient_evidence.accuracy)}</div></section>`;}).join('')}</div><div class="section-head"><h2>Where do the approaches fail?</h2><span class="subtle">All four decisions · click a cell to inspect a case</span></div><div class="table-wrap"><table><thead><tr><th>Scenario family</th>${Object.values(study.providers).map(name=>`<th>${esc(name)}</th>`).join('')}</tr></thead><tbody>${study.splits[state.resultSplit].families.map(f=>`<tr class="result-family-row"><td>${esc(challengeName(f))}<small class="subtle"> · ${f.cases.length}</small></td>${Object.keys(study.providers).map(p=>{const recorded=f.cases.filter(c=>c.outcomes[p]),good=recorded.filter(c=>c.outcomes[p].correct).length,rate=recorded.length===f.cases.length?good/f.cases.length:null;const target=recorded.find(c=>!c.outcomes[p].correct)||recorded[0];return `<td class="heat-cell" style="background:${rate===null?'#eee':rate===1?'#e0eee3':rate===0?'#f3ddd0':'#efe8d9'}">${target?button(`${good}/${f.cases.length}`,'result-case',`data-split="${state.resultSplit}" data-id="${target.id}" data-model="${p}" aria-label="Inspect ${esc(challengeName(f))} with ${esc(study.providers[p])}"`):'No results'}</td>`;}).join('')}</tr>`).join('')}</tbody></table></div>
 <div class="section-head"><h2>High probability can accompany a wrong answer</h2></div><div class="grid two"><section class="card"><h3>Confidence is not a safety test</h3><p>Click a family above or open the wrong-at-80% filter in the workbench. Probabilities are reported by the models and are not calibrated for network operations.</p>${caseLink(presets[5])}</section><section class="card"><h3>Comparison controls</h3><p>${esc(study.freeze.selection || 'No freeze record available.')}</p><p>${esc(study.freeze.previous_exposure || '')}</p><span class="tag ${Object.keys(study.freeze.source_matches).length>0&&Object.values(study.freeze.source_matches).every(Boolean)?'good':'warn'}">${Object.keys(study.freeze.source_matches).length>0&&Object.values(study.freeze.source_matches).every(Boolean)?'Inference source matches recorded freeze':'Some inference sources differ from the freeze'}</span><details><summary>Inspect saved scores and training provenance</summary>${codeBlock(run)}</details>${button('Download results JSON','download','data-kind="results"','small-button')} ${button('Copy results JSON','copy-json','data-kind="results"','small-button')}</section></div>`;
}
function graph(packet) {
 const edges=packet.topology.edges,nodes=[...new Set(edges.flat())],levels={};nodes.forEach(n=>levels[n]=/(^|-)S\d+$/.test(n)?0:1);
 // Longest dependency depth, capped for an unexpected cycle in an edited fixture.
 for(let i=0;i<6;i++)for(const [a,b]of edges)levels[b]=Math.min(6,Math.max(levels[b],levels[a]+1));
 const groups={};nodes.forEach(n=>(groups[levels[n]]??=[]).push(n));
 const depth=Math.max(...Object.keys(groups).map(Number)),height=Math.max(190,...Object.values(groups).map(g=>g.length*33+65)),width=Math.max(470,depth*160+120),positions={};
 Object.entries(groups).forEach(([l,g])=>g.forEach((n,i)=>positions[n]=[55+(width-110)*Number(l)/Math.max(1,depth),45+(height-90)*(i+.5)/g.length]));
 const svg=`<svg class="network" viewBox="0 0 ${width} ${height}" role="img" aria-label="Inventory dependency graph for ${esc(packet.topology.pattern)}"><defs><marker id="edge-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#92aca0"/></marker></defs>${edges.map(([a,b])=>`<line x1="${positions[a][0]+16}" y1="${positions[a][1]}" x2="${positions[b][0]-18}" y2="${positions[b][1]}" marker-end="url(#edge-arrow)"/>`).join('')}${nodes.map(n=>{const [x,y]=positions[n],type=/(^|-)S\d+$/.test(n)?'site':/(^|-)U\d+$/.test(n)?'upstream':'';return `<g><title>${esc(n)}</title><circle class="${type}" cx="${x}" cy="${y}" r="17"/><text class="${type==='upstream'?'upstream':''}" text-anchor="middle" x="${x}" y="${y+3}">${esc(n.split('-').at(-1))}</text></g>`;}).join('')}</svg>`;
 return `<div class="graph-wrap">${svg}</div><p class="subtle">${esc(packet.topology.pattern)} · Arrows follow the supplied dependency edges. ${esc(packet.topology.note)}</p>`;
}
function predictionTable(c, rows=c.predictions, scored=true) {
 return `<div class="table-wrap"><table><thead><tr><th>Approach</th>${Object.keys(study.fields).map(f=>`<th>${esc(fieldName(f))}</th>`).join('')}</tr></thead><tbody>${scored&&state.reveal?`<tr><td><b>Reference</b></td>${Object.keys(study.fields).map(f=>`<td>${esc(pretty(c.reference.labels[f]))}</td>`).join('')}</tr>`:''}${Object.keys(rows).sort((a,b)=>Object.keys(study.providers).indexOf(a)-Object.keys(study.providers).indexOf(b)).map(p=>`<tr><td>${esc(study.providers[p])}</td>${Object.keys(study.fields).map(f=>{const row=rows[p],pred=row.predictions?.[f],prob=row.probabilities?.[f]?.[pred],correct=c.reference?.accepted_answers[f]?.includes(pred),cls=scored&&state.reveal?(row.status==='ok'&&correct?'cell-good':'cell-bad'):'';return `<td class="prediction-cell ${cls}">${esc(pretty(pred||'No valid response'))}${scored&&state.reveal?`<span class="result-mark">${row.status==='ok'?(correct?'✓ Matches reference':'× Differs from reference'):'× Response unavailable'}</span>`:''}${prob==null?'':`<small>Chosen probability ${pct(prob)}</small>`}</td>`;}).join('')}</tr>`).join('')}</tbody></table></div>`;
}
function probabilitiesView(c) {
 const row=c.predictions[state.model];
 const replay=!row&&state.model.startsWith('ml')&&state.microscope?.probabilities;
 if(!row&&!replay)return '<div class="empty">No saved prediction for this approach and packet.</div>';
 const dist=row?.probabilities?.[state.field]||replay;
 if(!dist)return '<div class="empty">This approach did not return class probabilities.<small>Rules produce a deterministic decision.</small></div>';
 const chosen=row?.predictions[state.field]||state.microscope.chosen,accepted=c.reference.accepted_answers[state.field];
 return (replay?notice('Local ML replay. This packet has no saved evaluation response.'):'')+Object.entries(dist).sort((a,b)=>b[1]-a[1]).map(([choice,p])=>`<div class="prob-row ${choice===chosen?'chosen':''} ${state.reveal&&accepted.includes(choice)?'reference':''} ${state.reveal&&choice===chosen&&!accepted.includes(choice)?'bad':''}"><span>${esc(pretty(choice))}${choice===chosen?' ●':''}${state.reveal&&accepted.includes(choice)?' ✓':''}</span><div class="bar-track"><div class="bar-fill" style="width:${p*100}%"></div></div><span class="bar-value">${pct(p)}</span></div>`).join('')+`<p class="subtle">● selected choice ${state.reveal?'· ✓ reference':''}.${state.model.startsWith('jev')?' The provider’s confidence field, when present, is separate from these class probabilities.':''}</p>`;
}
function ruleView(c) {
 return `<section class="card"><h3>Follow the executed branches</h3><p>${esc(c.rules.limitation)}</p>${c.rules.steps.map(s=>`<div class="rule-step ${!s.reached?'unreached':s.matched?'hit':''}"><b>${!s.reached?'Skipped':s.matched?'Matched':'Did not match'} · ${esc(s.name)}</b><span class="subtle">${esc(s.condition)}${s.evidence?.length?' · '+esc(Array.isArray(s.evidence)?s.evidence.join(', '):s.evidence):''}</span></div>`).join('')}<div class="notice">Priority runs separately: ${esc(c.rules.priority.status)} / ${esc(c.rules.priority.affected_sites)} sites → <b>${esc(c.rules.priority.result)}</b>.</div><details><summary>See the matched keyword groups</summary>${codeBlock(c.rules.steps)}</details></section>`;
}
function jevView(c) {
 const request=c.requests[state.model],row=c.predictions[state.model];
 return `<section class="card"><h3>Jev’s visible boundary</h3><p>Inspect the request and the hosted checkpoint’s response. Its internal weights and reasoning are not available.</p><span class="tag ${request.matches_saved_request?'good':'warn'}">${request.matches_saved_request?'Payload matches the recorded request hash':request.matches_saved_request===null?'No recorded request to verify':'Reconstructed payload differs from saved request'}</span><details open><summary>Task definition for ${esc(fieldName(state.field))}</summary>${codeBlock(request.body.questions[state.field])}</details><details><summary>Complete request</summary>${codeBlock(request.body)}</details><details><summary>Raw returned answer</summary>${codeBlock(row?.raw_response?.answers?.[state.field] || 'No saved raw answer')}</details><details><summary>Response audit</summary>${codeBlock({model:row?.resolved_model,usage:row?.usage,distribution_sums:row?.distribution_sums,probability_adjustments:row?.probability_adjustments,provider_confidence:row?.provider_confidence,latency_ms:row?.latency_ms})}</details>${button('Download case evidence','download','data-kind="case"','small-button')} ${button('Copy case JSON','copy-json','data-kind="case"','small-button')}</section>`;
}
function mlView(c) {
 const lens=state.microscope;
 if(!lens||lens.loading)return '<section class="card"><div class="loading">Fitting from the training split and reconstructing the classifier score…</div></section>';
 if(lens.error)return `<section class="card error">${esc(lens.error)}</section>`;
 const match=lens.saved_match, verified=match.training&&match.state&&match.source&&match.max_probability_difference<1e-10;
 const filtered=lens.contributions.filter(x=>(state.lensGroup==='all'||x.feature.startsWith(state.lensGroup+':'))&&x.feature.toLowerCase().includes(state.lensSearch.toLowerCase()));
 const max=Math.max(.001,...lens.contributions.map(c=>Math.abs(c.contribution)));
 return `<section class="card"><h3>ML microscope</h3><p>Feature value × weight difference = contribution to the selected class’s score versus the comparison class. Positive values favour ${esc(pretty(lens.chosen))}; negative values favour ${esc(pretty(lens.alternative))}.</p><span class="tag ${verified?'good':'warn'}">${verified?'Reconstruction matches saved probabilities':match.max_probability_difference===null?'Training-split replay · no saved prediction':'Current fit; inspect provenance before attributing the saved result'}</span>
 <div class="controls"><label>Compare ${esc(pretty(lens.chosen))} against<select id="lens-alternative">${options(Object.keys(study.fields[state.field]).filter(c=>c!==lens.chosen),lens.alternative,pretty)}</select></label><label>Feature group<select id="lens-group">${options(['all',...new Set(lens.contributions.map(c=>c.feature.split(':')[0]))],state.lensGroup,pretty)}</select></label><label>Find a feature<input id="lens-search" type="text" value="${esc(state.lensSearch)}" placeholder="e.g. power, scope, ten_or_more"></label></div>
 <div class="lens-summary"><span><strong>${lens.feature_count.toLocaleString()}</strong>possible features</span><span><strong>${lens.active_features}</strong>active features</span><span><strong>${lens.intercept.toFixed(3)}</strong>intercept difference</span><span><strong>${lens.margin.toFixed(3)}</strong>complete score margin</span></div>
 <div id="feature-contributions">${featureRows(filtered,max)}</div><p class="subtle"><span id="feature-count">Showing ${Math.min(filtered.length,state.lensLimit)} of ${filtered.length} matching active features.</span> The complete score sums every active contribution plus the intercept. Reconstruction error: ${lens.reconstruction_error.toExponential(2)}.</p>${button(state.lensLimit===15?'Show up to 50 features':'Show top 15 features','feature-limit','','small-button')}
 <div class="actions">${button('Download all contributions','download','data-kind="lens"','small-button')} ${button('Copy contributions JSON','copy-json','data-kind="lens"','small-button')}${button('Switch ML variant','switch-ml','','small-button')}</div><details><summary>Check score reconstruction and provenance</summary>${codeBlock({intercept:lens.intercept,groups:lens.groups,complete_margin:lens.margin,log_probability_ratio:lens.expected_log_odds,reconstruction_error:lens.reconstruction_error,saved_match:lens.saved_match,training:lens.metadata})}</details></section>
 <section class="card margin-top"><details><summary>Inspect five nearby training packets</summary><p>These are the five nearest training states by word TF-IDF cosine similarity. Similarity is not a causal explanation or proof of shared fault. Multiple entries can be variations from one family.</p>${lens.nearest_training.map(n=>`<div class="nearest"><b>${esc(pretty(n.family))} · similarity ${n.similarity.toFixed(3)}</b><p>${esc(n.observation)}</p><span class="subtle">Training reference: ${esc(pretty(n.reference[state.field]))} · ${esc(n.id)}</span></div>`).join('')}</details></section>`;
}
function featureRows(filtered,max) {return filtered.slice(0,state.lensLimit).map(c=>`<div class="contribution-row" title="value ${c.value.toFixed(6)} × weight difference ${c.weight_difference.toFixed(6)}"><span class="mono">${esc(c.feature.startsWith('character:')?'character:'+JSON.stringify(c.feature.slice(10)):c.feature)}</span><div class="signed-track"><div class="signed-fill ${c.contribution<0?'negative':''}" style="width:${Math.abs(c.contribution)/max*49}%"></div></div><span class="bar-value ${c.contribution<0?'bad':'good'}">${c.contribution>0?'+':''}${c.contribution.toFixed(3)}</span></div>`).join('') || '<div class="empty">No active feature matches.</div>';}
function caseView() {
 const c=state.case;if(!c)return '<div class="loading" role="status">Loading case evidence…</div>';
 const preset=presets.find(p=>p[1]===c.id),input=c.input;
 const tabs=[['evidence','1 · Evidence'],['decisions','2 · Decisions'],['inside','3 · Inside an approach'],...(c.paired?[['pair','Paired change']]:[])];
 if(!tabs.some(([id])=>id===state.caseTab))state.caseTab='evidence';
 let panel='';
 if(state.caseTab==='evidence')panel=`<div class="grid two"><section class="card"><h2>What the packet says</h2>${input.observations.map(o=>`<div class="evidence">${esc(o.detail)}</div><div class="subtle">Report arrived ${esc(o.observed_at)} · ${esc(o.source)}</div>`).join('')}<div class="chips"><span class="chip">${esc(input.service_impact.status)}</span><span class="chip">${input.service_impact.affected_sites===null?'Unknown site count':input.service_impact.affected_sites+(input.service_impact.affected_sites===1?' site':' sites')}</span><span class="chip">${esc(input.service_impact.basis)}</span></div><details><summary>Complete input packet</summary>${codeBlock(input)}</details>${state.reveal?`<details><summary>Separate answer key and rationale</summary>${codeBlock(c.reference)}</details>`:''}</section><section class="card"><h2>Supplied dependency graph</h2>${graph(input)}${c.partner?notice(`This pair changes ${esc(c.reference.changed_path || c.reference.pair_kind)}. Open Paired change to compare the two inputs.`):''}<details><summary>Inspect graph edges and change context</summary>${codeBlock({topology:input.topology,change_record:input.change_record})}</details></section></div>
 ${!state.reveal?`<div class="question-card"><b>Before revealing the key: which team should investigate first?</b><div class="actions">${Object.keys(study.fields.initial_owner).map(v=>button(pretty(v),'guess',`data-choice="${v}"`,'small-button')).join('')}</div><span class="subtle">The reference is a synthetic policy decision, not a confirmed root cause.</span></div>`:''}<div class="actions margin-top">${button('Compare the four decisions →','case-tab','data-view="decisions"','primary')}${c.paired?button('Compare the paired inputs','case-tab','data-view="pair"'):''}</div>`;
 if(state.caseTab==='decisions')panel=`<div class="section-head"><h2>Saved decisions · experiment 2 comparison</h2><span class="subtle">${state.reveal?'✓ Matches reference · × Differs':'Reference and correctness markers are hidden.'}</span></div>${Object.keys(c.predictions).length?predictionTable(c):notice('This training packet has no saved evaluation predictions. The ML microscope can replay the fitted classifier; Jev has not been called for it.')}<div class="actions margin-top">${button('Inspect '+esc(study.providers[state.model])+' →','case-tab','data-view="inside"','primary')}${button('Compare the Jev inputs','page','data-page="transform"')}</div>${Object.keys(c.initial_predictions).length?`<details><summary>Experiment 1 · original validation predictions</summary>${predictionTable(c,c.initial_predictions)}</details>`:''}`;
 if(state.caseTab==='inside')panel=`<section class="inspection-controls"><h2>Inspect an approach and a decision</h2><div class="segmented model-tabs" aria-label="Approach">${Object.entries(study.providers).map(([p,n])=>button(esc(n),'model',`data-model="${p}"`,p===state.model?'active':'')).join('')}</div><div class="segmented" aria-label="Decision">${Object.keys(study.fields).map(f=>button(esc(fieldName(f)),'field',`data-field="${f}"`,f===state.field?'active':'')).join('')}</div><p class="field-help">${state.field==='insufficient_evidence'?'The output answers “Is evidence insufficient?” Yes means the policy cannot yet justify an investigating domain.':'Compare the selected answer with the reference, then inspect the request or fitted score that produced it.'}</p></section><div class="grid two inspection-grid"><div><section class="card"><h2>${esc(study.providers[state.model])} · ${esc(fieldName(state.field))}</h2>${probabilitiesView(c)}</section>${state.reveal?`<section class="card margin-top"><h3>Reference rationale</h3>${Object.entries(c.reference.label_rationale).map(([k,v])=>`<p><b>${esc(pretty(k))}:</b> ${esc(typeof v==='string'?v:JSON.stringify(v))}</p>`).join('')}</section>`:''}${preset?notice(esc(preset[3])):''}</div><div>${state.model==='baseline'?ruleView(c):state.model.startsWith('jev')?jevView(c):mlView(c)}</div></div>`;
 if(state.caseTab==='pair')panel=pairedView(c)+`<div class="actions margin-top">${button('Compare this packet’s decisions →','case-tab','data-view="decisions"','primary')}${button('Inspect paired packet ↔','partner',`data-id="${c.partner}"`)}</div>`;
 return title('06 · Case workbench',preset?esc(preset[2]):esc(challengeName({name:c.reference.incident_family_id})),'Read the evidence, compare the four decisions, then inspect the selected approach.')+caseToolbar()+
 `<div class="case-meta"><div><span class="mono">${esc(c.id)}</span><div class="subtle">${esc(challengeName({name:c.reference.incident_family_id}))} · ${esc(splitName(c.split))} · ${esc(input.decision_timestamp)}</div></div><div class="actions">${button(state.reveal?'Hide reference':'Reveal reference','reveal','','small-button')}${button('Try an evidence change','page','data-page="sandbox"','small-button')}</div></div><nav class="workbench-tabs" aria-label="Case inspection steps">${tabs.map(([id,label])=>button(esc(label),'case-tab',`data-view="${id}" aria-controls="case-panel"`,id===state.caseTab?'active':'')).join('')}</nav><div id="case-panel" tabindex="-1">${panel}</div>`;
}
function sandboxView() {
 const c=state.case;if(!c)return '<div class="loading">Loading evidence…</div>';
 const draft=state.sandboxDraft || {status:c.input.service_impact.status,count:c.input.service_impact.affected_sites??'',observation:c.input.observations[0].detail};
 const inactive=['none','unknown'].includes(draft.status);
 return title('07 · Evidence sandbox','Change a fact. Watch the local decisions.','The sandbox replays edited evidence through the two trained ML variants and the rules. It does not fit a new model, score against the old key or call Jev. The saved experiments stay unchanged.')+caseToolbar()+
 `<div class="grid two"><section class="card sandbox-form" data-case="${c.id}"><h2>Edit the evidence</h2><p>Starting family: ${esc(challengeName({name:c.reference.incident_family_id}))}</p><div class="controls"><label>Service impact<select id="sandbox-status">${options(['outage','degraded','unknown','none'],draft.status)}</select></label><label>Affected sites<input type="number" id="sandbox-count" min="0" max="1000" value="${esc(draft.count)}" ${inactive?'disabled':''} aria-describedby="count-help"></label></div><p id="count-help" class="subtle">${inactive?'Unknown impact has an unknown count; no impact has zero sites.':'Priority changes at the 9/10-site boundary.'}</p><label>Observation evidence<textarea id="sandbox-observation" rows="6" maxlength="5000">${esc(draft.observation)}</textarea></label><div class="actions">${button('Set 9 sites','sandbox-count','data-count="9" '+(inactive?'disabled':''),'small-button')}${button('Set 10 sites','sandbox-count','data-count="10" '+(inactive?'disabled':''),'small-button')}</div><div class="actions margin-top">${button('Run local replay','sandbox-run','','primary')}${button('Reset evidence','sandbox-reset')}</div><p>Edits persist across chapters. Selecting another packet starts a new sandbox.</p></section><section class="card"><h2>What changes in the replay?</h2><p>The replay compares the three local approaches before and after the edit. The saved Jev answers stay available in the workbench.</p>${notice('Impact edits do not rewrite observation text; update both when they describe the same fact. Other observations and the dependency graph remain as supplied. The ticket summary follows the edited first observation.')}<details><summary>Recorded starting decisions · all five approaches</summary>${Object.keys(c.predictions).length?predictionTable(c,c.predictions,false):'<p>No saved predictions for this training packet.</p>'}</details><details><summary>Inspect the untouched source packet</summary>${codeBlock(c.input)}</details></section></div><div id="sandbox-output" class="sandbox-result" tabindex="-1" aria-live="polite">${sandboxOutput()}</div>`;
}
function captureSandbox() {
 const form=$('.sandbox-form');
 if(!form || form.dataset.case!==state.id)return;
 state.sandboxDraft={status:$('#sandbox-status').value,count:$('#sandbox-count').value,observation:$('#sandbox-observation').value};
}
function sandboxOutput() {
 const replay=state.sandboxResult;
 if(!replay)return '<div class="empty">Edit the evidence, then run a local replay to see what changes.</div>';
 const {response,draft}=replay,c=state.case;
 const changes=Object.keys(study.fields);
 const stale=JSON.stringify(draft)!==JSON.stringify(state.sandboxDraft);
 return `<section class="card"><div class="section-head"><h2>Local replay · before and after</h2><span class="tag">Rules + two ML variants</span></div><p id="replay-status">${stale?'Evidence has changed since this replay. Run it again to refresh the decisions.':'These outputs use the edited evidence below. They have no reference score.'}</p><div class="chips"><span class="chip">${esc(response.input.service_impact.status)} · ${esc(response.input.service_impact.affected_sites??'unknown')} sites</span><span class="chip">${draft.observation===c.input.observations[0].detail?'Observation unchanged':'Observation edited'}</span></div><p class="subtle">An arrow marks a changed choice. “Same” means the recorded choice stayed the same. A training packet has no recorded starting prediction.</p><div class="table-wrap"><table><thead><tr><th>Approach</th>${changes.map(f=>`<th>${esc(fieldName(f))}</th>`).join('')}</tr></thead><tbody>${Object.entries(response.outputs).map(([p,row])=>`<tr><td>${esc(study.providers[p])}</td>${changes.map(f=>{const before=c.predictions[p]?.predictions?.[f],after=row.predictions?.[f];return `<td class="prediction-cell ${before&&before!==after?'cell-changed':''}">${before&&before!==after?`${esc(pretty(before))} → <b>${esc(pretty(after))}</b>`:`<b>${esc(pretty(after||'No valid response'))}</b><small>${before?'Same choice':'Starting result not recorded'}</small>`}</td>`;}).join('')}</tr>`).join('')}</tbody></table></div><details><summary>Inspect the replayed packet, probabilities and rule trace</summary>${codeBlock(response)}</details></section>`;
}
function nextView() {
 return title('08 · Next experiment','Test the missing calculations.','Existing failures guide the next changes. I will freeze those changes before evaluating new families that did not influence them.')+
 `<div class="grid two"><section class="card"><div class="eyebrow">Candidate A · dependency coverage</div><h2>Does the faulty node explain the affected sites?</h2><p>A dependency calculation will identify which affected sites have paths through the observed faulty node. Jev will receive the supporting paths and coverage summary alongside the raw topology.</p><p>This needs reliable affected-site identities and a complete dependency map. A count and an incomplete inventory excerpt do not support that calculation.</p>${caseLink(presets[5])}<div class="understanding">The paired topology case makes the missing inference visible. The current focused request still requires Jev to connect fault location to dependencies.</div></section><section class="card"><div class="eyebrow">Candidate B · measurement freshness</div><h2>When was the evidence measured?</h2><p>The request will distinguish report arrival time from measurement time. The comparison will test whether explicit measurement age and freshness status improve routing.</p><p>The current data often carries measurement age in prose. Missing measurement times will stay explicitly unknown; report age cannot substitute for measurement age.</p><div class="understanding">The next data generator needs separate report and measurement timestamps, domain-reviewed freshness criteria and new examples with conflicting observations.</div></section></div>
 <section class="card margin-top"><h2>Comparison plan</h2><div class="plan-step"><span>1</span><div><h3>Create new development families</h3><p>The new scenarios will keep evidence and answer keys separate. Network specialists will review their realism before I freeze the references. Existing failures guide the hypotheses.</p></div></div><div class="plan-step"><span>2</span><div><h3>Change one input element at a time</h3><p>The comparison will test the unchanged request, explicit dependency coverage and measurement freshness on the same development cases, including correct cases to detect regressions.</p></div></div><div class="plan-step"><span>3</span><div><h3>Freeze the transformations and questions</h3><p>The Jev checkpoint and policy will stay fixed. ML fitting will use only training data, and the evaluation will score software-derived priority separately.</p></div></div><div class="plan-step"><span>4</span><div><h3>Evaluate new held-out families</h3><p>The evaluation will measure all-four accuracy, semantic decisions, paired sensitivity, high-probability errors and failures. Families used to develop a change will not be its final test.</p></div></div></section>
 ${notice('This experiment has not run. The observatory shows the existing evidence and saved results; it does not claim that these candidate transformations improve performance.')}`;
}
async function selectCase(split,id,page='cases') {
 const version=++state.version;state.split=split;state.id=id;state.case=null;state.microscope=null;state.lensSearch='';state.lensGroup='all';state.sandboxDraft=null;state.sandboxResult=null;
 route(page);
 try {const c=await api(`/api/case?split=${encodeURIComponent(split)}&id=${encodeURIComponent(id)}`);if(version!==state.version)return;state.case=c;render();}
 catch(e){if(version===state.version)$('#main').innerHTML=`<div class="error">${esc(e.message)}</div>`;}
}
async function loadMicroscope(alternative) {
 const split=state.split,id=state.id,variant=state.model,field=state.field,version=state.version;
 state.microscope={loading:true};
 if(state.page==='cases')render();
 try {const lens=await api(`/api/microscope?split=${split}&id=${id}&variant=${variant}&field=${field}${alternative?'&alternative='+encodeURIComponent(alternative):''}`);
 if(version!==state.version||id!==state.id||variant!==state.model||field!==state.field)return;state.microscope=lens;render();}
 catch(e){if(version===state.version&&id===state.id&&variant===state.model&&field===state.field){state.microscope={error:e.message};render();}}
}
function inspection(kind) {
 if(kind==='case')return state.case;
 if(kind==='original-request'||kind==='focused-request')return state.case.requests[kind==='original-request'?'jev':'jev_focused'].body;
 if(kind==='lens')return state.microscope;
 return study.runs[state.resultSplit];
}
function download(kind) {
 const params=new URLSearchParams({kind,split:kind==='results'?state.resultSplit:state.split,id:state.id,variant:state.model,field:state.field});
 if(kind==='lens')params.set('alternative',state.microscope.alternative);
 const a=document.createElement('a');a.href='/api/export?'+params;a.download='Northstar-inspection.json';a.click();
 toast('Export requested.');
}
async function copyExport() {
 try {await navigator.clipboard.writeText($('#export-text').value);toast('JSON copied.');}
 catch {$('#export-text').focus();$('#export-text').select();toast('Text selected. Use your usual copy shortcut.');}
}
async function dispatch(action,el) {
 if(action==='page'){route(el.dataset.page);return;}
 if(action==='tour'){await startTour();return;}
 if(action==='exit-tour'){state.tour=false;render();return;}
 if(action==='preset'||action==='atlas-case'){state.filter='all';state.family='all';state.reveal=true;state.caseTab='evidence';if(action==='atlas-case')state.model=state.atlasModel;await selectCase(el.dataset.split,el.dataset.id);return;}
 if(action==='atlas-example'){state.filter='all';state.family='all';state.caseTab='evidence';await selectCase(state.atlasSplit,familyCases(state.atlasSplit)[0].id);return;}
 if(action==='result-case'){state.model=el.dataset.model;state.filter='all';state.family='all';state.caseTab='decisions';await selectCase(el.dataset.split,el.dataset.id);return;}
 if(action==='atlas-split'){state.atlasSplit=el.dataset.split;render();return;}
 if(action==='partner'){state.filter='all';await selectCase(state.split,el.dataset.id);return;}
 if(action==='case-tab'){state.caseTab=el.dataset.view;syncLocation(true);render();$('#case-panel').focus({preventScroll:true});scrollToContent($('#case-panel'));return;}
 if(action==='step-case'){const cases=matchingCases(),index=cases.findIndex(c=>c.id===state.id),next=cases[index+Number(el.dataset.direction)];if(next)await selectCase(state.split,next.id,state.page);return;}
 if(action==='clear-filters'){state.filter='all';state.family='all';render();return;}
 if(action==='reveal'){state.reveal=!state.reveal;render();return;}
 if(action==='guess'){const correct=state.case.reference.accepted_answers.initial_owner.includes(el.dataset.choice);toast(correct?'Matches the reference. Now inspect the evidence.':'The reference selects '+pretty(state.case.reference.labels.initial_owner)+'. Inspect its rationale.');state.reveal=true;render();return;}
 if(action==='model'||action==='inspect-model'){state.model=el.dataset.model;state.microscope=null;state.lensSearch='';state.lensGroup='all';state.caseTab='inside';if(action==='inspect-model'){state.filter='all';route('cases');}else await applyCaseFilters();return;}
 if(action==='field'){state.field=el.dataset.field;state.microscope=null;syncLocation(true);render();return;}
 if(action==='switch-ml'){state.model=state.model==='ml'?'ml_structured':'ml';state.microscope=null;state.lensGroup='all';syncLocation(true);await applyCaseFilters();return;}
 if(action==='feature-limit'){state.lensLimit=state.lensLimit===15?50:15;render();return;}
 if(action==='download'){download(el.dataset.kind);return;}
 if(action==='copy-json'){$('#export-text').value=JSON.stringify(inspection(el.dataset.kind),null,2);$('#export-dialog').showModal();$('#export-text').focus();$('#export-text').select();return;}
 if(action==='close-export'){$('#export-dialog').close();return;}
 if(action==='copy-export'){await copyExport();return;}
 if(action==='sandbox-count'){$('#sandbox-count').value=el.dataset.count;captureSandbox();markReplayStale();return;}
 if(action==='sandbox-reset'){state.sandboxDraft=null;state.sandboxResult=null;render(false);return;}
 if(action==='sandbox-run'){
  if(!$('#sandbox-count').disabled&&!$('#sandbox-count').reportValidity())return;
  if(!$('#sandbox-observation').value.trim()){toast('Enter an observation before running the replay.');$('#sandbox-observation').focus();return;}
  captureSandbox();const draft={...state.sandboxDraft};
  const split=state.split,id=state.id,version=state.version;el.disabled=true;el.textContent='Running local models…';
  try {const response=await api('/api/sandbox',{split,id,status:draft.status,affected_sites:Number(draft.count),observation:draft.observation});
  if(version!==state.version)return;state.sandboxResult={response,draft};
  if(state.page!=='sandbox')return;
  captureSandbox();$('#sandbox-output').innerHTML=sandboxOutput();$('#sandbox-output').focus({preventScroll:true});scrollToContent($('#sandbox-output'));}
  catch(e){toast(e.message);}finally{el.disabled=false;el.textContent='Run local replay';}return;
 }
}
document.addEventListener('click',async event=>{
 if(event.target.closest('.skip-link')){event.preventDefault();$('#main').focus({preventScroll:true});scrollToContent($('#main'));return;}
 const pageLink=event.target.closest('[data-page]:not([data-action])');
 if(pageLink){event.preventDefault();route(pageLink.dataset.page);return;}
 const el=event.target.closest('[data-action]');if(!el)return;
 try {await dispatch(el.dataset.action,el);}catch(e){toast(e.message);}
});
document.addEventListener('change',async event=>{
 const el=event.target;
 if(el.id==='chapter-select')route(el.value);
 if(el.id==='atlas-split'){state.atlasSplit=el.value;render();}
 if(el.id==='atlas-model'){state.atlasModel=el.value;render();}
 if(el.id==='result-split'){state.resultSplit=el.value;if(state.metric==='pair_all_fields_accuracy'&&el.value!=='challenge')state.metric='all_fields_accuracy';render();}
 if(el.id==='result-metric'){state.metric=el.value;render();}
 if(el.id==='case-split'){const first=familyCases(el.value)[0];state.filter='all';state.family='all';await selectCase(el.value,first.id,state.page);}
 if(el.id==='case-id')await selectCase(state.split,el.value,state.page);
 if(el.id==='case-filter'){state.filter=el.value;await applyCaseFilters();}
 if(el.id==='case-family'){state.family=el.value;await applyCaseFilters();}
 if(el.id==='filter-model'){state.model=el.value;state.microscope=null;await applyCaseFilters();}
 if(el.id==='decision-field'){state.field=el.value;state.microscope=null;render();}
 if(el.id==='lens-alternative'){state.microscope=null;await loadMicroscope(el.value);}
 if(el.id==='lens-group'){state.lensGroup=el.value;render();}
 if(el.id==='sandbox-status'){const inactive=['none','unknown'].includes(el.value);$('#sandbox-count').disabled=inactive;if(inactive)$('#sandbox-count').value=el.value==='none'?'0':'';else if(!$('#sandbox-count').value)$('#sandbox-count').value='1';document.querySelectorAll('[data-action="sandbox-count"]').forEach(b=>b.disabled=inactive);$('#count-help').textContent=inactive?'Unknown impact has an unknown count; no impact has zero sites.':'Priority changes at the 9/10-site boundary.';captureSandbox();markReplayStale();}
});
function markReplayStale() {if(state.sandboxResult&&$('#replay-status'))$('#replay-status').textContent=JSON.stringify(state.sandboxResult.draft)!==JSON.stringify(state.sandboxDraft)?'Evidence has changed since this replay. Run it again to refresh the decisions.':'These outputs use the edited evidence below. They have no reference score.';}
document.addEventListener('input',event=>{
 if(['sandbox-count','sandbox-observation'].includes(event.target.id)){captureSandbox();markReplayStale();}
 if(event.target.id==='lens-search'){
  state.lensSearch=event.target.value;
  const lens=state.microscope;if(!lens?.contributions)return;
  const filtered=lens.contributions.filter(c=>(state.lensGroup==='all'||c.feature.startsWith(state.lensGroup+':'))&&c.feature.toLowerCase().includes(state.lensSearch.toLowerCase()));
  $('#feature-contributions').innerHTML=featureRows(filtered,Math.max(.001,...lens.contributions.map(c=>Math.abs(c.contribution))));
  $('#feature-count').textContent='Showing '+Math.min(filtered.length,state.lensLimit)+' of '+filtered.length+' matching active features.';
 }
});
async function startTour() {
 state.tour=true;state.model='jev_focused';state.field='initial_owner';state.caseTab='evidence';state.filter='all';state.family='all';state.atlasSplit='validation';state.atlasModel='jev_focused';state.resultSplit='test';state.metric='all_fields_accuracy';
 await selectCase('validation','NS-b073aba91088','overview');
}
$('#tour').addEventListener('click',()=>startTour());
async function restoreNavigation() {
 const old={id:state.id,split:state.split,model:state.model,field:state.field},params=new URLSearchParams(location.search);
 const saved=history.state?.inspection;
 if(saved)Object.assign(state,saved);
 else {
  if(params.get('model') in study.providers)state.model=params.get('model');
  if(params.get('field') in study.fields)state.field=params.get('field');
  const split=params.get('split'),id=params.get('case');
  if(study.splits[split]&&familyCases(split).some(c=>c.id===id)){state.split=split;state.id=id;}
  if(['evidence','decisions','inside','pair'].includes(params.get('view')))state.caseTab=params.get('view');
 }
 state.page=chapters.some(c=>c[0]===location.hash.slice(1))?location.hash.slice(1):'overview';
 if(old.model!==state.model||old.field!==state.field)state.microscope=null;
 if(!state.case||old.id!==state.id||old.split!==state.split){
  const version=++state.version;state.case=null;state.microscope=null;state.sandboxDraft=null;state.sandboxResult=null;render();
  try{const c=await api(`/api/case?split=${encodeURIComponent(state.split)}&id=${encodeURIComponent(state.id)}`);if(version!==state.version)return;state.case=c;}
  catch(e){toast(e.message);return;}
 }
 render();window.scrollTo(0,0);
}
window.addEventListener('popstate',()=>restoreNavigation());
window.addEventListener('hashchange',()=>{if(study&&state.page!==location.hash.slice(1))restoreNavigation();});
(async()=>{
 try {
  study=await api('/api/study');
  await restoreNavigation();
 }catch(e){$('#main').innerHTML=`<div class="error">Could not open the study: ${esc(e.message)}</div>`;}
})();
