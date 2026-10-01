# v3 검증 보고서

검증일: 2026-09-22. **수정된 프로젝트의 로컬 검증이며, 실제 사이트 수집·원격 배포·휴대폰 수신 확인서가 아닙니다.**

## 결과
| 항목 | 결과 |
|---|---|
| 제공된 v2 기준 테스트 | 67개 통과 |
| v3 Python 전체 테스트 | **97개 통과, 실패 0개** |
| JavaScript 구문 | `node --check web/app.js` 통과 |
| Python 구문 | `python -m compileall -q contest_alert tools tests` 통과 |
| 기본 검색·필터·CSV | 기존 브라우저 검증 1280px / 390px 통과 |
| 접수·대회기간·자격·주최·링크 | 기존 상세정보 검증 1280px / 390px 통과 |
| 새 디자인·신규 필터·키보드 | 320 / 390 / 768 / 1280 / 1600px 통과 |
| 비교 상태 | 최초 기준 없음 / 이전 날짜 대체 / 전체 실패 / 오래된 기록 검증 통과 |
| 대비 | 선정한 텍스트 역할 4.5:1 이상, 입력 경계 3:1 이상 검사 통과 |
| 데이터 노출 | 공개 payload에 선점 기록·시험용 비밀값·일별 전체 스냅샷 미포함 |
| 변경 범위 | 기존 `config.json`, `data/state.json`, `.github/workflows/daily.yml` 변경 없음 |

실제 출력은 `verification/`에 보관했습니다. Chromium을 이용한 로컬 화면 테스트이며 외부 요청을 차단한 v3 테스트도 포함합니다. 서체 파일은 제공하지 않으며 Pretendard 미설치 시 시스템 폴백으로 그려집니다. 화면 이미지를 직접 확인했습니다.

로컬 Python은 3.13 계열이며, GitHub workflow의 Python 3.12 원격 실행은 수행하지 않았습니다.

## 신규 비교 검증 범위
한국 날짜 경계(UTC 입력 포함), 전날 최종 저장 기록 선택, 당일 재실행, 첫 설치/v2 마이그레이션, 이전 날짜 누락, 새 출처 최초 적재 제외, 이전 실패 출처의 추가 발견 분리, 전체 실패를 0으로 표현하지 않음, 부분 실패 경고, 공고 변경 반복 시 중복 계수 제외, 새 공고와 변경 공고 중복 제외, 마감 항목이 숨겨져도 신규에서 차감하지 않음, 32일 기록 유지, 알림 커서와 비교 수 독립성, 기존 날짜별 중복 전송 억제를 검사했습니다.

collect → snapshot → public summary / digest 연결도 합성 게시판으로 확인했습니다. 전날 관련 공고 0건인 정상 출처에 다음 날 새 공고가 생기는 경우와, 전체 접속 실패 시 기존 목록 보존도 검사했습니다.

## 화면 검증 범위
본문 바로가기, 키보드 포커스 표시, Enter로 상세 열기, ‘접기/펼치기’ 상태 문구, 검색 초기화 후 초점 복귀, 신규 요약 클릭으로 신규만 보기, 마감 신규도 포함하도록 상태 필터 조정, 출처별 신규 수, 원문 화살표의 설명 있는 이름, 모바일 GitHub 링크, 긴 한국어·영문 혼합 제목 줄바꿈, 가로 넘침 없음, 움직임 감소 설정, 빈 결과의 CSV 버튼 비활성화를 확인했습니다.

대형 화면에서는 첫 카드의 접수기간이 첫 화면에 보이는지도 확인했습니다. 예시의 공고·금액·날짜·건수는 **모두 가상 자료**이며 실사용 state에 넣지 않았습니다.

## 검토 방식과 남은 한계
작성자가 별도 단계로 변경 사항과 회귀 테스트를 자체 검토했습니다. 독립 검토자 검토는 아닙니다. 검토 과정에서 접힌/열린 상세 액션 문구, 스크롤된 전체 화면 이미지에서 드러나는 바로가기 링크, 좁은 화면에서 숨겨진 GitHub 이동 링크를 수정했습니다.

실제 CampusPick/인하대/DACON 등의 HTTP 응답, robots 정책, 로그인·접속 차단, 동적 페이지 구조는 이번 작업에서 새로 확인하지 않았습니다. 기존 수집기는 그대로이며 운영 성공률이 검증된 것으로 해석해서는 안 됩니다. 본인 GitHub의 예약 실행·Pages 배포·ntfy 수락·실제 푸시 표시도 수행하지 않았습니다.

일별 숫자는 **발견한 공고 주소** 기준이지 게시일이 확정된 실제 신규 대회 수가 아닙니다. 서로 다른 사이트의 같은 대회를 의미 기반으로 통합하지 않으며, 포스터/PDF/HWP 자동 해석도 범위 밖입니다. 전날 마지막 저장 목록이 기준이므로 전날 저녁 수동 갱신이나 전달 실패가 있었다면 ‘지난 알림 이후 미전달 신규’와 다를 수 있습니다.

WCAG 2.2 AA는 첨부 자료의 목표이며, 이 보고서는 선정된 검사 결과만 설명합니다. 실제 screen reader/다양한 OS/모든 상호작용의 완전한 적합성 인증은 아닙니다. 정오 정각/하루 정확히 한 번의 휴대폰 수신 역시 보장하지 않습니다.

## 재실행
프로젝트 루트에서 다음을 실행합니다. 브라우저 테스트는 **실제 데이터가 아닌 미리보기**를 사용합니다.

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m compileall -q contest_alert tools tests
node --check web/app.js
python -m contest_alert render
python tools/preview_demo.py --output preview.html
python -m playwright install chromium
python tools/check_browser.py preview.html
python tools/check_details_browser.py preview.html
python tools/check_design_browser.py preview.html --screenshots screenshots
```

예시 HTML을 `site/index.html`로 복사하지 마세요. 실사용 페이지는 collect/render가 실제 state에서 생성합니다.

## 배포 파일 추가 확인

전체 ZIP을 새 폴더에 풀어 97개 테스트가 통과했습니다. 업데이트 ZIP을 원본 v2에 적용한 별도 복사본에서도 97개 테스트와 페이지 생성을 확인했습니다. 그 과정에서 임의의 보존 표식을 넣은 기존 state/config/workflow의 바이트가 그대로 유지되었고, 원래 공고가 페이지에 남으며 시험용 비공개 선점 값이 공개 데이터에 노출되지 않음을 확인했습니다. 이 검증은 본인 GitHub에 업로드한 것이 아니라 로컬 복사본에서 수행했습니다.
