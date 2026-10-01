"""Standard-library-only daily gate: skipped ticks do not install dependencies."""
import argparse,json,os,sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from contest_alert.settings import load,due,KST

def main():
    root=Path(__file__).resolve().parents[1]
    state=json.loads((root/'data/state.json').read_text(encoding='utf-8'))
    now=datetime.now(KST)
    result=due(load(root),state,now)
    if os.getenv('GITHUB_EVENT_NAME')=='workflow_dispatch':result.update(run=True,reason='manual_refresh')
    output=os.getenv('GITHUB_OUTPUT')
    if output:
        with open(output,'a') as f:f.write('run='+str(result['run']).lower()+'\nday='+result['day']+'\n')
    print('수집 실행' if result['run'] else '수집 생략',result['reason'])
if __name__=='__main__':main()
