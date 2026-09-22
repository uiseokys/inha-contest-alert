"""Offline browser acceptance on the documented selected-live-case replay."""
from pathlib import Path
import sys,argparse,shutil,json
from playwright.sync_api import sync_playwright
p=argparse.ArgumentParser();p.add_argument('page',type=Path);p.add_argument('--screenshots',type=Path);a=p.parse_args()
text=a.page.read_text();results=[]
with sync_playwright() as pw:
    b=pw.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
    for width,height in [(320,900),(390,844),(768,1024),(1440,1050)]:
        page=b.new_page(viewport={'width':width,'height':height});page.set_default_timeout(3000);errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)));page.route('**/*',lambda r:r.abort());page.set_content(text)
        assert page.locator('.contest').count()==7
        titles=page.locator('.contest h3').all_text_contents()
        assert not any('선발 결과' in x or '인턴십' in x for x in titles),titles
        assert page.locator('.contest').nth(0).get_attribute('id').startswith('contest-af')
        assert '2026-10-06 14:00' in page.locator('.contest').first.inner_text()
        page.locator('.contest').first.locator('summary').click()
        assert '국립공원공단' in page.locator('.contest').first.inner_text()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
        if a.screenshots:
            a.screenshots.mkdir(exist_ok=True,parents=True);page.screenshot(path=str(a.screenshots/f'v6-{width}.png'),full_page=True)
        page.locator('#kindFilter').select_option('contest');assert page.locator('.contest').count()==6
        page.locator('#kindFilter').select_option('program');assert page.locator('.contest').count()==1
        assert '세미나' in page.locator('.contest').first.inner_text()
        page.locator('#statusFilter').select_option('all');assert page.locator('.contest').count()==3
        page.locator('#searchInput').fill('없는검색결과');page.locator('#resetFilters').click();assert page.locator('.contest').count()==7
        page.locator('#searchInput').fill('딥보이스');assert page.locator('.contest').count()==1
        page.locator('.contest summary').click();assert '2026-09-29 10:00' in page.locator('.contest').inner_text()
        assert '뒤섞여' in page.locator('.contest').inner_text() or '역전' in page.locator('.contest').inner_text()
        assert not errors,errors
        results.append(dict(width=width,passed=True,page_errors=errors));page.close()
    b.close()
print(json.dumps(results,ensure_ascii=False,indent=2))
