import pandas as pd
import streamlit as st
import unicodedata

# -----------------------------
# 1. Funkcija za normalizacijo nizov
# -----------------------------
def normalize_string(s):
    """
    Normalizira niz tako, da nadomesti črke s poudarjenimi znaki z njihovimi ASCII
    ekvivalenti ter pretvori vse črke v male.
    """
    if not isinstance(s, str):
        return s
    s = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in s if not unicodedata.combining(c)).lower()

# -----------------------------
# 2. Nalaganje podatkov (predpomnjenje)
# -----------------------------
@st.cache_data
def load_data():
    """
    Naloži podatke iz Excel datoteke in vrne DataFrame.
    """
    return pd.read_excel("LIST_type=person_search-engine.xlsx", sheet_name="Sheet2")

# -----------------------------
# 3. Funkcija za iskanje
# -----------------------------
def search_data(dataframe, query, column=None, match_type="Delno ujemanje"):
    """
    Išče po DataFrame-u za vrstice, ki vsebujejo 'query'.
    Lahko išče po določenem stolpcu ali po celotnem DataFrame-u.
    
    Parameters:
        dataframe (pd.DataFrame): Podatkovni okvir za iskanje.
        query (str): Iskalna poizvedba.
        column (str, optional): Specifični stolpec za iskanje.
        match_type (str): Tip ujemanja - "Delno ujemanje" ali "Natančno ujemanje".
    
    Returns:
        pd.DataFrame: Rezultati iskanja.
    """
    normalized_query = normalize_string(query)
    if column:
        # Iskanje v specifičnem stolpcu
        if match_type == "Delno ujemanje":
            mask = dataframe[column].apply(normalize_string).str.contains(normalized_query, na=False)
        else:  # Natančno ujemanje
            mask = dataframe[column].apply(normalize_string) == normalized_query
        return dataframe[mask]
    else:
        # Globalno iskanje po vseh stolpcih
        if match_type == "Delno ujemanje":
            mask = dataframe.apply(
                lambda row: row.astype(str).apply(normalize_string).str.contains(normalized_query).any(),
                axis=1
            )
        else:  # Natančno ujemanje
            mask = dataframe.apply(
                lambda row: row.astype(str).apply(normalize_string) == normalized_query).any(axis=1)
        return dataframe[mask]

# -----------------------------
# 4. Nastavitve aplikacije
# -----------------------------
st.title("Maj68-Search-Engine-alfa")

# Naloži podatke
data = load_data()

# Normalizacija podatkov za predlog
normalized_data = data.applymap(normalize_string)

# Izbira načina iskanja
search_type = st.radio("Način iskanja:", ["Globalno iskanje", "Iskanje po specifičnem stolpcu"])

# Izbira stolpca samo, če je izbrano iskanje po specifičnem stolpcu
if search_type == "Iskanje po specifičnem stolpcu":
    column = st.selectbox("Izberi stolpec za iskanje:", data.columns)
else:
    column = None

# Izbira tipa ujemanja
match_type = st.radio("Tip ujemanja:", ["Delno ujemanje", "Natančno ujemanje"], index=0)

# Vnos poizvedbe
query_input = st.text_input("Začni tipkati svojo poizvedbo:")

# Generiranje predlogov
if column:
    # Pridobi unikatne, normalizirane vrednosti iz izbranega stolpca
    column_data = data[column].dropna().astype(str)
else:
    # Združi vse stolpce v eno serijo za globalne predloge
    column_data = pd.Series(data.values.flatten()).dropna().astype(str)

# Funkcija za pridobivanje predlogov
def get_suggestions(query, column_data, max_suggestions=10):
    normalized_query = normalize_string(query)
    if normalized_query:
        mask = column_data.apply(normalize_string).str.contains(normalized_query, na=False)
        suggestions = column_data[mask].unique()
        return suggestions[:max_suggestions]
    else:
        return pd.Series([])

# Prikaži predloge, če obstajajo
if query_input:
    suggestions = get_suggestions(query_input, column_data)
    if len(suggestions) > 0:
        st.write("Predlogi:")
        for suggestion in suggestions:
            st.write(f"- {suggestion}")
    else:
        st.write("Predlogi niso na voljo.")

# Izbira stolpcev za prikaz rezultatov
columns_to_display = st.multiselect("Izberi stolpce za prikaz:", data.columns, default=list(data.columns))

# Izvedba iskanja
if query_input:
    results = search_data(data, query_input, column, match_type)
    if not results.empty:
        st.write(f"Najdenih {len(results)} rezultatov:")
        st.dataframe(results[columns_to_display])
    else:
        st.write("Ni najdenih rezultatov.")
