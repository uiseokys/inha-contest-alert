/* v8 controls. GitHub performs authentication; this page never receives a token. */
let plannerStorage;
try{plannerStorage=window.localStorage;}catch{plannerStorage=null;}
const plannerStore=CMPlanner.store(plannerStorage,'contest-monitor:planner:v1:'+location.pathname.replace(/index\.html$/,''));
let plannerState=plannerStore.read(),reportItem=null;
const CONDITION_LABELS={audience:'참가 신분',affiliation:'소속 조건',team:'팀 구성',mode:'진행 방식',cost:'참가 비용'};
const CONDITION_VALUES={unknown:'확인 필요',undergraduate:'학부생',graduate:'대학원생',general:'일반인',inha:'인하대 구성원 명시',unrestricted:'소속 제한 없음 명시',individual:'개인 참가 가능',individual_or_team:'개인 또는 팀',team_required:'팀 참가 필수',online:'온라인',onsite:'현장 참석',hybrid:'온라인·현장 병행',free:'무료',paid:'유료',all:'조건 선택 안 함'};
function downloadV8(text,name,type){const u=URL.createObjectURL(new Blob([text],{type}));const a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}
function savePlanner(){const ok=plannerStore.write(plannerState);if($('plannerNotice'))$('plannerNotice').textContent=ok?'진행·메모는 이 브라우저에 저장됩니다.':'저장소가 차단되어 현재 화면에서만 유지됩니다. 백업을 권합니다.';return ok;}
function planningFor(item){return CMPlanner.record(plannerState,item);}
function conditionsPanel(item){
 const box=el('section','criteria-panel');box.append(el('h4','','참가 조건 근거'));
 const grid=el('dl','details-grid');
 for(const key in CONDITION_LABELS){
  const c=item.conditions?.[key]||{value:'unknown'},f=el('div','detail-field');
  const value=Array.isArray(c.value)?c.value.map(v=>CONDITION_VALUES[v]||v).join(' · '):(CONDITION_VALUES[c.value]||'확인 필요');
  f.append(el('dt','',CONDITION_LABELS[key]),el('dd','',value));
  if(c.evidence)f.append(el('small','detail-note',c.evidence));grid.append(f);
 }
 box.append(grid,el('p','detail-note','표시된 조건만 확인한 결과이며, 최종 참가 가능 여부는 원문의 추가 제한까지 확인하세요.'));
 if(item.attachment_source_url)box.append(outLink(item.attachment_source_url,'텍스트 첨부 확인 근거 ↗','detail-link'),el('small','detail-note','첨부 확인: '+item.attachment_status));
 return box;
}
function plannerPanel(item){
 const section=el('section','planner-panel');section.append(el('h4','','내 신청·제출 관리'));
 const form=el('form','planner-form'),grid=el('div','form-grid');const r=structuredClone(planningFor(item));
 const stage=el('select');stage.setAttribute('aria-label',item.title+' 진행 상태');
 for(const [value,label] of Object.entries(CMPlanner.STAGES)){const o=el('option','',label);o.value=value;stage.append(o);}stage.value=r.stage;
 const stageLabel=el('label','','진행 상태');stageLabel.append(stage);
 const memo=el('textarea');memo.rows=2;memo.maxLength=1000;memo.value=r.note;memo.setAttribute('aria-label',item.title+' 개인 메모');
 const memoLabel=el('label','span-full','개인 메모 (서버에 보내지 않음)');memoLabel.append(memo);grid.append(stageLabel,memoLabel);
 const tasks=el('div','saved-tasks'),taskLabel=el('input'),taskDay=el('input'),taskClock=el('input');
 taskLabel.maxLength=100;taskLabel.placeholder='예: 제안서 제출';taskDay.type='date';taskClock.type='time';
 for(const [label,input] of [['다음 할 일 (선택)',taskLabel],['할 일 날짜',taskDay],['시각 (선택)',taskClock]]){const l=el('label','',label);l.append(input);grid.append(l);}
 const message=el('p','detail-note');message.setAttribute('role','status');
 function save(record){
  plannerState.records[item.id]=record;
  const ok=savePlanner();message.textContent=ok?'이 브라우저에 저장했습니다.':'현재 화면에만 저장했습니다. 백업해주세요.';
  const chip=document.getElementById('progress-'+item.id);if(chip)chip.textContent=CMPlanner.STAGES[record.stage];
  redrawTasks();
 }
 function redrawTasks(){
  tasks.replaceChildren();
  for(const t of planningFor(item).tasks){
   const line=el('div','task-row');line.append(el('span','',t.label+' · '+t.date+(t.time?' '+t.time:'')));
   const b=el('button','secondary','삭제');b.type='button';b.addEventListener('click',()=>save({...planningFor(item),stage:stage.value,note:memo.value,tasks:planningFor(item).tasks.filter(x=>x.id!==t.id)}));line.append(b);tasks.append(line);
  }
 }
 redrawTasks();
 const saveButton=el('button','secondary','진행·할 일 저장');saveButton.type='submit';
 form.append(grid,tasks,saveButton,message);
 form.addEventListener('submit',ev=>{
  ev.preventDefault();
  try{
   const saved={stage:stage.value,note:memo.value,tasks:structuredClone(planningFor(item).tasks)};
   if(taskLabel.value||taskDay.value||taskClock.value){
    if(!taskLabel.value.trim()||!CMPlanner.validDate(taskDay.value)||(taskClock.value&&!CMPlanner.validTime(taskClock.value)))throw Error('할 일 제목과 유효한 날짜를 함께 입력하세요.');
    saved.tasks.push({id:'task-'+Date.now().toString(36),label:taskLabel.value.trim(),date:taskDay.value,time:taskClock.value||null});
   }
   const probe=structuredClone(plannerState);probe.records[item.id]=saved;CMPlanner.parse(JSON.stringify(probe));
   save(saved);taskLabel.value=taskDay.value=taskClock.value='';
  }catch(err){message.textContent=err.message;}
 });
 section.append(form);
 if(item.milestones?.length){const list=el('div','automatic-milestones');list.append(el('strong','','원문에서 별도로 확인한 일정'));for(const m of item.milestones)list.append(el('p','detail-note',m.label+' · '+m.date+(m.time?' '+m.time:'')));section.append(list);}
 const actions=el('div','personal-actions'),cal=el('button','secondary','신청·제출 일정 저장 (.ics)');cal.type='button';
 cal.addEventListener('click',()=>{const text=CMPlanner.calendar(item,planningFor(item),currentTime());if(!text){message.textContent='저장할 날짜가 없습니다. 원문 확인 후 할 일 날짜를 추가하세요.';return;}downloadV8(text,'contest-'+item.id+'.ics','text/calendar;charset=utf-8');message.textContent='일회성 일정 파일입니다. 이후 마감 변경은 자동 동기화되지 않습니다.';});
 const report=el('button','secondary','정보가 달라요');report.type='button';
 report.addEventListener('click',()=>{reportItem=item;$('reportContest').textContent=item.title;$('reportDescription').value='';$('reportDialog').showModal();});
 const correction=el('button','secondary','원문 확인 후 수정 요청');correction.type='button';
 correction.addEventListener('click',()=>{$('manualKind').value='correct_notice';$('manualURL').value=item.url;$('manualTitleInput').value=item.title;$('manualDeadline').value=item.deadline||'';$('manualStart').value=item.registration_start||'';$('manualClock').value=item.deadline_time||'';$('manualEvidence').checked=false;$('manual-notice').scrollIntoView({block:'start'});$('manualSummary').focus();});
 actions.append(cal,report,correction);section.append(actions,el('p','detail-note','진행·메모·직접 입력 일정은 이 브라우저에만 저장됩니다. 서버 관심 알림에는 원문에서 확인한 일정만 사용합니다.'));
 return section;
}
function openRequest(kind,payload){
 const box=$('requestStatus');box.replaceChildren();
 try{
  const href=CMPlanner.issueURL(DATA.repo_url,kind,payload),body=CMPlanner.request(kind,payload);
  box.append(el('p','','아직 적용되지 않았습니다. GitHub에서 로그인 후 Create / Submit new issue를 눌러 요청을 제출하세요.'));
  if(href.length>7500){
   const ta=el('textarea');ta.value=body;ta.readOnly=true;ta.rows=6;ta.setAttribute('aria-label','GitHub 이슈 본문에 붙여 넣을 요청');
   const a=outLink(DATA.repo_url.replace(/\/$/,'')+'/issues/new','GitHub 이슈 열기 ↗','detail-link');
   box.append(el('p','','요청이 길어 자동 입력 대신 아래 내용을 복사해 이슈 본문에 붙여 넣어주세요.'),ta,a);
  }else{
   box.append(outLink(href,'GitHub에서 요청 제출하기 ↗','detail-link primary'));
   window.open(href,'_blank','noopener,noreferrer');
  }
  box.append(el('p','detail-note','Apply page request가 성공하고 페이지가 다시 배포되면 적용된 시각과 요청 번호가 표시됩니다. 일반 신고는 검토 대상이며 자동으로 데이터를 바꾸지 않습니다.'));
 }catch(err){box.append(el('p','detail-warning',err.message));}
}
function setupV8(){
 const settings=DATA.server_settings||{},n=settings.notification||{time:'12:00',enabled:true};
 $('notificationClock').textContent=n.enabled?n.time:'알림 꺼짐';$('notificationTime').value=n.time;$('notificationEnabled').checked=n.enabled;
 $('serverRevision').textContent='현재 서버 설정: '+(n.enabled?n.time+' KST':'알림 꺼짐')+(settings.revision?' · '+settings.revision:' · 기본값')+(settings.updated_at?' · '+settings.updated_at.slice(0,16):'');
 $('serverWatchlistCount').textContent='서버 관심 '+(settings.watchlist||[]).length+'개';
 $('manualChecked').value=CMRuntime.dayOf(new Date());
 $('notificationForm').addEventListener('submit',ev=>{ev.preventDefault();if(!CMPlanner.validTime($('notificationTime').value))return;openRequest('settings',{notification:{time:$('notificationTime').value,enabled:$('notificationEnabled').checked,timezone:'Asia/Seoul'}});});
 $('openNotificationSettings').addEventListener('click',()=>setTimeout(()=>$('notificationTime').focus(),0));
 function sync(clear){
  if(!$('syncConsent').checked){$('requestStatus').textContent='선택한 공고 ID가 공개됨을 확인하는 체크박스를 먼저 선택하세요.';return;}
  const ids=clear?[]:preferences.favorites;
  if(ids.length>100){$('requestStatus').textContent='서버 관심 알림은 최대 100개입니다.';return;}
  openRequest('settings',{watchlist:ids,fields:$('fieldFilter').value==='all'?[]:[$('fieldFilter').value]});
 }
 $('syncWatchlist').addEventListener('click',()=>sync(false));$('clearWatchlist').addEventListener('click',()=>sync(true));
 const controls=$('eligibilityControls');
 for(const [key,choices] of Object.entries(CMPlanner.FILTERS)){
  const label=el('label','',CONDITION_LABELS[key]),select=el('select');select.id='eligibility-'+key;
  for(const c of choices){const o=el('option','',CONDITION_VALUES[c]);o.value=c;select.append(o);}select.value=plannerState.filters[key];label.append(select);controls.append(label);
  select.addEventListener('change',()=>{plannerState.filters[key]=select.value;savePlanner();update();});
 }
 $('includeUnknown').checked=plannerState.filters.unknown;
 $('includeUnknown').addEventListener('change',()=>{plannerState.filters.unknown=$('includeUnknown').checked;savePlanner();update();});
 $('exportPlanner').addEventListener('click',()=>downloadV8(JSON.stringify(CMPlanner.parse(JSON.stringify(plannerState)),null,2),'contest-progress.json','application/json'));
 $('importPlanner').addEventListener('click',()=>$('plannerFile').click());
 $('plannerFile').addEventListener('change',async()=>{
  const f=$('plannerFile').files[0];if(!f)return;
  try{if(f.size>500000)throw Error('파일은 500KB 이하여야 합니다.');const p=CMPlanner.parse(await f.text());plannerState=CMPlanner.parse(JSON.stringify({...p,records:{...plannerState.records,...p.records}}));savePlanner();for(const key in CMPlanner.FILTERS)$('eligibility-'+key).value=plannerState.filters[key];$('includeUnknown').checked=plannerState.filters.unknown;update();}
  catch(err){$('plannerNotice').textContent=err.message;}
  $('plannerFile').value='';
 });
 $('manualNoticeForm').addEventListener('submit',ev=>{
  ev.preventDefault();const kind=$('manualKind').value;
  const payload={url:$('manualURL').value,title:$('manualTitleInput').value,evidence_url:$('manualURL').value,checked_at:$('manualChecked').value};
  payload[kind==='add_notice'?'summary':'reason']=$('manualSummary').value;
  if($('manualStart').value)payload.registration_start=$('manualStart').value;
  if($('manualDeadline').value)payload.deadline=$('manualDeadline').value;
  if($('manualClock').value){if(!payload.deadline){$('requestStatus').textContent='마감 시각에는 마감 날짜도 필요합니다.';return;}payload.deadline_time=$('manualClock').value;}
  openRequest(kind,payload);
 });
 $('closeReport').addEventListener('click',()=>$('reportDialog').close());
 $('reportForm').addEventListener('submit',ev=>{ev.preventDefault();if(!reportItem)return;openRequest('report',{url:reportItem.url,id:reportItem.notice_id||reportItem.id,category:$('reportCategory').value,description:$('reportDescription').value});$('reportDialog').close();});
 if(DATA.quality_alerts?.length){$('qualityAlertBanner').hidden=false;$('qualityAlertBanner').textContent='수집 점검 필요: '+DATA.quality_alerts.map(a=>a.source_id+' · '+a.message).join(' / ');}
 if(!plannerStore.available)$('plannerNotice').textContent='브라우저 저장이 제한되어 진행 상태는 현재 화면에서만 유지됩니다.';
}
