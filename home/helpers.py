from collections.abc import Mapping, Sequence
from typing import Any


def is_subscriptable(obj: Any) -> bool:
    return isinstance(obj, Sequence | Mapping)
