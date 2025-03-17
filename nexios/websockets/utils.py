from datetime import  datetime,timezone
from enum import Enum
from dataclasses import dataclass
import uuid
from uuid import UUID
import typing


class ChannelAddStatusEnum(Enum):
    CHANNEL_ADDED = "CHANNEL_ADDED"
    CHANNEL_EXIST = "CHANNEL_EXIST"


class ChannelRemoveStatusEnum(Enum):
    CHANNEL_REMOVED = "CHANNEL_REMOVED"
    CHANNEL_DOES_NOT_EXIST = "CHANNEL_DOES_NOT_EXIST"
    GROUP_REMOVED = "GROUP_REMOVED"
    GROUP_DOES_NOT_EXIST = "GROUP_DOES_NOT_EXIST"


class GroupSendStatusEnum(Enum):
    GROUP_SEND = "GROUP_SEND"
    NO_SUCH_GROUP = "NO_SUCH_GROUP"


class PayloadTypeEnum(Enum):
    JSON = "json"
    TEXT = "text"
    BYTES = "bytes"


@dataclass
class ChannelMessageDC:
    payload: typing.Union[str,bytes]
    uuid: UUID = uuid.uuid4()
    created: datetime = datetime.now(tz=timezone.utc)
