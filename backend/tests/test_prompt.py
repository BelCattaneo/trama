import pytest

from trama.prompts import load_prompt


def test_load_prompt_v1_returns_non_empty():
    content = load_prompt("v1")
    assert content
    assert content.strip()


def test_load_prompt_missing_version_raises():
    with pytest.raises(FileNotFoundError):
        load_prompt("v999")
