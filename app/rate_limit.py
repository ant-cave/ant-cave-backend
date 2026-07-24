"""每日配额管理：默认用户 2GB/天上传 + 8次/天流水线，未登录直接拒绝。"""

import time
from collections import defaultdict
from dataclasses import dataclass, field

UPLOAD_LIMIT_BYTES = 2 * 1024 * 1024 * 1024  # 2GB
PIPELINE_LIMIT_DAILY = 8


def _today() -> str:
    return time.strftime("%Y-%m-%d")


@dataclass
class _UserQuota:
    upload_bytes: int = 0
    pipeline_runs: int = 0
    date: str = field(default_factory=_today)


class RateLimiter:
    def __init__(self):
        self._quotas: dict[str, _UserQuota] = defaultdict(_UserQuota)

    def _reset_if_new_day(self, q: _UserQuota):
        today = _today()
        if q.date != today:
            q.upload_bytes = 0
            q.pipeline_runs = 0
            q.date = today

    def check_upload(self, user_sub: str, file_size: int) -> tuple[bool, str]:
        q = self._quotas[user_sub]
        self._reset_if_new_day(q)
        if q.upload_bytes + file_size > UPLOAD_LIMIT_BYTES:
            used_mb = q.upload_bytes / 1024 / 1024
            limit_mb = UPLOAD_LIMIT_BYTES / 1024 / 1024
            return False, f"上传配额已用尽（今日已用 {used_mb:.1f}MB / 限额 {limit_mb:.0f}MB）"
        return True, ""

    def record_upload(self, user_sub: str, file_size: int):
        q = self._quotas[user_sub]
        self._reset_if_new_day(q)
        q.upload_bytes += file_size

    def check_pipeline(self, user_sub: str) -> tuple[bool, str]:
        q = self._quotas[user_sub]
        self._reset_if_new_day(q)
        if q.pipeline_runs >= PIPELINE_LIMIT_DAILY:
            return False, f"今日流水线次数已用尽（已用 {q.pipeline_runs} 次 / 限额 {PIPELINE_LIMIT_DAILY} 次）"
        return True, ""

    def record_pipeline(self, user_sub: str):
        q = self._quotas[user_sub]
        self._reset_if_new_day(q)
        q.pipeline_runs += 1

    def get_usage(self, user_sub: str) -> dict:
        q = self._quotas[user_sub]
        self._reset_if_new_day(q)
        return {
            "upload_bytes": q.upload_bytes,
            "upload_limit": UPLOAD_LIMIT_BYTES,
            "upload_used_mb": round(q.upload_bytes / 1024 / 1024, 1),
            "upload_limit_mb": round(UPLOAD_LIMIT_BYTES / 1024 / 1024, 0),
            "pipeline_runs": q.pipeline_runs,
            "pipeline_limit": PIPELINE_LIMIT_DAILY,
        }


limiter = RateLimiter()
