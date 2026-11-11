from supabase import create_client, Client
from typing import Any

import streamlit as st
import pandas as pd

# Initialize client
_url : str = st.secrets["SUPABASE_URL"]
_key : str = st.secrets["SUPABASE_KEY"] 
client: Client = create_client(_url, _key)


def _period_is_empty(value) -> bool:
    """True when a Study Period cell carries no usable term (None / NaN /
    blank). A course with no term does not belong in the study plan."""
    if isinstance(value, str):
        return not value.strip()
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _clean_course_id(value) -> str:
    """Trimmed string of a typed course cell; '' for None / blank."""
    if value is None:
        return ""
    text = str(value)
    return text.strip()


def _clean_credits(value) -> int | None:
    """Whole-number credits from a cell; 0 for a blank cell; None when the
    user typed a non-integer number (e.g. 3.5) so the caller can surface an
    error instead of silently truncating or zeroing the value."""
    if value is None:
        return 0
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return 0
        try:
            num = float(text)
        except ValueError:
            return None
    else:
        try:
            num = float(value)
        except (TypeError, ValueError):
            return None
    if not num.is_integer() or num < 0:
        return None
    return int(num)


_ALL_TABLES = ("study_plan", "pe", "college_ge", "four_area_ge", "english", "other_courses")
_INPUT_TABLES = ("pe", "college_ge", "four_area_ge", "other_courses")
_USER_CONFIG_TABLE = "user_config"


def _checkbox_value(value) -> bool | None:
    """Normalise a Selected cell.

    None means the DataFrame carries no Selected column (legacy callers /
    tests), so the caller falls back to the old "has a Study Period" rule.
    """
    if value is None or isinstance(value, bool):
        return value
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return None
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("true", "1", "yes"):
            return True
        if text in ("false", "0", "no", ""):
            return False
        return None
    return bool(value)


def is_selected(row) -> bool:
    """True when a saved row is part of the plan.

    A scheduled course (non-empty Study Period) always counts: this keeps
    migrated rows and inserts made by older clients selected regardless of
    the stored flag. An unscheduled course counts only when explicitly ticked.
    """
    return bool(row.get("selected")) or not _period_is_empty(row.get("study_period"))


def data_on_change(key: str, df: pd.DataFrame) -> None:
    user_id = st.session_state.get("user_id")
    if not user_id:
        return # Never store data for guest users

    # Guard: index must carry canonical course keys, not RangeIndex row numbers
    if len(df.index) > 0 and not isinstance(df.index[0], str):
        st.error("Table index must carry course keys.")
        return

    edit_state = st.session_state[key]
    edited  = edit_state.get("edited_rows", {})  # {row_index: {column: new_value}} — only changed cells
    added   = edit_state.get("added_rows", [])   # [{column: value, ...}] — complete new rows
    deleted = edit_state.get("deleted_rows", []) # [row_index, ...]

    try:
        # 1) Modified cells: course identity is the row's index label (canonical key),
        #    not the editable "CUHK" display column — so editing display text can't
        #    hijack the stored course_id.
        for index, changes in edited.items():
            base = df.iloc[int(index)]
            course_id = base.name
            period = changes.get("Study Period", base["Study Period"])
            selected = _checkbox_value(changes.get("Selected", base.get("Selected")))

            # Un-ticking removes a catalogue course from the plan entirely:
            # the row (and its period) is deleted from study_plan.
            if "Selected" in changes and _checkbox_value(changes["Selected"]) is False:
                delete_data(user_id, course_id)
                continue

            # Setting a period always ticks the course; a ticked course with no
            # period is a valid "selected, not scheduled yet" row.
            if not _period_is_empty(period):
                selected = True
            if selected is None:
                # Legacy DataFrame without a Selected column: keep the old rule.
                selected = not _period_is_empty(period)
            if not selected:
                delete_data(user_id, course_id)
                continue

            upsert_data(user_id, {
                "id": user_id,
                "course_id": course_id,
                "study_period": None if _period_is_empty(period) else period,
                "selected": True,
            })

        # 2) Added rows (dynamic tables): no index label exists yet, so the
        #    identity is the course code — first token of the typed "CUHK" cell.
        #    A ticked row without a period is a valid unscheduled selection;
        #    an un-ticked row without a period is not planned yet.
        for row in added:
            cid = str(row.get("CUHK") or "").strip().split()[0]
            if not cid:
                continue
            period = row.get("Study Period")
            selected = _checkbox_value(row.get("Selected"))
            if selected is None:
                selected = not _period_is_empty(period)
            selected = bool(selected) or not _period_is_empty(period)
            if not selected:
                continue
            upsert_data(user_id, {
                "id": user_id,
                "course_id": cid,
                "study_period": None if _period_is_empty(period) else period,
                "selected": True,
            })

        # 3) Deleted rows: remove by (id, course_id) using the index label
        for index in deleted:
            delete_data(user_id, df.iloc[int(index)].name)

    except Exception:
        st.error("Failed to save changes, please try again.") # exception chain preserved in traceback

def user_input_on_change(
    key: str,
    df: pd.DataFrame,
    table_name: str = "study_plan",
) -> None:
    """on_change for user-input course tables (PE, College GE, Four Area of GE).

    Unlike data_on_change, the course identity is the user-typed "CUHK" cell —
    these courses have no catalogue / equivalence, so the index label is NOT
    the identity. Each section writes to its own table (table_name) so recall
    is unambiguous and user-input rows never collide with catalogue rows.
    Handles edited / added / deleted rows (added+deleted matter under
    num_rows='dynamic').
    """
    user_id = st.session_state.get("user_id")
    if not user_id:
        return # Never store data for guest users

    edit_state = st.session_state[key]
    edited  = edit_state.get("edited_rows", {})  # {row_index: {column: new_value}}
    added   = edit_state.get("added_rows", [])    # [{column: value, ...}]
    deleted = edit_state.get("deleted_rows", [])  # [row_index, ...]

    try:
        # 1) Modified cells: course_id is the "CUHK" cell (user-typed).
        #    Empty study_period is stored as None (DB CHECK passes NULL) so
        #    partially-filled rows persist instead of being rejected.
        for index, changes in edited.items():
            base = df.iloc[int(index)]
            # Identity: whichever campus column carries a code (CUHK preferred).
            course_id = (_clean_course_id(changes.get("CUHK", base["CUHK"]))
                         or _clean_course_id(changes.get("CUHKSZ", base["CUHKSZ"])))
            if not course_id:
                continue # no identity yet — nothing to store
            credits = _clean_credits(changes.get("Credits", base["Credits"]))
            if credits is None:
                st.error(f"Invalid credits for {course_id} — please use a whole number.")
                continue
            raw_selected = _checkbox_value(changes.get("Selected", base.get("Selected")))
            period = changes.get("Study Period", base["Study Period"])
            if "Selected" in changes and _checkbox_value(changes["Selected"]) is False:
                # Un-ticking a user-input course keeps its row as a draft but
                # unschedules it. The period must be cleared in the same write,
                # otherwise is_selected() would keep counting the course.
                selected = False
                period = None
            elif not _period_is_empty(period):
                selected = True # setting a period ticks the course automatically
            elif raw_selected is None:
                selected = not _period_is_empty(period) # legacy df without Selected
            else:
                selected = bool(raw_selected)
            study_period = None if _period_is_empty(period) else period
            try:
                upsert_data(user_id, {
                    "id": user_id,
                    "course_id": course_id,
                    "credits": credits,
                    "study_period": study_period,
                    "selected": selected,
                }, table_name=table_name)
            except Exception:
                st.error(f"Failed to save {course_id}, please try again.")

        # 2) Added rows: complete records; identity from either campus column.
        #    An un-ticked row is still persisted as a draft (user-input tables
        #    keep whatever the student typed); it is simply not planned.
        for row in added:
            course_id = _clean_course_id(row.get("CUHK")) or _clean_course_id(row.get("CUHKSZ"))
            if not course_id:
                continue
            credits = _clean_credits(row.get("Credits"))
            if credits is None:
                st.error(f"Invalid credits for {course_id} — please use a whole number.")
                continue
            period = row.get("Study Period")
            selected = _checkbox_value(row.get("Selected"))
            if selected is None:
                selected = not _period_is_empty(period) # legacy df without Selected
            selected = bool(selected) or not _period_is_empty(period)
            try:
                upsert_data(user_id, {
                    "id": user_id,
                    "course_id": course_id,
                    "credits": credits,
                    "study_period": None if _period_is_empty(period) else period,
                    "selected": selected,
                }, table_name=table_name)
            except Exception:
                st.error(f"Failed to save {course_id}, please try again.")

        # 3) Deleted rows: remove by the original row's campus cell.
        for index in deleted:
            base = df.iloc[int(index)]
            course_id = _clean_course_id(base["CUHK"]) or _clean_course_id(base["CUHKSZ"])
            if course_id:
                try:
                    delete_data(user_id, course_id, table_name=table_name)
                except Exception:
                    st.error(f"Failed to delete {course_id}, please try again.")

    except Exception:
        st.error("Failed to save changes, please try again.")


def pe_on_change(key: str, df: pd.DataFrame) -> None:
    """Physical Education (fixed single row) → 'pe' table."""
    user_input_on_change(key, df, table_name="pe")


def college_ge_on_change(key: str, df: pd.DataFrame) -> None:
    """College GE (dynamic) → 'college_ge' table."""
    user_input_on_change(key, df, table_name="college_ge")


def four_area_on_change(key: str, df: pd.DataFrame) -> None:
    """Four Area of GE (dynamic) → 'four_area_ge' table."""
    user_input_on_change(key, df, table_name="four_area_ge")


def other_courses_on_change(key: str, df: pd.DataFrame) -> None:
    """Other Courses (dynamic, outside the study scheme) → 'other_courses' table."""
    user_input_on_change(key, df, table_name="other_courses")




def english_on_change(key: str, df: pd.DataFrame) -> None:
    """English Language catalogue (fixed rows) → 'english' table.

    Like data_on_change, the course identity is the row's index label (the
    HK course code from english_lang_course_list.json), so editing display
    text cannot hijack the stored course_id. Unlike data_on_change, rows
    land in the section's own table. Ticking a row without a Study Period
    saves a "selected, not scheduled yet" row; clearing the period keeps the
    tick so the course returns to the Planner backlog. Un-ticking deletes the
    row. Credits are not stored — the planner derives them from the catalogue.
    """
    user_id = st.session_state.get("user_id")
    if not user_id:
        return # Never store data for guest users

    # Guard: index must carry canonical course keys, not RangeIndex row numbers
    if len(df.index) > 0 and not isinstance(df.index[0], str):
        st.error("Table index must carry course keys.")
        return

    edit_state = st.session_state[key]
    edited  = edit_state.get("edited_rows", {})  # {row_index: {column: new_value}}
    deleted = edit_state.get("deleted_rows", []) # [row_index, ...]

    try:
        # Only Selected / Study Period are editable; identity = the index label.
        for index, changes in edited.items():
            row = df.iloc[int(index)]
            course_id = row.name
            period = changes.get("Study Period", row["Study Period"])
            selected = _checkbox_value(changes.get("Selected", row.get("Selected")))

            if "Selected" in changes and _checkbox_value(changes["Selected"]) is False:
                # Un-ticking removes the English course from the plan entirely.
                delete_data(user_id, course_id, table_name="english")
                continue
            if not _period_is_empty(period):
                selected = True # setting a period ticks the course automatically
            if selected is None:
                # Legacy DataFrame without a Selected column: keep the old rule.
                selected = not _period_is_empty(period)
            if not selected:
                delete_data(user_id, course_id, table_name="english")
                continue
            upsert_data(user_id, {
                "id": user_id,
                "course_id": course_id,
                "study_period": None if _period_is_empty(period) else period,
                "selected": True,
            }, table_name="english")

        # Rows are fixed (no add), but honour deletion if it ever occurs.
        for index in deleted:
            delete_data(user_id, df.iloc[int(index)].name, table_name="english")

    except Exception:
        st.error("Failed to save changes, please try again.") # exception chain preserved in traceback


def update_study_period(
    user_id: str,
    course_id: str,
    study_period,
    table_name: str,
    credits: int | None = None,
) -> None:
    """Set (or clear) one course's Study Period from the Planner tab.

    The Planner is normally read-only; this is its single write path. The row
    stays selected either way — clearing the period sends the course back to
    the backlog instead of removing it. `credits` is only persisted for the
    user-input tables, which have no catalogue to derive credits from.
    """
    if table_name not in _ALL_TABLES:
        raise ValueError(f"Unknown study plan table: {table_name}")

    payload: dict[str, Any] = {
        "id": user_id,
        "course_id": course_id,
        "study_period": None if _period_is_empty(study_period) else study_period,
        "selected": True,
    }
    if table_name in _INPUT_TABLES:
        payload["credits"] = credits if credits is not None else 0
    upsert_data(user_id, payload, table_name=table_name)


def fetch_data(user_id : str, 
               table_name : str = "study_plan") -> list[dict]:
    
    response = (
        client.table(table_name)
        .select("*")
        .eq("id", user_id)
        .execute()
    )
    return response.data # type: ignore[return-value]

def upsert_data(user_id : str, 
                data : dict[str, Any],
                table_name : str = "study_plan") -> list[dict]:
    
    response = (
        client.table(table_name)
        .upsert(data, on_conflict = "id,course_id") # conflict target must match the DB unique constraint
        .execute()
    )
    return response.data # type: ignore[return-value]

def delete_data(user_id : str,
                course_id : str,
                table_name : str = "study_plan") -> None:

    (
        client.table(table_name)
        .delete()
        .eq("id", user_id)
        .eq("course_id", course_id)
        .execute()
    )

def fetch_all_planned(user_id : str) -> list[dict]:
    """Fetch every saved course across all tables, tagged with source table.

    Returns a flat list of dicts, each with course_id, study_period, selected,
    and a 'source' key identifying the originating table. Rows include
    selected-but-unscheduled courses (study_period None): callers decide
    whether to filter them with is_selected().
    """
    result : list[dict] = []
    for table in _ALL_TABLES:
        for row in fetch_data(user_id, table):
            entry = dict(row)
            entry["source"] = table
            result.append(entry)
    return result


def fetch_user_config(user_id : str) -> dict[str, Any] | None:
    """Fetch the user's saved preferences row, or None when it does not exist.

    The user_config table is created by a separate migration; until then a
    read failure must not break the app, so it degrades to None (callers fall
    back to their defaults and the stored choice is simply not restored).
    """
    try:
        response = (
            client.table(_USER_CONFIG_TABLE)
            .select("*")
            .eq("id", user_id)
            .execute()
        )
    except Exception:
        return None

    rows = response.data or []
    return rows[0] if rows else None


def save_major_2nd(user_id : str, major_2nd : str | None) -> None:
    """Upsert the 2nd Major chosen on the main page (one row per user)."""
    (
        client.table(_USER_CONFIG_TABLE)
        .upsert(
            {"id": user_id, "major_2nd": major_2nd},
            on_conflict = "id", # one preferences row per user
        )
        .execute()
    )



def save_notice_version(user_id : str, version : int) -> None:
    """Record the highest announcement version the user has acknowledged.

    Only the notice_version column is sent; PostgREST updates the provided
    columns on conflict, so this must not clobber major_2nd (and vice versa).
    """
    (
        client.table(_USER_CONFIG_TABLE)
        .upsert(
            {"id": user_id, "notice_version": version},
            on_conflict = "id", # one preferences row per user
        )
        .execute()
    )

# client = initialize_client()
# data = fetch_data(client, "dfe85cef-2f75-4df2-80b5-891a1bbbf583")
# print(data)
# new_data = upsert_data(
#     client,
#     "dfe85cef-2f75-4df2-80b5-891a1bbbf583",
#     {
#         "id" : "dfe85cef-2f75-4df2-80b5-891a1bbbf583",
#         "course_id" : "CSC1001",
#         "study_period" : "Year 4 Sem 2"
#     }
# )
# print("New data:", new_data)