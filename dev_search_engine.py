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

# Naslednji naslov aplikacije
st.title("Iskalnik po bazi lastnih imen korpusa Maj68")

# Naloži podatke z uporabo st.cache_data za učinkovito predpomnjenje
@st.cache_data
def load_data():
    try:
        df = pd.read_excel("LIST_type=person_2025-02-12-iskalnik.xlsx", sheet_name="Sheet1")
    except ValueError:
        st.error("Napaka: Delovni list 'Sheet1' ni najden v datoteki.")
        return pd.DataFrame()
    
    # === Preprocessing Comments (Section 3.3) ===
    # Za vsak vrstico, kjer je 'comment' neprazen:
    # 1. Shranimo originalno vrednost 'character' v začasni stolpec.
    # 2. Nadomestimo 'character' z vrednostjo iz 'real_char'.
    # 3. K 'comment' dodamo originalno vrednost 'character'.
    mask = df['comment'].notna()
    df.loc[mask, 'original_character'] = df.loc[mask, 'character']
    df.loc[mask, 'character'] = df.loc[mask, 'real_char']
    df.loc[mask, 'comment'] = df.loc[mask, 'original_character'].astype(str) + ": " + df.loc[mask, 'comment'].astype(str)
    df.drop(columns=['original_character'], inplace=True)
    # ===========================================
    
    return df

data = load_data()

# Zagotovi pravilno prikazovanje stolpcev 'year' in 'birth'
if "year" in data.columns:
    data["year"] = pd.to_numeric(data["year"], errors="coerce").fillna("").astype(str)
if "birth" in data.columns:
    data["birth"] = data["birth"].apply(
        lambda x: '; '.join([str(int(y)) for y in str(x).split(';') if y.strip().isdigit()]) if pd.notna(x) else ""
    )

# Definiraj seznam stolpcev, ki jih NE želimo prikazovati in ki ne smejo biti na voljo kot možnosti iskanja
excluded_columns = ['id', 'lemma', 'surface', 'comment', 'real_char', 'real_link']

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
    "character": "kanonična oblika"
}

# Normaliziraj podatke za predloge za samodejno dopolnjevanje
normalized_data = data.applymap(normalize_string)

# Tip iskanja
search_type = st.radio("Način iskanja:", ["Globalno iskanje", "Iskanje v določenem polju"])

# === Specific Column Selection (Section 7.2) ===
# Uporabi slovenske imenske oznake, pridobljene iz rename_dict.
if search_type == "Iskanje v določenem polju":
    options = {rename_dict.get(col, col): col for col in valid_columns}
    selected_slov = st.selectbox("Izberi stolpec za iskanje:", list(options.keys()))
    column = options[selected_slov]
else:
    column = None
# ==========================================

# Izbira načina ujemanja
match_type = st.radio("Vrsta ujemanja:", ["Delno ujemanje", "Natančno ujemanje"])

# Vnos poizvedbe
if "query_input" not in st.session_state:
    st.session_state.query_input = ""

query_input = st.text_input("Išči:", value=st.session_state.query_input)

def search_data(dataframe, query, column=None, exact=False):
    normalized_query = normalize_string(query)
    if column:
        # Če iščemo po kanoničnih oblikah, poišči samo po 'character' (ignoriramo 'real_char')
        if column == "character":
            if exact:
                mask = dataframe['character'].astype(str).apply(normalize_string) == normalized_query
            else:
                mask = dataframe['character'].astype(str).apply(normalize_string).str.contains(normalized_query, na=False)
            return dataframe[mask]
        else:
            col_data = dataframe[column].dropna().astype(str)
            if exact:
                return dataframe[col_data.apply(normalize_string) == normalized_query]
            else:
                return dataframe[col_data.apply(normalize_string).str.contains(normalized_query, na=False)]
    else:
        if exact:
            mask = dataframe.apply(lambda row: any(normalized_query == normalize_string(str(value)) for value in row), axis=1)
        else:
            mask = dataframe.apply(lambda row: any(normalized_query in normalize_string(str(value)) for value in row), axis=1)
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

        # Prikaz dodatnih informacij za vsak unikatni zapis
        for _, row in results_unique.iterrows():
            # Uporabi vrednost iz 'character' kot kanonično ime
            canonical = row['character']
            # === Spremenjena maska (Section 10.4) ===
            # Uporabimo natančno primerjanje normaliziranih vrednosti, 
            # da se ne združujejo različni expanderji.
            mask = (data["title_(year)"] == row["title_(year)"]) & (
                data['character'].astype(str).apply(
                    lambda x: normalize_string(x) == normalize_string(canonical)
                )
            )
            # ======================================
            
            # Zberi variacije imen iz stolpcev 'lemma' in 'surface'
            lemmas = data.loc[mask, 'lemma'].dropna().astype(str).unique()
            surfaces = data.loc[mask, 'surface'].dropna().astype(str).unique()
            variations = set(list(lemmas) + list(surfaces))
            
            # Pridobi naslov dela iz stolpca "title_(year)" (ki se prikaže kot "naslov")
            title_val = row["title_(year)"] if "title_(year)" in row.index else ""
            
            # Prikaži expander z dodatnimi informacijami.
            # Expander naslov vsebuje "author" in "title" v oklepaju, npr.: (Edvard Kocbek: Strah in pogum)
            author_val = row["author"] if "author" in row.index else ""
            expander = st.expander(f"{canonical} ({author_val}: {title_val})")
            
            expander.write(f"Variacije imen: {', '.join(variations)}")
            comment_text = row['comment'] if pd.notna(row['comment']) else "Ni komentarja."
            expander.write(f"Komentar: {comment_text}")
            
            wiki_link = row['real_link']
            # Povezavo prikaži le, če je URL veljaven (npr. se začne z "http")
            if isinstance(wiki_link, str) and wiki_link.strip().startswith("http"):
                expander.markdown(f"[Več informacij na Wikipediji]({wiki_link.strip()})")
    else:
        st.write("Ni najdenih rezultatov.")

# Insert dividing line with spacing before and after
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")
st.markdown("<br>", unsafe_allow_html=True)

# Dodaj footer z disclaimerjem in logotipom: disclaimer levo, logotip desno
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown(
        "Projekt LIMO68 je financirala Javna agencija za znanstvenoraziskovalno in "
        "inovacijsko dejavnost Republike Slovenije v okviru raziskovalne infrastrukture "
        "[DARIAH.SI](http://dariah.si/)."
    )
with col2:
    st.image(
        "https://raw.githubusercontent.com/andrejt64/maj68-search_engine/main/DARIAH-SI_logo_CMYK.jpg",
        use_container_width=True
    )
