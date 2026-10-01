"""Real-incident regressions; HTML is minimal reconstruction, not downloaded DOM."""
import copy, hashlib, unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from contest_alert.core import canonical, detail_fields, empty_state, parse_listing
from contest_alert.details import schedule_links
from contest_alert.quality import classify, apply_policy, visible_state
from contest_alert.collect import collect_all
from contest_alert.render import public_data
from contest_alert.daily import capture_snapshot, compare_day

NOW=datetime(2026,9,22,16,18,tzinfo=ZoneInfo('Asia/Seoul'))
BASE='https://swuniv.inha.ac.kr/bbs/swuniv/3113/188992/artclView.do'
DC='https://dacon.io/competitions/official/236754/overview/'
AF='https://aifactory.space/ko/competitions/9306'
SRC={'id':'sw','name':'SW중심대학사업단','url':'https://swuniv.inha.ac.kr/','kind':'k2web','group':'inha','mode':'candidate'}
def item(title='2026 AI 공모전',url=BASE,**kw):
    out=dict(id=hashlib.sha256(url.encode()).hexdigest()[:20],url=url,title=title,listing_title=title,source_id='sw',source_name=SRC['name'],group='inha',first_seen=NOW.isoformat(),last_changed=NOW.isoformat(),last_seen=NOW.isoformat())
    out.update(kw);return out

class LiveFailures(unittest.TestCase):
    def test_layout_does_not_change_article_identity(self):
        self.assertEqual(canonical(BASE+'?layout=unknown'),canonical(BASE))
    def test_other_sites_layout_query_is_not_blindly_removed(self):
        self.assertNotEqual(canonical('https://example.com/view?layout=x'),canonical('https://example.com/view'))
    def test_existing_duplicate_records_preserved_but_public_once(self):
        a,b=item(),item(url=BASE+'?layout=unknown');s=empty_state();s['items']={a['id']:a,b['id']:b};s['claims']={'2026-09-22':{'status':'reserved','run_id':'KEEP'}}
        apply_policy(s,{'sources':[SRC]})
        self.assertEqual(len(s['items']),2);self.assertEqual(len(visible_state(s)['items']),1)
        self.assertEqual(s['claims']['2026-09-22']['run_id'],'KEEP')
    def test_results_not_new_opportunities(self):
        for title in ['2026 AI-POT 자격증 취득 지원 프로그램(4차) 참여자 선발 결과 안내','2026 AI-POT 자격증 취득 지원 프로그램(3차) 시험 결과 제출 및 장학금 신청 안내(8/27~9/3)']:
            with self.subTest(title=title):self.assertEqual(classify(item(title))['relevance_status'],'excluded')
    def test_genuine_ai_program_is_kept(self):
        self.assertEqual(classify(item('2026 AI 부트캠프 참여자 모집'))['relevance_status'],'included')
    def test_title_registration_window_survives_missing_body(self):
        title='2026 AI-POT 자격증 취득 지원 프로그램(4차) 참여 신청 (9/10~9/16)'
        out=detail_fields('<body><h1>'+title+'</h1></body>',BASE,'k2web',title)
        self.assertEqual(out.get('deadline'),'2026-09-16');self.assertEqual(out.get('registration_start'),'2026-09-10')
    def test_title_only_end_date_uses_explicit_year(self):
        title='2026 SW·AI 해외 인턴십 프로그램 참여자 모집 (~8. 16. (일) 까지)'
        out=detail_fields('<body><h1>'+title+'</h1></body>',BASE,'k2web',title)
        self.assertEqual(out.get('deadline'),'2026-08-16');self.assertFalse(out.get('registration_start'))
    def test_yearless_title_does_not_use_machine_year(self):
        title='AI 프로그램 참여 신청 (9/10~9/16)'
        self.assertFalse(detail_fields('<body><h1>'+title+'</h1></body>',BASE,'k2web',title).get('deadline'))
    def test_dacon_schedule_discovery_outside_content(self):
        h='<body><nav><a href="/competitions/official/236754/overview/schedule">일정</a></nav><main><p>AI 대회 개요</p></main></body>'
        self.assertIn(DC+'schedule',schedule_links(h,DC))
    def test_dacon_schedule_known_path_when_shell_has_no_link(self):
        self.assertIn(DC+'schedule',schedule_links('<body><h1>AI 대회</h1></body>',DC))
    def test_not_recursing_schedule_itself(self):
        self.assertNotIn(DC+'schedule',schedule_links('<body></body>',DC+'schedule'))
    def test_aifactory_registration_label_without_period_suffix(self):
        h='''<body><h1>주제 3: 국립공원 내 시설물 변화 탐지</h1><div class="competition-content"><p>참가 접수</p><p>2026.07.31 10:00 ~ 2026.10.06 14:00</p><p>팀 병합 기간</p><p>2026.07.31 10:00 ~ 2026.09.29 14:00</p><p>대회 기간</p><p>2026.09.14 10:00 ~ 2026.10.06 14:00</p></div></body>'''
        out=detail_fields(h,AF,'aifactory')
        self.assertEqual(out.get('registration_start'),'2026-07-31');self.assertEqual(out.get('deadline'),'2026-10-06');self.assertEqual(out.get('deadline_time'),'14:00')
    def test_prose_organizer_and_benefits_do_not_pollute_fields(self):
        h='''<body><main><h1>AI 챌린지</h1><p>수상 후 주최 측 또는 제3자에게 발생한 손해에 대해 참가자가 책임을 부담합니다.</p><p>수상작은 상금 지급과 함께 계약을 체결합니다.</p><h2>주최 · 주관 · 운영</h2><p>주최 국립공원공단</p><p>주관 인공지능팩토리</p><p>운영 인공지능팩토리</p><h2>참가 자격</h2><p>14세 이상 대한민국 국민 누구나</p><p>개인 및 최대 인원 5인 팀으로 참가 가능</p><h2>평가 방법</h2><p>Public 점수 등 평가 설명</p></main></body>'''
        out=detail_fields(h,AF,'aifactory')
        self.assertEqual(out.get('organizer'),'국립공원공단 / 인공지능팩토리');self.assertNotIn('지급과 함께',out.get('benefits',''));self.assertNotIn('Public',out.get('eligibility',''))
    def test_event_prose_not_competing_date_range(self):
        h='''<main><h1>AI 대회</h1><p>대회 기간</p><p>2026.09.14 10:00 ~ 2026.10.06 14:00</p><h2>평가 방법</h2><p>대회 기간 중에는 Public 점수만 확인할 수 있습니다.</p></main>'''
        out=detail_fields(h,AF,'aifactory');self.assertEqual(out.get('event_end'),'2026-10-06')
    def test_metadata_labels_outside_first_article(self):
        h='<body><article><h1>2026 AI 공모전</h1></article><section class="info"><dl><dt>접수기간</dt><dd>2026.09.01 ~ 2026.10.31</dd></dl></section><aside><p>접수기간: 2026.01.01 ~ 2026.12.31</p></aside></body>'
        out=detail_fields(h,'https://www.campuspick.com/contest/view?id=36134','campuspick')
        self.assertEqual(out.get('deadline'),'2026-10-31')
    def test_bad_old_metadata_removed_without_deleting_item(self):
        x=item(organizer='측 또는 제3자에게 발생한 손해에 대해 참가자가 책임을 부담합니다.',benefits='지급과 함께 계약을 체결합니다.',date_parser_version=5)
        s=empty_state();s['items'][x['id']]=x;apply_policy(s,{'sources':[SRC]})
        self.assertFalse(s['items'][x['id']].get('organizer'));self.assertFalse(s['items'][x['id']].get('benefits'))
    def test_dacon_date_tab_text_without_container(self):
        h='<body><h1>나라장터 AI 경진대회</h1><p>참가 기간: 2026년 08월 18일(화) 10:00 ~ 2026년 09월 29일(화) 10:00</p><p>대회 기간: 2026년 08월 26일(수) 10:00 ~ 2026년 09월 30일(수) 10:00</p></body>'
        out=detail_fields(h,DC+'schedule','dacon');self.assertEqual(out.get('deadline'),'2026-09-29');self.assertEqual(out.get('deadline_time'),'10:00')

if __name__=='__main__':unittest.main()

class PipelineRegressions(unittest.TestCase):
    def test_known_dacon_schedule_is_actually_requested(self):
        src=dict(id='dacon',name='DACON',kind='dacon',group='external',url='https://dacon.io/competitions',mode='platform')
        class Client:
            def __init__(self):self.seen=[]
            def get_text(self,url):
                self.seen.append(url)
                if url==src['url']:return '<a href="'+DC+'">나라장터 AI 경진대회</a>'
                if url==DC:return '<body><h1>나라장터 AI 경진대회</h1><p>설명</p></body>'
                if url==DC+'schedule':return '<body><h1>나라장터 AI 경진대회</h1><p>참가 기간: 2026.08.18 10:00 ~ 2026.09.29 10:00</p></body>'
                raise AssertionError(url)
        client=Client();s=empty_state()
        collect_all({'sources':[src],'browser_fallback':False},s,NOW,client)
        self.assertIn(DC+'schedule',client.seen)
        self.assertEqual(next(iter(s['items'].values())).get('deadline'),'2026-09-29')
    def test_old_layout_id_reused_not_announced_as_new(self):
        from contest_alert.repair import reuse_existing_ids
        from contest_alert.core import merge_items
        from datetime import timedelta
        old=item(url=BASE+'?layout=unknown');s=empty_state();s['items'][old['id']]=old;s['initialized_sources']=['sw'];s['sources']['sw']={'status':'ok'};s['updated_at']=(NOW-timedelta(days=1)).isoformat();capture_snapshot(s,NOW-timedelta(days=1))
        before=copy.deepcopy(s['daily_snapshots']);apply_policy(s,{'sources':[SRC]})
        records=[item(url=BASE)];reuse_existing_ids(records,s);merge_items(s,records,NOW);apply_policy(s,{'sources':[SRC]});capture_snapshot(s,NOW)
        self.assertEqual(records[0]['id'],old['id']);self.assertEqual(len(s['items']),1)
        self.assertEqual(s['daily_snapshots']['2026-09-21'],before['2026-09-21']);self.assertEqual(compare_day(s,NOW)['new_count'],0)
    def test_budget_deferral_is_reported(self):
        class Client:
            def get_text(self,url):
                return '<a href="'+BASE+'">2026 AI 공모전</a>'
        s=empty_state();collect_all({'sources':[SRC],'max_detail_requests':0,'browser_fallback':False},s,NOW,Client())
        self.assertEqual(s['sources']['sw'].get('detail_deferred'),1)
    def test_kind_of_competition_and_program(self):
        self.assertEqual(classify(item('AI 영상 공모전')).get('opportunity_kind'),'contest')
        self.assertEqual(classify(item('AI 활용 부트캠프 참여자 모집')).get('opportunity_kind'),'program')
    def test_event_year_typo_does_not_poison_registration(self):
        h='<body><h1>딥보이스 AI 경진대회</h1><p>참가 기간: 2026.08.18 10:00 ~ 2026.09.29 10:00</p><p>대회 기간: 2026.08.26 10:00 ~ 2025.09.30 10:00</p></body>'
        out=detail_fields(h,DC+'schedule','dacon')
        self.assertEqual(out.get('deadline'),'2026-09-29');self.assertFalse(out.get('event_end'));self.assertTrue(out.get('event_ambiguous'))
    def test_total_prize_does_not_include_platform_counters(self):
        h='<body><h1>AI 대회</h1><p>총 상금</p><p>600만원</p><p>참가자수</p><p>186</p><p>조회수</p><p>9850</p><h2>소개</h2><p>긴 대회 소개</p></body>'
        out=detail_fields(h,AF,'aifactory')
        self.assertEqual(out.get('benefits'),'총상금 600만원')

class FinalReviewRegressions(unittest.TestCase):
    def test_insurance_organizer_name_is_not_legal_prose(self):
        from contest_alert.repair import sanitize_fields
        record={'title':'AI 데이터 공모전','organizer':'DB손해보험','url':BASE}
        sanitize_fields(record)
        self.assertEqual(record.get('organizer'),'DB손해보험')
    def test_competition_platform_topic_title_still_classified_as_contest(self):
        row=item('주제 3: 국립공원 내 시설물 변화 탐지',url='https://aifactory.space/ko/competitions/9306',source_id='aifactory',relevance_status='included',relevance_version=5,relevance_evidence='2026 국립공원 위성 모니터링 AI 챌린지')
        self.assertEqual(classify(row).get('opportunity_kind'),'contest')
