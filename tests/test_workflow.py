import unittest,os
from pathlib import Path
from unittest.mock import patch
from contest_alert.__main__ import urls

class WorkflowTests(unittest.TestCase):
    def test_private_mode_uses_repository_url(self):
        with patch.dict(os.environ,{'GITHUB_REPOSITORY':'owner/repo','ENABLE_PAGES':'false','PAGE_URL':''}):
            self.assertEqual(urls()[1],'https://github.com/owner/repo')
    def test_pages_job_is_separate_from_collector(self):
        text=(Path(__file__).resolve().parents[1]/'.github/workflows/daily.yml').read_text()
        self.assertIn('\n  deploy:\n',text)
        update=text.split('\n  update:\n',1)[1].split('\n  deploy:\n',1)[0]
        self.assertNotIn('environment:',update)
    def test_missing_secret_does_not_prevent_dashboard_refresh(self):
        text=(Path(__file__).resolve().parents[1]/'.github/workflows/daily.yml').read_text()
        reserve=text.split('id: reserve',1)[1].split('      - name:',1)[0]
        self.assertIn('continue-on-error: true',reserve)
    def test_noon_preparation_schedule_and_no_push_trigger(self):
        text=(Path(__file__).resolve().parents[1]/'.github/workflows/daily.yml').read_text()
        self.assertIn("cron: '40 2 * * *'",text)
        self.assertNotIn('\n  push:',text)
