"""Calendar-day comparisons must not be rolling-24h or list-length subtraction."""
import copy
import json
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from contest_alert import core, daily, notify, render

TZ=ZoneInfo('Asia/Seoul')
def at(day=22, hour=11, minute=40):
    return datetime(2026,9,day,hour,minute,tzinfo=TZ)

def item(rid, sid='a', when=None):
    stamp=(when or at()).isoformat()
    return {'id':rid,'title':f'AI 공모전 {rid}','url':f'https://example.com/{rid}',
            'source_id':sid,'source_name':'인하대' if sid=='a' else '캠퍼스픽',
            'group':'inha' if sid=='a' else 'external','first_seen':stamp,'last_seen':stamp,
            'last_changed':stamp,'deadline':None}

class DailyTests(unittest.TestCase):
    def capture(self,s,now):
        self.assertTrue(callable(getattr(daily,'capture_snapshot',None)), 'capture_snapshot 구현 필요')
        s['updated_at']=now.isoformat()
        daily.capture_snapshot(s,now)
    def compare(self,s,now=None):
        self.assertTrue(callable(getattr(daily,'compare_day',None)), 'compare_day 구현 필요')
        return daily.compare_day(s,now or at())
    def base(self):
        s=core.empty_state()
        s['sources']={'a':{'name':'인하대','group':'inha','status':'ok'}}
        s['initialized_sources']=['a'];s['items']={'old':item('old',when=at(21))}
        self.capture(s,at(21));return s
    def add(self,s,rid='new',sid='a',when=None,kind='new'):
        when=when or at();s['items'][rid]=item(rid,sid,when)
        s['changes'].append({'id':rid,'kind':kind,'at':when.isoformat()})
        s['updated_at']=when.isoformat()
    def test_first_snapshot_is_baseline_not_all_items_new(self):
        s=self.base();result=self.compare(s,at(21))
        self.assertEqual(result['status'],'baseline');self.assertIsNone(result['new_count'])
        self.assertEqual(result['new_ids'],[])
    def test_yesterday_difference_counts_new_ids_not_total_difference(self):
        s=self.base();s['items']['old']['deadline']='2026-09-21'
        self.add(s);self.capture(s,at());result=self.compare(s)
        self.assertEqual(result['status'],'comparable');self.assertEqual(result['new_count'],1)
        self.assertEqual(result['new_ids'],['new']);self.assertEqual(result['base_date'],'2026-09-21')
    def test_same_day_refresh_does_not_reset_the_yesterday_baseline(self):
        s=self.base();self.add(s);self.capture(s,at());self.capture(s,at(22,15))
        result=self.compare(s,at(22,15));self.assertEqual(result['new_count'],1)
        self.assertEqual(result['base_at'],at(21).isoformat())
    def test_yesterday_last_snapshot_is_the_reference(self):
        s=self.base();self.add(s,'last-night',when=at(21,20));self.capture(s,at(21,20))
        self.add(s);self.capture(s,at());result=self.compare(s)
        self.assertEqual(result['new_ids'],['new']);self.assertEqual(result['base_at'],at(21,20).isoformat())
    def test_missing_yesterday_names_older_date_not_yesterday(self):
        s=self.base();self.add(s,when=at(23));self.capture(s,at(23));result=self.compare(s,at(23))
        self.assertEqual(result['status'],'gap');self.assertEqual(result['base_date'],'2026-09-21')
        self.assertEqual(result['new_count'],1)
        text=notify.digest(s,at(23),'https://example.com/dashboard')
        self.assertIn('2026-09-21 대비 신규 1건',text);self.assertNotIn('어제 대비 신규 1건',text)
    def test_new_source_initial_import_excluded(self):
        s=self.base();s['sources']['b']={'name':'캠퍼스픽','group':'external','status':'ok'}
        s['initialized_sources'].append('b');self.add(s,'imported','b',kind='initial');self.capture(s,at())
        result=self.compare(s);self.assertEqual(result['new_count'],0);self.assertEqual(result['initial_count'],1)
    def test_failed_yesterday_source_is_separate_unverified_additions(self):
        s=self.base();s['sources']['a']['status']='error';self.capture(s,at(21))
        s['sources']['a']['status']='ok';self.add(s);self.capture(s,at());result=self.compare(s)
        self.assertEqual(result['new_count'],0);self.assertEqual(result['unverified_count'],1)
        self.assertTrue(result['partial'])
    def test_all_sources_failed_is_not_zero_new(self):
        s=self.base();s['sources']['a']['status']='error';self.capture(s,at());result=self.compare(s)
        self.assertEqual(result['status'],'unobserved');self.assertIsNone(result['new_count'])
        self.assertIn('비교 불가',notify.digest(s,at(),'https://example.com/dashboard'))
    def test_partial_source_includes_actual_found_ids_with_warning(self):
        s=self.base();s['sources']['a']['status']='partial';self.add(s);self.capture(s,at())
        result=self.compare(s);self.assertEqual(result['new_count'],1);self.assertTrue(result['partial'])
    def test_zero_new_is_real_comparison_not_baseline(self):
        s=self.base();self.capture(s,at());result=self.compare(s)
        self.assertEqual(result['status'],'comparable');self.assertEqual(result['new_count'],0)
    def test_repeated_changes_count_once_and_new_not_also_updated(self):
        s=self.base();self.add(s)
        for rid in ['old','old','new']:
            s['changes'].append({'id':rid,'kind':'updated','at':at().isoformat()})
        self.capture(s,at());result=self.compare(s)
        self.assertEqual(result['updated_count'],1);self.assertEqual(result['updated_ids'],['old'])
    def test_korean_calendar_boundary_with_utc_clock(self):
        s=self.base();when=datetime(2026,9,21,15,1,tzinfo=ZoneInfo('UTC'))
        self.add(s,when=when);self.capture(s,when);result=self.compare(s,when)
        self.assertEqual(result['date'],'2026-09-22');self.assertEqual(result['new_count'],1)
        self.assertIn('2026-09-22',s['daily_snapshots'])
    def test_stale_state_is_not_todays_zero(self):
        s=self.base();result=self.compare(s,at(23))
        self.assertEqual(result['status'],'stale');self.assertIsNone(result['new_count'])
    def test_upgrade_does_not_replace_existing_items_or_claims(self):
        s=core.empty_state();s.pop('daily_snapshots',None)
        s['items']={'legacy':item('legacy')};s['claims']={'2026-09-22':{'status':'accepted'}}
        before=copy.deepcopy(s);self.capture(s,at())
        self.assertEqual(s['claims'],before['claims']);self.assertEqual(s['items'],before['items'])
        self.assertEqual(self.compare(s)['status'],'baseline')
    def test_history_is_bounded_and_does_not_copy_secrets(self):
        s=self.base();s['claims']['x']={'topic':'private-test-value'}
        for d in range(40):self.capture(s,at(21)+timedelta(days=d))
        self.assertLessEqual(len(s['daily_snapshots']),32)
        self.assertNotIn('private-test-value',json.dumps(s['daily_snapshots']))
    def test_public_summary_and_notification_use_identical_daily_count(self):
        s=self.base();self.add(s);self.capture(s,at());s['digest_cursor']=at(22,11,41).isoformat()
        result=render.public_data(s,at());self.assertIn('daily_comparison',result)
        self.assertEqual(result['daily_comparison']['new_count'],1)
        text=notify.digest(s,at(),'https://example.com/dashboard')
        self.assertIn('어제 대비 신규 1건',text);self.assertIn('인하대 1건',text)
        self.assertTrue(next(i for i in result['items'] if i['id']=='new')['daily_new'])
        self.assertNotIn('daily_snapshots',result)
    def test_closed_new_item_still_in_comparison_count(self):
        s=self.base();self.add(s);s['items']['new']['deadline']='2026-09-21';self.capture(s,at())
        self.assertEqual(self.compare(s)['new_count'],1)
    def test_first_collect_with_old_initial_records_never_calls_them_new(self):
        s=self.base();self.add(s,kind='initial');self.capture(s,at())
        self.assertEqual(self.compare(s)['new_count'],0);self.assertEqual(self.compare(s)['initial_count'],1)

class DailyCollectionIntegrationTests(unittest.TestCase):
    def test_collect_records_empty_successful_source_then_new_next_day(self):
        from contest_alert.collect import collect_all
        source={'id':'a','name':'인하대','url':'https://example.com/list','kind':'k2web','group':'inha','mode':'contest'}
        config={'sources':[source],'browser_fallback':False,'max_pages_per_source':1,'max_detail_requests':0}
        class Client:
            html='<main>등록된 게시물이 없습니다</main>'
            def get_text(self,url):return self.html
        client=Client();state=collect_all(config,core.empty_state(),at(21),client)
        self.assertEqual(state['daily_snapshots']['2026-09-21']['ids'],[])
        client.html='<main><a href="/bbs/test/1/123/artclView.do">AI 경진대회</a></main>'
        state=collect_all(config,state,at(),client)
        self.assertEqual(daily.compare_day(state,at())['new_count'],1)
    def test_digest_reservation_does_not_reset_daily_counts(self):
        helper=DailyTests();s=helper.base();helper.add(s);helper.capture(s,at())
        before=daily.compare_day(s,at())
        draft=notify.reserve(s,at(),'https://example.com/dashboard','scheduled','daily-test')
        self.assertEqual(daily.compare_day(s,at()),before)
        self.assertIn('어제 대비 신규 1건',draft['payload']['message'])
        self.assertIsNone(notify.reserve(s,at(22,13),'https://example.com/dashboard','manual','again'))
    def test_full_failure_keeps_previous_items_and_records_bad_snapshot(self):
        from contest_alert.collect import collect_all,FetchError
        helper=DailyTests();s=helper.base()
        config={'sources':[{'id':'a','name':'인하대','url':'https://example.com/list','kind':'k2web'}],
                'browser_fallback':False,'max_pages_per_source':1,'max_detail_requests':0}
        class Client:
            def get_text(self,url):raise FetchError('http_403','HTTP 403')
        state=collect_all(config,s,at(),Client())
        self.assertIn('old',state['items'])
        self.assertEqual(state['daily_snapshots']['2026-09-22']['source_statuses']['a'],'error')
        self.assertIsNone(daily.compare_day(state,at())['new_count'])
