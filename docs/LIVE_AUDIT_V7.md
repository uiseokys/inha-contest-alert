# 공개 운영 데이터 점검 — 2026-09-23

## 이번에 읽은 공개 자료

- 화면: https://uiseokys.github.io/inha-contest-alert/
- 저장된 공개 데이터: https://raw.githubusercontent.com/uiseokys/inha-contest-alert/main/site/data.json
- 해당 데이터의 수집 시각: **2026-09-22 23:54:54 +09:00**
- 확인한 추출 버전: **6**. 이전 답변의 버전 5 관찰보다 최신 상태입니다.

저장된 공개 공고는 18개였고 출처별 지표상 시작/마감 모두 확인 6개, 일부 확인 1개(마감일), 미확인 11개였습니다. 따라서 해당 **기존 v6 저장 결과의 마감일 확인은 7/18**입니다. 새 v7 수집을 실제 GitHub에서 실행해 개선율을 측정한 결과가 아닙니다. 전체 사이트의 공고 누락률도 아닙니다.

| 출처 | 저장 공고 | 시작·마감 모두 | 일부 | 미확인 |
|---|---:|---:|---:|---:|
| 데이터사이언스학과 공지 | 1 | 1 | 0 | 0 |
| 인공지능융합연구센터 | 4 | 1 | 0 | 3 |
| SW중심대학사업단 | 2 | 0 | 1 | 1 |
| DACON | 3 | 3 | 0 | 0 |
| 인공지능팩토리 | 2 | 1 | 0 | 1 |
| 캠퍼스픽 | 6 | 0 | 0 | 6 |

AI-POT 공고의 참가 신청 2026-09-10~09-16과 11월 장학금 신청·환불 문장이 섞이는 사례를 확인했습니다. v7 테스트는 공개 데이터에 남은 추출 문구를 재현해 기간의 용도를 구별합니다. 제작 환경에서 원본 HTML 바이트를 새로 내려받았다고 주장하지 않습니다.

캠퍼스픽 상세는 공개 웹 읽기에서 제목 외에 사용할 수 있는 본문을 얻지 못한 사례가 있었습니다. 확인하지 못한 날짜를 채워 넣지 않았습니다.

## 실제 실행과의 구분

컨테이너에서 직접 Python HTTPS를 시도했지만 외부 DNS 요청이 실패했습니다. 사용자 GitHub에서 v7을 실행·배포하거나 ntfy에 실제 메시지를 보내지 않았습니다. 추가한 `Audit date collection (no notification)`은 적용 후 **GitHub 실행 환경의 실제 요청 결과**를 제한된 범위에서 진단하도록 만든 코드입니다. 그 보고서가 실제로 생성되는지는 첫 원격 실행에서 확인해야 합니다.

## 확인한 기술 문서

- GitHub 공개 workflow runs 조회: https://docs.github.com/en/rest/actions/workflow-runs#list-workflow-runs-for-a-workflow
- 예약 실행 지연·비활성화 조건: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule

위 공개 원문 읽기와 로컬 기능 테스트는 원격 운영 검증의 대체가 아닙니다.
