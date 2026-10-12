# Copyright (c) 2026 Textbelt SMS contributors
"""Durable admission rejects repeats across restarts and failed writes."""

import asyncio
import copy
import json
import threading
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers.storage import Store, WriteError, json_util

from custom_components.textbelt_sms import state, webhook
from custom_components.textbelt_sms.sender import PartResult, SendResult
from tests.test_webhook import request

_REAL_STORE_ASYNC_WRITE = Store._async_write_data  # noqa: SLF001 - real hook before HA fixtures
_REAL_STORE_PREPARED_WRITE = Store._write_prepared_data  # noqa: SLF001 - real atomic disk hook


class Disk:
    """Controlled disk transport boundary."""

    def __init__(self) -> None:
        """Init  ."""
        self.data = None
        self.fail = False

    async def async_load(self) -> dict | None:
        """Async load."""
        return copy.deepcopy(self.data)

    async def async_save(self, data: dict) -> None:
        """Async save."""
        if self.fail:
            message = "disk unavailable"
            raise OSError(message)
        self.data = copy.deepcopy(data)


async def verified(
    timestamp: str = "1000", text: str = "private transcript"
) -> webhook.VerifiedReply:
    """Sign a realistic private reply fixture."""
    body = json.dumps(
        {"textId": "old", "fromNumber": "+15551234567", "text": text}
    ).encode()
    return await webhook.async_verify_reply(
        request(body, timestamp), api_key="secret", entry_id="entry", now=int(timestamp)
    )


def make_state(hass: HomeAssistant, disk: Disk, clock: list[int]) -> state.ReplyState:
    """Make state."""
    with patch.object(state, "_DurableStore", return_value=disk):
        return state.ReplyState(hass, "entry", clock=lambda: clock[0])


@pytest.mark.asyncio
async def test_restore_correlation_all_accepted_parts_no_transcripts(
    hass: HomeAssistant,
) -> None:
    """Test restore correlation all accepted parts no transcripts."""
    disk, clock = Disk(), [1000]
    obj = make_state(hass, disk, clock)
    result = SendResult(
        (
            PartResult(0, "old", "accepted"),
            PartResult(1, "new", "accepted"),
            PartResult(2, "uncertain", "unknown"),
        ),
        3,
        "partial",
    )
    obj.record_send_result(result, "+1 (555) 123-4567")
    await obj.async_flush()
    assert obj.correlates("old", "+15551234567")
    assert obj.correlates("new", "+15551234567")
    assert not obj.correlates("uncertain", "+15551234567")
    assert not obj.correlates("old", "+15551234568")
    assert await obj.async_claim(await verified())
    restored = make_state(hass, disk, clock)
    await restored.async_load()
    assert restored.is_duplicate(await verified())
    assert restored.correlates("old", "+15551234567")
    assert "private transcript" not in json.dumps(disk.data)
    assert "secret" not in json.dumps(disk.data)


@pytest.mark.asyncio
async def test_packet_replay_outlives_body_fallback(hass: HomeAssistant) -> None:
    """Test packet replay outlives body fallback."""
    disk, clock = Disk(), [1000]
    obj = make_state(hass, disk, clock)
    a = await verified()
    assert await obj.async_claim(a)
    clock[0] = 1121
    assert obj.is_duplicate(a)
    b = await verified("1121")
    assert not obj.is_duplicate(b)
    assert await obj.async_claim(b)
    assert not await obj.async_claim(await verified("1122"))
    clock[0] = 1901
    assert not obj.is_duplicate(a)


@pytest.mark.asyncio
async def test_concurrent_claims_and_failed_save_fail_closed(
    hass: HomeAssistant,
) -> None:
    """Test concurrent claims and failed save fail closed."""
    disk, clock = Disk(), [1000]
    obj = make_state(hass, disk, clock)
    reply = await verified()
    assert sorted(
        await asyncio.gather(obj.async_claim(reply), obj.async_claim(reply))
    ) == [False, True]
    disk.fail = True
    with pytest.raises(state.ReplyStorageError, match="durable"):
        await obj.async_claim(await verified(text="different"))
    disk.fail = False
    assert await obj.async_claim(await verified(text="different"))


@pytest.mark.asyncio
async def test_prune_invalid_restore_and_sender_caps(hass: HomeAssistant) -> None:
    """Test prune invalid restore and sender caps."""
    disk, clock = Disk(), [1000]
    disk.data = {
        "outgoing": [{"text_id": True, "phone": "+15551234567", "sent_at": 1000}],
        "duplicates": [],
        "packets": [],
    }
    obj = make_state(hass, disk, clock)
    await obj.async_load()
    assert not obj.correlates("True", "+15551234567")
    for index in range(101):
        obj.record_send_result(
            SendResult((PartResult(0, str(index), "accepted"),), 1, "accepted"),
            "+15551234567",
            sent_at=1000 + index,
        )
    assert not obj.correlates("0", "+15551234567")
    assert obj.correlates("100", "+15551234567")
    clock[0] = 605900
    assert not obj.correlates("100", "+15551234567")


@pytest.mark.asyncio
async def test_exact_packet_suppressed_at_last_accepted_second(
    hass: HomeAssistant,
) -> None:
    """Test exact packet suppressed at last accepted second."""
    disk, clock = Disk(), [1000]
    obj = make_state(hass, disk, clock)
    reply = await verified()
    assert await obj.async_claim(reply)
    clock[0] = 1900
    assert obj.is_duplicate(reply)


@pytest.mark.asyncio
async def test_hostile_storage_integer_is_discarded(hass: HomeAssistant) -> None:
    """Test hostile storage integer is discarded."""
    disk, clock = Disk(), [1000]
    disk.data = {
        "outgoing": [{"text_id": "x", "phone": "+15551234567", "sent_at": 10**400}]
    }
    obj = make_state(hass, disk, clock)
    await obj.async_load()
    assert not obj.correlates("x", "+15551234567")


@pytest.mark.parametrize("error_kind", ["write", "serialization"])
@pytest.mark.asyncio
async def test_real_ha_store_write_failure_prevents_admission(
    hass: HomeAssistant, error_kind: str
) -> None:
    """Catch HA Store swallowing disk and serialization errors before admission."""

    async def unavailable(*_args: object) -> None:
        """Fail only the real Store disk/serialization boundary."""
        message = "unavailable"
        if error_kind == "write":
            raise WriteError(message)
        raise json_util.SerializationError(message)

    obj = state.ReplyState(hass, "entry", clock=lambda: 1000)
    with (
        patch.object(Store, "_async_write_data", unavailable),
        pytest.raises(state.ReplyStorageError, match="durable"),
    ):
        await obj.async_claim(await verified())


@pytest.mark.asyncio
async def test_real_ha_store_restore_preserves_replay(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """Exercise real HA Store serialization and reload with metadata only."""
    obj = state.ReplyState(hass, "entry", clock=lambda: 1000)
    reply = await verified()
    assert await obj.async_claim(reply)
    restored = state.ReplyState(hass, "entry", clock=lambda: 1121)
    await restored.async_load()
    assert restored.is_duplicate(reply)
    assert "private transcript" not in json.dumps(hass_storage)


@pytest.mark.asyncio
async def test_deferred_stop_save_cannot_admit(hass: HomeAssistant) -> None:
    """Forbid execution when HA defers persistence until final shutdown write."""
    hass.set_state(CoreState.stopping)
    obj = state.ReplyState(hass, "entry", clock=lambda: 1000)
    with pytest.raises(state.ReplyStorageError, match="durable"):
        await obj.async_claim(await verified())


@pytest.mark.asyncio
async def test_cancelled_claim_never_admits_and_flush_waits(
    hass: HomeAssistant,
) -> None:
    """Cancel during disk admission and serialize the subsequent flush."""

    class PausedDisk(Disk):
        """Pause the actual persistence boundary."""

        async def async_save(self, data: dict) -> None:
            """Hold a save until released or cancelled."""
            entered.set()
            await release.wait()
            await super().async_save(data)

    entered, release = asyncio.Event(), asyncio.Event()
    disk, clock = PausedDisk(), [1000]
    obj = make_state(hass, disk, clock)
    reply = await verified()
    task = asyncio.create_task(obj.async_claim(reply))
    await entered.wait()
    flush = asyncio.create_task(obj.async_flush())
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    await flush
    assert not obj.is_duplicate(reply)
    assert await obj.async_claim(reply)


@pytest.mark.asyncio
async def test_restore_enforces_global_caps_and_lookup_expiry(
    hass: HomeAssistant,
) -> None:
    """Drop old correlations and digests beyond global capacity on restore."""
    disk, clock = Disk(), [2000]
    disk.data = {
        "outgoing": [
            {"text_id": str(i), "phone": f"+1555123{i // 100:04d}", "sent_at": 1000 + i}
            for i in range(1001)
        ],
        "duplicates": [
            {"digest": f"{i:064x}", "expires_at": 2001 + i / 100} for i in range(1001)
        ],
        "packets": [
            {"digest": f"{i:064x}", "expires_at": 2001 + i / 100} for i in range(1001)
        ],
    }
    obj = make_state(hass, disk, clock)
    await obj.async_load()
    await obj.async_flush()
    assert not obj.correlates("0", "+15551230000")
    assert obj.correlates("1000", "+15551230010")
    expected_count = 1000
    assert (
        len(disk.data["outgoing"])
        == len(disk.data["duplicates"])
        == len(disk.data["packets"])
        == expected_count
    )
    clock[0] = 606801
    assert not obj.correlates("1000", "+15551230010")


@pytest.mark.asyncio
async def test_duplicate_checks_do_not_extend_body_expiry(hass: HomeAssistant) -> None:
    """A duplicate near expiry cannot extend identical resend suppression."""
    disk, clock = Disk(), [1000]
    obj = make_state(hass, disk, clock)
    assert await obj.async_claim(await verified())
    clock[0] = 1119
    assert not await obj.async_claim(await verified("1119"))
    clock[0] = 1120
    assert await obj.async_claim(await verified("1120"))


@pytest.mark.parametrize("fail_first", [False, True])
@pytest.mark.asyncio
async def test_cancelled_real_executor_write_settles_before_next_claim_and_flush(
    hass: HomeAssistant,
    *,
    fail_first: bool,
) -> None:
    """An abandoned older atomic write must never replace a confirmed new claim."""
    entered, release = threading.Event(), threading.Event()
    first_reply = await verified(text="first")
    second_reply = await verified(text="second")

    def delayed_write(store: Store, mode: str, data: str | bytes) -> None:
        """Pause only the first executor write before real atomic replacement."""
        payload = json.loads(data)["data"]
        if any(
            row["digest"] == first_reply.packet_digest for row in payload["packets"]
        ):
            entered.set()
            if not release.wait(5):
                message = "test executor release timed out"
                raise RuntimeError(message)
            if fail_first:
                message = "unavailable first write"
                raise WriteError(message)
        _REAL_STORE_PREPARED_WRITE(store, mode, data)

    obj = state.ReplyState(hass, "entry", clock=lambda: 1000)
    tasks = []
    with (
        patch.object(Store, "_async_write_data", _REAL_STORE_ASYNC_WRITE),
        patch.object(Store, "_write_prepared_data", delayed_write),
    ):
        try:
            first = asyncio.create_task(obj.async_claim(first_reply))
            tasks.append(first)
            assert await asyncio.to_thread(entered.wait, 5)
            first.cancel()
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            assert not first.done()
            # Repeated shutdown cancellation must still keep ownership of disk I/O.
            first.cancel()
            second = asyncio.create_task(obj.async_claim(second_reply))
            flush = asyncio.create_task(obj.async_flush())
            tasks.extend((second, flush))
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            assert not first.done()
            assert not second.done()
            assert not flush.done()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await first
            assert await second
            await flush
            path = Path(hass.config.path(".storage", "textbelt_sms.reply.entry"))
            saved = json.loads(await asyncio.to_thread(path.read_text))["data"]
            assert any(
                row["digest"] == second_reply.packet_digest for row in saved["packets"]
            )
            assert not any(
                row["digest"] == first_reply.packet_digest for row in saved["packets"]
            )
        finally:
            release.set()
            await asyncio.gather(*tasks, return_exceptions=True)
