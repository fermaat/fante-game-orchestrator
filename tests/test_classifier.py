"""Tests for ActionClassifier."""

import pytest

from fante.domain.turn import ActionIntent


@pytest.mark.functional
def test_classifier_returns_intent_on_valid_json() -> None:
    from tests.conftest import MockProvider

    from fante.turn.classifier import ActionClassifier

    provider = MockProvider(['{"rule_id": "climb", "context": {"surface": "wet"}}'])
    clf = ActionClassifier(provider=provider, rule_ids=["climb", "dodge"], prompt_path=None)
    result = clf.classify("quiero trepar", "Fante")
    assert isinstance(result, ActionIntent)
    assert result.rule_id == "climb"
    assert result.context == {"surface": "wet"}


@pytest.mark.functional
def test_classifier_returns_none_when_rule_id_null() -> None:
    from tests.conftest import MockProvider

    from fante.turn.classifier import ActionClassifier

    provider = MockProvider(['{"rule_id": null}'])
    clf = ActionClassifier(provider=provider, rule_ids=["climb"], prompt_path=None)
    result = clf.classify("hola", "Fante")
    assert result is None


@pytest.mark.functional
def test_classifier_returns_none_on_parse_failure() -> None:
    from tests.conftest import MockProvider

    from fante.turn.classifier import ActionClassifier

    provider = MockProvider(["esto no es json"])
    clf = ActionClassifier(provider=provider, rule_ids=["climb"], prompt_path=None)
    result = clf.classify("cualquier cosa", "Fante")
    assert result is None


@pytest.mark.functional
def test_classifier_strips_markdown_fences() -> None:
    from tests.conftest import MockProvider

    from fante.turn.classifier import ActionClassifier

    provider = MockProvider(['```json\n{"rule_id": "dodge", "context": {}}\n```'])
    clf = ActionClassifier(provider=provider, rule_ids=["dodge"], prompt_path=None)
    result = clf.classify("esquiva", "Fante")
    assert result is not None
    assert result.rule_id == "dodge"


@pytest.mark.functional
def test_classifier_returns_none_on_empty_rule_id() -> None:
    from tests.conftest import MockProvider

    from fante.turn.classifier import ActionClassifier

    provider = MockProvider(['{"rule_id": "", "context": {}}'])
    clf = ActionClassifier(provider=provider, rule_ids=["climb"], prompt_path=None)
    result = clf.classify("mmm", "Fante")
    assert result is None
