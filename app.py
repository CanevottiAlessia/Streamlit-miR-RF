import streamlit as st
import pandas as pd
import altair as alt
from PIL import Image

# -----------------------------------------------------------
# STREAMLIT CONFIG (must be before any other st.* output)
# -----------------------------------------------------------
st.set_page_config(layout="wide")

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
    def safe_open(path):
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
        "Other": safe_open("other.png"),
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
        "kidney", "bladder", "urine",
        "uterus", "cervix", "ovary", "testis", "prostate",
        "vaginal_tissue",
        "placenta", "chorionic_villi", "umbilical_cord",
        "embryo",
        "oocyte", "sperm", "semen",
        "follicular_fluid", "amniotic_fluid", "theca",
    ],
    "Other": [
        "adipose", "epithelium", "podocyte", "milk",
        "mesenchymal_stromal_cells", "mesenchymal_stem_cells",
        "nucleus_pulposus", "glandular_breast_tissue",
        "lavage", "aqueous_humor",
    ],
}

# -----------------------------------------------------------
# TITLE
# -----------------------------------------------------------
st.title("pre-miRNA Annotation Browser")
st.markdown("Explore pre-miRNA annotations, conservation, repeat classification, family membership and optional tissue/animal columns.")

# -----------------------------------------------------------
# SIDEBAR: BASIC FILTERS (always visible)
# -----------------------------------------------------------
st.sidebar.header("Filters")

search_term = st.sidebar.text_input("Search any column:")

conservation_filter = st.sidebar.selectbox("Conservation:", ["Show all", "PASSED", "NOT PASSED"])
expression_filter   = st.sidebar.selectbox("Expression:",   ["Show all", "PASSED", "NOT PASSED"])
structure_filter    = st.sidebar.selectbox("Structure:",    ["Show all", "PASSED", "NOT PASSED"])

family_filter = st.sidebar.selectbox(
    "Family:",
    ["Show all", "Single miRNAs – miRBase", "Single miRNAs – MirGeneDB",
     "miRNAs in family – miRBase", "miRNAs in family – MirGeneDB"]
)

hsa_filter = st.sidebar.selectbox("hsa specificity:", ["Show all", "Only hsa-specific", "Not hsa-specific"])

repeats_selected = st.sidebar.multiselect(
    "Repeat class:",
    sorted(df["Repeat_Class"].dropna().unique()) if "Repeat_Class" in df.columns else []
)

# -----------------------------------------------------------
# SIDEBAR: ADVANCED OPTIONS (collapsible)
# -----------------------------------------------------------
st.sidebar.markdown("---")
with st.sidebar.expander("Show advanced options", expanded=False):

    st.subheader("Show extra columns")

    animals_to_show_sidebar = st.multiselect(
        "Show species columns:",
        list(animal_sidebar_names.values())
    )
    animals_to_show = [animal_sidebar_rev[x] for x in animals_to_show_sidebar]

    tissues_to_show = st.multiselect(
        "Show tissue columns:",
        tissue_sidebar_names
    )

    show_class_cols = st.checkbox("Show Class columns", value=False)

    st.markdown("---")
    st.subheader("Filter extra columns")

    conservation_state_filter = st.selectbox(
        "Conservation:",
        [
            "Show all",
            "Conserved (stable structure)",
            "Conserved (unstable structure)",
            "Not conserved",
        ]
    )

    species_filter_sidebar = st.multiselect(
        "Conserved in (structure passed):",
        list(animal_sidebar_names.values())
    )
    species_filter_cols = [animal_sidebar_rev[x] for x in species_filter_sidebar]

    st.markdown("Expressed in (select tissues by system):")
    tissues_filter_set = set()

    # --- ICONS + EXPANDERS (icon left, expander right) ---
    for system_name, sys_tissues in SYSTEM_TISSUES.items():
        available = [t for t in sys_tissues if t in tissue_sidebar_names]
        if not available:
            continue

        icon = SYSTEM_ICONS.get(system_name)

        col_icon, col_exp = st.columns([1, 10], gap="small")
        with col_icon:
            if icon is not None:
                st.image(icon, width=60)  # adjust size here if you want
            else:
                st.write("")  # fallback spacing if missing icon

        with col_exp:
            with st.expander(system_name, expanded=False):
                picked = st.multiselect(
                    "Select tissues",
                    available,
                    key=f"tree_{system_name}",
                )
                tissues_filter_set.update(picked)

    tissues_filter = sorted(tissues_filter_set)

    mirgene_filter = st.selectbox(
        "Database:",
        ["Show all", "In both", "Only in miRBase"]
    )

    classes = sorted(df["Class_miRBase"].dropna().unique()) if "Class_miRBase" in df.columns else []
    classes_selected = st.multiselect("Class:", classes)

# Defaults if advanced options never opened
if "animals_to_show" not in locals():
    animals_to_show = []
if "tissues_to_show" not in locals():
    tissues_to_show = []
if "show_class_cols" not in locals():
    show_class_cols = False
if "conservation_state_filter" not in locals():
    conservation_state_filter = "Show all"
if "species_filter_cols" not in locals():
    species_filter_cols = []
if "tissues_filter" not in locals():
    tissues_filter = []
if "mirgene_filter" not in locals():
    mirgene_filter = "Show all"
if "classes_selected" not in locals():
    classes_selected = []

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
# Helper columns for coloring + display columns for table
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
# APPLY FILTERS
# -----------------------------------------------------------
filtered = df.copy()

# PASSED/NOT PASSED (original)
if conservation_filter == "PASSED":
    filtered = filtered[filtered["_Conservation_tf"] == "TRUE"]
elif conservation_filter == "NOT PASSED":
    filtered = filtered[filtered["_Conservation_tf"] == "FALSE"]

if expression_filter == "PASSED":
    filtered = filtered[filtered["_Expression_tf"] == "TRUE"]
elif expression_filter == "NOT PASSED":
    filtered = filtered[filtered["_Expression_tf"] == "FALSE"]

if structure_filter == "PASSED":
    filtered = filtered[filtered["_Structure_tf"] == "TRUE"]
elif structure_filter == "NOT PASSED":
    filtered = filtered[filtered["_Structure_tf"] == "FALSE"]

# Conservation 3-way filter uses SHOWN SPECIES (animals_to_show) with AND logic
if conservation_state_filter != "Show all":
    if animals_to_show:
        tmp = filtered[animals_to_show]
        all_true  = (tmp == True).all(axis=1)
        all_false = (tmp == False).all(axis=1)
        all_na    = tmp.isna().all(axis=1)

        if conservation_state_filter == "Conserved (stable structure)":
            filtered = filtered[all_true]
        elif conservation_state_filter == "Conserved (unstable structure)":
            filtered = filtered[all_false]
        elif conservation_state_filter == "Not conserved":
            filtered = filtered[all_na]

# Class filter
if classes_selected and "Class_miRBase" in filtered.columns:
    filtered = filtered[filtered["Class_miRBase"].isin(classes_selected)]

# Database filter
if mirgene_filter == "In both":
    filtered = filtered[filtered["Class_miRBase"] == filtered["Class_MirGeneDB"]]
elif mirgene_filter == "Only in miRBase":
    filtered = filtered[(filtered["Class_miRBase"].notna()) & (filtered["Class_MirGeneDB"] == "—")]

# Family filter
if family_filter == "Single miRNAs – miRBase":
    filtered = filtered[filtered["miRBase family"] == "NO"]
elif family_filter == "miRNAs in family – miRBase":
    filtered = filtered[filtered["miRBase family"] == "YES"]
elif family_filter == "Single miRNAs – MirGeneDB":
    filtered = filtered[filtered["MirGeneDB family"] == "NO"]
elif family_filter == "miRNAs in family – MirGeneDB":
    filtered = filtered[filtered["MirGeneDB family"] == "YES"]

# hsa specificity
if hsa_filter == "Only hsa-specific":
    filtered = filtered[filtered["hsa-specificity"] == "YES"]
elif hsa_filter == "Not hsa-specific":
    filtered = filtered[filtered["hsa-specificity"] == "NO"]

# Repeat filter
if repeats_selected:
    filtered = filtered[filtered["Repeat_Class"].isin(repeats_selected)]

# Conserved in species (AND): require TRUE in all selected species
if species_filter_cols:
    filtered = filtered[(filtered[species_filter_cols] == True).all(axis=1)]

# Expressed in tissues (AND): each selected tissue must be >= 1.5
if tissues_filter:
    tissue_num = filtered[tissues_filter].apply(pd.to_numeric, errors="coerce")
    expressed_mask = (tissue_num >= 1.5).all(axis=1)
    filtered = filtered[expressed_mask]

# Search (keep last)
if search_term:
    mask = filtered.astype(str).apply(
        lambda col: col.str.contains(search_term, case=False, na=False)
    ).any(axis=1)
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

# Tissue threshold colors (UPDATED)
TISSUE_HIGH_BG = "#BDE131"   # RPMM>=1.5
TISSUE_LOW_BG  = "#FEE08B"   # RPMM<1.5

# Class colors (R/D similar; I/S similar)
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

# species colors + hidden text
if visible_species_cols:
    styled_df = (
        styled_df
        .applymap(color_binary, subset=visible_species_cols)
        .applymap(hide_text_species, subset=visible_species_cols)
    )

# hsa colors + hidden text
if "hsa-specificity" in df_display.columns:
    styled_df = (
        styled_df
        .applymap(color_hsa, subset=["hsa-specificity"])
        .applymap(lambda _v: "color: transparent !important; text-shadow: 0 0 0 transparent !important;", subset=["hsa-specificity"])
    )

# repeat colors
if "Repeat Class" in df_display.columns:
    styled_df = styled_df.applymap(bg_repeat, subset=["Repeat Class"])

# tissue formatting + threshold-based colors
if visible_tissue_cols:
    styled_df = styled_df.format({c: fmt_2dec for c in visible_tissue_cols}, na_rep="")
    styled_df = styled_df.applymap(tissue_bg, subset=visible_tissue_cols)

# class colors (R/D/I/S)
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
# CSS — TABLE + LEGEND + SIDEBAR NORMALIZATION
# -----------------------------------------------------------
custom_css = r"""
<style>
/* ---------------- Sidebar normalization ---------------- */
section[data-testid="stSidebar"] label{
  font-weight: 400 !important;
  font-size: 14px !important;
}
section[data-testid="stSidebar"] .stMarkdown p{
  font-weight: 400 !important;
  font-size: 14px !important;
}

/* ---------------- TABLE: reliable vertical+horizontal scroll ---------------- */
.table-container{
  max-height: 560px;
  overflow-y: auto !important;
  overflow-x: auto !important;   /* <-- forza scroll orizzontale */
  border: 2px solid black;
  margin-bottom: 16px;
  width: 100%;
  -webkit-overflow-scrolling: touch;
}

/* wrapper that can grow beyond container width */
.table-inner{
  display: inline-block !important;
  min-width: 100% !important;     /* se la tabella è stretta, riempie */
  width: max-content !important;  /* se è larga, può superare il container */
}

/* the table can expand when there are many columns, but fills when few */
.table-inner table{
  border-collapse: separate !important;
  border-spacing: 0 !important;

  display: inline-table !important; /* <-- IMPORTANTISSIMO: evita compressione a 100% */
  width: max-content !important;    /* <-- la tabella cresce con le colonne */
  min-width: 100% !important;       /* <-- ma se poche colonne, full width */

  table-layout: fixed !important;   /* <-- colonne tutte uguali */
}

/* equal columns for all cells (except first column overridden below) */
.table-inner th,
.table-inner td{
  border: 1px solid black !important;
  border-radius: 8px !important;
  padding: 4px !important;

  width: 160px !important;        /* <-- ALL columns same width */
  min-width: 160px !important;
  max-width: 160px !important;

  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;

  text-align: center !important;
  font-size: 16px !important;
  font-weight: 700 !important;
  color: black !important;
}

/* sticky header */
.table-inner th{
  position: sticky;
  top: 0;
  z-index: 10;
  background-color: #222 !important;
  color: white !important;
  font-size: 18px !important;
  font-weight: 800 !important;
}

/* sticky first column (miRNA) */
.table-inner th:first-child{
  position: sticky !important;
  left: 0;
  z-index: 30 !important;              /* sopra tutto */
  width: 200px !important;
  min-width: 200px !important;
  max-width: 200px !important;
  background-color: #222 !important;
  color: white !important;
  background-clip: padding-box;
}

.table-inner td:first-child{
  position: sticky !important;
  left: 0;
  z-index: 25 !important;              /* sopra le altre celle */
  width: 200px !important;
  min-width: 200px !important;
  max-width: 200px !important;
  background-color: #333 !important;
  color: white !important;
  font-size: 15px !important;
  font-weight: 800 !important;
  background-clip: padding-box;
}

/* ---------------- LEGEND: unified + responsive ---------------- */
.legend-wrap{
  display: flex;
  flex-wrap: wrap;
  gap: 14px 22px;
  align-items: flex-start;
  margin-top: 10px;
}

.legend-card{
  flex: 1 1 260px;                /* responsive cards */
  min-width: 260px;
  font-size: 14px;
  font-weight: 400;
  line-height: 1.45;
}

.legend-title{
  font-size: 16px;
  font-weight: 400;
  margin-bottom: 6px;
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
  gap: 6px;
}

.swatch{
  width: 16px;
  height: 16px;
  display: inline-block;
  vertical-align: middle;
  border: 1px solid rgba(0,0,0,0.25);
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

# --- Filter PASSED/NOT PASSED
legend_cards.append(f"""
<div class="legend-card">
  <div class="legend-title">Filter</div>
  <div class="legend-row">
    <span class="legend-item"><span class="swatch" style="background:{TRUE_COLOR};"></span>PASSED</span>
    <span class="legend-item"><span class="swatch" style="background:{FALSE_COLOR};"></span>NOT PASSED</span>
  </div>
</div>
""")

# --- Family
legend_cards.append(f"""
<div class="legend-card">
  <div class="legend-title">Family</div>
  <div class="legend-row">
    <span class="legend-item"><span class="swatch" style="background:{FAM_YES_COLOR};"></span>In family</span>
    <span class="legend-item"><span class="swatch" style="background:{FAM_NO_COLOR};"></span>Single</span>
  </div>
</div>
""")

# --- hsa specificity
legend_cards.append(f"""
<div class="legend-card">
  <div class="legend-title">hsa specificity</div>
  <div class="legend-row">
    <span class="legend-item"><span class="swatch" style="background:#f1b6da;"></span>hsa-specific</span>
    <span class="legend-item"><span class="swatch" style="background:#0072B2;"></span>Not hsa-specific</span>
  </div>
</div>
""")

# --- Repeat class
legend_cards.append(f"""
<div class="legend-card">
  <div class="legend-title">Repeat Class</div>
  <div class="legend-row">
    <span class="legend-item"><span class="swatch" style="background:{REPEAT_NOREPEAT_COLOR};"></span>No repeat</span>
    <span class="legend-item"><span class="swatch" style="background:{REPEAT_OTHER_COLOR};"></span>Repeat present</span>
  </div>
</div>
""")

# --- Species (conditional)
if visible_species_cols:
    legend_cards.append(f"""
<div class="legend-card">
  <div class="legend-title">Species conservation</div>
  <div class="legend-row">
    <span class="legend-item"><span class="swatch" style="background:#fdb863;"></span>Conserved (stable structure)</span>
    <span class="legend-item"><span class="swatch" style="background:#b2abd2;"></span>Conserved (unstable structure)</span>
    <span class="legend-item"><span class="swatch" style="background:{NA_SPECIES_COLOR};"></span>Not conserved</span>
  </div>
</div>
""")

# --- Tissue (conditional)
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

# --- Class (conditional)
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
# DOWNLOAD BUTTONS (TSV + FASTA)
# -----------------------------------------------------------
st.markdown("<div style='display:flex; justify-content:flex-end; gap:12px; margin-top:10px;'>", unsafe_allow_html=True)

st.download_button(
    "Download table (TSV)",
    data=tsv_export_df.to_csv(index=False, sep="\t"),
    file_name="mirna_filtered_table.tsv",
    mime="text/tab-separated-values"
)

st.download_button(
    "Get FASTA",
    data=generate_fasta(filtered),
    file_name="mirna_selected.fasta",
    mime="text/plain"
)

st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------------------------------------
# BARPLOT (Repeat distribution)
# -----------------------------------------------------------
ucscgb_palette = ["#009ADE","#7CC242","#F98B2A","#E4002B","#B7312C","#E78AC3","#00A4A6","#00458A"]
repeat_order = ["LINE","SINE","LTR","DNA","Satellite repeats","Simple repeats","Low complexity","No repeat","tRNA","RC"]

st.subheader("Repeat class distribution")

if "Repeat_Class" in filtered.columns and filtered["Repeat_Class"].notna().any():
    repeat_counts = filtered.groupby("Repeat_Class").size().reset_index(name="Count")
    repeat_counts["Percent"] = (repeat_counts["Count"] / repeat_counts["Count"].sum() * 100).round(2)

    barplot = (
        alt.Chart(repeat_counts)
        .mark_bar(stroke="white", strokeWidth=1.5)
        .encode(
            x=alt.X(
                "Repeat_Class:N",
                sort=repeat_order,
                title="Repeat class",
                axis=alt.Axis(labelAngle=45, labelFontSize=14.5, titleFontSize=16)
            ),
            y=alt.Y(
                "Count:Q",
                title="Count",
                axis=alt.Axis(labelFontSize=14, titleFontSize=16)
            ),
            color=alt.Color(
                "Repeat_Class:N",
                scale=alt.Scale(domain=repeat_order, range=ucscgb_palette),
                legend=None
            ),
            tooltip=["Repeat_Class", "Count", "Percent"]
        )
        .properties(height=600, width=700)
    )

    st.altair_chart(barplot)
else:
    st.info("Repeat_Class is missing or empty: barplot not available.")

# -----------------------------------------------------------
# FOOTER
# -----------------------------------------------------------
st.markdown("---")
st.caption("pre-miRNA Annotation Browser — Streamlit App")


