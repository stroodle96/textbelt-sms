# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""Explicit international notification destinations."""

import re

CONF_NOTIFICATION_RECIPIENTS = "notification_recipients"


def normalize_recipients(value: str) -> list[str]:
    """Normalize one explicit international number per nonempty line."""
    recipients = []
    for line in value.splitlines():
        if not line.strip():
            continue
        phone = re.sub(r"[ ()\-.]", "", line.strip())
        if not re.fullmatch(r"\+[1-9][0-9]{1,14}", phone):
            msg = "Use explicit international numbers"
            raise ValueError(msg)
        if phone not in recipients:
            recipients.append(phone)
    return recipients
