# v6 실제 운영 데이터 점검 및 수정 범위

2026-09-22 확인 대상: https://uiseokys.github.io/inha-contest-alert/ 및 공개 GitHub main의 site/data.json, data/state.json, web/app.js, contest_alert/render.py, .github/workflows/daily.yml.

운영 자료에서 확인한 원인: K2web layout 쿼리만 다른 동일 게시글 중복, 선발 결과·장학금 제출 같은 사후 행정 공지 혼입, 일정 탭으로 이동하지 못한 DACON, 인공지능팩토리의 '참가 접수' 라벨 누락, 본문 속 '주최 측'과 '상금 지급'을 필드로 잘못 해석, 일부 공고의 상세조회 대기와 단순 추출 실패 혼동.

수정 범위: 표준 게시글 정체성으로 중복 숨김(기존 ID/claims/비교기록 보존), 모집과 사후 안내 구별, 날짜·주최·주제의 문맥 추출, 같은 DACON 대회의 검증된 공개 일정 경로, 제목의 명시적 신청 기간 활용, 브라우저 렌더링 대기 및 상세 확인 원인 표시. 기존 디자인 토큰과 정오 일정·마감 여유순 유지.

검증 방식: 실제 운영 JSON에서 필요한 필드만 전사한 사례, 직접 연 공개 원문의 날짜를 바탕으로 구성한 최소 HTML 재현 사례, 기존 전체 테스트, 로컬 Chromium. 원본 HTML 바이트를 다운로드한 것으로 간주하지 않으며, 픽스처의 HTML 구조는 재현용이다. 컨테이너 외부 DNS가 실패하여 원격 Python 크롤링·GitHub 쓰기·실제 Pages 배포·ntfy 전송은 수행하지 않는다.

추가 일정 근거:
- https://dacon.io/competitions/official/236754/overview/schedule
- https://dacon.io/competitions/official/236749/overview/schedule
- https://dacon.io/competitions/official/236753/overview/schedule
- https://aifactory.space/ko/competitions/9306
- https://aifactory.space/ko/competitions/9307

주의: 딥보이스/블랙박스 대회의 대회기간 종료연도는 원문에 2025로 표기되어 역전된다. 참가기간은 2026으로 확인되나 대회기간을 임의로 정정하지 않는다. 캠퍼스픽 상세는 웹 읽기에서 제목 외 본문을 얻지 못했으므로 마감 복구를 확약하지 않는다. 페이지의 JavaScript 실행 전 정적 문구 '0건'은 실제 데이터 0건의 근거로 사용하지 않는다.
