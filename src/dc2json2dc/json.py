import dataclasses
import json
import types
from typing import Callable, Iterable, Mapping

from typing_extensions import override

from .protocols import DataclassInstance

_sentinel = object()


class JSONDataclassEncoder(json.JSONEncoder):
    """
    Allows for encoding objects of any ``@dataclass''-decorated class into
    JSON.

    This is done by iterating over the dataclass's fields which were not
    explicitly declared as having ``init=False`` (or as ``InitVar``s) in the
    dataclass's definition.  A field ``__class__`` is added to the JSON for
    each object, specifying the name of the dataclass in question.
    """

    @override
    def default(self, obj):
        if dataclasses.is_dataclass(obj):
            cls_flds = [f for f in dataclasses.fields(obj) if f.init]
            result = {"__class__": obj.__class__.__name__}
            result.update((f.name, getattr(obj, f.name)) for f in cls_flds)
            return result
        if isinstance(obj, Mapping):
            return dict(obj.items())
        if isinstance(obj, Iterable):
            return list(iter(obj))
        return super().default(obj)


class AbstractJSONDataclassDecoder(json.JSONDecoder):
    """
    This class lays the groundwork for decoding objects of any
    ``@dataclass''-decorated class from JSON.

    This is done by iterating over the dataclass's fields which were not
    explicitly declared as having ``init=False`` (or as ``InitVar``s) in the
    dataclass's definition.  The name of the dataclass to deserialize is
    taken from ``__class__`` fields in the JSON, and has to be explicitly
    registered first.

    How this is done is the reponsibility of classes extending this class.
    Also, if a dataclass specifies ``InitVar``s without a default value,
    this needs to be handled by a custom subclass.
    """

    serializable_classes: dict[str, type[DataclassInstance]] | None
    delegate_object_hook: Callable[[object], object] | None = None

    def __init__(self, **kwargs):
        self.delegate_object_hook = kwargs.pop("object_hook", None)
        super().__init__(object_hook=self.object_hook, **kwargs)

    def __init_subclass__(cls, **kwargs):
        if not hasattr(cls, "serializable_classes"):
            raise TypeError(f"{cls.__name__} must define serializable_classes")

    def object_hook(self, obj):
        if self.delegate_object_hook is not None:
            new_obj = self.delegate_object_hook(obj)
            if new_obj is not obj:
                return new_obj
        classname = obj.pop("__class__", _sentinel)
        if classname is _sentinel:
            return obj
        if type(classname) is not str:
            raise ValueError(
                f"Invalid type for class name (__class__): "
                f"expected str, found {type(classname).__name__}"
            )
        cls: type[DataclassInstance] = self.serializable_classes.get(
            classname, None
        )
        if not cls:
            raise TypeError(
                f"Class {classname} not registered for deserialization."
            )
        cls_flds = [f for f in dataclasses.fields(cls) if f.init]
        kwargs = {}
        for fld in cls_flds:
            val = obj.pop(fld.name, _sentinel)
            if val is _sentinel:
                raise ValueError(
                    f"Field {fld.name} not specified for class {classname}"
                )
            kwargs[fld.name] = val
        if obj:
            keynames = " ".join(str(key) for key in obj)
            raise ValueError(
                f"Extraneous values specified for dataclass {classname}: "
                f"{keynames}"
            )
        try:
            return cls(**kwargs)
        except Exception as e:
            raise ValueError(
                f"Instantiation of dataclass {cls.__name__} "
                "failed. (Does it specify InitVars?)"
            ) from e


def _build_serializable_classes_dict(
    class_list: Iterable[type],
) -> dict[str, type[DataclassInstance]]:
    result: dict[str, type[DataclassInstance]] = {}
    for cls in class_list:
        if cls.__name__ in result:
            raise ValueError(f"Duplicate name {cls.__name__} in class_list")
        if not dataclasses.is_dataclass(cls):
            raise TypeError(f"{cls.__name__} is not a dataclass")
        result[cls.__name__] = cls
    return result


class JSONDataclassDecoder(AbstractJSONDataclassDecoder):
    """
    Class for decoding objects of ``@dataclass''-decorated classes from JSON,
    as previously encoded with `JSONDataclassDecoder`.

    A list of classes to be supported must be passed as a ``class_list``
    argument when using this decoder.

    If a dataclass specifies ``InitVar``s without a default value, this class
    cannot deal with that and should be extended.

    Examples
    --------
    >>> json.loads(source, cls=JSONDataclassDecoder,
    ...            class_list=(Knight, Viking, Parrot))

    """

    serializable_classes = None

    def __init__(self, class_list=(), **kwargs):
        self.serializable_classes = _build_serializable_classes_dict(
            class_list
        )
        super().__init__(**kwargs)


def decoder_factory(name: str, class_list: Iterable[type]):
    """
    Construct a new class for decoding objects of ``@dataclass''-decorated
    classes from JSON, as previously encoded with `JSONDataclassDecoder`.

    Note that a the generated decoder cannot deal with dataclasses specifying
    ``InitVar``s without a default value.

    Parameters
    ----------
    class_list : An iterable of dataclass types
        The dataclasses to be supported by the class.

    Examples
    --------
    >>> class_list=(Knight, Viking, Parrot)
    >>> PythonDecoder = decoder_factory('PythonDecoder', class_list)
    >>> json.loads(source, cls=PythonDecoder)

    """

    def class_body(ns):
        ns["serializable_classes"] = _build_serializable_classes_dict(
            class_list
        )

    return types.new_class(
        name, (AbstractJSONDataclassDecoder,), exec_body=class_body
    )
