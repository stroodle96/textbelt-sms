# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""Constants for textbelt_sms."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "textbelt_sms"
ATTRIBUTION = "Data provided by Textbelt SMS API (https://textbelt.com/)"
API_BASE_URL_ENV = "TEXTBELT_SMS_API_BASE_URL"
DEFAULT_API_BASE_URL = "https://textbelt.com"
SERVICE_SEND_SMS = "send_sms"
EVENT_REPLY = "textbelt_sms_reply"
WEBHOOK_ID = "textbelt_sms_reply"

ATTR_DELIVERY_STATUS = "delivery_status"
ATTR_TEXT_ID = "text_id"
ATTR_PHONE = "phone"
ATTR_MESSAGE = "message"

STATUS_PENDING = "pending"
STATUS_DELIVERED = "delivered"
STATUS_FAILED = "failed"
STATUS_UNKNOWN = "unknown"

CONF_WEBHOOK_ID = "webhook_id"
SERVICE_START_CONVERSATION = "start_conversation"


def reply_key_usable(value: object) -> bool:
    """Reject known public/free and test keys without inferring account eligibility."""
    return (
        isinstance(value, str)
        and bool(value)
        and value.lower() != "textbelt"
        and not value.lower().endswith("_test")
    )


CONFIG_VERSION = 2
