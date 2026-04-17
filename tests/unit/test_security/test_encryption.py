"""Tests for AES-256 encryption layer."""

import pytest

from tgai_agent.storage.encryption import decrypt, encrypt


def test_encrypt_returns_string():
    result = encrypt("my-secret-key")
    assert isinstance(result, str)
    assert result != "my-secret-key"


def test_roundtrip():
    original = "sk-openai-abc123"
    assert decrypt(encrypt(original)) == original


def test_empty_string():
    assert encrypt("") == ""
    assert decrypt("") == ""


def test_tampered_ciphertext_returns_empty():
    bad = "this-is-not-valid-fernet-data"
    assert decrypt(bad) == ""


def test_different_values_produce_different_ciphertexts():
    a = encrypt("key-one")
    b = encrypt("key-two")
    assert a != b
