from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class UserProfile:
    user_id: str                            # session_id / from_hash
    name: str | None = None
    district: str | None = None
    issue: str | None = None
    conversation_stage: str = "ONBOARDING"  # ONBOARDING | ACTIVE
    awaiting_doc_confirmation: bool = False  # esperando que el usuario confirme generar documento
    awaiting_next_action: bool = False       # esperando selección del menú post-documento
    pending_doc_type: str | None = None      # tipo de documento pendiente de confirmación (carta, solicitud…)

    def is_complete(self) -> bool:
        return bool(self.name and self.district)
