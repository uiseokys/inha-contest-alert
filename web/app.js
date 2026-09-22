'use strict';
const DATA=JSON.parse(document.getElementById('app-data').textContent);
const NOTICE_ITEMS=DATA.items||[];
DATA.items=DATA.events||NOTICE_ITEMS;
const $=id=>document.getElementById(id);
const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
const safeURL=value=>{try{const u=new URL(value);return ['https:','http:'].includes(u.protocol)&&!u.username&&!u.password?u.href:'';}catch{return '';}};
const currentTime=()=>DATA.demo&&DATA.updated_at?new Date(DATA.updated_at):new Date();
let today=CMRuntime.dayOf(currentTime());
const epoch=d=>Date.parse(d+'T00:00:00+09:00');
const days=d=>Math.round((epoch(d)-epoch(today))/86400000);
function isDailyNew(item){return ['comparable','gap'].includes(CMRuntime.comparison(DATA.daily_comparison,currentTime()).status)&&item.daily_new;}
function status(item){return CMRuntime.status(item,currentTime());}
function statusLabel(item){return CMRuntime.label(item,currentTime());}
function outLink(url,text,cls){const a=el('a',cls,text);const safe=safeURL(url);if(safe){a.href=safe;a.target='_blank';a.rel='noopener noreferrer';}return a;}
let selectedGroup='all';let filtered=[];
let local;try{local=window.localStorage;}catch{local=null;}
const prefStore=CMPersonal.store(local,'contest-monitor:preferences:v1:'+location.pathname.replace(/index\.html$/,''));
let preferences=prefStore.read();preferences.favorites=CMPersonal.normalizeFavorites(preferences.favorites,DATA.items);
const fieldLabels=DATA.field_labels||{data_analysis:'데이터 분석',model_development:'AI 모델 개발',service_development:'AI 서비스 개발',creative_ai:'AI 영상·디자인',general_ai:'AI·데이터 일반'};
let personalReady=false;
function isFavorite(item){return preferences.favorites.includes(item.id)||(item.favorite_ids||[]).some(id=>preferences.favorites.includes(id));}
function filterValues(){return {query:$('searchInput').value,source:$('sourceFilter').value,group:selectedGroup,kind:$('kindFilter').value,field:$('fieldFilter').value,status:$('statusFilter').value,sort:$('sortFilter').value,newOnly:$('newOnly').checked,onlyFavorites:$('favoriteOnly').checked};}
function savePreferences(){
  if(!personalReady)return;
  preferences.filters=CMPersonal.filters(filterValues());
  if(!prefStore.write(preferences))$('personalNotice').textContent='브라우저 저장소를 사용할 수 없어 현재 화면에서만 보관합니다. 내보내기로 백업하세요.';
  $('favoriteCount').textContent=DATA.items.filter(isFavorite).length;
}
function applyPreferences(){
  const f=preferences.filters;selectedGroup=f.group;
  for(const [id,key] of [['searchInput','query'],['sourceFilter','source'],['kindFilter','kind'],['fieldFilter','field'],['statusFilter','status'],['sortFilter','sort']])$(id).value=f[key];
  if(!$('sourceFilter').value)$('sourceFilter').value='all';
  $('newOnly').checked=f.newOnly&&!$('newOnly').disabled;$('favoriteOnly').checked=f.onlyFavorites;
  document.querySelectorAll('[data-group]').forEach(b=>{const active=b.dataset.group===selectedGroup;b.classList.toggle('selected',active);b.setAttribute('aria-pressed',String(active));});
}
function favoriteButton(item){
  const button=el('button','favorite-button',isFavorite(item)?'★ 관심 저장됨':'☆ 관심 저장');button.type='button';button.setAttribute('aria-pressed',String(isFavorite(item)));button.setAttribute('aria-label',item.title+' 관심 저장');
  button.addEventListener('click',()=>{
    if(isFavorite(item)){const aliases=new Set([item.id,...(item.favorite_ids||[])]);preferences.favorites=preferences.favorites.filter(id=>!aliases.has(id));}
    else{if(preferences.favorites.length>=1000){$('personalNotice').textContent='관심 목록은 최대 1000개입니다. 일부를 해제한 뒤 다시 저장하세요.';return;}preferences.favorites.push(item.id);}
    savePreferences();button.textContent=isFavorite(item)?'★ 관심 저장됨':'☆ 관심 저장';button.setAttribute('aria-pressed',String(isFavorite(item)));renderUrgentFavorites();
    if($('favoriteOnly').checked&&!isFavorite(item)){update();$('favoriteOnly').focus();}
  });return button;
}
if(DATA.demo)$('demoBanner').hidden=false;
if(safeURL(DATA.repo_url)){for(const id of ['repoLink','repoLinkMobile']){$(id).href=DATA.repo_url;$(id).hidden=false;$(id).target='_blank';$(id).rel='noopener noreferrer';}}
if(DATA.updated_at){$('updatedAt').textContent='마지막 수집 시도 '+new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',dateStyle:'medium',timeStyle:'short'}).format(new Date(DATA.updated_at));if(!DATA.demo&&Date.now()-Date.parse(DATA.updated_at)>36*3600000){$('staleBanner').hidden=false;$('staleBanner').textContent='목록이 36시간 이상 갱신되지 않았습니다. GitHub Actions 실행 상태와 출처별 수집 상태를 확인하세요.';}}
else{$('staleBanner').hidden=false;$('staleBanner').textContent='아직 첫 수집 전입니다. 저장소의 SETUP.md를 따라 설정하고 Actions에서 수동 실행하세요.';}
const sources=DATA.sources||[];const enabled=sources.filter(s=>s.status!=='disabled');const failed=enabled.filter(s=>!['ok'].includes(s.status));
$('totalCount').textContent=DATA.items.filter(i=>status(i)!=='closed').length;
renderComparison();
$('dueCount').textContent=DATA.items.filter(i=>status(i)!=='closed'&&i.deadline&&days(i.deadline)>=0&&days(i.deadline)<=7).length;
$('sourceCount').textContent=enabled.filter(s=>s.status==='ok').length+' / '+enabled.length;
$('sourceNote').textContent=failed.length?failed.length+'곳 확인 필요':'설정된 수집 범위 기준';
const sourceNames=new Map(sources.map(s=>[s.name,s.name]));DATA.items.forEach(i=>(i.source_names||[i.source_name]).forEach(n=>sourceNames.set(n,n)));
for(const name of [...sourceNames.keys()].sort()){$('sourceFilter').appendChild(new Option(name,name));}
const healthLabels={ok:'정상',partial:'부분 실패',error:'수집 실패',disabled:'직접 확인',pending:'미확인'};
for(const s of sources){const row=el('div','health-row');const title=el('div','health-title');title.append(outLink(s.url,s.name+' ↗'),el('span',s.status,healthLabels[s.status]||s.status));row.append(title,el('p','',s.message||'첫 수집 전'));if(s.detail_errors)row.append(el('p','',`상세 페이지 확인 실패 ${s.detail_errors}건 · 날짜는 원문 확인`));if(s.detail_unconfirmed)row.append(el('p','',`상세정보 추출 미확인 ${s.detail_unconfirmed}건 · 원문 직접 확인`));if(s.dates_complete!==undefined)row.append(el('p','','접수 시작·마감 확인 '+s.dates_complete+'건 · 일부 확인 '+s.dates_partial+'건 · 미확인 '+s.dates_missing+'건'));if(s.excluded||s.topic_pending)row.append(el('p','','관련성 검사: 제외 '+(s.excluded||0)+'건 · 확인 대기 '+(s.topic_pending||0)+'건 (목록·알림에서 숨김)'));if(s.duplicates_hidden)row.append(el('p','','동일 게시글 중복 '+s.duplicates_hidden+'건 통합 · 원본 기록은 보존'));if(s.detail_render_errors)row.append(el('p','','동적 상세 화면 확인 실패 '+s.detail_render_errors+'건'));if(s.schedule_errors)row.append(el('p','','추가 일정 페이지 접근 실패 '+s.schedule_errors+'건'));if(s.detail_deferred)row.append(el('p','','이번 실행의 상세 확인 예산 초과 '+s.detail_deferred+'건 · 다음 수집에서 이어서 확인'));$('sourceHealth').append(row);}
if(!sources.length)$('sourceHealth').append(el('p','','첫 실행 후 수집 상태가 표시됩니다.'));
function renderComparison(){
  const c=CMRuntime.comparison(DATA.daily_comparison,currentTime());
  const valid=['comparable','gap'].includes(c.status);
  if(!valid)$('newOnly').checked=false;
  const label=c.status==='gap'?c.base_date+' 대비 신규':'어제 대비 신규';
  $('newCountLabel').textContent=label;
  $('newCount').textContent=valid?(c.new_event_count??c.new_count):'—';
  $('newCountNote').textContent=valid?'새 대회·프로그램 · 목록 보기':c.status==='baseline'?'첫 저장 후 다음 날부터 비교':'비교 가능한 수집 기록 없음';
  $('showNew').disabled=!valid||(c.new_event_count??c.new_count)===0;
  $('newOnly').disabled=!valid;
  $('newOnlyLabel').textContent=c.status==='gap'?'비교 기준 이후 신규만':'어제 대비 신규만';
  const titles={baseline:'어제 대비 비교 준비 중',stale:'오늘 수집 기록이 없어 비교할 수 없습니다.',unobserved:'수집 실패로 신규 건수를 비교할 수 없습니다.'};
  $('comparisonTitle').textContent=valid?(label+' 대회·프로그램 '+(c.new_event_count??c.new_count)+'개 · 새 공고 '+c.new_count+'건'):titles[c.status]||titles.baseline;
  const shortTime=value=>new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(value));
  $('comparisonRange').textContent=c.base_at&&c.as_of?'비교 구간  '+shortTime(c.base_at)+' → '+shortTime(c.as_of)+' (한국시간)':'';
  const chips=(c.by_source||[]).map(s=>{const chip=el('span','source-chip',s.name);chip.append(el('strong','',s.count+'건'));return chip;});
  $('dailySourceCounts').replaceChildren(...chips);
  const notes=[];
  if(c.status==='stale'&&c.saved_date)notes.push('최근 저장 결과는 '+c.saved_date+' 기준입니다. 현재 날짜의 신규 건수로 표시하지 않습니다.');
  if(c.status==='baseline')notes.push('기존 목록은 비교 기준으로만 저장합니다. 다음 날 수집부터 신규 건수를 표시합니다.');
  if(c.status==='gap')notes.push('어제 기록이 없어 가장 최근의 이전 수집 날짜와 비교했습니다.');
  if(c.partial)notes.push('일부 출처의 수집이 불완전하므로 확인된 범위만 집계했습니다.');
  if(c.initial_count)notes.push('새 출처 최초 적재 '+c.initial_count+'건은 신규 집계에서 제외했습니다.');
  if(c.unverified_count)notes.push('이전 수집 불완전 출처의 추가 확인 '+c.unverified_count+'건은 별도입니다.');
  if(c.repost_count)notes.push('기존 기회의 재게시 '+c.repost_count+'건은 새 대회 수에서 제외했습니다.');
  if(c.deadline_extensions?.length)notes.push('마감이 뒤로 변경된 기록 '+c.deadline_extensions.length+'개가 있습니다. 원문을 확인하세요.');
  if(c.date_correction_count)notes.push('추출 방식 갱신에 따른 날짜 정정 '+c.date_correction_count+'건은 별도입니다.');
  notes.push('공식 주소 등 확실한 근거가 있는 공고만 같은 대회로 묶습니다. 유사한 제목만으로 합치지 않습니다.');
  $('comparisonNote').textContent=notes.join(' ');
}

function period(start,end){if(start&&end)return start===end?start:start+' ~ '+end;if(end)return '시작 미확인 ~ '+end;if(start)return start+' ~ 종료 미확인';return '미확인';}
function fact(grid,label,value,wide=false){const field=el('div','detail-field'+(wide?' wide':''));field.append(el('dt','',label),el('dd','',value||'미확인 · 공고 원문 확인'));grid.append(field);}
function detailPanel(item){
  const panel=el('details','contest-details');const summary=el('summary');
  const state=({ok:'공개 정보 일부 확인',error:'상세 확인 실패',unconfirmed:'상세정보 미확인'}[item.detail_status]||'상세 확인 대기');
  summary.append(el('span','','일정·참가 정보 펼치기'),el('small',item.detail_status==='error'?'detail-warning':'',state));panel.append(summary);
  panel.addEventListener('toggle',()=>{summary.querySelector('span').textContent=panel.open?'일정·참가 정보 접기':'일정·참가 정보 펼치기';});
  const grid=el('dl','details-grid');
  fact(grid,'대회명 (전체)',item.title,true);
  fact(grid,'접수기간',period(item.registration_start,item.deadline));
  if(item.deadline_time)fact(grid,'접수 마감 시각',item.deadline_time+' (원문 기준)');
  if(item.registration_start_time)fact(grid,'접수 시작 시각',item.registration_start_time+' (원문 기준)');
  if(item.relevance_evidence)fact(grid,'AI·데이터 관련 근거',item.relevance_evidence,true);
  fact(grid,'대회·행사기간',period(item.event_start,item.event_end));
  if(item.registration_text)fact(grid,'접수기간 원문 표기',item.registration_text,true);
  fact(grid,'주최 / 주관',item.organizer);fact(grid,'참가 대상 / 팀 구성',item.eligibility);
  fact(grid,'상금 / 혜택',item.benefits);fact(grid,'대회 주제',item.summary);
  if(item.schedule_text)fact(grid,'세부 일정 안내',item.schedule_text,true);
  if(item.date_evidence)fact(grid,'날짜 근거 (원문)',item.date_evidence,true);
  panel.append(grid);
  if(item.date_note)panel.append(el('p','detail-note',item.date_note));
  if(safeURL(item.date_source_url))panel.append(outLink(item.date_source_url,'날짜 근거 페이지 ↗','date-evidence-link detail-link'));
  if(!item.deadline)panel.append(el('p','detail-note',item.detail_status==='error'?'상세 페이지 접근에 실패해 마감일을 확인하지 못했습니다.':'텍스트·공개 일정에서 접수 마감일을 아직 확정하지 못했습니다. 포스터에만 적힌 날짜는 원문을 확인하세요.'));
  if(item.event_ambiguous)panel.append(el('p','detail-warning','대회·행사기간의 날짜가 역전되거나 여러 일정이 섞여 있어 확정하지 않았습니다. 접수기간과 별도로 원문을 확인하세요.'));
  if(item.registration_ambiguous)panel.append(el('p','detail-warning','접수기간이 여러 개이거나 날짜를 확정할 수 없습니다. 원문에서 해당 트랙과 기간을 확인하세요.'));
  if(item.sources?.length>1){
    const merged=el('section','merged-sources');merged.append(el('h4','','같은 대회의 공고 '+item.sources.length+'건'),el('p','detail-note','통합 근거: '+item.grouping_basis));
    for(const source of item.sources){const line=el('p');line.append(outLink(source.url,source.source_name+' · '+source.title+' ↗'));if(source.deadline)line.append(el('small','','원문 마감 '+source.deadline+(source.deadline_time?' '+source.deadline_time:'')));merged.append(line);}panel.append(merged);
  }
  if(item.cross_source_conflict)panel.append(el('p','detail-warning','출처별 마감일이 다릅니다. 위 날짜 근거와 각 공고를 대조하세요.'));
  if(item.manual_correction){const m=item.manual_correction;panel.append(el('p','detail-note','관리자 보정 · '+m.checked_at+' 확인 · '+m.reason));if(safeURL(m.evidence_url))panel.append(outLink(m.evidence_url,'관리자 보정 근거 ↗','detail-link'));if(m.needs_review)panel.append(el('p','detail-warning','보정 이후 자동 수집 값이 변경되었습니다. 관리자 재확인이 필요합니다.'));}
  const actions=el('div','detail-actions');actions.append(outLink(item.url,'공고 원문 ↗','detail-link primary'));
  if(safeURL(item.website_url))actions.append(outLink(item.website_url,'안내 사이트 ↗','detail-link'));
  if(safeURL(item.application_url))actions.append(outLink(item.application_url,'신청 페이지 ↗','detail-link'));
  panel.append(actions);
  if(!safeURL(item.website_url)&&!safeURL(item.application_url))panel.append(el('p','detail-note','별도 안내·신청 링크는 아직 확인되지 않았습니다. 공고 원문에서 확인하세요.'));
  let note=item.detail_checked_at?'상세정보 마지막 확인: '+item.detail_checked_at.slice(0,10):'상세정보를 아직 확인하지 못했습니다.';
  if(item.detail_status==='error'||item.detail_status==='unconfirmed')note+=' 이전에 확인한 정보가 남아 있을 수 있습니다.';
  panel.append(el('p','detail-note',note+' · 일부 항목만 추출하며, 마감 시각·참가 자격·최종 변경은 원문이 기준입니다.'));
  return panel;
}
function card(item){
  const row=el('article','contest');row.id='contest-'+item.id;
  const source=el('div','source-block');source.append(el('span','source-name',item.source_name),el('span','kind-label',({contest:'공모전·경진대회',program:'프로그램·교육',other:'참여 기회'}[item.opportunity_kind]||'참여 기회')),el('span','pill '+status(item),statusLabel(item)));
  const body=el('div','contest-body');const h=el('h3');h.append(outLink(item.url,item.title));
  h.querySelector('a').title=item.title;
  if(isDailyNew(item))source.append(el('span','new-badge','신규'));
  source.append(favoriteButton(item));
  const reg=el('div','registration-line');
  for(const [label,value] of [['접수 시작',item.registration_start],['접수 마감',item.deadline?(item.deadline+(item.deadline_time?' '+item.deadline_time:'')):null]]){const part=el('div','date-pair');part.append(el('span','date-label',label),el('span','date-value'+(value?'':' is-unknown'),value||'확인 필요'));reg.append(part);}
  const fields=el('div','field-tags');for(const tag of item.technical_fields||[])fields.append(el('span','field-tag',fieldLabels[tag]||tag));
  body.append(h,fields,reg);
  body.append(el('p','organizer-line','주최 / 주관 '+(item.organizer||'확인 필요')));
  const meta=el('div','metadata');meta.append(el('span','',item.posted_at?'게시 '+item.posted_at:'게시일 미확인'),el('span','','첫 확인 '+(item.first_seen||'').slice(0,10)));body.append(meta);
  const due=el('div','deadline');
  if(item.deadline){const d=days(item.deadline);due.append(el('strong',d>=0&&d<=7?'urgent':'',status(item)==='closed'?'마감 / 종료':d===0?'오늘 마감일':'D−'+d),el('small','',item.deadline));}
  else{due.append(el('strong','','원문 확인'),el('small','','마감일 미확인'));}
  const open=outLink(item.url,'↗','open-link');open.setAttribute('aria-label',item.title+' 공고 원문 열기 (새 탭)');
  row.append(source,body,due,open,detailPanel(item));return row;
}
function update(){
  const query=$('searchInput').value.trim().toLowerCase(),source=$('sourceFilter').value,state=$('statusFilter').value,kind=$('kindFilter').value,field=$('fieldFilter').value;
  filtered=DATA.items.filter(i=>{const current=status(i);return (selectedGroup==='all'||(i.groups||[i.group]).includes(selectedGroup))&&(kind==='all'||(i.opportunity_kind||'other')===kind)&&(field==='all'||(i.technical_fields||['general_ai']).includes(field))&&(source==='all'||(i.source_names||[i.source_name]).includes(source))&&(state==='all'||(state==='review'?current!=='closed':current===state))&&(!$('newOnly').checked||isDailyNew(i))&&(!$('favoriteOnly').checked||isFavorite(i))&&(!query||[i.title,i.source_name,i.organizer,i.eligibility,i.summary,i.benefits].filter(Boolean).join(' ').toLowerCase().includes(query));});
  filtered.sort((a,b)=>CMRuntime.compareItems(a,b,$('sortFilter').value,currentTime()));
  $('items').replaceChildren(...filtered.map(card));$('resultCount').textContent=filtered.length+'개 대회·프로그램';$('empty').hidden=filtered.length!==0;$('csvButton').disabled=filtered.length===0;$('loading').hidden=true;savePreferences();
}
$('newOnly').addEventListener('change',()=>{if($('newOnly').checked)$('statusFilter').value='all';});
for(const id of ['searchInput','sourceFilter','statusFilter','sortFilter','newOnly','kindFilter','fieldFilter','favoriteOnly'])$(id).addEventListener(id==='searchInput'?'input':'change',update);
for(const button of document.querySelectorAll('[data-group]'))button.addEventListener('click',()=>{selectedGroup=button.dataset.group;document.querySelectorAll('[data-group]').forEach(b=>{const yes=b===button;b.classList.toggle('selected',yes);b.setAttribute('aria-pressed',String(yes));});update();});
$('csvButton').addEventListener('click',()=>{const quote=value=>{let s=String(value??'');if(/^[\s]*[=+@\-\t\r]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';};const rows=[['공고명','출처','접수시작일','접수마감일','접수기간 원문','대회시작일','대회종료일','일정안내','주최기관','참가대상','혜택','주제','안내사이트','신청링크','상태','공고원문','상세확인일','접수시작시각','접수마감시각'],...filtered.map(i=>[i.title,i.source_name,i.registration_start,i.deadline,i.registration_text,i.event_start,i.event_end,i.schedule_text,i.organizer,i.eligibility,i.benefits,i.summary,safeURL(i.website_url),safeURL(i.application_url),statusLabel(i),safeURL(i.url),i.detail_checked_at,i.registration_start_time,i.deadline_time])];const blob=new Blob(['\ufeff'+rows.map(r=>r.map(quote).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'});const url=URL.createObjectURL(blob);const a=el('a');a.href=url;a.download='contests-'+today+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
function resetFilters(){
  selectedGroup='all';$('fieldFilter').value='all';$('favoriteOnly').checked=false;$('kindFilter').value='all';$('searchInput').value='';$('sourceFilter').value='all';$('statusFilter').value='review';$('sortFilter').value='remaining';$('newOnly').checked=false;
  document.querySelectorAll('[data-group]').forEach(b=>{const active=b.dataset.group==='all';b.classList.toggle('selected',active);b.setAttribute('aria-pressed',String(active));});
  update();
}
$('resetFilters').addEventListener('click',()=>{resetFilters();$('searchInput').focus();});
$('showNew').addEventListener('click',()=>{resetFilters();$('statusFilter').value='all';$('newOnly').checked=true;update();$('opportunities').scrollIntoView({block:'start'});$('newOnly').focus({preventScroll:true});});
document.querySelectorAll('.nav-item').forEach(a=>a.addEventListener('click',()=>{document.querySelectorAll('.nav-item').forEach(x=>{x.classList.toggle('current',x===a);if(x===a)x.setAttribute('aria-current','location');else x.removeAttribute('aria-current');});}));
applyPreferences();personalReady=true;update();renderUrgentFavorites();

function displayTime(value){if(!value)return '기록 없음';const parsed=new Date(value);return Number.isNaN(+parsed)?'기록 확인 필요':new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',dateStyle:'medium',timeStyle:'short',hour12:false}).format(parsed);}
function runtimePanel(){
  const r=DATA.runtime||{},c=r.collection||{},n=r.notification||{},labels={complete:'모든 설정 출처의 목록 확인',partial:'일부 출처 확인',failed:'수집 실패',legacy:'이전 버전 기록',not_started:'수집 전'};
  $('runtimeSummary').textContent='v'+(r.version||DATA.version)+' · '+(labels[c.status]||'상태 미확인');
  const grid=$('runtimeDetails');
  for(const [label,value] of [['페이지 코드','v'+(r.version||DATA.version)+' · '+((r.build||{}).fingerprint||'해시 미확인')],['수집 코드',c.version?'v'+c.version+' · '+(c.fingerprint||''):'새 수집 후 표시'],['마지막 수집 시도',displayTime(c.attempted_at)],['마지막 일부 이상 성공',displayTime(r.last_usable_at)],['페이지 생성',displayTime(r.generated_at)],['최근 알림 요청',({not_attempted:'시도 기록 없음',reserved:'발송 선점 · 수락 미확인',accepted:'ntfy 서버 수락',scheduled:'예약 수락',failed:'전송 실패',unknown:'상태 미확인'}[n.status]||'상태 미확인')+' · '+displayTime(n.accepted_at||n.failed_at||n.at)]])fact(grid,label,value);
  const link=safeURL(c.run_url||(r.build||{}).run_url);if(link){const field=el('div','detail-field wide');field.append(el('dt','','실행 기록'),el('dd'));field.lastChild.append(outLink(link,'해당 GitHub Actions 실행 확인 ↗'));grid.append(field);}
  $('workflowLive').textContent='마지막 저장 기록입니다. ntfy 수락은 휴대폰 수신 성공과 다릅니다.';
}
runtimePanel();
let timeSignature='',pendingClockRender=false;
function refreshClock(){
  const now=currentTime(),signature=CMRuntime.dayOf(now)+'|'+DATA.items.map(i=>CMRuntime.status(i,now)).join(',');
  if(timeSignature&&timeSignature!==signature){
    today=CMRuntime.dayOf(now);renderComparison();renderUrgentFavorites();
    if(!['comparable','gap'].includes(CMRuntime.comparison(DATA.daily_comparison,now).status))document.querySelectorAll('.new-badge').forEach(n=>n.remove());
    $('totalCount').textContent=DATA.items.filter(i=>status(i)!=='closed').length;
    $('dueCount').textContent=DATA.items.filter(i=>status(i)!=='closed'&&i.deadline&&days(i.deadline)>=0&&days(i.deadline)<=7).length;
    const inside=document.activeElement?.closest('#items');
    if(inside){
      // Update time-sensitive text in place without removing keyboard focus.
      for(const item of DATA.items){const row=$('contest-'+item.id);if(!row)continue;const pill=row.querySelector('.pill');pill.className='pill '+status(item);pill.textContent=statusLabel(item);if(status(item)==='closed'){const due=row.querySelector('.deadline strong');due.textContent='마감 / 종료';due.className='';}}
      pendingClockRender=true;
    }else renderClockChange();
  }
  timeSignature=signature;
}
function renderClockChange(){
  const open=[...document.querySelectorAll('.contest-details[open]')].map(n=>n.closest('article').id);
  update();for(const id of open){const detail=$(id)?.querySelector('details');if(detail)detail.open=true;}pendingClockRender=false;
}
$('items').addEventListener('focusout',()=>setTimeout(()=>{if(pendingClockRender&&!document.activeElement?.closest('#items'))renderClockChange();},0));
refreshClock();setInterval(refreshClock,15000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)refreshClock();});

function renderUrgentFavorites(){
  const due=DATA.items.filter(i=>isFavorite(i)&&status(i)!=='closed'&&i.deadline&&days(i.deadline)>=0&&days(i.deadline)<=7).sort((a,b)=>CMRuntime.compareItems(a,b,'deadline',currentTime()));
  $('urgentFavorites').hidden=due.length===0;
  $('urgentItems').replaceChildren(...due.slice(0,6).map(item=>{const row=el('p');row.append(outLink(item.url,item.title+' ↗'),el('span','',item.deadline+(item.deadline_time?' '+item.deadline_time:' · 시각 미확인')));return row;}));
}
function downloadJSON(text,name){const url=URL.createObjectURL(new Blob([text],{type:'application/json;charset=utf-8'}));const a=el('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
$('exportPersonal').addEventListener('click',()=>{savePreferences();downloadJSON(CMPersonal.exportJSON(preferences),'contest-favorites-'+today+'.json');$('personalNotice').textContent='관심·필터 백업을 내보냈습니다. 파일에는 관심 공고 ID와 선택한 필터가 포함됩니다.';});
$('importPersonal').addEventListener('click',()=>$('importPersonalFile').click());
$('importPersonalFile').addEventListener('change',async event=>{
  const file=event.target.files?.[0];if(!file)return;
  const trigger=$('importPersonal');trigger.disabled=true;
  try{
    if(file.size>262144)throw Error('가져오기 파일 크기는 256KB 이하여야 합니다.');
    const imported=CMPersonal.parseImport(await file.text());
    const merged=CMPersonal.normalizeFavorites([...preferences.favorites,...imported.favorites],DATA.items);
    if(merged.length>1000)throw Error('합친 관심 목록이 1000개를 넘습니다.');
    preferences={version:1,favorites:merged,filters:imported.filters};applyPreferences();update();renderUrgentFavorites();
    $('personalNotice').textContent='관심 목록을 합치고 가져온 필터를 적용했습니다. 저장된 ID '+merged.length+'개 · 이 기기의 브라우저에만 적용됩니다.';
    if(!prefStore.available)$('personalNotice').textContent+=' 저장소를 사용할 수 없어 탭을 닫기 전에 내보내세요.';
  }catch(error){$('personalNotice').textContent=error.message||'가져오기에 실패했습니다. 기존 목록은 유지됩니다.';}
  finally{trigger.disabled=false;event.target.value='';}
});

function renderReviewAndQuality(){
  const pending=DATA.review_items||[];$('reviewCount').textContent=pending.length+'건';
  for(const item of pending){const row=el('article','review-item');row.append(outLink(item.url,item.title+' ↗'),el('p','detail-note',item.relevance_reason||'관련성 확인 대기'));$('reviewItems').append(row);}
  if(!pending.length)$('reviewItems').append(el('p','list-note','현재 관련성 확인 대기 공고가 없습니다.'));
  const report=DATA.quality||{};$('qualitySummary').textContent=report.total?'마감일 '+report.deadline_known+'/'+report.total+'건 확인 · '+report.coverage+'%'+(report.manual_count?' · 관리자 보정 '+report.manual_count+'건':''):'분모가 없어 확인율을 계산하지 않습니다.';$('qualityBasis').textContent=report.basis||'수집 후 진단 결과가 표시됩니다.';
  for(const source of report.sources||[]){
    const row=el('details','quality-source');row.append(el('summary','',source.name+' · 마감 '+source.deadline_known+'/'+source.denominator+'건'+(source.deadline_coverage===null?'':(' ('+source.deadline_coverage+'%)'))));
    row.append(el('p','list-note','이번 실행에서 상세 조회 '+source.attempted_this_run+'건 / 날짜 확인 '+source.deadline_confirmed_this_run+'건 · 저장된 마감 시각 확인 '+source.deadline_time_known+'건 · 자동 확인 '+source.automatic_deadline_known+'건 / 관리자 보정 '+source.manual_count+'건'));
    for(const sample of source.samples||[]){const line=el('p','quality-sample');line.append(outLink(sample.url,sample.title+' ↗'),el('span','',sample.label));if(sample.last_attempted_at)line.append(el('small','','마지막 상세 시도 '+displayTime(sample.last_attempted_at)));row.append(line);}
    $('qualityDetails').append(row);
  }
  if(!DATA.demo&&safeURL(DATA.page_url)){const p=el('p','list-note');const base=DATA.page_url.replace(/\/?$/,'/');p.append(outLink(base+'quality.json','기계가 읽을 수 있는 품질 보고서 ↗'),el('span','',' · '),outLink(DATA.repo_url+'/actions/workflows/diagnose.yml','GitHub에서 읽기 전용 진단 실행 ↗'));$('qualityDetails').append(p);}
}
renderReviewAndQuality();
async function verifyLiveWorkflow(){
  if(DATA.demo)return;
  const match=(safeURL(DATA.repo_url)||'').match(/^https:\/\/github\.com\/([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+)\/?$/);if(!match)return;
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),7000);
  try{
    const response=await fetch('https://api.github.com/repos/'+match[1]+'/'+match[2]+'/actions/workflows/daily.yml/runs?per_page=1',{signal:controller.signal,credentials:'omit',headers:{Accept:'application/vnd.github+json'}});
    if(!response.ok)throw Error('unavailable');
    const latest=(await response.json()).workflow_runs?.[0];
    if(!latest){$('workflowLive').textContent='공개 API에서 자동 실행 기록을 찾지 못했습니다. 저장된 정보는 위와 같습니다.';return;}
    const status=latest.status==='completed'?({success:'완료',failure:'실패',cancelled:'취소',timed_out:'시간 초과',skipped:'건너뜀'}[latest.conclusion]||'결과 확인 필요'):'실행 중 / 대기';
    const url=safeURL(latest.html_url);$('workflowLive').replaceChildren(el('span','','GitHub 최신 작업: '+status+' · '+displayTime(latest.updated_at)+'. 작업 성공은 개별 출처 성공·휴대폰 수신을 보장하지 않습니다. '));
    if(url&&url.startsWith('https://github.com/'+match[1]+'/'+match[2]+'/actions/runs/'))$('workflowLive').append(outLink(url,'실행·배포 로그 ↗'));
    const saved=String(DATA.runtime?.collection?.run_id||'');
    if(saved&&saved!==String(latest.id))$('workflowLive').append(el('strong','',' 현재 화면의 수집 실행과 최신 작업이 다릅니다. 배포 완료 여부를 확인하세요.'));
  }catch{$('workflowLive').textContent='GitHub 최신 실행 상태를 실시간 확인하지 못했습니다(연결/권한/요청 제한 등). 위 내용은 마지막 저장 기록이며, 실패나 성공으로 단정하지 않습니다.';}
  finally{clearTimeout(timer);}
}
verifyLiveWorkflow();
