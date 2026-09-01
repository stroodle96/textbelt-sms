"""Constants for textbelt_sms."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "textbelt_sms"
ATTRIBUTION = "Data provided by Textbelt SMS API (https://textbelt.com/)"
API_BASE_URL_ENV = "TEXTBELT_SMS_API_BASE_URL"
DEFAULT_API_BASE_URL = "https://textbelt.com"
SERVICE_SEND_SMS = "send_sms"
EVENT_REPLY = "textbelt_sms_reply"
# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
