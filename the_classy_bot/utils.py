from __future__ import annotations

__all__ = ("resolve_relative_path", )

import os

def resolve_relative_path(base_path: str, relative_path) -> str:
    base_path = os.path.abspath(base_path)
    if os.path.isfile(base_path):
        base_path = os.path.dirname(base_path)
    return os.path.join(base_path, relative_path)