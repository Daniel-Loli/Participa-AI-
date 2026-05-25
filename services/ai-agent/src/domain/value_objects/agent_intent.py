from enum import Enum


class AgentIntent(str, Enum):
    ONBOARDING      = "onboarding"
    LEGAL           = "legal"
    LEGAL_REDACTOR  = "legal_redactor"  # intención compuesta: ley + documento en un turno
    ESTRATEGA       = "estratega"
    OPORTUNIDADES   = "oportunidades"
    RED             = "red"
    REDACTOR        = "redactor"
    GENERAL         = "general"
