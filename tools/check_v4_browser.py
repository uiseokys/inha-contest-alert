"""Actual Chromium checks of ordering, common date fields and long-title access."""
from pathlib import Path
import argparse,json,shutil
from playwright.sync_api import sync_playwright

def main():
    p=argparse.ArgumentParser();p.add_argument('html',type=Path);p.add_argument('--screenshots',type=Path);args=p.parse_args()
    reports=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
        for width,height in [(320,900),(390,844),(768,1024),(1440,1100)]:
            page=browser.new_page(viewport={'width':width,'height':height});errors=[]
            page.set_default_timeout(3000)
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.route('**/*',lambda r:r.abort())
            page.set_content(args.html.read_text(),wait_until='load')
            assert page.locator('#sortFilter').input_value()=='remaining','default not longest remaining'
            ids=[x.get_attribute('id').replace('contest-','') for x in page.locator('.contest').all()]
            assert ids[:2]==['3','6'],ids
            assert set(ids[-2:])=={'2','5'},ids
            cards=page.locator('.contest')
            assert all(c.locator('.date-pair').count()==2 for c in cards.all())
            assert all('접수 시작' in c.locator('.registration-line').inner_text() and '접수 마감' in c.locator('.registration-line').inner_text() for c in cards.all())
            title=cards.first.locator('h3 a')
            assert title.evaluate('x=>getComputedStyle(x).webkitLineClamp')=='2'
            assert title.evaluate('x=>x.clientHeight<=parseFloat(getComputedStyle(x).lineHeight)*2+2')
            cards.first.locator('summary').click()
            assert '대회명 (전체)' in cards.first.locator('.contest-details').inner_text()
            assert title.inner_text() in cards.first.locator('.contest-details').inner_text()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.locator('#statusFilter').select_option('all')
            assert page.locator('.contest').last.get_attribute('id')=='contest-7'
            page.locator('#sortFilter').select_option('deadline')
            assert '제조' in page.locator('.contest h3').first.inner_text()
            page.locator('#searchInput').fill('NO_MATCH_987')
            page.locator('#resetFilters').click()
            assert page.locator('#sortFilter').input_value()=='remaining'
            page.locator('#sourceFilter').select_option(label='캠퍼스픽 · AI/데이터')
            page.locator('.contest summary').click()
            assert '날짜 근거' in page.locator('.contest-details').inner_text()
            assert page.locator('.date-evidence-link').get_attribute('href')=='https://example.com/demo-contest/8'
            assert not errors,errors
            if args.screenshots:
                args.screenshots.mkdir(parents=True,exist_ok=True)
                page.screenshot(path=str(args.screenshots/f'details-{width}.png'),full_page=True)
                page.locator('#searchInput').fill('NO_MATCH_987')
                page.locator('#resetFilters').click();page.evaluate('scrollTo(0,0)')
                page.screenshot(path=str(args.screenshots/f'dashboard-{width}.png'),full_page=True)
            reports.append({'width':width,'result':'PASS','page_errors':errors})
            page.close()
        browser.close()
    print(json.dumps(reports,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
