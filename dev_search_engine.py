import pandas as pd
import streamlit as st
import unicodedata
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode  # Uvoz st_aggrid

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
    
    # === Section 3.3 – Preprocessing Comments ===
    # Za vsak vrstico, kjer je 'comment' neprazen:
    # 1. Shranimo originalno vrednost 'character' v začasni stolpec.
    # 2. Nadomestimo 'character' z vrednostjo iz 'real_char'.
    # 3. K 'comment' dodamo originalno vrednost 'character'.
    mask = df['comment'].notna()
    df.loc[mask, 'original_character'] = df.loc[mask, 'character']
    df.loc[mask, 'character'] = df.loc[mask, 'real_char']
    df.loc[mask, 'comment'] = df.loc[mask, 'original_character'].astype(str) + ": " + df.loc[mask, 'comment'].astype(str)
    df.drop(columns=['original_character'], inplace=True)
    # ============================================
    
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
    "character": "protagonist"
}

# Normaliziraj podatke za predloge za samodejno dopolnjevanje
normalized_data = data.applymap(normalize_string)

# Tip iskanja
search_type = st.radio("Način iskanja:", ["Globalno iskanje", "Iskanje v določenem polju"])

# === Section 7.2 – Specific Column Selection ===
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
        # Če iščemo po protagonistih, poišči samo po 'character'
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
                return dataframe[col_data.apply(normalize_string) .str.contains(normalized_query, na=False)]
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
        
        # Resetiramo index, da lažje sledimo izbranim vrsticam (dodamo stolpec 'index')
        results = results.reset_index()
        
        # Pripravimo tabelo za prikaz: vključimo index in samo veljavne stolpce,
        # nato preimenujemo stolpce v slovenščino.
        display_results = results[["index"] + valid_columns].rename(columns=rename_dict)
        
        # Konfiguriramo AgGrid, pri čemer stolpec "index" skrijemo.
        gb = GridOptionsBuilder.from_dataframe(display_results)
        gb.configure_column("index", hide=True)
        gb.configure_selection('single', use_checkbox=False)
        grid_options = gb.build()
        
        grid_response = AgGrid(
            display_results,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            fit_columns_on_grid_load=True,
            theme="streamlit"
        )
        
        selected = grid_response['selected_rows']
        if selected:
            # Ustvarimo reverse mapping iz slovenskih nazivov v originalne imenske oznake
            reverse_rename = {v: k for k, v in rename_dict.items()}
            # Izbrane podatke poiščemo v originalnem DataFrame 'results' s pomočjo skritega indeksa
            selected_index = selected[0]["index"]
            selected_details = results[results["index"] == selected_index].iloc[0]
            
            # Iz originalnih vrednosti pripravimo header expanderja
            canonical = selected_details["character"]
            author_val = selected_details["author"] if "author" in selected_details else ""
            title_val = selected_details["title_(year)"] if "title_(year)" in selected_details else ""
            
            # Izračunamo variacije (združimo vrednosti iz stolpcev 'lemma' in 'surface')
            mask = (data["title_(year)"] == selected_details["title_(year)"]) & (
                data['character'].astype(str).apply(lambda x: normalize_string(x) == normalize_string(selected_details["character"]))
            )
            lemmas = data.loc[mask, 'lemma'].dropna().astype(str).unique()
            surfaces = data.loc[mask, 'surface'].dropna().astype(str).unique()
            variations = set(list(lemmas) + list(surfaces))
            
            expander = st.expander(f"{canonical} ({author_val}: {title_val})")
            expander.write(f"Variacije imen: {', '.join(variations) if variations else 'Ni dodatnih variacij.'}")
            comment_text = selected_details["comment"] if pd.notna(selected_details["comment"]) else "Ni komentarja."
            expander.write(f"Komentar: {comment_text}")
            
            wiki_link = selected_details["real_link"]
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
