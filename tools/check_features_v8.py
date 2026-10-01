"""Offline interactive v8 checks. No GitHub issue or ntfy request is sent."""
from pathlib import Path
import argparse,json,shutil
from urllib.parse import urlsplit,parse_qs
from playwright.sync_api import sync_playwright,expect
p=argparse.ArgumentParser();p.add_argument('page',type=Path);p.add_argument('--screenshots',type=Path);a=p.parse_args()
results=[];requests=[]
with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
    for width,height in [(390,844),(1440,1000)]:
        context=browser.new_context(viewport={'width':width,'height':height},accept_downloads=True)
        context.route('**/*',lambda r:r.abort());errors=[]
        def load(saved=None):
            page=context.new_page();page.set_default_timeout(4000);page.on('pageerror',lambda e:errors.append(str(e)))
            page.evaluate("""seed=>{window.values={...seed};Object.defineProperty(window,'localStorage',{value:{getItem:k=>values[k]??null,setItem:(k,v)=>values[k]=String(v),removeItem:k=>delete values[k]}});window.requests=[];window.open=(u)=>{window.requests.push(u);return null;};}""",saved or {})
            page.set_content(a.page.read_text());return page
        page=load()
        assert page.locator('#notificationClock').inner_text()=='19:37'
        page.locator('#notificationTime').fill('07:25')
        page.locator('#notificationForm button[type=submit]').click()
        assert '아직 적용되지 않았습니다' in page.locator('#requestStatus').inner_text()
        assert '19:37' in page.locator('#serverRevision').inner_text()
        sent=page.evaluate('requests');body=parse_qs(urlsplit(sent[-1]).query)['body'][0]
        request=json.loads(body.split('```json\n')[1].split('\n```')[0])
        assert request['payload']['notification']['time']=='07:25'
        requests.append(body)
        # Only public IDs, not local private profile/memo, leave the browser.
        page.locator('.contest').first.locator('.favorite-button').click()
        n=len(sent);page.locator('#syncWatchlist').click()
        assert len(page.evaluate('requests'))==n
        page.locator('#syncConsent').check();page.locator('#syncWatchlist').click()
        body=parse_qs(urlsplit(page.evaluate('requests').pop()).query)['body'][0]
        q=json.loads(body.split('```json\n')[1].split('\n```')[0]);assert q['payload']['watchlist']==['evt_urban'];assert set(q['payload'])=={'watchlist','fields'};requests.append(body)
        page.locator('#searchInput').fill('제조 현장')
        card=page.locator('.contest');expect(card).to_have_count(1);card.locator('summary').click()
        expect(card.locator('.criteria-panel')).to_contain_text('무료')
        panel=card.locator('.planner-panel')
        panel.locator('select').select_option('registered')
        panel.locator('textarea').fill('PRIVATE_NOTE_ONLY_ON_DEVICE')
        panel.get_by_label('다음 할 일 (선택)').fill('제안서 제출')
        panel.get_by_label('할 일 날짜').fill('2026-11-03')
        panel.get_by_label('시각 (선택)').fill('16:45')
        panel.get_by_role('button',name='진행·할 일 저장',exact=True).click()
        expect(panel.locator('.saved-tasks')).to_contain_text('2026-11-03 16:45')
        with page.expect_download() as d:panel.get_by_role('button',name='신청·제출 일정 저장 (.ics)',exact=True).click()
        text=Path(d.value.path()).read_text();assert '20261103T074500Z' in text;assert '20261107T080000Z' in text;assert 'PRIVATE_NOTE' not in text
        with page.expect_download() as d:page.locator('#exportPlanner').click()
        backup=Path(d.value.path()).read_text();assert 'PRIVATE_NOTE_ONLY_ON_DEVICE' in backup
        panel.get_by_role('button',name='정보가 달라요',exact=True).click()
        page.locator('#reportCategory').select_option('date')
        page.locator('#reportDescription').fill('원문과 마감 시각이 다릅니다.')
        page.locator('#reportForm button[type=submit]').click()
        assert not page.locator('#reportDialog').is_visible()
        body=parse_qs(urlsplit(page.evaluate('requests').pop()).query)['body'][0];requests.append(body)
        assert 'PRIVATE_NOTE' not in body
        saved=page.evaluate('values');page.close();page=load(saved)
        page.locator('#searchInput').fill('제조 현장');card=page.locator('.contest');card.locator('summary').click()
        panel=card.locator('.planner-panel');assert panel.locator('select').input_value()=='registered'
        assert panel.locator('textarea').input_value()=='PRIVATE_NOTE_ONLY_ON_DEVICE'
        expect(panel.locator('.saved-tasks')).to_contain_text('제안서 제출')
        if a.screenshots:
            a.screenshots.mkdir(parents=True,exist_ok=True)
            card.scroll_into_view_if_needed()
            page.screenshot(path=str(a.screenshots/f'v8-details-{width}.png'),full_page=False)
        page.locator('#searchInput').fill('')
        page.locator('#eligibilityControls').locator('xpath=..').locator('summary').click()
        page.locator('#eligibility-cost').select_option('free');page.locator('#includeUnknown').uncheck()
        assert page.locator('.contest').count()==3
        page.locator('#includeUnknown').check();assert page.locator('.contest').count()==8
        page.locator('#manualURL').fill('https://example.org/new-ai')
        page.locator('#manualTitleInput').fill('2026 AI 데이터 경진대회')
        page.locator('#manualSummary').fill('공공데이터로 AI 모델을 개발하는 대회입니다.')
        page.locator('#manualChecked').fill('2026-10-01')
        page.locator('#manualStart').fill('2026-10-02');page.locator('#manualDeadline').fill('2026-11-03');page.locator('#manualClock').fill('18:30')
        page.locator('#manualEvidence').check();page.locator('#manualNoticeForm button[type=submit]').click()
        body=parse_qs(urlsplit(page.evaluate('requests').pop()).query)['body'][0];requests.append(body)
        assert 'add_notice' in body and 'PRIVATE_NOTE' not in body
        if a.screenshots:
            page.locator('#notification-settings').scroll_into_view_if_needed()
            page.screenshot(path=str(a.screenshots/f'v8-settings-{width}.png'),full_page=False)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert not errors,errors;results.append({'width':width,'passed':True,'page_errors':errors})
        context.close()
    browser.close()
# Validate the actual generated issue bodies against backend schema.
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from contest_alert.intake import parse_request
for body in requests:assert parse_request(body)
print(json.dumps({'results':results,'validated_request_bodies':len(requests),'remote_writes':0},ensure_ascii=False,indent=2))
