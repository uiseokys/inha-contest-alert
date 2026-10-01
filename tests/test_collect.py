import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from contest_alert import collect, core

class FakeClient:
    def get_text(self,url):
        if 'bad' in url: raise collect.FetchError('http_403','HTTP 403; 우회하지 않음')
        if 'robots' in url:return 'User-agent: *\nDisallow: /'
        if 'empty' in url:return '<html>Access denied</html>'
        return '<table><tr><td><a href="/bbs/ds/1/2/artclView.do">AI 경진대회 안내</a></td><td>2026.09.20</td></tr></table>'
    def browser_html(self,url):raise AssertionError('Browser must be disabled in fixture config')
    def close(self):pass

class CollectTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,9,22,11,40,tzinfo=ZoneInfo('Asia/Seoul'))
        self.config={'browser_fallback':False,'max_pages_per_source':1,'max_detail_requests':0,'lookback_days':120,'sources':[
            {'id':'ok','name':'정상','url':'https://good.example/list','kind':'k2web','mode':'contest','group':'inha'},
            {'id':'bad','name':'접속실패','url':'https://bad.example/list','kind':'k2web','mode':'contest','group':'inha'},
            {'id':'empty','name':'파싱실패','url':'https://empty.example/list','kind':'k2web','mode':'contest','group':'inha'}]}
    def test_partial_failure_is_reported_and_valid_items_preserved(self):
        state=collect.collect_all(self.config,core.empty_state(),self.now,FakeClient())
        self.assertEqual(len(state['items']),1)
        self.assertEqual(state['sources']['ok']['status'],'ok')
        self.assertEqual(state['sources']['bad']['status'],'error')
        self.assertEqual(state['sources']['empty']['status'],'error')
        self.assertIn('HTTP 403',state['sources']['bad']['message'])
    def test_robots_disallow_is_not_ignored(self):
        self.assertFalse(collect.robots_allowed('User-agent: *\nDisallow: /private', 'https://x.example/private/a'))
    def test_robots_allow_is_parsed(self):
        self.assertTrue(collect.robots_allowed('User-agent: *\nDisallow: /private','https://x.example/list'))
    def test_discover_only_same_site_boards(self):
        html='<a href="/swuniv/123/subview.do">공지사항</a><a href="https://evil.example/subview.do">공지사항</a>'
        self.assertEqual(collect.discover_pages(html,'https://good.example/'),['https://good.example/swuniv/123/subview.do'])
