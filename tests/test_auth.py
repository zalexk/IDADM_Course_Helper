"""Tests for src/auth.py — password hashing, local verification, and the
legacy-plaintext upgrade path. Uses a fake client; no network, no secrets.
"""

import pytest

from src import auth
from src.auth import _is_hashed, hash_password, signin, signup, verify_password

PASSWORD = "Passw0rd!"


class _FakeResp:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    """Records every chain call; select/eq/maybe_single/update return self."""

    def __init__(self, rows=None, user_id="u1"):
        self.rows = rows or []
        self.user_id = user_id
        self.calls = []
        self.inserted = None
        self.updated = None
        self._single = False
        self._insert_mode = False

    def select(self, *cols):
        self.calls.append(("select", cols))
        return self

    def eq(self, col, val):
        self.calls.append(("eq", (col, val)))
        return self

    def maybe_single(self):
        self._single = True
        return self

    def execute(self):
        if self._insert_mode:
            return _FakeResp([{**self.inserted, "id": self.user_id}])
        if self._single:
            return _FakeResp(self.rows[0] if self.rows else None)
        return _FakeResp(self.rows)

    def insert(self, payload):
        self.inserted = payload
        self._insert_mode = True
        return self

    def update(self, payload):
        self.updated = payload
        return self


class _FakeClient:
    def __init__(self, rows=None):
        self.table_ = _FakeTable(rows)

    def table(self, name):  # noqa: ARG002
        return self.table_


@pytest.fixture
def fake(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr(auth, "client", fake_client)
    return fake_client.table_


class TestHashPassword:
    def test_format(self):
        stored = hash_password(PASSWORD)
        assert _is_hashed(stored)
        scheme, iterations, salt_hex, digest_hex = stored.split("$")
        assert scheme == "pbkdf2_sha256"
        assert int(iterations) > 0
        assert len(bytes.fromhex(salt_hex)) == 16
        assert len(bytes.fromhex(digest_hex)) == 32  # SHA-256 digest

    def test_salt_randomness(self):
        assert hash_password(PASSWORD) != hash_password(PASSWORD)

    def test_never_contains_plaintext(self):
        assert PASSWORD not in hash_password(PASSWORD)


class TestVerifyPassword:
    def test_correct(self):
        assert verify_password(PASSWORD, hash_password(PASSWORD))

    def test_wrong(self):
        assert not verify_password("WrongPass1", hash_password(PASSWORD))

    def test_malformed(self):
        assert not verify_password(PASSWORD, "")
        assert not verify_password(PASSWORD, "plaintext")
        assert not verify_password(PASSWORD, "pbkdf2_sha256$abc$zz$qq")

    def test_plaintext_rejected(self):
        assert not verify_password(PASSWORD, PASSWORD)


class TestSignup:
    def test_stores_hash_not_plaintext(self, fake):
        assert signup("alice", PASSWORD) == "u1"
        assert fake.inserted["name"] == "alice"
        stored = fake.inserted["password"]
        assert stored != PASSWORD
        assert _is_hashed(stored)
        assert verify_password(PASSWORD, stored)

    def test_repeated_username_returns_none(self, fake):
        fake.rows = [{"id": "u1"}]
        assert signup("alice", PASSWORD) is None
        assert fake.inserted is None


class TestSignin:
    def test_hashed_row_success(self, fake):
        fake.rows = [{"id": "u1", "password": hash_password(PASSWORD)}]
        assert signin("alice", PASSWORD) == "u1"
        assert fake.updated is None  # no upgrade needed

    def test_hashed_row_wrong_password(self, fake):
        fake.rows = [{"id": "u1", "password": hash_password(PASSWORD)}]
        assert signin("alice", "WrongPass1") is None
        assert fake.updated is None

    def test_password_never_a_query_condition(self, fake):
        fake.rows = [{"id": "u1", "password": hash_password(PASSWORD)}]
        signin("alice", PASSWORD)
        eq_calls = [args for op, args in fake.calls if op == "eq"]
        assert all(col != "password" for col, _ in eq_calls)

    def test_legacy_plaintext_upgrades(self, fake):
        fake.rows = [{"id": "u1", "password": PASSWORD}]
        assert signin("alice", PASSWORD) == "u1"
        assert fake.updated is not None
        assert fake.updated["password"] != PASSWORD
        assert _is_hashed(fake.updated["password"])
        assert verify_password(PASSWORD, fake.updated["password"])

    def test_legacy_plaintext_wrong_password(self, fake):
        fake.rows = [{"id": "u1", "password": PASSWORD}]
        assert signin("alice", "WrongPass1") is None
        assert fake.updated is None

    def test_unknown_user(self, fake):
        assert signin("nobody", PASSWORD) is None
        assert fake.updated is None
