import copy,importlib.util,unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from contest_alert.core import detail_fields,empty_state
from contest_alert.collect import collect_all,FetchError
NOW=datetime(2026,9,23,11,40,tzinfo=ZoneInfo('Asia/Seoul'))
URL='https://swuniv.inha.ac.kr/bbs/swuniv/3113/188992/artclView.do'
TITLE='2026 AI-POT 자격증 취득 지원 프로그램(4차) 참여 신청 (9/10~9/16)'
BODY='''<article><h1>2026 AI-POT 프로그램 참여 신청</h1><p>2. 신청 기간 및 일정(안)</p><p>∙ 신청 기간: 2026. 9. 10.(목) ~ 9. 16.(수) *온라인 원서접수 기간과 동일</p><p>∙ 장학금 신청 기간: 2026. 11. 5.(목) ~ 11. 12.(목)</p><p>∙ 환불 규정: 인터넷 접수 마감일 포함 6일 이내 17:59:59까지 100% 환불 가능</p></article>'''
class DateScopeTests(unittest.TestCase):
    def test_primary_registration_not_scholarship_or_refund(self):
        r=detail_fields(BODY,URL,'k2web',TITLE)
        self.assertEqual(r.get('deadline'),'2026-09-16');self.assertEqual(r.get('registration_start'),'2026-09-10')
        self.assertFalse(r.get('deadline_time'));self.assertFalse(r.get('registration_ambiguous'))
    def test_two_genuine_tracks_remain_ambiguous(self):
        html='<article><h1>2026 AI 경진대회</h1><p>학생 부문 접수기간: 2026.09.01 ~ 09.20</p><p>일반 부문 접수기간: 2026.09.01 ~ 09.30</p></article>'
        self.assertFalse(detail_fields(html,URL,'k2web').get('deadline'))
    def test_cancelled_old_period_not_current_registration(self):
        html='<article><h1>2026 AI 대회</h1><p>당초 접수기간: 2026.09.01 ~ 09.20</p><p>변경 접수기간: 2026.09.01 ~ 09.30</p></article>'
        r=detail_fields(html,URL,'k2web');self.assertEqual(r.get('deadline'),'2026-09-30')
    def test_heading_without_date_does_not_poison_valid_period(self):
        r=detail_fields('<article><h1>2026 AI 프로그램</h1><h2>신청 기간 및 일정(안)</h2><p>신청 기간: 2026.09.10 ~ 09.16</p></article>',URL,'k2web')
        self.assertEqual(r.get('deadline'),'2026-09-16')
    def test_notice_fingerprint_changes_only_with_body(self):
        a=detail_fields(BODY,URL,'k2web',TITLE);self.assertIn('detail_content_hash',a)
        b=detail_fields(BODY.replace('9. 16.','9. 17.'),URL,'k2web',TITLE)
        self.assertNotEqual(a['detail_content_hash'],b['detail_content_hash'])
class DiagnosticTests(unittest.TestCase):
    def test_diagnostics_module_available(self):self.assertIsNotNone(importlib.util.find_spec('contest_alert.diagnostics'))
    def test_failed_detail_has_machine_readable_reason(self):
        source={'id':'s','name':'S','url':'https://a.example/list','kind':'k2web','group':'inha'}
        class Client:
            def get_text(self,url):
                if url==source['url']:return '<a href="/bbs/a/1/2/artclView.do">2026 AI 경진대회</a>'
                raise FetchError('http_403','HTTP 403')
        s=empty_state();collect_all({'sources':[source],'browser_fallback':False},s,NOW,Client())
        item=next(iter(s['items'].values()));self.assertEqual(item.get('date_failure_code'),'http_403')
        self.assertTrue(item.get('detail_trace'))
    def test_budget_deferred_not_access_failure(self):
        src={'id':'s','name':'S','url':'https://a.example/list','kind':'k2web','group':'inha'}
        class Client:
            def get_text(self,url):return '<a href="/bbs/a/1/2/artclView.do">2026 AI 경진대회</a>'
        s=empty_state();collect_all({'sources':[src],'max_detail_requests':0},s,NOW,Client())
        self.assertEqual(next(iter(s['items'].values())).get('date_failure_code'),'budget_deferred')
class CorrectionTests(unittest.TestCase):
    def test_correction_module_available(self):self.assertIsNotNone(importlib.util.find_spec('contest_alert.corrections'))
    def run_correction(self,entry):
        from contest_alert.corrections import apply_corrections
        state=empty_state();state['items']['x']={'id':'x','url':URL,'title':TITLE,'deadline':'2026-09-16','detail_checked_at':NOW.isoformat()}
        apply_corrections(state,{'version':1,'entries':{URL:entry}},NOW);return state
    def test_evidence_is_required(self):
        if not importlib.util.find_spec('contest_alert.corrections'):self.fail('corrections missing')
        with self.assertRaises(ValueError):self.run_correction({'deadline':'2026-09-30'})
    def test_correction_preserves_original_and_is_idempotent(self):
        if not importlib.util.find_spec('contest_alert.corrections'):self.fail('corrections missing')
        from contest_alert.corrections import apply_corrections,restore_automatic_dates
        cfg={'version':1,'entries':{URL:{'deadline':'2026-09-30','evidence_url':URL,'checked_at':'2026-09-23','reason':'공식 연장 안내 확인'}}}
        s=self.run_correction(cfg['entries'][URL]);self.assertEqual(s['items']['x']['deadline'],'2026-09-30')
        self.assertEqual(s['items']['x']['_automatic_dates']['deadline'],'2026-09-16')
        apply_corrections(s,cfg,NOW);self.assertEqual(s['items']['x']['_automatic_dates']['deadline'],'2026-09-16')
        restore_automatic_dates(s);self.assertEqual(s['items']['x']['deadline'],'2026-09-16')
    def test_later_conflicting_observation_requests_review(self):
        if not importlib.util.find_spec('contest_alert.corrections'):self.fail('corrections missing')
        from contest_alert.corrections import apply_corrections,restore_automatic_dates
        entry={'deadline':'2026-09-30','evidence_url':URL,'checked_at':'2026-09-22','reason':'공식 변경 확인'}
        s=self.run_correction(entry);restore_automatic_dates(s);s['items']['x']['deadline']='2026-10-01'
        apply_corrections(s,{'version':1,'entries':{URL:entry}},NOW)
        self.assertTrue(s['items']['x']['manual_correction']['needs_review'])
    def test_invalid_clock_and_inverted_interval_rejected(self):
        if not importlib.util.find_spec('contest_alert.corrections'):self.fail('corrections missing')
        base={'evidence_url':URL,'checked_at':'2026-09-23','reason':'검토'}
        for fields in [{'deadline':'2026-09-30','deadline_time':'30:00'},{'registration_start':'2026-10-01','deadline':'2026-09-30'}]:
            with self.assertRaises(ValueError):self.run_correction(dict(base,**fields))
class QualityReportRegression(unittest.TestCase):
    def test_denominator_and_current_attempt_are_not_conflated(self):
        from contest_alert.diagnostics import diagnostic_report
        s=empty_state();s['quality_policy_version']=6;s['updated_at']=NOW.isoformat();s['sources']={'s':{'name':'S','status':'partial'}}
        s['items']={'a':{'id':'a','title':'AI 대회','source_id':'s','url':URL,'relevance_status':'included','deadline':'2026-10-01','detail_attempted_at':NOW.isoformat(),'detail_trace':[{'stage':'date_parse','outcome':'ok'}]},
                    'b':{'id':'b','title':'AI 미확인','source_id':'s','url':URL,'relevance_status':'included','date_failure_code':'budget_deferred'},
                    'excluded':{'id':'excluded','source_id':'s','relevance_status':'excluded','deadline':'2026-10-01'}}
        r=diagnostic_report(s,NOW);self.assertEqual(r['total'],2);self.assertEqual(r['coverage'],50.0)
        self.assertEqual(r['sources'][0]['attempted_this_run'],1);self.assertEqual(r['sources'][0]['reasons']['budget_deferred'],1)
    def test_previous_date_after_failed_parse_marked_stale(self):
        from contest_alert.diagnostics import reason_for
        self.assertEqual(reason_for({'deadline':'2026-10-01','date_failure_code':'no_explicit_date'}),'stale_evidence')
    def test_diagnostic_does_not_leak_unexpected_trace_properties(self):
        from contest_alert.diagnostics import diagnostic_report
        s=empty_state();s['items']['a']={'id':'a','source_id':'s','detail_trace':[{'stage':'x','outcome':'ok','response_body':'secret','topic':'secret'}]}
        self.assertNotIn('secret',str(diagnostic_report(s,NOW)))
