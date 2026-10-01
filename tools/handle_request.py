"""Apply only an authenticated repository owner's structured request."""
import json,os,sys
from pathlib import Path
from datetime import datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from contest_alert.intake import authorized,parse_request,apply_request
from contest_alert.settings import KST

def main():
    root=Path(__file__).resolve().parents[1]
    event=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'))
    repo=event.get('repository',{});owner=repo.get('owner',{}).get('login','')
    actor=os.getenv('GITHUB_ACTOR','');issue=event.get('issue')
    if not authorized(actor,owner):
        print('저장소 소유자 검토가 필요한 요청입니다. 서버 설정을 변경하지 않았습니다.');return
    if os.getenv('GITHUB_EVENT_NAME')=='workflow_dispatch':
        n=os.getenv('REQUEST_NUMBER','')
        if not n.isdigit():raise ValueError('이슈 번호는 양의 정수여야 합니다.')
        import requests
        r=requests.get(f"https://api.github.com/repos/{repo['full_name']}/issues/{int(n)}",
            headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json'},timeout=15)
        r.raise_for_status();issue=r.json()
    if not issue or issue.get('pull_request') or not authorized(issue.get('user',{}).get('login',''),owner):
        print('소유자 본인이 작성한 이슈만 자동 적용합니다. 타인의 제안은 검토 후 본인 요청으로 재제출하세요.');return
    request=parse_request(issue.get('body',''))
    if not request:print('일반 이슈: 자동 변경 없음');return
    result=apply_request(root,request,int(issue['number']),datetime.now(KST))
    print('요청 처리 결과:',result['status'])
    out=os.getenv('GITHUB_OUTPUT')
    if out:
        with open(out,'a') as f:f.write('ready='+str(result['status'] in ('applied','already_applied')).lower()+'\n')
    summary=os.getenv('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary,'a') as f:
            f.write('## 페이지 설정 요청\n결과: '+result['status']+'\n\n이슈 #'+str(issue['number'])+'\n\n당일 알림을 이미 예약/시도했다면 변경 시간은 다음 날부터 적용됩니다. 토픽은 변경하지 않았습니다.\n')
if __name__=='__main__':
    try:main()
    except Exception as e:
        print('요청 처리 중단: '+type(e).__name__+' · 형식·권한·원문 근거를 확인하세요. 요청 본문은 로그에 출력하지 않습니다.',file=sys.stderr)
        sys.exit(2)
