# Copyright (c) 2026 Textbelt SMS contributors
"""Run local native SMS checks inside pinned HA using its aiohttp dependency."""

# Fixture assertions and compact local API closures use dynamic JSON schemas.
# ruff: noqa: ANN001, ANN201, ANN202, PLR2004, ASYNC240
# Small bounded artifact files are synchronous in this standalone local CLI.
from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from pathlib import Path

import aiohttp
from exercise_api import callback_path, decode_expected_response, signed_headers
from fixture_files import wait_for_migrated_entry

BASE = "http://127.0.0.1:8123"
STUB = "http://textbelt:8080"
PHONE = "+15551234567"
OTHER = "+15557654321"
STATE = Path("/config/stage4-state.json")
REPORT = Path("/config/stage4-evidence.json")


async def run(token, phase):  # noqa: PLR0915, C901, PLR0912 -- explicit acceptance matrix.
    """Assert actual HTTP sends, registered agent calls and pipeline debug events."""
    if os.environ.get("LIVE_SMOKE", "0") != "0":
        message = "Native smoke is strictly offline"
        raise RuntimeError(message)
    evidence = (
        json.loads(REPORT.read_text())
        if REPORT.exists()
        else {"checks": [], "runs": []}
    )
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30)
    ) as session:

        async def http(path, payload=None, *, stub=False, expected=200):
            async with session.request(
                "POST" if payload is not None else "GET",
                (STUB if stub else BASE) + path,
                json=payload,
                headers={} if stub else {"Authorization": f"Bearer {token}"},
            ) as response:
                assert response.status == expected, (
                    path,
                    response.status,
                    await response.text(),
                )
                raw = await response.read()
                return decode_expected_response(
                    raw, status=response.status, expected=expected
                )

        async with session.ws_connect(BASE + "/api/websocket") as ws:
            assert (await ws.receive_json())["type"] == "auth_required"
            await ws.send_json({"type": "auth", "access_token": token})
            assert (await ws.receive_json())["type"] == "auth_ok"
            counter = 0
            events = []

            async def command(kind, **fields: object):
                nonlocal counter
                counter += 1
                await ws.send_json({"id": counter, "type": kind, **fields})
                while True:
                    result = await ws.receive_json()
                    if result["type"] == "event":
                        events.append(result["event"])
                        continue
                    if result.get("id") == counter:
                        assert result.get("success"), result
                        return result.get("result")

            await command("subscribe_events", event_type="textbelt_sms_reply")

            async def snapshot():
                for _ in range(100):
                    async with session.get(
                        BASE + "/api/textbelt_smoke_agent/snapshot",
                        headers={"Authorization": f"Bearer {token}"},
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                    await asyncio.sleep(0.1)
                message = "Smoke agent snapshot unavailable"
                raise AssertionError(message)

            async def requests():
                return (await http("/requests", stub=True))["requests"]

            async def options(*, enabled):
                entries = await http("/api/config/config_entries/entry")
                entry = next(e for e in entries if e["domain"] == "textbelt_sms")
                flow = await http(
                    "/api/config/config_entries/options/flow",
                    {"handler": entry["entry_id"]},
                )
                result = await http(
                    "/api/config/config_entries/options/flow/" + flow["flow_id"],
                    {
                        "assist_enabled": enabled,
                        "pipeline_id": "preferred",
                        "authorized_senders": PHONE + "\n" + OTHER,
                        "notification_recipients": PHONE,
                        "conversation_timeout": 1800,
                    },
                )
                assert result["type"] == "create_entry", result
                for _ in range(100):
                    entries = await http("/api/config/config_entries/entry")
                    if (
                        next(e for e in entries if e["domain"] == "textbelt_sms")[
                            "state"
                        ]
                        == "loaded"
                    ):
                        await asyncio.sleep(1)
                        return
                    await asyncio.sleep(0.1)
                message = "Options reload did not finish"
                raise AssertionError(message)

            async def send(service, payload, expected=200):
                return await http(
                    "/api/services/" + service, payload, expected=expected
                )

            async def post(  # noqa: PLR0913 -- fixture transport controls.
                path, body, expected=200, *, signed=True, timestamp=None, tampered=False
            ):
                raw = body if isinstance(body, bytes) else json.dumps(body).encode()
                headers = (
                    signed_headers(raw, "smoke-test-key", timestamp)
                    if signed
                    else {"Content-Type": "application/json"}
                )
                if tampered:
                    headers["X-textbelt-signature"] = "0" * 64
                async with session.post(
                    BASE + path, data=raw, headers=headers
                ) as response:
                    assert response.status == expected, (
                        response.status,
                        expected,
                        await response.text(),
                    )
                return raw

            async def debug_ids(pipeline):
                result = await command(
                    "assist_pipeline/pipeline_debug/list", pipeline_id=pipeline
                )
                return {r["pipeline_run_id"] for r in result["pipeline_runs"]}

            async def stable_counts(pipelines):
                await asyncio.sleep(0.5)
                ids = [await debug_ids(p) for p in pipelines]
                return (
                    len((await snapshot())["calls"]),
                    len(await requests()),
                    len(events),
                    ids,
                )

            async def turn(path, body, pipeline):
                old_calls = len((await snapshot())["calls"])
                old_requests = len(await requests())
                old_ids = await debug_ids(pipeline)
                await post(path, body)
                for _ in range(150):
                    snap = await snapshot()
                    reqs = await requests()
                    if (
                        len(snap["calls"]) == old_calls + 1
                        and len(reqs) > old_requests
                        and snap["active"] == 0
                    ):
                        break
                    await asyncio.sleep(0.1)
                else:
                    message = "Native turn did not finish"
                    raise AssertionError(message)
                # Let response sends settle after agent completion.
                await asyncio.sleep(0.5)
                snap = await snapshot()
                reqs = await requests()
                ids = await debug_ids(pipeline)
                added = ids - old_ids
                assert len(added) == 1, added
                debug = await command(
                    "assist_pipeline/pipeline_debug/get",
                    pipeline_id=pipeline,
                    pipeline_run_id=added.pop(),
                )
                types = [e["type"] for e in debug["events"]]
                assert types == [
                    "run-start",
                    "intent-start",
                    "intent-end",
                    "run-end",
                ], debug
                record = snap["calls"][-1]
                assert record["user_id"] is None
                assert all(
                    r["phone"] == body["fromNumber"] for r in reqs[old_requests:]
                )
                assert record["speech"] in " ".join(
                    r["message"] for r in reqs[old_requests:]
                ) or body["text"].strip().startswith("long")
                evidence["runs"].append(debug)
                evidence["checks"].append(body["text"])
                REPORT.write_text(json.dumps(evidence, indent=2))
                return record

            if phase == "initial":

                async def migration_runtime():
                    return await http("/api/config/config_entries/entry")

                def migration_storage():
                    return json.loads(
                        Path("/config/.storage/core.config_entries").read_text()
                    )

                migrated = await wait_for_migrated_entry(
                    migration_runtime, migration_storage
                )
                assert migrated["version"] == 2
                assert migrated["options"]["assist_enabled"] is False
                assert migrated["options"]["smoke_unrelated"] == "preserved"
                evidence["checks"].append("key-only migration/native disabled")
                for label in ("A", "B"):
                    flow = await http(
                        "/api/config/config_entries/flow",
                        {"handler": "textbelt_smoke_agent"},
                    )
                    result = await http(
                        "/api/config/config_entries/flow/" + flow["flow_id"],
                        {"label": label},
                    )
                    assert result["type"] == "create_entry"
                for _ in range(100):
                    snap = await snapshot()
                    if len(snap["agents"]) == 2:
                        break
                    await asyncio.sleep(0.1)
                pipelines = []
                for label in ("A", "B"):
                    pipeline = await command(
                        "assist_pipeline/pipeline/create",
                        name=label,
                        conversation_engine=snap["agents"][label],
                        conversation_language="en",
                        language="en",
                        stt_engine=None,
                        stt_language=None,
                        tts_engine=None,
                        tts_language=None,
                        tts_voice=None,
                        wake_word_entity=None,
                        wake_word_id=None,
                        prefer_local_intents=False,
                    )
                    pipelines.append(pipeline["id"])
                a, b = pipelines
                await command("assist_pipeline/pipeline/set_preferred", pipeline_id=a)
                await options(enabled=True)
                before = len(await requests())
                await send("textbelt_sms/start_conversation", {"phone": PHONE})
                reqs = await requests()
                assert len(reqs) > before
                assert all(
                    "Home Assistant" in r["message"] or "(2/" in r["message"]
                    for r in reqs[before:]
                )
                ledger = (await http("/outcomes", stub=True))["outcomes"]
                text_id = ledger[-1]["textId"]
                path = callback_path(reqs[-1]["replyWebhookUrl"])
                assert not (await snapshot())["calls"]
                body = {
                    "textId": text_id,
                    "fromNumber": PHONE,
                    "text": "remember alpha",
                }
                first = await turn(path, body, a)
                body["text"] = "recall"
                second = await turn(path, body, a)
                assert first["conversation_id"] == second["conversation_id"]
                assert first["context_id"] != second["context_id"]
                assert second["turn"] == 2
                assert second["speech"].endswith("alpha")
                counts = await stable_counts(pipelines)
                await post(path, body)  # identical raw body, newly signed
                assert await stable_counts(pipelines) == counts
                for text in ("STOP", "START", "HELP"):
                    await post(path, {**body, "text": text})
                    assert await stable_counts(pipelines) == counts
                for rejected, status, kwargs in (
                    ({**body, "text": "unsigned"}, 401, {"signed": False}),
                    ({**body, "text": "tampered"}, 401, {"tampered": True}),
                    (
                        {**body, "text": "stale"},
                        401,
                        {"timestamp": str(int(time.time()) - 1000)},
                    ),
                    (
                        {**body, "text": "future"},
                        401,
                        {"timestamp": str(int(time.time()) + 1000)},
                    ),
                    ({**body, "textId": "unknown", "text": "unknown"}, 403, {}),
                    ({**body, "fromNumber": OTHER, "text": "mismatch"}, 403, {}),
                    ({**body, "text": "x" * 4097}, 400, {}),
                    (b"x" * 16385, 413, {}),
                    (b'{"textId":"1","textId":"2"}', 400, {}),
                    (b"{", 400, {}),
                ):
                    await post(path, rejected, status, **kwargs)
                    assert await stable_counts(pipelines) == counts
                # Correlate this sender correctly so only the allowlist can reject it.
                unauthorized_phone = "+15550000000"
                before_seed = await stable_counts(pipelines)
                await send(
                    "textbelt_sms/send_sms",
                    {
                        "phone": unauthorized_phone,
                        "message": "Synthetic unauthorized sender seed",
                    },
                )
                seeded_requests = await requests()
                assert len(seeded_requests) == before_seed[1] + 1
                assert seeded_requests[-1]["phone"] == unauthorized_phone
                unauthorized_path = callback_path(
                    seeded_requests[-1]["replyWebhookUrl"]
                )
                assert unauthorized_path == path
                seeded_ledger = (await http("/outcomes", stub=True))["outcomes"]
                assert seeded_ledger[-1]["accepted"] is True
                unauthorized_id = seeded_ledger[-1]["textId"]
                counts = await stable_counts(pipelines)
                assert counts[0] == before_seed[0]
                assert counts[2:] == before_seed[2:]
                await post(
                    unauthorized_path,
                    {
                        "textId": unauthorized_id,
                        "fromNumber": unauthorized_phone,
                        "text": "correlated unauthorized",
                    },
                    403,
                )
                assert await stable_counts(pipelines) == counts
                evidence["checks"].append("correlated unauthorized sender rejected")
                await send("textbelt_sms/start_conversation", {"phone": OTHER})
                other_id = (await http("/outcomes", stub=True))["outcomes"][-1][
                    "textId"
                ]
                isolated = await turn(
                    path, {"textId": other_id, "fromNumber": OTHER, "text": "recall"}, a
                )
                assert isolated["turn"] == 1
                assert isolated["speech"].endswith("none")
                assert isolated["conversation_id"] != first["conversation_id"]
                await command("assist_pipeline/pipeline/set_preferred", pipeline_id=b)
                changed = await turn(path, {**body, "text": "preferred change"}, b)
                assert changed["agent"] == "B"
                assert changed["turn"] == 1
                assert changed["conversation_id"] != first["conversation_id"]
                counts = await stable_counts(pipelines)
                await post(path, {**body, "text": "/new"})
                new_counts = await stable_counts(pipelines)
                assert new_counts[0] == counts[0]
                assert new_counts[1] > counts[1]
                assert new_counts[3] == counts[3]
                reset = await turn(path, {**body, "text": "after new"}, b)
                assert reset["turn"] == 1
                assert reset["conversation_id"] != changed["conversation_id"]
                counts = await stable_counts(pipelines)
                await post(
                    "/api/webhook/textbelt_sms_reply",
                    {**body, "text": "legacy event", "data": "synthetic"},
                )
                after = await stable_counts(pipelines)
                assert after[0:2] == counts[0:2]
                assert after[2] == counts[2] + 1
                assert after[3] == counts[3]
                assert events[-1]["data"]["text"] == "legacy event"
                await post("/api/webhook/textbelt_sms_reply", body, 401, signed=False)
                await options(enabled=False)
                counts = await stable_counts(pipelines)
                await post(path, {**body, "text": "disabled event"})
                after = await stable_counts(pipelines)
                assert after[0:2] == counts[0:2]
                assert after[2] == counts[2] + 1
                assert after[3] == counts[3]
                before = len(await requests())
                await send(
                    "textbelt_sms/send_sms",
                    {"phone": "5551234567", "message": "legacy destination"},
                )
                reqs = await requests()
                assert len(reqs) == before + 1
                assert reqs[-1]["replyWebhookUrl"].endswith("/textbelt_sms_reply")
                await options(enabled=True)
                notify_states = await http("/api/states")
                notify_id = next(
                    s["entity_id"]
                    for s in notify_states
                    if s["entity_id"].startswith("notify.textbelt_sms")
                )
                timestamp_before = (await http("/api/states/" + notify_id))["state"]
                await http("/plan", ["success", "provider_reject"], stub=True)
                before = len(await requests())
                await send(
                    "notify/send_message",
                    {
                        "entity_id": notify_id,
                        "message": "Synthetic notification partial. " * 12,
                    },
                    expected=500,
                )
                assert len(await requests()) == before + 2
                assert (await http("/api/states/" + notify_id))[
                    "state"
                ] == timestamp_before
                evidence["checks"].append("failed notify timestamp unchanged")
                # A normal long turn establishes ordered successful multipart output.
                before = len(await requests())
                await turn(path, {**body, "text": "long success"}, b)
                prepared = (await requests())[before:]
                assert 1 < len(prepared) <= 5
                for index, part in enumerate(prepared, 1):
                    assert part["message"].startswith(f"({index}/{len(prepared)}) ")
                    septets = sum(
                        2 if char in "^{}\\[~]|" else 1 for char in part["message"]
                    )
                    assert septets <= 160
                    assert all(ord(char) < 128 for char in part["message"])
                # Lookup failures and recovery must never add send attempts.
                before = len(await requests())
                for prefix, entity in (
                    ("status", "sensor.textbelt_sms_last_message_status"),
                    ("quota-mode", "sensor.textbelt_sms_quota_remaining"),
                ):
                    for mode in (
                        "http_failure",
                        "malformed_json",
                        "delivered" if prefix == "status" else "success",
                    ):
                        await http(f"/{prefix}/{mode}", {}, stub=True)
                        await send("homeassistant/update_entity", {"entity_id": entity})
                        expected = (
                            "unavailable"
                            if mode in ("http_failure", "malformed_json")
                            else (
                                "delivered"
                                if prefix == "status"
                                else str(
                                    (await http("/quota/smoke-test-key", stub=True))[
                                        "quotaRemaining"
                                    ]
                                )
                            )
                        )
                        for _ in range(100):
                            if (await http("/api/states/" + entity))[
                                "state"
                            ] == expected:
                                break
                            await asyncio.sleep(0.1)
                        assert (await http("/api/states/" + entity))[
                            "state"
                        ] == expected
                        assert len(await requests()) == before
                evidence["checks"].extend(
                    [
                        "successful ordered multipart",
                        "quota/status independent failure/recovery",
                    ]
                )
                # Response failures must not repeat the pipeline or retry sends.
                for failure in ("provider_reject", "accept_disconnect"):
                    quota_before = (await http("/quota/smoke-test-key", stub=True))[
                        "quotaRemaining"
                    ]
                    await http("/plan", ["success", failure], stub=True)
                    before = len(await requests())
                    await turn(
                        path,
                        {
                            **body,
                            "text": "long" if failure == "provider_reject" else "long ",
                        },
                        b,
                    )
                    # long plus whitespace must also trigger the fixture's long speech.
                    ledger = (await http("/outcomes", stub=True))["outcomes"]
                    assert len(await requests()) == before + 2
                    assert ledger[-1]["kind"] == failure
                    known_ids = [ledger[-2]["textId"]]
                    expected_outcome = (
                        "partial" if failure == "provider_reject" else "unknown"
                    )
                    expected_state = (
                        "failed" if failure == "provider_reject" else "unknown"
                    )
                    visible = await http(
                        "/api/states/sensor.textbelt_sms_last_message_status"
                    )
                    assert visible["state"] == expected_state
                    attrs = visible["attributes"]
                    assert attrs["submission_outcome"] == expected_outcome
                    assert attrs["text_ids"] == known_ids
                    assert attrs["text_id"] == known_ids[-1]
                    assert set(attrs["part_statuses"]) == set(known_ids)
                    assert attrs["total_parts"] == len(prepared)
                    debit = 1 if failure == "provider_reject" else 2
                    quota_after = (await http("/quota/smoke-test-key", stub=True))[
                        "quotaRemaining"
                    ]
                    assert quota_after == quota_before - debit
                    assert ledger[-1]["quotaRemaining"] == quota_after
                    await send(
                        "homeassistant/update_entity",
                        {"entity_id": "sensor.textbelt_sms_quota_remaining"},
                    )
                    for _ in range(100):
                        visible_quota = await http(
                            "/api/states/sensor.textbelt_sms_quota_remaining"
                        )
                        if visible_quota["state"] == str(quota_after):
                            break
                        await asyncio.sleep(0.1)
                    assert visible_quota["state"] == str(quota_after)
                    metadata_files = list(
                        Path("/config/.storage").glob("textbelt_sms.reply.*")
                    )
                    assert len(metadata_files) == 1
                    metadata = json.loads(metadata_files[0].read_text())["data"]
                    retained_ids = {row["text_id"] for row in metadata["outgoing"]}
                    assert set(known_ids) <= retained_ids
                    if failure == "accept_disconnect":
                        assert ledger[-1]["textId"] not in retained_ids
                    evidence.setdefault("failure_accounting", []).append(
                        {
                            "fixture": failure,
                            "sensor": visible,
                            "known_ids": known_ids,
                            "quota_before": quota_before,
                            "quota_after": quota_after,
                            "expected_debit": debit,
                        }
                    )
                    counts = await stable_counts(pipelines)
                    await post(
                        path,
                        {
                            **body,
                            "text": "long" if failure == "provider_reject" else "long ",
                        },
                    )
                    assert await stable_counts(pipelines) == counts
                    if failure == "accept_disconnect":
                        await post(
                            path,
                            {
                                **body,
                                "textId": ledger[-1]["textId"],
                                "text": "uncertain ID",
                            },
                            403,
                        )
                evidence["checks"].extend(
                    [
                        "greeting",
                        "replay",
                        "controls",
                        "rejections",
                        "sender isolation",
                        "preferred change",
                        "/new",
                        "legacy",
                        "disabled",
                        "partial/unknown no retry",
                    ]
                )
                STATE.write_text(
                    json.dumps(
                        {
                            "path": path,
                            "body": body,
                            "pipelines": pipelines,
                            "old_cid": reset["conversation_id"],
                        }
                    )
                )
            elif phase == "hold":
                state = json.loads(STATE.read_text())
                raw1 = await post(state["path"], {**state["body"], "text": "hold"})
                for _ in range(100):
                    snap = await snapshot()
                    if snap["active"] == 1:
                        break
                    await asyncio.sleep(0.1)
                assert snap["active"] == 1
                raw2 = await post(state["path"], {**state["body"], "text": "queued"})
                await asyncio.sleep(0.5)
                assert (await snapshot())["calls"][-1]["text"] == "hold"
                state.update(
                    boot_id=snap["boot_id"],
                    held=[raw1.decode(), raw2.decode()],
                    restart_at=time.time(),
                    requests=len(await requests()),
                )
                STATE.write_text(json.dumps(state))
            else:
                state = json.loads(STATE.read_text())
                assert time.time() - state["restart_at"] < 110, (
                    "Restart exceeded duplicate-window test budget"
                )
                snap = await snapshot()
                assert snap["boot_id"] != state["boot_id"]
                assert not snap["calls"]
                assert len(await requests()) == state["requests"]
                for raw in state["held"]:
                    await post(state["path"], raw.encode())
                counts = await stable_counts(state["pipelines"])
                assert counts[0] == 0
                assert counts[1] == state["requests"]
                fresh = await turn(
                    state["path"],
                    {**state["body"], "text": "fresh after restart"},
                    state["pipelines"][1],
                )
                assert fresh["turn"] == 1
                assert fresh["conversation_id"] != state["old_cid"]
                assert (
                    callback_path((await requests())[-1]["replyWebhookUrl"])
                    == state["path"]
                )
                evidence["checks"].append(
                    "restart no replay/stable webhook/new session"
                )
            evidence["snapshot"] = await snapshot()
            evidence["requests"] = await requests()
            evidence["outcomes"] = (await http("/outcomes", stub=True))["outcomes"]
            evidence["events"] = events
            REPORT.write_text(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase", choices=["initial", "hold", "restart"], default="initial"
    )
    args = parser.parse_args()
    token = input().strip()  # token via stdin, never command/log/artifact
    asyncio.run(run(token, args.phase))
