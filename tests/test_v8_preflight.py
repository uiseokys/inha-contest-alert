import hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
path=Path(__file__).resolve().parents[1]/'tools/preflight.py'
spec=importlib.util.spec_from_file_location('preflight',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class PreflightTests(unittest.TestCase):
    def setup(self,p):
        (p/'data').mkdir();(p/'data/state.json').write_text('{}');(p/'config.json').write_text('{}')
        (p/'release-manifest.json').write_text(json.dumps({'files':{'quality.py':hashlib.sha256(b'ok').hexdigest()}}))
    def test_missing_file_named(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.setup(p);self.assertIn('누락: quality.py',module.check(p))
    def test_wrong_version(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.setup(p);(p/'quality.py').write_text('wrong');self.assertTrue(any('버전 불일치' in e for e in module.check(p)))
    def test_keeps_state(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.setup(p);before=(p/'data/state.json').read_bytes();module.check(p);self.assertEqual(before,(p/'data/state.json').read_bytes())
    def test_matching_file(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.setup(p);(p/'quality.py').write_bytes(b'ok');self.assertEqual(module.check(p),[])
