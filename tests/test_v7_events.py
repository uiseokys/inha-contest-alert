import copy,importlib.util,unittest
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from contest_alert.core import empty_state,merge_items
from contest_alert.daily import capture_snapshot,compare_day
NOW=datetime(2026,9,23,11,40,tzinfo=ZoneInfo('Asia/Seoul'))
OFF='https://dacon.io/competitions/official/236754/overview/'
def item(rid='a',**changes):
    x=dict(id=rid,title='2026 공공데이터 AI 분석 경진대회',url='https://univ.example/notices/'+rid,source_id='s',source_name='학과',group='inha',first_seen=(NOW-timedelta(days=1)).isoformat(),last_changed=(NOW-timedelta(days=1)).isoformat(),last_seen=NOW.isoformat(),deadline='2026-09-30',registration_start='2026-09-01',organizer='공공기관',relevance_status='included')
    x.update(changes);return x
class EventTests(unittest.TestCase):
    def group(self,rows,state=None):
        self.assertIsNotNone(importlib.util.find_spec('contest_alert.events'),'event grouping not implemented')
        from contest_alert.events import group_events
        s=state or empty_state();s['items']={x['id']:x for x in rows};return group_events(s),s
    def test_shared_official_url_merges_sources_not_records(self):
        rows=[item('a',website_url=OFF),item('b',url=OFF,source_id='dacon',source_name='DACON',group='external')]
        events,s=self.group(rows);self.assertEqual(len(events),1);self.assertEqual(len(s['items']),2);self.assertEqual(len(events[0]['sources']),2)
        self.assertEqual(events[0]['url'],OFF)
    def test_diff_official_ids_never_merge_even_same_title(self):
        rows=[item('a',url=OFF),item('b',url=OFF.replace('236754','236753'))]
        self.assertEqual(len(self.group(rows)[0]),2)
    def test_diff_year_round_track_never_merge(self):
        for a,b in [('2025 AI 경진대회','2026 AI 경진대회'),('2026 AI 교육 3차','2026 AI 교육 4차'),('2026 데이터 대회 주제 3','2026 데이터 대회 주제 4')]:
            with self.subTest(a=a):self.assertEqual(len(self.group([item('a',title=a,website_url=OFF),item('b',title=b,url=OFF)])[0]),2)
    def test_common_homepage_is_not_a_group_key(self):
        rows=[item('a',title='2026 모델 개발 공모전',website_url='https://example.org/'),item('b',title='2026 AI 영상 경진대회',website_url='https://example.org/')]
        self.assertEqual(len(self.group(rows)[0]),2)
    def test_exact_evidence_supported_title_fallback(self):
        rows=[item('a'),item('b',source_id='campus',source_name='캠퍼스픽',url='https://www.campuspick.com/contest/view?id=2')]
        self.assertEqual(len(self.group(rows)[0]),1)
    def test_similar_not_identical_title_is_not_enough(self):
        self.assertEqual(len(self.group([item('a'),item('b',title='2026 공공데이터 AI 분석 해커톤')])[0]),2)
    def test_registry_stable_and_old_favorite_ids_survive(self):
        ev,s=self.group([item('a')]);saved=ev[0]['id']
        ev2,s=self.group([item('a',website_url=OFF),item('b',url=OFF,first_seen=NOW.isoformat())],s)
        self.assertEqual(saved,ev2[0]['id']);self.assertIn('a',ev2[0]['favorite_ids'])
    def test_ambiguous_group_dates_without_official_evidence_stay_uncertain(self):
        shared='https://agency.example/contest/2026-ai'
        ev,s=self.group([item('a',website_url=shared),item('b',website_url=shared,deadline='2026-10-01')])
        self.assertEqual(len(ev),1);self.assertFalse(ev[0].get('deadline'));self.assertTrue(ev[0].get('cross_source_conflict'))
    def test_new_repost_does_not_become_new_event(self):
        rows=[item('a',website_url=OFF)];ev,s=self.group(rows);s['initialized_sources']=['s','dacon'];s['sources']={'s':{'status':'ok'},'dacon':{'status':'ok'}};s['updated_at']=(NOW-timedelta(days=1)).isoformat();capture_snapshot(s,NOW-timedelta(days=1))
        merge_items(s,[item('b',url=OFF,source_id='dacon',source_name='DACON',first_seen=NOW.isoformat())],NOW);ev,s=self.group(list(s['items'].values()),s)
        from contest_alert.events import event_comparison
        c=event_comparison(s,compare_day(s,NOW),ev);self.assertEqual(c['new_count'],1);self.assertEqual(c['new_event_count'],0)
    def test_truly_new_event_count_and_migration_do_not_reset_snapshots(self):
        ev,s=self.group([item('a',website_url=OFF)]);s['sources']={'s':{'status':'ok'}};s['initialized_sources']=['s'];s['updated_at']=(NOW-timedelta(days=1)).isoformat();capture_snapshot(s,NOW-timedelta(days=1));snap=copy.deepcopy(s['daily_snapshots'])
        merge_items(s,[item('b',title='2026 다른 AI 모델 경진대회',url=OFF.replace('236754','999999'))],NOW)
        from contest_alert.events import group_events,event_comparison
        c=event_comparison(s,compare_day(s,NOW),group_events(s));self.assertEqual(c['new_event_count'],1);self.assertEqual(snap,s['daily_snapshots'])
    def test_extension_is_recorded_with_old_and_new_date(self):
        s=empty_state();s['items']['a']=item('a');s['initialized_sources']=['s']
        merge_items(s,[item('a',deadline='2026-10-07')],NOW)
        change=s['changes'][-1];self.assertEqual(change.get('old_deadline'),'2026-09-30');self.assertEqual(change.get('new_deadline'),'2026-10-07')
