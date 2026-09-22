import copy,inspect,json,tempfile,unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from contest_alert.core import empty_state,status_of
from contest_alert.operations import runtime_metadata,code_fingerprint
from contest_alert.render import public_data,deadline_sort_key
from contest_alert.diagnostics import diagnostic_report,reason_for
NOW=datetime(2026,9,23,12,tzinfo=ZoneInfo('Asia/Seoul'))
class ReviewTests(unittest.TestCase):
    def test_runtime_collection_whitelists_state_fields(self):
        s=empty_state();s['operations']={'collection':{'status':'failed','version':'7.0.0','topic':'PRIVATE_OPS','raw_html':'PRIVATE_HTML'}}
        text=json.dumps(runtime_metadata(s,NOW));self.assertNotIn('PRIVATE_OPS',text);self.assertNotIn('PRIVATE_HTML',text)
    def test_fingerprint_covers_web_source_not_only_python(self):
        self.assertIn('root',inspect.signature(code_fingerprint).parameters,'fingerprint cannot verify web content')
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'contest_alert').mkdir();(root/'web').mkdir();(root/'contest_alert/a.py').write_text('a=1');(root/'web/app.js').write_text('v=1')
            first=code_fingerprint(root);(root/'web/app.js').write_text('v=2');self.assertNotEqual(first,code_fingerprint(root))
    def test_explicit_non_korean_instant_overrides_korean_date_boundary(self):
        row={'deadline':'2026-09-22','deadline_time':'23:00','registration_timezone':'America/New_York'}
        self.assertEqual(status_of(row,NOW.replace(hour=11,minute=59)),'active')
    def test_public_normalizes_known_clock_for_browser(self):
        s=empty_state();s['items']['a']={'id':'a','title':'AI test','url':'https://example.org/1','source_id':'s','source_name':'S','deadline':'2026-09-23','deadline_time':'18:00'}
        value=public_data(s,NOW)['events'][0]
        self.assertEqual(value.get('deadline_at'),'2026-09-23T18:00:00+09:00')
    def test_backend_sorts_exact_time_on_same_day(self):
        rows=[{'title':'A','deadline':'2026-10-01','deadline_time':'10:00'},{'title':'Z','deadline':'2026-10-01','deadline_time':'18:00'}]
        self.assertEqual(sorted(rows,key=lambda x:deadline_sort_key(x,NOW))[0]['title'],'Z')
    def test_ambiguous_stored_date_not_sorted_above_known(self):
        rows=[{'title':'ambiguous','deadline':'2026-12-01','registration_ambiguous':True},{'title':'known','deadline':'2026-10-01'}]
        self.assertEqual(sorted(rows,key=lambda x:deadline_sort_key(x,NOW))[0]['title'],'known')
    def test_no_timestamp_is_not_an_attempt(self):
        s=empty_state();s['items']['a']={'id':'a','source_id':'s','title':'AI','url':'https://example.org/1'}
        self.assertEqual(diagnostic_report(s,NOW)['sources'][0]['attempted_this_run'],0)
    def test_manual_corrections_separate_from_automatic_coverage(self):
        s=empty_state();s['items']['a']={'id':'a','source_id':'s','deadline':'2026-10-01','manual_correction':{'needs_review':True},'_automatic_dates':{'deadline':None},'date_failure_code':'no_explicit_date'}
        r=diagnostic_report(s,NOW);self.assertEqual(r.get('manual_count'),1);self.assertEqual(r.get('automatic_deadline_known'),0);self.assertEqual(reason_for(s['items']['a']),'manual_review')
    def test_changed_workflow_preserves_failed_collection_snapshot_without_notification(self):
        text=(Path(__file__).resolve().parents[1]/'.github/workflows/daily.yml').read_text()
        self.assertIn('id: collect',text);self.assertIn("steps.collect.outcome == 'success'",text);self.assertIn('Persist failed collection metadata',text)
    def test_named_tracks_sharing_landing_page_are_not_merged(self):
        from test_v7_events import item,OFF
        from contest_alert.events import group_events
        s=empty_state();s['items']={'a':item('a',title='2026 AI 경진대회 이미지 부문',website_url=OFF),'b':item('b',title='2026 AI 경진대회 음성 부문',website_url=OFF)}
        self.assertEqual(len(group_events(s)),2)
    def test_read_only_audit_never_overwrites_state_or_sends(self):
        from unittest.mock import patch
        from contest_alert.__main__ import main
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'data').mkdir();(root/'config.json').write_text('{"sources":[]}')
            s=empty_state();s['claims']['2026-09-22']={'status':'accepted','test':'SENTINEL'};(root/'data/state.json').write_text(json.dumps(s));before=(root/'data/state.json').read_bytes()
            with patch('sys.argv',['contest_alert','audit','--root',str(root)]),patch('contest_alert.__main__.collect_all',side_effect=lambda cfg,st,now:st),patch('contest_alert.__main__.reserve') as reserve,patch('contest_alert.__main__.publish') as publish:
                self.assertEqual(main(),0);reserve.assert_not_called();publish.assert_not_called()
            self.assertEqual(before,(root/'data/state.json').read_bytes());self.assertTrue((root/'.runtime/quality.json').exists())
    def test_collect_fatal_error_keeps_prior_items_and_records_failure(self):
        import shutil
        from unittest.mock import patch
        from contest_alert.__main__ import main
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'data').mkdir();(root/'config.json').write_text('{"sources":[]}');shutil.copytree(Path(__file__).resolve().parents[1]/'web',root/'web')
            s=empty_state();s['claims']['2026-09-22']={'status':'accepted','test':'SENTINEL'};(root/'data/state.json').write_text(json.dumps(s))
            with patch('sys.argv',['contest_alert','collect','--root',str(root)]),patch('contest_alert.__main__.collect_all',side_effect=ValueError('example failure')):
                with self.assertRaises(ValueError):main()
            after=json.loads((root/'data/state.json').read_text());self.assertEqual(s['items'],after['items']);self.assertEqual(s['claims'],after['claims']);self.assertEqual(after['operations']['collection']['status'],'failed');self.assertTrue((root/'site/health.json').exists())
    def test_parser_upgrade_correction_is_not_reported_as_confirmed_extension(self):
        from test_v7_digest_events import DigestEventTests
        from test_v7_events import item,OFF
        from contest_alert.core import merge_items
        from contest_alert.events import group_events,event_comparison
        from contest_alert.daily import compare_day
        s=DigestEventTests().state();s['items']['a']['date_parser_version']=6
        merge_items(s,[item('a',website_url=OFF,deadline='2026-10-07',date_parser_version=7)],NOW)
        c=event_comparison(s,compare_day(s,NOW),group_events(s));self.assertEqual(c['deadline_extensions'],[]);self.assertEqual(c.get('date_correction_count'),1)
    def test_scheduled_due_list_uses_noon_delivery_time(self):
        from test_v7_events import item
        from contest_alert.notify import reserve
        s=empty_state();s['items']={'a':item('a',title='11시50분 마감 테스트',deadline='2026-09-23',deadline_time='11:50')};s['sources']={'s':{'status':'ok'}}
        text=reserve(s,NOW.replace(hour=11,minute=40),'https://example.org/','scheduled','test')['payload']['message']
        self.assertNotIn('7일 이내 마감일 확인:',text)
