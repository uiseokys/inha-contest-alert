import json, unittest
from datetime import datetime, date
from zoneinfo import ZoneInfo
from unittest.mock import patch
from contest_alert.core import status_of, empty_state
from contest_alert.render import public_data
KST=ZoneInfo('Asia/Seoul')
def dt(h,m=0): return datetime(2026,9,23,h,m,tzinfo=KST)
class ExactTimeTests(unittest.TestCase):
    def test_before_known_deadline_is_active(self):
        self.assertEqual(status_of({'deadline':'2026-09-23','deadline_time':'18:00'},dt(17,59)), 'active')
    def test_at_known_deadline_is_closed(self):
        self.assertEqual(status_of({'deadline':'2026-09-23','deadline_time':'18:00'},dt(18)), 'closed')
    def test_start_later_today_is_upcoming(self):
        self.assertEqual(status_of({'registration_start':'2026-09-23','registration_start_time':'14:00','deadline':'2026-10-03'},dt(13)), 'upcoming')
    def test_start_exactly_now_is_active(self):
        self.assertEqual(status_of({'registration_start':'2026-09-23','registration_start_time':'14:00','deadline':'2026-10-03'},dt(14)), 'active')
    def test_date_only_today_not_falsely_closed(self):
        self.assertEqual(status_of({'deadline':'2026-09-23'},dt(23,59)), 'active')
    def test_timezone_is_korea_not_computer_local(self):
        now=datetime(2026,9,23,9,tzinfo=ZoneInfo('UTC'))
        self.assertEqual(status_of({'deadline':'2026-09-23','deadline_time':'18:00'},now),'closed')
    def test_invalid_date_does_not_claim_active(self):
        self.assertEqual(status_of({'deadline':'2026-99-23'},dt(12)),'unknown')
    def test_ambiguous_time_is_not_used(self):
        self.assertEqual(status_of({'deadline':'2026-09-23','deadline_time':'18:00','registration_time_ambiguous':True},dt(20)),'active')
    def test_legacy_date_interface_retained(self):
        self.assertEqual(status_of({'deadline':'2026-09-24'},date(2026,9,23)),'active')
class OperationsTests(unittest.TestCase):
    def test_public_metadata_exists_and_does_not_export_claims(self):
        state=empty_state();state['claims']={'2026-09-23':{'status':'accepted','at':dt(12).isoformat(),'accepted_at':dt(12).isoformat(),'topic':'SECRET','run_id':'secret_internal'}}
        data=public_data(state,dt(12));self.assertIn('runtime',data)
        runtime=data['runtime'];self.assertEqual(runtime['notification']['status'],'accepted')
        self.assertNotIn('SECRET',json.dumps(data));self.assertNotIn('claims',data)
    def test_build_time_and_collection_time_separate(self):
        state=empty_state();state['updated_at']=dt(11,40).isoformat()
        data=public_data(state,dt(12));self.assertIn('runtime',data)
        self.assertEqual(data['runtime']['generated_at'],dt(12).isoformat())
        self.assertEqual(data['runtime']['collection']['attempted_at'],dt(11,40).isoformat())
    def test_public_status_uses_exact_time(self):
        state=empty_state();state['items']['a']={'id':'a','title':'AI test contest','url':'https://example.org/1','source_name':'test','source_id':'s','group':'external','deadline':'2026-09-23','deadline_time':'18:00'}
        self.assertEqual(public_data(state,dt(18))['items'][0]['status'],'closed')
