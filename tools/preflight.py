"""Check uploaded release completeness before importing the application."""
from __future__ import annotations
import argparse,hashlib,importlib,json,sys
from pathlib import Path

def check(root:Path,imports:bool=False)->list[str]:
    issues=[];path=root/'release-manifest.json'
    if not path.is_file():return ['release-manifest.json 누락: v8 업데이트 내용물 전체를 다시 올리세요.']
    try:data=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):return ['release-manifest.json 형식 오류']
    for rel,expected in data.get('files',{}).items():
        p=Path(rel)
        if p.is_absolute() or '..' in p.parts:return ['배포 목록에 허용되지 않은 경로']
        target=root/p
        if not target.is_file():issues.append('누락: '+rel)
        elif hashlib.sha256(target.read_bytes()).hexdigest()!=expected:issues.append('버전 불일치/수정됨: '+rel)
    for rel in ('config.json','data/state.json'):
        p=root/rel
        if not p.is_file():issues.append('사용자 파일 누락: '+rel+' (기존 데이터를 복원하세요. 빈 파일로 초기화하지 마세요.)')
        else:
            try:json.loads(p.read_text(encoding='utf-8'))
            except (ValueError,OSError):issues.append('JSON 읽기 오류: '+rel)
    if not issues and imports:
        sys.path.insert(0,str(root))
        for p in sorted((root/'contest_alert').glob('*.py')):
            try:importlib.import_module('contest_alert.'+p.stem)
            except Exception as e:issues.append(f'실행 모듈 검사 실패: {p.name} ({type(e).__name__})')
    return issues

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--imports',action='store_true');a=p.parse_args()
    errors=check(a.root,a.imports)
    if errors:
        print('업데이트 파일/설정 검사 실패. 공고·알림 기록은 변경하지 않았습니다.')
        print('\n'.join('- '+e for e in errors));print('이전 버전에 의존하지 않는 v8 업데이트 전체를 같은 경로에 올린 후 새 실행을 시작하세요.')
        return 2
    print('필수 파일·코드 버전 검사 통과. 데이터·설정은 변경하지 않았습니다.');return 0
if __name__=='__main__':sys.exit(main())
