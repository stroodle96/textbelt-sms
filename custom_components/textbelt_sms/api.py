# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""API client for Textbelt SMS service."""

from __future__ import annotations

import os
from http import HTTPStatus
from typing import Any

import aiohttp

from .const import API_BASE_URL_ENV, DEFAULT_API_BASE_URL

AUTHENTICATION_ERROR = "Invalid API key or unauthorized."
INVALID_RESPONSE_ERROR = "Textbelt API returned an invalid response."


class TextbeltApiClientError(Exception):
    """Exception to indicate a general API error."""


class TextbeltApiClientCommunicationError(TextbeltApiClientError):
    """Exception to indicate a communication error."""


class TextbeltApiClientAuthenticationError(TextbeltApiClientError):
    """Exception to indicate an authentication error."""


class TextbeltApiClient:
    """API client for sending SMS via Textbelt."""

    def __init__(self, api_key: str, session: aiohttp.ClientSession) -> None:
        """Initialize the client with API key and aiohttp session."""
        self._api_key = api_key
        self._session = session
        base_url = os.getenv(API_BASE_URL_ENV, DEFAULT_API_BASE_URL).strip().rstrip("/")
        self._endpoint = f"{base_url}/text"

    async def async_send_sms(
        self, phone: str, message: str, webhook_url: str | None = None
    ) -> dict[str, Any]:
        """
        Send an SMS message using the Textbelt API.

        Optionally include a webhook URL for replies.

        Args:
            phone: The recipient's phone number (international format
                recommended).
            message: The SMS message text.
            webhook_url: Optional webhook URL to receive SMS replies.

        Returns:
            The JSON response from the API.

        Raises:
            TextbeltApiClientError: For general API errors.
            TextbeltApiClientCommunicationError: For network errors.

        """
        payload = {
            "phone": phone,
            "message": message,
            "key": self._api_key,
        }
        if webhook_url:
            payload["webhookUrl"] = webhook_url
        try:
            async with self._session.post(self._endpoint, data=payload) as response:
                if response.status in {HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN}:
                    raise TextbeltApiClientAuthenticationError(AUTHENTICATION_ERROR)
                if response.status >= HTTPStatus.BAD_REQUEST:
                    msg = f"Textbelt API returned HTTP {response.status}."
                    raise TextbeltApiClientError(msg)
                try:
                    data = await response.json()
                except (aiohttp.ClientError, TypeError, ValueError) as err:
                    raise TextbeltApiClientError(INVALID_RESPONSE_ERROR) from err
                if not isinstance(data, dict):
                    raise TextbeltApiClientError(INVALID_RESPONSE_ERROR)
                if not data.get("success", False):
                    msg = data.get("error", "Unknown error from Textbelt API.")
                    raise TextbeltApiClientError(str(msg))
                return data
        except (aiohttp.ClientError, TimeoutError) as err:
            msg = f"Network error: {err}"
            raise TextbeltApiClientCommunicationError(msg) from err
