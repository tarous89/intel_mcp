from __future__ import annotations

from contextvars import ContextVar, Token

_oauth_subject: ContextVar[str | None] = ContextVar("oauth_subject", default=None)


def current_oauth_subject() -> str | None:
    return _oauth_subject.get()


def set_oauth_subject(subject: str | None) -> Token[str | None]:
    return _oauth_subject.set(subject)


def reset_oauth_subject(token: Token[str | None]) -> None:
    _oauth_subject.reset(token)
