import copy,unittest
from test_v7_events import item,NOW,OFF
from datetime import timedelta
from contest_alert.core import empty_state,merge_items
from contest_alert.daily import capture_snapshot
from contest_alert.notify import digest
from contest_alert.render import public_data

class DigestEventTests(unittest.TestCase):
    def state(self):
        s=empty_state();s['items']={'a':item('a',website_url=OFF)};s['sources']={'s':{'name':'학과','status':'ok'},'dacon':{'name':'DACON','status':'ok'}};s['initialized_sources']=['s','dacon'];s['updated_at']=(NOW-timedelta(days=1)).isoformat();capture_snapshot(s,NOW-timedelta(days=1));return s
    def test_digest_repost_is_zero_new_event_and_one_notice(self):
        s=self.state();merge_items(s,[item('b',url=OFF,source_id='dacon',source_name='DACON')],NOW)
        text=digest(s,NOW,'https://example.org/')
        self.assertIn('새 대회·프로그램 0개',text);self.assertIn('새 공고 1건',text)
        self.assertEqual(text.count('• 2026 공공데이터 AI 분석 경진대회'),1)
    def test_digest_extension_includes_previous_and_new_deadline(self):
        s=self.state();merge_items(s,[item('a',website_url=OFF,deadline='2026-10-07')],NOW)
        text=digest(s,NOW,'https://example.org/')
        self.assertIn('마감 연장 1개',text);self.assertIn('2026-09-30 → 2026-10-07',text)
    def test_grouped_public_fields_do_not_leak_private_state(self):
        s=self.state();s['items']['a'].update(secret_topic='TOP_SECRET',_topic_text='PRIVATE',_automatic_dates={'deadline':'SECRET'},private='HIDDEN')
        import json
        text=json.dumps(public_data(s,NOW),ensure_ascii=False)
        for value in ['TOP_SECRET','PRIVATE','SECRET','HIDDEN']:self.assertNotIn(value,text)
