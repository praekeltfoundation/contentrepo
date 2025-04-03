from typing import Any
from collections.abc import Sequence, Mapping

def is_subscriptable(obj: Any) -> bool:
    return isinstance(obj, (Sequence, Mapping))