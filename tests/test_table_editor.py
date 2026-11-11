"""The catalogue tables must keep CUHK / CUHKSZ / Credits read-only.

Only the free-entry tables (PE, College GE, Four Area of GE, Other Courses)
let students type the course code and credits, because those courses have no
catalogue row. Every other table must pass the locked default to
``st.data_editor``.
"""

import pandas as pd
import pytest

import app.components as components
from app.ida import _catalog_table as ida_catalog_table
from app.major_2 import _catalog_table as major_2_catalog_table
from app.ucore import _catalogue_section, _user_input_section
from src.data_retrieval import CourseDataContext, load_all_data


LOCKED = ["CUHK", "CUHKSZ", "Credits"]


@pytest.fixture(scope="module")
def context() -> CourseDataContext:
    return load_all_data()


@pytest.fixture()
def editor_calls(monkeypatch : pytest.MonkeyPatch) -> list[dict]:
    """Record every st.data_editor call instead of rendering it."""
    calls : list[dict] = []

    def fake_data_editor(df : pd.DataFrame, **kwargs) -> pd.DataFrame:
        calls.append(kwargs)
        return df

    monkeypatch.setattr(components.st, "data_editor", fake_data_editor)
    return calls


def _table() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "CUHK": ["FINA3080 Investment Analysis"],
            "CUHKSZ": ["FIN3080 Investment Analysis"],
            "Credits": [3],
            "Selected": [False],
            "Study Period": [""],
        }
    )


def test_table_editor_locks_catalogue_columns_by_default(editor_calls) -> None:
    components.table_editor(_table(), "default-test", lambda key, df: None)

    assert editor_calls[0]["disabled"] == LOCKED


def test_table_editor_keeps_explicit_free_entry_table_editable(editor_calls) -> None:
    components.table_editor(
        _table(), "free-entry-test", lambda key, df: None, disabled_col=[]
    )

    assert editor_calls[0]["disabled"] == []


def test_ida_catalogue_table_locks_official_columns(editor_calls, context) -> None:
    ida_catalog_table(
        context,
        "Interdisciplinary Data Analytics",
        ["FINA3080"],
        "ida-lock-test",
    )

    assert editor_calls[0]["disabled"] == LOCKED
    assert editor_calls[0]["num_rows"] == "fixed"


def test_major_2_catalogue_table_locks_official_columns(editor_calls, context) -> None:
    major_2_catalog_table(
        context,
        "Interdisciplinary Data Analytics",
        ["FINA3080"],
        "major2-lock-test",
    )

    assert editor_calls[0]["disabled"] == LOCKED
    assert editor_calls[0]["num_rows"] == "fixed"


def test_ucore_catalogue_section_locks_official_columns(editor_calls, context) -> None:
    _catalogue_section(
        context,
        "University Core",
        "Required Courses",
        "ucore-lock-test",
        lambda key, df: None,
    )

    assert editor_calls[0]["disabled"] == LOCKED
    assert editor_calls[0]["num_rows"] == "fixed"


def test_ucore_free_entry_section_keeps_columns_editable(editor_calls) -> None:
    _user_input_section(
        "Other Courses",
        "other-lock-test",
        lambda key, df: None,
        "other_courses",
        1,
        3,
        True,
    )

    assert editor_calls[0]["disabled"] == []
    assert editor_calls[0]["num_rows"] == "dynamic"
