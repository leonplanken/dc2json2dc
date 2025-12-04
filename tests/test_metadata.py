import datetime
from dataclasses import dataclass, field
from typing import Optional

from .dataclasses_json import DataClassJsonMixin


@dataclass
class Car(DataClassJsonMixin):
    license_number: str = field(metadata={"dataclasses_json": {}})


@dataclass
class StringDate(DataClassJsonMixin):
    string_date: datetime.datetime = field(
        metadata={
            "dataclasses_json": {
                "encoder": str,
                "decoder": str,
            }
        }
    )


@dataclass
class OptionalStringDate(DataClassJsonMixin):
    string_date: Optional[datetime.datetime] = field(
        default=None,
        metadata={
            "dataclasses_json": {
                "encoder": str,
                "decoder": str,
            }
        },
    )
