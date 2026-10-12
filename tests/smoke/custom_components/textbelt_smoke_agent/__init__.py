# Copyright (c) 2026 Textbelt SMS contributors
"""Smoke-only conversation engine; never routes callbacks or sends SMS."""

# Disposable HA fixture uses HA callback argument conventions.
# ruff: noqa: ANN001, ANN201, ANN204
import asyncio
from uuid import uuid4

from homeassistant.components import conversation
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers import intent

DOMAIN = "textbelt_smoke_agent"


class Snapshot(HomeAssistantView):
    """Authenticated read-only synthetic execution evidence."""

    url = "/api/textbelt_smoke_agent/snapshot"
    name = "api:textbelt_smoke_agent:snapshot"
    requires_auth = True

    async def get(self, request):
        """Return fixture state only."""
        return self.json(request.app["hass"].data[DOMAIN])


async def async_setup(hass, _config):
    """Register the read-only snapshot once per HA boot."""
    hass.data[DOMAIN] = {
        "boot_id": uuid4().hex,
        "agents": {},
        "calls": [],
        "active": 0,
        "cancelled": 0,
    }
    hass.http.register_view(Snapshot())
    return True


class Agent(conversation.AbstractConversationAgent):
    """Deterministic volatile per-conversation memory."""

    def __init__(self, hass, entry):
        """Initialize volatile synthetic memory."""
        self.hass = hass
        self.label = entry.data["label"]
        self.histories = {}

    @property
    def supported_languages(self):
        """Support the language selected in the smoke pipelines."""
        return ["en"]

    async def async_process(self, user_input):
        """Record actual native pipeline input and produce bounded speech."""
        state = self.hass.data[DOMAIN]
        cid = user_input.conversation_id or uuid4().hex
        history = self.histories.setdefault(cid, {"turn": 0, "memory": "none"})
        history["turn"] += 1
        record = {
            "agent": self.label,
            "text": user_input.text,
            "conversation_id": cid,
            "context_id": user_input.context.id,
            "user_id": user_input.context.user_id,
            "turn": history["turn"],
        }
        state["calls"].append(record)
        state["calls"] = state["calls"][-100:]
        state["active"] += 1
        try:
            if user_input.text == "hold":
                await asyncio.Event().wait()
            if user_input.text.startswith("remember "):
                history["memory"] = user_input.text.removeprefix("remember ")
            speech = f"{self.label} turn {history['turn']} memory {history['memory']}"
            if user_input.text.strip().startswith("long"):
                speech = "Synthetic long reply. " * 18
            response = intent.IntentResponse(language=user_input.language)
            response.async_set_speech(speech)
            record["speech"] = speech
            return conversation.ConversationResult(response, cid)
        except asyncio.CancelledError:
            state["cancelled"] += 1
            raise
        finally:
            state["active"] -= 1


async def async_setup_entry(hass, entry):
    """Register through HA's supported agent API."""
    conversation.async_set_agent(hass, entry, Agent(hass, entry))
    hass.data[DOMAIN]["agents"][entry.data["label"]] = entry.entry_id
    return True


async def async_unload_entry(hass, entry):
    """Remove the fixture agent."""
    conversation.async_unset_agent(hass, entry)
    hass.data[DOMAIN]["agents"].pop(entry.data["label"], None)
    return True
