/* Browser-local progress/eligibility filters; no token or implicit remote writes. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.CMPlanner=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const STAGES={review:'검토 중',teaming:'팀원 모집 중',registered:'신청 완료',preparing:'준비 중',submitted:'제출 완료',passed:'참가 안 함'};
const ID=/^[A-Za-z0-9:_-]{1,120}$/;const forbidden=new Set(['__proto__','constructor','prototype']);
const FILTERS={audience:['all','undergraduate','graduate','general'],affiliation:['all','inha','unrestricted'],team:['all','individual','individual_or_team','team_required'],mode:['all','online','onsite','hybrid'],cost:['all','free','paid']};
const defaults=()=>({version:1,filters:{audience:'all',affiliation:'all',team:'all',mode:'all',cost:'all',unknown:true},records:{}});
function validDate(v){return typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&!isNaN(Date.parse(v+'T00:00:00Z'))&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v;}
function validTime(v){return typeof v==='string'&&/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(v);}
function parse(text){
 if(typeof text!=='string'||text.length>500000)throw Error('진행 상태 파일은 500KB 이하여야 합니다.');
 const d=JSON.parse(text),out=defaults();
 if(!d||d.version!==1||!d.records||Array.isArray(d.records)||typeof d.records!=='object')throw Error('진행 상태 파일 형식이 다릅니다.');
 for(const k in FILTERS)if(FILTERS[k].includes(d.filters?.[k]))out.filters[k]=d.filters[k];
 out.filters.unknown=d.filters?.unknown!==false;
 const pairs=Object.entries(d.records);if(pairs.length>1000)throw Error('진행 공고는 1000개까지입니다.');
 for(const [id,r] of pairs){
  if(!ID.test(id)||forbidden.has(id)||!r||Array.isArray(r)||!Object.hasOwn(STAGES,r.stage||'review'))throw Error('진행 상태 식별자/단계 오류');
  if(typeof(r.note??'')!=='string'||(r.note||'').length>1000)throw Error('메모는 1000자 이하여야 합니다.');
  const tasks=r.tasks||[];if(!Array.isArray(tasks)||tasks.length>12)throw Error('일정은 대회당 12개까지입니다.');
  out.records[id]={stage:r.stage||'review',note:r.note||'',tasks:tasks.map(t=>{
   if(!t||!ID.test(t.id)||forbidden.has(t.id)||typeof t.label!=='string'||!t.label.trim()||t.label.length>100||!validDate(t.date)||(t.time&&!validTime(t.time)))throw Error('할 일 날짜/시각/제목을 확인하세요.');
   return {id:t.id,label:t.label.trim(),date:t.date,time:t.time||null};
  })};
 }return out;
}
function store(storage,key){
 let memory=defaults(),ok=true;
 try{const raw=storage?.getItem(key);if(raw)memory=parse(raw);if(!storage)ok=false;}catch{ok=false;}
 return {get available(){return ok;},read:()=>structuredClone(memory),write(v){memory=parse(JSON.stringify(v));try{if(!storage)throw Error();storage.setItem(key,JSON.stringify(memory));ok=true;}catch{ok=false;}return ok;}};
}
function matches(conditions,filter){
 conditions=conditions||{};
 for(const key in FILTERS){const need=filter[key]||'all';if(need==='all')continue;const value=conditions[key]?.value||'unknown';
  if(value==='unknown'){if(filter.unknown===false)return false;continue;}
  if(key==='team'&&need==='individual'&&value==='individual_or_team')continue;
  if(Array.isArray(value)){if(!value.includes(need))return false;}
  else if(value!==need)return false;
 }return true;
}
function record(state,event){for(const id of [event.id,...(event.favorite_ids||[])])if(Object.hasOwn(state.records,id))return state.records[id];return {stage:'review',note:'',tasks:[]};}
function escapeICS(s){return String(s??'').replace(/\\/g,'\\\\').replace(/\r?\n/g,'\\n').replace(/;/g,'\\;').replace(/,/g,'\\,').replace(/\r/g,'');}
function fold(line){let n=0,out='',buffer='';for(const c of line){const len=new TextEncoder().encode(c).length;if(n+len>75){out+=buffer+'\r\n';buffer=' ';n=1;}buffer+=c;n+=len;}return out+buffer;}
function calendar(event,progress,now=new Date()){
 let dates=[];
 if(validDate(event.deadline)&&!event.registration_ambiguous)dates.push({id:'registration',label:'참가 신청 마감',date:event.deadline,time:event.registration_time_ambiguous?null:event.deadline_time,instant:event.registration_time_ambiguous?null:event.deadline_at});
 for(const [idx,m] of (event.milestones||[]).entries())if(validDate(m.date))dates.push({...m,id:'milestone-'+idx});
 for(const t of progress?.tasks||[])if(validDate(t.date))dates.push({...t,id:'local-'+t.id});
 if(!dates.length)return '';
 const stamp=now.toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,'');
 const lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Contest Monitor//v8//KO','CALSCALE:GREGORIAN','METHOD:PUBLISH'];
 for(const d of dates){
  let start;
  if(validTime(d.time)){const instant=d.instant&&Number.isFinite(Date.parse(d.instant))?new Date(d.instant):new Date(d.date+'T'+d.time+':00+09:00');start='DTSTART:'+instant.toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,'');}
  else start='DTSTART;VALUE=DATE:'+d.date.replaceAll('-','');
  lines.push('BEGIN:VEVENT','UID:'+escapeICS(event.id+'-'+d.id+'@contest-monitor'),'DTSTAMP:'+stamp,start,
   'SUMMARY:'+escapeICS(event.title+' · '+d.label),
   'DESCRIPTION:'+escapeICS((d.time?'한국시간 기준. ':'시각 미확인: 날짜 일정으로 저장. ')+(event.url||'')+'\n일회성 내보내기이며 이후 변경은 자동 동기화되지 않습니다.'));
  if(/^https?:\/\//.test(event.url||''))lines.push('URL:'+escapeICS(event.url));
  lines.push('END:VEVENT');
 }lines.push('END:VCALENDAR');return lines.map(fold).join('\r\n')+'\r\n';
}
function request(kind,payload){return '<!-- CONTEST_REQUEST_V8 -->\n```json\n'+JSON.stringify({version:1,kind,payload},null,2)+'\n```\n\n공개 저장소 요청입니다. 개인정보·토픽·비밀번호를 포함하지 않았습니다.';}
function issueURL(repo,kind,payload){
 const u=new URL(repo);
 if(u.origin!=='https://github.com'||!/^\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/?$/.test(u.pathname))throw Error('GitHub 저장소 주소를 확인할 수 없습니다.');
 u.pathname=u.pathname.replace(/\/$/,'')+'/issues/new';u.search='';
 u.searchParams.set('title','[Contest Monitor] '+({settings:'알림 설정 변경',add_notice:'공고 직접 추가',correct_notice:'공고 정보 수정',report:'잘못된 정보 신고'}[kind]||'요청'));
 u.searchParams.set('body',request(kind,payload));return u.href;
}
return {STAGES,FILTERS,defaults,parse,store,matches,record,calendar,request,issueURL,validDate,validTime};
});
