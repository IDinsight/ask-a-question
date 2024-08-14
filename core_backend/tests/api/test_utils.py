import logging
import string

import pytest

from core_backend.app.utils import (
    SECRET_KEY_N_BYTES,
    create_langfuse_metadata,
    generate_key,
    generate_secret_key,
    get_log_level_from_str,
    get_password_salted_hash,
    get_random_string,
)


def test_create_langfuse_metadata_with_query_only() -> None:
    metadata = create_langfuse_metadata(query_id=1)

    assert "trace_id" in metadata


def test_create_langfuse_metadata_with_query_and_user() -> None:
    metadata = create_langfuse_metadata(query_id=1, user_id=1)

    assert "trace_id" in metadata
    assert "trace_user_id" in metadata


@pytest.mark.parametrize("size", [1, 10, 100])
def test_get_random_string_length(size: int) -> None:
    random_string = get_random_string(size)

    assert len(random_string) == size


@pytest.mark.parametrize("size", [1, 10, 100])
def test_get_random_string_characters(size: int) -> None:
    allowed = string.ascii_letters + string.digits
    random_string = get_random_string(size)

    assert all(c in allowed for c in random_string)


def test_generate_secret_key() -> None:
    secret_key = generate_secret_key()

    assert len(secret_key) == 32
    assert all(c in string.hexdigits for c in secret_key)


def test_generate_key() -> None:
    key = generate_key()

    assert len(key) >= SECRET_KEY_N_BYTES
    assert all(c in string.ascii_letters + string.digits for c in key)


@pytest.mark.parametrize(
    "log_level_str", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NOTSET"]
)
def test_get_log_level_from_str_existing(log_level_str: str) -> None:
    log_level = get_log_level_from_str(log_level_str)

    assert isinstance(log_level, int)
    assert log_level in [0, 10, 20, 30, 40, 50]


@pytest.mark.parametrize("log_level_str", ["UNKNWON", "VERBOSE"])
def test_get_log_level_from_str_unknown(log_level_str: str) -> None:
    log_level = get_log_level_from_str(log_level_str)

    assert isinstance(log_level, int)
    assert log_level == logging.INFO


def test_get_password_salted_hash_output_length() -> None:
    """Test that the length of the output string is correct."""
    key = "test_password"
    result = get_password_salted_hash(key)
    expected_length = 32 + 64  # 16 bytes salt (hex) + 32 bytes hash (hex)
    assert len(result) == expected_length


def test_get_password_salted_hash_output_structure() -> None:
    """Test that the output is structured as salt + hash."""
    key = "test_password"
    result = get_password_salted_hash(key)
    salt = result[:32]
    hash_value = result[32:]

    assert len(salt) == 32
    assert len(hash_value) == 64


def test_get_password_salted_hash_different_salts_for_same_key() -> None:
    """Test that the function returns different results for the same input key due to
    different salts."""
    key = "test_password"
    result1 = get_password_salted_hash(key)
    result2 = get_password_salted_hash(key)

    assert result1 != result2


def test_get_password_salted_hash_different_hashes_for_different_keys() -> None:
    """Test that the function returns different results for different input keys."""
    key1 = "test_password_1"
    key2 = "test_password_2"
    result1 = get_password_salted_hash(key1)
    result2 = get_password_salted_hash(key2)

    assert result1 != result2


def test_get_password_salted_hash_consistent_hash_length() -> None:
    """Test that the hash part of the output is always the correct length."""
    key = "test_password"
    result = get_password_salted_hash(key)
    hash_value = result[32:]

    assert len(hash_value) == 64
