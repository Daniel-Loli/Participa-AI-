from enum import Enum


class AgentIntent(str, Enum):
    ONBOARDING    = "onboarding"
    LEGAL         = "legal"
    ESTRATEGA     = "estratega"
    OPORTUNIDADES = "oportunidades"
    RED           = "red"
    REDACTOR      = "redactor"
    GENERAL       = "general"
