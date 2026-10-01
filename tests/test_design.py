"""The uploaded design's tokens and interaction requirements are contractual."""
from pathlib import Path
import re
import unittest
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]

class DesignTests(unittest.TestCase):
    def test_reference_font_scale_and_monochrome_tokens(self):
        css=(ROOT/'web/style.css').read_text()
        for token in ['--font-family-primary', 'Pretendard Variable', '--font-size-base: 16px',
                      '--font-weight-base: 500', '--font-line-height-base: 24px',
                      '--color-text-primary: #191f28', '--color-surface-base: #000000',
                      '--radius-lg: 10px', '--motion-normal: 300ms']:
            self.assertIn(token,css)
    def test_raw_hex_only_in_token_definitions(self):
        css=(ROOT/'web/style.css').read_text();body=css.split('/* COMPONENTS */')
        self.assertEqual(len(body),2)
        self.assertFalse(re.search(r'#[0-9a-fA-F]{3,8}\b',body[1]))
    def test_skip_link_and_landmarks(self):
        soup=BeautifulSoup((ROOT/'web/index.template.html').read_text(),'html.parser')
        self.assertIsNotNone(soup.select_one('a.skip-link[href="#mainContent"]'))
        self.assertEqual(soup.select_one('main')['id'],'mainContent')
        self.assertIsNotNone(soup.select_one('nav[aria-label]'))
    def test_daily_comparison_and_clear_filters_have_real_elements(self):
        soup=BeautifulSoup((ROOT/'web/index.template.html').read_text(),'html.parser')
        for key in ['comparisonTitle','comparisonNote','comparisonRange','dailySourceCounts','newCountLabel','resetFilters']:
            self.assertIsNotNone(soup.find(id=key),key)
    def test_reduced_motion_and_focus_visible_preserved(self):
        css=(ROOT/'web/style.css').read_text()
        self.assertIn('prefers-reduced-motion: reduce',css)
        self.assertIn(':focus-visible',css)
        self.assertIn(':disabled',css)
    def test_loading_and_no_javascript_states_exist(self):
        soup=BeautifulSoup((ROOT/'web/index.template.html').read_text(),'html.parser')
        self.assertIsNotNone(soup.select_one('#loading[role="status"]'))
        self.assertIsNotNone(soup.find('noscript'))

class ContrastTests(unittest.TestCase):
    """Selected text and control pairs; not a full WCAG conformance audit."""
    def ratio(self,a,b):
        def luminance(h):
            vals=[int(h[i:i+2],16)/255 for i in (1,3,5)]
            linear=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in vals]
            return sum(x*w for x,w in zip(linear,[.2126,.7152,.0722]))
        la,lb=sorted([luminance(a),luminance(b)])
        return (lb+.05)/(la+.05)
    def token(self,name):
        css=(ROOT/'web/style.css').read_text()
        match=re.search(re.escape(name)+r':\s*(#[0-9a-fA-F]{6});',css)
        self.assertIsNotNone(match,name);return match.group(1)
    def test_primary_and_muted_text_reach_4_5(self):
        for fg in ['--color-text-primary','--color-text-secondary','--color-text-inverse','--color-text-muted']:
            for bg in ['--color-text-tertiary','--color-surface-canvas','--color-surface-subtle']:
                self.assertGreaterEqual(self.ratio(self.token(fg),self.token(bg)),4.5,(fg,bg))
    def test_dark_panel_foregrounds_reach_4_5(self):
        for fg in ['--color-text-tertiary','--color-text-on-dark-muted']:
            self.assertGreaterEqual(self.ratio(self.token(fg),self.token('--color-surface-base')),4.5)
    def test_enabled_form_control_boundary_reaches_3(self):
        for bg in ['--color-text-tertiary','--color-surface-canvas']:
            self.assertGreaterEqual(self.ratio(self.token('--color-border-control'),self.token(bg)),3)
