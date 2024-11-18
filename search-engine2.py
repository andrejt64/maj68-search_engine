import pandas as pd
import streamlit as st
import unicodedata

# Normalize strings to treat "č", "ć", "c"; "š", "s"; and "ž", "z" as equivalent
def normalize_string(s):
    if not isinstance(s, str):
        return s
    s = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in s if not unicodedata.combining(c)).lower()

# Load the data using st.cache_data for efficient caching
@st.cache_data
def load_data():
    return pd.read_excel("LIST_type=person_search-engine.xlsx", sheet_name="Sheet2")

data = load_data()

# App Title
st.title("May68-Search-Engine")

# Search Type
search_type = st.radio("Search Mode:", ["Global Search", "Field-Specific Search"])

# Input Query
query = st.text_input("Enter your search query:")

# Column Selection for Field-Specific Search
if search_type == "Field-Specific Search":
    column = st.selectbox("Choose column to search in:", data.columns)
else:
    column = None

# Column Selection for Result Presentation
columns_to_display = st.multiselect("Choose columns to display:", data.columns, default=data.columns)

# Search Logic
def search_data(dataframe, query, column=None):
    normalized_query = normalize_string(query)
    
    if column:
        # Normalize column values for comparison
        return dataframe[dataframe[column].apply(normalize_string).str.contains(normalized_query, na=False)]
    else:
        # Global search across all columns with normalization
        mask = dataframe.apply(
            lambda row: any(normalized_query in normalize_string(str(value)) for value in row), axis=1
        )
        return dataframe[mask]

# Show Results
if query:
    results = search_data(data, query, column)
    if not results.empty:
        st.write(f"Found {len(results)} result(s):")
        # Show results with only selected columns
        st.dataframe(results[columns_to_display])
    else:
        st.write("No results found.")
