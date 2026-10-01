import copy, json, tempfile, unittest
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from contest_alert.core import empty_state
from contest_alert.intake import apply_intake
from contest_alert.briefing import priority_lines
KST=ZoneInfo('Asia/Seoul'); NOW=datetime(2026,10,1,19,30,tzinfo=KST)

class V8ReviewTests(unittest.TestCase):
    def test_manual_entry_does_not_claim_live_collection(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);p={'title':'2026 AI 데이터 경진대회','url':'https://example.org/contest/1',
                'summary':'인공지능 모델을 개발하는 대회','evidence_url':'https://example.org/contest/1','checked_at':'2026-10-01'}
            (r/'intake.json').write_text(json.dumps({'version':1,'entries':{p['url']:p},'corrections':{}}))
            s=empty_state();s['updated_at']='2026-09-30T11:40:00+09:00'
            s['claims']['2026-01-01']={'status':'accepted','proof':'preserve'}
            before=copy.deepcopy(s['claims']);apply_intake(r,s,NOW)
            self.assertEqual(len(s['items']),1)
            self.assertEqual(s['updated_at'],'2026-09-30T11:40:00+09:00')
            self.assertEqual(s['claims'],before)
    def test_interest_does_not_list_elapsed_clock_but_keeps_submission(self):
        e={'id':'a','title':'AI 관심 대회','deadline':'2026-10-01','deadline_time':'18:00',
           'milestones':[{'label':'결과물 제출','date':'2026-10-03','time':'17:00'}]}
        text='\n'.join(priority_lines([e],empty_state(),NOW,{'watchlist':['a']},{}))
        self.assertNotIn('신청 마감 2026-10-01',text)
        self.assertIn('결과물 제출 2026-10-03',text)
    def test_elapsed_milestone_clock_is_not_in_upcoming_briefing(self):
        e={'id':'a','title':'AI 관심 대회','milestones':[{'label':'결과물 제출','date':'2026-10-01','time':'18:00'}]}
        text='\n'.join(priority_lines([e],empty_state(),NOW,{'watchlist':['a']},{}))
        self.assertNotIn('결과물 제출 2026-10-01',text)

if __name__=='__main__':unittest.main()
