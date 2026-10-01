"""Read/render a disposable copy. Never rewrite the checked-out user's state."""
import json,shutil,sys,tempfile
from pathlib import Path
from datetime import datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from contest_alert.__main__ import read_json
from contest_alert.render import build
from contest_alert.settings import KST
root=Path(__file__).resolve().parents[1]
original=(root/'data/state.json').read_bytes()
with tempfile.TemporaryDirectory() as d:
    dest=Path(d);shutil.copytree(root/'web',dest/'web')
    for name in ('server_settings.json','README.md'):
        if (root/name).exists():shutil.copyfile(root/name,dest/name)
    build(dest,json.loads(original),datetime.now(KST),repo_url='https://github.com/example/test')
    html=(dest/'site/index.html').read_text()
    assert '/*__' not in html and '알림 시간' in html
assert original==(root/'data/state.json').read_bytes()
print('기존 상태를 변경하지 않은 화면 생성 검사 통과')
