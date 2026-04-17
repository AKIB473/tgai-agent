"""Integration-style roundtrip: encrypt → store as string → decrypt."""

import pytest

from tgai_agent.storage.encryption import decrypt, encrypt


@pytest.mark.parametrize(
    "secret",
    [
        "sk-short",
        "AIzaSyLongGeminiKeyWith-SpecialChars_123",
        "a" * 256,
        "unicode: 日本語テスト",
    ],
)
def test_roundtrip_parametrized(secret: str):
    assert decrypt(encrypt(secret)) == secret


def test_ciphertext_is_not_plaintext():
    secret = "my-api-key"
    ct = encrypt(secret)
    assert secret not in ct
