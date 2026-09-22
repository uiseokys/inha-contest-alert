import unittest,json
from datetime import datetime
from zoneinfo import ZoneInfo
from contest_alert import core,notify

TZ=ZoneInfo('Asia/Seoul')
class Reply:
    status_code=200
class Sender:
    def __init__(self):self.calls=[]
    def post(self,*args,**kwargs):self.calls.append((args,kwargs));return Reply()

class NotifyTests(unittest.TestCase):
    def test_noon_is_korean_time_not_utc(self):
        now=datetime(2026,9,22,2,40,tzinfo=ZoneInfo('UTC'))
        self.assertEqual(notify.noon_target(now).isoformat(),'2026-09-22T12:00:00+09:00')
    def test_empty_day_still_builds_a_message(self):
        state=core.empty_state();state['sources']={'x':{'status':'ok'}}
        draft=notify.reserve(state,datetime(2026,9,22,11,40,tzinfo=TZ),'https://a.github.io/b/','scheduled','1')
        self.assertIn('0건',draft['payload']['message'])
        self.assertEqual(draft['day'],'2026-09-22')
    def test_second_attempt_same_date_is_suppressed(self):
        state=core.empty_state();now=datetime(2026,9,22,11,40,tzinfo=TZ)
        self.assertIsNotNone(notify.reserve(state,now,'https://a.github.io/b/','scheduled','1'))
        self.assertIsNone(notify.reserve(state,now,'https://a.github.io/b/','scheduled','2'))
    def test_failure_is_not_reported_as_no_new_posts(self):
        state=core.empty_state();state['sources']={'x':{'status':'error'}}
        text=notify.digest(state,datetime(2026,9,22,11,40,tzinfo=TZ),'https://a.github.io/b/')
        self.assertIn('수집 실패',text)
        self.assertNotIn('새 공고가 없습니다',text)
    def test_old_manual_refresh_events_are_not_lost(self):
        state=core.empty_state();state['items']={'a':{'id':'a','title':'어젯밤 신규 공모전','source_name':'학과'}}
        state['changes']=[{'id':'a','kind':'new','at':'2026-09-21T18:00:00+09:00'}]
        state['digest_cursor']='2026-09-21T11:40:00+09:00'
        self.assertIn('어젯밤 신규 공모전',notify.digest(state,datetime(2026,9,22,11,40,tzinfo=TZ),'https://a.github.io/b/'))
    def test_scheduled_publish_uses_unix_noon(self):
        state=core.empty_state();now=datetime(2026,9,22,11,40,tzinfo=TZ);sender=Sender()
        draft=notify.reserve(state,now,'https://a.github.io/b/','scheduled','1')
        notify.publish(draft,'x'*48,now,sender)
        body=json.loads(sender.calls[0][1]['data'])
        self.assertEqual(body['delay'],str(int(datetime(2026,9,22,12,tzinfo=TZ).timestamp())))
        self.assertNotIn('topic',draft['payload'])
    def test_late_publish_is_immediate_with_note(self):
        state=core.empty_state();early=datetime(2026,9,22,11,40,tzinfo=TZ);late=datetime(2026,9,22,12,15,tzinfo=TZ);sender=Sender()
        draft=notify.reserve(state,early,'https://a.github.io/b/','scheduled','1')
        notify.publish(draft,'x'*48,late,sender)
        body=json.loads(sender.calls[0][1]['data'])
        self.assertNotIn('delay',body)
        self.assertIn('지연',body['message'])
    def test_short_topic_rejected(self):
        with self.assertRaises(ValueError):notify.validate_topic('inha')
    def test_korean_payload_fits_limit(self):
        state=core.empty_state();now=datetime(2026,9,22,11,40,tzinfo=TZ)
        for i in range(100):
            state['items'][str(i)]={'id':str(i),'title':'아주긴공모전제목'*40,'source_name':'데이터사이언스학과'}
            state['changes'].append({'id':str(i),'kind':'new','at':now.isoformat()})
        draft=notify.reserve(state,now,'https://a.github.io/b/','manual','1');sender=Sender()
        notify.publish(draft,'x'*48,now,sender)
        self.assertLessEqual(len(sender.calls[0][1]['data']),4096)
        self.assertIn('https://a.github.io/b/',json.loads(sender.calls[0][1]['data'])['message'])
    def test_secret_not_in_exception(self):
        class Broken:
            def post(self,*a,**kw):raise RuntimeError('secret-is-here')
        d={'mode':'manual','day':'2026-09-22','payload':{'message':'test','title':'test'}}
        with self.assertRaisesRegex(RuntimeError,'연결 실패') as cm:notify.publish(d,'x'*48,datetime(2026,9,22,12,tzinfo=TZ),Broken())
        self.assertNotIn('secret-is-here',str(cm.exception))
