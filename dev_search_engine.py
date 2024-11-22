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
    data["year"] = data["year"].apply(lambda x: int(x) if pd.notna(x) else x)

if "birth" in data.columns:
    data["birth"] = data["birth"].apply(lambda x: int(x) if pd.notna(x) else x)

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
if "query_input" not in st.session_state:
    st.session_state.query_input = ""

# Display search field
query_input = st.text_input("Start typing your query:", value=st.session_state.query_input)

# Generate Suggestions
if column:
    column_data = data[column].dropna().astype(str)
else:
    column_data = pd.DataFrame(
        [(col, value) for col in data.columns for value in data[col].dropna()],
        columns=["column", "value"]
    )

if query_input:
    normalized_query = normalize_string(query_input)
    if column:
        column_data = column_data[column_data.astype(str).apply(normalize_string).str.contains(normalized_query, na=False)].unique()
        suggestions = pd.DataFrame({"column": [column] * len(column_data), "value": column_data})
    else:
        column_data = column_data[column_data["value"].astype(str).apply(normalize_string).str.contains(normalized_query, na=False)]
        column_data = column_data.drop_duplicates(subset="value")
        suggestions = column_data.head(10)

    if not suggestions.empty:
        st.write("Suggestions:")
        for i, row in suggestions.iterrows():
            display_text = f"{row['value']} (from {row['column']})"
            if st.button(display_text, key=f"suggestion_{i}"):
                st.session_state.query_input = row["value"]
                query_input = row["value"]
    else:
        st.write("No suggestions available.")

columns_to_display = st.multiselect("Choose columns to display:", valid_columns, default=valid_columns)

def search_data(dataframe, query, column=None):
    normalized_query = normalize_string(query)
    if column:
        col_data = dataframe[column].dropna().astype(str)
        return dataframe[col_data.apply(normalize_string).str.contains(normalized_query, na=False)]
    else:
        mask = dataframe.apply(
            lambda row: any(normalized_query in normalize_string(str(value)) for value in row), axis=1
        )
        return dataframe[mask]

if query_input:
    results = search_data(data, query_input, column)
    if not results.empty:
        # Ensure proper formatting of 'birth' and 'year' columns
        if "year" in results.columns:
            results["year"] = results["year"].apply(lambda x: str(x) if pd.notna(x) else "")
        if "birth" in results.columns:
            results["birth"] = results["birth"].apply(lambda x: str(x) if pd.notna(x) else "")
        st.write(f"Found {len(results)} result(s):")
        st.dataframe(results[columns_to_display])
    else:
        st.write("No results found.")
