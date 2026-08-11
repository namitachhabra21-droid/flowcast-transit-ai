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
stations.forEach((s,i)=>{const g=document.createElementNS('http://www.w3.org/2000/svg','g');g.classList.add('station',s.level);if([0,1,3,6].includes(i))g.classList.add('interchange');g.dataset.index=i;g.setAttribute('transform',`translate(${s.x} ${s.y})`);g.innerHTML=`<circle class="halo" r="17"/><circle class="node" r="7"/><circle class="core" r="2"/><text class="station-label" x="12" y="-10">${s.name}</text>`;g.addEventListener('click',()=>selectStation(i));stationLayer.appendChild(g)});

const busLayer=document.querySelector('#busStops');
busStops.forEach((s,i)=>{const g=document.createElementNS('http://www.w3.org/2000/svg','g');g.classList.add('bus-stop',s.level);if([0,1,2,4].includes(i))g.classList.add('interchange');g.dataset.index=i;g.setAttribute('transform',`translate(${s.x} ${s.y})`);g.innerHTML=`<rect class="bus-halo" x="-15" y="-15" width="30" height="30" rx="8"/><rect class="bus-node" x="-6" y="-6" width="12" height="12" rx="3"/><circle class="core" r="2"/><text class="station-label bus-label" x="12" y="-10">${s.name}</text>`;g.addEventListener('click',()=>selectStation(i,'bus'));busLayer.appendChild(g)});

let selectedStation=null;
function selectStation(index,type='metro'){selectedStation={index,type};const source=type==='bus'?busStops:stations;const s=source[index];document.querySelectorAll('.station,.bus-stop').forEach(n=>n.classList.remove('selected'));document.querySelectorAll(type==='bus'?'.bus-stop':'.station')[index]?.classList.add('selected');const pop=document.querySelector('#stationPopover');const riskBadge=document.querySelector('#popRisk');document.querySelector('#popLine').textContent=type==='bus'?s.line:s.line+' LINE';document.querySelector('#popName').textContent=s.name;document.querySelector('#popMeta').textContent=s.meta||(type==='bus'?'Bus interchange':'Interchange · 2 platforms');riskBadge.textContent=s.level==='critical'?'CRITICAL':s.level==='packed'?'VERY CROWDED':s.level.toUpperCase();riskBadge.className=`pop-risk-${s.level}`;document.querySelector('#popCrowd').textContent=s.crowd+'%';document.querySelector('#crowdBar').style.width=s.crowd+'%';document.querySelector('#crowdBar').className=s.level;document.querySelector('#popNow').textContent=s.now;document.querySelector('#popFuture').textContent=s.future;document.querySelector('#popWait').textContent=s.wait;pop.classList.add('open')}

let currentNetworkMode='metro';
function estimateWaitTime(crowd){return `${Math.max(3,Math.round(45-crowd*0.35))} min`}
function watchSourceForMode(){
  if(currentNetworkMode==='bus') return busStops.map((s,i)=>({...s,_index:i,_type:'bus'}));
  if(currentNetworkMode==='combined') return [...stations.map((s,i)=>({...s,_index:i,_type:'metro'})),...busStops.map((s,i)=>({...s,_index:i,_type:'bus'}))];
  return stations.map((s,i)=>({...s,_index:i,_type:'metro'}));
}
/* Watchlist is derived live from the same stations/busStops the map reads —
   one source of truth, so the map dot, popover and this list can never
   show contradictory numbers for the same station. */
function renderWatch(multiplier=1){
  const top=watchSourceForMode().sort((a,b)=>b.crowd-a.crowd).slice(0,4);
  document.querySelector('#watchlist').innerHTML=top.map(s=>{
    const risk=Math.min(99,Math.round(s.crowd*multiplier));
    const delta=s._delta||0;
    return `<button class="watch-row" data-station="${s._index}" data-type="${s._type}"><span class="risk-num ${risk>88?'critical':risk>75?'packed':'busy'}">${risk}</span><span><b>${s.name}</b><small><i class="line-dot ${s._type==='bus'?'bus':''}"></i>${s.line}</small></span><em>${delta>=0?'+':''}${delta}%<small>in ${estimateWaitTime(s.crowd)}</small></em><strong>→</strong></button>`;
  }).join('');
  document.querySelectorAll('.watch-row').forEach(r=>r.addEventListener('click',()=>{selectStation(+r.dataset.station,r.dataset.type);document.querySelector('#transitMap').scrollIntoView({behavior:'smooth',block:'center'})}));
}
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
function renderRoutes(){const routeRows=document.querySelector('#routeRows');routeRows.innerHTML=routes.map((r,i)=>`<button class="route-row" data-route-index="${i}"><span><i style="background:${r.color}"></i><b>${r.name}</b><small>${r.from}</small></span><span><b>${r.load}%</b><i class="loadbar"><em style="width:${r.load}%"></em></i></span><span class="next-load">${r.next}% <small>↑</small></span><span>${r.reliability}</span><span><em class="status ${r.next>90?'danger':r.next>75?'warn':''}">${r.status}</em></span><strong>→</strong></button>`).join('');routeRows.querySelectorAll('[data-route-index]').forEach(row=>row.addEventListener('click',()=>{const r=routes[+row.dataset.routeIndex];showToast(`${r.name}: ${r.next}% predicted load · ${r.reliability} reliability`)}))}
renderRoutes();

const heatTimes=['16:00','16:30','17:00','17:30','18:00','18:30','19:00','19:30'];
let heatmapSeed=0;

function renderHeatmap(modeShift=0){
  let peak={value:-1,route:routes[0],timeIndex:0};
  const body=routes.map((r,ri)=>{
    const cells=heatTimes.map((t,ti)=>{
      const base=35+ri*5+Math.round(Math.sin((ti+ri+heatmapSeed)*.75)*17)+ti*7;
      const v=Math.max(12,Math.min(99,base+modeShift));
      if(v>peak.value)peak={value:v,route:r,timeIndex:ti};
      return `<em style="--load:${v}%" title="${r.name} · ${t} · ${v}%" data-route="${ri}" data-time="${ti}" data-value="${v}"><span>${v}%</span></em>`;
    }).join('');
    return `<b><i style="background:${r.color}"></i>${r.name}</b>${cells}`;
  }).join('');
  document.querySelector('#heatmap').innerHTML=`<div></div>${heatTimes.map(t=>`<span>${t}</span>`).join('')}`+body;
  document.querySelector('#heatmapDetail').textContent='Hover or tap a cell for details';

  document.querySelectorAll('#heatmap em').forEach(cell=>cell.addEventListener('click',()=>{
    document.querySelectorAll('#heatmap em.selected').forEach(c=>c.classList.remove('selected'));
    cell.classList.add('selected');
    const ri=+cell.dataset.route,ti=+cell.dataset.time,v=cell.dataset.value;
    const level=v>85?'Critical':v>70?'Very crowded':v>45?'Busy':'Comfortable';
    document.querySelector('#heatmapDetail').textContent=`${routes[ri].name} · ${heatTimes[ti]} · ${v}% predicted (${level})`;
  }));

  const busiestStation=[...stations].sort((a,b)=>b.crowd-a.crowd)[0];
  document.querySelector('#peakTime').textContent=heatTimes[peak.timeIndex];
  document.querySelector('#peakRing').style.background=`conic-gradient(var(--orange) ${peak.value}%,#e8ccc0 0)`;
  document.querySelector('#peakRing span').innerHTML=`${peak.value}<small>%</small>`;
  document.querySelector('#peakLine').textContent=peak.route.name;
  document.querySelector('#peakStation').textContent=busiestStation.name;
  document.querySelector('#peakRiders').textContent=Math.round(peak.value*3120).toLocaleString('en-IN');
}
renderHeatmap();

const activeAlerts=[{level:'critical',title:'Capacity breach predicted',place:'Rajiv Chowk · Platform 2',time:'8 min ago',load:'112%',riders:'8,420'},{level:'critical',title:'Unusual demand surge',place:'Kashmere Gate · Yellow Line',time:'14 min ago',load:'104%',riders:'6,180'},{level:'warning',title:'Bus bunching detected',place:'Route 534 · South Extension',time:'21 min ago',load:'88%',riders:'2,940'},{level:'info',title:'Event-related demand',place:'Central Secretariat',time:'34 min ago',load:'79%',riders:'3,610'}];
function renderAlerts(filter='all'){const visible=activeAlerts.filter(a=>filter==='all'||filter==='critical'&&a.level==='critical'||filter==='watching'&&a.level!=='critical');document.querySelector('#alertsList').innerHTML=visible.map(a=>`<button class="alert-row" data-alert-index="${activeAlerts.indexOf(a)}"><i class="${a.level}">${a.level==='info'?'i':'!'}</i><span><b>${a.title}</b><small>${a.place}</small></span><em>${a.time}</em><strong>→</strong></button>`).join('');document.querySelectorAll('[data-alert-index]').forEach(row=>row.addEventListener('click',()=>selectAlert(+row.dataset.alertIndex)))}
function selectAlert(index){const a=activeAlerts[index];const detail=document.querySelector('.alert-detail');detail.querySelector('.critical-pill').textContent=`${a.level.toUpperCase()} · ${a.time.toUpperCase()}`;detail.querySelector('h2').textContent=a.title;detail.querySelector('p').textContent=`${a.place} is forecast to exceed its expected operating threshold. Review and execute the recommended response below.`;detail.querySelectorAll('.alert-impact b')[0].textContent=a.load;detail.querySelectorAll('.alert-impact b')[1].textContent=a.riders;detail.querySelectorAll('input').forEach(input=>input.checked=false)}
renderAlerts();

function switchView(view){document.querySelectorAll('.view').forEach(v=>v.classList.toggle('hidden',v.dataset.section!==view));document.querySelectorAll('.nav[data-view]').forEach(n=>n.classList.toggle('active',n.dataset.view===view));window.scrollTo({top:0,behavior:'smooth'})}
document.querySelectorAll('.nav[data-view]').forEach(n=>n.addEventListener('click',()=>switchView(n.dataset.view)));
document.querySelectorAll('.forecast-tabs button').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('.forecast-tabs button').forEach(x=>x.classList.remove('active'));b.classList.add('active');renderWatch(b.dataset.time==='30'?1:b.dataset.time==='60'?1.05:1.09)}));
document.querySelectorAll('.mode-tabs button').forEach(b=>b.addEventListener('click',()=>{b.parentElement.querySelectorAll('button').forEach(x=>x.classList.remove('active'));b.classList.add('active');showToast(`${b.textContent} view selected`)}));
document.querySelectorAll('[data-action]').forEach(b=>b.addEventListener('click',()=>{b.textContent='Approved ✓';b.classList.add('approved');showToast('Intervention added to operations plan')}));
document.querySelector('#closePopover').addEventListener('click',()=>document.querySelector('#stationPopover').classList.remove('open'));
document.querySelector('#stationDetail').addEventListener('click',()=>switchView('forecast'));

const modal=document.querySelector('#commandModal');function toggleSearch(open){modal.classList.toggle('open',open);if(open)setTimeout(()=>document.querySelector('#commandInput').focus(),100)}modal.addEventListener('click',e=>{if(e.target===modal)toggleSearch(false)});document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key==='k'){e.preventDefault();toggleSearch(true)}if(e.key==='Escape')toggleSearch(false)});document.querySelectorAll('[data-command]').forEach(b=>b.addEventListener('click',()=>{toggleSearch(false);if(b.dataset.command==='station'){switchView('network');selectStation(0)}else switchView(b.dataset.command)}));
document.querySelector('#generateBtn').addEventListener('click',e=>{e.currentTarget.innerHTML='✓ Brief generated';showToast('Operations brief is ready');setTimeout(()=>e.currentTarget.innerHTML='✦ Generate operations brief',1900)});
document.querySelector('#runModel').addEventListener('click',e=>{
  const btn=e.currentTarget,icon=document.querySelector('#runModelIcon');
  btn.disabled=true;icon.classList.add('spinning');
  document.querySelectorAll('#heatmap em').forEach(cell=>cell.classList.add('refreshing'));
  setTimeout(()=>{
    heatmapSeed+=1+Math.random()*3;
    renderHeatmap();
    icon.classList.remove('spinning');btn.disabled=false;
    document.querySelector('#modelConfidence').textContent=`${(93+Math.random()*2).toFixed(1)}%`;
    showToast('Latest ticketing data processed · forecast updated');
  },900);
});
function showToast(message){const t=document.querySelector('#toast');t.querySelector('span').textContent=message;t.classList.add('show');clearTimeout(window.toastTimer);window.toastTimer=setTimeout(()=>t.classList.remove('show'),2400)}

/* Complete the remaining dashboard controls with useful demo behavior. */
document.querySelector('#viewAllForecastBtn').addEventListener('click',()=>switchView('forecast'));
const MONTH_SHORT=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function formatDatePill(date){return `${date.getDate()} ${MONTH_SHORT[date.getMonth()]}`}
let dateBtnShowingTomorrow=false;
document.querySelector('#dateBtn').addEventListener('click',e=>{
  dateBtnShowingTomorrow=!dateBtnShowingTomorrow;
  const target=new Date();
  if(dateBtnShowingTomorrow) target.setDate(target.getDate()+1);
  e.currentTarget.innerHTML=`${dateBtnShowingTomorrow?'Tomorrow':'Today'}, ${formatDatePill(target)} <span>⌄</span>`;
  showToast('Dashboard timeline updated');
});
document.querySelector('#dateBtn').innerHTML=`Today, ${formatDatePill(new Date())} <span>⌄</span>`;

/* Greeting on the Network page's header, driven by the visitor's real local
   time instead of a hardcoded "Good morning." — updated once on load and
   again on every livePulse() tick so a long-open tab still reflects the
   current hour. */
function updateGreeting(){
  const heading=document.querySelector('#greetingHeading');
  if(!heading) return;
  const hour=new Date().getHours();
  const greeting=hour<5?'Good night':hour<12?'Good morning':hour<17?'Good afternoon':hour<21?'Good evening':'Good night';
  heading.textContent=`${greeting}.`;
}
updateGreeting();

let mapScale=1;
function setMapScale(next){mapScale=Math.max(.8,Math.min(1.45,next));document.querySelector('#transitMap>svg').style.transform=`scale(${mapScale})`;showToast(`Map zoom ${Math.round(mapScale*100)}%`)}
document.querySelector('#zoomInBtn').addEventListener('click',()=>setMapScale(mapScale+.1));
document.querySelector('#zoomOutBtn').addEventListener('click',()=>setMapScale(mapScale-.1));
document.querySelector('#locateBtn').addEventListener('click',()=>{setMapScale(1);selectStation(0);showToast('Map centered on the busiest interchange')});
document.querySelector('#mapOptionsBtn').addEventListener('click',()=>{document.querySelector('#transitMap').classList.toggle('high-contrast');showToast('Map contrast toggled')});
const lineFilterBtn=document.querySelector('.line-filter button');
const lineChoices=['All lines','Blue Line','Yellow Line','Airport Express'];let lineChoiceIndex=0;
lineFilterBtn.addEventListener('click',()=>{lineChoiceIndex=(lineChoiceIndex+1)%lineChoices.length;lineFilterBtn.textContent=`${lineChoices[lineChoiceIndex]} ⌄`;document.querySelector('.line-filter i').style.background=routes[Math.max(0,lineChoiceIndex-1)]?.color||'var(--purple)';showToast(`${lineChoices[lineChoiceIndex]} demand displayed`)});

document.querySelectorAll('#forecastControls select,#forecastControls input').forEach(control=>control.addEventListener('change',()=>{
  const mode=document.querySelector('#forecastMode').value;
  const horizon=document.querySelector('#forecastHorizon').value;
  const shift=mode==='Bus'?8:mode==='Metro'?3:0;
  renderHeatmap(shift);
  document.querySelector('#modelConfidence').textContent=mode==='All transit'?'94.6%':'93.8%';
  showToast(`${mode} forecast updated · ${horizon}`);
}));

document.querySelector('#addCorridorBtn').addEventListener('click',()=>{const name=`Special Corridor ${routes.length-4}`;routes.push({name,color:'#56ccf2',from:'New Delhi → Central Secretariat',load:52,next:66,reliability:'95.0%',status:'Monitoring'});renderRoutes();showToast(`${name} added to monitoring`)});

document.querySelectorAll('.alerts-list .mode-tabs button').forEach(button=>button.addEventListener('click',()=>renderAlerts(button.textContent.trim().toLowerCase())));
document.querySelector('#markRead').addEventListener('click',event=>{document.querySelectorAll('.alert-row').forEach(row=>row.classList.add('reviewed'));event.currentTarget.textContent='✓ All reviewed'});
document.querySelector('#executePlan').addEventListener('click',()=>{const checked=[...document.querySelectorAll('.alert-detail input:checked')];if(!checked.length){showToast('Select at least one response action first');return}showToast(`${checked.length} response action${checked.length>1?'s':''} dispatched`)});

const commandInput=document.querySelector('#commandInput');
commandInput.addEventListener('input',()=>{const query=commandInput.value.toLowerCase();document.querySelectorAll('#commandModal [data-command]').forEach(item=>item.classList.toggle('hidden',!item.textContent.toLowerCase().includes(query)))});
commandInput.addEventListener('keydown',event=>{if(event.key==='Enter'){const first=document.querySelector('#commandModal [data-command]:not(.hidden)');if(first)first.click()}});

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
  document.querySelector('.scenario-ring').style.background=`conic-gradient(var(--orange) ${load}%,#e8ccc0 0)`;
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
const ML_BACKEND_URL=location.hostname==='localhost'||location.hostname==='127.0.0.1'
  ?'http://localhost:8000'
  :'https://transit-crowding-backend.onrender.com';

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
const swapRouteBtn=document.querySelector('#swapRouteBtn');
const localStations=[
  {id:'rajiv-chowk',name:'Rajiv Chowk'},{id:'kashmere-gate',name:'Kashmere Gate'},{id:'new-delhi',name:'New Delhi'},{id:'central-secretariat',name:'Central Secretariat'},{id:'hauz-khas',name:'Hauz Khas'},{id:'botanical-garden',name:'Botanical Garden'},{id:'dwarka-sector-21',name:'Dwarka Sector 21'},{id:'noida-sector-18',name:'Noida Sector 18'},{id:'igi-airport',name:'IGI Airport'}
];

swapRouteBtn.addEventListener('click',()=>{
  const source=sourceSelect.value;
  sourceSelect.value=destSelect.value;
  destSelect.value=source;
  runJourneySearch();
});

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
    const options=localStations.map(s=>`<option value="${s.id}">${s.name}</option>`).join('');
    sourceSelect.innerHTML=options;
    destSelect.innerHTML=options;
    destSelect.value=localStations[1].id;
    showJourneyNote('✦','Demo prediction ready','Using the built-in Delhi transit model. Connect the FastAPI service for live ticketing predictions.');
  }
}
loadStations();
// Keep a useful sample prediction visible from the moment the live demo opens.
renderLocalJourney(localStations[0].id,localStations[1].id);

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
    const confidencePct=r.confidence!=null?Math.round(r.confidence*100):null;
    const subtitle=(r.transfer_station?`Transfer at ${r.transfer_station}`:'Direct')+(isRecommended?' · Recommended':'')+(confidencePct!=null?` · ${confidencePct}% model confidence`:'');
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

let journeySearchGeneration=0;

async function searchRoute(source,destination,{silent=false}={}){
  const generation=++journeySearchGeneration;
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
    // A newer search (different stations, e.g. the user switched again while
    // this request was in flight) has already started — this response is
    // stale, don't let it clobber what's now on screen.
    if(generation!==journeySearchGeneration) return;
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
    if(generation!==journeySearchGeneration) return;
    renderLocalJourney(source,destination);
    stopJourneyPolling();
  }finally{
    if(!silent){
      findRouteBtn.textContent='Find best route';
      findRouteBtn.disabled=false;
    }
  }
}

function renderLocalJourney(source,destination){
  const from=localStations.find(s=>s.id===source)?.name||source;
  const to=localStations.find(s=>s.id===destination)?.name||destination;
  const seed=(source.length+destination.length)%8;
  const options=[
    {name:'Blue Line',color:'#3b82f6',load:54+seed,time:24+seed,status:'LOW',note:'Direct · Recommended'},
    {name:'Yellow + Violet',color:'#f5c94a',load:70+seed,time:29+seed,status:'MEDIUM',note:'Transfer at Central Secretariat'},
    {name:'Bus + Metro',color:'#29d9c4',load:81+seed,time:35+seed,status:'HIGH',note:'Transfer at Connaught Place'}
  ];
  journeyResultsTable.classList.remove('hidden');
  journeyRows.innerHTML=options.map((r,i)=>`<button class="route-row"><span><i style="background:${r.color}"></i><b>${r.name}</b><small>${r.note}</small></span><span><b>${r.load-6}%</b><i class="loadbar"><em style="width:${r.load-6}%"></em></i></span><span class="next-load">${r.load}%</span><span>${r.time} min</span><span><em class="status ${r.status==='HIGH'?'danger':r.status==='MEDIUM'?'warn':''}">${r.status}</em></span><strong>${i===0?'★':'→'}</strong></button>`).join('');
  showJourneyNote('✦','Best route found',`${from} → ${to}: Blue Line is fastest and ${options[1].load-options[0].load}% less crowded than the next option · Demo prediction`);
}

function runJourneySearch(){
  const source=sourceSelect.value;
  const destination=destSelect.value;
  stopJourneyPolling();
  journeyResultsTable.classList.add('hidden');
  hideJourneyNote();
  if(!source||!destination){showJourneyNote('!','Select both stations','Pick a source and destination to find a route.');return}
  if(source===destination){showJourneyNote('!','Pick two different stations','Source and destination must be different.');return}
  searchRoute(source,destination);
}
findRouteBtn.addEventListener('click',runJourneySearch);
// Re-search automatically when either station changes — previously only the
// explicit "Find best route" click did this, so picking a new combination
// from the dropdowns (or swapping) left the *previous* combination's stale
// results on screen with nothing indicating they hadn't updated.
sourceSelect.addEventListener('change',runJourneySearch);
destSelect.addEventListener('change',runJourneySearch);

// The planner lives on Network, so stop refreshing after the user leaves that view.
document.querySelectorAll('.nav[data-view]').forEach(n=>n.addEventListener('click',()=>{
  if(n.dataset.view!=='network') stopJourneyPolling();
}));

/* ---- Live data engine: periodic realistic drift across stations, buses ----
   and routes, driving the map, watchlist, summary stats, route table and
   an open popover from ONE source of truth (stations/busStops/routes) so
   nothing can show contradictory numbers. Everything above reads from the
   same arrays this mutates. */
function driftCrowd(current){return Math.max(8,Math.min(99,current+Math.round((Math.random()-0.5)*12)))}
function levelFor(crowd){if(crowd>88)return'critical';if(crowd>75)return'packed';if(crowd>45)return'busy';return'quiet'}

function driftStopList(list,layer,scale){
  list.forEach((s,i)=>{
    const prev=s.crowd;
    s.crowd=driftCrowd(s.crowd);
    s._delta=prev?Math.round(((s.crowd-prev)/prev)*100):0;
    s.level=levelFor(s.crowd);
    const base=s.crowd*scale;
    s.now=`${(base/1000).toFixed(1)}k`;
    s.future=`${(base*1.18/1000).toFixed(1)}k`;
    s.wait=estimateWaitTime(s.crowd);
    const node=layer.children[i];
    if(node){node.classList.remove('quiet','busy','packed','critical');node.classList.add(s.level)}
  });
}

function refreshPopoverIfOpen(){
  const pop=document.querySelector('#stationPopover');
  if(!selectedStation||!pop.classList.contains('open')) return;
  const s=(selectedStation.type==='bus'?busStops:stations)[selectedStation.index];
  const riskBadge=document.querySelector('#popRisk');
  riskBadge.textContent=s.level==='critical'?'CRITICAL':s.level==='packed'?'VERY CROWDED':s.level.toUpperCase();
  riskBadge.className=`pop-risk-${s.level}`;
  document.querySelector('#popCrowd').textContent=s.crowd+'%';
  document.querySelector('#crowdBar').style.width=s.crowd+'%';
  document.querySelector('#crowdBar').className=s.level;
  document.querySelector('#popNow').textContent=s.now;
  document.querySelector('#popFuture').textContent=s.future;
  document.querySelector('#popWait').textContent=s.wait;
}

function refreshSummaryStats(){
  const avg=Math.round(stations.reduce((sum,s)=>sum+s.crowd,0)/stations.length);
  const highRisk=stations.filter(s=>s.level==='packed'||s.level==='critical').length;
  const critical=stations.filter(s=>s.level==='critical').length;
  document.querySelector('#avgCrowdLevel').textContent=avg+'%';
  document.querySelector('#avgCrowdNote').textContent=avg>72?'Elevated across network':avg>45?'Moderate across network':'Comfortable across network';
  const ring=document.querySelector('#avgCrowdRing');
  ring.style.background=`conic-gradient(var(--purple) ${avg}%,#e4ecf5 0)`;
  ring.querySelector('b').textContent=avg;
  document.querySelector('#highRiskCount').textContent=highRisk;
  document.querySelector('#highRiskNote').textContent=`${critical} critical in next 30 min`;
}

function refreshModeSummary(){
  const avg=Math.round(stations.reduce((sum,s)=>sum+s.crowd,0)/stations.length);
  const busAvg=Math.round(busStops.reduce((sum,s)=>sum+s.crowd,0)/busStops.length);
  modeContent.metro.load=`${avg}% avg. load`;
  modeContent.bus.load=`${busAvg}% avg. load`;
  modeContent.combined.load=`${Math.round((avg+busAvg)/2)}% avg. load`;
  const content=modeContent[currentNetworkMode];
  document.querySelector('#modeSummary').innerHTML=`<i>${content.icon}</i><div><span>${content.label}</span><b>${content.detail}</b></div><em>${content.load}</em>`;
}

function refreshRoutesLive(){
  routes.forEach(r=>{
    r.load=driftCrowd(r.load);
    r.next=Math.max(20,Math.min(99,r.load+Math.round((Math.random()-0.3)*14)));
    r.status=r.next>90?'Critical soon':r.next>80?'High demand':r.next>65?'Watching':r.next>48?'Stable':'Comfortable';
  });
  renderRoutes();
}

function livePulse(){
  driftStopList(stations,stationLayer,136);
  driftStopList(busStops,busLayer,44);
  renderWatch();
  refreshSummaryStats();
  refreshModeSummary();
  refreshRoutesLive();
  refreshPopoverIfOpen();
  updateGreeting();
}
livePulse();
setInterval(livePulse,4500);
