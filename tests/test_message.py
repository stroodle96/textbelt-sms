# Copyright (c) 2026 Textbelt SMS contributors
"""Message preparation behavior and approved character evidence."""

# Boundary fixtures intentionally use literal, independently counted budgets.
# ruff: noqa: PLR2004
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from custom_components.textbelt_sms import message as module

EVIDENCE = json.loads(
    (
        Path(__file__).parents[1]
        / "docs/research/probes/v1-character-policy-proposal.json"
    ).read_text()
)


@pytest.mark.parametrize("item", EVIDENCE["allowed"])
def test_every_observed_character_preserved_and_weighted(
    item: dict[str, object],
) -> None:
    """Every observed character preserved and weighted."""
    char = str(item["character"])
    text = "A" + char + "B"
    assert module.prepare_message(text).parts == (text,)
    n = 160 // int(str(item["gsm_septets"]))
    assert (
        len(
            module.prepare_message(
                char * n if char not in {"\n", " "} else "A" + char * (n - 2) + "B"
            ).parts
        )
        == 1
    )


@pytest.mark.parametrize("text", ["😀", "Δ", "\x00", "\f", "中文"])
def test_unsupported_content_fails_explicitly(text: str) -> None:
    """Unsupported content fails explicitly."""
    with pytest.raises(ValueError, match="Unsupported"):
        module.prepare_message(text)


def test_boundaries_labels_and_extensions() -> None:
    """Boundaries labels and extensions."""
    assert module.prepare_message("A" * 160).parts == ("A" * 160,)
    assert module.prepare_message("^" * 80).parts == ("^" * 80,)
    assert module.prepare_message("A" * 161).parts == (
        "(1/2) " + "A" * 154,
        "(2/2) " + "A" * 7,
    )
    assert len(module.prepare_message("^" * 81).parts) == 2


def test_empty_and_overflow_modes() -> None:
    """Empty and overflow modes."""
    with pytest.raises(ValueError, match="empty"):
        module.prepare_message(" \n ")
    assert module.prepare_message("", mode="assist").parts == (
        "No response was returned.",
    )
    with pytest.raises(ValueError, match="maximum"):
        module.prepare_message("A" * 771)
    result = module.prepare_message("A" * 900, mode="assist")
    assert result.shortened
    assert len(result.parts) == 5
    assert result.parts[-1].endswith("Response shortened.")


def test_readable_markup_preserves_values_and_urls() -> None:
    """Readable markup preserves values and urls."""
    text = "**Status**\n• Temperature: \u22122.5 °C\n<p>Not open &amp; unsafe.</p>\n[Details](https://example.com/?a=1&b=-2.5)"
    assert (
        module.prepare_message(text).normalized_text
        == "Status\n- Temperature: -2.5 degrees C\nNot open & unsafe.\n"
        "Details (https://example.com/?a=1&b=-2.5)"
    )
    assert (
        module.prepare_message(
            "<speak>Door <emphasis>not</emphasis> open."
            '<break time="1s"/>Check it.</speak>'
        ).normalized_text
        == "Door not open. Check it."
    )


def test_newlines_title_and_literal_backslash() -> None:
    """Newlines title and literal backslash."""
    assert module.prepare_message("one\ntwo").parts == ("one\ntwo",)
    assert module.prepare_message(r"one\ntwo").parts == (r"one\ntwo",)
    assert module.prepare_message(
        "one\ntwo", mode="assist", compact=True, title="Alert"
    ).parts == ("Alert: one two",)
    with pytest.raises(ValueError, match="Unsupported"):
        module.prepare_message("good", title="😀")


def test_word_sentence_and_two_digit_labels() -> None:
    """Word sentence and two digit labels."""
    result = module.prepare_message("First sentence. " + "word " * 40)
    assert result.parts[0] == "(1/3) First sentence."
    policy = replace(module.DEFAULT_POLICY, max_part_septets=20, max_parts=30)
    result = module.prepare_message("A" * 140, policy=policy)
    assert len(result.parts) == 11
    assert result.parts[9].startswith("(10/11) ")
    assert all(len(part) <= 20 for part in result.parts)


def test_policy_and_prepared_message_immutable() -> None:
    """Policy and prepared message immutable."""
    result = module.prepare_message("Hello")
    with pytest.raises(FrozenInstanceError):
        result.shortened = True
    with pytest.raises(FrozenInstanceError):
        module.DEFAULT_POLICY.max_parts = 9


def test_legacy_blank_lines_and_numeric_comparisons() -> None:
    """Legacy blank lines and numeric comparisons."""
    assert module.prepare_message("one\n\n\ntwo").normalized_text == "one\n\n\ntwo"
    assert (
        module.prepare_message("Temperature < 2.5 and > -1").normalized_text
        == "Temperature < 2.5 and > -1"
    )


def test_html_link_destination_is_meaningful() -> None:
    """Html link destination is meaningful."""
    assert (
        module.prepare_message(
            '<a href="https://example.com/?a=1&b=2">Details</a>'
        ).normalized_text
        == "Details (https://example.com/?a=1&b=2)"
    )


def test_custom_policy_revalidates_fallback_and_notice() -> None:
    """Custom policy revalidates fallback and notice."""
    policy = replace(
        module.DEFAULT_POLICY, allowed_characters="A", extension_characters=frozenset()
    )
    with pytest.raises(ValueError, match="Unsupported"):
        module.prepare_message("", mode="assist", policy=policy)
    with pytest.raises(ValueError, match="Unsupported"):
        module.prepare_message("A" * 900, mode="assist", policy=policy)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.test/?q=__not__&tag=**bold**",
        "https://example.test/?q=&copy;",
        "https://example.test/?q=\u22122.5",
        "https://example.test/?q=`value`",
    ],
)
def test_url_values_are_not_rewritten(url: str) -> None:
    """Url values are not rewritten."""
    if "\u2212" in url or "`" in url:
        with pytest.raises(ValueError, match="Unsupported"):
            module.prepare_message(url)
    else:
        assert module.prepare_message(url).normalized_text == url


def test_url_placeholder_text_and_parentheses_preserved() -> None:
    """Preserve user text matching placeholders and meaningful URL parentheses."""
    text = "URLTOKEN0ENDTOKEN https://example.test/?q=(a)__not__&tag=**bold**"
    assert module.prepare_message(text).normalized_text == text


@pytest.mark.parametrize("wrapper", ["{}", "[Details]({})", '<a href="{}">Details</a>'])
@pytest.mark.parametrize(
    "query", ["O'Reilly&tag=__not__", '"quoted"&tag=**bold**', "(O'Reilly)&tag=&copy;"]
)
def test_quoted_url_queries_are_preserved(wrapper: str, query: str) -> None:
    """Preserve full quoted URL values in bare and wrapped destinations."""
    url = "https://example.test/?q=" + query
    if wrapper.startswith("<a") and '"' in query:
        wrapper = "<a href='{}'>Details</a>"
    expected = url if wrapper == "{}" else "Details (" + url + ")"
    assert module.prepare_message(wrapper.format(url)).normalized_text == expected
