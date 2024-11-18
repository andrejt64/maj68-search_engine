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
st.title("Advanced Search Tool for Person Data")

# Normalize the entire dataset for suggestions
normalized_data = data.applymap(normalize_string)

# Search Type
search_type = st.radio("Search Mode:", ["Global Search", "Field-Specific Search"])

# Column Selection for Field-Specific Search
if search_type == "Field-Specific Search":
    column = st.selectbox("Choose column to search in:", data.columns)
else:
    column = None

# Generate Suggestions
if column:
    # Get unique, normalized values from the selected column
    suggestions = data[column].dropna().astype(str).apply(normalize_string).unique()
else:
    # Get unique, normalized values from the entire dataset
    suggestions = pd.Series(normalized_data.values.flatten()).dropna().unique()

# Search Query with Autocomplete
query = st.selectbox(
    "Enter or select your search query:",
    options=[""] + sorted(suggestions),  # Add a blank option for custom input
    format_func=lambda x: x if x else "Type to search or select...",
    key="autocomplete_query",
)

# Allow custom input
query_input = st.text_input("Or type your own search query:", value=query)

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

# Perform the search
if query_input:
    results = search_data(data, query_input, column)
    if not results.empty:
        st.write(f"Found {len(results)} result(s):")
        # Show results with only selected columns
        st.dataframe(results[columns_to_display])
    else:
        st.write("No results found.")
