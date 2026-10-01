# v8 검증 보고서 — 누적 복구 · 6가지 기능 · 서버 알림 시각

검증일: 2026-10-01. **로컬 코드/브라우저/ZIP 검증이며 원격 배포·ntfy 수신 성공 확인서가 아닙니다.**

## 실제 결과

| 검사 | 결과 |
|---|---|
| Python 전체 테스트 | **311개 통과, 실패 0** |
| JavaScript/Node 전체 테스트 | **42개 통과, 실패 0** |
| Python 컴파일·새/기존 JS 구문 | 통과 |
| 누적 배포 manifest·모든 모듈 import | 통과 |
| 저장된 state를 바꾸지 않는 렌더 smoke | 통과 |
| 기존 화면/검색/필터/관심/정렬/날짜 변경 | Chromium 320/390/768/1440px 통과 |
| 새 시간 요청·참가 조건·진행/메모/할 일·ICS·신고·직접 추가 | Chromium 390/1440px 통과 |
| 실제 UI가 만든 8개 요청 본문 → 백엔드 검증 | 통과. 외부 이슈 제출 0회 |
| PDF/HWPX/TXT의 별도 제한 프로세스 추출 | 로컬 생성 텍스트 문서로 통과 |
| 소유자/타인/타인이 작성한 이슈 재실행 권한 검사 | 검증된 소유자만 설정 저장, 상태 파일 보존 |
| full ZIP 독립 해제 | 311 Python + 42 Node + preflight/import/render 통과 |
| 불완전한 v7에 update ZIP 적용 | 누락 모듈 오류 재현 → 복구 후 311 Python + 42 Node 통과 |
| 보존 검사 | state/config/README/overrides/server_settings/intake 6개 파일 적용 직후 바이트 동일 |
| 비공개 시험 발송 표식 | 공개 HTML/JSON에 포함되지 않음 |
| 폰트/바이트코드/사용자 상태가 업데이트 ZIP에 섞이지 않음 | 통과 |

## 복구 실험

제공된 전체 v7을 별도 폴더에 풀고 extraction.py와 quality.py를 실제로 제거했습니다.
`import contest_alert.details`에서 누락 오류가 발생함을 확인한 뒤, 새 누적 업데이트 ZIP을 그 위에 풀었습니다.
두 파일과 모든 모듈이 복구되었고 전체 테스트를 다시 실행했습니다.
기존 가상 공고 ID, 날짜별 accepted 기록, 전일 snapshot을 갖는 state 바이트를 보호했습니다.
기존 사용자 시간 15:14도 보존되어 새 공개 페이지에 반영되는 것을 검사했습니다.
시험 자료는 배포물에 포함하지 않았으며, 실사용 저장소의 state는 수정하지 않았습니다.

## 검토 중 수정한 문제

- 수동 공고를 화면에 추가한 것만으로 마지막 실제 수집 시각이 갱신되지 않도록 했습니다.
- 신청 마감이 지난 날에도 남은 결과물 제출 일정은 관심 브리핑에 유지하되, 이미 지난 시각은 제외합니다.
- 부분 알림 설정 요청이 기존 enabled 값을 초기화하지 않도록 했습니다.
- 원문 근거 없는 참가 조건은 모두 '확인 필요'로 남기고, 제외 문구가 있는 자격은 보수적으로 처리합니다.
- 개인 메모/할 일/프로필은 서버 관심 동기화 요청에 포함되지 않습니다.
- 파일 누락/코드 혼합은 manifest에서 막고 알림 전송 전에 상태 저장 성공을 확인합니다.
- 자체 화면 검사에서 새 영역의 색상도 기존 의미별 CSS 변수로 통일했습니다.

독립 검토자 없이 작성자가 별도 코드/화면 검토를 했습니다.

## 환경 및 중요한 한계

로컬: Python 3.13, requests2.32.5, beautifulsoup4 4.14.3, Playwright1.57.0, Node22, 시스템 Chromium.
**로컬에서 사용 가능한 pypdf는5.9.0이고, 배포 requirements는 공식 배포6.19.0으로 고정했습니다.**
6.19.0 문서와 PyPI 배포는 확인했으나 이 도구에서 wheel 다운로드가 허용되지 않아 그 버전을 설치한 로컬 재검사는 하지 못했습니다.
GitHub 목표 Python3.12 및 requirements 전체의 정확한 조합 검사는 업로드 후 **Verify complete release**가 수행해야 합니다.
pypdf 의존성을 포함한 실제 원격 설치가 실패하면 배포 전 검사가 중단됩니다.

개발 Python 시작 시 제공 환경의 artifact_tool 스프레드시트 초기화 오류가 stderr에 함께 찍혔습니다.
프로젝트는 artifact_tool을 사용하지 않으며 요구사항에도 없습니다. 해당 출력과 별개로 표의 테스트 종료 코드는 모두0이었습니다.
원본 로그에는 이 환경 메시지도 숨기지 않고 남겼습니다.

브라우저는 HTML set_content + Storage 호환 대체 저장소로 검사했고 외부 URL 요청을 차단했습니다.
저장 차단 대응과 새 문서의 상태 복원은 검사했으나 실제 GitHub Pages origin의 저장 지속성/네트워크는 검증하지 않았습니다.
GitHub 이슈 화면은 URL/JSON 생성과 소유자 처리기를 별도로 연결해 검사했으며 실제 GitHub 로그인·이슈 제출·커밋·Pages 배포는 수행하지 않았습니다.
ntfy 실제 메시지/휴대폰 표시도 확인하지 않았습니다. 기존 일일 예약 정확성이나 사이트별 수집 확인율 향상을 수치로 주장하지 않습니다.

## 범위 제한

- 설정 시각/관심은 저장소의 공통 ntfy 채널 단위. 개인 방문자별 계정/채널/OAuth 서버는 추가하지 않았습니다.
- 페이지→GitHub에서 요청 제출 확인이 필요합니다. 클릭만으로 서버 저장 완료라고 표시하지 않습니다.
- 이미 예약/시도한 날의 시간 변경/알림 끄기는 그 메시지를 취소하지 않습니다.
- 직접 추가는 검증한 공개 내용을 입력하는 수동 카드이며 임의 사이트 범용 자동 파서가 아닙니다.
- 신고는 검토 항목입니다. 관련 없음/중복을 자동 삭제하거나 자동 병합하지 않습니다.
- 텍스트 첨부는 동일 호스트의 명시적 .pdf/.hwpx/.txt 링크에 한정. 구형HWP/스캔/OCR/CDN/중계주소 미지원.
- 브라우저 진행 상태와 개인 메모는 로컬이며 자동 다중 기기 동기화 없음. ICS는 일회성 파일, 변경 자동 동기화 아님.
- 시간 검사 job은 약20분 간격, 실제 수집은 보통 하루1회. 공개 저장소 전제이며 비공개는 사용량 한도에 주의.

## 재검사 명령

```bash
python -m pip install -r requirements.txt
python tools/preflight.py --imports
python -m unittest discover -s tests -v
node --test tests/*.test.cjs
python tools/smoke.py
python tools/preview_v8.py --output preview-v8.html
python tools/check_v8_browser.py preview-v8.html --screenshots screenshots
python tools/check_features_v8.py preview-v8.html --screenshots screenshots
```

브라우저 검사 도구는 로컬 개발용 Chromium이 있어야 하며 운영 사이트를 위해 사용자 PC를 켜두라는 뜻이 아닙니다.
배포 ZIP에는 가상 공고·토픽·개인 백업 파일이 없습니다.
