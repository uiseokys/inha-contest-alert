# v2 검증 보고서 — 2026-09-22

**프로젝트 파일의 로컬 테스트 결과입니다. 실제 수집/배포/휴대폰 수신 확인서는 아닙니다.**

## 확인 결과

| 항목 | 결과 |
|---|---|
| 수정 전 기존 Python 전체 테스트 | 39개 통과 |
| 수정 후 전체 Python 테스트 | **67개 통과**, 실패 0개 |
| 테스트 우선 실행 | 신규 17개 중 미구현 14개 실패 확인 후 구현; 연동 4개와 검토 2개 실패를 재현한 뒤 수정 |
| JavaScript 문법 | `node --check web/app.js` 통과 |
| Python 구문 컴파일 | `python -m compileall -q contest_alert tools tests` 통과 |
| 로컬 사이트·README·CSV 생성 | `python -m contest_alert render` 통과 |
| 기존 화면 회귀 확인 | Chromium 1280×1000, 390×844: 각각 10개 확인 항목 통과 |
| v2 상세 화면 확인 | Chromium 1280×1050, 390×844: 각각 16개 확인 항목 통과 |
| 초기 운영 데이터 | items/claims 비어 있음; 가상 예시 미포함 |
| 일정·실행 환경 | 기존 UTC `40 2 * * *`, GitHub-hosted `ubuntu-latest`, ntfy 정오 전달 유지 |

## 새로 검증한 기능

합성 HTML로 캠퍼스픽 `/contest/view?id=숫자` 링크, 제목·카드 AI/데이터 선별, `AI영상` 등 한글 연결 키워드, `Chair` 같은 오탐 제외를 검사했습니다. 접수/행사기간 구분, 한글 날짜, 동일 연도 끝날짜 생략, 여러 차수의 접수기간, 잘못된 날짜를 미확인으로 남기는 동작을 검사했습니다.

명시된 주최·참가 대상·상금/혜택·주제·안내/신청 링크 추출, footer 링크 오인 방지, 위험한 URL 배제, CSV 수식과 HTML 주입 방어를 검사했습니다. 목록만 다시 읽는 날에도 상세정보가 보존되고 참가 대상 변경이 기록되는지 확인했습니다. 출처별 상세 예산 배분, 상세 실패 상태, JavaScript 상세 페이지 렌더링 대체 경로는 **가짜 HTTP 클라이언트**로 검사했습니다.

브라우저에서는 제목·주최기관 검색, 캠퍼스픽 필터, 기간 표시, 상세 펼치기, 날짜와 참가 정보, 안내/신청 버튼의 목적지, 모든 상세 필드를 포함한 CSV 저장, 미확인 항목, 가로 넘침과 JavaScript 오류가 없는지 확인했습니다. 두 화면 크기의 이미지를 직접 검토했습니다. 사용한 공고는 모두 가상 예시입니다.

## 실제 웹 확인과 한계

공개 웹 읽기로 https://www.campuspick.com/contest 의 목록과 게시글 URL 형식, https://www.campuspick.com/robots.txt 를 확인했습니다. AI 관련 공고 링크는 공개 목록에서 확인되었으나 상세 페이지의 본문은 웹 읽기 결과에서 비어 있었습니다.

컨테이너에서 `requests.get`으로 실제 캠퍼스픽 연결을 시도했지만 DNS 이름 확인 오류가 발생했습니다. 따라서 **Python/Chromium 수집기가 현재 실제 캠퍼스픽 DOM에서 정보를 성공적으로 읽는지 검증하지 못했습니다.** 현재 HTML 구조나 접근 정책에 따라 파서 조정이 필요할 수 있습니다. 다른 인하대/AI 플랫폼의 실제 연결 역시 이번 수정에서 종단간 검증하지 않았습니다.

**사용자 GitHub 생성/업로드, Actions 원격 실행, Pages 실제 배포, ntfy 서버 전송과 휴대폰 수신은 수행하지 않았습니다.** 프로그램은 파일로 제공되며 설치가 필요합니다. 공개 페이지의 일부 링크만 확인하며 모든 페이지/더보기/첨부문서를 수집하지 않습니다. 본문에만 AI 키워드가 있는 공고, 포스터/PDF/HWP의 정보는 놓칠 수 있습니다. 최대 30개의 상세 읽기 예산 때문에 정보가 첫날 다 채워지지 않을 수 있습니다.

## 자체 검토에서의 수정

독립 검토자 없이 작성자가 별도 점검했습니다. 날짜 범위의 끝날짜가 잘못됐을 때 시작일을 단일 행사일로 오인하는 문제와 Markdown 링크 안의 제어문자/마크업 문제를 재현하는 테스트를 먼저 작성하고 수정했습니다. 그 뒤 전체 67개 테스트를 재실행했습니다.

선택 사항: 기간을 읽지 못하면 원문 텍스트와 미확인 상태를 우선하며, 원문 전체 복제나 유료 AI/OCR을 추가하지 않았습니다. 같은 대회가 서로 다른 URL에 재게시되면 별도 항목으로 남을 수 있습니다. 미확인 필드가 있는 공고도 페이지에서 보여 주되 자격이나 모집 상태를 보장하지 않습니다.

기존 알림 정책은 그대로입니다. 최대 하루 한 번의 제출 시도를 우선하므로 서비스 장애나 전송 도중 중단 시 그날 누락될 수 있습니다. 정오 정확한 도착, 모든 게시판의 전수 수집, 실제 푸시 표시를 보장하지 않습니다.

## 재검증 명령

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m contest_alert render
node --check web/app.js
python -m playwright install chromium
python tools/preview_demo.py --output preview.html
python tools/check_browser.py preview.html
python tools/check_details_browser.py preview.html
```

`preview.html`은 별도의 가상 예시입니다. 실사용 `site/index.html`로 덮어쓰지 마세요.
