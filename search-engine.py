import pandas as pd
import streamlit as st

# Load the data
@st.cache
def load_data():
    return pd.read_excel("LIST_type=person_search-engine.xlsx", sheet_name="Sheet2")

data = load_data()

# App Title
st.title("Search Tool for Person Data")

# Search Type
search_type = st.radio("Search Mode:", ["Global Search", "Field-Specific Search"])

# Input Query
query = st.text_input("Enter your search query:")

# Column Selection for Field-Specific Search
if search_type == "Field-Specific Search":
    column = st.selectbox("Choose column:", data.columns)
else:
    column = None

# Search Logic
def search_data(dataframe, query, column=None):
    query = query.lower()
    if column:
        return dataframe[dataframe[column].astype(str).str.lower().str.contains(query, na=False)]
    else:
        return dataframe[dataframe.apply(lambda row: row.astype(str).str.lower().str.contains(query, na=False).any(), axis=1)]

# Show Results
if query:
    results = search_data(data, query, column)
    st.write(f"Found {len(results)} result(s):")
    st.dataframe(results)
