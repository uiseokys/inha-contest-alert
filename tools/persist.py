"""Commit only known state/public files. Never force-push or reset user records."""
import os,re,subprocess,sys
from pathlib import Path
def main():
    root=Path(__file__).resolve().parents[1];os.chdir(root)
    branch=os.getenv('DEFAULT_BRANCH','main')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_./-]*',branch) or '..' in branch:raise ValueError('브랜치 이름 형식 오류')
    def git(*args):return subprocess.run(['git',*args],check=True)
    git('config','user.name','github-actions[bot]')
    git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    paths=[p for p in ('data/state.json','server_settings.json','intake.json','overrides.json','README.md','site') if (root/p).exists()]
    if not paths:return
    git('add','--',*paths)
    if subprocess.run(['git','diff','--cached','--quiet']).returncode==0:return
    git('commit','-m','Update contest data and validated server preferences')
    # Concurrent owner changes cause a visible conflict, not a destructive reset.
    git('pull','--rebase','origin',branch)
    git('push','origin','HEAD:'+branch)
if __name__=='__main__':main()
