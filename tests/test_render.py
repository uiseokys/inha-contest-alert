import unittest,json
from datetime import datetime
from zoneinfo import ZoneInfo
from contest_alert import core,render
NOW=datetime(2026,9,22,11,40,tzinfo=ZoneInfo('Asia/Seoul'))
class RenderTests(unittest.TestCase):
    def state(self):
        s=core.empty_state();s['updated_at']=NOW.isoformat()
        s['items']['x']={'id':'x','title':'</script><script>alert(1)</script>','url':'https://example.com/a',
         'source_id':'a','source_name':'학과','group':'inha','deadline':None,'posted_at':None,
         'first_seen':NOW.isoformat(),'last_seen':NOW.isoformat(),'last_changed':NOW.isoformat()}
        s['claims']['2026-09-22']={'status':'reserved','private_test':'SECRET_VALUE'}
        return s
    def test_public_payload_has_no_claims(self):
        d=render.public_data(self.state(),NOW)
        self.assertNotIn('claims',d);self.assertNotIn('SECRET_VALUE',json.dumps(d))
    def test_script_breakout_escaped(self):
        text=render.embedded_json(render.public_data(self.state(),NOW))
        self.assertNotIn('</script>',text);self.assertIn('\\u003c',text)
    def test_csv_formula_injection_neutralized(self):
        self.assertEqual(render.csv_cell('=HYPERLINK("bad")'),'\'=HYPERLINK("bad")')
        self.assertEqual(render.csv_cell('AI 대회'),'AI 대회')
    def test_unknown_deadline_remains_unknown(self):
        d=render.public_data(self.state(),NOW)
        self.assertEqual(d['items'][0]['status'],'unknown')
    def test_readme_html_is_escaped(self):
        md=render.markdown_table(render.public_data(self.state(),NOW))
        self.assertNotIn('<script>',md);self.assertIn('마감 미확인',md)
