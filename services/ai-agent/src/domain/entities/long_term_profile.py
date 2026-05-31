from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LongTermProfile:
    user_id: str
    name: str | None = None
    district: str | None = None
    issues_worked: list[str] = field(default_factory=list)
    documents_generated: int = 0
    last_session_summary: str | None = None
    sessions_count: int = 0
    first_seen: str | None = None   # fecha ISO (YYYY-MM-DD)
    last_seen: str | None = None    # fecha ISO (YYYY-MM-DD)
