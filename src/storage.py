from supabase import create_client, Client
import streamlit as st

# Initialize client
_url : str = st.secrets["SUPABASE_URL"]
_key : str = st.secrets["SUPABASE_KEY"] 
client: Client = create_client(_url, _key)


def data_on_change(*args):
    key = args[0]
    edit_state = st.session_state[key]["edited_rows"]
    st.write("编辑详情：", edit_state)
    st.write(args)


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
        .upsert(data)
        .execute()
    )
    return response.data # type: ignore[return-value]
    
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