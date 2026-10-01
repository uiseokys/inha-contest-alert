# v8 implementation and verification plan

Goal: implement the six approved improvements plus a web-operated cloud notification time, retaining old state, config, ntfy topic, identity, and comparison histories.

1. Complete-code update archive, hash manifest and early preflight; Python 3.12 and Node CI; render smoke test; do not publish failed code.
2. Bounded PDF-text/HWPX/TXT attachment reading after HTML/official schedule failure. No OCR, auth bypass, unbounded downloads or arbitrary manual URL crawling. Track quality regressions on comparable IDs, not changing denominators.
3. Explicit eligibility evidence and conservative filters. Unknown stays unknown; profile is browser-local.
4. Browser-local application stages, next-task dates, notes, import/export, .ics export. Registration and submission remain separate. No claimed cloud sync.
5. Server-side selected event watchlist and fields, daily digest priority. Opt-in sync publishes only selected IDs, never personal notes or profile.
6. Page forms to create structured GitHub issues for additions/corrections/reports. Only repository owner's own requests execute; other users' requests require a new owner-authored request. No issue-body interpolation into shell, eval, PAT, anonymous writes or arbitrary code.
7. Page time input -> GitHub-authenticated request -> validated server_settings.json -> scheduled cloud tick. Default noon KST. A lightweight 20-minute tick runs the full collector once/day around the selected time. ntfy delay handles minutes. Already-attempted day is not sent twice; changes after queueing apply next day. Free standard public runner; exact time not guaranteed.

Tests: fail new APIs first, then implement; run all old/new Python/Node suites; browser desktop/mobile; archive clean extraction and damaged-v7 repair preserving protected file bytes. No remote changes/real ntfy messages. Self-review for security, midnight, failed uploads, conflicts, private-field leakage.
