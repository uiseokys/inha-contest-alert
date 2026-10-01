# Build log

Scope: independent downloadable project, not a deployed service.
Ruling: public repository default for free GitHub Pages; private repository can use README-only mode.
Ruling: collect 20 minutes before noon and use ntfy scheduled delivery, improving punctuality without a long-running job.
Ruling: preserve date claims before sending; at-most-one attempt per day prioritizes no duplicate over retry after uncertain network failures.
Ruling: no external account connection because this is a shared ChatGPT account.
Pre-flight: parser records feed state, state feeds renderer and notification summary; all dates are ISO strings, all scheduling timezone aware.

Task 1 complete: 19 local fixture tests passed; live DNS unavailable.

Task 2 complete: 29 local tests passed, including notification protocol stubs; no real push sent.

Final review: self-review (no independent reviewer). Fixed participant-counter false changes, missing-secret coupling, and free private README mode via separate Pages job. Regression tests RED→GREEN; suite 39/39.

Task 3 complete: full suite 39/39; JavaScript syntax and Python compilation pass; desktop/mobile Chromium checks pass. Live deployment state intentionally empty.
Ruling: file:// navigation blocked by browser policy; smoke test uses set_content with the standalone HTML — validates UI behavior but not real host/network/deployment.
Final: minor (deferred): cross-board semantic deduplication and attachment-only deadlines; original-source review required.
Final verification: Python 3.13.5 locally; workflow targets Python 3.12, remote execution unverified. No external requests sent to ntfy.

## v2 — 2026-09-22

- 별도 로컬 사본/브랜치에 제공된 v1 ZIP을 가져와 기존 39개 테스트를 확인.
- 캠퍼스픽·기간·참가 정보·기록 보존에 관한 실패 테스트를 확인한 뒤 파서/수집기/출력을 수정.
- 데스크톱·모바일 상세 화면 시험에서 기존 화면에 접수기간이 없음을 확인 후 구현.
- 자체 검토로 잘못된 행사 종료일과 URL 마크업 입력 문제를 회귀 테스트로 고침.
- 최종 Python 67개 통과, 두 화면 크기의 기존/새 UI 확인 통과. 외부 수집/배포/푸시는 미검증.
- 선택: 명시된 공개 필드만 짧게 저장, 불명확한 날짜 추측 금지. 상세 예산 출처별 순환. 기존 클라우드/정오 일정 유지.

## v3 — 2026-09-22
- 첨부 SKILL.md / DESIGN.md 기반 토큰과 추가 역할을 DESIGN_APPLICATION.md에 분리 기록.
- 캘린더 날짜별 비교 로직, 기준 없는 날·실패·누락·신규 출처 분리 및 기존 알림 커서 유지.
- 초기 비교 테스트 18개 실패 → 구현 후 통과. 디자인 구조 검사 6개 실패 → 적용 후 통과.
- 키보드 focus-visible과 마우스 programmatic focus를 혼동한 검사, 제목뿐 아니라 주제까지 검색되어 2건이 나온 시험 쿼리는 실제 UI 동작에 맞게 수정함.
- 자체 검토 후 상세 액션 문구, 숨긴 바로가기의 클리핑, 모바일 GitHub 링크, 첫 카드 기간의 화면 내 배치를 회귀 검증함.
- 최종 Python 테스트 97개 및 5개 폭의 새 UI 검사 통과. 이전 상세·검색 검사도 그대로 통과.
- 실제 원격 배포나 ntfy 메시지 발송 없음. 기존 수집기의 실사이트 연결은 새로 검증하지 않음.

## v4 — 날짜·제목·정렬

별도 기능 브랜치에서 제공된 v3 기준 97개를 확인한 뒤 사용자 요구에 맞는 날짜·표시·정렬 회귀 테스트를 먼저 추가했다. 원인: 참가 기간 라벨/축약 날짜의 미인식, 부분 정보가 있으면 JS 보완을 생략, 실제 일정 URL이 개요로 정규화됨, 제목에 목록 카드의 카운터 혼입. 해결 후 총 129개를 확인했다.

자체 검토에서 데이콘 보조 타임라인 혼동, 해결된 날짜 추정 문구 잔존, 역전된 JSON-LD 기간을 재현하는 테스트가 먼저 실패하는 것을 확인한 뒤 수정했다. 본문에 참가기간이 있는 경우 그것을 기준으로 하며 행사·제출·시상식 날짜로 신청기간을 채우지 않는다. 이 검토는 독립 리뷰가 아니다.

화면 검증에서 기본 마감 여유순/미확인 하단/제목 2줄/전체 제목·근거 공개/모바일 오버플로를 검사했다. 기존 검색 및 키보드 회귀 검사도 통과했다. 가상 자료는 별도 preview에만 사용하며, 생성된 배포용 site는 빈 원래 state로 다시 렌더했다. 실제 운영 데이터나 외부 GitHub 계정을 수정하지 않았다.
