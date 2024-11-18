import pandas as pd
import streamlit as st
import unicodedata

# Normalize strings to treat characters like "č", "ć", "c" as equivalent
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

# Search Type
search_type = st.radio("Search Mode:", ["Global Search", "Field-Specific Search"])
