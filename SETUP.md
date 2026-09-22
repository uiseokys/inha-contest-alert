# 처음 설정하기 — v2 캠퍼스픽·상세정보 포함

## 먼저 알아둘 것

이 파일은 **배포 가능한 초기 프로젝트**입니다. 이 채팅에서 개인 GitHub 저장소를 생성하거나 ntfy로 실제 알림을 발송하지 않았습니다. 본인 계정에서 아래 설정을 해야 실행됩니다. 이 ChatGPT는 공용 계정이므로 토픽·로그인 정보·인증 토큰을 대화에 올리지 마세요.

기본 구성은 **공개 GitHub 저장소 + 무료 GitHub Pages + 표준 GitHub Actions + ntfy 무료 서버**입니다. 대회 제목/날짜/링크는 공개됩니다. 비공개 연구자료와 개인정보는 넣지 않습니다. 비공개 저장소만 사용하려면 맨 아래 대안을 따르세요.

## 컴퓨터를 꺼도 실행되나요?

**본인 GitHub에 설치하고 Actions를 활성화했다면 실행됩니다.** `daily.yml`은 `runs-on: ubuntu-latest`인 GitHub-hosted runner를 사용합니다. 본인 PC, ChatGPT 앱, 브라우저 창은 계속 켜두지 않아도 됩니다. 파일을 다운로드만 했거나 PC에서 Python을 직접 실행한 상태는 클라우드 배포가 아닙니다. 정적 목록은 GitHub Pages가 제공하고 휴대폰은 ntfy 알림을 받는 역할입니다.

이미 v1을 사용 중이면 먼저 [UPGRADE.md](UPGRADE.md)를 읽으세요. **기존 `data/state.json`을 빈 파일로 덮어쓰면 안 됩니다.**

## 1. 본인 GitHub에 파일 올리기

1. 본인 GitHub에서 새 저장소를 만듭니다. 예시 이름은 `inha-contest-alert`입니다. 기본 브랜치는 `main`, 공개 범위는 **Public**으로 설정합니다. 이 프로젝트가 그 저장소의 루트에 들어가야 합니다.
2. ZIP 압축을 풀고 **안쪽 폴더의 내용물**을 업로드합니다. 파일 전체를 ZIP 그대로 올리면 실행되지 않습니다. `README.md`, `config.json`, `requirements.txt`, `contest_alert/`, `web/`, `data/`, `site/`, `tests/`, `.github/`가 저장소 첫 화면에 있어야 합니다.
3. **숨김 폴더 `.github`도 반드시 업로드합니다.** macOS Finder에서는 `Command + Shift + .`로 숨김 파일을 표시할 수 있습니다. 웹 업로드에서 이 폴더가 빠졌다면 GitHub의 **Add file → Create new file**에서 이름을 `.github/workflows/daily.yml`로 입력하고, 압축 안의 같은 파일 내용을 붙여 넣어 저장하세요.
4. 저장소의 **Actions** 탭에서 `Daily contest dashboard`가 보이는지 확인합니다. 아직 목록이 비어 있는 것은 정상입니다.

Git을 사용한다면 새 저장소 URL로 다음처럼 업로드할 수도 있습니다. 아래 `YOUR_ID`는 본인 아이디로 바꿉니다. 이 방법은 본인 컴퓨터에서만 한 번 수행하면 됩니다.

```bash
cd inha-contest-alert
git init -b main
git add .
git commit -m "Initial contest monitor"
git remote add origin https://github.com/YOUR_ID/inha-contest-alert.git
git push -u origin main
```

## 2. 무료 목록 페이지 켜기

저장소 **Settings → Pages → Build and deployment → Source**를 **GitHub Actions**로 바꾸고 저장합니다. **Deploy from a branch가 아닙니다.** 이 프로젝트는 공식 Pages 배포 action을 직접 실행합니다.

페이지 주소는 기본적으로 다음 형태입니다.

```text
https://YOUR_ID.github.io/inha-contest-alert/
```

별도 도메인을 구매할 필요가 없습니다. 다른 저장소명을 써도 주소는 자동 계산됩니다. 별도 주소를 사용한다면 **Settings → Secrets and variables → Actions → Variables**에 `PAGE_URL`을 등록합니다. 이 값은 공개 웹페이지 주소이며 비밀값이 아닙니다.

## 3. 개인 ntfy 토픽 준비

휴대폰에 ntfy 앱을 설치하고 알림 권한을 허용합니다. 서버는 `https://ntfy.sh`를 사용합니다. Android/iOS 각각 앱의 기능과 OS 알림·배터리 설정에 따라 실제 수신에 차이가 있을 수 있습니다.

본인 컴퓨터의 Python에서 아래 명령으로 무작위 토픽을 만듭니다.

```bash
python -c "import secrets; print(secrets.token_hex(24))"
```

출력된 **48자리 문자열**을 본인만 보관합니다. 이 프로젝트는 32~64자의 영문/숫자/밑줄/하이픈 토픽을 요구합니다. `inha`, `ai-contest`처럼 추측하기 쉬운 이름은 쓰지 않습니다.

휴대폰 ntfy 앱의 **토픽 구독 / Subscribe to topic**에서 같은 문자열을 입력합니다. 서버 `https://ntfy.sh`와 토픽 문자열은 서로 다른 입력값입니다. 같은 토픽을 구독한 모든 기기는 같은 알림을 받습니다.

**무료 익명 토픽은 계정 권한으로 보호된 비공개 채팅방이 아닙니다.** 토픽을 아는 사람은 읽거나 게시할 수 있습니다. 공개 공고 요약만 보내세요. 토픽이 유출되면 새 문자열로 교체하고 앱의 이전 구독을 지우세요.

## 4. 토픽을 GitHub Secret에 저장

**Settings → Secrets and variables → Actions → Secrets → New repository secret**를 엽니다.

```text
Name:   NTFY_TOPIC
Secret: 위에서 만든 48자리 문자열
```

앱에서 구독한 문자열과 정확히 같아야 합니다. 주소 전체가 아니라 **토픽 문자열만** 넣습니다. `config.json`, README, HTML, 공개 Variables에는 넣지 마세요. 별도의 ntfy 유료 계정·API 키·OpenAI API 키는 필요하지 않습니다.

## 5. 첫 실행으로 목록과 수집 상태 확인

**Actions → Daily contest dashboard → Run workflow**를 누릅니다.

첫 실행은 `send_today`를 **체크하지 않고** 진행하세요. 기존 공고를 기준 목록에 적재하고 페이지를 만들지만 ntfy 알림은 보내지 않습니다. 한꺼번에 오래된 공고가 새 공고로 전송되는 것을 피합니다.

실행이 끝나면 저장소 README와 Pages 주소를 확인합니다. 특히 페이지 하단 **출처별 수집 상태**를 확인하세요. **Actions 전체가 초록색이어도 일부 출처의 수집은 실패할 수 있습니다.** 실패한 사이트를 '공고가 없음'으로 처리하지 않고 화면에 남기도록 설계했습니다.

휴대폰 시험 알림이 필요하면 다시 Run workflow를 열고 `send_today`를 체크합니다. **즉시 일일 요약을 1회** 보내며, 같은 한국 날짜의 정오 알림을 이미 시도했으면 재발송하지 않습니다. 시험 발송도 그날의 1회에 포함됩니다. 다른 날에는 다시 시험할 수 있습니다.

정상 여부는 세 단계로 구분합니다.

- 소스의 `정상`: 설정 범위 내 게시글 링크를 수집했다는 뜻입니다. 모든 공고를 빠짐없이 수집했다는 뜻은 아닙니다.
- Actions의 `ntfy가 메시지를 수락`: ntfy 서버의 HTTP 수락을 확인했다는 뜻입니다. 휴대폰 표시 성공과는 다릅니다.
- 실제 휴대폰 수신: 본인이 앱에서 확인해야 합니다.

## 6. 이후 매일 작동하는 방식

**11:40 KST**에 GitHub Actions가 수집을 시작합니다. UTC cron은 `40 2 * * *`입니다. 수집이 끝나면 README와 페이지를 갱신하고, ntfy 서버에 **같은 날 12:00 KST에 전달할 메시지**를 맡깁니다. Python이 정오까지 계속 켜져서 기다리는 구조가 아닙니다.

11:40 전에 공고가 게시됐더라도 해당 사이트의 반영 지연/수집 범위 밖/접속 실패 등으로 다음 번에 발견될 수 있습니다. 11:40 이후 게시물은 다음 수집 때 보게 됩니다. 목록을 다시 확인하고 싶을 때는 Run workflow를 `send_today` 미체크로 실행합니다. **페이지 방문만으로 수집이 새로 실행되지는 않습니다.**

GitHub 작업이 늦어 정오가 지나면 지연 표시와 함께 완료 후 발송합니다. GitHub 예약 실행이나 ntfy, 휴대폰의 네트워크·알림 설정은 엄격한 정시·수신 보장을 제공하지 않습니다. 무료 범위에서 정오 목표를 구현한 것입니다.

알림에는 신규 발견 수, 내용 변경 수, 7일 이내 확인된 마감일, 수집 실패 여부, 전체 목록 링크가 담깁니다. 신규가 없는 날도 작동 확인용으로 1건을 보냅니다. 오류를 추가 푸시로 따로 쏟아내지 않고 같은 메시지에 묶습니다. GitHub 계정의 워크플로 실패 이메일은 GitHub 자체 알림 설정의 별도 기능입니다.

## 중복 방지와 장애 복구 원칙

`data/state.json`에 공고 ID, 마지막 확인 시각, 알림 날짜별 시도 기록을 보관합니다. 알림 전송 전에 해당 날짜를 선점한 기록을 GitHub에 먼저 저장합니다. 저장 실패 시 메시지를 보내지 않습니다. 같은 날짜에 수동 실행하거나 재실행해도 중복 시도를 막습니다.

대신 **선점 기록 저장 후 작업이 중단되거나, ntfy 요청이 실패하면 그날 알림이 누락될 수 있습니다.** HTTP 시간초과는 실제 접수 여부가 불명확하므로 자동 재시도하지 않습니다. 날짜별 ‘정확히 1회 수신’을 보장하는 시스템은 아닙니다. 기본 정책은 **중복 방지를 우선하는 하루 최대 한 번의 제출 시도**입니다. 전송 실패 시 다음 날 요약은 성공적으로 전달 요청한 이후의 변화를 다시 포함합니다.

`data/state.json`을 임의로 지우면 기준 목록과 중복 방지 기록을 잃습니다. 손상 시 자동 초기화하지 않고 중단합니다. 필요하면 GitHub의 이전 커밋에서 파일을 복원하세요. ntfy 토픽은 상태 파일에 저장하지 않습니다.

## 수집 범위를 바꾸는 곳

`config.json`에 출처별 URL과 종류가 들어 있습니다. 초기 설정은 인하대 데이터사이언스학과/인공지능공학과/AIX/SW사업단/대학 홈페이지, DACON, 인공지능팩토리, **캠퍼스픽 AI·데이터 공모전**입니다. **초기 URL 설정이 실제 수집 성공을 보장하지 않습니다.** 일부 학과 사이트는 제작 시 공개 웹에서도 접근 오류가 있었습니다.

- `max_pages_per_source: 2`: 공개 링크로 이어진 게시판·페이지를 최대 두 페이지 확인합니다. 대규모 전체 기록 수집기가 아닙니다. JavaScript 버튼으로만 숨겨진 페이지네이션·더보기는 누르지 않습니다.
- `lookback_days: 120`: 처음 발견한 글 중 게시일이 확인되면 최근 120일을 기준 목록으로 삼습니다. 게시일을 모르면 오래된 글을 완벽히 거를 수 없습니다.
- `max_detail_requests: 30`: 상세 페이지 읽기 예산을 출처별로 번갈아 배분합니다. 일부 사이트가 전체 예산을 차지하지 않도록 했습니다. 한 번에 30개까지이며, 확인한 공고는 기본적으로 3일 이후 다시 읽습니다. 새 공고가 많으면 모든 상세정보가 첫날 채워지지 않습니다. 목록 밖으로 밀려난 최근 공고와 최근 7일 이내 마감 공고도 예산 안에서 재확인합니다.
- `browser_fallback: true`: HTML에 링크가 없으면 공개 페이지를 Chromium으로 렌더링합니다. 로그인·CAPTCHA·403 차단을 우회하지 않습니다.
- `mode: contest`: 대회 관련 표현을 기준으로 선별합니다. `ai_contest`는 AI/데이터 표현도 필요합니다. `platform`은 AI 대회 전용 플랫폼용입니다. 캠퍼스픽의 `ai_platform`은 공개 공모전 제목·카드의 AI/데이터/통계 등 키워드를 확인합니다. `AI영상`처럼 붙여 쓴 표현도 지원합니다. AI 영상·디자인 공모전도 포함되며, 관련 키워드가 본문에만 있는 공고는 놓칠 수 있습니다.
- `enabled: false`: 해당 출처의 자동 수집을 멈추고 직접 확인 링크만 남깁니다.

기관 홈페이지 첫 화면에서 찾을 수 있는 공지 링크는 일부만 따라갑니다. 필요한 게시판이 빠진다면 **해당 게시판의 실제 주소를 직접 `url`에 넣는 것이 더 확실**합니다. 공모전 전용 사이트를 추가할 때는 실제 링크 구조에 맞는 `kind` 또는 `link_pattern`도 검증해야 합니다. 아무 사이트 주소나 추가한다고 모두 지원되는 것은 아닙니다.

원문 전체/첨부파일/사진은 공개 저장하지 않습니다. 제목·링크·날짜와 명시된 주최/주관·참가 대상·상금/혜택·주제의 **짧은 공개 텍스트**를 보관합니다. 내용은 AI로 작성한 요약이나 자격 판정이 아니라 라벨 기반 추출입니다.

웹페이지 목록에서 접수기간을 바로 보고, **‘일정·참가 정보 펼치기’**를 누르면 대회기간·주최기관·참가 대상·혜택·주제·상세 일정·원문/안내 사이트/신청 링크를 확인할 수 있습니다. 주최기관·참가 대상으로도 검색되며, GitHub README 표와 CSV에도 기간과 정보가 포함됩니다. 연결 주소는 공고에 적힌 주소를 표시하는 것으로, 신청 사이트의 현재 유효성까지 별도로 검증한 것은 아닙니다.

접수기간과 실제 대회기간은 서로 구분합니다. 접수 날짜는 ‘접수기간/신청기간/모집기간’ 등의 명시적 문맥과 연도 포함 날짜가 있어야 합니다. 같은 연도가 분명한 `2026.09.01 ~ 09.30`은 지원하되, 연도를 새로 추측하지 않습니다. 원문에 적힌 `18:00` 같은 시각은 별도 원문 표기에 보존하고, D-day 계산은 날짜 단위입니다. 여러 트랙·차수의 접수기간은 하나로 합치지 않으며 **미확인**으로 표시합니다.

사진/PDF/HWP에만 있는 정보, 인식하지 못한 라벨/동적 페이지는 빈칸을 추측해서 채우지 않습니다. 상세 확인 실패 시 이전 정보가 남을 수 있으며 그 상태와 마지막 확인일을 표시합니다. 모든 필드가 항상 채워진다는 의미는 아닙니다.

캠퍼스픽은 공개 `/contest` 목록과 `/contest/view?id=...` 링크를 대상으로 합니다. 목록 HTML이 비어 있으면 기존 Chromium 렌더링을 시도하고 상세 HTML이 비어 있어도 한 번 렌더링합니다. 로그인·CAPTCHA·403·robots 제한을 우회하거나 비공개 API를 쓰지 않습니다. **실제 사이트의 현재 구조에 따라 파서 조정이 필요할 수 있습니다.**

## 문제가 생겼을 때

| 증상 | 확인할 부분 |
|---|---|
| Actions에 작업이 없음 | `.github/workflows/daily.yml`이 저장소 루트 기준 올바른 경로에 있는지 확인 |
| push / permission denied | Settings → Actions → General → Workflow permissions에서 정책을 확인. 기본 브랜치 보호 규칙이 봇의 직접 커밋을 막으면 이 단순 구조는 동작하지 않음 |
| Pages 404 / 배포 실패 | Public 저장소인지, Settings → Pages의 Source가 GitHub Actions인지 확인. 개인 GitHub Free의 private 저장소는 Pages 기본안을 지원하지 않음 |
| 특정 출처 0건·수집 실패 | 하단 메시지, 원문 접근, 실제 게시판 주소/HTML, robots.txt 확인. 차단이면 우회하지 말고 직접 확인 |
| ntfy 429 | 무료 서비스 이용량/IP 기반 제한 가능. 실패로 기록하며 재시도 폭주하지 않음 |
| ntfy 수락됐지만 휴대폰에 없음 | 앱 서버/토픽 일치, OS 알림 권한·집중 모드·배터리 제한·인터넷 연결 확인 |
| 같은 날 재실행해도 알림 없음 | 날짜별 시도 기록이 있으면 정상적으로 생략됨. 수동 시험도 그날 1회에 포함 |
| 페이지가 오래 갱신되지 않음 | Actions의 최근 실행과 활성화 상태 확인. 공개 저장소는 60일간 저장소 활동이 없으면 예약 실행이 비활성화될 수 있음. 이 프로젝트는 정상 실행 때 수집 시각을 실제 커밋하지만 장기 중단 시 직접 확인 필요 |

## 완전히 비공개로 쓰는 대안

GitHub Free에서 비공개 저장소만 사용하려면 웹 Pages 대신 **로그인 후 README 표로 확인**하는 방식으로 바꿉니다. Repository Variables에 `ENABLE_PAGES=false`를 추가하고 `PAGE_URL`을 본인 저장소 주소로 설정합니다. Pages 작업은 생략됩니다. 알림의 링크도 저장소로 열리며 로그인 권한이 필요합니다.

비공개 저장소는 계정의 무료 Actions 실행시간/저장공간 한도를 공유합니다. 공개 저장소의 표준 runner 실행은 현재 무료입니다. 유료 larger runner나 유료 API를 이 프로젝트는 쓰지 않습니다. 결제수단 없는 무료 계정은 할당량 초과 시 사용이 차단되는 방식입니다. 이 프로젝트가 다른 저장소의 사용량/청구 설정까지 통제하지는 않습니다.

## 검증 결과와 한계

오프라인 합성 HTML 파싱, 출처 부분 실패, URL 정규화, 마감 날짜 추출, 신규/변경 기록, 정오 시간 계산, 날짜별 중복 억제, ntfy HTTP 요청 구성, 공개 HTML/CSV 안전성, 실제 Chromium 화면 동작을 테스트합니다. `docs/TEST_REPORT.md`에 최종 실행 결과가 있습니다.

v2 제작 환경에서도 외부 DNS 요청이 실패해 Python 수집기의 실제 사이트 접속, GitHub에서의 워크플로 실행과 Pages 배포, 휴대폰 수신을 종단간 검증하지 못했습니다. 공개 웹 도구로 캠퍼스픽 목록과 게시글 URL 형식을 확인했지만, 상세 페이지 본문은 읽기 결과에 노출되지 않았습니다. 합성 HTML 테스트 통과를 실제 캠퍼스픽 수집 성공으로 해석하면 안 됩니다. **예시 화면의 가상 데이터는 실사용 상태 파일에 넣지 않았습니다.**

## 근거 문서 — 2026-09-22 확인

공식 문서의 조건은 바뀔 수 있으므로 설정 시 다시 확인하세요.

- GitHub Pages 무료/공개 저장소: https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages
- 표준 Actions 무료 실행 및 private 할당량: https://docs.github.com/en/billing/concepts/product-billing/github-actions
- 예약 실행의 UTC·지연·60일 비활성화: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
- Pages 공식 배포 workflow: https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- GitHub Secrets: https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets
- ntfy 예약 전달·JSON 전송·무료 제한: https://docs.ntfy.sh/publish/
- ntfy 무료 토픽 보안·가용성: https://docs.ntfy.sh/faq/
- ntfy 휴대폰 구독: https://docs.ntfy.sh/subscribe/phone/

- 캠퍼스픽 공개 목록: https://www.campuspick.com/contest
- 캠퍼스픽 robots 정책: https://www.campuspick.com/robots.txt
- GitHub-hosted runner: https://docs.github.com/en/actions/concepts/runners/github-hosted-runners

## v3 화면과 어제 대비 신규 건수

화면은 첨부 디자인 지침을 기반으로 수정했습니다. `docs/DESIGN_APPLICATION.md`에서 기준과 추가 역할 토큰을 구분해 설명합니다. Pretendard 우선 글꼴 스택을 사용하지만 서체 파일은 포함하지 않아 해당 폰트가 없으면 시스템 폰트를 사용합니다.

첫 실행/첫 v3 실행은 기존 목록을 비교 기준으로만 저장하고, 다음 날부터 **어제 마지막 저장 목록 대비 새로 확인한 공고 주소 수**를 표시합니다. 같은 날 수동 갱신은 어제의 기준을 지우지 않습니다. 실제 게시일·고유한 대회 수와는 다를 수 있습니다. 전날 누락/수집 실패/새 출처 적재는 별도로 표시합니다.

알림의 ‘어제 대비 신규’와 페이지 상단 신규 카드는 같은 함수를 사용합니다. 해당 카드를 누르면 신규 공고 목록이 열립니다. ‘지난 알림 이후 미전달 신규’는 전달 누락을 줄이기 위한 별도 통계라 두 수가 다를 수 있습니다. 자세한 기준과 기존 기록 보존 절차는 `UPGRADE.md`를 읽으세요.
