"""API client for Textbelt SMS service."""

from __future__ import annotations

from typing import Any

import aiohttp
from sqlalchemy import false


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
        self._endpoint = "https://textbelt.com/text"

    async def async_get_sms_status(self, text_id: str) -> dict[str, Any]:
        """
        Check the delivery status of an SMS message using its textId.

        Args:
            text_id: The textId of the sent SMS message.

        Returns:
            The JSON response from the status API, including status and error if any.

        Raises:
            TextbeltApiClientError: For general API errors.
            TextbeltApiClientCommunicationError: For network errors.

        """
        status_endpoint = f"https://textbelt.com/status/{text_id}"
        try:
            async with self._session.get(status_endpoint) as response:
                data = await response.json()
                if response.status != 200:  # noqa: PLR2004
                    msg = data.get("error", "Unknown error from Textbelt status API.")
                    raise TextbeltApiClientError(msg)
                return data
        except aiohttp.ClientError as err:
            msg = f"Network error: {err}"
            raise TextbeltApiClientCommunicationError(msg) from err

    async def async_send_sms(
        self, phone: str, message: str, webhook_url: str | None = None
    ) -> dict[str, Any]:
        """
        Send an SMS message using the Textbelt API.

        Optionally, provide a webhook URL for replies.

        Args:
            phone: The recipient's phone number (international format recommended).
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
                data = await response.json()
                if response.status in {401, 403}:
                    msg = "Invalid API key or unauthorized."
                    raise TextbeltApiClientAuthenticationError(msg)
                if not data.get("success", false):
                    msg = data.get("error", "Unknown error from Textbelt API.")
                    raise TextbeltApiClientError(msg)
                return data
        except aiohttp.ClientError as err:
            msg = f"Network error: {err}"
            raise TextbeltApiClientCommunicationError(msg) from err

    async def async_check_status(self, text_id: str) -> dict[str, Any]:
        """Check the status of a sent SMS message."""
        status_endpoint = f"https://textbelt.com/status/{text_id}"
        try:
            async with self._session.get(status_endpoint) as response:
                data = await response.json()
                if response.status != 200:  # noqa: PLR2004
                    msg = data.get("error", "Unknown error from Textbelt status API.")
                    raise TextbeltApiClientError(msg)
                return data
        except aiohttp.ClientError as err:
            msg = f"Network error: {err}"
            raise TextbeltApiClientCommunicationError(msg) from err
