from enum import Enum


class MessageType(str, Enum):
    TEXT  = "text"
    AUDIO = "audio"
