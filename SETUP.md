# v8 처음 설치

기존 사용자는 **UPGRADE.md**와 업데이트 ZIP을 사용합니다. 전체 ZIP의 `data/state.json`은 새 설치용 빈 파일입니다.

1. 본인 GitHub에서 Public 저장소를 만들고 전체 ZIP 안 `inha-contest-alert`의 **내용물**을 루트에 업로드합니다. `.github/`, `release-manifest.json`을 빠뜨리지 않습니다.
2. 저장소 Settings → Pages → Source를 **GitHub Actions**로 설정합니다.
3. 본인 기기에서 `python -c "import secrets; print(secrets.token_hex(24))"`로 ntfy 토픽을 만들고 ntfy 앱에서 서버 `https://ntfy.sh`와 그 토픽을 구독합니다. 토픽은 공개 채팅/코드/페이지/이슈에 입력하지 않습니다.
4. Settings → Secrets and variables → Actions → **Secrets**에 `NTFY_TOPIC`으로 같은 문자열을 저장합니다.
5. Settings → General → Features의 **Issues**를 활성화합니다. 페이지 시간 변경과 공고 요청은 GitHub 인증된 이슈를 사용합니다.
6. Verify release 확인 후 Actions → Daily contest dashboard → Run workflow, `send_today` 미체크로 처음 수집·배포합니다.
7. 정상 페이지 주소는 `https://YOUR_ID.github.io/REPOSITORY/`입니다. 수집 상태도 확인합니다.
8. 기본 알림은 한국시간12:00입니다. 페이지에서 시간 선택 → GitHub에서 시간 적용 → Owner 로그인 후 Create/Submit issue → Apply page request 성공 → 페이지 새로고침 순서로 변경합니다.
9. 휴대폰 시험 발송은 Daily contest dashboard의 send_today를 켜서 실행합니다. 해당 날짜의 1회 시도에 포함됩니다.

상세 업데이트·시간 설정·권한/비용/제약은 **UPGRADE.md**를 읽으세요.
계속 컴퓨터를 켜두는 프로그램이 아니며, GitHub에서 실행합니다. 실제 배포·휴대폰 수신은 본인 계정에서 확인해야 합니다.
