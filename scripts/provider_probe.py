# Copyright (c) 2026 Daniel Strodl
"""
Generate raw provider probes offline without making requests.

GSM tables reviewed against ETSI TS 123 038 V18.0.0 (2024-05), clauses
6.2.1 and 6.2.1.1, pages 20-22, on 2026-09-30. Provider acceptance remains
unverified. Raw ESC is a diagnostic control, never a prose candidate.
"""

from __future__ import annotations

import argparse
import json
import unicodedata
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlencode

if TYPE_CHECKING:
    from typing import Any

DEFAULT = (
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ"
    " !\"#¤%&'()*+,-./0123456789:;<=>?¡"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿"
    "abcdefghijklmnopqrstuvwxyzäöñüà"
)
EXTENSION = "\f^{}\\[~]|€"
EXTRAS = (
    "\x1b",
    "\t",
    "`",
    "\u2022",
    "\u2018",
    "\u2019",
    "\u201c",
    "\u201d",
    "\u2013",
    "\u2014",
    "\u4e2d",
    "\u0627",
    "\U0001f600",
    "\U0001f44d\U0001f3fd",
    "\U0001f469\u200d\U0001f4bb",
    "e\u0301",
    "\u00a0",
    "\u200b",
    "\u2028",
    "\r\n",
    "\\n",
    "\x00",
)


def units(message: str) -> tuple[bool, int | None, int]:
    """Describe GSM septets and UTF-16 code units without sanitization."""
    gsm = all(char in DEFAULT or char in EXTENSION for char in message)
    septets = sum(2 if char in EXTENSION else 1 for char in message) if gsm else None
    return gsm, septets, len(message.encode("utf-16-le")) // 2


def record(identifier: str, message: str, category: str) -> dict[str, Any]:
    """Create reproducible payload metadata and deliberately unknown evidence."""
    gsm, septets, utf16 = units(message)
    return {
        "version": 1,
        "id": identifier,
        "category": category,
        "message": message,
        "code_points": [f"U+{ord(char):04X}" for char in message],
        "unicode_names": [unicodedata.name(char, "CONTROL") for char in message],
        "utf8_hex": message.encode().hex(),
        "gsm_eligible": gsm,
        "gsm_septets": septets,
        "utf16_units": utf16,
        "content_type": "application/x-www-form-urlencoded",
        "message_form": urlencode({"message": message}),
        "verification_mode": "not_run",
        "api_verdict": "unknown",
        "carrier_verdict": "unconfirmed",
        "fidelity_verdict": "unknown",
        "http_status": None,
        "sanitized_response": None,
        "text_id": None,
        "quota_before": None,
        "quota_after": None,
        "quota_change": None,
        "status_timeline": [],
        "received_text": None,
        "transformation": None,
        "segmentation": None,
        "date": None,
        "account_scope": None,
        "country": None,
        "carrier": None,
    }


def maximum_probes(maximum: int) -> list[dict[str, Any]]:
    """Generate exact lengths only after the provider maximum is established."""
    if maximum < 1:
        message = "Maximum must be positive"
        raise ValueError(message)
    return [
        record(f"provider-max-{n}", "A" * n, "provider_maximum")
        for n in (maximum - 1, maximum, maximum + 1)
    ]


def corpus() -> list[dict[str, Any]]:
    """Generate every candidate character and the planned boundary hypotheses."""
    rows = []
    for category, characters in (
        ("gsm_default", DEFAULT),
        ("gsm_extension", EXTENSION),
    ):
        rows.extend(
            record(f"{category}-{ord(char):04x}", "A" + char + "B", category)
            for char in characters
        )
    rows.extend(
        record(f"extra-{n:02}", "A" + char + "B", "diagnostic_unicode_control")
        for n, char in enumerate(EXTRAS)
    )
    for name, char, lengths in (
        ("ascii", "A", (159, 160, 161, 306, 307)),
        ("extension", "^", (79, 80, 81)),
        ("bmp", "中", (69, 70, 71, 134, 135)),
        ("emoji", "😀", (34, 35, 36)),
    ):
        rows.extend(
            record(f"boundary-{name}-{n}", char * n, "length_hypothesis")
            for n in lengths
        )
    rows.extend(
        record(f"encoding-switch-{n}", "A" * n + "\u2022", "encoding_hypothesis")
        for n in (69, 70)
    )
    return rows


def write_records(
    output: Path, rows: list[dict[str, Any]], *, overwrite: bool = False
) -> None:
    """Create a probe file without silently replacing existing evidence."""
    with output.open("w" if overwrite else "x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")


def main() -> None:
    """Write deterministic JSONL inputs and unexecuted evidence templates."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--documented-maximum", type=int)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    rows = corpus()
    if args.documented_maximum is not None:
        rows.extend(maximum_probes(args.documented_maximum))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_records(args.output, rows, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
