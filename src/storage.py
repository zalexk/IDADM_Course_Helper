from supabase import create_client, Client
import streamlit as st
import pandas as pd

# Initialize client
_url : str = st.secrets["SUPABASE_URL"]
_key : str = st.secrets["SUPABASE_KEY"] 
client: Client = create_client(_url, _key)


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

            upsert_data(user_id, {
                "id": user_id,
                "course_id": df.iloc[int(index)].name,
                "study_period": changes.get("Study Period", base["Study Period"]),
            })

        # 2) Added rows: already complete records (dormant while num_rows="fixed")
        for row in added:
            upsert_data(user_id, {
                "id": user_id,
                "course_id": row["CUHK"],
                "study_period": row["Study Period"],
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
        for index, changes in edited.items():
            base = df.iloc[int(index)]
            course_id = changes.get("CUHK", base["CUHK"])
            if not course_id:
                continue # nothing to store yet
            upsert_data(user_id, {
                "id": user_id,
                "course_id": course_id,
                "study_period": changes.get("Study Period", base["Study Period"]),
            }, table_name=table_name)

        # 2) Added rows: complete records; course_id is the typed "CUHK" value.
        for row in added:
            course_id = row.get("CUHK", "")
            if not course_id:
                continue
            upsert_data(user_id, {
                "id": user_id,
                "course_id": course_id,
                "study_period": row.get("Study Period", ""),
            }, table_name=table_name)

        # 3) Deleted rows: remove by the original row's "CUHK" cell.
        for index in deleted:
            course_id = df.iloc[int(index)]["CUHK"]
            if course_id:
                delete_data(user_id, course_id, table_name=table_name)

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
                data : dict[str, str], 
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
    """Fetch all planned courses across all tables, tagged with source table.

    Returns a flat list of dicts, each with course_id, study_period, and a
    'source' key identifying the originating table.
    """
    result : list[dict] = []
    for table in ("study_plan", "pe", "college_ge", "four_area_ge"):
        for row in fetch_data(user_id, table):
            entry = dict(row)
            entry["source"] = table
            result.append(entry)
    return result
    
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