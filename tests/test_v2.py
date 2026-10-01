"""Synthetic public HTML fixtures. Not a claim of live CampusPick ingestion."""
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from contest_alert import core, render

NOW=datetime(2026,9,22,11,40,tzinfo=ZoneInfo('Asia/Seoul'))
SRC={'id':'campuspick','name':'캠퍼스픽 · AI/데이터','url':'https://www.campuspick.com/contest','kind':'campuspick','group':'external','mode':'ai_platform'}
LIST='''<main><a href="/contest/view?id=10"><h2>2026 AI활용 공모전</h2><p>예시 기관</p></a>
<a href="/contest/view?id=11"><h2>2026 데이터 분석 챌린지</h2></a>
<a href="/contest/view?id=12"><h2>Chair design contest</h2></a>
<a href="/contest/view?id=13"><h2>제조 예측 모델 만들기</h2><span>분야: 데이터 / AI</span></a>
<a href="/activity/view?id=14"><h2>AI 교육</h2></a></main>'''
DETAIL='''<main><h1>예시 대회</h1><table>
<tr><th>접수기간</th><td>2026.09.01 ~ 2026.09.30 18:00</td></tr>
<tr><th>대회기간</th><td>2026.10.10 ~ 2026.10.12</td></tr>
<tr><th>주최</th><td>예시 연구원</td></tr>
<tr><th>참가 대상</th><td>대학생 및 대학원생</td></tr>
<tr><th>상금 및 혜택</th><td>총상금 300만원</td></tr></table>
<p>공모 주제: 공공데이터를 이용한 수요 예측</p>
<p><a href="https://host.example/contest">공식 홈페이지</a></p>
<p><a href="https://apply.example/form">참가 신청</a></p>
</main>'''

def record(**kwargs):
    out={'id':'r','title':'AI 대회','url':'https://x.example/1','source_id':'x','source_name':'출처','group':'external','deadline':None,'registration_start':None,'posted_at':None,'platform_status':None}
    out.update(kwargs);return out

class CampusPickTests(unittest.TestCase):
    def test_recognizes_only_contests_and_filters_ai_not_chair(self):
        items,count=core.parse_listing(LIST,SRC)
        self.assertEqual(count,4)
        self.assertEqual({x['url'].split('=')[-1] for x in items},{'10','11','13'})
    def test_ai_attached_to_korean_and_statistics_are_relevant(self):
        self.assertTrue(core.relevant('AI영상 공모전','ai_contest'))
        self.assertTrue(core.relevant('통계 활용 경진대회','ai_contest'))
        self.assertFalse(core.relevant('Chair design contest','ai_platform'))
    def test_subject_without_contest_word_supported_on_contest_platform(self):
        self.assertTrue(core.relevant('제조 데이터 예측','ai_platform'))
    def test_count_badge_is_not_title_or_date(self):
        html='<a href="/contest/view?id=10"><h2>AI 공모전</h2><span>D-3</span><span>관심 99</span></a>'
        items,count=core.parse_listing(html,SRC)
        self.assertEqual(count,1)
        self.assertEqual(items[0]['title'],'AI 공모전')
        self.assertIsNone(items[0]['deadline'])

class DetailTests(unittest.TestCase):
    def test_registration_and_event_are_separate(self):
        f=core.detail_fields(DETAIL)
        self.assertEqual(f.get('registration_start'),'2026-09-01')
        self.assertEqual(f.get('deadline'),'2026-09-30')
        self.assertEqual(f.get('event_start'),'2026-10-10')
        self.assertEqual(f.get('event_end'),'2026-10-12')
    def test_information_and_links_are_extracted(self):
        f=core.detail_fields(DETAIL)
        self.assertEqual(f.get('organizer'),'예시 연구원')
        self.assertEqual(f.get('eligibility'),'대학생 및 대학원생')
        self.assertEqual(f.get('benefits'),'총상금 300만원')
        self.assertEqual(f.get('summary'),'공공데이터를 이용한 수요 예측')
        self.assertEqual(f.get('website_url'),'https://host.example/contest')
        self.assertEqual(f.get('application_url'),'https://apply.example/form')
    def test_original_registration_text_keeps_time(self):
        f=core.detail_fields(DETAIL)
        self.assertIn('18:00',f.get('registration_text',''))
    def test_definition_list_fields(self):
        f=core.detail_fields('<article><dl><dt>접수기간</dt><dd>2026년 9월 1일 ~ 2026년 9월 30일</dd><dt>주최기관</dt><dd>예시 기관</dd></dl></article>')
        self.assertEqual(f.get('deadline'),'2026-09-30')
        self.assertEqual(f.get('organizer'),'예시 기관')
    def test_same_year_abbreviated_range_supported(self):
        self.assertEqual(core.registration_dates('접수기간: 2026.09.01 ~ 09.30'),('2026-09-01','2026-09-30'))
    def test_missing_year_stays_unknown(self):
        self.assertEqual(core.registration_dates('접수기간: 9/1 ~ 9/30'),(None,None))
    def test_ambiguous_multitrack_raw_text_retained(self):
        f=core.detail_fields('<main><p>접수기간: 2026.09.01 ~ 2026.09.10</p><p>추가 접수기간: 2026.09.20 ~ 2026.09.30</p></main>')
        self.assertIsNone(f.get('deadline'))
        self.assertIn('2026.09.10',f.get('registration_text',''))
        self.assertIn('2026.09.30',f.get('registration_text',''))
    def test_event_only_not_used_as_registration(self):
        f=core.detail_fields('<article><p>행사기간: 2026.10.10 ~ 2026.10.12</p></article>')
        self.assertIsNone(f.get('deadline'))
        self.assertEqual(f.get('event_start'),'2026-10-10')
    def test_untrusted_script_link_is_ignored(self):
        f=core.detail_fields('<main><p><a href="javascript:alert(1)">공식 홈페이지</a></p></main>')
        self.assertFalse(f.get('website_url'))
    def test_no_arbitrary_footer_homepage(self):
        f=core.detail_fields('<main><p>접수 마감: 2026.09.30</p></main><footer><a href="https://wrong.example/">홈페이지</a></footer>')
        self.assertFalse(f.get('website_url'))

class PersistenceTests(unittest.TestCase):
    def test_details_survive_listing_only_refresh(self):
        s=core.empty_state();r=record(organizer='연구원',eligibility='대학생',event_start='2026-10-01',website_url='https://host.example/')
        core.merge_items(s,[r],NOW)
        core.merge_items(s,[record()],NOW+timedelta(days=1))
        self.assertEqual(s['items']['r'].get('organizer'),'연구원')
        self.assertEqual(s['items']['r'].get('event_start'),'2026-10-01')
        self.assertEqual(len(s['changes']),1)
    def test_eligibility_change_is_recorded(self):
        s=core.empty_state();core.merge_items(s,[record(eligibility='대학생')],NOW)
        core.merge_items(s,[record(eligibility='누구나')],NOW+timedelta(days=1))
        self.assertEqual(s['changes'][-1]['kind'],'updated')
    def test_new_fields_visible_in_public_data_and_readme(self):
        s=core.empty_state();core.merge_items(s,[record(organizer='연구원',registration_start='2026-09-01',deadline='2026-09-30',event_start='2026-10-10',event_end='2026-10-12')],NOW)
        d=render.public_data(s,NOW)
        self.assertEqual(d['items'][0].get('organizer'),'연구원')
        md=render.markdown_table(d)
        self.assertIn('2026-09-01',md)
        self.assertIn('2026-10-10',md)
        self.assertIn('연구원',md)


from contest_alert import collect

class DetailIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.config={'sources':[SRC], 'max_pages_per_source':1,'browser_fallback':False,'max_detail_requests':3,'lookback_days':120}
    def test_campuspick_container_details_are_collected(self):
        class Client:
            def get_text(self,url):return LIST if url==SRC['url'] else DETAIL.replace('<main>','<div id="container">').replace('</main>','</div>')
        state=collect.collect_all(self.config,core.empty_state(),NOW,Client())
        self.assertEqual(len(state['items']),3)
        self.assertTrue(all(i.get('organizer')=='예시 연구원' for i in state['items'].values()))
        self.assertTrue(all(i.get('detail_status')=='ok' for i in state['items'].values()))
    def test_failed_detail_reports_unconfirmed_not_no_contests(self):
        class Client:
            def get_text(self,url):
                if url==SRC['url']:return LIST
                raise collect.FetchError('http_403','HTTP 403')
        state=collect.collect_all(self.config,core.empty_state(),NOW,Client())
        self.assertEqual(len(state['items']),3)
        self.assertTrue(all(i.get('detail_status')=='error' for i in state['items'].values()))
        self.assertEqual(state['sources']['campuspick'].get('detail_errors'),3)
    def test_detail_budgets_do_not_starve_later_sources(self):
        class Client:
            def get_text(self,url):
                if url.endswith('/list'):return ''.join(f'<a href="/bbs/ds/1/{n}/artclView.do">AI 경진대회 {n}</a>' for n in range(10))
                if url==SRC['url']:return LIST
                return DETAIL
        config=dict(self.config,max_detail_requests=2,sources=[{'id':'first','name':'학과','url':'https://x.example/list','kind':'k2web','mode':'contest'},SRC])
        state=collect.collect_all(config,core.empty_state(),NOW,Client())
        self.assertTrue(any(i.get('detail_checked_at') for i in state['items'].values() if i['source_id']=='campuspick'))
    def test_old_unlisted_active_item_can_get_deadline_extension(self):
        old=record(source_id='campuspick',source_name=SRC['name'],url='https://www.campuspick.com/contest/view?id=99',deadline='2026-09-21',detail_checked_at='2026-09-18T11:40:00+09:00')
        state=core.empty_state();core.merge_items(state,[old],NOW-timedelta(days=3))
        class Client:
            def get_text(self,url):return '<main>등록된 게시물이 없습니다</main>' if url==SRC['url'] else DETAIL
        state=collect.collect_all(self.config,state,NOW,Client())
        self.assertEqual(state['items']['r'].get('deadline'),'2026-09-30')
    def test_confirmed_date_clears_if_new_period_is_ambiguous(self):
        s=core.empty_state();core.merge_items(s,[record(deadline='2026-09-30')],NOW)
        core.merge_items(s,[record(registration_ambiguous=True,registration_text='트랙별 상이')],NOW+timedelta(days=1))
        self.assertIsNone(s['items']['r'].get('deadline'))
    def test_details_html_uses_only_explicit_content_and_safe_link(self):
        html='<div id="container"><p>주최: 예시 기관</p><p><a href="/linkclick?id=30">공식 홈페이지</a></p></div>'
        f=core.detail_fields(html,'https://www.campuspick.com/contest/view?id=30','campuspick')
        self.assertEqual(f.get('organizer'),'예시 기관')
        self.assertFalse(f.get('website_url'))

class ReviewRegressionTests(unittest.TestCase):
    def test_invalid_event_range_does_not_become_single_day(self):
        f=core.detail_fields('<main><p>대회기간: 2026.09.01 ~ 2026.09.99</p></main>')
        self.assertFalse(f.get('event_end'))
    def test_url_markup_and_control_characters_rejected(self):
        self.assertEqual(core.canonical('https://x.example/><img src=x>'),'')
        self.assertEqual(core.canonical('https://x.example/\nsecret'),'')
    def test_ambiguous_event_clears_old_event_dates(self):
        s=core.empty_state();core.merge_items(s,[record(event_start='2026-10-01',event_end='2026-10-02')],NOW)
        core.merge_items(s,[record(event_ambiguous=True,schedule_text='부문별 상이')],NOW+timedelta(days=1))
        self.assertIsNone(s['items']['r'].get('event_end'))
    def test_js_detail_fallback_reads_campuspick_container(self):
        class Client:
            def get_text(self,url):return LIST if url==SRC['url'] else '<html><div id="container"></div></html>'
            def browser_html(self,url):return DETAIL.replace('<main>','<div id="container">').replace('</main>','</div>')
        config={'sources':[SRC],'browser_fallback':True,'max_pages_per_source':1,'max_detail_requests':3}
        state=collect.collect_all(config,core.empty_state(),NOW,Client())
        self.assertTrue(all(i.get('deadline')=='2026-09-30' for i in state['items'].values()))
    def test_field_absence_is_not_promised_information(self):
        f=core.detail_fields('<main><p>포스터 참조</p><img src="poster.png"></main>')
        self.assertEqual(f,{})

if __name__=='__main__':unittest.main()
