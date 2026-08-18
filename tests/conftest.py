"""Test infrastructure: stub external deps so the import chain works without
network, secrets, or a live Streamlit run context.

Why this exists:
  src/storage.py imports `supabase` at module level and reads `st.secrets` at
  import time. src/data_retrieval.py imports src.storage. So merely collecting
  any test that touches src.data_retrieval pulls in supabase + a Streamlit
  secrets context. In a bare checkout (no `uv sync`, no populated
  .streamlit/secrets.toml) collection crashes with ModuleNotFoundError before a
  single test runs.

Fix: insert a fake `supabase` module into sys.modules and bind `streamlit.secrets`
to a plain dict BEFORE any test module imports the src.* chain. A per-test
autouse fixture then gives each test a fresh, isolated `streamlit.session_state`
dict (storage.data_on_change and data_retrieval.show_course_info read it at call
time, never at import time).
"""

import sys
import types

# --- 1) Stub supabase before src.storage is imported -------------------------
if "supabase" not in sys.modules:
    _sb = types.ModuleType("supabase")

    class _Resp:
        def __init__(self) -> None:
            self.data: list = []

    class _Table:
        # Fluent no-op chain; .execute() returns an empty response.
        def select(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def upsert(self, *a, **k): return self
        def delete(self, *a, **k): return self
        def execute(self): return _Resp()

    class _Client:
        def table(self, name): return _Table()  # noqa: ARG002

    def create_client(url, key):  # noqa: ARG001
        return _Client()

    setattr(_sb, "create_client", create_client)
    setattr(_sb, "Client", _Client)
    sys.modules["supabase"] = _sb

# --- 2) Bind streamlit.secrets so src.storage module-level init passes -------
import streamlit as st  # noqa: E402

st.secrets = {"SUPABASE_URL": "test-url", "SUPABASE_KEY": "test-key"}

# --- 3) Per-test isolated session_state --------------------------------------
import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_session_state(monkeypatch):
    """Give each test a fresh empty dict for `streamlit.session_state`.

    Tests that need a logged-in user do `st.session_state["user_id"] = "..."`
    directly; tests that feed an editor edit_state set
    `st.session_state["<element_key>"] = {...}`. Restored automatically.
    """
    monkeypatch.setattr(st, "session_state", {}, raising=False)
