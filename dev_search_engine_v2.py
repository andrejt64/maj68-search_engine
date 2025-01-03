import pandas as pd
import streamlit as st
import unicodedata
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from st_aggrid import JsCode

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
            filtered_data = data[column].dropna().astype(str).apply(normalize_string).str.contains(normalized_query, na=False)
        
        column_data_filtered = data[column][filtered_data].astype(str).unique()
        suggestions = pd.DataFrame({"stolpec": [column] * len(column_data_filtered), "vrednost": column_data_filtered})
    else:
        if match_type == "Natančno ujemanje":
            mask = column_data["vrednost"].astype(str).apply(normalize_string) == normalized_query
        else:  # Delno ujemanje
            mask = column_data["vrednost"].astype(str).apply(normalize_string).str.contains(normalized_query, na=False)
        
        column_data_filtered = column_data[mask]
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
        # Izberi stolpce za prikaz
        results_to_display = results[columns_to_display]

        # Priprava nastavitev za AgGrid
        gb = GridOptionsBuilder.from_dataframe(results_to_display)
        gb.configure_pagination(paginationAutoPageSize=True)  # Omogoči paginacijo
        gb.configure_side_bar()  # Omogoči stransko vrstico za filtriranje
        gb.configure_default_column(editable=False, sortable=True, filter=True)  # Nastavitve stolpcev
        
        # Dodatne stilizacije (opcijsko)
        gb.configure_selection('single', use_checkbox=True, groupSelectsChildren=True)
        
        grid_options = gb.build()

        # Prikaz AgGrid tabele
        st.write(f"Najdenih {len(results)} rezultatov:")
        AgGrid(
            results_to_display,
            gridOptions=grid_options,
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED, 
            update_mode=GridUpdateMode.MODEL_CHANGED, 
            fit_columns_on_grid_load=True,
            theme='dark',  # Lahko poskusite tudi 'light', 'dark', 'blue', 'fresh', 'material'
            enable_enterprise_modules=False,
            height=400,
            width='100%',
        )
    else:
        st.write("Ni najdenih rezultatov.")
