// TODO: progressively replace this DOM interaction layer with typed React
// components. It remains TypeScript source during the screen-by-screen migration.
// @ts-nocheck
export {}

const stations = [
  {name:'Rajiv Chowk',line:'BLUE · YELLOW',x:293,y:215,crowd:94,now:'12.8k',future:'15.2k',wait:'8 min',level:'critical'},
  {name:'Kashmere Gate',line:'YELLOW · VIOLET',x:392,y:280,crowd:87,now:'9.4k',future:'11.8k',wait:'6 min',level:'packed'},
  {name:'New Delhi',line:'YELLOW · AIRPORT',x:334,y:253,crowd:79,now:'8.1k',future:'10.3k',wait:'4 min',level:'packed'},
  {name:'Central Secretariat',line:'YELLOW · VIOLET',x:438,y:337,crowd:74,now:'7.3k',future:'9.1k',wait:'5 min',level:'busy'},
  {name:'Noida Sector 18',line:'BLUE',x:658,y:204,crowd:58,now:'5.6k',future:'6.4k',wait:'3 min',level:'busy'},
  {name:'Dwarka Sector 21',line:'BLUE · AIRPORT',x:162,y:50,crowd:42,now:'3.8k',future:'4.1k',wait:'2 min',level:'quiet'},
  {name:'Hauz Khas',line:'YELLOW · MAGENTA',x:526,y:244,crowd:69,now:'6.7k',future:'7.9k',wait:'4 min',level:'busy'},
  {name:'Botanical Garden',line:'BLUE · MAGENTA',x:765,y:285,crowd:62,now:'5.9k',future:'7.2k',wait:'3 min',level:'busy'},
  {name:'IGI Airport',line:'AIRPORT',x:606,y:222,crowd:36,now:'2.9k',future:'3.5k',wait:'2 min',level:'quiet'}
];

const busStops = [
  {name:'ISBT Kashmere Gate',line:'BUS 729 · 753',x:392,y:292,crowd:91,now:'3.8k',future:'4.9k',wait:'11 min',level:'critical',meta:'Bus terminal · 18 bays'},
  {name:'Connaught Place',line:'BUS 522 · 894',x:293,y:228,crowd:83,now:'2.9k',future:'3.7k',wait:'9 min',level:'packed',meta:'Bus hub · 8 bays'},
  {name:'AIIMS',line:'BUS 534 · 615',x:492,y:330,crowd:76,now:'2.4k',future:'3.1k',wait:'7 min',level:'busy',meta:'Bus interchange · 6 bays'},
  {name:'Nehru Place',line:'BUS 433 · 511',x:575,y:397,crowd:68,now:'2.1k',future:'2.6k',wait:'5 min',level:'busy',meta:'Bus terminal · 10 bays'},
  {name:'Anand Vihar ISBT',line:'BUS 543 · 740',x:706,y:198,crowd:88,now:'3.4k',future:'4.2k',wait:'12 min',level:'packed',meta:'Interstate terminal · 22 bays'},
  {name:'Dhaula Kuan',line:'BUS 610 · 729',x:235,y:324,crowd:57,now:'1.7k',future:'2.0k',wait:'6 min',level:'quiet',meta:'Bus interchange · 5 bays'},
  {name:'ITO',line:'BUS 85 · 307',x:438,y:274,crowd:72,now:'2.2k',future:'2.8k',wait:'8 min',level:'busy',meta:'Bus stop cluster · 4 bays'},
  {name:'Saket',line:'BUS 427 · 522',x:534,y:447,crowd:49,now:'1.4k',future:'1.8k',wait:'4 min',level:'quiet',meta:'Bus stop · 3 bays'}
];

const stationLayer=document.querySelector('#stations');
stations.forEach((s,i)=>{const g=document.createElementNS('http://www.w3.org/2000/svg','g');g.classList.add('station',s.level);if([0,1,3,6].includes(i))g.classList.add('interchange');g.dataset.index=i;g.setAttribute('transform',`translate(${s.x} ${s.y})`);g.innerHTML='<circle class="halo" r="17"/><circle class="node" r="7"/><circle class="core" r="2"/>';g.addEventListener('click',()=>selectStation(i));stationLayer.appendChild(g)});

const busLayer=document.querySelector('#busStops');
busStops.forEach((s,i)=>{const g=document.createElementNS('http://www.w3.org/2000/svg','g');g.classList.add('bus-stop',s.level);if([0,1,2,4].includes(i))g.classList.add('interchange');g.dataset.index=i;g.setAttribute('transform',`translate(${s.x} ${s.y})`);g.innerHTML='<rect class="bus-halo" x="-15" y="-15" width="30" height="30" rx="8"/><rect class="bus-node" x="-6" y="-6" width="12" height="12" rx="3"/><circle class="core" r="2"/>';g.addEventListener('click',()=>selectStation(i,'bus'));busLayer.appendChild(g)});

function selectStation(index,type='metro'){const source=type==='bus'?busStops:stations;const s=source[index];document.querySelectorAll('.station,.bus-stop').forEach(n=>n.classList.remove('selected'));document.querySelectorAll(type==='bus'?'.bus-stop':'.station')[index]?.classList.add('selected');const pop=document.querySelector('#stationPopover');const riskBadge=document.querySelector('#popRisk');document.querySelector('#popLine').textContent=type==='bus'?s.line:s.line+' LINE';document.querySelector('#popName').textContent=s.name;document.querySelector('#popMeta').textContent=s.meta||(type==='bus'?'Bus interchange':'Interchange · 2 platforms');riskBadge.textContent=s.level==='critical'?'CRITICAL':s.level==='packed'?'VERY CROWDED':s.level.toUpperCase();riskBadge.className=`pop-risk-${s.level}`;document.querySelector('#popCrowd').textContent=s.crowd+'%';document.querySelector('#crowdBar').style.width=s.crowd+'%';document.querySelector('#crowdBar').className=s.level;document.querySelector('#popNow').textContent=s.now;document.querySelector('#popFuture').textContent=s.future;document.querySelector('#popWait').textContent=s.wait;pop.classList.add('open')}

const watchData=[{name:'Rajiv Chowk',line:'Blue · Yellow',risk:94,delta:'+18%',time:'18 min'},{name:'Kashmere Gate',line:'Yellow · Violet',risk:87,delta:'+12%',time:'24 min'},{name:'New Delhi',line:'Yellow · Airport',risk:79,delta:'+9%',time:'31 min'},{name:'Central Secretariat',line:'Yellow · Violet',risk:74,delta:'+7%',time:'38 min'}];
const busWatch=[{name:'ISBT Kashmere Gate',line:'Bus 729 · 753',risk:91,delta:'+16%',time:'14 min',index:0},{name:'Anand Vihar ISBT',line:'Bus 543 · 740',risk:88,delta:'+14%',time:'22 min',index:4},{name:'Connaught Place',line:'Bus 522 · 894',risk:83,delta:'+11%',time:'29 min',index:1},{name:'AIIMS',line:'Bus 534 · 615',risk:76,delta:'+8%',time:'35 min',index:2}];
const combinedWatch=[{name:'Kashmere Gate Hub',line:'Metro + Bus interchange',risk:97,delta:'+21%',time:'12 min',index:1,type:'metro'},{name:'Rajiv Chowk / CP',line:'Metro + Bus interchange',risk:95,delta:'+19%',time:'17 min',index:0,type:'metro'},{name:'Anand Vihar Hub',line:'Metro + Interstate bus',risk:89,delta:'+15%',time:'23 min',index:4,type:'bus'},{name:'AIIMS Corridor',line:'Metro + Bus transfer',risk:81,delta:'+10%',time:'31 min',index:2,type:'bus'}];
let currentNetworkMode='metro';
function renderWatch(multiplier=1){const data=currentNetworkMode==='bus'?busWatch:currentNetworkMode==='combined'?combinedWatch:watchData;document.querySelector('#watchlist').innerHTML=data.map((w,i)=>{const risk=Math.min(99,Math.round(w.risk*multiplier));return `<button class="watch-row" data-station="${w.index??i}" data-type="${w.type||(currentNetworkMode==='bus'?'bus':'metro')}"><span class="risk-num ${risk>89?'critical':risk>78?'packed':'busy'}">${risk}</span><span><b>${w.name}</b><small><i class="line-dot ${currentNetworkMode}"></i>${w.line}</small></span><em>${w.delta}<small>in ${w.time}</small></em><strong>→</strong></button>`}).join('');document.querySelectorAll('.watch-row').forEach(r=>r.addEventListener('click',()=>{selectStation(+r.dataset.station,r.dataset.type);document.querySelector('#transitMap').scrollIntoView({behavior:'smooth',block:'center'})}))}
renderWatch();

const modeContent={
  metro:{icon:'Ⓜ',label:'METRO NETWORK',detail:'286 trains · 94.6% on time',load:'64% avg. load'},
  bus:{icon:'▣',label:'BUS NETWORK',detail:'4,218 buses · 91.2% on time',load:'71% avg. load'},
  combined:{icon:'⌘',label:'MULTIMODAL NETWORK',detail:'4,504 active vehicles · 312 hubs',load:'68% avg. load'}
};
document.querySelectorAll('#networkModes button').forEach(button=>button.addEventListener('click',()=>{
  currentNetworkMode=button.dataset.mode;
  const map=document.querySelector('#transitMap');
  map.classList.remove('mode-metro','mode-bus','mode-combined');
  map.classList.add(`mode-${currentNetworkMode}`);
  document.querySelector('#stationPopover').classList.remove('open');
  document.querySelectorAll('.station,.bus-stop').forEach(node=>node.classList.remove('selected'));
  const content=modeContent[currentNetworkMode];
  document.querySelector('#modeSummary').innerHTML=`<i>${content.icon}</i><div><span>${content.label}</span><b>${content.detail}</b></div><em>${content.load}</em>`;
  renderWatch();
  document.querySelector('.prediction-panel .eyebrow').textContent=currentNetworkMode==='combined'?'MULTIMODAL AI WATCHLIST':`${currentNetworkMode.toUpperCase()} AI WATCHLIST`;
}));

const actions=[{icon:'↗',title:'Add 2 trains on Yellow Line',meta:'Reduces projected load by 14%',type:'CAPACITY'},{icon:'♙',title:'Deploy marshals at Rajiv Chowk',meta:'Recommended before 18:25',type:'STAFFING'},{icon:'⌁',title:'Issue alternate-route advisory',meta:'Potentially redirects 3,200 riders',type:'PASSENGER INFO'}];
document.querySelector('#actionsList').innerHTML=actions.map((a,i)=>`<div class="action-row"><i>${a.icon}</i><span><b>${a.title}</b><small>${a.meta}</small></span><em>${a.type}</em><button data-action="${i}">Review</button></div>`).join('');

const routes=[{name:'Blue Line',color:'#3b82f6',from:'Dwarka Sec 21 → Noida Electronic City',load:81,next:92,reliability:'96.1%',status:'High demand'},{name:'Yellow Line',color:'#f5c94a',from:'Samaypur Badli → Millennium City',load:88,next:97,reliability:'94.8%',status:'Critical soon'},{name:'Magenta Line',color:'#e653a8',from:'Janakpuri West → Botanical Garden',load:63,next:71,reliability:'97.2%',status:'Stable'},{name:'Violet Line',color:'#8b5cf6',from:'Kashmere Gate → Raja Nahar Singh',load:69,next:78,reliability:'95.4%',status:'Watching'},{name:'Airport Express',color:'#f59e0b',from:'New Delhi → Yashobhoomi Dwarka',load:38,next:44,reliability:'98.6%',status:'Comfortable'}];
document.querySelector('#routeRows').innerHTML=routes.map(r=>`<button class="route-row"><span><i style="background:${r.color}"></i><b>${r.name}</b><small>${r.from}</small></span><span><b>${r.load}%</b><i class="loadbar"><em style="width:${r.load}%"></em></i></span><span class="next-load">${r.next}% <small>↑</small></span><span>${r.reliability}</span><span><em class="status ${r.next>90?'danger':r.next>75?'warn':''}">${r.status}</em></span><strong>→</strong></button>`).join('');

const heatTimes=['16:00','16:30','17:00','17:30','18:00','18:30','19:00','19:30'];
document.querySelector('#heatmap').innerHTML=`<div></div>${heatTimes.map(t=>`<span>${t}</span>`).join('')}`+routes.map((r,ri)=>`<b><i style="background:${r.color}"></i>${r.name}</b>${heatTimes.map((_,ti)=>{const v=Math.min(99,35+ri*5+Math.round(Math.sin((ti+ri)*.75)*17)+ti*7);return `<em style="--load:${v}%" title="${v}%"><span>${v}%</span></em>`}).join('')}`).join('');

const activeAlerts=[{level:'critical',title:'Capacity breach predicted',place:'Rajiv Chowk · Platform 2',time:'8 min ago'},{level:'critical',title:'Unusual demand surge',place:'Kashmere Gate · Yellow Line',time:'14 min ago'},{level:'warning',title:'Bus bunching detected',place:'Route 534 · South Extension',time:'21 min ago'},{level:'info',title:'Event-related demand',place:'Central Secretariat',time:'34 min ago'}];
document.querySelector('#alertsList').innerHTML=activeAlerts.map(a=>`<button class="alert-row"><i class="${a.level}">!</i><span><b>${a.title}</b><small>${a.place}</small></span><em>${a.time}</em><strong>→</strong></button>`).join('');

function switchView(view){document.querySelectorAll('.view').forEach(v=>v.classList.toggle('hidden',v.dataset.section!==view));document.querySelectorAll('.nav[data-view]').forEach(n=>n.classList.toggle('active',n.dataset.view===view));window.scrollTo({top:0,behavior:'smooth'})}
document.querySelectorAll('.nav[data-view]').forEach(n=>n.addEventListener('click',()=>switchView(n.dataset.view)));
document.querySelectorAll('.forecast-tabs button').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('.forecast-tabs button').forEach(x=>x.classList.remove('active'));b.classList.add('active');renderWatch(b.dataset.time==='30'?1:b.dataset.time==='60'?1.05:1.09)}));
document.querySelectorAll('.mode-tabs button').forEach(b=>b.addEventListener('click',()=>{b.parentElement.querySelectorAll('button').forEach(x=>x.classList.remove('active'));b.classList.add('active');showToast(`${b.textContent} view selected`)}));
document.querySelectorAll('[data-action]').forEach(b=>b.addEventListener('click',()=>{b.textContent='Approved ✓';b.classList.add('approved');showToast('Intervention added to operations plan')}));
document.querySelector('#closePopover').addEventListener('click',()=>document.querySelector('#stationPopover').classList.remove('open'));
document.querySelector('#stationDetail').addEventListener('click',()=>switchView('forecast'));

const cityBtn=document.querySelector('#cityBtn'),cityMenu=document.querySelector('#cityMenu');cityBtn.addEventListener('click',()=>cityMenu.classList.toggle('open'));document.querySelectorAll('#cityMenu button').forEach(b=>b.addEventListener('click',()=>{document.querySelector('#cityName').textContent=b.dataset.city;cityMenu.classList.remove('open');showToast(`${b.dataset.city} network loaded`)}));
const modal=document.querySelector('#commandModal');function toggleSearch(open){modal.classList.toggle('open',open);if(open)setTimeout(()=>document.querySelector('#commandInput').focus(),100)}document.querySelector('#searchBtn').addEventListener('click',()=>toggleSearch(true));modal.addEventListener('click',e=>{if(e.target===modal)toggleSearch(false)});document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key==='k'){e.preventDefault();toggleSearch(true)}if(e.key==='Escape')toggleSearch(false)});document.querySelectorAll('[data-command]').forEach(b=>b.addEventListener('click',()=>{toggleSearch(false);if(b.dataset.command==='station'){switchView('network');selectStation(0)}else switchView(b.dataset.command)}));
document.querySelector('#generateBtn').addEventListener('click',e=>{e.currentTarget.innerHTML='✓ Brief generated';showToast('Operations brief is ready');setTimeout(()=>e.currentTarget.innerHTML='✦ Generate operations brief',1900)});document.querySelector('#runModel').addEventListener('click',e=>{e.currentTarget.textContent='Running model…';setTimeout(()=>{e.currentTarget.textContent='✓ Model updated';showToast('Latest ticketing data processed')},1100)});document.querySelector('#markRead').addEventListener('click',()=>showToast('All alerts marked as reviewed'));document.querySelector('#executePlan').addEventListener('click',()=>showToast('Response plan sent to operations teams'));document.querySelector('#menuBtn').addEventListener('click',()=>document.querySelector('.sidebar').classList.toggle('mobile-open'));
function showToast(message){const t=document.querySelector('#toast');t.querySelector('span').textContent=message;t.classList.add('show');clearTimeout(window.toastTimer);window.toastTimer=setTimeout(()=>t.classList.remove('show'),2400)}

const simulator=document.querySelector('#simulator');
const simulatorBackdrop=document.querySelector('#simulatorBackdrop');
function toggleSimulator(open){simulator.classList.toggle('open',open);simulatorBackdrop.classList.toggle('open',open)}
document.querySelector('#simulateBtn').addEventListener('click',()=>toggleSimulator(true));
document.querySelector('#closeSimulator').addEventListener('click',()=>toggleSimulator(false));
simulatorBackdrop.addEventListener('click',()=>toggleSimulator(false));

function updateScenario(){
  const attendance=+document.querySelector('#attendanceRange').value;
  const proximity=+document.querySelector('#proximityRange').value;
  const scenario=document.querySelector('#scenarioType').value;
  const base=scenario==='baseline'?55:scenario==='weather'?68:scenario==='disruption'?76:62;
  const load=Math.min(99,Math.round(base+attendance/5000+(10-proximity)*1.2));
  document.querySelector('#attendanceValue').textContent=`${attendance.toLocaleString('en-IN')} people`;
  document.querySelector('#proximityValue').textContent=`${(proximity*.6).toFixed(1)} km`;
  document.querySelector('#scenarioLoad').textContent=`${load}%`;
  document.querySelector('#ringValue').textContent=load;
  document.querySelector('#scenarioChange').textContent=`+${Math.max(0,load-64)}% from baseline`;
  document.querySelector('.scenario-ring').style.background=`conic-gradient(var(--orange) ${load}%,#252b38 0)`;
}
['attendanceRange','proximityRange','scenarioType'].forEach(id=>document.querySelector(`#${id}`).addEventListener('input',updateScenario));
document.querySelectorAll('.affected-lines button').forEach(button=>button.addEventListener('click',()=>button.classList.toggle('selected')));
document.querySelector('#applyScenario').addEventListener('click',()=>{toggleSimulator(false);showToast('Scenario applied to the network digital twin');document.querySelector('.brief-signal b').innerHTML='<i></i> Simulated'});

let forecastProgress=0,forecastTimer;
document.querySelector('#playForecast').addEventListener('click',event=>{
  clearInterval(forecastTimer);forecastProgress=0;event.currentTarget.textContent='❚❚';
  forecastTimer=setInterval(()=>{forecastProgress+=2;document.querySelector('#scrubberFill').style.width=`${forecastProgress}%`;document.querySelector('#scrubberHandle').style.left=`${forecastProgress}%`;document.querySelector('#forecastOffset').textContent=forecastProgress<4?'Now':`+${Math.round(forecastProgress*1.2)} min`;if(forecastProgress>=100){clearInterval(forecastTimer);event.currentTarget.textContent='▶'}},75)
});
document.querySelector('#liveTime').addEventListener('click',()=>{clearInterval(forecastTimer);forecastProgress=0;document.querySelector('#scrubberFill').style.width='0';document.querySelector('#scrubberHandle').style.left='0';document.querySelector('#forecastOffset').textContent='Now';document.querySelector('#playForecast').textContent='▶'});
// #mapClock / #passengerCount were removed from index.html in the React migration —
// LiveMetrics.tsx now owns #reactMapClock / #reactPassengerCount instead.

/* ---- Journey planner: real source -> destination route recommendation, ----
   calling the FastAPI backend's POST /recommend-route. Everything above
   this point in the file is unchanged. */
const ML_BACKEND_URL='http://localhost:8000'; // update once a backend is deployed publicly

const JOURNEY_LINE_COLORS={'Blue Line':'#3b82f6','Yellow Line':'#f5c94a','Violet Line':'#8b5cf6','Magenta Line':'#e653a8','Airport Express':'#f59e0b'};

const sourceSelect=document.querySelector('#sourceStation');
const destSelect=document.querySelector('#destStation');
const journeyResultsTable=document.querySelector('#journeyResultsTable');
const journeyRows=document.querySelector('#journeyRows');
const journeyNote=document.querySelector('#journeyNote');
const journeyNoteIcon=document.querySelector('#journeyNoteIcon');
const journeyNoteTitle=document.querySelector('#journeyNoteTitle');
const journeyNoteText=document.querySelector('#journeyNoteText');
const findRouteBtn=document.querySelector('#findRouteBtn');

function showJourneyNote(icon,title,text){journeyNote.classList.remove('hidden');journeyNoteIcon.textContent=icon;journeyNoteTitle.textContent=title;journeyNoteText.textContent=text}
function hideJourneyNote(){journeyNote.classList.add('hidden')}

async function loadStations(){
  try{
    const res=await fetch(`${ML_BACKEND_URL}/stations`);
    if(!res.ok) throw new Error(`status ${res.status}`);
    const list=await res.json();
    const options=list.map(s=>`<option value="${s.id}">${s.name}</option>`).join('');
    sourceSelect.innerHTML=options;
    destSelect.innerHTML=options;
    if(list.length>1) destSelect.value=list[1].id;
  }catch(err){
    sourceSelect.innerHTML='<option>Backend unavailable</option>';
    destSelect.innerHTML='<option>Backend unavailable</option>';
    findRouteBtn.disabled=true;
    showJourneyNote('!','Backend unavailable',`Couldn't load stations from ${ML_BACKEND_URL} — start the FastAPI backend (uvicorn app.main:app --port 8000) to use the journey planner.`);
  }
}
loadStations();

const JOURNEY_POLL_INTERVAL_MS=5000;
let journeyPollTimer=null;

function stopJourneyPolling(){
  if(journeyPollTimer){clearInterval(journeyPollTimer);journeyPollTimer=null}
}

function renderJourneyResults(data){
  journeyResultsTable.classList.remove('hidden');
  journeyRows.innerHTML=data.evaluated_routes.map(r=>{
    const isRecommended=r.route_id===data.recommended_route_id;
    const color=JOURNEY_LINE_COLORS[r.route_name.split(' + ')[0]]||'#8390a2';
    const statusClass=r.crowding_level==='HIGH'?'danger':r.crowding_level==='MEDIUM'?'warn':'';
    const currentPct=Math.round((r.current_data.current_passenger_count/r.current_data.vehicle_capacity)*100);
    const subtitle=(r.transfer_station?`Transfer at ${r.transfer_station}`:'Direct')+(isRecommended?' · Recommended':'');
    return `<button class="route-row"><span><i style="background:${color}"></i><b>${r.route_name}</b><small>${subtitle}</small></span><span><b>${r.current_data.current_passenger_count}/${r.current_data.vehicle_capacity}</b><i class="loadbar"><em style="width:${currentPct}%"></em></i></span><span class="next-load">${r.predicted_occupancy_percentage}%</span><span>${r.estimated_travel_time_minutes} min</span><span><em class="status ${statusClass}">${r.crowding_level}</em></span><strong>${isRecommended?'★':'→'}</strong></button>`;
  }).join('');
  showJourneyNote('✦','Recommended route',data.recommendation_reason+' · Live, refreshes every 5s');
}

function buildDepartureTime(){
  const timeValue=document.querySelector('#departTime').value;
  if(!timeValue) return undefined;
  const [h,m]=timeValue.split(':');
  const d=new Date();
  d.setHours(+h,+m,0,0);
  return d.toISOString();
}

async function searchRoute(source,destination,{silent=false}={}){
  if(!silent){
    findRouteBtn.textContent='Finding routes…';
    findRouteBtn.disabled=true;
  }
  try{
    const departure_time=buildDepartureTime();
    const res=await fetch(`${ML_BACKEND_URL}/recommend-route`,{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({source_station:source,destination_station:destination,...(departure_time?{departure_time}:{})})
    });
    const data=await res.json();
    if(!res.ok){
      showJourneyNote('!','Could not find a route',data.detail?JSON.stringify(data.detail):`Request failed with status ${res.status}`);
      journeyResultsTable.classList.add('hidden');
      stopJourneyPolling();
      return;
    }
    renderJourneyResults(data);
    if(!journeyPollTimer){
      journeyPollTimer=setInterval(()=>searchRoute(source,destination,{silent:true}),JOURNEY_POLL_INTERVAL_MS);
    }
  }catch(err){
    showJourneyNote('!','Backend unavailable',`Couldn't reach ${ML_BACKEND_URL} — make sure the FastAPI backend is running.`);
    journeyResultsTable.classList.add('hidden');
    stopJourneyPolling();
  }finally{
    if(!silent){
      findRouteBtn.textContent='Find best route';
      findRouteBtn.disabled=false;
    }
  }
}

findRouteBtn.addEventListener('click',()=>{
  const source=sourceSelect.value;
  const destination=destSelect.value;
  stopJourneyPolling();
  journeyResultsTable.classList.add('hidden');
  hideJourneyNote();
  if(!source||!destination){showJourneyNote('!','Select both stations','Pick a source and destination to find a route.');return}
  if(source===destination){showJourneyNote('!','Pick two different stations','Source and destination must be different.');return}
  searchRoute(source,destination);
});

// stop polling once the user leaves the Routes view, resume when they come back
document.querySelectorAll('.nav[data-view]').forEach(n=>n.addEventListener('click',()=>{
  if(n.dataset.view!=='routes') stopJourneyPolling();
}));
