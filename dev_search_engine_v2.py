import pandas as pd
import streamlit as st
import unicodedata

# Nastavitev konfiguracije strani na široko
st.set_page_config(layout="wide")

# Normaliziraj nize, da obravnava "č", "ć", "c"; "š", "s"; in "ž", "z" kot enake
def normalize_string(s):
    if not isinstance(s, str):
        return s
    s = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in s if not unicodedata.combining(c)).lower()

# Naloži podatke z uporabo st.cache_data za učinkovito predpomnjenje
@st.cache_data
def load_data():
    return pd.read_excel("LIST_type=person_search-engine.xlsx", sheet_name="Sheet2")

data = load_data()

# Zagotovi pravilno prikazovanje stolpcev 'year' in 'birth'
if "year" in data.columns:
    data["year"] = data["year"].apply(lambda x: int(x) if pd.notna(x) else "")
if "birth" in data.columns:
    data["birth"] = data["birth"].apply(lambda x: int(x) if pd.notna(x) else "")

# Očisti imena stolpcev, da odstraniš neveljavne možnosti
valid_columns = [col for col in data.columns if col.strip() != "#"]  # Izključi stolpce z le "#"

# Naslov aplikacije
st.title("Maj68-Iskalnik")

# Normaliziraj podatke za predloge za samodejno dopolnjevanje
normalized_data = data.applymap(normalize_string)

# Tip iskanja
search_type = st.radio("Način iskanja:", ["Globalno iskanje", "Iskanje v določenem polju"])

# Izbira stolpca za iskanje v določenem polju
if search_type == "Iskanje v določenem polju":
    column = st.selectbox("Izberi stolpec za iskanje:", valid_columns)
else:
    column = None

# Izbira načina ujemanja
match_type = st.radio("Vrsta ujemanja:", ["Delno ujemanje", "Natančno ujemanje"])

# Vnos poizvedbe
if "query_input" not in st.session_state:
    st.session_state.query_input = ""

# Prikaz iskalnega polja
query_input = st.text_input("Začni vnašati poizvedbo:", value=st.session_state.query_input)

# Generiraj predloge
if column:
    column_data = data[column].dropna().astype(str)
else:
    column_data = pd.DataFrame(
        [(col, value) for col in data.columns for value in data[col].dropna()],
        columns=["stolpec", "vrednost"]
    )

if query_input:
    normalized_query = normalize_string(query_input)
    if column:
        if match_type == "Natančno ujemanje":
            filtered_data = data[column].dropna().astype(str).apply(normalize_string) == normalized_query
        else:  # Delno ujemanje
            filtered_data = data[column].dropna().astype(str).apply(normalize_string).str.contains(normalized_query, na=
