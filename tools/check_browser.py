"""Local browser smoke test. Pass a synthetic preview, not a live website."""
from pathlib import Path
import argparse,json,shutil
from playwright.sync_api import sync_playwright

def main():
    p=argparse.ArgumentParser();p.add_argument('html',type=Path);p.add_argument('--screenshots',type=Path);args=p.parse_args()
    results=[]
    with sync_playwright() as pw:
        opts={'headless':True}
        if shutil.which('chromium'):opts['executable_path']=shutil.which('chromium')
        browser=pw.chromium.launch(**opts)
        for width,height,name in [(1280,1000,'desktop'),(390,844,'mobile')]:
            page=browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1)
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.set_content(args.html.read_text(encoding='utf-8'), wait_until='load');page.wait_for_selector('.contest')
            assert page.locator('.contest').count()==8
            assert page.locator('#demoBanner').is_visible()
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'),name+' overflow'
            if args.screenshots:
                args.screenshots.mkdir(parents=True,exist_ok=True)
                page.screenshot(path=str(args.screenshots/f'{name}.png'),full_page=True)
            page.locator('#searchInput').fill('제조');assert page.locator('.contest').count()==1
            page.locator('#searchInput').fill('');page.locator('[data-group=inha]').click();assert page.locator('.contest').count()==5
            page.locator('[data-group=all]').click();page.locator('#statusFilter').select_option('closed');assert page.locator('.contest').count()==1
            page.locator('#statusFilter').select_option('review');page.locator('#newOnly').check();assert page.locator('.contest').count()==3
            page.locator('#sortFilter').select_option('deadline');assert '제조' in page.locator('.contest h3').first.inner_text()
            with page.expect_download() as dl:page.locator('#csvButton').click()
            assert dl.value.suggested_filename.endswith('.csv')
            page.locator('#searchInput').fill('NO_MATCH_999');assert page.locator('#empty').is_visible()
            assert not errors,errors
            results.append({'viewport':name,'checks':10,'result':'PASS','page_errors':errors});page.close()
        browser.close()
    print(json.dumps(results,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
