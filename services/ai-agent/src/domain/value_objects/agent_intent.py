from enum import Enum


class AgentIntent(str, Enum):
    ONBOARDING      = "onboarding"
    MENU            = "menu"            # saludo o solicitud de menú principal
    LEGAL           = "legal"
    LEGAL_REDACTOR  = "legal_redactor"  # intención compuesta: ley + documento en un turno
    ESTRATEGA       = "estratega"
    OPORTUNIDADES   = "oportunidades"
    RED             = "red"
    REDACTOR        = "redactor"
    GENERAL         = "general"
