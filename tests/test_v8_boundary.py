import copy, importlib.util, io, json, os, tempfile, unittest, zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo
from contest_alert.settings import validate,due
from contest_alert.attachments import bounded_extract
ROOT=Path(__file__).resolve().parents[1]
class BoundaryTests(unittest.TestCase):
    def test_settings_change_after_reservation_does_not_repeat(self):
        from contest_alert.core import empty_state
        s=empty_state();s['claims']['2026-10-01']={'status':'reserved','target_at':'2026-10-01T12:00:00+09:00'}
        now=datetime(2026,10,1,21,1,tzinfo=ZoneInfo('Asia/Seoul'))
        self.assertFalse(due(validate({'notification':{'time':'21:00'}}),s,now)['run'])
    def test_actual_bounded_hwpx_worker(self):
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w') as z:
            z.writestr('Contents/section0.xml','<r><p>접수기간: 2026.10.01 ~ 2026.10.31</p></r>')
        result=bounded_extract(buf.getvalue(),'hwpx')
        self.assertEqual(result['status'],'ok');self.assertIn('2026.10.31',result['text'])
    def test_actual_bounded_text_worker(self):
        result=bounded_extract('신청 마감: 2026.10.31 18:00'.encode(),'txt')
        self.assertEqual(result['status'],'ok')

    def test_text_pdf_extraction(self):
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
        writer=PdfWriter();page=writer.add_blank_page(width=400,height=400)
        page[NameObject('/Resources')]=DictionaryObject({
            NameObject('/Font'):DictionaryObject({NameObject('/F1'):DictionaryObject({
                NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),
                NameObject('/BaseFont'):NameObject('/Helvetica')})})})
        stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 20 360 Td (Deadline 2026-10-31 18:00) Tj ET')
        page[NameObject('/Contents')]=writer._add_object(stream)
        b=io.BytesIO();writer.write(b)
        result=bounded_extract(b.getvalue(),'pdf')
        self.assertEqual(result['status'],'ok');self.assertIn('2026-10-31 18:00',result['text'])
    def _invoke(self,actor,issuer):
        spec=importlib.util.spec_from_file_location('page_handler',ROOT/'tools/handle_request.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);(r/'tools').mkdir();(r/'data').mkdir()
            state={'items':{},'claims':{'2026-10-01':{'status':'accepted','marker':'KEEP'}}}
            (r/'data/state.json').write_text(json.dumps(state));before=(r/'data/state.json').read_bytes()
            body='<!-- CONTEST_REQUEST_V8 -->\n```json\n'+json.dumps({'version':1,'kind':'settings','payload':{'notification':{'time':'20:13'}}})+'\n```'
            event={'repository':{'full_name':'owner/repo','owner':{'login':'owner'}},'issue':{'number':1,'body':body,'user':{'login':issuer}}}
            (r/'event.json').write_text(json.dumps(event));env={'GITHUB_EVENT_PATH':str(r/'event.json'),'GITHUB_ACTOR':actor,'GITHUB_EVENT_NAME':'issues','GITHUB_OUTPUT':str(r/'output.txt'),'GITHUB_STEP_SUMMARY':str(r/'summary.txt')}
            with patch.object(m,'__file__',str(r/'tools/handle_request.py')),patch.dict(os.environ,env):
                m.main()
            self.assertEqual(before,(r/'data/state.json').read_bytes())
            return json.loads((r/'server_settings.json').read_text()) if (r/'server_settings.json').exists() else None
    def test_public_visitor_cannot_change_settings(self):self.assertIsNone(self._invoke('visitor','visitor'))
    def test_owner_cannot_autoapprove_forged_other_user_issue(self):self.assertIsNone(self._invoke('owner','visitor'))
    def test_owner_issue_updates_time_but_not_state(self):
        data=self._invoke('owner','owner');self.assertEqual(data['notification']['time'],'20:13');self.assertEqual(data['revision'],'issue-1')
if __name__=='__main__':unittest.main()
