import hashlib,importlib.util,json,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ReleaseTests(unittest.TestCase):
    def builder(self):
        p=ROOT/'tools/build_release.py';self.assertTrue(p.is_file(),'cumulative release builder is missing')
        spec=importlib.util.spec_from_file_location('release_builder',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    def fixture(self,r):
        for rel,body in {'contest_alert/quality.py':'unchanged quality','contest_alert/extraction.py':'unchanged extraction','web/app.js':'app','tests/test_one.py':'test','tools/preflight.py':'check','.github/workflows/daily.yml':'workflow','requirements.txt':'dep','config.json':'userconfig','data/state.json':'state','overrides.json':'private','server_settings.json':'settings','intake.json':'manual','README.md':'custom','site/index.html':'oldsite'}.items():
            p=r/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body)
    def test_cumulative_manifest_includes_unchanged_dependencies(self):
        m=self.builder()
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);self.fixture(r);manifest=m.make_manifest(r)
            self.assertIn('contest_alert/quality.py',manifest['files']);self.assertIn('contest_alert/extraction.py',manifest['files'])
            self.assertNotIn('data/state.json',manifest['files'])
    def test_update_excludes_all_user_data_including_new_settings(self):
        m=self.builder()
        with tempfile.TemporaryDirectory() as td:
            r=Path(td)/'repo';r.mkdir();self.fixture(r);m.make_manifest(r)
            out=Path(td)/'update.zip';m.bundle(r,out,update=True)
            with zipfile.ZipFile(out) as z:
                names={n.removeprefix('inha-contest-alert/') for n in z.namelist()}
                self.assertIn('contest_alert/extraction.py',names)
                for path in ('data/state.json','config.json','README.md','overrides.json','server_settings.json','intake.json','site/index.html'):self.assertNotIn(path,names)
                self.assertIn('release-manifest.json',names);self.assertIn('.github/workflows/daily.yml',names)
if __name__=='__main__':unittest.main()
