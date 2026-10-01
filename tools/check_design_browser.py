"""Offline UI acceptance tests for the supplied design and daily comparison.

This is not a WCAG certification; selected measurable criteria are checked.
No real collection, hosting or ntfy delivery is performed.
"""
import argparse,json,re,shutil,sys
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from contest_alert.render import embedded_json

def variant(html,status):
    soup=BeautifulSoup(html,'html.parser')
    data=json.loads(soup.select_one('#app-data').string)
    c=data['daily_comparison'];c['status']=status
    if status=='gap':c['base_date']='2026-09-19';c['base_at']='2026-09-19T11:43:00+09:00'
    else:
        c.update(new_count=None,new_ids=[],by_source=[],updated_count=0,initial_count=0,unverified_count=0)
        for row in data['items']:row['daily_new']=False
    soup.select_one('#app-data').string=embedded_json(data)
    return str(soup)

def run():
    parser=argparse.ArgumentParser();parser.add_argument('html',type=Path);parser.add_argument('--screenshots',type=Path)
    args=parser.parse_args();html=args.html.read_text(encoding='utf-8');reports=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
        for width,height in [(320,800),(390,844),(768,1024),(1280,1000),(1600,1000)]:
            page=browser.new_page(viewport={'width':width,'height':height},reduced_motion='reduce')
            page.set_default_timeout(3000)
            page.route('**/*',lambda route:route.abort());errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.set_content(html,wait_until='load')
            assert page.locator('#newCount').inner_text()=='3'
            if width<=960:
                assert page.locator('#repoLinkMobile').is_visible(), 'mobile GitHub shortcut is missing'
            assert page.locator('#dailySourceCounts .source-chip').count()==3
            assert not page.locator('#loading').is_visible()
            if width >= 1280:
                assert page.locator('.registration-line').first.bounding_box()['y'] < height-16, 'first registration period should be visible above fold'
            page.keyboard.press('Tab')
            assert page.locator('.skip-link').evaluate('(x)=>x===document.activeElement')
            assert page.locator('.skip-link').bounding_box()['y']>=0
            page.keyboard.press('Enter')
            assert page.locator('#mainContent').evaluate('(x)=>x===document.activeElement')
            page.locator('#showNew').click()
            assert page.locator('.contest').count()==3
            assert page.locator('#newOnly').is_checked()
            assert page.locator('#statusFilter').input_value()=='all'
            page.keyboard.press('Tab');page.keyboard.press('Shift+Tab')
            assert page.locator('#newOnly').evaluate('(x)=>getComputedStyle(x).outlineStyle')!='none'
            page.locator('#searchInput').fill('NO_MATCH_TEST')
            assert page.locator('#empty').is_visible()
            assert page.locator('#csvButton').is_disabled()
            page.locator('#resetFilters').click()
            assert page.locator('.contest').count()==8
            assert page.locator('#searchInput').evaluate('(x)=>x===document.activeElement')
            page.locator('#searchInput').fill('도시 수요예측')
            summary=page.locator('.contest summary');summary.focus();page.keyboard.press('Enter')
            assert page.locator('.contest-details').get_attribute('open') is not None
            page.wait_for_function("document.querySelector('.contest summary').textContent.includes('접기')")
            for a in page.locator('.open-link').all():
                assert '공고 원문' in a.get_attribute('aria-label')
            # Reproduce fixed-element clipping seen in a full-page screenshot after scroll.
            assert page.locator('.skip-link').bounding_box()['width']<=1,'inactive skip link can appear in scrolled screenshots'
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),f'{width}px overflow'
            # Long unbroken mixed-script text must wrap, without injecting HTML.
            page.locator('.contest h3 a').evaluate("x=>x.textContent='매우긴한국어제목TEST'.repeat(30)")
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert page.locator('body').evaluate('x=>getComputedStyle(x).fontSize')=='16px'
            assert page.locator('.tab').first.evaluate('x=>getComputedStyle(x).transitionDuration')=='0s'
            assert not errors,errors
            reports.append({'width':width,'result':'PASS','checks':22,'page_errors':errors})
            page.close()
        for status in ['baseline','gap','unobserved','stale']:
            page=browser.new_page(viewport={'width':390,'height':844})
            page.set_content(variant(html,status),wait_until='load')
            if status=='gap':
                assert '2026-09-19 대비 신규' in page.locator('#newCountLabel').inner_text()
                assert '어제 기록이 없어' in page.locator('#comparisonNote').inner_text()
            else:
                assert page.locator('#newCount').inner_text()=='—'
                assert page.locator('#showNew').is_disabled()
                assert page.locator('#newOnly').is_disabled()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            reports.append({'state':status,'result':'PASS'});page.close()
        if args.screenshots:
            args.screenshots.mkdir(exist_ok=True,parents=True)
            for width,height,name in [(1440,1040,'dashboard-desktop'),(390,844,'dashboard-mobile')]:
                page=browser.new_page(viewport={'width':width,'height':height})
                page.set_content(html,wait_until='load');page.evaluate('window.scrollTo(0,0)')
                page.screenshot(path=str(args.screenshots/(name+'.png')),full_page=False)
                page.close()
        browser.close()
    print(json.dumps(reports,ensure_ascii=False,indent=2))
if __name__=='__main__':run()
