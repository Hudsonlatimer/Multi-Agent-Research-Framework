"""Optional progress messages. The library stays quiet unless a sink is bound."""

from collections.abc import Callable
from contextvars import ContextVar, Token

StatusFn = Callable[[str], None]

_status: ContextVar[StatusFn | None] = ContextVar("research_status", default=None)


def emit(message: str) -> None:
    sink = _status.get()
    if sink is not None:
        sink(message)


def bind_status(sink: StatusFn) -> Token[StatusFn | None]:
    return _status.set(sink)


def reset_status(token: Token[StatusFn | None]) -> None:
    _status.reset(token)
