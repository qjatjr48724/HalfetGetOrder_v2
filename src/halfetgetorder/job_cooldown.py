"""주문 수집 작업 재실행 간격(고도몰·쿠팡 API, 2분) 확인."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

MIN_INTERVAL_MINUTES = 2
MIN_INTERVAL_SECONDS = MIN_INTERVAL_MINUTES * 60


def get_last_run_datetime(last_run_path: Path | str) -> datetime | None:
    path = Path(last_run_path)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        ts = data.get("ts")
        if not ts:
            return None
        return datetime.fromisoformat(ts)
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return None


def get_remaining_seconds(
    last_run_path: Path | str,
    *,
    now: datetime | None = None,
) -> int:
    """0이면 실행 가능, 0보다 크면 남은 대기 초."""
    last_dt = get_last_run_datetime(last_run_path)
    if last_dt is None:
        return 0
    now = now or datetime.now()
    elapsed = (now - last_dt).total_seconds()
    return max(0, int(MIN_INTERVAL_SECONDS - elapsed))


def record_last_run(last_run_path: Path | str, *, when: datetime | None = None) -> None:
    """작업 완료 직후 호출 — 이 시각부터 재실행 대기가 시작됩니다."""
    when = when or datetime.now()
    path = Path(last_run_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"ts": when.isoformat()}), encoding="utf-8")


def format_remaining_hms(seconds: int) -> str:
    m, s = divmod(max(0, seconds), 60)
    return f"{m}:{s:02d}"


def format_block_message(remaining: int, *, last_dt: datetime | None = None) -> str:
    m, s = divmod(remaining, 60)
    lines = [
        f"⚠️ 고도몰·쿠팡 API 보호: 작업 완료 후 최소 {MIN_INTERVAL_MINUTES}분 간격이 필요합니다.",
    ]
    if last_dt is not None:
        lines.append(f"   마지막 완료: {last_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"   약 {m}분 {s:02d}초 후 다시 시도해 주세요.")
    return "\n".join(lines)
