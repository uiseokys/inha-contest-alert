"""v4 regressions; HTML fixtures are synthetic unless explicitly attributed."""
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from contest_alert import core, details, render, collect
NOW=datetime(2026,9,22,11,40,tzinfo=ZoneInfo('Asia/Seoul'))
SRC={'id':'cp','name':'캠퍼스픽','url':'https://www.campuspick.com/contest','kind':'campuspick','mode':'ai_platform'}
LIST='<a href="/contest/view?id=101"><h2>2026 AI 공모전</h2></a>'
PERIOD='<main><p>접수기간: 2026.09.01 ~ 2026.11.30</p></main>'

class DateV4Tests(unittest.TestCase):
    def pair(self,text,expected):
        f=core.detail_fields('<main>'+text+'</main>','https://x.example/contest/1')
        self.assertEqual((f.get('registration_start'),f.get('deadline')),expected)
    def test_spaced_dates_with_weekdays(self):
        self.pair('<p>접수기간 : 2026. 9. 1.(화) ~ 9. 30.(수) 18:00</p>',('2026-09-01','2026-09-30'))
    def test_bracketed_heading_does_not_hide_period(self):
        self.pair('<h3>[참가 신청 기간]</h3><p>2026년 9월 1일 ~ 2026년 9월 30일</p>',('2026-09-01','2026-09-30'))
    def test_participation_period_label(self):
        self.pair('<p>참가 기간 : 2026년 08월 18일(화) 10:00 ~ 2026년 09월 29일(화) 10:00</p><p>대회 기간 : 2026년 08월 26일 ~ 2025년 09월 30일</p><p>팀 병합 마감 : 2026년 09월 23일</p>',('2026-08-18','2026-09-29'))
    def test_separate_table_start_end(self):
        self.pair('<table><tr><th>접수 시작일</th><td>2026-09-01</td></tr><tr><th>접수 종료일</th><td>2026-10-31</td></tr></table>',('2026-09-01','2026-10-31'))
    def test_plain_application_label(self):
        self.pair('<p>접수 : 2026.09.01~2026.10.31</p>',('2026-09-01','2026-10-31'))
    def test_contest_submission_period_synonyms(self):
        for label in ['응모기간','공모기간','공모 일정','작품 접수기간']:
            with self.subTest(label=label):self.pair(f'<p>{label}: 2026.09.01~2026.10.31</p>',('2026-09-01','2026-10-31'))
    def test_english_iso_period(self):
        self.pair('<p>Registration period: 2026-09-01 to 2026-10-31</p>',('2026-09-01','2026-10-31'))
    def test_infer_year_only_from_explicit_title(self):
        self.pair('<h1>2026 AI 공모전</h1><p>접수기간: 9/1 ~ 10/31</p>',('2026-09-01','2026-10-31'))
    def test_missing_year_still_not_guessed(self):
        self.pair('<h1>AI 공모전</h1><p>접수기간: 9/1 ~ 10/31</p>',(None,None))
    def test_same_period_twice_no_ambiguity(self):
        self.pair('<p>접수기간: 2026.09.01~2026.10.31</p>'*2,('2026-09-01','2026-10-31'))
    def test_reversed_and_multiple_track_dates_not_repaired(self):
        for text in ['접수기간: 2026.10.01~2026.09.30','접수기간: 2026.09.01~2026.09.10 / 2026.09.20~2026.09.30']:
            with self.subTest(text=text):self.pair('<p>'+text+'</p>',(None,None))
    def test_time_and_evidence_preserved(self):
        f=core.detail_fields(PERIOD,'https://x.example/contest/1')
        self.assertEqual(f.get('date_source_url'),'https://x.example/contest/1')
        self.assertTrue(f.get('date_evidence'))
    def test_dacon_div_root_without_main(self):
        html='<html><body><div id="__nuxt"><p>주최: 예시 기관</p><p>참가 기간: 2026.09.01 ~ 2026.11.30</p></div></body></html>'
        f=core.detail_fields(html,'https://dacon.io/competitions/official/100/overview/schedule','dacon')
        self.assertEqual(f.get('deadline'),'2026-11-30')
    def test_metadata_description_can_supply_explicit_period(self):
        html='<html><head><meta property="og:title" content="2026 AI 공모전"><meta property="og:description" content="접수기간: 2026.09.01 ~ 2026.11.30"></head><body></body></html>'
        f=core.detail_fields(html,'https://www.campuspick.com/contest/view?id=1','campuspick')
        self.assertEqual(f.get('deadline'),'2026-11-30')
    def test_jsonld_event_is_not_registration_deadline(self):
        html='<script type="application/ld+json">{"@type":"Event","name":"2026 AI 대회","startDate":"2026-10-01","endDate":"2026-10-30"}</script>'
        f=core.detail_fields(html,'https://x.example/contest/1')
        self.assertIsNone(f.get('deadline'))
        self.assertEqual(f.get('event_end'),'2026-10-30')
    def test_generic_updated_date_not_registration(self):
        self.pair('<p>게시일: 2026.09.01</p><p>수정일: 2026.10.31</p>',(None,None))

class TitleV4Tests(unittest.TestCase):
    def test_platform_tail_removed(self):
        self.assertEqual(core.clean_title('2026 AI 대회 | 에브리커리어'),'2026 AI 대회')
        self.assertEqual(core.clean_title('2026 AI 대회 - DACON'),'2026 AI 대회')
    def test_title_preserved_in_full(self):
        text='2026 ' + '매우 긴 대회명 ' * 40
        self.assertEqual(core.clean_title(text),text.strip())
    def test_new_badge_must_be_separate(self):
        self.assertEqual(core.clean_title('RENEW'),'RENEW')
    def test_card_organizer_and_count_not_title(self):
        html='<a href="/contest/view?id=101"><p class="title">2026 AI 공모전</p><strong>주최 예시기관</strong><span>관심 123 D-3</span></a>'
        items,_=core.parse_listing(html,SRC)
        self.assertEqual(items[0]['title'],'2026 AI 공모전')
    def test_full_detail_title_overrides_noisy_list(self):
        state=core.empty_state();item={'id':'x','source_id':'cp','source_name':'cp','group':'external','url':'https://x.example/1','title':'AI 공모전 관심 100','detail_title':'AI 공모전'}
        core.merge_items(state,[item],NOW)
        self.assertEqual(state['items']['x']['title'],'AI 공모전')
        item.pop('detail_title');core.merge_items(state,[item],NOW+timedelta(days=1))
        self.assertEqual(state['items']['x']['title'],'AI 공모전')

class CollectionV4Tests(unittest.TestCase):
    def cfg(self,**kw):return dict(sources=[SRC],max_pages_per_source=1,max_detail_requests=3,browser_fallback=True,**kw)
    def test_partial_static_info_still_renders_missing_date(self):
        class C:
            def get_text(self,u):return LIST if u==SRC['url'] else '<main><p>주최: 예시기관</p></main>'
            def browser_html(self,u):return PERIOD
        s=collect.collect_all(self.cfg(),core.empty_state(),NOW,C())
        self.assertEqual(next(iter(s['items'].values())).get('deadline'),'2026-11-30')
    def test_schedule_tab_not_canonicalized_to_overview(self):
        src=dict(SRC,id='d',url='https://dacon.io/competitions',kind='dacon',mode='platform')
        listing='<a href="/competitions/official/100/overview/"><h3>AI 대회</h3></a>'
        overview='<main><p>주최: 예시</p><a href="/competitions/official/100/overview/schedule">일정</a></main>'
        class C:
            calls=[]
            def get_text(self,u):
                self.calls.append(u)
                return listing if u==src['url'] else PERIOD if u.endswith('/schedule') else overview
            def browser_html(self,u):return overview
        c=C();cfg=self.cfg();cfg['sources']=[src]
        s=collect.collect_all(cfg,core.empty_state(),NOW,c)
        self.assertIn('https://dacon.io/competitions/official/100/overview/schedule',c.calls)
        self.assertEqual(next(iter(s['items'].values())).get('deadline'),'2026-11-30')
    def test_recent_v3_record_rechecked_after_upgrade(self):
        records,_=core.parse_listing(LIST,SRC);s=core.empty_state()
        records[0].update(detail_attempted_at=NOW.isoformat(),detail_status='ok',organizer='예시')
        core.merge_items(s,records,NOW)
        class C:
            def get_text(self,u):return LIST if u==SRC['url'] else PERIOD
            def browser_html(self,u):return PERIOD
        result=collect.collect_all(self.cfg(),s,NOW+timedelta(minutes=1),C())
        self.assertEqual(next(iter(result['items'].values())).get('deadline'),'2026-11-30')
    def test_403_does_not_trigger_browser_bypass(self):
        class C:
            called=False
            def get_text(self,u):
                if u==SRC['url']:return LIST
                raise collect.FetchError('http_403','HTTP 403')
            def browser_html(self,u):self.called=True;return PERIOD
        c=C();collect.collect_all(self.cfg(),core.empty_state(),NOW,c);self.assertFalse(c.called)

class SortV4Tests(unittest.TestCase):
    def test_public_default_far_deadlines_first_unknown_bottom(self):
        s=core.empty_state()
        for n,d in [('near','2026-09-23'),('unknown',None),('far','2026-11-30'),('closed','2026-09-20'),('today','2026-09-22')]:
            core.merge_items(s,[{'id':n,'title':n,'url':'https://x.example/'+n,'source_id':'x','source_name':'x','group':'external','deadline':d}],NOW)
        rows=render.public_data(s,NOW)['items']
        self.assertEqual([x['id'] for x in rows],['far','near','today','unknown','closed'])

class FinalReviewV4Tests(unittest.TestCase):
    def test_dacon_explicit_period_not_confused_by_summary_timeline(self):
        # Reduced text structure observed on the public DACON schedule page.
        # Full DOM scraping is NOT claimed by this fixture.
        html='''<main><h1>2026 예시 AI 챌린지</h1>
        <p>참가 신청 기간: 2026.07.16 (목) 오전 10시 ~ 2026.08.17 (월) 오후 11시 59분</p>
        <p>대회 기간: 2026.07.16 ~ 2026.08.20</p>
        <h3>대회 주요 일정</h3><ol><li>07.16<br>참가 신청 시작 (10:00)</li><li>07.16<br>대회 시작 (10:00)</li><li>08.17<br>참가 신청 마감 (23:59)</li><li>08.20<br>대회 종료 (18:00)</li></ol></main>'''
        f=core.detail_fields(html,'https://dacon.io/competitions/official/100/overview/schedule','dacon')
        self.assertEqual((f.get('registration_start'),f.get('deadline')),('2026-07-16','2026-08-17'))
    def test_resolved_date_removes_old_uncertainty_note(self):
        r={'id':'x','title':'AI 대회','source_id':'cp','url':'https://x.example/1','date_note':'확정할 수 없습니다','date_status':'missing'}
        state=core.empty_state();core.merge_items(state,[r],NOW)
        f=core.detail_fields(PERIOD,'https://x.example/1');r.update(f)
        core.merge_items(state,[r],NOW+timedelta(days=1))
        self.assertEqual(state['items']['x'].get('date_note'),'')
    def test_invalid_jsonld_event_range_is_unconfirmed(self):
        h='<script type="application/ld+json">{"@type":"Event","name":"AI 대회","startDate":"2026-11-30","endDate":"2026-10-01"}</script>'
        f=core.detail_fields(h,'https://x.example/contest/1')
        self.assertIsNone(f.get('event_end'))
    def test_different_contest_schedule_link_never_followed(self):
        h='<a href="/competitions/official/999/overview/schedule">일정</a>'
        # v6 also checks the verified same-event schedule path; it must never follow event 200.
        links=details.schedule_links(h,'https://dacon.io/competitions/official/100/overview/')
        self.assertEqual(links,['https://dacon.io/competitions/official/100/overview/schedule'])
    def test_date_parser_version_does_not_make_new_contest(self):
        r={'id':'x','title':'AI 대회','source_id':'cp','url':'https://x.example/1'}
        state=core.empty_state();core.merge_items(state,[r],NOW)
        core.merge_items(state,[dict(r,date_parser_version=4)],NOW+timedelta(days=1))
        self.assertFalse(any(x['kind']=='new' for x in state['changes']))
    def test_missing_dates_retry_next_day_after_version4(self):
        records,_=core.parse_listing(LIST,SRC);s=core.empty_state()
        records[0].update(date_parser_version=4,detail_attempted_at=NOW.isoformat(),detail_status='unconfirmed')
        core.merge_items(s,records,NOW)
        class C:
            def get_text(self,u):return LIST if u==SRC['url'] else PERIOD
        cfg={'sources':[SRC],'max_pages_per_source':1,'max_detail_requests':3,'browser_fallback':False}
        collect.collect_all(cfg,s,NOW+timedelta(days=1),C())
        self.assertEqual(next(iter(s['items'].values())).get('deadline'),'2026-11-30')
