/* Shared pure browser/Node clock rules. The page never invents a missing clock. */
(function(root){
  'use strict';
  const dayOf=now=>new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Seoul'}).format(now);
  function dayEpoch(value){
    if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value))return NaN;
    const n=Date.parse(value+'T00:00:00+09:00');
    return Number.isFinite(n)&&dayOf(new Date(n))===value?n:NaN;
  }
  function instant(item,field){
    const day=item[field],clock=item[field==='deadline'?'deadline_time':'registration_start_time'];
    if(!Number.isFinite(dayEpoch(day))||item.registration_time_ambiguous||typeof clock!=='string'||!/^\d{2}:\d{2}(?::\d{2})?$/.test(clock))return NaN;
    if(item.registration_timezone&&item.registration_timezone!=='Asia/Seoul'){
      const normalized=item[field+'_at'];return typeof normalized==='string'&&/T.*(?:Z|[+-]\d{2}:\d{2})$/.test(normalized)?Date.parse(normalized):NaN;
    }
    const [hour,minute,second=0]=clock.split(':').map(Number);
    if(hour>24||minute>59||second>59||(hour===24&&(minute||second)))return NaN;
    return dayEpoch(day)+(hour*3600+minute*60+second)*1000;
  }
  function status(item,now=new Date()){
    const today=dayOf(now),d=dayEpoch(today),end=item.registration_ambiguous?NaN:dayEpoch(item.deadline),start=item.registration_ambiguous?NaN:dayEpoch(item.registration_start);
    if(item.platform_status==='closed')return 'closed';
    const ending=instant(item,'deadline'),starting=instant(item,'registration_start');
    if(Number.isFinite(end)&&(Number.isFinite(ending)?+now>=ending:end<d))return 'closed';
    if(Number.isFinite(start)&&(Number.isFinite(starting)?+now<starting:start>d))return 'upcoming';
    if(Number.isFinite(end))return 'active';
    const seen=dayEpoch((item.last_seen||'').slice(0,10));
    if(item.platform_status==='open'&&Number.isFinite(seen)&&seen<=d&&d-seen<=3*86400000)return 'active';
    return 'unknown';
  }
  function label(item,now=new Date()){
    const s=status(item,now);
    if(s==='closed')return '마감 / 종료';if(s==='upcoming')return '접수 예정';if(s==='unknown')return '마감 미확인';
    if(item.deadline===dayOf(now)&&!Number.isFinite(instant(item,'deadline')))return '오늘 마감 · 시각 미확인';
    return item.deadline?'기한 남음':'접수중 표시 · 마감 확인 필요';
  }
  function comparison(c,now=new Date()){
    if(!c)return {status:'baseline',new_count:null,new_ids:[],by_source:[]};
    const stamp=Date.parse(c.as_of||''),observed=Number.isFinite(stamp)?dayOf(new Date(stamp)):'';
    if(observed&&observed!==dayOf(now))return {...c,status:'stale',saved_status:c.status,saved_date:observed,saved_new_count:c.new_count,saved_new_event_count:c.new_event_count,new_count:null,new_ids:[],new_event_count:null,new_event_ids:[],by_source:[],deadline_extensions:[]};
    return {...c};
  }
  function compareItems(a,b,mode,now=new Date()){
    const tier=i=>status(i,now)==='closed'?2:(!i.registration_ambiguous&&Number.isFinite(dayEpoch(i.deadline))?0:1);
    if(mode==='remaining'||mode==='deadline'){
      const t=tier(a)-tier(b);if(t)return t;
      if(tier(a)===0){const x=dayEpoch(a.deadline),y=dayEpoch(b.deadline);if(x!==y)return mode==='remaining'?y-x:x-y;
        const ta=instant(a,'deadline'),tb=instant(b,'deadline');if(Number.isFinite(ta)!==Number.isFinite(tb))return Number.isFinite(ta)?-1:1;if(Number.isFinite(ta)&&Number.isFinite(tb)&&ta!==tb)return mode==='remaining'?tb-ta:ta-tb;
      }
      return String(a.title||'').localeCompare(String(b.title||''),'ko');
    }
    return String(b.posted_at||b.first_seen||'').localeCompare(String(a.posted_at||a.first_seen||''));
  }
  const api={dayOf,dayEpoch,instant,status,label,comparison,compareItems};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.CMRuntime=api;
})(globalThis);
