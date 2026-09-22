"""Independent, multi-label technical fields from the notice, not the source name."""
from __future__ import annotations
import re
from .quality import NEGATION,ORG
from .core import preferred_title
LABELS={'data_analysis':'데이터 분석','model_development':'AI 모델 개발','service_development':'AI 서비스 개발','creative_ai':'AI 영상·디자인','general_ai':'AI·데이터 일반'}
PATTERNS={
 'data_analysis':r'데이터\s*(?:분석|시각화|마이닝|과학|활용)|공공\s*데이터|빅\s*데이터|통계|data\s*(?:analysis|science|visualization)|수요\s*예측',
 'model_development':r'모델|머신\s*러닝|딥\s*러닝|컴퓨터\s*비전|자연어\s*처리|분류|탐지|예측|세그멘테이션|강화\s*학습|model|machine\s*learning|deep\s*learning|detection',
 'service_development':r'서비스|챗봇|에이전트|에이아이\s*에이전트|(?:AI|인공지능)\s*앱|RAG|agent|chatbot',
 'creative_ai':r'(?:영상|이미지|음악|디자인|콘텐츠|숏폼|영화)\s*(?:제작|창작|생성|공모)|(?:AI|인공지능)\s*(?:영상|디자인|음악|숏폼|영화)\s*(?:공모|콘테스트)|생성형\s*AI\s*(?:영상|디자인|음악)'
}

def technical_fields(item:dict)->list[str]:
    parts=[preferred_title(item),str(item.get('summary') or ''),str(item.get('relevance_evidence') or '')]
    text='\n'.join(ORG.sub('',line) for part in parts for line in part.splitlines() if not NEGATION.search(line))
    tags=[tag for tag,pattern in PATTERNS.items() if re.search(pattern,text,re.I)]
    return tags or ['general_ai']
