from __future__ import annotations

__all__ = ("resolve_relative_path", )

import os
import random


def resolve_relative_path(base_path: str, relative_path: str) -> str:
    base_path = os.path.abspath(base_path)
    if os.path.isfile(base_path):
        base_path = os.path.dirname(base_path)
    return os.path.join(base_path, relative_path)


def random_hex(size: int) -> str:
    return "".join(random.choices("0123456789abcdef", k = size))