const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');
test('time runtime module is present',()=>assert.ok(fs.existsSync('web/runtime.js')));
if(fs.existsSync('web/runtime.js')){
const R=require('../web/runtime.js');
test('precise deadline and different device timezone',()=>{const i={deadline:'2026-09-23',deadline_time:'18:00'};assert.equal(R.status(i,new Date('2026-09-23T08:59:00Z')),'active');assert.equal(R.status(i,new Date('2026-09-23T09:00:00Z')),'closed');});
test('start time and date-only truthfulness',()=>{assert.equal(R.status({registration_start:'2026-09-23',registration_start_time:'14:00',deadline:'2026-09-30'},new Date('2026-09-23T13:00:00+09:00')),'upcoming');assert.equal(R.label({deadline:'2026-09-23'},new Date('2026-09-23T23:59:00+09:00')),'오늘 마감 · 시각 미확인');});
test('old yesterday comparison becomes explicitly dated',()=>{const c={status:'comparable',date:'2026-09-23',as_of:'2026-09-23T11:40:00+09:00',new_count:3};assert.equal(R.comparison(c,new Date('2026-09-24T00:00:00+09:00')).status,'stale');assert.equal(c.status,'comparable');});
test('bad dates and ambiguous clocks do not fabricate deadline',()=>{assert.equal(R.status({deadline:'2026-02-31'},new Date('2026-02-01T00:00:00+09:00')),'unknown');assert.equal(R.status({deadline:'2026-09-23',deadline_time:'10:00',registration_time_ambiguous:true},new Date('2026-09-23T20:00:00+09:00')),'active');});
}
