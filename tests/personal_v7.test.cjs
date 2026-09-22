const test=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');
const modulePath='../web/personal.js';
test('personal preferences module exists',()=>assert.ok(fs.existsSync(require('node:path').join(__dirname,modulePath))));
if(fs.existsSync(require('node:path').join(__dirname,modulePath))){
 const P=require(modulePath);const event={id:'evt_new',favorite_ids:['old','evt_old','evt_new']};
 test('local default retains farthest deadline ordering',()=>assert.equal(P.defaults().filters.sort,'remaining'));
 test('imports merge favorite aliases into a stable event id',()=>assert.deepEqual(P.normalizeFavorites(['old'],[event]),['evt_new']));
 test('unknown favorite ids survive for archived events',()=>assert.deepEqual(P.normalizeFavorites(['archived'],[event]),['archived']));
 test('unsafe strings rejected',()=>assert.throws(()=>P.parseImport(JSON.stringify({version:1,favorites:['<script>x</script>']})),/관심/));
 test('oversized import is rejected',()=>assert.throws(()=>P.parseImport('x'.repeat(262145)),/크기/));
 test('too many favorites rejected',()=>assert.throws(()=>P.parseImport(JSON.stringify({version:1,favorites:Array(1001).fill('x')})),/1000/));
 test('invalid JSON and wrong shape rejected',()=>{assert.throws(()=>P.parseImport('{'));assert.throws(()=>P.parseImport('[]'));assert.throws(()=>P.parseImport('{"version":2,"favorites":[]}'));});
 test('import is whitelisted and pollution proof',()=>{const value=P.parseImport('{"version":1,"favorites":["evt_a"],"__proto__":{"bad":true},"topic":"SECRET","filters":{"sort":"oldest","kind":"contest","field":"model_development"}}');assert.equal({}.bad,undefined);assert.equal(value.topic,undefined);assert.equal(value.filters.sort,'remaining');assert.equal(value.filters.kind,'contest');});
 test('storage forbidden uses functional memory fallback',()=>{const store=P.store({getItem(){throw Error('blocked')},setItem(){throw Error('blocked')}},'test');assert.equal(store.read().favorites.length,0);const v=P.defaults();v.favorites=['evt_a'];assert.equal(store.write(v),false);assert.deepEqual(store.read().favorites,['evt_a']);});
 test('corrupted storage returns safe defaults',()=>{const store=P.store({getItem:()=>'{',setItem:()=>{}},'test');assert.deepEqual(store.read(),P.defaults());assert.equal(store.available,false);});
 test('valid export roundtrip preserves filters without copying unknown keys',()=>{const original=P.defaults();original.favorites=['evt_a'];original.filters.query='데이터';original.filters.onlyFavorites=true;const text=P.exportJSON(original);assert.deepEqual(P.parseImport(text),original);});
 test('filter validation keeps only supported values and bounded query',()=>{const result=P.filters({query:'a'.repeat(600),group:'evil',kind:'program',newOnly:true,onlyFavorites:true,field:'creative_ai'});assert.equal(result.query.length,300);assert.equal(result.group,'all');assert.equal(result.kind,'program');assert.equal(result.field,'creative_ai');});
}
