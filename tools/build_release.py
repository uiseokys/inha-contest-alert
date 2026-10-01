"""Build cumulative code updates. Never infer the file set from a git diff."""
from __future__ import annotations
import argparse,hashlib,json,zipfile
from pathlib import Path
CODE_DIRS={'contest_alert','web','tools','tests','.github'}
USER_FILES={'config.json','README.md','overrides.json','server_settings.json','intake.json'}
EXCLUDE_DIRS={'.git','.runtime','__pycache__','.venv','node_modules','.superpowers','verification'}
FONT_EXT={'.ttf','.otf','.woff','.woff2','.ttc'}
def allowed(p:Path,root:Path)->bool:
    rel=p.relative_to(root)
    return p.is_file() and not p.is_symlink() and not any(x in EXCLUDE_DIRS for x in rel.parts) and p.suffix.lower() not in FONT_EXT|{'.pyc','.pyo','.zip'} and not p.name.startswith('.DS_Store')
def make_manifest(root:Path)->dict:
    files={}
    for p in sorted(root.rglob('*')):
        if allowed(p,root):
            rel=p.relative_to(root)
            if rel.parts[0] in CODE_DIRS or str(rel)=='requirements.txt':
                files[rel.as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    data={'version':'8.0.0','files':files}
    (root/'release-manifest.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return data
def bundle(root:Path,out:Path,*,update:bool)->None:
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(root.rglob('*')):
            if not allowed(p,root):continue
            rel=p.relative_to(root)
            if update and (rel.parts[0] in {'data','site'} or rel.as_posix() in USER_FILES):continue
            if rel.parts[0] not in CODE_DIRS|{'docs','data','site'} and len(rel.parts)>1:continue
            z.write(p,'inha-contest-alert/'+rel.as_posix())
    with zipfile.ZipFile(out) as z:
        bad=z.testzip()
        if bad:raise ValueError('ZIP CRC failure: '+bad)
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--output-dir',type=Path,default=Path.cwd())
    p.add_argument('--manifest-only',action='store_true')
    a=p.parse_args();m=make_manifest(a.root)
    print('Manifest files:',len(m['files']))
    if not a.manifest_only:
        for update in (True,False):
            out=a.output_dir/('inha-contest-alert-v8'+('-update' if update else '')+'.zip')
            bundle(a.root,out,update=update);print(out)
if __name__=='__main__':main()
