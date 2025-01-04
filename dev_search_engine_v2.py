import pandas as pd
import streamlit as st
import unicodedata

# Nastavitev konfiguracije strani na široko
st.set_page_config(layout="wide")

# Funkcija za normalizacijo nizov
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

# Funkcija za iskanje podatkov
def search_data(dataframe, query, column=None, exact=False):
    normalized_query = normalize_string(query)
    if column:
        col_data = dataframe[column].dropna().astype(str)
        if exact:
            return dataframe[col_data.apply(normalize_string) == normalized_query]
        else:
            return dataframe[col_data.apply(normalize_string).str.contains(normalized_query, na=False)]
    else:
        if exact:
            mask = dataframe.apply(
                lambda row: any(normalized_query == normalize_string(str(value)) for value in row), axis=1
            )
        else:
            mask = dataframe.apply(
                lambda row: any(normalized_query in normalize_string(str(value)) for value in row), axis=1
            )
        return dataframe[mask]

# Generiraj predloge
if query_input:
    if column:
        if match_type == "Natančno ujemanje":
            filtered_data = data[column].dropna().astype(str).apply(normalize_string) == normalize_string(query_input)
        else:  # Delno ujemanje
            filtered_data = data[column].dropna().astype(str).apply(normalize_string).str.contains(normalize_string(query_input), na=False)
        
        column_data_filtered = data[column][filtered_data].astype(str).unique()
        suggestions = pd.DataFrame({"stolpec": [column] * len(column_data_filtered), "vrednost": column_data_filtered})
    else:
        if match_type == "Natančno ujemanje":
            mask = data.apply(
                lambda row: any(normalize_string(query_input) == normalize_string(str(value)) for value in row), axis=1
            )
        else:  # Delno ujemanje
            mask = data.apply(
                lambda row: any(normalize_string(query_input) in normalize_string(str(value)) for value in row), axis=1
            )
        
        column_data_filtered = data[mask]
        column_data_filtered = column_data_filtered.drop_duplicates(subset="vrednost")
        suggestions = column_data_filtered.head(10)
    
    if not suggestions.empty:
        st.write("Predlogi:")
        for i, row in suggestions.iterrows():
            display_text = f"{row['vrednost']} (iz {row['stolpec']})"
            if st.button(display_text, key=f"suggestion_{i}"):
                st.session_state.query_input = row["vrednost"]
                query_input = row["vrednost"]
    else:
        st.write("Predlogi niso na voljo.")

# Izbira stolpcev za prikaz
columns_to_display = st.multiselect("Izberi stolpce za prikaz:", valid_columns, default=valid_columns)

# Prikaz rezultatov iskanja
if query_input:
    exact = match_type == "Natančno ujemanje"
    results = search_data(data, query_input, column, exact)
    if not results.empty:
        # Izberi stolpce za prikaz
        results_to_display = results[columns_to_display]
        
        # Dodaj možnost sortiranja
        sort_column = st.selectbox("Sortiraj po stolpcu:", columns_to_display, index=0)
        sort_order = st.radio("Vrstni red:", ["Naraščajoče", "Padajoče"])
        results_to_display = results_to_display.sort_values(by=sort_column, ascending=(sort_order == "Naraščajoče"))
        
        # Prikaz DataFrame z Streamlitovimi funkcijami
        st.write(f"Najdenih {len(results)} rezultatov:")
        st.dataframe(results_to_display, use_container_width=True)
    else:
        st.write("Ni najdenih rezultatov.")
