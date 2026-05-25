from enum import Enum


class RagCollection(str, Enum):
    LEGAL          = "legal"
    ODS            = "ods"
    PROCEDIMIENTOS = "procedimientos"
    CASOS_EXITO    = "casos_exito"
