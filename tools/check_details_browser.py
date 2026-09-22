"""UI regression test using a labeled synthetic preview. No external requests."""
import argparse, json, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

def main():
    parser=argparse.ArgumentParser();parser.add_argument('html',type=Path);parser.add_argument('--screenshots',type=Path)
    args=parser.parse_args();results=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
        for width,height,label in [(1280,1050,'desktop'),(390,844,'mobile')]:
            page=browser.new_page(viewport={'width':width,'height':height});errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.set_content(args.html.read_text(encoding='utf-8'),wait_until='load')
            page.locator('#sourceFilter').select_option(label='캠퍼스픽 · AI/데이터')
            assert page.locator('.contest').count()==1
            card=page.locator('.contest')
            assert card.locator('.registration-line').count()==1, '접수기간 바로 표시가 없음'
            assert '2026-09-01' in card.locator('.registration-line').inner_text()
            assert '2026-09-30' in card.locator('.registration-line').inner_text()
            assert card.locator('.contest-details').count()==1, '상세정보 패널이 없음'
            card.locator('summary').click()
            detail=card.locator('.contest-details')
            for text in ['2026-10-10','2026-10-12','18:00','예시데이터연구원','대학생','총상금']:
                assert text in detail.inner_text(),text
            assert detail.locator('a',has_text='안내 사이트').get_attribute('href')=='https://example.com/demo-official'
            assert detail.locator('a',has_text='신청 페이지').get_attribute('href')=='https://example.com/demo-apply'
            assert detail.locator('a',has_text='공고 원문').get_attribute('href')=='https://example.com/demo-contest/8'
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),label+' overflow'
            if args.screenshots:
                args.screenshots.mkdir(exist_ok=True,parents=True)
                page.screenshot(path=str(args.screenshots/f'{label}-details.png'),full_page=True)
            page.locator('#sourceFilter').select_option('all')
            page.locator('#searchInput').fill('예시데이터연구원')
            assert page.locator('.contest').count()==2,'주최기관 검색 실패'
            with page.expect_download() as dl:page.locator('#csvButton').click()
            content=Path(dl.value.path()).read_text(encoding='utf-8-sig')
            assert '접수시작일' in content and '대회종료일' in content and '예시데이터연구원' in content
            page.locator('#searchInput').fill('해커톤');assert page.locator('.contest').count()==1
            page.locator('.contest summary').click()
            assert '미확인' in page.locator('.contest-details').inner_text()
            assert not errors,errors
            results.append({'viewport':label,'result':'PASS','checks':16,'page_errors':errors});page.close()
        browser.close()
    print(json.dumps(results,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
