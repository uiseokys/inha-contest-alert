import importlib.util,unittest,copy
from test_v7_events import item,NOW
from contest_alert.core import empty_state
from contest_alert.render import public_data

class TaxonomyTests(unittest.TestCase):
    def tags(self,**fields):
        self.assertIsNotNone(importlib.util.find_spec('contest_alert.taxonomy'),'independent subject filter missing')
        from contest_alert.taxonomy import technical_fields
        return technical_fields(fields)
    def test_model_and_data_tags(self):
        tags=self.tags(title='공공데이터 분석 및 예측 AI 모델 개발 경진대회')
        self.assertIn('data_analysis',tags);self.assertIn('model_development',tags)
    def test_vision_detection_is_not_creative_video(self):
        tags=self.tags(title='블랙박스 영상 기반 고의사고 AI 탐지 모델 경진대회')
        self.assertIn('model_development',tags);self.assertNotIn('creative_ai',tags)
    def test_video_creation_has_own_category(self):
        self.assertIn('creative_ai',self.tags(title='생성형 AI 영상 제작 공모전'))
    def test_service_and_retrieval(self):
        self.assertIn('service_development',self.tags(title='LLM RAG 기반 챗봇 서비스 해커톤'))
    def test_ai_department_not_a_technical_field(self):
        self.assertEqual(self.tags(title='사진 공모전',organizer='인공지능공학과'),['general_ai'])
    def test_education_kind_does_not_prevent_field_tags(self):
        self.assertIn('data_analysis',self.tags(title='데이터 시각화 교육 프로그램'))
    def test_negation_line_does_not_count_creative(self):
        self.assertNotIn('creative_ai',self.tags(title='공공데이터 분석',summary='AI 영상 제작 금지'))
    def test_public_has_fields_and_pending_separate_not_counted(self):
        s=empty_state();s['quality_policy_version']=6;s['items']={'a':item('a'),'p':item('p',title='지역 문제해결 공모전',relevance_status='pending',relevance_reason='원문 확인 대기',private='SECRET')}
        s['sources']={};data=public_data(s,NOW)
        self.assertIn('technical_fields',data['events'][0]);self.assertEqual(len(data['events']),1)
        self.assertEqual(len(data.get('review_items',[])),1)
        self.assertNotIn('private',data['review_items'][0]);self.assertEqual(data['review_items'][0]['id'],'p')
