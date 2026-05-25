from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class UserProfile:
    user_id: str                            # session_id / from_hash
    name: str | None = None
    district: str | None = None
    issue: str | None = None
    conversation_stage: str = "ONBOARDING"  # ONBOARDING | ACTIVE

    def is_complete(self) -> bool:
        return bool(self.name and self.district)
