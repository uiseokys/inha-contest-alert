"""Persist daily observation snapshots and compare calendar dates in Asia/Seoul.

Counts refer to first-observed public notice URLs, not publication dates or
semantically deduplicated competitions. Notification acceptance is independent.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

KST = ZoneInfo('Asia/Seoul')


def _time(value: str | None) -> datetime | None:
    try:
        dt = datetime.fromisoformat(value or '')
        return dt.astimezone(KST) if dt.tzinfo is not None else None
    except (TypeError, ValueError):
        return None


def capture_snapshot(state: dict, now: datetime) -> None:
    """Replace only today's snapshot, keeping yesterday's last observation.

This additive migration never deletes or rebuilds old item IDs, claims, sources,
notification cursors or configuration. A failed collection is recorded as such.
"""
    if now.tzinfo is None:
        raise ValueError('일별 기록에는 시간대가 있는 시각이 필요합니다.')
    local = now.astimezone(KST)
    history = state.setdefault('daily_snapshots', {})
    history[local.date().isoformat()] = {
        'at': local.isoformat(),
        'ids': sorted(state.get('items', {})),
        'initialized_sources': sorted(state.get('initialized_sources', [])),
        'source_statuses': {sid: report.get('status', 'pending')
                            for sid, report in state.get('sources', {}).items()},
    }
    oldest = (local.date() - timedelta(days=31)).isoformat()
    state['daily_snapshots'] = {day: snap for day, snap in history.items()
                               if oldest <= day <= local.date().isoformat()}


def compare_day(state: dict, now: datetime) -> dict:
    """Compare yesterday's last snapshot with the latest observation.

A missing day gets an explicitly dated fallback. First-time imports and sources
without a complete previous observation are separated, not presented as new.
The returned object is safe for the public dashboard (no claims or secrets).
"""
    from .quality import visible_state
    state = visible_state(state)
    local = now.astimezone(KST)
    day = local.date().isoformat()
    yesterday = (local.date() - timedelta(days=1)).isoformat()
    observed = _time(state.get('updated_at'))
    result = {
        'status': 'baseline', 'date': day,
        'as_of': observed.isoformat() if observed else None,
        'base_date': None, 'base_at': None,
        'new_count': None, 'new_ids': [], 'updated_count': 0, 'updated_ids': [],
        'initial_count': 0, 'initial_ids': [],
        'unverified_count': 0, 'unverified_ids': [],
        'by_source': [], 'partial': False,
        'baseline_count': len(state.get('items', {})),
    }
    if observed and observed.date() != local.date():
        result['status'] = 'stale'
        return result
    history = state.get('daily_snapshots', {})
    past = [d for d in history if d < day and _time(history[d].get('at'))]
    if not past:
        return result
    base_day = max(past)
    base = history[base_day]
    base_time = _time(base['at'])
    result.update(base_date=base_day, base_at=base['at'])
    current_status = {sid: s.get('status', 'pending')
                      for sid, s in state.get('sources', {}).items()
                      if s.get('status') != 'disabled'}
    old_status = base.get('source_statuses', {})
    incomplete = ('partial', 'error', 'pending')
    result['partial'] = (any(s in incomplete for s in current_status.values()) or
                         any(old_status.get(sid) in incomplete for sid in current_status))
    # An all-failed run cannot establish a real zero, even if IDs are unchanged.
    if not observed or not any(s in ('ok', 'partial') for s in current_status.values()):
        result['status'] = 'unobserved'
        return result
    result['status'] = 'comparable' if base_day == yesterday else 'gap'
    items = state.get('items', {})
    candidate_ids = set(items) - set(base.get('ids', []))
    changes = [c for c in state.get('changes', [])
               if c.get('id') in items and
               (stamp := _time(c.get('at'))) and base_time < stamp <= observed]
    imported = {c['id'] for c in changes if c.get('kind') == 'initial'}
    previous_sources = set(base.get('initialized_sources', []))
    new, initial, unverified = [], [], []
    for rid in sorted(candidate_ids):
        source = items[rid].get('source_id', '')
        if rid in imported or source not in previous_sources:
            initial.append(rid)
        elif old_status.get(source) != 'ok':
            unverified.append(rid)
        else:
            new.append(rid)
    updated = sorted({c['id'] for c in changes
                      if c.get('kind') == 'updated' and c['id'] not in candidate_ids})
    counts = Counter(items[rid].get('source_id', '') for rid in new)
    by_source = []
    for sid, count in sorted(counts.items()):
        src = state.get('sources', {}).get(sid, {})
        example = next(items[rid] for rid in new if items[rid].get('source_id', '') == sid)
        by_source.append({'source_id': sid,
                          'name': src.get('name') or example.get('source_name', sid),
                          'group': src.get('group') or example.get('group', 'external'),
                          'count': count})
    result.update(new_count=len(new), new_ids=new,
                  updated_count=len(updated), updated_ids=updated,
                  initial_count=len(initial), initial_ids=initial,
                  unverified_count=len(unverified), unverified_ids=unverified,
                  by_source=by_source,
                  partial=result['partial'] or bool(unverified))
    return result


def comparison_lines(result: dict) -> list[str]:
    """Shared truthful labels for notifications, README and documentation tests."""
    status = result['status']
    if status == 'baseline':
        return ['어제 대비: 비교 기준 준비 중',
                f"기준 목록 {result['baseline_count']}건 · 첫 실행/업데이트 후 다음 날부터 비교"]
    if status == 'stale':
        return ['어제 대비: 비교 불가 · 오늘 수집 기록 없음']
    if status == 'unobserved':
        return ['어제 대비: 비교 불가 · 수집 실패 또는 확인 가능한 출처 없음']
    if status == 'gap':
        lines = [f"어제 수집 기록 없음 · {result['base_date']} 대비 신규 {result['new_count']}건"]
    else:
        lines = [f"어제 대비 신규 {result['new_count']}건 · 기존 공고 변경 {result['updated_count']}건"]
    base = _time(result['base_at'])
    end = _time(result['as_of'])
    if base and end:
        lines.append(f"비교: {base:%m/%d %H:%M} → {end:%m/%d %H:%M} (한국시간)")
    if result['by_source']:
        rows = [f"{s['name']} {s['count']}건" for s in result['by_source'][:5]]
        if len(result['by_source']) > 5:
            rows.append(f"외 {len(result['by_source']) - 5}개 출처")
        lines.append(' / '.join(rows))
    if result['initial_count']:
        lines.append(f"신규 출처 최초 적재 {result['initial_count']}건 별도 (신규 집계 제외)")
    if result['unverified_count']:
        lines.append(f"이전 수집 불완전 출처 추가 확인 {result['unverified_count']}건 별도")
    if result['partial']:
        lines.append('일부 출처 수집 불완전 · 확인된 범위만 집계')
    return lines
