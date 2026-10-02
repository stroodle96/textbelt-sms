# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""Native Assist options, separate from outbound notification destinations."""

from __future__ import annotations

# ValueError is the shared configuration-validation contract.
# ruff: noqa: TRY004
from dataclasses import dataclass
from ipaddress import ip_address
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from collections.abc import Mapping

from .recipients import normalize_recipients

CONF_ASSIST_ENABLED = "assist_enabled"
CONF_PIPELINE_ID = "pipeline_id"
CONF_AUTHORIZED_SENDERS = "authorized_senders"
CONF_CONVERSATION_TIMEOUT = "conversation_timeout"
DEFAULT_CONVERSATION_TIMEOUT = 1800
MAX_CONVERSATION_TIMEOUT = 86400


def normalize_pipeline_id(value: Any) -> str | None:
    """Keep preferred dynamic rather than persisting the selector sentinel."""
    if value in (None, "", "preferred"):
        return None
    if not isinstance(value, str):
        msg = "Invalid pipeline ID"
        raise ValueError(msg)
    return value


def normalize_authorized_senders(value: Any) -> tuple[str, ...]:
    """Validate text input and persisted lists using the same number rules."""
    if isinstance(value, (list, tuple)) and all(isinstance(x, str) for x in value):
        value = "\n".join(value)
    if not isinstance(value, str):
        msg = "Invalid authorized senders"
        raise ValueError(msg)
    return tuple(normalize_recipients(value))


def normalize_conversation_timeout(value: Any) -> int:
    """Accept integral seconds within a one-day inactivity bound."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        msg = "Invalid conversation timeout"
        raise ValueError(msg)
    if not 1 <= value <= MAX_CONVERSATION_TIMEOUT or int(value) != value:
        msg = "Invalid conversation timeout"
        raise ValueError(msg)
    return int(value)


def callback_base_url(value: str | None) -> str:
    """Validate configured HTTPS/public URL shape, without testing reachability."""
    try:
        url = urlsplit(value or "")
        host = (url.hostname or "").rstrip(".")
        if (
            url.scheme != "https"
            or not host
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise ValueError  # noqa: TRY301 -- normalize all URL parse failures below.
        if url.port is not None and not 1 <= url.port <= 65535:  # noqa: PLR2004 -- TCP port bound.
            raise ValueError  # noqa: TRY301 -- normalize all URL parse failures below.
        try:
            address = ip_address(host)
        except ValueError:
            if "." not in host or host.endswith(
                (".local", ".localhost", ".internal", ".test", ".invalid")
            ):
                raise ValueError from None
        else:
            if not address.is_global:
                raise ValueError
    except ValueError:
        msg = "Configure a public HTTPS Home Assistant external URL"
        raise ValueError(msg) from None
    return value.rstrip("/")


@dataclass(frozen=True, slots=True)
class AssistOptions:
    """Validated opt-in settings consumed by the native conversation manager."""

    enabled: bool = False
    pipeline_id: str | None = None
    authorized_senders: tuple[str, ...] = ()
    conversation_timeout: int = DEFAULT_CONVERSATION_TIMEOUT

    @classmethod
    def from_mapping(cls, options: Mapping[str, Any]) -> AssistOptions:
        """Read persisted configuration; reject malformed values explicitly."""
        enabled = options.get(CONF_ASSIST_ENABLED, False)
        if not isinstance(enabled, bool):
            msg = "Invalid Assist enabled value"
            raise ValueError(msg)
        return cls(
            enabled=enabled,
            pipeline_id=normalize_pipeline_id(options.get(CONF_PIPELINE_ID)),
            authorized_senders=normalize_authorized_senders(
                options.get(CONF_AUTHORIZED_SENDERS, [])
            ),
            conversation_timeout=normalize_conversation_timeout(
                options.get(CONF_CONVERSATION_TIMEOUT, DEFAULT_CONVERSATION_TIMEOUT)
            ),
        )
