"""This is a mock-up of the relevant classes / decorators from the original
dataclasses_json source."""

import json
from typing import Type, TypeVar, Union

from dc2json2dc.json import JSONDataclassDecoder, JSONDataclassEncoder

JsonData = Union[str, bytes, bytearray]
A = TypeVar("A", bound="DataClassJsonMixin")


def recursive_pop(key, obj):
    if isinstance(obj, dict):
        return {k: recursive_pop(key, v) for (k, v) in obj.items() if k != key}
    if isinstance(obj, list):
        return [recursive_pop(key, x) for x in obj]
    return obj


test_classes = set()


class DataClassJsonMixin:
    def __init_subclass__(cls, **kwargs):
        test_classes.add(cls)

    @classmethod
    def from_json(
        cls: Type[A],
        s: JsonData,
        *,
        parse_float=None,
        parse_int=None,
        parse_constant=None,
        infer_missing=False,
        **kw,
    ) -> A:
        kw["class_list"] = test_classes
        kw["cls"] = JSONDataclassDecoder
        return json.loads(s, **kw)

    def to_json(self, *args, **kwargs):
        return json.dumps(self, cls=JSONDataclassEncoder)


def dataclass_json(*args, **kwargs):
    def wrap(cls):
        test_classes.add(cls)
        cls.from_json = classmethod(DataClassJsonMixin.from_json.__func__)
        cls.to_json = DataClassJsonMixin.to_json
        return cls

    if kwargs or len(args) > 1:
        return lambda x: wrap(x)
    if len(args) != 1:
        raise ValueError
    cls = args[0]
    return wrap(cls)
