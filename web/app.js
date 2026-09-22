'use strict';
const DATA=JSON.parse(document.getElementById('app-data').textContent);
const $=id=>document.getElementById(id);
const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
const safeURL=value=>{try{const u=new URL(value);return ['https:','http:'].includes(u.protocol)&&!u.username&&!u.password?u.href:'';}catch{return '';}};
const today=DATA.demo&&DATA.updated_at?DATA.updated_at.slice(0,10):new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Seoul'}).format(new Date());
const epoch=d=>Date.parse(d+'T00:00:00+09:00');
const days=d=>Math.round((epoch(d)-epoch(today))/86400000);
function status(item){if(item.deadline&&days(item.deadline)<0)return 'closed';if(item.registration_start&&days(item.registration_start)>0)return 'upcoming';if(item.platform_status==='closed')return 'closed';if(item.deadline)return 'active';if(item.platform_status==='open'&&item.last_seen&&days(item.last_seen.slice(0,10))>=-3)return 'active';return 'unknown';}
function statusLabel(item){const s=status(item);return s==='active'?(item.deadline?'기한 남음':'접수중 표시'):({upcoming:'접수 예정',closed:'마감 / 종료',unknown:'마감 미확인'}[s]);}
function outLink(url,text,cls){const a=el('a',cls,text);const safe=safeURL(url);if(safe){a.href=safe;a.target='_blank';a.rel='noopener noreferrer';}return a;}
let selectedGroup='all';let filtered=[];
if(DATA.demo)$('demoBanner').hidden=false;
if(safeURL(DATA.repo_url)){for(const id of ['repoLink','repoLinkMobile']){$(id).href=DATA.repo_url;$(id).hidden=false;$(id).target='_blank';$(id).rel='noopener noreferrer';}}
if(DATA.updated_at){$('updatedAt').textContent='마지막 수집 시도 '+new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',dateStyle:'medium',timeStyle:'short'}).format(new Date(DATA.updated_at));if(!DATA.demo&&Date.now()-Date.parse(DATA.updated_at)>36*3600000){$('staleBanner').hidden=false;$('staleBanner').textContent='목록이 36시간 이상 갱신되지 않았습니다. GitHub Actions 실행 상태와 출처별 수집 상태를 확인하세요.';}}
else{$('staleBanner').hidden=false;$('staleBanner').textContent='아직 첫 수집 전입니다. 저장소의 SETUP.md를 따라 설정하고 Actions에서 수동 실행하세요.';}
const sources=DATA.sources||[];const enabled=sources.filter(s=>s.status!=='disabled');const failed=enabled.filter(s=>!['ok'].includes(s.status));
$('totalCount').textContent=DATA.items.filter(i=>status(i)!=='closed').length;
renderComparison();
$('dueCount').textContent=DATA.items.filter(i=>i.deadline&&days(i.deadline)>=0&&days(i.deadline)<=7).length;
$('sourceCount').textContent=enabled.filter(s=>s.status==='ok').length+' / '+enabled.length;
$('sourceNote').textContent=failed.length?failed.length+'곳 확인 필요':'설정된 수집 범위 기준';
const sourceNames=new Map(sources.map(s=>[s.name,s.name]));DATA.items.forEach(i=>sourceNames.set(i.source_name,i.source_name));
for(const name of [...sourceNames.keys()].sort()){$('sourceFilter').appendChild(new Option(name,name));}
const healthLabels={ok:'정상',partial:'부분 실패',error:'수집 실패',disabled:'직접 확인',pending:'미확인'};
for(const s of sources){const row=el('div','health-row');const title=el('div','health-title');title.append(outLink(s.url,s.name+' ↗'),el('span',s.status,healthLabels[s.status]||s.status));row.append(title,el('p','',s.message||'첫 수집 전'));if(s.detail_errors)row.append(el('p','',`상세 페이지 확인 실패 ${s.detail_errors}건 · 날짜는 원문 확인`));if(s.detail_unconfirmed)row.append(el('p','',`상세정보 추출 미확인 ${s.detail_unconfirmed}건 · 원문 직접 확인`));$('sourceHealth').append(row);}
if(!sources.length)$('sourceHealth').append(el('p','','첫 실행 후 수집 상태가 표시됩니다.'));
function renderComparison(){
  const c=DATA.daily_comparison||{status:'baseline',new_count:null,new_ids:[],by_source:[]};
  const valid=['comparable','gap'].includes(c.status);
  const label=c.status==='gap'?c.base_date+' 대비 신규':'어제 대비 신규';
  $('newCountLabel').textContent=label;
  $('newCount').textContent=valid?c.new_count:'—';
  $('newCountNote').textContent=valid?'새로 확인한 공고 · 목록 보기':c.status==='baseline'?'첫 저장 후 다음 날부터 비교':'비교 가능한 수집 기록 없음';
  $('showNew').disabled=!valid||c.new_count===0;
  $('newOnly').disabled=!valid;
  $('newOnlyLabel').textContent=c.status==='gap'?'비교 기준 이후 신규만':'어제 대비 신규만';
  const titles={baseline:'어제 대비 비교 준비 중',stale:'오늘 수집 기록이 없어 비교할 수 없습니다.',unobserved:'수집 실패로 신규 건수를 비교할 수 없습니다.'};
  $('comparisonTitle').textContent=valid?(label+' '+c.new_count+'건 · 기존 공고 변경 '+c.updated_count+'건'):titles[c.status]||titles.baseline;
  const shortTime=value=>new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(value));
  $('comparisonRange').textContent=c.base_at&&c.as_of?'비교 구간  '+shortTime(c.base_at)+' → '+shortTime(c.as_of)+' (한국시간)':'';
  const chips=(c.by_source||[]).map(s=>{const chip=el('span','source-chip',s.name);chip.append(el('strong','',s.count+'건'));return chip;});
  $('dailySourceCounts').replaceChildren(...chips);
  const notes=[];
  if(c.status==='baseline')notes.push('기존 목록은 비교 기준으로만 저장합니다. 다음 날 수집부터 신규 건수를 표시합니다.');
  if(c.status==='gap')notes.push('어제 기록이 없어 가장 최근의 이전 수집 날짜와 비교했습니다.');
  if(c.partial)notes.push('일부 출처의 수집이 불완전하므로 확인된 범위만 집계했습니다.');
  if(c.initial_count)notes.push('새 출처 최초 적재 '+c.initial_count+'건은 신규 집계에서 제외했습니다.');
  if(c.unverified_count)notes.push('이전 수집 불완전 출처의 추가 확인 '+c.unverified_count+'건은 별도입니다.');
  notes.push('신규는 새로 확인한 공고 주소 기준입니다. 다른 출처의 같은 대회는 중복될 수 있습니다.');
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
  fact(grid,'접수기간',period(item.registration_start,item.deadline));
  fact(grid,'대회·행사기간',period(item.event_start,item.event_end));
  if(item.registration_text)fact(grid,'접수기간 원문 표기',item.registration_text,true);
  fact(grid,'주최 / 주관',item.organizer);fact(grid,'참가 대상 / 팀 구성',item.eligibility);
  fact(grid,'상금 / 혜택',item.benefits);fact(grid,'대회 주제',item.summary);
  if(item.schedule_text)fact(grid,'세부 일정 안내',item.schedule_text,true);
  panel.append(grid);
  if(item.registration_ambiguous)panel.append(el('p','detail-warning','접수기간이 여러 개이거나 날짜를 확정할 수 없습니다. 원문에서 해당 트랙과 기간을 확인하세요.'));
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
  const source=el('div','source-block');source.append(el('span','source-name',item.source_name),el('span','pill '+status(item),statusLabel(item)));
  const body=el('div','contest-body');const h=el('h3');h.append(outLink(item.url,item.title));
  if(item.daily_new)h.append(el('span','new-badge','신규'));
  body.append(h,el('p','registration-line','접수 '+period(item.registration_start,item.deadline)));
  if(item.organizer)body.append(el('p','organizer-line','주최 / 주관 '+item.organizer));
  const meta=el('div','metadata');meta.append(el('span','',item.posted_at?'게시 '+item.posted_at:'게시일 미확인'),el('span','','첫 확인 '+(item.first_seen||'').slice(0,10)));body.append(meta);
  const due=el('div','deadline');
  if(item.deadline){const d=days(item.deadline);due.append(el('strong',d>=0&&d<=7?'urgent':'',d<0?'마감일 지남':d===0?'오늘 마감일':'D−'+d),el('small','',item.deadline));}
  else{due.append(el('strong','','원문 확인'),el('small','','마감일 미확인'));}
  const open=outLink(item.url,'↗','open-link');open.setAttribute('aria-label',item.title+' 공고 원문 열기 (새 탭)');
  row.append(source,body,due,open,detailPanel(item));return row;
}
function update(){const query=$('searchInput').value.trim().toLowerCase();const source=$('sourceFilter').value;const state=$('statusFilter').value;const onlyNew=$('newOnly').checked;filtered=DATA.items.filter(i=>{const s=status(i);return(selectedGroup==='all'||i.group===selectedGroup)&&(source==='all'||i.source_name===source)&&(state==='all'||(state==='review'?s!=='closed':s===state))&&(!onlyNew||i.daily_new)&&(!query||[i.title,i.source_name,i.organizer,i.eligibility,i.summary,i.benefits].filter(Boolean).join(' ').toLowerCase().includes(query));});filtered.sort((a,b)=>{if($('sortFilter').value==='deadline'){return(a.deadline||'9999').localeCompare(b.deadline||'9999');}return(b.posted_at||b.first_seen||'').localeCompare(a.posted_at||a.first_seen||'');});$('items').replaceChildren(...filtered.map(card));$('resultCount').textContent=filtered.length+'개 공고';$('empty').hidden=filtered.length!==0;$('csvButton').disabled=filtered.length===0;$('loading').hidden=true;}
$('newOnly').addEventListener('change',()=>{if($('newOnly').checked)$('statusFilter').value='all';});
for(const id of ['searchInput','sourceFilter','statusFilter','sortFilter','newOnly'])$(id).addEventListener(id==='searchInput'?'input':'change',update);
for(const button of document.querySelectorAll('[data-group]'))button.addEventListener('click',()=>{selectedGroup=button.dataset.group;document.querySelectorAll('[data-group]').forEach(b=>{const yes=b===button;b.classList.toggle('selected',yes);b.setAttribute('aria-pressed',String(yes));});update();});
$('csvButton').addEventListener('click',()=>{const quote=value=>{let s=String(value??'');if(/^[\s]*[=+@\-\t\r]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';};const rows=[['공고명','출처','접수시작일','접수마감일','접수기간 원문','대회시작일','대회종료일','일정안내','주최기관','참가대상','혜택','주제','안내사이트','신청링크','상태','공고원문','상세확인일'],...filtered.map(i=>[i.title,i.source_name,i.registration_start,i.deadline,i.registration_text,i.event_start,i.event_end,i.schedule_text,i.organizer,i.eligibility,i.benefits,i.summary,safeURL(i.website_url),safeURL(i.application_url),statusLabel(i),safeURL(i.url),i.detail_checked_at])];const blob=new Blob(['\ufeff'+rows.map(r=>r.map(quote).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'});const url=URL.createObjectURL(blob);const a=el('a');a.href=url;a.download='contests-'+today+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
function resetFilters(){
  selectedGroup='all';$('searchInput').value='';$('sourceFilter').value='all';$('statusFilter').value='review';$('sortFilter').value='newest';$('newOnly').checked=false;
  document.querySelectorAll('[data-group]').forEach(b=>{const active=b.dataset.group==='all';b.classList.toggle('selected',active);b.setAttribute('aria-pressed',String(active));});
  update();
}
$('resetFilters').addEventListener('click',()=>{resetFilters();$('searchInput').focus();});
$('showNew').addEventListener('click',()=>{resetFilters();$('statusFilter').value='all';$('newOnly').checked=true;update();$('opportunities').scrollIntoView({block:'start'});$('newOnly').focus({preventScroll:true});});
document.querySelectorAll('.nav-item').forEach(a=>a.addEventListener('click',()=>{document.querySelectorAll('.nav-item').forEach(x=>{x.classList.toggle('current',x===a);if(x===a)x.setAttribute('aria-current','location');else x.removeAttribute('aria-current');});}));
update();
