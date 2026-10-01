import copy, json, tempfile, unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo
from contest_alert.core import empty_state, detail_fields
from contest_alert.settings import validate
from contest_alert.notify import reserve,publish,digest
KST=ZoneInfo('Asia/Seoul'); NOW=datetime(2026,10,1,19,10,tzinfo=KST)
class IntegrationTests(unittest.TestCase):
    def test_custom_notification_reservation(self):
        s=empty_state();d=reserve(s,NOW,'https://example.org','scheduled','1',settings=validate({'notification':{'time':'19:37'}}))
        self.assertEqual(d['target_at'],'2026-10-01T19:37:00+09:00')
    def test_disabled_does_not_reserve(self):
        s=empty_state();self.assertIsNone(reserve(s,NOW,'https://example.org','scheduled','1',settings=validate({'notification':{'enabled':False}})));self.assertEqual(s['claims'],{})
    def test_publish_uses_saved_clock(self):
        class Sender:
            def post(self,*args,**kw):self.p=json.loads(kw['data']);return type('R',(),{'status_code':200})()
        r=Sender();d={'day':'2026-10-01','mode':'scheduled','target_at':'2026-10-01T19:37:00+09:00','payload':{'message':'test'}}
        publish(d,'a'*48,NOW,sender=r)
        self.assertEqual(r.p['delay'],str(int(datetime(2026,10,1,19,37,tzinfo=KST).timestamp())))
    def test_details_preserve_conditions_and_milestones(self):
        h='<article><h1>2026 AI 대회</h1><p>참가 대상: 대학생 및 대학원생</p><p>팀 구성: 개인 또는 2~4인 팀</p><p>참가비: 무료</p><p>결과물 제출 마감: 2026.10.15 17:00</p></article>'
        d=detail_fields(h,'https://example.org/a')
        self.assertEqual(d['conditions']['cost']['value'],'free');self.assertEqual(d['milestones'][0]['date'],'2026-10-15')
    def test_interest_is_first_section(self):
        s=empty_state();s['items']['a']={'id':'a','title':'AI 관심 대회','url':'https://example.org/a','source_id':'s','source_name':'s','group':'external','deadline':'2026-10-03'}
        msg=digest(s,NOW,'https://example.org',settings=validate({'watchlist':['a']}))
        self.assertLess(msg.index('관심 공고'),msg.index('지난 알림'))
    def test_settings_partial_does_not_reset_disabled(self):
        from contest_alert.intake import validate_payload
        p=validate_payload('settings',{'notification':{'time':'17:11'}})
        self.assertNotIn('enabled',p['notification'])
if __name__=='__main__':unittest.main()
