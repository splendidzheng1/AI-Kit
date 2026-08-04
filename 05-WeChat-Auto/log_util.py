"""带时间戳的终端输出。"""

from __future__ import annotations

import builtins
from datetime import datetime


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(*args, sep: str = " ", end: str = "\n", file=None, flush: bool = False) -> None:
    """等价于 print，但在内容前加上 [YYYY-MM-DD HH:MM:SS]。"""
    if not args:
        builtins.print(f"[{now_str()}]", end=end, file=file, flush=flush)
        return

    text = sep.join(str(a) for a in args)
    leading_nl = 0
    while text.startswith("\n"):
        leading_nl += 1
        text = text[1:]
    if leading_nl:
        builtins.print("\n" * leading_nl, end="", file=file, flush=flush)
    builtins.print(f"[{now_str()}] {text}", end=end, file=file, flush=flush)
