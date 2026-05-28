"""Unit tests for GameManager._detect_wake_word."""

import pytest


@pytest.mark.unit
@pytest.mark.parametrize(
    "text,expected_remainder",
    [
        ("fante pon X", "pon X"),
        ("fante, pon X", "pon X"),
        ("fante. pon X", "pon X"),
        ("FANTE PON X", "PON X"),
        ("Fánte pon X", "pon X"),
        ("  fante pon X", "pon X"),
        ("fante", ""),
        ("fante!", ""),
    ],
)
def test_detects_wake_word(make_game, text, expected_remainder):
    game, *_ = make_game(input_lines=[None])
    game._wake_words = ["fante"]
    assert game._detect_wake_word(text) == expected_remainder


@pytest.mark.unit
@pytest.mark.parametrize(
    "text",
    [
        "fantástico pon X",
        "pon fante X",
        "pon X",
        "",
    ],
)
def test_does_not_match(make_game, text):
    game, *_ = make_game(input_lines=[None])
    game._wake_words = ["fante"]
    assert game._detect_wake_word(text) is None


@pytest.mark.unit
def test_no_wake_words_configured_never_matches(make_game):
    game, *_ = make_game(input_lines=[None])
    game._wake_words = []
    assert game._detect_wake_word("fante pon X") is None


@pytest.mark.unit
def test_multi_word_wake_words_matched_longest_first(make_game):
    game, *_ = make_game(input_lines=[None])
    game._wake_words = ["fante", "hey fante"]
    assert game._detect_wake_word("hey fante pon X") == "pon X"
