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

# Ensure the year column is displayed correctly
if "year" in data.columns:
    # Convert the 'year' column to an integer or string for proper formatting
    data["year"] = data["year"].apply(lambda x: int(x) if pd.notna(x) else x)

# Sanitize column names to remove invalid options
valid_columns = [col for col in data.columns if col.strip() != "#"]  # Exclude columns with just "#"

# App Title
st.title("Maj68-Search-Engine")

# Normalize the dataset for autocomplete suggestions
normalized_data = data.applymap(normalize_string)

# Search Type
search_type = st.radio("Search Mode:", ["Global Search", "Field-Specific Search"])

# Column Selection for Field-Specific Search
if search_type == "Field-Specific Search":
    column = st.selectbox("Choose column to search in:", valid_columns)
else:
    column = None

# Input Query
query_input = st.text_input("Start typing your query:")

# Store the clicked suggestion using Streamlit's session state
if "selected_suggestion" not in st.session_state:
    st.session_state["selected_suggestion"] = ""

# Update query_input if a suggestion is clicked
if st.session_state["selected_suggestion"]:
    query_input = st.session_state["selected_suggestion"]

# Generate Suggestions
if column:
    # Get unique, normalized values from the selected column
    column_data = data[column].dropna().astype(str)
else:
    # Combine all columns into a single Series for global suggestions
    column_data = pd.Series(data.values.flatten()).dropna().astype(str)

# Match query with suggestions
if query_input:
    normalized_query = normalize_string(query_input)
    suggestions = column_data[column_data.apply(normalize_string).str.contains(normalized_query, na=False)].unique()

    # Display suggestions below the search box
    if len(suggestions) > 0:
        st.write("Suggestions:")
        for suggestion in suggestions[:10]:  # Limit to top 10 suggestions
            if st.button(suggestion):  # Make each suggestion a button
                st.session_state["selected_suggestion"] = suggestion
    else:
        st.write("No suggestions available.")

# Column Selection for Result Presentation
columns_to_display = st.multiselect("Choose columns to display:", valid_columns, default=valid_columns)

# Search Logic
def search_data(dataframe, query, column=None):
    normalized_query = normalize_string(query)
    if column:
        # Normalize column values for comparison
        col_data = dataframe[column].dropna().astype(str)  # Ensure the column is treated as strings
        return dataframe[col_data.apply(normalize_string).str.contains(normalized_query, na=False)]
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
