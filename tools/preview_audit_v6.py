"""Replay a selected set of public live observations, not the whole live snapshot.

Title/URL samples: user's public site/data.json observed 2026-09-22.
Schedule text: the directly opened official pages listed in LIVE_AUDIT_V6.md.
Minimal HTML below is a reconstruction; it is not downloaded original markup.
Never writes production data/state.json and never sends notifications.
"""
from pathlib import Path
import sys,copy,shutil,tempfile,argparse,html,json
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from contest_alert import core,quality,render


def make_state():
    now=datetime(2026,9,22,16,18,23,tzinfo=ZoneInfo('Asia/Seoul'))
    sources=[dict(id='dacon',name='DACON',kind='dacon',group='external',url='https://dacon.io/competitions'),
        dict(id='aifactory',name='인공지능팩토리',kind='aifactory',group='external',url='https://aifactory.space/ko/competition'),
        dict(id='campuspick',name='캠퍼스픽 · AI/데이터',kind='campuspick',group='external',url='https://www.campuspick.com/contest'),
        dict(id='aix',name='인공지능융합연구센터',kind='mangboard',group='inha',url='https://aix.inha.ac.kr/news/notice/'),
        dict(id='sw',name='SW중심대학사업단',kind='k2web',group='inha',url='https://swuniv.inha.ac.kr/')]
    cfg={'sources':sources};state=core.empty_state();state['updated_at']=now.isoformat()
    def add(rid,sid,title,url):
        source=next(s for s in sources if s['id']==sid)
        row=dict(id=rid,title=title,listing_title=title,url=url,source_id=sid,source_name=source['name'],group=source['group'],
            deadline=None,registration_start=None,first_seen=now.isoformat(),last_seen=now.isoformat(),last_changed=now.isoformat(),
            relevance_status='included',relevance_evidence=title,relevance_version=5)
        state['items'][rid]=row;state['changes'].append(dict(id=rid,kind='initial',at=now.isoformat()));return row
    for code,title in [('236754','나라장터 자체입찰 공고 법령 위반사항 모니터링 AI 경진대회'),
                       ('236749','딥보이스 범죄 대응을 위한 AI 탐지 모델 경진대회'),
                       ('236753','블랙박스 영상 기반 지능형 고의사고 분석 모델 AI 경진대회')]:
        url=f'https://dacon.io/competitions/official/{code}/overview/'
        row=add('dc'+code,'dacon',title,url)
        event_year='2026' if code=='236754' else '2025'  # Preserve the actual source's inconsistent year.
        raw=f'<body><h1>{html.escape(title)}</h1><p>참가 기간: 2026년 08월 18일(화) 10:00 ~ 2026년 09월 29일(화) 10:00</p><p>대회 기간: 2026년 08월 26일(수) 10:00 ~ {event_year}년 09월 30일(수) 10:00</p><p>팀 병합 마감: 2026년 09월 23일(수) 23:59</p></body>'
        row.update(core.detail_fields(raw,url+'schedule','dacon'));row['detail_checked_at']=now.isoformat();row['detail_status']='ok'
        assert row['deadline']=='2026-09-29' and row['deadline_time']=='10:00'
    for code,title in [('9306','주제 3: 국립공원 내 시설물 변화 탐지'),('9307','주제 4: 해안 쓰레기 탐지 및 규모 추정')]:
        url=f'https://aifactory.space/ko/competitions/{code}';row=add('af'+code,'aifactory',title,url)
        row.update(organizer='측 또는 제3자에게 발생한 손해에 대해 참가자가 책임을 부담합니다.',benefits='지급과 함께 계약을 체결합니다.')
        raw=f'''<body><h1>{html.escape(title)}</h1><p>2026 국립공원 위성 모니터링 AI 챌린지</p><p>총 상금</p><p>600만원</p><p>참가자수</p><p>186</p><h2>소개</h2><p>참가 접수</p><p>2026.07.31 10:00 ~ 2026.10.06 14:00</p><p>팀 병합 기간</p><p>2026.07.31 10:00 ~ 2026.09.29 14:00</p><p>대회 기간</p><p>2026.09.14 10:00 ~ 2026.10.06 14:00</p><h2>평가 방법</h2><p>대회 기간 중에는 Public 점수만 확인할 수 있습니다.</p><p>수상작은 상금 지급과 함께 계약을 체결합니다.</p><p>주최 국립공원공단</p><p>주관 인공지능팩토리</p><p>운영 인공지능팩토리</p><h2>참가 자격</h2><p>14세 이상 대한민국 국민 누구나</p></body>'''
        row.update(core.detail_fields(raw,url,'aifactory'));row['detail_checked_at']=now.isoformat();row['detail_status']='ok'
        assert row['deadline']=='2026-10-06' and row['deadline_time']=='14:00';assert '국립공원공단' in row['organizer']
    add('cp36134','campuspick','2026 KoMaP AI 경진대회','https://www.campuspick.com/contest/view?id=36134').update(detail_status='unconfirmed')
    add('aix108','aix','[교육] 2026-2학기 인공지능융합세미나 개최 안내','https://aix.inha.ac.kr/news/notice/?vid=108')
    add('sw4application','sw','2026 AI-POT 자격증 취득 지원 프로그램(4차) 참여 신청 (9/10~9/16)','https://swuniv.inha.ac.kr/bbs/swuniv/3113/188992/artclView.do')
    for suffix in ('','?layout=unknown'):
        add('sw4result'+str(bool(suffix)),'sw','2026 AI-POT 자격증 취득 지원 프로그램(4차) 참여자 선발 결과 안내','https://swuniv.inha.ac.kr/bbs/swuniv/3113/191810/artclView.do'+suffix)
    add('swinternship','sw','2026 SW·AI 해외 인턴십 프로그램 참여자 모집 (~8. 16. (일) 까지)','https://swuniv.inha.ac.kr/bbs/swuniv/3113/187543/artclView.do')
    state['sources']={s['id']:dict(name=s['name'],url=s['url'],group=s['group'],status='partial',message='선택한 실제 사례의 로컬 재현 · 운영 수집 성공률 아님',checked_at=now.isoformat()) for s in sources}
    quality.apply_policy(state,cfg)
    for sid,report in state['sources'].items():
        own=[x for x in state['items'].values() if x['source_id']==sid]
        keep=[x for x in own if x['relevance_status']=='included' and not x.get('duplicate_of')]
        report.update(retained=len(keep),duplicates_hidden=sum(bool(x.get('duplicate_of')) for x in own),excluded=sum(x['relevance_status']=='excluded' for x in own),
            dates_complete=sum(bool(x.get('deadline') and x.get('registration_start')) for x in keep),dates_partial=sum(bool(x.get('deadline'))!=bool(x.get('registration_start')) for x in keep),dates_missing=sum(not x.get('deadline') and not x.get('registration_start') for x in keep))
    assert state['items']['sw4application']['deadline']=='2026-09-16'
    assert state['items']['swinternship']['deadline']=='2026-08-16'
    return state,now


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    root=Path(__file__).resolve().parents[1];state,now=make_state()
    with tempfile.TemporaryDirectory() as tmp:
        target=Path(tmp);shutil.copytree(root/'web',target/'web')
        render.build(target,state,now,repo_url='https://github.com/uiseokys/inha-contest-alert',demo=True)
        text=(target/'site/index.html').read_text()
        text=text.replace('<strong>디자인 미리보기</strong> 아래 공고·날짜·건수는 모두 가상 데이터이며 실제 모집 공고가 아닙니다.',
            '<strong>운영 사례 수정 미리보기 · 2026-09-22 기준</strong> 공개 사이트에서 선택한 사례와 공식 일정 원문을 재현한 화면입니다. 전체 운영 데이터나 실제 배포 결과가 아니며, 기간이 지난 뒤에는 원문을 확인하세요.')
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text)
    print('Selected live-case replay saved:',args.output)
if __name__=='__main__':main()
