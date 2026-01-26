import streamlit.components.v1 as components
from pathlib import Path
import streamlit as st
import pandas as pd
import altair as alt
from PIL import Image

# -----------------------------------------------------------
# STREAMLIT CONFIG (must be before any other st.* output)
# -----------------------------------------------------------
st.set_page_config(layout="wide")

# Toolbar Streamlit: riduci o elimina la barra (icona tabella/expand) sopra i charts
# "minimal" la riduce; con il CSS sotto la nascondiamo comunque del tutto
st.set_option("client.toolbarMode", "minimal")

# -----------------------------------------------------------
# GLOBAL THEME: AUTO LIGHT/DARK (via prefers-color-scheme)
# + SIDEBAR IMPROVEMENTS
# + GREY PANELS/BUTTONS
# + +2px text OUTSIDE TABLE
# NOTE: pill ONLY for "Show extra columns" + "Filter extra columns"
# -----------------------------------------------------------
st.markdown(
    """
    <style>
    /* =======================================================
       AUTO THEME VARIABLES (LIGHT/DARK)
    ======================================================= */
    :root{
      --bg: #ffffff;
      --text: #111111;

      --header-bg: #ffffff;

      --sidebar-bg: #f7f7f7;
      --sidebar-border: rgba(0,0,0,0.12);

      --input-bg: #ffffff;
      --input-border: rgba(0,0,0,0.16);

      --panel-bg: #e9e9e9;
      --panel-border: rgba(0,0,0,0.16);

      --btn-bg: #e6e6e6;
      --btn-bg-hover: #d9d9d9;
      --btn-border: rgba(0,0,0,0.22);

      --plot-card-bg: #f0f0f0;

      --link: #0b62d6;

      --table-th-bg: #eaeaea;
      --table-first-th-bg: #eaeaea;
      --table-first-td-bg: #f2f2f2;
      --table-border: #000000;

      /* Per griglia Altair (soft) in light */
      --grid-opacity: 0.14;
    }

    @media (prefers-color-scheme: dark){
      :root{
        --bg: #000000;
        --text: #ffffff;

        --header-bg: #000000;

        --sidebar-bg: #000000;
        --sidebar-border: rgba(255,255,255,0.12);

        --input-bg: #111111;
        --input-border: rgba(255,255,255,0.16);

        --panel-bg: #2b2b2b;
        --panel-border: rgba(255,255,255,0.18);

        --btn-bg: #2b2b2b;
        --btn-bg-hover: #3a3a3a;
        --btn-border: rgba(255,255,255,0.22);

        --plot-card-bg: #2b2b2b;

        --link: #7cc7ff;

        --table-th-bg: #222222;
        --table-first-th-bg: #222222;
        --table-first-td-bg: #333333;
        --table-border: #000000;

        /* Per griglia Altair (soft) in dark */
        --grid-opacity: 0.10;
      }
    }

    /* =======================================================
       GLOBAL FONT: +2px everywhere OUTSIDE TABLE
       (table handled separately below)
    ======================================================= */
    html, body, [data-testid="stAppViewContainer"]{
        font-size: 22px !important;
        background: var(--bg) !important;
        color: var(--text) !important;
    }

    /* header / toolbar */
    [data-testid="stHeader"], [data-testid="stToolbar"]{
        background: var(--header-bg) !important;
    }

    /* sidebar */
    section[data-testid="stSidebar"]{
        background: var(--sidebar-bg) !important;
        color: var(--text) !important;
        border-right: 1px solid var(--sidebar-border);
    }
    section[data-testid="stSidebar"] *{
        color: var(--text) !important;
    }

    /* inputs background (readable on both themes) */
    .stTextInput input, .stNumberInput input{
        background: var(--input-bg) !important;
        color: var(--text) !important;
        border: 1px solid var(--input-border) !important;
    }

    /* BaseWeb select controls (selectbox + multiselect) */
    section[data-testid="stSidebar"] [data-baseweb="select"] > div{
        background: var(--input-bg) !important;
        color: var(--text) !important;
        box-shadow: none !important;
        border: 1px solid var(--input-border) !important;
    }

    /* remove any weird halo/shadow on labels */
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] .stMarkdown{
        background: transparent !important;
        box-shadow: none !important;
        filter: none !important;
        text-shadow: none !important;
    }

    /* expander as cards (global) */
    [data-testid="stExpander"]{
        background: color-mix(in srgb, var(--bg) 96%, var(--text) 4%) !important;
        border: 1px solid color-mix(in srgb, var(--text) 16%, transparent) !important;
        border-radius: 14px !important;
        padding: 6px 8px !important;
        margin: 10px 0 14px 0 !important;
        box-shadow: none !important;
    }

    /* sidebar expanders: grey panels + pill on title only */
    section[data-testid="stSidebar"] [data-testid="stExpander"]{
        background: var(--panel-bg) !important;
        border: 1px solid var(--panel-border) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] summary{
        display: inline-flex !important;
        align-items: center !important;
        background: var(--panel-bg) !important;
        padding: 6px 10px !important;
        border-radius: 10px !important;
        width: fit-content !important;
        color: var(--text) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] summary *{
        background: transparent !important;
    }

    /* subtle separators */
    .subtle-hr{
        border: 0;
        border-top: 1px solid color-mix(in srgb, var(--text) 10%, transparent);
        margin: 10px 0;
    }

    /* links */
    a { color: var(--link) !important; }

    /* ---------------------------
       SIDEBAR TYPOGRAPHY SIZES
    ---------------------------- */
    section[data-testid="stSidebar"] h2{
      font-size: 24px !important;
      font-weight: 800 !important;
      margin-top: 8px !important;
      margin-bottom: 10px !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stToggle"] label{
      font-size: 24px !important;
      font-weight: 800 !important;
    }

    section[data-testid="stSidebar"] [data-testid="stExpander"] summary{
      font-size: 20px !important;
      font-weight: 750 !important;
    }

    .sidebar-section-title{
      font-size: 18px;
      font-weight: 700;
      margin: 8px 0 6px 0;
    }

    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown p{
      font-size: 16px !important;
    }

    /* ---------------------------
       ICON SIZE
    ---------------------------- */
    .sidebar-icon img{
      width: 120px !important;
      height: auto !important;
    }

    /* ---------------------------
       GREY BACKGROUND FOR DOWNLOAD BUTTONS
    ---------------------------- */
    [data-testid="stDownloadButton"] button{
        background: var(--btn-bg) !important;
        color: var(--text) !important;
        border: 1px solid var(--btn-border) !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
    }
    [data-testid="stDownloadButton"] button:hover{
        background: var(--btn-bg-hover) !important;
        border-color: color-mix(in srgb, var(--btn-border) 70%, var(--text) 30%) !important;
    }

    /* ---------------------------
       BARPLOT CONTAINER GREY BACKGROUND
       + IMPORTANT: set color so Altair "currentColor" works
    ---------------------------- */
    .plot-card{
        background: var(--plot-card-bg);
        border: 0px solid var(--panel-border);
        border-radius: 16px;
        padding: 0px;
        margin-top: 6px;
        margin-bottom: 10px;

        /* This is key: Altair labels using currentColor will follow this */
        color: var(--text) !important;
    }

    /* ---------------------------
       REMOVE THE BAR ABOVE CHARTS (Streamlit element toolbar)
       This is the "barra" with icons (table/expand/...) shown in your screenshot
    ---------------------------- */
    div[data-testid="stElementToolbar"]{
        display: none !important;
        height: 0 !important;
        visibility: hidden !important;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------------------------------------
# Load data
# -----------------------------------------------------------
@st.cache_data
def load_data():
    return pd.read_csv("sfile2_NEW_plusFam.csv")

df = load_data()

# -----------------------------------------------------------
# LOAD ICONS (same folder as this script)
# -----------------------------------------------------------
@st.cache_resource
def load_icons():
    base_dir = Path(__file__).resolve().parent

    def safe_open(filename):
        path = base_dir / filename
        try:
            return Image.open(path)
        except Exception:
            return None

    return {
        "1. Cardiorespiratory system": safe_open("cardio.png"),
        "2. Digestive & Metabolic system": safe_open("gastro.png"),
        "3. Neuro-Endocrine system": safe_open("neuro.png"),
        "4. Immune / Hematolymphoid system": safe_open("immune.png"),
        "5. Musculoskeletal & Integumentary system": safe_open("muscle.png"),
        "6. Urogenital & Reproductive system": safe_open("reproductive.png"),
        "Other system": safe_open("other.png"),
    }

SYSTEM_ICONS = load_icons()

# -----------------------------------------------------------
# PREPROCESSING FIXES
# -----------------------------------------------------------
df = df.replace(["nan", "NaN", "NAN", "-", ""], pd.NA)

expected_cols = [
    "miRNA",
    "Conservation",
    "Pan_troglodytes","Pan_paniscus","Macaca_mulatta","Lemur_catta","Felis_catus",
    "Sus_scrofa","Bos_taurus","Mus_musculus","Gallus_gallus","Xenopus_tropicalis",
    "Danio_rerio","Takifugu_rubripes",
    "Expression",
    "blood","colon","liver","brain","oral_cavity","plasma","lung","kidney","PBMC","heart","serum",
    "milk","placenta","astrocyte","glandular_breast_tissue","cartilage","adrenal_gland",
    "amniotic_fluid","artery","lymphocyte_B","stomach","epidermis","bone","thyroid","skin",
    "saliva","pancreas","sperm","bronchus","embryo","feces","ileum","retina","lavage","uterus",
    "mesenchymal_stromal_cells","islet","melanocyte","prostate","lymphocyte","cortex","semen",
    "foreskin","neuron","cd34","bone_marrow","fast_twitch","macrophage","ovary",
    "chorionic_villi","cerebellum","urine","duodenum","csf","pleurae","spinal_cord","platelet",
    "testis","bladder","hippocampus","pituitary_gland","cervix","dendritic_cells","larynx",
    "ventricle","limb_muscle","keratinocyte","umbilical_cord","nucleus_pulposus",
    "follicular_fluid","cd19","salivary_glands","basophils","mononuclear_cells","epithelium",
    "adipose","natural_killer","meninges","vein","oocyte","temporomandibular_joint",
    "grey_matter","pharynx","cd4","dermis","aqueous_humor","podocyte","choroid_plexus",
    "esophagus","theca","vaginal_tissue","mesenchymal_stem_cells","tonsil",
    "Structure",
    "Class_miRBase","Class_MirGeneDB",
    "MirGeneDB family","miRBase family",
    "hsa-specificity","Repeat_Class",
    "sequence",
    "family_name_mirbase","family_name_mirgene",
]
for c in expected_cols:
    if c not in df.columns:
        df[c] = pd.NA

# Fix Class_MirGeneDB placeholder
df["Class_MirGeneDB"] = df["Class_MirGeneDB"].fillna("—")
df["Class_MirGeneDB"] = df["Class_MirGeneDB"].replace(
    ["nan", "NaN", "NA", None, pd.NA, ""], "—"
)

# Fix family flags
df["miRBase family"] = df["miRBase family"].fillna("NO")
df["MirGeneDB family"] = df["MirGeneDB family"].fillna("—")

# Repeat class cleanup
def shorten_repeat(val):
    if not isinstance(val, str):
        return val
    if "(" in val:
        val = val.split("(")[0]
    return val.split(",")[0].strip()

df["Repeat_Class"] = df["Repeat_Class"].apply(shorten_repeat)
df["Repeat_Class"] = df["Repeat_Class"].astype("string").str.replace("_", " ", regex=False)

# Keep TRUE/FALSE text for these columns
for c in ["Structure", "Conservation", "Expression"]:
    if c in df.columns:
        df[c] = df[c].map(lambda x: "TRUE" if x is True else ("FALSE" if x is False else x))

# -----------------------------------------------------------
# COLUMN GROUPS
# -----------------------------------------------------------
animal_cols = [
    "Pan_troglodytes","Pan_paniscus","Macaca_mulatta","Lemur_catta","Felis_catus",
    "Sus_scrofa","Bos_taurus","Mus_musculus","Gallus_gallus","Xenopus_tropicalis",
    "Danio_rerio","Takifugu_rubripes"
]
animal_cols = [c for c in animal_cols if c in df.columns]

tissue_cols = [
    "blood","colon","liver","brain","oral_cavity","plasma","lung","kidney","PBMC","heart","serum",
    "milk","placenta","astrocyte","glandular_breast_tissue","cartilage","adrenal_gland",
    "amniotic_fluid","artery","lymphocyte_B","stomach","epidermis","bone","thyroid","skin",
    "saliva","pancreas","sperm","bronchus","embryo","feces","ileum","retina","lavage","uterus",
    "mesenchymal_stromal_cells","islet","melanocyte","prostate","lymphocyte","cortex","semen",
    "foreskin","neuron","cd34","bone_marrow","fast_twitch","macrophage","ovary",
    "chorionic_villi","cerebellum","urine","duodenum","csf","pleurae","spinal_cord","platelet",
    "testis","bladder","hippocampus","pituitary_gland","cervix","dendritic_cells","larynx",
    "ventricle","limb_muscle","keratinocyte","umbilical_cord","nucleus_pulposus",
    "follicular_fluid","cd19","salivary_glands","basophils","mononuclear_cells","epithelium",
    "adipose","natural_killer","meninges","vein","oocyte","temporomandibular_joint",
    "grey_matter","pharynx","cd4","dermis","aqueous_humor","podocyte","choroid_plexus",
    "esophagus","theca","vaginal_tissue","mesenchymal_stem_cells","tonsil",
]
tissue_cols = [c for c in tissue_cols if c and (c in df.columns)]

# -----------------------------------------------------------
# DISPLAY NAMES (species italic)
# -----------------------------------------------------------
def sci_name(col):
    genus, species = col.split("_", 1)
    return f"<i>{genus[0]}. {species}</i>"

animal_display_names = {c: sci_name(c) for c in animal_cols}
animal_sidebar_names = {c: animal_display_names[c].replace("<i>", "").replace("</i>", "") for c in animal_cols}
animal_sidebar_rev = {v: k for k, v in animal_sidebar_names.items()}
tissue_sidebar_names = tissue_cols[:]

# -----------------------------------------------------------
# Tissue "tree" definition
# -----------------------------------------------------------
SYSTEM_TISSUES = {
    "1. Cardiorespiratory system": [
        "heart", "ventricle",
        "artery", "vein",
        "blood", "plasma", "serum", "platelet",
        "lung", "bronchus", "pleurae", "larynx", "pharynx",
    ],
    "2. Digestive & Metabolic system": [
        "oral_cavity", "esophagus", "stomach",
        "duodenum", "ileum", "colon",
        "liver",
        "pancreas", "islet",
        "salivary_glands",
        "feces",
    ],
    "3. Neuro-Endocrine system": [
        "brain", "cortex", "cerebellum", "hippocampus",
        "spinal_cord", "grey_matter", "meninges",
        "choroid_plexus", "csf",
        "retina",
        "neuron", "astrocyte",
        "adrenal_gland", "thyroid", "pituitary_gland",
    ],
    "4. Immune / Hematolymphoid system": [
        "PBMC", "mononuclear_cells",
        "lymphocyte", "lymphocyte_B",
        "cd4", "cd19", "cd34",
        "macrophage", "dendritic_cells",
        "natural_killer", "basophils",
        "tonsil", "bone_marrow",
    ],
    "5. Musculoskeletal & Integumentary system": [
        "bone", "cartilage", "temporomandibular_joint",
        "limb_muscle", "fast_twitch",
        "skin", "epidermis", "dermis",
        "keratinocyte", "melanocyte", "foreskin",
    ],
    "6. Urogenital & Reproductive system": [
        "kidney", "bladder", "urine", "testis", "prostate",
        "uterus", "cervix", "ovary", "vaginal_tissue", "oocyte",
        "embryo", "placenta", "chorionic_villi", "umbilical_cord",
        "follicular_fluid", "amniotic_fluid", "theca", "glandular_breast_tissue", "sperm", "semen",
    ],
    "Other system": [
        "adipose", "epithelium", "podocyte", "milk",
        "mesenchymal_stromal_cells", "mesenchymal_stem_cells",
        "nucleus_pulposus","lavage", "aqueous_humor",
    ],
}

# -----------------------------------------------------------
# SPECIES MAPPING: True/False/NA robust
# -----------------------------------------------------------
binary_map = {
    "TRUE": True, True: True, 1: True,
    "FALSE": False, False: False, 0: False,
    "NA": pd.NA, None: pd.NA, pd.NA: pd.NA, "": pd.NA
}
if animal_cols:
    df[animal_cols] = df[animal_cols].applymap(lambda x: binary_map.get(x, pd.NA))

# -----------------------------------------------------------
# Helper columns for filtering + display helpers
# -----------------------------------------------------------
df["_Structure_tf"] = df["Structure"].astype(str).str.upper()
df["_Expression_tf"] = df["Expression"].astype(str).str.upper()
df["_Conservation_tf"] = df["Conservation"].astype("string").str.strip().str.upper()

df["_miRBase_family_flag"] = df["miRBase family"].astype(str).str.upper()
df["_MirGeneDB_family_flag"] = df["MirGeneDB family"].astype(str).str.upper()

df["Conservation_display"] = (
    df[animal_cols].apply(lambda r: r.isin([True, False]).sum(), axis=1) if animal_cols else pd.NA
)

if tissue_cols:
    tissue_num_all = df[tissue_cols].apply(pd.to_numeric, errors="coerce")
    df["Expression_display"] = (tissue_num_all >= 1.5).sum(axis=1)
else:
    df["Expression_display"] = pd.NA

def format_class_pair(row):
    a = row.get("Class_miRBase", pd.NA)
    b = row.get("Class_MirGeneDB", pd.NA)
    a = "-" if pd.isna(a) or str(a).strip() == "" else str(a).strip()
    b = "-" if pd.isna(b) or str(b).strip() in ["", "—"] else str(b).strip()
    return f"{a}/{b}"

df["Structure_display"] = df.apply(format_class_pair, axis=1)

def family_name_or_single(flag_val, name_val, empty_as=None):
    if str(flag_val).strip().upper() == "YES":
        if pd.isna(name_val) or str(name_val).strip() == "":
            return None
        return str(name_val).strip()
    return empty_as

df["miRBase_family_display"] = df.apply(
    lambda r: family_name_or_single(
        r.get("miRBase family", "NO"),
        r.get("family_name_mirbase", pd.NA),
        empty_as=None
    ),
    axis=1
)

df["MirGeneDB_family_display"] = df.apply(
    lambda r: family_name_or_single(
        r.get("MirGeneDB family", "—"),
        r.get("family_name_mirgene", pd.NA),
        empty_as=None
    ),
    axis=1
)

# -----------------------------------------------------------
# TITLE
# -----------------------------------------------------------
st.title("pre-miRNA Annotation Browser")
st.markdown(
    "Interactively explore and filter pre-miRNA annotations by species conservation, tissue expression, repeat classification and family context."
)

# -----------------------------------------------------------
# SIDEBAR: FILTERS (always visible)
# -----------------------------------------------------------
st.sidebar.header("Filters")

search_term = st.sidebar.text_input("Search any column:", key="search_any")

pass_options = ["PASSED", "NOT PASSED"]
conservation_selected = st.sidebar.multiselect("Conservation:", pass_options, default=[], key="ms_conservation")
expression_selected   = st.sidebar.multiselect("Expression:",   pass_options, default=[], key="ms_expression")
structure_selected    = st.sidebar.multiselect("Structure:",    pass_options, default=[], key="ms_structure")

family_options = [
    "Single miRNAs – miRBase",
    "Single miRNAs – MirGeneDB",
    "miRNAs in family – miRBase",
    "miRNAs in family – MirGeneDB",
]
family_selected = st.sidebar.multiselect("Family:", family_options, default=[], key="ms_family")

hsa_options = ["Only hsa-specific", "Not hsa-specific"]
hsa_selected = st.sidebar.multiselect("hsa specificity:", hsa_options, default=[], key="ms_hsa")

repeats_selected = st.sidebar.multiselect(
    "Repeat class:",
    sorted(df["Repeat_Class"].dropna().unique()) if "Repeat_Class" in df.columns else [],
    default=[],
    key="ms_repeat",
)

# -----------------------------------------------------------
# SIDEBAR: ADVANCED OPTIONS
# -----------------------------------------------------------
st.sidebar.markdown("---")
show_adv = st.sidebar.toggle("Advanced options", value=False, key="show_adv")

if show_adv:
    # --- SECTION 1: Show extra columns ---
    with st.sidebar.expander("Show extra columns", expanded=True):

        animals_to_show_sidebar = st.multiselect(
            "Show species columns:",
            list(animal_sidebar_names.values()),
            default=[],
            key="show_species_cols",
        )
        animals_to_show = [animal_sidebar_rev[x] for x in animals_to_show_sidebar]

        tissues_to_show = st.multiselect(
            "Show tissue columns:",
            tissue_sidebar_names,
            default=[],
            key="show_tissue_cols",
        )

        show_class_cols = st.checkbox("Show Class columns", value=False, key="show_class_cols")

    st.sidebar.markdown("<hr class='subtle-hr'>", unsafe_allow_html=True)

    # --- SECTION 2: Filter extra columns ---
    with st.sidebar.expander("Filter extra columns", expanded=True):

        st.markdown("<div class='sidebar-section-title'>Conservation</div>", unsafe_allow_html=True)
        species_options = list(animal_sidebar_names.values())

        species_found_sidebar = st.multiselect("Found in:", species_options, default=[], key="cons_species_found")

        if species_found_sidebar:
            stable_unstable = st.multiselect(
                "Structure:",
                ["Stable (R/D)", "Unstable (S/I)"],
                default=[],
                key="cons_stability",
            )
        else:
            stable_unstable = []

        species_na_sidebar = st.multiselect("Not found in:", species_options, default=[], key="cons_species_na")

        st.markdown("<hr class='subtle-hr'>", unsafe_allow_html=True)

        st.markdown(
            "<div class='sidebar-section-title'>Expressed in (select tissues by system):</div>",
            unsafe_allow_html=True
        )
        tissues_filter_set = set()

        for system_name, sys_tissues in SYSTEM_TISSUES.items():
            available = [t for t in sys_tissues if t in tissue_sidebar_names]
            if not available:
                continue

            icon = SYSTEM_ICONS.get(system_name)
            col_icon, col_exp = st.columns([1.6, 10], gap="small")

            with col_icon:
                if icon is not None:
                    st.markdown("<div class='sidebar-icon'>", unsafe_allow_html=True)
                    st.image(icon, width=120)
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.write("")

            with col_exp:
                display_system = system_name.split(". ", 1)[-1].replace(" system", "")
                with st.expander(display_system, expanded=False):
                    picked = st.multiselect("Select tissues", available, key=f"tree_{system_name}")
                    tissues_filter_set.update(picked)

        tissues_filter = sorted(tissues_filter_set)

        st.markdown("<hr class='subtle-hr'>", unsafe_allow_html=True)

        st.markdown("<div class='sidebar-section-title'>Database / Class</div>", unsafe_allow_html=True)
        mirgene_filter = st.selectbox("Database:", ["Show all", "In both", "Only in miRBase"], key="db_filter")

        classes = sorted(df["Class_miRBase"].dropna().unique()) if "Class_miRBase" in df.columns else []
        classes_selected = st.multiselect("Class:", classes, default=[], key="class_filter")

else:
    animals_to_show = []
    tissues_to_show = []
    show_class_cols = False
    tissues_filter = []
    mirgene_filter = "Show all"
    classes_selected = []
    species_na_sidebar = []
    species_found_sidebar = []
    stable_unstable = []


# -----------------------------------------------------------
# APPLY FILTERS
# -----------------------------------------------------------
filtered = df.copy()

def apply_pass_filter(data: pd.DataFrame, selected: list, helper_col: str) -> pd.DataFrame:
    if not selected:
        return data
    want_true = "PASSED" in selected
    want_false = "NOT PASSED" in selected
    if want_true and want_false:
        return data
    if want_true:
        return data[data[helper_col] == "TRUE"]
    if want_false:
        return data[data[helper_col] == "FALSE"]
    return data

filtered = apply_pass_filter(filtered, conservation_selected, "_Conservation_tf")
filtered = apply_pass_filter(filtered, expression_selected,   "_Expression_tf")
filtered = apply_pass_filter(filtered, structure_selected,    "_Structure_tf")

if mirgene_filter == "In both":
    filtered = filtered[filtered["Class_miRBase"] == filtered["Class_MirGeneDB"]]
elif mirgene_filter == "Only in miRBase":
    filtered = filtered[(filtered["Class_miRBase"].notna()) & (filtered["Class_MirGeneDB"] == "—")]

if classes_selected and "Class_miRBase" in filtered.columns:
    filtered = filtered[filtered["Class_miRBase"].isin(classes_selected)]

if family_selected:
    fam_mask = pd.Series(False, index=filtered.index)
    mirbase_flag = filtered["miRBase family"].astype(str).str.strip().str.upper()
    mirgenedb_flag = filtered["MirGeneDB family"].astype(str).str.strip().str.upper()

    if "Single miRNAs – miRBase" in family_selected:
        fam_mask |= (mirbase_flag == "NO")
    if "miRNAs in family – miRBase" in family_selected:
        fam_mask |= (mirbase_flag == "YES")

    if "Single miRNAs – MirGeneDB" in family_selected:
        fam_mask |= (mirgenedb_flag == "NO")
    if "miRNAs in family – MirGeneDB" in family_selected:
        fam_mask |= (mirgenedb_flag == "YES")

    filtered = filtered[fam_mask]

if hsa_selected:
    hsa_flag = filtered["hsa-specificity"].astype(str).str.strip().str.upper()
    hsa_mask = pd.Series(False, index=filtered.index)
    if "Only hsa-specific" in hsa_selected:
        hsa_mask |= (hsa_flag == "YES")
    if "Not hsa-specific" in hsa_selected:
        hsa_mask |= (hsa_flag == "NO")
    filtered = filtered[hsa_mask]

if repeats_selected:
    filtered = filtered[filtered["Repeat_Class"].isin(repeats_selected)]

species_na_cols = [animal_sidebar_rev[x] for x in species_na_sidebar] if species_na_sidebar else []
species_found_cols = [animal_sidebar_rev[x] for x in species_found_sidebar] if species_found_sidebar else []

if species_na_cols:
    tmp_na = filtered[species_na_cols]
    filtered = filtered[tmp_na.isna().all(axis=1)]

if species_found_cols:
    tmp_found = filtered[species_found_cols]
    filtered = filtered[tmp_found.isin([True, False]).all(axis=1)]

    if stable_unstable:
        allowed = []
        if "Stable" in stable_unstable:
            allowed.append(True)
        if "Unstable" in stable_unstable:
            allowed.append(False)
        if allowed:
            filtered = filtered[tmp_found.isin(allowed).all(axis=1)]

if tissues_filter:
    tissue_num = filtered[tissues_filter].apply(pd.to_numeric, errors="coerce")
    expressed_mask = (tissue_num >= 1.5).all(axis=1)
    filtered = filtered[expressed_mask]

if search_term:
    mask = filtered.astype(str).apply(lambda col: col.str.contains(search_term, case=False, na=False)).any(axis=1)
    filtered = filtered[mask]

# -----------------------------------------------------------
# FASTA EXPORT
# -----------------------------------------------------------
def generate_fasta(df_):
    lines = []
    for _, r in df_.iterrows():
        if pd.notna(r.get("sequence", pd.NA)):
            lines.append(f">{r['miRNA']}")
            lines.append(str(r["sequence"]).replace(" ", "").upper())
    return "\n".join(lines)

# -----------------------------------------------------------
# PREP TABLE DISPLAY (WEB)
# -----------------------------------------------------------
df_display = filtered.copy()

df_display["Conservation"] = df_display["Conservation_display"]
df_display["Expression"] = df_display["Expression_display"]
df_display["Structure"] = df_display["Structure_display"]

df_display["miRBase family"] = df_display["miRBase_family_display"]
df_display["MirGeneDB family"] = df_display["MirGeneDB_family_display"]

df_display = df_display.rename(columns=animal_display_names)

if "sequence" in df_display.columns:
    df_display = df_display.drop(columns=["sequence"])

df_display = df_display.rename(columns={
    "Repeat_Class": "Repeat Class",
    "Class_miRBase": "Class miRBase",
    "Class_MirGeneDB": "Class MirGeneDB",
})

mandatory_display_cols = [
    "miRNA","Conservation","Expression","Structure",
    "MirGeneDB family","miRBase family","hsa-specificity","Repeat Class",
]

animals_to_show_display = [animal_display_names[c] for c in animals_to_show if c in animal_display_names]
tissues_to_show_display = [c for c in tissues_to_show if c in df_display.columns]
class_to_show_display = ["Class miRBase", "Class MirGeneDB"] if show_class_cols else []

desired_order = (
    ["miRNA", "Conservation"]
    + animals_to_show_display
    + ["Expression"]
    + tissues_to_show_display
    + ["Structure"]
    + class_to_show_display
    + ["MirGeneDB family","miRBase family","hsa-specificity","Repeat Class"]
)

visible_cols = []
for c in desired_order:
    if (c in mandatory_display_cols) or (c in animals_to_show_display) or (c in tissues_to_show_display) or (c in class_to_show_display):
        if c in df_display.columns:
            visible_cols.append(c)

if not visible_cols:
    visible_cols = [c for c in mandatory_display_cols if c in df_display.columns]

helper_cols = [
    "_Conservation_tf",
    "_Expression_tf","_Structure_tf",
    "_miRBase_family_flag","_MirGeneDB_family_flag",
]
helper_cols_present = [c for c in helper_cols if c in df_display.columns]
df_display = df_display[visible_cols + helper_cols_present]

# -----------------------------------------------------------
# PREP TABLE EXPORT (TSV CLEAN)
# -----------------------------------------------------------
def prepare_tsv_export(df_disp):
    export_df = df_disp.copy()
    export_df = export_df.drop(columns=helper_cols_present, errors="ignore")
    export_df.columns = export_df.columns.str.replace(r"<.*?>", "", regex=True)
    return export_df

tsv_export_df = prepare_tsv_export(df_display)

# -----------------------------------------------------------
# TABLE STYLING
# -----------------------------------------------------------
NA_SPECIES_COLOR = "#D9D9D9"
TRUE_COLOR = "#009E73"
FALSE_COLOR = "#D55E00"
FAM_YES_COLOR = "#f4a582"
FAM_NO_COLOR  = "#92c5de"

REPEAT_NOREPEAT_COLOR = "#c7e9c0"
REPEAT_OTHER_COLOR    = "#e6c28a"

TISSUE_HIGH_BG = "#BDE131"
TISSUE_LOW_BG  = "#FEE08B"

CLASS_R_BG = "#1F78B4"
CLASS_D_BG = "#A6CEE3"
CLASS_I_BG = "#6A3D9A"
CLASS_S_BG = "#CAB2D6"

def color_binary(v):
    if pd.isna(v):
        return f"background-color:{NA_SPECIES_COLOR};"
    if v is True:
        return "background-color:#fdb863;"
    if v is False:
        return "background-color:#b2abd2;"
    return f"background-color:{NA_SPECIES_COLOR};"

def color_hsa(v):
    if pd.isna(v):
        return ""
    return "background-color:#f1b6da;" if str(v) == "YES" else "background-color:#0072B2;"

def hide_text_species(_v):
    return "color: transparent !important; text-shadow: 0 0 0 transparent !important;"

def bg_true_false(flag):
    if pd.isna(flag):
        return ""
    f = str(flag).upper()
    if f == "TRUE":
        return f"background-color:{TRUE_COLOR};"
    if f == "FALSE":
        return f"background-color:{FALSE_COLOR};"
    return ""

def bg_family(flag):
    if pd.isna(flag):
        return ""
    f = str(flag).upper()
    if f == "YES":
        return f"background-color:{FAM_YES_COLOR};"
    if f == "NO":
        return f"background-color:{FAM_NO_COLOR};"
    if str(flag) == "—":
        return ""
    return f"background-color:{FAM_NO_COLOR};"

def bg_repeat(val):
    if pd.isna(val):
        return ""
    v = str(val).strip()
    if v.lower() == "no repeat":
        return f"background-color:{REPEAT_NOREPEAT_COLOR};"
    return f"background-color:{REPEAT_OTHER_COLOR};"

def fmt_2dec(v):
    if pd.isna(v):
        return ""
    try:
        return f"{float(v):.2f}"
    except Exception:
        return str(v)

def tissue_bg(v):
    if pd.isna(v):
        return ""
    try:
        x = float(v)
    except Exception:
        return ""
    if x >= 1.5:
        return f"background-color:{TISSUE_HIGH_BG}; color: black !important;"
    return f"background-color:{TISSUE_LOW_BG}; color: black !important;"

def class_bg(v):
    if pd.isna(v):
        return ""
    s = str(v).strip().upper()
    if s == "R":
        return f"background-color:{CLASS_R_BG}; color: white !important;"
    if s == "D":
        return f"background-color:{CLASS_D_BG}; color: black !important;"
    if s == "I":
        return f"background-color:{CLASS_I_BG}; color: white !important;"
    if s == "S":
        return f"background-color:{CLASS_S_BG}; color: black !important;"
    return ""

visible_species_cols = [animal_display_names[c] for c in animals_to_show if c in animal_display_names]
visible_species_cols = [c for c in visible_species_cols if c in df_display.columns]
visible_tissue_cols = [c for c in tissues_to_show_display if c in df_display.columns]
visible_class_cols = [c for c in class_to_show_display if c in df_display.columns]

styled_df = df_display.style

if visible_species_cols:
    styled_df = (
        styled_df
        .applymap(color_binary, subset=visible_species_cols)
        .applymap(hide_text_species, subset=visible_species_cols)
    )

if "hsa-specificity" in df_display.columns:
    styled_df = (
        styled_df
        .applymap(color_hsa, subset=["hsa-specificity"])
        .applymap(lambda _v: "color: transparent !important; text-shadow: 0 0 0 transparent !important;", subset=["hsa-specificity"])
    )

if "Repeat Class" in df_display.columns:
    styled_df = styled_df.applymap(bg_repeat, subset=["Repeat Class"])

if visible_tissue_cols:
    styled_df = styled_df.format({c: fmt_2dec for c in visible_tissue_cols}, na_rep="")
    styled_df = styled_df.applymap(tissue_bg, subset=visible_tissue_cols)

if visible_class_cols:
    styled_df = styled_df.applymap(class_bg, subset=visible_class_cols)

def style_row(row):
    styles = ["font-weight: 700; font-size: 14px;"] * len(row)
    idx = {c: i for i, c in enumerate(row.index)}

    if "Conservation" in idx and "_Conservation_tf" in idx:
        styles[idx["Conservation"]] += bg_true_false(row["_Conservation_tf"])
    if "Expression" in idx and "_Expression_tf" in idx:
        styles[idx["Expression"]] += bg_true_false(row["_Expression_tf"])
    if "Structure" in idx and "_Structure_tf" in idx:
        styles[idx["Structure"]] += bg_true_false(row["_Structure_tf"])

    if "miRBase family" in idx and "_miRBase_family_flag" in idx:
        styles[idx["miRBase family"]] += bg_family(row["_miRBase_family_flag"])
    if "MirGeneDB family" in idx and "_MirGeneDB_family_flag" in idx:
        styles[idx["MirGeneDB family"]] += bg_family(row["_MirGeneDB_family_flag"])

    return styles

styled_df = styled_df.apply(style_row, axis=1)

if helper_cols_present:
    styled_df = styled_df.hide(axis="columns", subset=helper_cols_present)

html_table = styled_df.hide(axis="index").to_html(escape=False)

# -----------------------------------------------------------
# CSS — TABLE + LEGEND
# -----------------------------------------------------------
custom_css = r"""
<style>
.table-container{
  max-height: 916px;
  overflow-y: auto !important;
  overflow-x: auto !important;
  border: 2px solid var(--table-border);
  margin-bottom: 16px;

  width: 100% !important;
  max-width: 100% !important;
  -webkit-overflow-scrolling: touch;
}

.table-inner{
  display: block !important;
  width: 100% !important;
}

.table-inner table{
  border-collapse: separate !important;
  border-spacing: 0 !important;
  table-layout: fixed !important;
  width: max-content !important;
  min-width: 100% !important;
}

.table-inner th,
.table-inner td{
  border: 1px solid var(--table-border) !important;
  border-radius: 8px !important;

  line-height: 1.25 !important;
  min-height: 42px !important;
  padding: 10px 10px !important;
  font-size: 20px !important;

  width: 200px !important;
  min-width: 200px !important;
  max-width: 200px !important;

  white-space: nowrap !important;
  overflow: hidden !important;

  text-align: center !important;
  font-weight: 700 !important;
  color: black !important;
  vertical-align: middle !important;
}

.table-inner th{
  position: sticky;
  top: 0;
  z-index: 10;
  background-color: var(--table-th-bg) !important;
  color: color-mix(in srgb, var(--text) 95%, transparent) !important;
  font-weight: 800 !important;

  white-space: normal !important;
  overflow: visible !important;
  text-overflow: clip !important;
}

.table-inner th:first-child{
  position: sticky !important;
  left: 0;
  z-index: 30 !important;

  width: 230px !important;
  min-width: 230px !important;
  max-width: 230px !important;

  background-color: var(--table-first-th-bg) !important;
  color: color-mix(in srgb, var(--text) 95%, transparent) !important;
  background-clip: padding-box;
}

.table-inner td:first-child{
  position: sticky !important;
  left: 0;
  z-index: 25 !important;

  width: 230px !important;
  min-width: 230px !important;
  max-width: 230px !important;

  background-color: var(--table-first-td-bg) !important;
  color: color-mix(in srgb, var(--text) 95%, transparent) !important;
  font-weight: 800 !important;
  background-clip: padding-box;
}

.legend-wrap{
  display: flex;
  flex-wrap: wrap;
  gap: 14px 22px;
  align-items: flex-start;
  margin-top: 10px;
  margin-bottom: 18px;
}

.legend-card{
  flex: 1 1 260px;
  min-width: 260px;
  font-size: 18px;
  font-weight: 400;
  line-height: 1.45;
}

.legend-title{
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
}

.legend-row{
  display: flex;
  flex-wrap: wrap;
  gap: 10px 14px;
  align-items: center;
}

.legend-item{
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.swatch{
  width: 18px;
  height: 18px;
  border-radius: 999px;
  display: inline-block;
  vertical-align: middle;
  border: 1px solid color-mix(in srgb, var(--text) 35%, transparent);
  box-sizing: border-box;
}
</style>
"""

# -----------------------------------------------------------
# SHOW TABLE
# -----------------------------------------------------------
st.write(f"Rows shown: **{len(filtered)}**")
st.markdown(
    custom_css
    + "<div class='table-container'><div class='table-inner'>"
    + html_table
    + "</div></div>",
    unsafe_allow_html=True
)

# -----------------------------------------------------------
# LEGEND (below table)
# -----------------------------------------------------------
legend_cards = []

legend_cards.append(f"""
<div class="legend-card">
  <div class="legend-title">Filter</div>
  <div class="legend-row">
    <span class="legend-item"><span class="swatch" style="background:{TRUE_COLOR};"></span>PASSED</span>
    <span class="legend-item"><span class="swatch" style="background:{FALSE_COLOR};"></span>NOT PASSED</span>
  </div>
</div>
""")

legend_cards.append(f"""
<div class="legend-card">
  <div class="legend-title">Family</div>
  <div class="legend-row">
    <span class="legend-item"><span class="swatch" style="background:{FAM_YES_COLOR};"></span>In family</span>
    <span class="legend-item"><span class="swatch" style="background:{FAM_NO_COLOR};"></span>Single</span>
  </div>
</div>
""")

legend_cards.append(f"""
<div class="legend-card">
  <div class="legend-title">hsa specificity</div>
  <div class="legend-row">
    <span class="legend-item"><span class="swatch" style="background:#f1b6da;"></span>hsa-specific</span>
    <span class="legend-item"><span class="swatch" style="background:#0072B2;"></span>Not hsa-specific</span>
  </div>
</div>
""")

legend_cards.append(f"""
<div class="legend-card">
  <div class="legend-title">Repeat Class</div>
  <div class="legend-row">
    <span class="legend-item"><span class="swatch" style="background:{REPEAT_NOREPEAT_COLOR};"></span>No repeat</span>
    <span class="legend-item"><span class="swatch" style="background:{REPEAT_OTHER_COLOR};"></span>Repeat present</span>
  </div>
</div>
""")

species_filter_active = bool(species_found_cols or species_na_cols)
if visible_species_cols or species_filter_active:
    legend_cards.append(f"""
<div class="legend-card">
  <div class="legend-title">Species conservation</div>
  <div class="legend-row">
    <span class="legend-item"><span class="swatch" style="background:#fdb863;"></span>Stable (TRUE)</span>
    <span class="legend-item"><span class="swatch" style="background:#b2abd2;"></span>Unstable (FALSE)</span>
    <span class="legend-item"><span class="swatch" style="background:{NA_SPECIES_COLOR};"></span>Not found (NA)</span>
  </div>
</div>
""")

if visible_tissue_cols:
    legend_cards.append(f"""
<div class="legend-card">
  <div class="legend-title">Tissue value</div>
  <div class="legend-row">
    <span class="legend-item"><span class="swatch" style="background:{TISSUE_HIGH_BG};"></span>RPMM≥1.5</span>
    <span class="legend-item"><span class="swatch" style="background:{TISSUE_LOW_BG};"></span>RPMM&lt;1.5</span>
  </div>
</div>
""")

if visible_class_cols:
    legend_cards.append(f"""
<div class="legend-card">
  <div class="legend-title">Class (miRBase / MirGeneDB)</div>
  <div class="legend-row">
    <span class="legend-item"><span class="swatch" style="background:{CLASS_R_BG};"></span>R</span>
    <span class="legend-item"><span class="swatch" style="background:{CLASS_D_BG};"></span>D</span>
    <span class="legend-item"><span class="swatch" style="background:{CLASS_I_BG};"></span>I</span>
    <span class="legend-item"><span class="swatch" style="background:{CLASS_S_BG};"></span>S</span>
  </div>
</div>
""")

st.markdown(f"<div class='legend-wrap'>{''.join(legend_cards)}</div>", unsafe_allow_html=True)

# -----------------------------------------------------------
# DOWNLOAD BUTTONS (TSV + FASTA) — left + stacked
# -----------------------------------------------------------
st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

btn_col, _ = st.columns([2, 8])
with btn_col:
    st.download_button(
        "Download table (TSV)",
        data=tsv_export_df.to_csv(index=False, sep="\t"),
        file_name="mirna_filtered_table.tsv",
        mime="text/tab-separated-values",
        key="dl_tsv",
        use_container_width=True,
    )

    st.download_button(
        "Get FASTA",
        data=generate_fasta(filtered),
        file_name="mirna_selected.fasta",
        mime="text/plain",
        key="dl_fasta",
        use_container_width=True,
    )

# -----------------------------------------------------------
# BARPLOT (Repeat distribution) — THEME-AWARE
# -----------------------------------------------------------
ucscgb_palette = ["#009ADE","#7CC242","#F98B2A","#E4002B","#B7312C","#E78AC3","#00A4A6","#00458A"]
repeat_order = ["LINE","SINE","LTR","DNA","Satellite repeats","Simple repeats","Low complexity","No repeat","tRNA","RC"]

st.subheader("Repeat class distribution")
st.markdown("<div class='plot-card'>", unsafe_allow_html=True)

if "Repeat_Class" in filtered.columns and filtered["Repeat_Class"].notna().any():
    repeat_counts = filtered.groupby("Repeat_Class").size().reset_index(name="Count")
    repeat_counts["Percent"] = (repeat_counts["Count"] / repeat_counts["Count"].sum() * 100).round(2)

    barplot = (
        alt.Chart(repeat_counts)
        .mark_bar(
            # stroke e testi "auto" col tema grazie a currentColor (eredita da .plot-card { color: var(--text) })
            stroke="currentColor",
            strokeOpacity=0.55,
            strokeWidth=1.2
        )
        .encode(
            x=alt.X(
                "Repeat_Class:N",
                sort=repeat_order,
                title="Repeat class",
                axis=alt.Axis(
                    labelAngle=45,
                    labelFontSize=16.5,
                    titleFontSize=18
                )
            ),
            y=alt.Y(
                "Count:Q",
                title="Count",
                axis=alt.Axis(
                    labelFontSize=16,
                    titleFontSize=18
                )
            ),
            color=alt.Color(
                "Repeat_Class:N",
                scale=alt.Scale(domain=repeat_order, range=ucscgb_palette),
                legend=None
            ),
            tooltip=["Repeat_Class", "Count", "Percent"]
        )
        .properties(height=600)
        # sfondo trasparente, si integra col tuo CSS
        .configure(background="transparent")
        .configure_view(fill="transparent", strokeOpacity=0)
        # assi/titoli in currentColor + griglia "soft" via opacità
        .configure_axis(
            labelColor="currentColor",
            titleColor="currentColor",
            labelFontSize=16,
            titleFontSize=18,
            grid=True,
            gridColor="currentColor",
            gridOpacity=0.12,
            domainColor="currentColor",
            domainOpacity=0.55,
            tickColor="currentColor",
            tickOpacity=0.55
        )
        .configure_title(color="currentColor")
    )

    st.altair_chart(barplot, use_container_width=True)
else:
    st.info("Repeat_Class is missing or empty: barplot not available.")

st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------------------------------------
# FOOTER
# -----------------------------------------------------------
st.markdown("---")
st.caption("pre-miRNA Annotation Browser — Streamlit App")







