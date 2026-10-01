"""Check asynchronous public HTML readiness offline; no requests are made."""
from pathlib import Path
import sys,shutil
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from contest_alert.collect import wait_for_public_content
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which('chromium'),headless=True)
    page=browser.new_page()
    page.set_content('<h1>2026 AI 대회</h1><p>기간: 2026.09.14 ~ 2026.10.06</p><div id="later"></div>')
    page.evaluate('''() => setTimeout(()=>{document.querySelector('#later').textContent='참가 접수 2026.07.31 10:00 ~ 2026.10.06 14:00';window.ready=true;},350)''')
    wait_for_public_content(page,'https://aifactory.space/ko/competitions/9306')
    assert page.evaluate('Boolean(window.ready)'), 'Event banner alone was incorrectly considered a ready registration schedule'
    page.set_content('<div id="later"></div>')
    page.evaluate('''() => setTimeout(()=>{document.querySelector('#later').innerHTML='<a href="/contest/view?id=1234">AI 대회</a>';window.ready=true;},100)''')
    wait_for_public_content(page,'https://www.campuspick.com/contest')
    assert page.locator('a[href]').count()==1
    browser.close()
print('PASS: delayed registration content and delayed public listing')
