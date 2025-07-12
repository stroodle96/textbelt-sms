"""Constants for the Textbelt SMS integration."""

import logging

DOMAIN = "textbelt_sms"
LOGGER = logging.getLogger(__package__)

WEBHOOK_ID = "textbelt_sms_webhook"

# Sensor attributes
ATTR_TEXT_ID = "text_id"
ATTR_PHONE = "phone"
ATTR_MESSAGE = "message"
ATTR_STATUS = "status"
ATTR_RESPONSE = "response"

# Default values
DEFAULT_STATUS = "unknown"
DEFAULT_NAME = "Last Message Status"

# Service call parameters
CONF_API_KEY = "api_key"
CONF_PHONE = "phone"
CONF_MESSAGE = "message"

# Status response states
STATUS_DELIVERED = "delivered"
STATUS_FAILED = "failed"
STATUS_PENDING = "pending"
STATUS_UNKNOWN = "unknown"
