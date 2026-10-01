"""v5 regression fixtures. HTML structure is synthetic, not a captured live DOM.
The short AIX registration line follows the published vid=107 text.
"""
import copy, json, unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from contest_alert import core, details, collect, render, notify, daily
NOW=datetime(2026,9,22,11,40,tzinfo=ZoneInfo('Asia/Seoul'))
AIX={'id':'aix','name':'인공지능융합연구센터','url':'https://aix.inha.ac.kr/news/notice/','kind':'mangboard','mode':'contest','group':'inha'}
URL=AIX['url']+'?vid=107'
TITLE='2026 인하 인공지능 챌린지 개최 안내'

def record(**kw):
    return dict(id='r',source_id='aix',source_name=AIX['name'],group='inha',url=URL,title=TITLE,**kw)

def listing(title=TITLE,vid=107):
    return f'<table><tr><td><a href="?vid={vid}">{title}</a></td><td>2026-09-20</td></tr></table>'

class TitleAndBodyV5(unittest.TestCase):
    def test_generic_page_heading_and_metadata_not_a_title(self):
        h='<title>공지사항 – 인하대학교 인공지능융합연구센터</title><meta property="og:title" content="공지사항"><h1>공지사항</h1><main><p>본문</p></main>'
        self.assertNotIn('detail_title',core.detail_fields(h,URL,'mangboard'))
    def test_mangboard_post_heading_wins(self):
        h=f'<h1>공지사항</h1><main><form><h3>{TITLE}</h3><div class="mb-view-content">접수기간: 2026.09.01 ~ 2026.10.31</div></form></main>'
        f=core.detail_fields(h,URL,'mangboard')
        self.assertEqual(f.get('detail_title'),TITLE)
        self.assertEqual(f.get('deadline'),'2026-10-31')
    def test_form_wrapper_must_not_delete_article(self):
        h=f'<main><form><h3>{TITLE}</h3><p>접수기간: 2026.09.01 ~ 2026.10.31</p><input type="hidden"></form></main>'
        self.assertEqual(core.detail_fields(h,URL,'mangboard').get('deadline'),'2026-10-31')
    def test_generic_old_detail_does_not_overwrite_correct_listing(self):
        s=core.empty_state();core.merge_items(s,[record(detail_title='공지사항',title_raw=TITLE)],NOW)
        core.merge_items(s,[record()],NOW+timedelta(minutes=1))
        self.assertEqual(s['items']['r']['title'],TITLE)
    def test_public_view_restores_original_listing_title(self):
        s=core.empty_state();core.merge_items(s,[record()],NOW)
        s['items']['r'].update(title='공지사항',detail_title='공지사항',title_raw=TITLE)
        self.assertEqual(render.public_data(s,NOW)['items'][0]['title'],TITLE)
    def test_body_nav_and_recommendations_not_subject(self):
        h='<main><nav>AI 데이터 경진대회</nav><h1>바다 사진 공모전</h1><article><p>자연 풍경을 직접 촬영하세요.</p></article><aside>인공지능 활용 교육</aside></main>'
        f=core.detail_fields(h,URL,'mangboard')
        self.assertNotIn('데이터',f.get('_topic_text',''))
    def test_deleted_old_date_not_conflict(self):
        h='<main><del>접수마감: 2026.09.30</del><p>접수마감: 2026.10.15 18:00</p></main>'
        f=core.detail_fields(h,URL,'mangboard')
        self.assertEqual(f.get('deadline'),'2026-10-15')

class DatesV5(unittest.TestCase):
    def test_aix_apostrophe_year_and_unrelated_next_milestone(self):
        h=f'''<main><h3>{TITLE}</h3><p>접수 기간 : '26. 7. 16(목) 오전 10 시 ~ 8. 17(월)</p>
        <p>- 학습 데이터셋 공개 : '26. 7. 16(목) 오전 10 시</p>
        <p>- 대회 기간 : '26. 7. 16(목) 오전 10 시 ~ 8. 20(목) 오후 6 시</p></main>'''
        f=core.detail_fields(h,URL,'mangboard')
        self.assertEqual((f.get('registration_start'),f.get('deadline')),('2026-07-16','2026-08-17'))
        self.assertIsNone(f.get('deadline_time'))
        self.assertEqual(f.get('event_end'),'2026-08-20')
    def test_spaced_label_and_deadline_time(self):
        h='<main><p>접 수 기 간 : 2026.09.01 ~ 2026.10.31 오후 6시</p><p>문 의 : 운영팀</p></main>'
        f=core.detail_fields(h,URL)
        self.assertEqual(f.get('deadline'),'2026-10-31');self.assertEqual(f.get('deadline_time'),'18:00')
    def test_single_deadline_datetime_label(self):
        f=core.detail_fields('<main><p>신청 마감 일시: 2026-10-31 23:59</p></main>',URL)
        self.assertEqual(f.get('deadline'),'2026-10-31');self.assertEqual(f.get('deadline_time'),'23:59')
    def test_date_before_label_timeline(self):
        h='<main><table><tr><td>2026.09.01 10:00</td><td>참가 신청 시작</td></tr><tr><td>2026.10.31 18:00</td><td>참가 신청 마감</td></tr><tr><td>2026.11.30</td><td>결과 발표</td></tr></table></main>'
        f=core.detail_fields(h,URL)
        self.assertEqual((f.get('registration_start'),f.get('deadline')),('2026-09-01','2026-10-31'))
    def test_embedded_explicit_registration_keys_same_id(self):
        obj={'props':{'pageProps':{'contest':{'id':107,'title':TITLE,'registrationStartDate':'2026-09-01T10:00:00+09:00','registrationEndDate':'2026-10-31T18:00:00+09:00'}}}}
        h='<script id="__NEXT_DATA__" type="application/json">'+json.dumps(obj)+'</script>'
        f=core.detail_fields(h,'https://www.campuspick.com/contest/view?id=107','campuspick')
        self.assertEqual(f.get('deadline'),'2026-10-31');self.assertEqual(f.get('deadline_time'),'18:00')
    def test_unrelated_json_record_never_supplies_dates(self):
        obj={'recommendations':[{'id':999,'registrationEndDate':'2026-12-31'}]}
        h='<script type="application/json">'+json.dumps(obj)+'</script>'
        f=core.detail_fields(h,'https://www.campuspick.com/contest/view?id=107','campuspick')
        self.assertIsNone(f.get('deadline'))
    def test_generic_json_event_end_not_application_end(self):
        h='<script type="application/json">{"contest":{"id":107,"startDate":"2026-10-01","endDate":"2026-12-31"}}</script>'
        self.assertIsNone(core.detail_fields(h,'https://www.campuspick.com/contest/view?id=107','campuspick').get('deadline'))
    def test_official_platform_link_from_application_context(self):
        h='<main><p>접수처: <a href="https://dacon.io/competitions/official/236736/overview/description">데이콘 홈페이지</a></p></main>'
        self.assertIn('https://dacon.io/competitions/official/236736/overview/schedule',details.schedule_links(h,URL))
    def test_related_or_navigation_links_not_followed(self):
        h='<main><aside><a href="https://dacon.io/competitions/official/999/overview/">신청 사이트</a></aside></main>'
        self.assertEqual(details.schedule_links(h,URL),[])

class ScopeV5(unittest.TestCase):
    def cfg(self,sources=None,**kw):return dict(sources=sources or [AIX],browser_fallback=False,max_pages_per_source=1,max_detail_requests=10,**kw)
    def test_main_inha_automatically_disabled_without_touching_config(self):
        src=dict(AIX,id='inha',url='https://www.inha.ac.kr/',kind='k2web');cfg=self.cfg([src]);original=copy.deepcopy(cfg)
        class C:
            def get_text(self,u):raise AssertionError('Disabled representative site must not be requested')
        s=collect.collect_all(cfg,core.empty_state(),NOW,C())
        self.assertEqual(s['sources']['inha']['status'],'disabled');self.assertEqual(cfg,original)
    def test_non_ai_contest_hidden_but_identity_preserved(self):
        class C:
            def get_text(self,u):return listing('바다 사진 공모전') if u==AIX['url'] else '<main><h3>바다 사진 공모전</h3><p>공모 주제: 바다 풍경 촬영</p></main>'
        s=collect.collect_all(self.cfg(),core.empty_state(),NOW,C())
        self.assertTrue(s['items']);self.assertEqual(render.public_data(s,NOW)['items'],[])
        self.assertNotIn('바다 사진',notify.digest(s,NOW,'https://x.example'))
    def test_organizer_name_alone_not_ai_evidence(self):
        class C:
            def get_text(self,u):return listing('일반 창업 아이디어 공모전') if u==AIX['url'] else '<main><h3>일반 창업 아이디어 공모전</h3><p>주최: 인공지능융합연구센터</p><p>주제: 자유로운 창업 아이디어</p></main>'
        s=collect.collect_all(self.cfg(),core.empty_state(),NOW,C())
        self.assertEqual(render.public_data(s,NOW)['items'],[])
    def test_ai_prohibition_is_not_ai_contest(self):
        class C:
            def get_text(self,u):return listing('풍경 사진 공모전') if u==AIX['url'] else '<main><h3>풍경 사진 공모전</h3><p>생성형 AI 사용 작품은 출품 불가합니다.</p></main>'
        s=collect.collect_all(self.cfg(),core.empty_state(),NOW,C())
        self.assertEqual(render.public_data(s,NOW)['items'],[])
    def test_generic_title_can_be_kept_with_actual_body_evidence(self):
        class C:
            def get_text(self,u):return listing('도시 문제 해결 공모전') if u==AIX['url'] else '<main><h3>도시 문제 해결 공모전</h3><p>공모 주제: 공공데이터 분석을 활용한 교통량 예측</p></main>'
        s=collect.collect_all(self.cfg(),core.empty_state(),NOW,C())
        self.assertEqual(len(render.public_data(s,NOW)['items']),1)
    def test_ai_video_contest_remains_included(self):
        class C:
            def get_text(self,u):return listing('생성형 AI 활용 영상 공모전') if u==AIX['url'] else '<main><p>접수기간: 2026.09.01~2026.10.31</p></main>'
        s=collect.collect_all(self.cfg(),core.empty_state(),NOW,C())
        self.assertEqual(len(render.public_data(s,NOW)['items']),1)
    def test_old_non_ai_records_hidden_even_when_collection_fails(self):
        old=record();old['title']='바다 사진 공모전';s=core.empty_state();core.merge_items(s,[old],NOW-timedelta(days=1));s['claims']['2026-09-21']={'status':'accepted','run_id':'existing'}
        class C:
            def get_text(self,u):raise collect.FetchError('network_error','network')
        s=collect.collect_all(self.cfg(),s,NOW,C())
        self.assertIn('r',s['items']);self.assertEqual(s['claims']['2026-09-21']['run_id'],'existing')
        self.assertEqual(render.public_data(s,NOW)['items'],[])
    def test_old_generic_title_is_restored_without_detail_network(self):
        s=core.empty_state();core.merge_items(s,[record()],NOW-timedelta(days=1));s['items']['r'].update(title='공지사항',detail_title='공지사항',title_raw=TITLE)
        class C:
            def get_text(self,u):raise collect.FetchError('network_error','network')
        s=collect.collect_all(self.cfg(),s,NOW,C())
        self.assertEqual(s['items']['r']['title'],TITLE)
        self.assertEqual(render.public_data(s,NOW)['items'][0]['title'],TITLE)

class IntegrationV5(unittest.TestCase):
    def test_official_link_dates_reach_aix_item_without_renaming(self):
        class C:
            calls=[]
            def get_text(self,u):
                self.calls.append(u)
                if u==AIX['url']:return listing()
                if u==URL:return f'<main><h3>{TITLE}</h3><p>접수처: <a href="https://dacon.io/competitions/official/236736/overview/description">데이콘 홈페이지</a></p></main>'
                if u.endswith('/schedule'):return '<main><h1>인하 AI 대회 - DACON</h1><p>참가 신청 기간: 2026.07.16 10:00 ~ 2026.08.17 23:59</p></main>'
                raise AssertionError(u)
        cfg=dict(sources=[AIX],browser_fallback=False,max_pages_per_source=1,max_detail_requests=3)
        c=C();s=collect.collect_all(cfg,core.empty_state(),NOW,c);item=next(iter(s['items'].values()))
        self.assertEqual(item['title'],TITLE);self.assertEqual(item['deadline'],'2026-08-17')
        self.assertEqual(item['deadline_time'],'23:59');self.assertTrue(item['date_source_url'].endswith('/schedule'))
    def test_platform_generic_task_can_be_checked_for_real_topic(self):
        src=dict(AIX,id='dacon',url='https://dacon.io/competitions',kind='dacon',mode='platform')
        class C:
            def get_text(self,u):return '<a href="/competitions/official/55/overview/"><h2>손글씨 숫자 분류</h2></a>' if u==src['url'] else '<main><h1>손글씨 숫자 분류</h1><p>대회 주제: 딥러닝을 이용한 숫자 이미지 분류</p></main>'
        cfg=dict(sources=[src],browser_fallback=False,max_pages_per_source=1,max_detail_requests=3)
        s=collect.collect_all(cfg,core.empty_state(),NOW,C())
        self.assertEqual(len(render.public_data(s,NOW)['items']),1)
    def test_new_changed_deadline_does_not_reuse_old_time(self):
        s=core.empty_state();core.merge_items(s,[record(deadline='2026-09-30',deadline_time='18:00')],NOW)
        core.merge_items(s,[record(deadline='2026-10-15')],NOW+timedelta(days=1))
        self.assertIsNone(s['items']['r'].get('deadline_time'))
    def test_conflicting_period_also_clears_deadline_clock(self):
        s=core.empty_state();core.merge_items(s,[record(deadline='2026-09-30',deadline_time='18:00')],NOW)
        core.merge_items(s,[record(registration_ambiguous=True)],NOW+timedelta(days=1))
        self.assertIsNone(s['items']['r'].get('deadline_time'))
    def test_unrelated_new_notice_not_in_daily_new_or_digest(self):
        class C:
            day=0
            def get_text(self,u):
                if u==AIX['url']:return listing()+ (listing('바다 사진 공모전',108) if self.day else '')
                return '<main><h1>바다 사진 공모전</h1><p>직접 촬영한 사진</p></main>' if '108' in u else f'<main><h1>{TITLE}</h1></main>'
        c=C();cfg=dict(sources=[AIX],browser_fallback=False,max_pages_per_source=1,max_detail_requests=5)
        s=collect.collect_all(cfg,core.empty_state(),NOW,c);c.day=1
        s=collect.collect_all(cfg,s,NOW+timedelta(days=1),c)
        self.assertEqual(daily.compare_day(s,NOW+timedelta(days=1))['new_count'],0)
        self.assertNotIn('바다 사진',notify.digest(s,NOW+timedelta(days=1),'https://x.example'))
    def test_relevance_evidence_is_kept_after_no_detail_budget(self):
        class C:
            def get_text(self,u):return listing('도시 교통 공모전') if u==AIX['url'] else '<main><p>공모 주제: 공공데이터 분석</p></main>'
        cfg=dict(sources=[AIX],browser_fallback=False,max_pages_per_source=1,max_detail_requests=5)
        s=collect.collect_all(cfg,core.empty_state(),NOW,C());cfg['max_detail_requests']=0
        s=collect.collect_all(cfg,s,NOW+timedelta(days=1),C())
        self.assertEqual(len(render.public_data(s,NOW+timedelta(days=1))['items']),1)
        self.assertNotIn('_topic_text',next(iter(s['items'].values())))
    def test_raw_apostrophe_evidence_kept(self):
        h="<main><p>접수기간: '26. 9. 1 ~ 10. 31</p></main>"
        f=core.detail_fields(h,URL)
        self.assertIn("'26",f.get('date_evidence',''))
    def test_utc_registration_metadata_normalized_to_korea(self):
        obj={'contest':{'id':107,'registrationEndAt':'2026-10-31T23:00:00Z'}}
        h='<script type="application/json">'+json.dumps(obj)+'</script>'
        f=core.detail_fields(h,'https://www.campuspick.com/contest/view?id=107','campuspick')
        self.assertEqual((f.get('deadline'),f.get('deadline_time')),('2026-11-01','08:00'))

class FinalReviewV5(unittest.TestCase):
    def test_complete_dates_still_follow_official_link_for_missing_clock(self):
        class C:
            def get_text(self,u):
                if u==AIX['url']:return listing()
                if u==URL:return f'''<main><h3>{TITLE}</h3><p>접수기간: '26. 7. 16 오전 10시 ~ 8. 17</p><p>접수처: <a href="https://dacon.io/competitions/official/236736/overview/description">데이콘 홈페이지</a></p></main>'''
                if u.endswith('/schedule'):return '<main><h1>인하 AI 대회</h1><p>참가 신청 기간: 2026.07.16 오전 10시 ~ 2026.08.17 오후 11시 59분</p></main>'
                raise AssertionError(u)
        cfg=dict(sources=[AIX],browser_fallback=False,max_pages_per_source=1,max_detail_requests=3)
        s=collect.collect_all(cfg,core.empty_state(),NOW,C());item=next(iter(s['items'].values()))
        self.assertEqual(item.get('deadline_time'),'23:59')
        self.assertEqual(item['title'],TITLE)
    def test_disagreeing_clock_is_unconfirmed_not_last_value(self):
        f=core.detail_fields('<main><p>접수마감: 2026.10.31 18:00</p><p>신청마감: 2026.10.31 23:59</p></main>',URL)
        self.assertEqual(f.get('deadline'),'2026-10-31')
        self.assertIsNone(f.get('deadline_time'))
        self.assertTrue(f.get('registration_time_ambiguous'))
    def test_conflicting_clock_clears_previously_stored_clock(self):
        s=core.empty_state();core.merge_items(s,[record(deadline='2026-10-31',deadline_time='18:00')],NOW)
        core.merge_items(s,[record(deadline='2026-10-31',registration_time_ambiguous=True)],NOW+timedelta(days=1))
        self.assertIsNone(s['items']['r'].get('deadline_time'))
    def test_spaced_ai_center_name_is_not_the_post_title(self):
        h='<main><h2>AI 융합연구센터</h2><h3>도시 데이터 경진대회</h3><p>접수마감: 2026.10.31</p></main>'
        self.assertEqual(core.detail_fields(h,URL,'mangboard').get('detail_title'),'도시 데이터 경진대회')
