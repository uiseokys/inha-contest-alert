"""Offline UI failure-state checks with denied storage and stubbed public API."""
from pathlib import Path
import argparse,shutil,json
from playwright.sync_api import sync_playwright,expect
p=argparse.ArgumentParser();p.add_argument('page',type=Path);a=p.parse_args();text=a.page.read_text();result=[]
with sync_playwright() as pw:
 b=pw.chromium.launch(headless=True,executable_path=shutil.which('chromium'));page=b.new_page(viewport={'width':390,'height':844});page.route('**/*',lambda r:r.abort());errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 # about:blank opaque origin rejects native localStorage; production catches it.
 page.set_content(text);expect(page.locator('#personalNotice')).to_contain_text('저장소');page.locator('.favorite-button').first.click();expect(page.locator('.favorite-button').first).to_have_attribute('aria-pressed','true');assert page.locator('.contest').count()==8;result.append('denied native storage -> in-memory favorites still functional')
 page.evaluate("""()=>{DATA.demo=false;DATA.runtime.collection.run_id='1';window.fetch=async(url,opts)=>{if(opts.credentials!=='omit')throw Error('credentials leak');return new Response(JSON.stringify({workflow_runs:[{id:2,status:'completed',conclusion:'failure',html_url:'https://github.com/example/contest-demo/actions/runs/2',updated_at:'2026-09-23T12:05:00+09:00'}]}),{status:200});};verifyLiveWorkflow();}""")
 expect(page.locator('#workflowLive')).to_contain_text('실패');expect(page.locator('#workflowLive')).to_contain_text('다릅니다');result.append('stubbed latest workflow failure + run mismatch distinguished from cached metadata')
 page.evaluate("window.fetch=async()=>{throw Error('offline')};verifyLiveWorkflow()")
 expect(page.locator('#workflowLive')).to_contain_text('단정하지 않습니다');result.append('API failure does not imply a successful deployment')
 assert not errors,errors;b.close()
print(json.dumps({'checks':result,'page_errors':errors},ensure_ascii=False,indent=2))
