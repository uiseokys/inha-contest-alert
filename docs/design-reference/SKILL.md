---
name: design-system-
description: Creates implementation-ready design-system guidance with tokens, component behavior, and accessibility standards. Use when creating or updating UI rules, component specifications, or design-system documentation.
---

<!-- TYPEUI_SH_MANAGED_START -->

# 엘리스

## Mission
Deliver implementation-ready design-system guidance for 엘리스 that can be applied consistently across documentation site interfaces.

## Brand
- Product/brand: 엘리스
- URL: https://elice.io/ko?NaPm=ct%3Dm4unadj4%7Cci%3D0zC00010rQbBn0R5Y10J%7Ctr%3Dbrnd%7Chk%3D9a11d64bf9afaab6be3279280a89817144532840%7Cnacn%3DkqaYBcQGrPzl&gad_source=1&gad_campaignid=20380388064&gbraid=0AAAAAoizgMesdYtpnAnMoBv4_R8Dvejom&gclid=CjwKCAjwq8PVBhAKEiwA2i3SHd55VqSHDSkheghhV77QYp5iV3zvgpM1ZV4SKhlYIDeJF1i49vmWpxoCtaAQAvD_BwE
- Audience: developers and technical teams
- Product surface: documentation site

## Style Foundations
- Visual style: structured, accessible, implementation-first
- Main font style: `font.family.primary=Pretendard Variable`, `font.family.stack=Pretendard Variable, Pretendard, -apple-system, system-ui, system-ui, Roboto, Helvetica Neue, Segoe UI, Apple SD Gothic Neo, Noto Sans KR, Malgun Gothic, Apple Color Emoji, Segoe UI Emoji, Segoe UI Symbol, sans-serif`, `font.size.base=16px`, `font.weight.base=500`, `font.lineHeight.base=24px`
- Typography scale: `font.size.xs=12px`, `font.size.sm=13px`, `font.size.md=14px`, `font.size.lg=15px`, `font.size.xl=16px`, `font.size.2xl=18px`, `font.size.3xl=20px`, `font.size.4xl=24px`
- Color palette: `color.text.primary=#191f28`, `color.text.secondary=#212121`, `color.text.tertiary=#ffffff`, `color.text.inverse=#343e4b`, `color.surface.base=#000000`
- Spacing scale: `space.1=4px`, `space.2=5px`, `space.3=7px`, `space.4=8px`, `space.5=10px`, `space.6=11px`, `space.7=12px`, `space.8=15px`
- Radius/shadow/motion tokens: `radius.xs=4px`, `radius.sm=6px`, `radius.md=8px`, `radius.lg=10px`, `radius.xl=50px` | `motion.duration.instant=150ms`, `motion.duration.fast=250ms`, `motion.duration.normal=300ms`

## Accessibility
- Target: WCAG 2.2 AA
- Keyboard-first interactions required.
- Focus-visible rules required.
- Contrast constraints required.

## Writing Tone
concise, confident, implementation-focused

## Rules: Do
- Use semantic tokens, not raw hex values in component guidance.
- Every component must define required states: default, hover, focus-visible, active, disabled, loading, error.
- Responsive behavior and edge-case handling should be specified for every component family.
- Accessibility acceptance criteria must be testable in implementation.

## Rules: Don't
- Do not allow low-contrast text or hidden focus indicators.
- Do not introduce one-off spacing or typography exceptions.
- Do not use ambiguous labels or non-descriptive actions.

## Guideline Authoring Workflow
1. Restate design intent in one sentence.
2. Define foundations and tokens.
3. Define component anatomy, variants, and interactions.
4. Add accessibility acceptance criteria.
5. Add anti-patterns and migration notes.
6. End with QA checklist.

## Required Output Structure
- Context and goals
- Design tokens and foundations
- Component-level rules (anatomy, variants, states, responsive behavior)
- Accessibility requirements and testable acceptance criteria
- Content and tone standards with examples
- Anti-patterns and prohibited implementations
- QA checklist

## Component Rule Expectations
- Include keyboard, pointer, and touch behavior.
- Include spacing and typography token requirements.
- Include long-content, overflow, and empty-state handling.

## Quality Gates
- Every non-negotiable rule must use "must".
- Every recommendation should use "should".
- Every accessibility rule must be testable in implementation.
- Prefer system consistency over local visual exceptions.

<!-- TYPEUI_SH_MANAGED_END -->
