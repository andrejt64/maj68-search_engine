import pandas as pd
import streamlit as st
import unicodedata

# Nastavi konfiguracijo strani na široko postavitev
st.set_page_config(page_title="Iskalnik po bazi lastnih imen korpusa Maj68")

def normalize_string(s):
    if not isinstance(s, str):
        return s
    s = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in s if not unicodedata.combining(c)).lower()

# Naloži podatke z uporabo st.cache_data za učinkovito predpomnjenje
@st.cache_data
def load_data():
    try:
        df = pd.read_excel("LIST_type=person_2025-02-12-iskalnik.xlsx", sheet_name="Sheet1")  # Updated to correct sheet
    except ValueError:
        st.error("Napaka: Delovni list 'Sheet1' ni najden v datoteki.")
        return pd.DataFrame()
    
    # Replace 'real_char' with 'character' where applicable
    df.loc[df['real_char'].notna(), 'real_char'] = df['character']
    
    # Prepend 'character' to 'comment'
    df['comment'] = df.apply(lambda row: f"{row['character']}: {row['comment']}" if pd.notna(row['comment']) else row['comment'], axis=1)
    
    return df

data = load_data()

# Zagotovi pravilno prikazovanje stolpcev 'year' in 'birth'
if "year" in data.columns:
    data["year"] = pd.to_numeric(data["year"], errors="coerce").fillna("").astype(str)
if "birth" in data.columns:
    data["birth"] = data["birth"].apply(lambda x: '; '.join([str(int(y)) for y in str(x).split(';') if y.strip().isdigit()]) if pd.notna(x) else "")

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

if query_input:
    exact = match_type == "Natančno ujemanje"
    results = search_data(data, query_input, column, exact)
    if not results.empty:
        st.write(f"Najdenih {len(results)} rezultatov:")
        st.dataframe(results[valid_columns])  # Removed formatting to avoid errors with multi-year values
        
        # Prikaz dodatnih informacij ob kliku na znak
        for _, row in results.iterrows():
            char_name = row['character']
            variations = data[data['character'] == char_name]['surface'].dropna().unique()
            wiki_link = row['real_link']
            comment_text = row['comment'] if pd.notna(row['comment']) else "Ni komentarja."
            
            expander = st.expander(f"{char_name}")
            expander.write(f"Variacije imen: {', '.join(variations)}")
            expander.write(f"Komentar: {comment_text}")
            
            if wiki_link:
                expander.markdown(f"[Več informacij na Wikipediji]({wiki_link})")
    else:
        st.write("Ni najdenih rezultatov.")
