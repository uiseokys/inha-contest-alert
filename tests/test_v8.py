import copy, importlib, io, json, unittest, zipfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from unittest.mock import patch
KST=ZoneInfo('Asia/Seoul')
def now(h=11,m=45):return datetime(2026,10,1,h,m,tzinfo=KST)
class SettingsTests(unittest.TestCase):
    def mod(self):
        self.assertIsNotNone(importlib.util.find_spec('contest_alert.settings'),'settings module required')
        return importlib.import_module('contest_alert.settings')
    def test_default_noon(self): self.assertEqual(self.mod().validate({})['notification']['time'],'12:00')
    def test_arbitrary_clock(self):
        s=self.mod().validate({'notification':{'time':'19:37'}})
        self.assertEqual(self.mod().target(s,now()).hour,19);self.assertEqual(self.mod().target(s,now()).minute,37)
    def test_invalid_time(self):
        for t in ['24:00','12:99','$(curl x)','1:00','12:00\n']:
            with self.subTest(t=t),self.assertRaises(ValueError):self.mod().validate({'notification':{'time':t}})
    def test_secrets_rejected(self):
        with self.assertRaises(ValueError):self.mod().validate({'topic':'secret'})
    def test_early_tick_no_collection(self):self.assertFalse(self.mod().due(self.mod().validate({}),{},now(9))['run'])
    def test_due_before_target(self):self.assertTrue(self.mod().due(self.mod().validate({}),{},now())['run'])
    def test_once_per_day(self):self.assertFalse(self.mod().due(self.mod().validate({}),{'claims':{'2026-10-01':{}}},now(18))['run'])
    def test_failed_collection_no_busy_loop(self):self.assertFalse(self.mod().due(self.mod().validate({}),{'scheduler_attempts':{'2026-10-01':'failed'}},now(18))['run'])
    def test_disabled_still_collects_noon(self):self.assertTrue(self.mod().due(self.mod().validate({'notification':{'enabled':False}}),{},now())['run'])
    def test_midnight_same_day_only(self):
        s=self.mod().validate({'notification':{'time':'00:05'}});self.assertTrue(self.mod().due(s,{},now(0,3))['run'])
    def test_watchlist_is_ids_only(self):
        with self.assertRaises(ValueError):self.mod().validate({'watchlist':[{'id':'a','note':'private'}]})
class IntakeTests(unittest.TestCase):
    def mod(self):
        self.assertIsNotNone(importlib.util.find_spec('contest_alert.intake'),'intake module required')
        return importlib.import_module('contest_alert.intake')
    def request(self,kind='settings',payload=None):return '<!-- CONTEST_REQUEST_V8 -->\n```json\n'+json.dumps({'version':1,'kind':kind,'payload':payload or {'notification':{'time':'18:30'}}})+'\n```'
    def test_owner_only(self):self.assertFalse(self.mod().authorized('stranger','owner'))
    def test_owner_case_insensitive(self):self.assertTrue(self.mod().authorized('Owner','owner'))
    def test_unmarked_body_no_op(self):self.assertIsNone(self.mod().parse_request('ordinary issue'))
    def test_settings_request(self):self.assertEqual(self.mod().parse_request(self.request())['kind'],'settings')
    def test_reject_extra_keys(self):
        with self.assertRaises(ValueError):self.mod().parse_request(self.request(payload={'topic':'secret'}))
    def test_reject_private_urls(self):
        for url in ['http://127.0.0.1/x','https://169.254.169.254/','https://localhost/a','javascript:alert(1)','https://example.com@127.0.0.1/','https://[::1]/']:
            with self.subTest(url=url),self.assertRaises(ValueError):self.mod().public_url(url)
    def test_manual_notice_requires_title_and_evidence(self):
        with self.assertRaises(ValueError):self.mod().parse_request(self.request('add_notice',{'url':'https://example.org/a'}))
    def test_manual_notice_valid(self):
        p={'url':'https://example.org/a','title':'2026 AI 데이터 경진대회','summary':'공공데이터 분석','deadline':'2026-11-01','evidence_url':'https://example.org/a','checked_at':'2026-10-01'}
        self.assertEqual(self.mod().parse_request(self.request('add_notice',p))['payload']['deadline'],'2026-11-01')
class ParticipationTests(unittest.TestCase):
    def mod(self):
        self.assertIsNotNone(importlib.util.find_spec('contest_alert.participation'),'participation module required')
        return importlib.import_module('contest_alert.participation')
    def test_unknown_not_allowed(self):self.assertEqual(self.mod().conditions('')['audience']['value'],'unknown')
    def test_university_evidence(self):
        c=self.mod().conditions('참가 대상: 대학생 및 대학원생\n팀 구성: 개인 또는 2~4인 팀\n참가비: 무료\n진행 방식: 온라인')
        self.assertIn('undergraduate',c['audience']['value']);self.assertEqual(c['cost']['value'],'free');self.assertEqual(c['team']['value'],'individual_or_team')
    def test_organizer_not_eligibility(self):self.assertEqual(self.mod().conditions('주최: 인하대학교\n참가 대상: 누구나')['affiliation']['value'],'unrestricted')
    def test_exclusion_is_unknown_not_yes(self):
        self.assertEqual(self.mod().conditions('참가 대상: 대학생 제외')['audience']['value'],'unknown')
    def test_submission_not_registration(self):
        x=self.mod().milestones('참가 신청 마감: 2026.10.01 18:00\n결과물 제출 마감: 2026.10.15 17:00','2026 AI 대회','https://example.org/a')
        self.assertEqual(len(x),1);self.assertEqual(x[0]['date'],'2026-10-15');self.assertEqual(x[0]['time'],'17:00')
    def test_no_year_no_invented_milestone(self):self.assertEqual(self.mod().milestones('코드 제출 마감: 10.15','AI 대회','https://example.org/a'),[])
class AttachmentTests(unittest.TestCase):
    def mod(self):
        self.assertIsNotNone(importlib.util.find_spec('contest_alert.attachments'),'attachments module required')
        return importlib.import_module('contest_alert.attachments')
    def test_only_linked_supported_attachments(self):
        h='<a href="/x.pdf">공지</a><a href="https://evil.org/x.pdf">공지</a><a href="/x.jpg">포스터</a>'
        self.assertEqual(self.mod().links(h,'https://example.org/a'),['https://example.org/x.pdf'])
    def test_text_document(self):self.assertIn('접수',self.mod().extract(b'\xec\xa0\x91\xec\x88\x98','txt')['text'])
    def test_hwpx(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:z.writestr('Contents/section0.xml','<s><p><t>접수기간 2026.10.01 ~ 2026.10.10</t></p></s>')
        self.assertIn('2026.10.10',self.mod().extract(b.getvalue(),'hwpx')['text'])
    def test_entity_rejected(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:z.writestr('Contents/section0.xml','<!DOCTYPE s [<!ENTITY x SYSTEM "file:///etc/passwd">]><s>&x;</s>')
        self.assertEqual(self.mod().extract(b.getvalue(),'hwpx')['status'],'unsafe_document')
    def test_image_and_hwp_not_fake_text(self):self.assertEqual(self.mod().extract(b'abc','hwp')['status'],'unsupported')
    def test_oversize_rejected(self):self.assertEqual(self.mod().extract(b'x'*5_000_001,'txt')['status'],'too_large')
    def test_pdf_no_text(self):
        from pypdf import PdfWriter
        b=io.BytesIO();p=PdfWriter();p.add_blank_page(width=100,height=100);p.write(b)
        self.assertEqual(self.mod().extract(b.getvalue(),'pdf')['status'],'no_text')
class AlertsTests(unittest.TestCase):
    def mod(self):
        self.assertIsNotNone(importlib.util.find_spec('contest_alert.alerts'),'alerts module required')
        return importlib.import_module('contest_alert.alerts')
    def test_low_sample_not_anomaly(self):self.assertEqual(self.mod().compare({'a':{'items':2,'known':2}}, {'a':{'items':2,'known':0}}),[])
    def test_stable_sample_regression(self):
        a={'a':{'items':8,'known':8,'ids':[str(i) for i in range(8)]}};b={'a':{'items':8,'known':1,'ids':[str(i) for i in range(8)]}}
        self.assertEqual(self.mod().compare(a,b)[0]['kind'],'date_regression')
    def test_new_unchecked_items_not_false_regression(self):
        a={'a':{'items':8,'known':8,'ids':[str(i) for i in range(8)]}};b={'a':{'items':80,'known':8,'ids':[str(i) for i in range(80)]}}
        self.assertEqual(self.mod().compare(a,b),[])
if __name__=='__main__':unittest.main()
