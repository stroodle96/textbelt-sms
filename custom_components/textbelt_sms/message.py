# Copyright (c) 2026 Textbelt SMS contributors
"""Readable formatting and bounded GSM preparation without provider calls."""

# Exception constructor takes a stable code and user-visible message.
# ruff: noqa: EM101
import html
import re
from typing import Literal

from .models import (
    DEFAULT_POLICY,
    MessagePreparationError,
    PreparedMessage,
    ProviderPolicy,
)

_TRANSLATIONS = str.maketrans(
    {
        "“": '"',
        "”": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u2013": "-",
        "—": "-",
        "\u2212": "-",
        "…": "...",
        "•": "-",
        "°": " degrees ",
        "\u00a0": " ",
    }
)
_CONTROL_LIMIT = 32
_NOTICE = "Response shortened."


def _normalize(text: str) -> str:
    for char in text:
        if ord(char) < _CONTROL_LIMIT and char not in "\n\r":
            raise MessagePreparationError(
                "unsupported_character", f"Unsupported character U+{ord(char):04X}"
            )
    # Resolve quoted link wrappers before protecting the entire URL span.
    text = re.sub(
        r"<a\s+href=([\"\'])(.*?)\1\s*>(.*?)</a>",
        r"[\3](\2)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    prefix = "URLTOKEN"
    while prefix in text:
        prefix += "X"
    urls: list[str] = []

    def protect(match: re.Match[str]) -> str:
        url = match[0]
        closing = ""
        if text[: match.start()].endswith("](") and url.endswith(")"):
            url = url[:-1]
            closing = ")"
        urls.append(url)
        return f"{prefix}{len(urls) - 1}ENDTOKEN" + closing

    text = re.sub(r"https?://[^\s<>]+", protect, text)
    text = text.replace("\r\n", "\n").replace("\r", "\n").translate(_TRANSLATIONS)
    # Only complete reviewed tags are formatting; comparisons and URL values stay.
    text = re.sub(
        r"</?(?:speak|ul|ol|emphasis|prosody|say-as|span|strong|b|i)\b[^>]*>",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"<break\b[^>]*>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\n*</?(?:p|div|br)\b[^>]*>\n*", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<li\b[^>]*>", "\n- ", text, flags=re.IGNORECASE)
    text = re.sub(r"</li\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(
        r"&(?:#[xX][0-9a-fA-F]+|#[0-9]+|[A-Za-z][A-Za-z0-9]+);",
        lambda match: html.unescape(match[0]),
        text,
    )
    text = text.replace("  degrees ", " degrees ")
    text = re.sub(
        rf"\[([^]\n]+)\]\(((?:https?://[^\s)]+|{prefix}[0-9]+ENDTOKEN))\)",
        r"\1 (\2)",
        text,
    )
    text = re.sub(r"(\*\*|__)(.+?)\1", r"\2", text)
    text = re.sub(r"(?m)^\s{0,3}#{1,6} ", "", text)
    text = re.sub(r"(?m)^([ \t]*)[*+] ", r"\1- ", text)
    text = re.sub(r"`([^`\n]+)`", r"\1", text)
    for index, url in enumerate(urls):
        text = text.replace(f"{prefix}{index}ENDTOKEN", url)
    return text.strip()


def _units(text: str, policy: ProviderPolicy) -> int:
    for char in text:
        if char not in policy.allowed_characters:
            raise MessagePreparationError(
                "unsupported_character", f"Unsupported character U+{ord(char):04X}"
            )
    return sum(2 if char in policy.extension_characters else 1 for char in text)


def _take(text: str, budget: int, policy: ProviderPolicy) -> tuple[str, str]:
    used = index = 0
    while index < len(text):
        weight = 2 if text[index] in policy.extension_characters else 1
        if used + weight > budget:
            break
        used += weight
        index += 1
    if index == 0:
        raise MessagePreparationError(
            "invalid_policy", "Policy cannot fit message content"
        )
    if index == len(text):
        return text, ""
    candidate = text[:index]
    sentences = list(re.finditer(r"[.!?](?=\s)", candidate))
    if sentences:
        index = sentences[-1].end()
    else:
        spaces = list(re.finditer(r"\s+", candidate))
        if spaces and spaces[-1].start() > 0:
            index = spaces[-1].start()
    return text[:index], text[index:].lstrip()


def _split(
    text: str, count: int, policy: ProviderPolicy, *, shorten: bool = False
) -> tuple[str, ...]:
    parts: list[str] = []
    remaining = text
    index = 1
    while remaining:
        prefix = f"({index}/{count}) "
        suffix = " " + _NOTICE if shorten and index == policy.max_parts else ""
        budget = policy.max_part_septets - _units(prefix + suffix, policy)
        if budget < 1:
            raise MessagePreparationError(
                "invalid_policy", "Policy cannot fit labels and notice"
            )
        chunk, remaining = _take(remaining, budget, policy)
        parts.append(prefix + chunk + suffix)
        if suffix:
            break
        index += 1
    return tuple(parts)


def prepare_message(  # noqa: PLR0912
    message: str,
    *,
    title: str | None = None,
    mode: Literal["automation", "assist"] = "automation",
    compact: bool = False,
    policy: ProviderPolicy = DEFAULT_POLICY,
) -> PreparedMessage:
    """Validate the complete source before splitting or visibly shortening."""
    if mode not in {"automation", "assist"}:
        error = "Unknown preparation mode"
        raise ValueError(error)
    text = _normalize(message)
    if not text:
        if mode == "automation":
            raise MessagePreparationError("empty_message", "Message is empty")
        text = "No response was returned."
    if title:
        normalized_title = _normalize(title)
        if normalized_title:
            text = normalized_title + ": " + text
    if compact and mode == "assist":
        text = re.sub(r"\s+", " ", text)
    units = _units(text, policy)
    if units <= policy.max_part_septets:
        return PreparedMessage((text,), text, shortened=False)
    count = 2
    while True:
        parts = _split(text, count, policy)
        if len(parts) == count:
            break
        count = len(parts)
    shortened = count > policy.max_parts
    if shortened:
        if mode == "automation":
            raise MessagePreparationError(
                "message_too_long", "Message exceeds maximum outgoing parts"
            )
        parts = _split(text, policy.max_parts, policy, shorten=True)
    for part in parts:
        if _units(part, policy) > policy.max_part_septets:
            raise MessagePreparationError(
                "invalid_policy", "Prepared part exceeds budget"
            )
    return PreparedMessage(parts, text, shortened)
