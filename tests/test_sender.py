# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""Whole-batch sending and uncertain outcome tests."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from custom_components.textbelt_sms.api import (
    TextbeltApiClientError,
    TextbeltApiClientUnknownOutcomeError,
)
from custom_components.textbelt_sms.models import (
    MessagePreparationError,
    PreparedMessage,
)
from custom_components.textbelt_sms.sender import TextbeltSender


async def test_sender_serializes_complete_batches() -> None:
    """Concurrent batches retain IDs without part interleaving."""
    started, release = asyncio.Event(), asyncio.Event()
    calls = []

    async def post(phone: str, text: str, _webhook: str | None = None) -> dict:
        calls.append((phone, text))
        if len(calls) == 1:
            started.set()
            await release.wait()
        return {"success": True, "textId": len(calls)}

    client = AsyncMock()
    client.async_send_sms.side_effect = post
    sender = TextbeltSender(client)
    first = asyncio.create_task(sender.async_send("+1", "a" * 200))
    await started.wait()
    second = asyncio.create_task(sender.async_send("+2", "b" * 200))
    await asyncio.sleep(0)
    release.set()
    a, b = await asyncio.gather(first, second)
    assert [phone for phone, _ in calls] == ["+1", "+1", "+2", "+2"]
    assert a.text_ids == ("1", "2")
    assert b.text_ids == ("3", "4")
    assert a.outcome == b.outcome == "accepted"


@pytest.mark.parametrize(
    ("response", "outcome"),
    [
        ({"success": False}, "partial"),
        ({"success": True}, "unknown"),
        ({"success": "yes", "textId": "bad"}, "unknown"),
        ([], "unknown"),
        (TextbeltApiClientError("rejected"), "partial"),
    ],
)
async def test_sender_retains_ids_and_stops_after_failure(
    response: dict | list | Exception, outcome: str
) -> None:
    """Failed submission preserves accepted IDs and stops the batch."""
    client = AsyncMock()
    client.async_send_sms.side_effect = [{"success": True, "textId": "one"}, response]
    sender = TextbeltSender(client)
    result = await sender.async_send("legacy phone", "a" * 400)
    assert result.text_ids == ("one",)
    assert result.accepted_parts == 1
    expected_parts = 3
    assert result.total_parts == expected_parts
    assert result.outcome == outcome
    expected_attempts = 2
    assert len(result.parts) == expected_attempts
    assert client.async_send_sms.await_count == expected_attempts


async def test_sender_rejects_all_invalid_text_before_first_post() -> None:
    """Submission respects validation and lifecycle boundaries."""
    client = AsyncMock()
    sender = TextbeltSender(client)
    with pytest.raises(MessagePreparationError):
        await sender.async_send("+1", "a" * 170 + "\u6f22")
    client.async_send_sms.assert_not_awaited()


async def test_sender_cancellation_retains_ids_and_marks_inflight_unknown() -> None:
    """Submission respects validation and lifecycle boundaries."""
    client = AsyncMock()
    started = asyncio.Event()

    async def post(_phone: str, _text: str, _webhook: str | None = None) -> dict:
        if client.async_send_sms.await_count == 1:
            return {"success": True, "textId": "one"}
        started.set()
        await asyncio.Event().wait()
        return {"success": True, "textId": "unreachable"}

    client.async_send_sms.side_effect = post
    sender = TextbeltSender(client)
    task = asyncio.create_task(sender.async_send("+1", "a" * 400))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert sender.last_result.text_ids == ("one",)
    assert sender.last_result.outcome == "unknown"
    assert sender.last_result.parts[-1].outcome == "unknown"
    expected_attempts = 2
    assert client.async_send_sms.await_count == expected_attempts


async def test_sender_unload_stops_future_parts_and_queued_batches() -> None:
    """Submission respects validation and lifecycle boundaries."""
    started, release = asyncio.Event(), asyncio.Event()
    client = AsyncMock()

    async def post(_phone: str, _text: str, _webhook: str | None = None) -> dict:
        started.set()
        await release.wait()
        return {"success": True, "textId": "one"}

    client.async_send_sms.side_effect = post
    sender = TextbeltSender(client)
    task = asyncio.create_task(sender.async_send("+1", "a" * 400))
    await started.wait()
    sender.shutdown()
    release.set()
    result = await task
    assert result.outcome == "partial"
    assert result.text_ids == ("one",)
    assert (await sender.async_send("+1", "again")).outcome == "rejected"
    assert client.async_send_sms.await_count == 1


@pytest.mark.parametrize(
    ("response", "outcome"),
    [
        ({"success": False}, "rejected"),
        ({"success": True, "textId": None}, "unknown"),
    ],
)
async def test_first_part_failure_is_visible_without_previous_ids(
    response: dict, outcome: str
) -> None:
    """First-part failures replace an earlier success and never retry."""
    client = AsyncMock()
    client.async_send_sms.side_effect = [{"success": True, "textId": "old"}, response]
    sender = TextbeltSender(client)
    await sender.async_send("+1", "old")
    result = await sender.async_send("+1", "a" * 400)
    assert sender.last_result is result
    assert result.text_ids == ()
    assert result.outcome == outcome
    assert len(result.parts) == 1
    expected_attempts = 2
    assert client.async_send_sms.await_count == expected_attempts


async def test_sender_unknown_api_outcome_is_not_retried() -> None:
    """Provider acceptance may precede transport failure; never repeat it."""
    client = AsyncMock()
    client.async_send_sms.side_effect = TextbeltApiClientUnknownOutcomeError("offline")
    sender = TextbeltSender(client)
    result = await sender.async_send("+1", "a" * 400)
    assert result.outcome == "unknown"
    assert result.parts[0].outcome == "unknown"
    assert result.text_ids == ()
    client.async_send_sms.assert_awaited_once()


@pytest.mark.parametrize(
    "parts", [(), ("valid", "a" * 161), ("valid", "\u6f22"), ("valid", "")]
)
async def test_sender_revalidates_every_completed_part(
    monkeypatch: pytest.MonkeyPatch, parts: tuple[str, ...]
) -> None:
    """Even faulty preparation output cannot send the first valid part."""
    monkeypatch.setattr(
        "custom_components.textbelt_sms.sender.prepare_message",
        lambda *_args, **_kwargs: PreparedMessage(parts, "source", shortened=False),
    )
    client = AsyncMock()
    sender = TextbeltSender(client)
    with pytest.raises(MessagePreparationError):
        await sender.async_send("+1", "source")
    assert sender.last_result.outcome == "rejected"
    client.async_send_sms.assert_not_awaited()
