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
    
    # Če obstaja entry v 'real_char', obdrži 'character' za variacije
    # (torej ne prepisujemo 'real_char' z 'character', kot smo prej delali)
    # df.loc[df['real_char'].notna(), 'real_char'] = df['character']
    
    # Prepend 'character' k 'comment'
    df['comment'] = df.apply(lambda row: f"{row['character']}: {row['comment']}" if pd.notna(row['comment']) else row['comment'], axis=1)
    
    return df

data = load_data()

# Zagotovi pravilno prikazovanje stolpcev 'year' in 'birth'
if "year" in data.columns:
    data["year"] = pd.to_numeric(data["year"], errors="coerce").fillna("").astype(str)
if "birth" in data.columns:
    data["birth"] = data["birth"].apply(lambda x: '; '.join([str(int(y)) for y in str(x).split(';') if y.strip().isdigit()]) if pd.notna(x) else "")

# Definiraj seznam stolpcev, ki jih NE želimo prikazovati in ki ne smejo biti na voljo kot možnosti iskanja
excluded_columns = ['id', 'surface', 'lemma', 'comment', 'real_char', 'real_link']

# Očisti imena stolpcev, da odstraniš neveljavne možnosti (tudi tiste, ki so samo "#")
valid_columns = [col for col in data.columns if col not in excluded_columns and col.strip() != "#"]

# Slovenski prevodi stolpcev za prikaz:
rename_dict = {
    "title_(year)": "naslov",
    "text_id": "id teksta",
    "author": "avtor",
    "publication": "publikacija",
    "gender": "spol",
    "subtype": "podtip",
    "type": "tip",
    "birth": "leto rojstva",
    "text_type": "zvrst",
    "year": "leto izdaje",
    "character": "protagonist"
}

# Naslov aplikacije
st.title("Iskalnik po bazi lastnih imen korpusa Maj68")

# Normaliziraj podatke za predloge za samodejno dopolnjevanje
normalized_data = data.applymap(normalize_string)

# Tip iskanja
search_type = st.radio("Način iskanja:", ["Globalno iskanje", "Iskanje v določenem polju"])

# Če je iskanje v določenem polju, ponudi izbor stolpca med dovoljeni stolpci
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
        # Če iščemo po protagonistih, poišči tako po 'character' kot tudi po 'real_char'
        if column == "character":
            if exact:
                mask = (
                    dataframe['character'].astype(str).apply(normalize_string) == normalized_query
                ) | (
                    dataframe['real_char'].astype(str).apply(normalize_string) == normalized_query
                )
            else:
                mask = (
                    dataframe['character'].astype(str).apply(normalize_string).str.contains(normalized_query, na=False)
                ) | (
                    dataframe['real_char'].astype(str).apply(normalize_string).str.contains(normalized_query, na=False)
                )
            return dataframe[mask]
        else:
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
        
        # Prikaz rezultatov: uporabimo samo dovoljene stolpce in jih preimenujemo v slovenščino
        display_results = results[valid_columns].rename(columns=rename_dict)
        st.dataframe(display_results)
        
        # Če imamo več zadetkov istega 'text_id', prikažemo le enega
        if 'text_id' in results.columns:
            results_unique = results.drop_duplicates(subset=["text_id"])
        else:
            results_unique = results

        # Prikaz dodatnih informacij ob kliku na posamezni zapis
        for _, row in results_unique.iterrows():
            # Določimo kanonično obliko imena: če obstaja entry v 'real_char', jo uporabimo
            if pd.notna(row.get('real_char')) and str(row.get('real_char')).strip() != "":
                canonical = row['real_char']
                # Poišči vse iteracije iz 'character', ki pripadajo tej kanonični obliki
                variations = data[data['real_char'].astype(str).apply(normalize_string) == normalize_string(canonical)]['character'].dropna().unique()
            else:
                canonical = row['character']
                variations = data[data['character'].astype(str).apply(normalize_string) == normalize_string(canonical)]['character'].dropna().unique()
            
            wiki_link = row['real_link']
            comment_text = row['comment'] if pd.notna(row['comment']) else "Ni komentarja."
            
            expander = st.expander(f"{canonical}")
            expander.write(f"Variacije imen: {', '.join(variations)}")
            expander.write(f"Komentar: {comment_text}")
            
            if wiki_link:
                expander.markdown(f"[Več informacij na Wikipediji]({wiki_link})")
    else:
        st.write("Ni najdenih rezultatov.")
