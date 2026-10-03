# Copyright (c) 2026 Textbelt SMS contributors
"""Immutable reviewed preparation contracts."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderPolicy:
    """Integration budgets, not universal provider or carrier limits."""

    allowed_characters: str = (
        "@£$¥èéùìòÇØøÅå_ÆæßÉ !\"#%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLM"
        "NOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà^{}\\[~]|€\n"
    )
    extension_characters: frozenset[str] = frozenset("^{}\\[~]|€")
    max_part_septets: int = 160
    max_parts: int = 5

    def __post_init__(self) -> None:
        """Reject invalid budgets and encoding tables."""
        if self.max_part_septets < 1 or self.max_parts < 1:
            error = "Policy budgets must be positive"
            raise ValueError(error)
        if not self.extension_characters.issubset(self.allowed_characters):
            error = "Extension characters must be allowed"
            raise ValueError(error)


DEFAULT_POLICY = ProviderPolicy()


@dataclass(frozen=True, slots=True)
class PreparedMessage:
    """Prepared parts and complete normalized source."""

    parts: tuple[str, ...]
    normalized_text: str
    shortened: bool


class MessagePreparationError(ValueError):
    """Visible failure before any provider request."""

    def __init__(self, code: str, message: str) -> None:
        """Record the preparation error code."""
        super().__init__(message)
        self.code = code
