import hashlib
import hmac
import os

from src.storage import client
from postgrest.exceptions import APIError


class AuthServiceError(Exception):
    pass


# --- Password hashing: PBKDF2-HMAC-SHA256 (stdlib, no new dependencies) -------
# Stored format: `pbkdf2_sha256$<iterations>$<salt_hex>$<digest_hex>`.
# Self-describing scheme prefix allows future migration (e.g. argon2/bcrypt)
# by swapping the verify function, not the DB column.
_PBKDF2_SCHEME = "pbkdf2_sha256"
_PBKDF2_ITERATIONS = 600_000  # OWASP recommendation for PBKDF2-HMAC-SHA256
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    """Hash a password with a fresh random salt."""
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS
    )
    return f"{_PBKDF2_SCHEME}${_PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def _is_hashed(stored: str) -> bool:
    parts = stored.split("$")
    return len(parts) == 4 and parts[0] == _PBKDF2_SCHEME


def verify_password(password: str, stored: str) -> bool:
    """Constant-time password check against a stored hash.

    Returns False for anything malformed (empty, plaintext, bad hex).
    """
    if not _is_hashed(stored):
        return False
    _, iterations, salt_hex, digest_hex = stored.split("$")
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        iterations = int(iterations)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(actual, expected)


def signup(username: str, password: str) -> str | None:
    try:
        existing = (  # Ensure the user name is unique
            client.table("user")
            .select("id")
            .eq("name", username)
            .execute()
        )

    except APIError as e:
        raise AuthServiceError("API Error") from e

    except Exception as e:
        raise AuthServiceError("Fail to retrieve data") from e

    if existing.data:
        return None  # No a unique user name

    try:
        response = (
            client.table("user")
            .insert(
                {
                    "name": username,
                    "password": hash_password(password),
                }
            )
            .execute()
        )
        return response.data[0]["id"]  # type: ignore[index]

    except APIError as e:
        if e.code == "23505":  # For repeated users in High Concurrency Scenario
            return None  # Same practice for repeated users

        raise AuthServiceError("Fail to access the database") from e

    except Exception as e:
        raise AuthServiceError("Fail to create new user") from e


def signin(username: str, password: str) -> str | None:
    """Verify credentials against the user table.

    The password is verified locally against its stored hash and is never
    used as a query condition. Legacy plaintext rows (pre-hashing) still log
    in and are upgraded to a hash on success; a failed upgrade is non-fatal
    because the user is already authenticated.
    """
    try:
        row = (
            client.table("user")
            .select("id", "password")
            .eq("name", username)
            .maybe_single()
            .execute()
        )

    except APIError as e:
        raise AuthServiceError("Fail to access the database") from e

    except Exception as e:
        raise AuthServiceError("Fail to retrieve user's information") from e

    if not row.data:
        return None

    stored = row.data.get("password") or ""
    user_id = row.data["id"]

    if _is_hashed(stored):
        ok = verify_password(password, stored)
    else:
        # Legacy plaintext row: verify directly, then upgrade in place.
        ok = hmac.compare_digest(
            password.encode("utf-8"), stored.encode("utf-8")
        )
        if ok:
            try:
                (
                    client.table("user")
                    .update({"password": hash_password(password)})
                    .eq("id", user_id)
                    .execute()
                )
            except Exception:
                pass  # Non-fatal: next successful login retries the upgrade

    return user_id if ok else None


def validate_password_strength(password: str) -> bool:
    if len(password) < 8:
        return False

    if not any(c.isupper() for c in password):
        return False

    if not any(c.islower() for c in password):
        return False

    if not any(c.isdigit() for c in password):
        return False

    return True
