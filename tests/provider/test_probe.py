# Copyright (c) 2026 Daniel Strodl
"""Offline contract preparation tests; no HA or network dependencies."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs

from scripts import provider_probe as probe

EXPECTED_DEFAULT_COUNT = 127
EXPECTED_EXTENSION_COUNT = 10
EXPECTED_PROBE_COUNT = 177


class ProbeTests(unittest.TestCase):
    """Protect raw code points, boundaries, serialization, and evidence states."""

    def test_complete_gsm_tables(self) -> None:
        """Check candidate counts and distinguish encoding unit weights."""
        assert len(probe.DEFAULT) == EXPECTED_DEFAULT_COUNT
        assert len(set(probe.DEFAULT)) == EXPECTED_DEFAULT_COUNT
        assert len(probe.EXTENSION) == EXPECTED_EXTENSION_COUNT
        assert "\u001b" not in probe.DEFAULT
        assert probe.units("A^€\n") == (True, 6, 4)
        assert probe.units("😀") == (False, None, 2)

    def test_reviewed_primary_table_membership(self) -> None:
        """Catch substitutions even when alphabet counts remain unchanged."""
        # Independently transcribed ETSI TS 123 038 V18.0.0 (2024-05),
        # clauses 6.2.1 and 6.2.1.1, printed pages 20-22; reviewed 2026-09-30.
        # ASCII printable entries except extension symbols and grave accent.
        expected_default = set(range(0x20, 0x7F)) - {
            0x5B,
            0x5C,
            0x5D,
            0x5E,
            0x60,
            0x7B,
            0x7C,
            0x7D,
            0x7E,
        }
        expected_default.update(
            {
                0x000A,
                0x000D,
                0x00A1,
                0x00A3,
                0x00A4,
                0x00A5,
                0x00A7,
                0x00BF,
                0x00C4,
                0x00C5,
                0x00C6,
                0x00C7,
                0x00C9,
                0x00D1,
                0x00D6,
                0x00D8,
                0x00DC,
                0x00DF,
                0x00E0,
                0x00E4,
                0x00E5,
                0x00E6,
                0x00E8,
                0x00E9,
                0x00EC,
                0x00F1,
                0x00F2,
                0x00F6,
                0x00F8,
                0x00F9,
                0x00FC,
                0x0393,
                0x0394,
                0x0398,
                0x039B,
                0x039E,
                0x03A0,
                0x03A3,
                0x03A6,
                0x03A8,
                0x03A9,
            }
        )
        expected_extension = {
            0x000C,
            0x005B,
            0x005C,
            0x005D,
            0x005E,
            0x007B,
            0x007C,
            0x007D,
            0x007E,
            0x20AC,
        }
        assert {ord(char) for char in probe.DEFAULT} == expected_default
        assert {ord(char) for char in probe.EXTENSION} == expected_extension

    def test_preserved_corpus_fixture(self) -> None:
        """Catch payload, metadata, ordering, or saved evidence drift."""
        fixture = (
            Path(__file__).resolve().parents[2]
            / "docs/research/probes/v1-inputs-and-pending-results.jsonl"
        ).read_bytes()
        # Frozen Stage 0 v1 artifact bytes; never regenerate expected rows here.
        assert (
            hashlib.sha256(fixture).hexdigest()
            == "c6af99bf9069ad878845d69474c170b7e4f8d4abf355a4eecc0b7197207fb07d"
        )
        expected_rows = [json.loads(line) for line in fixture.splitlines()]
        assert probe.corpus() == expected_rows

    def test_raw_form_roundtrip_and_separate_verdicts(self) -> None:
        """Preserve actual code points and explicitly pending evidence."""
        rows = probe.corpus()
        assert len({r["id"] for r in rows}) == len(rows)
        for row in rows:
            decoded = parse_qs(row["message_form"], keep_blank_values=True)
            assert decoded["message"][0] == row["message"]
            assert row["api_verdict"] == "unknown"
            assert row["carrier_verdict"] == "unconfirmed"
            assert row["fidelity_verdict"] == "unknown"
            assert row["http_status"] is None
            assert "key" not in decoded
            assert "phone" not in decoded
        messages = {r["message"] for r in rows}
        assert "A\nB" in messages
        assert "A\\nB" in messages
        assert "A\r\nB" in messages
        assert "A" * 307 in messages
        assert "^" * 81 in messages
        assert "😀" * 36 in messages

    def test_maximum_is_explicit_and_unlabelled(self) -> None:
        """Generate exact boundary payloads without added labels."""
        assert [r["message"] for r in probe.maximum_probes(10)] == [
            "A" * 9,
            "A" * 10,
            "A" * 11,
        ]
        rejected = False
        try:
            probe.maximum_probes(0)
        except ValueError:
            rejected = True
        assert rejected

    def test_existing_evidence_requires_explicit_overwrite(self) -> None:
        """Preserve prior observations unless replacement is requested."""
        with TemporaryDirectory() as directory:
            output = Path(directory) / "evidence.jsonl"
            output.write_text("observed result\n", encoding="utf-8")
            rejected = False
            try:
                probe.write_records(output, probe.corpus())
            except FileExistsError:
                rejected = True
            assert rejected
            assert output.read_text(encoding="utf-8") == "observed result\n"
            probe.write_records(output, probe.corpus(), overwrite=True)
            written_lines = output.read_text(encoding="utf-8").splitlines()
            assert len(written_lines) == EXPECTED_PROBE_COUNT


if __name__ == "__main__":
    unittest.main()
