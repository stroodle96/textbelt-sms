"""API client for Textbelt SMS service."""

from __future__ import annotations

from typing import Any

import aiohttp


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

    async def async_send_sms(
        self, phone: str, message: str, webhook_url: str | None = None
    ) -> dict[str, Any]:
        """
        Send an SMS message using the Textbelt API, optionally with a webhook URL for replies.

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
                if response.status == 401 or response.status == 403:
                    msg = "Invalid API key or unauthorized."
                    raise TextbeltApiClientAuthenticationError(msg)
                if not data.get("success", False):
                    msg = data.get("error", "Unknown error from Textbelt API.")
                    raise TextbeltApiClientError(msg)
                return data
        except aiohttp.ClientError as err:
            msg = f"Network error: {err}"
            raise TextbeltApiClientCommunicationError(msg) from err
