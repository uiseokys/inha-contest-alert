"""Non-destructive v5 source and subject policy.

State keeps every known ID and daily notification claim. Only confirmed relevant
records enter the public dashboard and digest. Main Inha root is disabled by
default; official department and AIX boards are not disabled.
"""
from __future__ import annotations
import copy,re
from urllib.parse import urlsplit

VERSION=5
AI_TOPIC=re.compile(r'인공\s*지능|빅\s*데이터|공공\s*데이터|데이터\s*(?:분석|활용|과학|사이언스|마이닝|시각화|셋|톤)|데이터|통계|머신\s*러닝|기계\s*학습|딥\s*러닝|자연어\s*처리|컴퓨터\s*비전|강화\s*학습|생성형\s*(?:모델|AI)|(?<![a-z0-9])(?:AI|AIOT|LLM|RAG|ML|data|machine learning|deep learning)(?![a-z0-9])',re.I)
ORG=re.compile(r'(?:인하대학교\s*)?(?:인공지능(?:융합)?(?:연구센터|공학과|융합센터|대학원|전공)|데이터사이언스학과|데이터과학과)|(?:AI|데이터)\s*(?:연구소|연구센터|학과|학부)',re.I)
NEGATION=re.compile(r'(?:AI|인공지능|생성형).{0,60}(?:불가|불허|금지|제외|인정하지|허용하지)|(?:금지|제외).{0,20}(?:AI|인공지능)',re.I)
NOT_OPPORTUNITY=re.compile(r'수상\s*(?:소식|결과|실적)|수상자\s*발표|수상팀\s*발표|입상\s*소식|수강신청|정규\s*수업|대학원.*신입생|입학\s*전형|채용\s*공고|교수\s*초빙',re.I)


def effective_config(config:dict)->dict:
    """Runtime defaults apply to existing users without overwriting config.json."""
    cfg=copy.deepcopy(config)
    for source in cfg['sources']:
        host=urlsplit(source['url']).hostname
        if source['id']=='inha' and host in ('www.inha.ac.kr','inha.ac.kr') and not cfg.get('enable_main_inha',False):
            source['enabled']=False
            source['disabled_reason']='인하대 대표 홈페이지: 자동 수집 대상에서 제외했습니다. 학과·센터 게시판은 계속 수집합니다.'
        if cfg.get('strict_ai_data',True):
            source['mode']=('ai_platform' if source.get('kind')=='campuspick' else
                            'candidate_platform' if source.get('kind') in ('dacon','aifactory') else 'candidate')
    return cfg


def _evidence(text:str)->str:
    for line in re.split(r'[\n\r]|(?<=[.!?])\s+',text):
        line=re.sub(r'\s+',' ',line).strip()
        if not line or NEGATION.search(line):continue
        # Merely naming an AI department, data privacy, or a prohibited tool is
        # not evidence that this opportunity is about AI/data.
        line=ORG.sub('',line)
        if re.search(r'^(?:주최|주관|문의|참가\s*대상|참여\s*대상|지원\s*대상|대상|개인정보|저작권)',line):continue
        if re.search(r'개인\s*데이터|데이터\s*(?:보관|삭제|수집\s*동의)',line) and not re.search(r'분석|모델|활용',line):continue
        match=AI_TOPIC.search(line)
        if match:
            start=max(0,match.start()-45)
            return line[start:start+160]
    return ''


def classify(item:dict)->dict:
    from .core import preferred_title
    title=preferred_title(item)
    if not title:return dict(relevance_status='pending',relevance_reason='게시글 제목 복구 대기',relevance_evidence='',relevance_version=VERSION)
    if NOT_OPPORTUNITY.search(title):return dict(relevance_status='excluded',relevance_reason='모집·참여 공고가 아닌 학사/채용/결과 공지',relevance_evidence='',relevance_version=VERSION)
    evidence=_evidence(title) or _evidence(item.get('summary') or '') or _evidence(item.get('_topic_text') or '')
    if not evidence and '_topic_text' not in item and item.get('relevance_version')==VERSION and item.get('relevance_status')=='included':
        evidence=item.get('relevance_evidence') or ''
    if evidence:return dict(relevance_status='included',relevance_reason='공고 자체의 AI·데이터 주제 확인',relevance_evidence=evidence,relevance_version=VERSION)
    checked=bool(item.get('_topic_text') or item.get('detail_checked_at'))
    return dict(relevance_status='excluded' if checked else 'pending',relevance_reason='공고 자체에서 AI·데이터 관련 근거를 찾지 못함' if checked else 'AI·데이터 관련성 확인 대기',relevance_evidence='',relevance_version=VERSION)


def apply_policy(state:dict,config:dict)->None:
    from .core import generic_title,preferred_title
    disabled={s['id'] for s in config['sources'] if not s.get('enabled',True)}
    strict=config.get('strict_ai_data',True)
    for item in state['items'].values():
        if generic_title(item.get('detail_title','')):item.pop('detail_title',None)
        if title:=preferred_title(item):item['title']=title
        if item['source_id'] in disabled:
            item.update(relevance_status='excluded',relevance_reason='수집에서 제외한 출처',relevance_evidence='',relevance_version=VERSION)
        elif strict:item.update(classify(item))
        else:item.update(relevance_status='included',relevance_reason='사용자 설정: 분야 제한 해제',relevance_version=VERSION)
        item.pop('_topic_text',None)
    state['quality_policy_version']=VERSION


def visible_state(state:dict)->dict:
    if not state.get('quality_policy_version'):return state
    items={rid:item for rid,item in state.get('items',{}).items() if item.get('relevance_status')=='included'}
    return dict(state,items=items)
