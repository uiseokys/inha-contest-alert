# Daily Noon Contest Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 무료 독립 일일 알림과 검색 가능한 공고 목록을 제공한다.

**Architecture:** Python 수집기 → 공개 JSON 기록 → README/단일 HTML → 날짜 선점 후 ntfy 예약 전송. GitHub Actions에서 실행하고 Pages artifact로 배포한다.

**Tech Stack:** Python 3.12, requests, BeautifulSoup, optional Playwright, stdlib unittest, HTML/CSS/JS, GitHub Actions, ntfy.

**Spec:** docs/superpowers/specs/2026-09-22-contest-monitor.md

## Global Constraints
- 알림 목표 Asia/Seoul 매일 12:00; 수집 cron UTC 02:40.
- 외부 배포/계정 연결/실제 알림은 이 세션에서 수행하지 않는다.
- 토픽은 Secret만, 공개 데이터는 제목/날짜/링크만.
- 실패를 신규 없음으로 숨기지 않으며 마감 미확인을 모집중으로 단정하지 않는다.

## Review Focus
- 한국시간 날짜 경계와 정오 이전/이후 delay.
- Unicode 메시지 4096바이트 제한 및 예외 로그의 비밀 유출.
- 등록 이후 동일 날짜 수동 재실행 시 중복 전송.
- HTML 구조 변경, robots 거부, 사이트별 부분 실패, 원문 삭제.
- HTML/CSV injection, 마감일 미확인/이미 지난 글의 기본 화면 처리.

### Task 1: parsing and state
- [x] tests/test_core.py에 URL 정규화, 합성 K2web/MangBoard/플랫폼 파서, 명확한 접수기간, 상태 병합 테스트를 먼저 쓴다.
- [x] `python -m unittest discover -s tests -v`에서 기능 부재로 실패를 확인한다.
- [x] contest_alert/core.py, collect.py를 구현한다. 공개 게시판 수집 요청은 GET만; 원문 선택 영역에서 날짜를 추출한다.
- [x] 전체 테스트를 실행하고 커밋한다.

### Task 2: daily notification
- [x] tests/test_notify.py에서 날짜별 선점, 정오 예약, 지연, 오류 은닉, UTF-8 길이, 전송 성공/실패를 검증한다.
- [x] `python -m unittest discover -s tests -v`의 실패 확인 후 notify.py와 CLI를 구현한다.
- [x] GITHUB_OUTPUT은 불리언만; ntfy POST의 응답 본문/토픽은 저장하지 않는다.
- [x] 전체 테스트를 실행하고 커밋한다.

### Task 3: dashboard and packaging
- [x] HTML script escape/README/CSV/필터 및 빈 상태 테스트를 먼저 쓴다.
- [x] web/ 템플릿과 render.py, workflow, SETUP.md를 구현한다.
- [x] 전체 Python 테스트 및 Playwright 모바일/데스크톱 확인, 패키지 비밀 스캔을 수행한다.
- [x] 데모는 합성 데이터 표시를 붙이고 실제 state는 비워서 ZIP으로 제공한다.
