import unittest
from datetime import datetime, date
from zoneinfo import ZoneInfo
from contest_alert import core

NOW = datetime(2026, 9, 22, 11, 40, tzinfo=ZoneInfo('Asia/Seoul'))
SRC = {'id':'ds','name':'데이터사이언스학과','group':'inha','url':'https://datascience.inha.ac.kr/datascience/11588/subview.do','kind':'k2web','mode':'contest'}
HTML = '''<table><tr><td>15</td><td><a href="/bbs/datascience/123/987/artclView.do">2026 데이터 경진대회 안내</a></td><td>2026.09.21</td></tr>
<tr><td>14</td><td><a href="/bbs/datascience/123/986/artclView.do">2026 수강신청 안내</a></td><td>2026.09.20</td></tr></table>'''

class CoreTests(unittest.TestCase):
    def test_canonical_removes_tracking_but_keeps_article_id(self):
        self.assertEqual(core.canonical('https://aix.inha.ac.kr/news/notice/?vid=109&utm_source=x#foo'), 'https://aix.inha.ac.kr/news/notice/?vid=109')
    def test_invalid_scheme_is_rejected(self):
        self.assertEqual(core.canonical('javascript:alert(1)'), '')
    def test_k2web_parsing_and_filter(self):
        items, count = core.parse_listing(HTML, SRC)
        self.assertEqual(count, 2)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['posted_at'], '2026-09-21')
        self.assertIn('/987/', items[0]['url'])
    def test_mangboard_vid(self):
        source = dict(SRC, id='aix',url='https://aix.inha.ac.kr/news/notice/',kind='mangboard')
        items, count = core.parse_listing('<tr><td><a href="?vid=109">[행사] WE·AX Project 공모 안내</a></td><td>2026-09-15</td></tr>',source)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['posted_at'], '2026-09-15')
    def test_platform_status_and_no_fake_deadline(self):
        source = dict(SRC, id='dacon',url='https://dacon.io/competitions',kind='dacon',mode='platform')
        items, _ = core.parse_listing('<a href="/competitions/official/123/overview/"><h3>AI 경진대회</h3><span>참가신청중 1,079명</span></a>',source)
        self.assertEqual(items[0]['platform_status'], 'open')
        self.assertIsNone(items[0]['deadline'])
    def test_only_explicit_registration_date(self):
        start, end = core.registration_dates('행사기간: 2026.10.10 ~ 2026.10.12\n접수기간: 2026.09.15 ~ 2026.09.30')
        self.assertEqual((start,end), ('2026-09-15','2026-09-30'))
        self.assertEqual(core.registration_dates('행사기간: 2026.10.10 ~ 2026.10.12'), (None,None))
        self.assertEqual(core.registration_dates('접수기간: 9/15 ~ 9/30'), (None,None))
    def test_ambiguous_registration_dates_stay_unknown(self):
        self.assertEqual(core.registration_dates('접수기간: 2026.09.01 ~ 2026.09.10\n추가 접수기간: 2026.09.20 ~ 2026.09.30'),(None,None))
    def test_ai_not_matched_inside_unrelated_english_word(self):
        self.assertFalse(core.relevant('Chair design competition', 'ai_contest'))
        self.assertTrue(core.relevant('AI 데이터 경진대회', 'ai_contest'))
        self.assertFalse(core.relevant('AI 경진대회 수상 소식','contest'))
    def test_merge_baseline_and_duplicate(self):
        records, _ = core.parse_listing(HTML,SRC)
        s=core.empty_state()
        core.merge_items(s, records, NOW)
        self.assertEqual(len(s['items']),1)
        self.assertEqual(s['changes'][0]['kind'],'initial')
        core.merge_items(s, records, NOW)
        self.assertEqual(len(s['changes']),1)
    def test_merge_preserves_old_items_when_fetch_fails(self):
        records,_=core.parse_listing(HTML,SRC)
        s=core.empty_state();core.merge_items(s,records,NOW)
        core.merge_items(s,[],NOW)
        self.assertEqual(len(s['items']),1)
    def test_source_first_recovery_is_baseline_not_new(self):
        records,_=core.parse_listing(HTML,SRC)
        s=core.empty_state(); s['updated_at']=NOW.isoformat()
        core.merge_items(s,records,NOW)
        self.assertEqual(s['changes'][0]['kind'],'initial')
    def test_unknown_date_does_not_mean_open(self):
        self.assertEqual(core.status_of({'deadline':None}, NOW.date()),'unknown')
    def test_deadline_date_is_inclusive(self):
        self.assertEqual(core.status_of({'deadline':'2026-09-22'},NOW.date()),'active')
        self.assertEqual(core.status_of({'deadline':'2026-09-21'},NOW.date()),'closed')
    def test_old_signup_label_is_not_trusted_forever(self):
        item={'platform_status':'open','last_seen':'2026-09-10T11:40:00+09:00'}
        self.assertEqual(core.status_of(item,NOW.date()),'unknown')
    def test_negative_list_has_no_records(self):
        items,count=core.parse_listing('<html>Access Denied</html>',SRC)
        self.assertEqual((items,count),([],0))

if __name__=='__main__':unittest.main()

class PlatformNoiseTests(unittest.TestCase):
    def test_platform_counter_changes_do_not_change_title(self):
        source={'id':'d','name':'D','url':'https://dacon.io/competitions','kind':'dacon','mode':'platform'}
        a='<a href="/competitions/official/123/overview/">AI 탐지 경진대회 알고리즘 | 코드 제출 평가 참가신청중 1,079명</a>'
        b=a.replace('1,079명','1,100명')
        ia,_=core.parse_listing(a,source);ib,_=core.parse_listing(b,source)
        self.assertEqual(ia[0]['title'],ib[0]['title'])
