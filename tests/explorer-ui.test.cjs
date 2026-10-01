const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');

// Exercise navigation and selection against small fixtures, without a browser,
// fitting a model, or making hosted requests.
function harness() {
  const element = {addEventListener(){}, focus(){}, innerHTML:'', textContent:''};
  const location = {href:'http://localhost/explorer#cases', search:'', hash:'#cases'};
  const history = {state:null, pushes:0};
  for (const method of ['pushState','replaceState']) history[method] = (value,unused,url) => {
    history.state=value;
    if(method==='pushState') history.pushes++;
    const parsed=new URL(url);
    Object.assign(location,{href:parsed.href,search:parsed.search,hash:parsed.hash});
  };
  const context = vm.createContext({URL,URLSearchParams,location,history,setTimeout,
    window:{addEventListener(){},scrollTo(){}},
    document:{querySelector:s=>s==='.sandbox-form'?null:element,addEventListener(){}},
    fetch:async()=>({ok:true,json:async()=>({id:'restored'})})});
  const source=fs.readFileSync(path.join(__dirname,'../triage_bench/web/explorer.js'),'utf8');
  vm.runInContext(source.slice(0,source.indexOf('(async()=>{')),context);
  const evaluate = code => vm.runInContext(code,context);
  evaluate(`
    study={providers:{jev_focused:'Jev',ml:'ML',ml_structured:'Revised ML'},fields:{initial_owner:{},priority:{}},splits:{validation:{families:[
      {name:'radio',cases:[
        {id:'A',outcomes:{jev_focused:{correct:true},ml:{wrong_fields:['priority']},ml_structured:{wrong_fields:['initial_owner']}}},
        {id:'B',outcomes:{jev_focused:{correct:false,high_probability_wrong:true},ml:{wrong_fields:[]},ml_structured:{wrong_fields:[]}}}]},
      {name:'power',cases:[{id:'C',outcomes:{jev_focused:{correct:false,high_probability_wrong:false}}}]}]}}};
    state.page='cases';state.id='A';state.case={id:'A'};
    render=()=>syncLocation();
  `);
  return {evaluate,history,location};
}

test('failure filtering uses the selected approach and probability threshold',()=>{
  const {evaluate}=harness();
  evaluate("state.filter='wrong'");
  assert.equal(evaluate("matchingCases().map(c=>c.id).join(',')"),'B,C');
  evaluate("state.filter='high'");
  assert.equal(evaluate("matchingCases().map(c=>c.id).join(',')"),'B');
});

test('family and failure filters intersect; other chapters ignore failure filters',()=>{
  const {evaluate}=harness();
  evaluate("state.filter='high';state.family='power'");
  assert.equal(evaluate('matchingCases().length'),0);
  evaluate("state.page='transform'");
  assert.equal(evaluate("matchingCases().map(c=>c.id).join(',')"),'C');
});

test('a regression includes a newly wrong field even when the old packet failed',()=>{
  const {evaluate}=harness();
  evaluate("state.filter='regression'");
  assert.equal(evaluate("matchingCases().map(c=>c.id).join(',')"),'A');
});

test('changing filters opens a matching packet rather than keeping an excluded packet',async()=>{
  const {evaluate}=harness();
  evaluate("state.filter='wrong';selectCase=async(split,id)=>{state.id=id}");
  await evaluate('applyCaseFilters()');
  assert.equal(evaluate('state.id'),'B');
});

test('an empty filter retains the previous evidence without inventing a match',async()=>{
  const {evaluate}=harness();
  evaluate("state.filter='high';state.family='power';selectCase=async()=>{throw Error('Unexpected selection')}");
  await evaluate('applyCaseFilters()');
  assert.equal(evaluate('state.id'),'A');
  assert.equal(evaluate('matchingCases().length'),0);
  evaluate("route('transform')");
  assert.equal(evaluate('state.family'),'all');
  assert.equal(evaluate('state.id'),'A');
});

test('local replay probabilities stay separate from missing saved or hosted predictions',()=>{
  const {evaluate}=harness();
  evaluate("const packet={predictions:{},reference:{accepted_answers:{initial_owner:['ran']}}};state.microscope={chosen:'ran',probabilities:{ran:.7,noc:.3}}");
  assert.match(evaluate('probabilitiesView(packet)'),/No saved prediction/);
  evaluate("state.model='ml'");
  assert.match(evaluate('probabilitiesView(packet)'),/Local ML replay/);
  assert.match(evaluate('probabilitiesView(packet)'),/70.0%/);
  assert.equal(evaluate('Object.keys(packet.predictions).length'),0);
});

test('inspection navigation records a distinct history entry and deep link',()=>{
  const {evaluate,history,location}=harness();
  evaluate("state.caseTab='inside';state.field='priority';syncLocation(true)");
  assert.equal(history.pushes,1);
  assert.equal(new URL(location.href).searchParams.get('view'),'inside');
  assert.equal(history.state.inspection.field,'priority');
  evaluate('syncLocation(true)');
  assert.equal(history.pushes,1);
});

test('Back restores the stored case, inspection step and result controls',async()=>{
  const {evaluate,history,location}=harness();
  history.state={inspection:{page:'cases',split:'validation',id:'B',model:'ml',field:'priority',caseTab:'decisions',resultSplit:'challenge',metric:'pair_all_fields_accuracy'}};
  location.hash='#cases';
  await evaluate('restoreNavigation()');
  assert.equal(evaluate('state.id'),'B');
  assert.equal(evaluate('state.caseTab'),'decisions');
  assert.equal(evaluate('state.resultSplit'),'challenge');
  assert.equal(evaluate('state.microscope'),null);
});

test('a delayed case response cannot replace a more recently selected case',async()=>{
  const {evaluate}=harness();
  evaluate("const pending={};api=path=>new Promise(resolve=>pending[path]=resolve)");
  const first=evaluate("selectCase('validation','B')");
  const second=evaluate("selectCase('validation','C')");
  evaluate("pending['/api/case?split=validation&id=C']({id:'C'})");
  await second;
  evaluate("pending['/api/case?split=validation&id=B']({id:'B'})");
  await first;
  assert.equal(evaluate('state.case.id'),'C');
});
