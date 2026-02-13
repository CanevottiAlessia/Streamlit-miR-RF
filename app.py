import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import altair as alt
from pathlib import Path
from PIL import Image
import re
import base64
from io import BytesIO


# -----------------------------------------------------------
# MCGPT: Global UI scaling (approx. -20% vs original)
# Adjust this value if you want the whole UI smaller/larger.
# -----------------------------------------------------------
UI_SCALE = 0.80

# -----------------------------------------------------------
# STREAMLIT CONFIG (must be before any other st.* output)
# -----------------------------------------------------------
st.set_page_config(layout="wide")
st.set_option("client.toolbarMode", "minimal")


# -----------------------------------------------------------
# ✅ FIX: in-page navigation (NO new tab)
# - Clicking a doc link:
#   1) switches to Documentation tab (by TEXT, not index)
#   2) scrolls to the right anchor in the same page
# -----------------------------------------------------------
def _inject_doc_nav_js():
    components.html(
        """
        <script>
        (function () {

          function clickTabByText(tabText) {
            const tabs = window.parent.document.querySelectorAll('button[role="tab"]');
            if (!tabs || tabs.length === 0) return false;

            const target = Array.from(tabs).find(b => (b.innerText || '').trim() === tabText);
            if (target) { target.click(); return true; }
            return false;
          }

          function scrollToId(id) {
            const el = window.parent.document.getElementById(id);
            if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
            return !!el;
          }

          // Global function called by our click handlers
          window.parent.mirrfNav = function(sectionId) {
            // 1) switch tab
            clickTabByText("Documentation");

            // 2) wait for render, then scroll
            let tries = 0;
            const t = setInterval(() => {
              tries++;
              const ok = scrollToId(sectionId);
              if (ok || tries >= 30) clearInterval(t);
            }, 150);
          };

          // Bind clicks to all <a data-doc-id="..."> links (Streamlit-safe)
          function bindDocLinks() {
            const root = window.parent.document;
            const links = root.querySelectorAll('a[data-doc-id]:not([data-doc-bound="1"])');

            links.forEach(a => {
              a.setAttribute("data-doc-bound", "1");
              a.style.cursor = "pointer";

              a.addEventListener("click", function(e){
                e.preventDefault();
                e.stopPropagation();
                const id = a.getAttribute("data-doc-id");
                if (id && window.parent.mirrfNav) window.parent.mirrfNav(id);
              }, true);
            });
          }

          // Streamlit re-renders often -> rebind periodically
          setInterval(bindDocLinks, 600);
          setTimeout(bindDocLinks, 100);

        })();
        </script>
        """,
        height=0,
    )


def doc_jump_link(section_id: str, label: str = "Docs") -> str:
    return f"""
    <a href="#" data-doc-id="{section_id}"
       style="text-decoration:none; font-weight:700;">
       ℹ️ {label}
    </a>
    """


def doc_jump_icon(section_id: str, title: str = "Docs") -> str:
    return f"""
    <a href="#" data-doc-id="{section_id}"
       title="{title}"
       style="
         text-decoration:none;
         font-weight:700;
         font-size: 12px;
         padding: 0 4px;
         line-height: 1;
         display: inline-block;
         transform: translateY(1px);
       ">
       ℹ️
    </a>
    """


# -----------------------------------------------------------
# ✅ NEW: INLINE label + doc icon (same row)
# -----------------------------------------------------------
def sidebar_label_with_doc(label: str, doc_id: str, icon_title="Docs"):
    st.sidebar.markdown(
        f"""
        <div style="
          display:flex;
          align-items:center;
          justify-content:space-between;
          gap:10px;
          margin: 2px 0 6px 0;
        ">
          <div style="font-weight:700;">{label}</div>
          <div style="flex:0 0 auto;">{doc_jump_icon(doc_id, icon_title)}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def sidebar_widget_inline_doc(widget_fn, label: str, doc_id: str, *args, icon_title="Docs", **kwargs):
    # 1) label + icon (inline)
    sidebar_label_with_doc(label, doc_id, icon_title=icon_title)

    # 2) hide Streamlit default label
    if "label_visibility" not in kwargs:
        kwargs["label_visibility"] = "collapsed"

    # most widgets expect a label as first positional argument
    return widget_fn("", *args, **kwargs)


# ✅ helper: render sidebar widget + icon on the same row (OLD - kept for compatibility)
def sidebar_widget_with_doc(widget_fn, doc_id: str, *args, icon_title="Docs", pad_top_px=30, **kwargs):
    col_w, col_i = st.sidebar.columns([12, 1], vertical_alignment="top")
    with col_w:
        out = widget_fn(*args, **kwargs)
    with col_i:
        st.markdown(
            f"<div style='display:flex; justify-content:center; padding-top:{pad_top_px}px;'>"
            f"{doc_jump_icon(doc_id, icon_title)}"
            f"</div>",
            unsafe_allow_html=True,
        )
    return out


# -----------------------------------------------------------
# GLOBAL THEME + RESPONSIVE CSS (LIGHT/DARK + BREAKPOINTS)
# -2px everywhere (outside + inside table)
# + ✅ tab bar bigger + sticky (ROBUST)  <-- FIXED HERE
# + ✅ anchors scroll-margin to avoid sticky bar overlap
# + ✅ tabs bar stays above streamlit header overlays
# -----------------------------------------------------------
st.markdown(
    """
    <style>
    /* =======================================================
       AUTO THEME VARIABLES (LIGHT/DARK)
    ======================================================= */
    :root{
  /* MCGPT: global UI scale */
  --ui-scale: 0.80; /* MCGPT: keep in sync with UI_SCALE */

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

      /* darker system bar (light) */
      --sysbar-bg: #d0d0d0;
      --sysbar-border: rgba(0,0,0,0.20);

      /* Altair grid opacity (light) */
      --grid-opacity: 0.14;

      /* ✅ Streamlit header height estimate for sticky tabs (tweak if needed) */
      --st-header-h: 4rem;
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

        /* darker system bar (dark) */
        --sysbar-bg: #3a3a3a;
        --sysbar-border: rgba(255,255,255,0.18);

        /* Altair grid opacity (dark) */
        --grid-opacity: 0.10;

        /* keep header estimate */
        --st-header-h: 3.5rem;
      }
    }

    /* =======================================================
       GLOBAL FONT: RESPONSIVE (outside table)  (-2px)
    ======================================================= */
    html, body, [data-testid="stAppViewContainer"]{
        font-size: clamp(12px, 1.2vw + 6px, 18px) !important;
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
        /* MCGPT: scale sidebar to match main UI */
        zoom: var(--ui-scale) !important;
        transform-origin: top left;
    }
    section[data-testid="stSidebar"] *{
        color: var(--text) !important;
    }

    /* inputs */
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

    /* sidebar expanders: grey panels + pill on title only (TOP LEVEL) */
    section[data-testid="stSidebar"] [data-testid="stExpander"]{
        background: var(--panel-bg) !important;
        border: 1px solid var(--panel-border) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] > details > summary{
        display: inline-flex !important;
        align-items: center !important;
        background: var(--panel-bg) !important;
        padding: 6px 10px !important;
        border-radius: 10px !important;
        width: fit-content !important;
        color: var(--text) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] > details > summary *{
        background: transparent !important;
    }

    /* subtle separators */
    .subtle-hr{
        border: 0;
        border-top: 1px solid color-mix(in srgb, var(--text) 10%, transparent);
        margin: 5px 0;
    }

    /* links */
    a { color: var(--link) !important; }

    /* ---------------------------
       SIDEBAR TYPOGRAPHY SIZES (-2px)
    ---------------------------- */
    section[data-testid="stSidebar"] h2{
      font-size: 20px !important;
      font-weight: 800 !important;
      margin-top: 8px !important;
      margin-bottom: 10px !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stToggle"] label{
      font-size: 20px !important;
      font-weight: 800 !important;
    }

    section[data-testid="stSidebar"] [data-testid="stExpander"] > details > summary{
      font-size: 16px !important;
      font-weight: 750 !important;
    }

    .sidebar-section-title{
      font-size: 16px;
      font-weight: 700;
      margin: 8px 0 6px 0;
    }

    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown p{
      font-size: 12px !important;
    }

    /* ---------------------------
       ICON SIZE
    ---------------------------- */
    .sidebar-icon img{
      width: 110px !important;
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

    /* main page download buttons smaller (-2px) */
    [data-testid="stDownloadButton"] button{
        padding: 6px 12px !important;
        font-size: 12px !important;
        line-height: 1.1 !important;
        border-radius: 10px !important;
        width: auto !important;
        min-height: 32px !important;
    }

    /* Sidebar normal buttons (e.g., Reset) styled like download buttons */
    section[data-testid="stSidebar"] .stButton > button{
        background: var(--btn-bg) !important;
        color: var(--text) !important;
        border: 1px solid var(--btn-border) !important;
        border-radius: 12px !important;
        font-weight: 800 !important;
        font-size: 12px !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover{
        background: var(--btn-bg-hover) !important;
        border-color: color-mix(in srgb, var(--btn-border) 70%, var(--text) 30%) !important;
    }

    /* ---------------------------
       BARPLOT CONTAINER
       + set color so Altair "currentColor" works
    ---------------------------- */
    .plot-card{
        background: var(--plot-card-bg);
        border: 0px solid var(--panel-border);
        border-radius: 16px;
        padding: 0px;
        margin-top: 6px;
        margin-bottom: 10px;
        color: var(--text) !important;
    }

    /* ---------------------------
       REMOVE THE BAR ABOVE CHARTS (Streamlit element toolbar)
    ---------------------------- */
    div[data-testid="stElementToolbar"]{
        display: none !important;
        height: 0 !important;
        visibility: hidden !important;
    }

    /* =======================================================
       RESPONSIVE BREAKPOINTS (mobile / small screens) (-2px)
    ======================================================= */
    @media (max-width: 900px){
      section[data-testid="stSidebar"] h2{
        font-size: 14px !important;
      }
      section[data-testid="stSidebar"] div[data-testid="stToggle"] label{
        font-size: 14px !important;
      }
      section[data-testid="stSidebar"] label,
      section[data-testid="stSidebar"] .stMarkdown p{
        font-size: 10px !important;
      }
      .sidebar-icon img{
        width: 82px !important;
      }
    }

    /* =======================================================
       TIGHTER VERTICAL SPACE BETWEEN SYSTEM ROWS
    ======================================================= */
    section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]{
      margin-top: 2px !important;
      margin-bottom: 2px !important;
      gap: 0.25rem !important;
    }

    /* =======================================================
       "MATERIAL" ACCORDION MENU FOR SYSTEM EXPANDERS (nested)
    ======================================================= */
    section[data-testid="stSidebar"]
    [data-testid="stExpander"]
    [data-testid="stExpander"]{
      padding: 0 !important;
      margin: 4px 0 !important;
      border-radius: 12px !important;
    }

    section[data-testid="stSidebar"]
    [data-testid="stExpander"]
    [data-testid="stExpander"] > details > summary{
      width: 100% !important;
      display: flex !important;
      align-items: center !important;
      justify-content: flex-start !important;

      background: var(--sysbar-bg) !important;
      border: 1px solid var(--sysbar-border) !important;

      padding: 8px 12px !important;
      border-radius: 10px !important;

      font-size: 12px !important;
      font-weight: 750 !important;

      box-shadow: none !important;
    }

    section[data-testid="stSidebar"]
    [data-testid="stExpander"]
    [data-testid="stExpander"] > details > summary:hover{
      filter: brightness(0.97);
    }

    section[data-testid="stSidebar"]
    [data-testid="stExpander"]
    [data-testid="stExpander"] > details > summary p,
    section[data-testid="stSidebar"]
    [data-testid="stExpander"]
    [data-testid="stExpander"] > details > summary span{
      margin: 0 !important;
      line-height: 1.1 !important;
      font-size: 14px !important;
    }

    /* =======================================================
       ✅ TABS BAR: STICKY (robusto)
    ======================================================= */

    /* IMPORTANTISSIMO: se un genitore ha overflow, sticky non funziona */
    div[data-testid="stAppViewContainer"],
    div[data-testid="stMain"],
    div[data-testid="stTabs"]{
      overflow: visible !important;
    }

    /* se vuoi tener conto della header Streamlit, metti 3.5rem; altrimenti 0px */
    :root{
      --st-header-h: 0px;
      --tabs-h: 58px;  /* se serve aumenta a 64/70 */
    }

    /* la barra vera dei tabs */
    div[data-testid="stTabs"] div[role="tablist"]{
      position: sticky !important;
      top: var(--st-header-h) !important;
      z-index: 10050 !important;
      background: var(--bg) !important;
      border-bottom: 1px solid color-mix(in srgb, var(--text) 12%, transparent) !important;
      padding-top: 6px !important;
      padding-bottom: 6px !important;
    }

    /* stile bottoni tabs */
    div[data-testid="stTabs"] button[role="tab"]{
      font-size: 18px !important;
      font-weight: 800 !important;
      padding: 10px 18px !important;
      border-radius: 14px !important;
    }

    /* =======================================================
       ✅ DOC ANCHORS: prevent being hidden under sticky header+tabs
    ======================================================= */
    .doc-anchor{
      scroll-margin-top: calc(var(--st-header-h) + 90px);
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
        "Others system": safe_open("other.png"),
    }


SYSTEM_ICONS = load_icons()


# -----------------------------------------------------------
# ✅ NEW: DOC ICONS (only used in Documentation tab)
# Files you added on GitHub:
# adv, global, cons1, tissue1, structure, hsa, fam, rep, barplot, reset,
# adv2, cons2, tissue2, database, export, scimmiaBrain, mouseCuore
# -----------------------------------------------------------
@st.cache_resource
def load_doc_icons_b64():
    base_dir = Path(__file__).resolve().parent

    def to_b64_png(filename: str):
        p = base_dir / filename
        try:
            img = Image.open(p).convert("RGBA")
            buf = BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            return None

    # keys == your “logical names”; values == filenames in repo
    icon_files = {
        "adv": "adv.png",
        "global": "global.png",
        "cons1": "cons1.png",
        "tissue1": "tissue1.png",
        "structure": "structure.png",
        "hsa": "hsa.png",
        "fam": "fam.png",
        "rep": "rep.png",
        "barplot": "barplot.png",
        "reset": "reset.png",
        "adv2": "adv2.png",
        "cons2": "cons2.png",
        "tissue2": "tissue2.png",
        "database": "database.png",
        "export": "export.png",
        "scimmiaBrain": "scimmiaBrain.png",
        "mouseCuore": "mouseCuore.png",
    }

    out = {}
    for k, fn in icon_files.items():
        out[k] = to_b64_png(fn)
    return out


DOC_ICONS_B64 = load_doc_icons_b64()


def doc_icon_html(key: str, size_em: float = 1.35, dy_em: float = -0.14, mr_em: float = 0.35) -> str:
    """
    Returns an <img> tag with base64 PNG for inline use in Markdown headings.
    Used ONLY in Documentation.
    """
    b64 = DOC_ICONS_B64.get(key)
    if not b64:
        return ""
    return (
        f"<img src='data:image/png;base64,{b64}' "
        f"style='height:{size_em}em; width:auto; vertical-align:{dy_em}em; margin-right:{mr_em}em;'/>"
    )


def doc_heading(level: int, icon_keys, text: str):
    if isinstance(icon_keys, str):
        icon_keys = [icon_keys]
    icons = "".join(doc_icon_html(k) for k in icon_keys if k)
    hashes = "#" * max(1, min(level, 6))
    st.markdown(f"{hashes} {icons}{text}", unsafe_allow_html=True)


# -----------------------------------------------------------
# PREPROCESSING FIXES
# -----------------------------------------------------------
df = df.replace(["nan", "NaN", "NAN", "-", ""], pd.NA)

expected_cols = [
    "miRNA",
    "Conservation",
    "Pan_troglodytes", "Pan_paniscus", "Macaca_mulatta", "Lemur_catta", "Felis_catus",
    "Sus_scrofa", "Bos_taurus", "Mus_musculus", "Gallus_gallus", "Xenopus_tropicalis",
    "Danio_rerio", "Takifugu_rubripes",
    "Expression",
    "blood", "colon", "liver", "brain", "oral_cavity", "plasma", "lung", "kidney", "PBMC", "heart", "serum",
    "milk", "placenta", "astrocyte", "glandular_breast_tissue", "cartilage", "adrenal_gland",
    "amniotic_fluid", "artery", "lymphocyte_B", "stomach", "epidermis", "bone", "thyroid", "skin",
    "saliva", "pancreas", "sperm", "bronchus", "embryo", "feces", "ileum", "retina", "lavage", "uterus",
    "mesenchymal_stromal_cells", "islet", "melanocyte", "prostate", "lymphocyte", "cortex", "semen",
    "foreskin", "neuron", "cd34", "bone_marrow", "fast_twitch", "macrophage", "ovary",
    "chorionic_villi", "cerebellum", "urine", "duodenum", "csf", "pleurae", "spinal_cord", "platelet",
    "testis", "bladder", "hippocampus", "pituitary_gland", "cervix", "dendritic_cells", "larynx",
    "ventricle", "limb_muscle", "keratinocyte", "umbilical_cord", "nucleus_pulposus",
    "follicular_fluid", "cd19", "salivary_glands", "basophils", "mononuclear_cells", "epithelium",
    "adipose", "natural_killer", "meninges", "vein", "oocyte", "temporomandibular_joint",
    "grey_matter", "pharynx", "cd4", "dermis", "aqueous_humor", "podocyte", "choroid_plexus",
    "esophagus", "theca", "vaginal_tissue", "mesenchymal_stem_cells", "tonsil",
    "Structure",
    "Class_miRBase", "Class_MirGeneDB",
    "MirGeneDB family", "miRBase family",
    "hsa-specificity", "Repeat_Class",
    "sequence",
    "family_name_mirbase", "family_name_mirgene",
]
for c in expected_cols:
    if c not in df.columns:
        df[c] = pd.NA

df["Class_MirGeneDB"] = df["Class_MirGeneDB"].fillna("—")
df["Class_MirGeneDB"] = df["Class_MirGeneDB"].replace(["nan", "NaN", "NA", None, pd.NA, ""], "—")

df["miRBase family"] = df["miRBase family"].fillna("NO")
df["MirGeneDB family"] = df["MirGeneDB family"].fillna("—")


def shorten_repeat(val):
    if not isinstance(val, str):
        return val
    if "(" in val:
        val = val.split("(")[0]
    return val.split(",")[0].strip()


df["Repeat_Class"] = df["Repeat_Class"].apply(shorten_repeat)
df["Repeat_Class"] = df["Repeat_Class"].astype("string").str.replace("_", " ", regex=False)

# ✅ FIX: rename specific repeat labels everywhere (table + plot + filters)
df["Repeat_Class"] = df["Repeat_Class"].replace({
    "DNA": "DNA repeats",
    "Low complexity": "Low complexity repeats",
})

for c in ["Structure", "Conservation", "Expression"]:
    if c in df.columns:
        df[c] = df[c].map(lambda x: "TRUE" if x is True else ("FALSE" if x is False else x))


# -----------------------------------------------------------
# COLUMN GROUPS
# -----------------------------------------------------------
animal_cols = [
    "Pan_troglodytes", "Pan_paniscus", "Macaca_mulatta", "Lemur_catta", "Felis_catus",
    "Sus_scrofa", "Bos_taurus", "Mus_musculus", "Gallus_gallus", "Xenopus_tropicalis",
    "Danio_rerio", "Takifugu_rubripes"
]
animal_cols = [c for c in animal_cols if c in df.columns]

tissue_cols = [
    "blood", "colon", "liver", "brain", "oral_cavity", "plasma", "lung", "kidney", "PBMC", "heart", "serum",
    "milk", "placenta", "astrocyte", "glandular_breast_tissue", "cartilage", "adrenal_gland",
    "amniotic_fluid", "artery", "lymphocyte_B", "stomach", "epidermis", "bone", "thyroid", "skin",
    "saliva", "pancreas", "sperm", "bronchus", "embryo", "feces", "ileum", "retina", "lavage", "uterus",
    "mesenchymal_stromal_cells", "islet", "melanocyte", "prostate", "lymphocyte", "cortex", "semen",
    "foreskin", "neuron", "cd34", "bone_marrow", "fast_twitch", "macrophage", "ovary",
    "chorionic_villi", "cerebellum", "urine", "duodenum", "csf", "pleurae", "spinal_cord", "platelet",
    "testis", "bladder", "hippocampus", "pituitary_gland", "cervix", "dendritic_cells", "larynx",
    "ventricle", "limb_muscle", "keratinocyte", "umbilical_cord", "nucleus_pulposus",
    "follicular_fluid", "cd19", "salivary_glands", "basophils", "mononuclear_cells", "epithelium",
    "adipose", "natural_killer", "meninges", "vein", "oocyte", "temporomandibular_joint",
    "grey_matter", "pharynx", "cd4", "dermis", "aqueous_humor", "podocyte", "choroid_plexus",
    "esophagus", "theca", "vaginal_tissue", "mesenchymal_stem_cells", "tonsil",
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
        "follicular_fluid", "amniotic_fluid", "theca",
        "glandular_breast_tissue", "sperm", "semen",
    ],
    "Others system": [
        "adipose", "epithelium", "podocyte", "milk",
        "mesenchymal_stromal_cells", "mesenchymal_stem_cells",
        "nucleus_pulposus", "lavage", "aqueous_humor",
    ],
}


def system_display_name(system_key: str) -> str:
    return system_key.split(". ", 1)[-1].replace(" system", "")


# -----------------------------------------------------------
# ✅ NEW: keys for "Show extra tissue columns" (per-system)
# -----------------------------------------------------------
def showcols_key(system_name: str) -> str:
    return f"show_cols_{system_name}"


SHOWCOL_KEYS = [showcols_key(sys_name) for sys_name in SYSTEM_TISSUES.keys()]


# -----------------------------------------------------------
# RESET FILTERS
# -----------------------------------------------------------
FILTER_KEYS = [
    "search_any",
    "sb_conservation", "sb_expression", "sb_structure", "sb_hsa",
    "ms_family", "ms_repeat",
    "show_repeat_plot",
    "show_adv",
    "show_species_cols",
    "cons_species_found", "cons_species_na", "cons_stability_choice",
    # removed: "show_tissue_systems",
    # new: per-system tissue column selections
    *SHOWCOL_KEYS,
    "show_class_cols",
    "db_filter",
    "class_filter",
]
for sys_name in SYSTEM_TISSUES.keys():
    FILTER_KEYS.append(f"tree_pos_{sys_name}")
    FILTER_KEYS.append(f"tree_neg_{sys_name}")


def any_filter_active() -> bool:
    if (st.session_state.get("search_any", "") or "").strip():
        return True

    if st.session_state.get("sb_conservation", "Show all") != "Show all":
        return True
    if st.session_state.get("sb_expression", "Show all") != "Show all":
        return True
    if st.session_state.get("sb_structure", "Show all") != "Show all":
        return True
    if st.session_state.get("sb_hsa", "Show all") != "Show all":
        return True

    if st.session_state.get("ms_family", []):
        return True
    if st.session_state.get("ms_repeat", []):
        return True

    if st.session_state.get("show_repeat_plot", False):
        return True

    if st.session_state.get("show_adv", False):
        return True

    if st.session_state.get("show_species_cols", []):
        return True
    if st.session_state.get("cons_species_found", []):
        return True
    if st.session_state.get("cons_species_na", []):
        return True
    if st.session_state.get("cons_stability_choice", "All") != "All":
        return True

    # ✅ NEW: any selected tissue columns to show (per-system)
    for k in SHOWCOL_KEYS:
        if st.session_state.get(k, []):
            return True

    for sys_name in SYSTEM_TISSUES.keys():
        if st.session_state.get(f"tree_pos_{sys_name}", []):
            return True
        if st.session_state.get(f"tree_neg_{sys_name}", []):
            return True

    if st.session_state.get("show_class_cols", False):
        return True
    if st.session_state.get("db_filter", "Show all") != "Show all":
        return True
    if st.session_state.get("class_filter", []):
        return True

    return False


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


# ===========================================================
# TABS BAR (APP / DOCUMENTATION)
# ===========================================================
tab_app, tab_docs = st.tabs(["App", "Documentation"])

# ✅ inject the tab switch + scroll router once
_inject_doc_nav_js()


# -----------------------------------------------------------
# Sidebar: Documentation (internal anchors, no new tab)
# (kept as main sections only)
# -----------------------------------------------------------
with st.sidebar.expander("Documentation", expanded=False):
    st.markdown("- " + doc_jump_link("doc_overview", "Overview"), unsafe_allow_html=True)
    st.markdown("- " + doc_jump_link("doc_key_features", "Key features"), unsafe_allow_html=True)
    st.markdown("- " + doc_jump_link("doc_advanced", "Advanced options"), unsafe_allow_html=True)
    st.markdown("- " + doc_jump_link("doc_export", "Data export"), unsafe_allow_html=True)
    st.markdown("- " + doc_jump_link("doc_use_cases", "Example use cases"), unsafe_allow_html=True)


# ===========================================================
# TAB 1 — APP (DEFAULT)
# ===========================================================
with tab_app:
    # --- HEADER (title + help) ---
    col_title, col_help = st.columns([12, 1])

    with col_title:
        st.title("miR-RF human pre-miRNA Explorer")
        st.markdown(
            "Interactively explore and filter pre-miRNA annotations by species conservation, "
            "tissue expression, repeat classification and family context."
        )

    with col_help:
        with st.popover("❓", use_container_width=True):
            st.markdown("""
### How to use the app
- Use the sidebar on the left to filter the dataset  
- Enable *Advanced options* for additional controls/filters  
- Export **TSV** / **FASTA** at the bottom of the table  
- Try the **Example use cases** presets at the bottom of the scrollable sidebar to quickly apply filter combinations  
- Use **Reset all filters** (bottom and top of the sidebar) to clear everything and start over
""")

    # -----------------------------------------------------------
    # SIDEBAR: FILTERS + inline doc icons (FIXED: ℹ️ next to label)
    # -----------------------------------------------------------
    st.sidebar.header("Filters")

    # ✅ FIX 1: Reset all filters ALSO above the filters in the sidebar
    if any_filter_active():
        st.sidebar.markdown(doc_jump_link("doc_filter_reset", "Docs (Reset)"), unsafe_allow_html=True)
        if st.sidebar.button("Reset all filters", use_container_width=True, key="reset_top"):
            for k in FILTER_KEYS:
                st.session_state.pop(k, None)
            st.session_state["show_adv"] = False
            st.session_state["page"] = 1  # MCGPT: reset pagination
            st.rerun()

    search_term = sidebar_widget_inline_doc(
        st.sidebar.text_input,
        "Search by name:",
        "doc_filter_search_any",
        key="search_any",
    )

    pass_sb_options = ["Show all", "PASSED", "NOT PASSED"]

    conservation_choice = sidebar_widget_inline_doc(
        st.sidebar.selectbox,
        "Conservation:",
        "doc_filter_conservation_pf",
        pass_sb_options,
        index=0,
        key="sb_conservation",
    )

    expression_choice = sidebar_widget_inline_doc(
        st.sidebar.selectbox,
        "Expression:",
        "doc_filter_expression_pf",
        pass_sb_options,
        index=0,
        key="sb_expression",
    )

    structure_choice = sidebar_widget_inline_doc(
        st.sidebar.selectbox,
        "Structure:",
        "doc_filter_structure_pf",
        pass_sb_options,
        index=0,
        key="sb_structure",
    )

    hsa_sb_options = ["Show all", "Only hsa-specific", "Not hsa-specific"]
    hsa_choice = sidebar_widget_inline_doc(
        st.sidebar.selectbox,
        "hsa specificity:",
        "doc_filter_hsa",
        hsa_sb_options,
        index=0,
        key="sb_hsa",
    )

    family_options = [
        "no family – miRBase",
        "no family – MirGeneDB",
        "miRNAs in family – miRBase",
        "miRNAs in family – MirGeneDB",
    ]
    family_selected = sidebar_widget_inline_doc(
        st.sidebar.multiselect,
        "Family:",
        "doc_filter_family",
        family_options,
        default=[],
        key="ms_family",
    )

    repeats_selected = sidebar_widget_inline_doc(
        st.sidebar.multiselect,
        "Repeat class:",
        "doc_filter_repeat",
        sorted(df["Repeat_Class"].dropna().unique()) if "Repeat_Class" in df.columns else [],
        default=[],
        key="ms_repeat",
    )

    show_repeat_plot = sidebar_widget_inline_doc(
        st.sidebar.checkbox,
        "Show repeat class distribution",
        "doc_filter_plot_repeat",
        value=False,
        key="show_repeat_plot",
    )

    # -----------------------------------------------------------
    # SIDEBAR: ADVANCED OPTIONS
    # -----------------------------------------------------------
    animals_to_show = []
    tissues_to_show = []
    tissues_filter = []
    tissues_not_filter = []

    species_na_sidebar = []
    species_found_sidebar = []
    stability_choice = "All"

    show_class_cols = False
    mirgene_filter = "Show all"
    classes_selected = []

    show_adv = sidebar_widget_inline_doc(
        st.sidebar.toggle,
        "Advanced options",
        "doc_advanced_options",
        value=False,
        key="show_adv",
    )

    if show_adv:
        with st.sidebar.expander("Evolutionary conservation", expanded=True):
            # link only to the main subsection (as requested)
            st.sidebar.markdown(
                f"<div style='margin-top:-2px; margin-bottom:6px;'>{doc_jump_link('doc_adv_conservation', 'Docs')}</div>",
                unsafe_allow_html=True
            )

            st.markdown("<div class='sidebar-section-title'>Show extra columns</div>", unsafe_allow_html=True)

            animals_to_show_sidebar = st.multiselect(
                "Show species columns:",
                list(animal_sidebar_names.values()),
                default=[],
                key="show_species_cols",
            )
            animals_to_show = [animal_sidebar_rev[x] for x in animals_to_show_sidebar]

            st.markdown("<hr class='subtle-hr'>", unsafe_allow_html=True)
            st.markdown("<div class='sidebar-section-title'>Filter extra columns</div>", unsafe_allow_html=True)

            species_options = list(animal_sidebar_names.values())

            species_found_sidebar = st.multiselect(
                "Found in:",
                species_options,
                default=[],
                key="cons_species_found",
            )

            if species_found_sidebar:
                stability_choice = st.selectbox(
                    "Structure:",
                    ["All", "Stable (R/D)", "Unstable (S/I)"],
                    index=0,
                    key="cons_stability_choice",
                )
            else:
                stability_choice = "All"

            species_na_sidebar = st.multiselect(
                "Not found in:",
                species_options,
                default=[],
                key="cons_species_na",
            )

        with st.sidebar.expander("Tissue expression", expanded=True):
            st.sidebar.markdown(
                f"<div style='margin-top:-2px; margin-bottom:6px;'>{doc_jump_link('doc_adv_tissue', 'Docs')}</div>",
                unsafe_allow_html=True
            )

            st.markdown("<div class='sidebar-section-title'>Show extra columns</div>", unsafe_allow_html=True)

            # ✅ CHANGED: user selects individual tissues (grouped by system), not full systems
            with st.expander("Show tissue columns (select tissues by system):", expanded=False):
                tissues_to_show_set = set()

                for system_name, sys_tissues in SYSTEM_TISSUES.items():
                    available = [t for t in sys_tissues if t in tissue_sidebar_names]
                    if not available:
                        continue

                    icon = SYSTEM_ICONS.get(system_name)
                    col_icon, col_exp = st.columns([1.6, 10], gap="small")

                    with col_icon:
                        if icon is not None:
                            st.markdown("<div class='sidebar-icon'>", unsafe_allow_html=True)
                            st.image(icon, width=110)
                            st.markdown("</div>", unsafe_allow_html=True)

                    with col_exp:
                        display_system = system_display_name(system_name)
                        with st.expander(display_system, expanded=False):
                            picked_show = st.multiselect(
                                "Select tissues",
                                available,
                                default=[],
                                key=showcols_key(system_name),
                            )
                            tissues_to_show_set.update(picked_show)

                tissues_to_show = sorted(tissues_to_show_set)

            st.markdown("<hr class='subtle-hr'>", unsafe_allow_html=True)
            st.markdown("<div class='sidebar-section-title'>Filter extra columns</div>", unsafe_allow_html=True)

            with st.expander("Expressed in (select tissues by system):", expanded=False):
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
                            st.image(icon, width=110)
                            st.markdown("</div>", unsafe_allow_html=True)

                    with col_exp:
                        display_system = system_display_name(system_name)
                        with st.expander(display_system, expanded=False):
                            picked = st.multiselect(
                                "Select tissues",
                                available,
                                key=f"tree_pos_{system_name}",
                            )
                            tissues_filter_set.update(picked)

                tissues_filter = sorted(tissues_filter_set)

            with st.expander("Not expressed in (select tissues by system):", expanded=False):
                tissues_not_filter_set = set()

                for system_name, sys_tissues in SYSTEM_TISSUES.items():
                    available = [t for t in sys_tissues if t in tissue_sidebar_names]
                    if not available:
                        continue

                    icon = SYSTEM_ICONS.get(system_name)
                    col_icon, col_exp = st.columns([1.6, 10], gap="small")

                    with col_icon:
                        if icon is not None:
                            st.markdown("<div class='sidebar-icon'>", unsafe_allow_html=True)
                            st.image(icon, width=110)
                            st.markdown("</div>", unsafe_allow_html=True)

                    with col_exp:
                        display_system = system_display_name(system_name)
                        with st.expander(display_system, expanded=False):
                            picked = st.multiselect(
                                "Select tissues",
                                available,
                                key=f"tree_neg_{system_name}",
                            )
                            tissues_not_filter_set.update(picked)

                tissues_not_filter = sorted(tissues_not_filter_set)

        with st.sidebar.expander("Database / Class", expanded=True):
            st.sidebar.markdown(
                f"<div style='margin-top:-2px; margin-bottom:6px;'>{doc_jump_link('doc_adv_db_class', 'Docs')}</div>",
                unsafe_allow_html=True
            )

            st.markdown("<div class='sidebar-section-title'>Show extra columns</div>", unsafe_allow_html=True)

            show_class_cols = st.checkbox(
                "Show Class columns",
                value=False,
                key="show_class_cols",
            )

            st.markdown("<hr class='subtle-hr'>", unsafe_allow_html=True)
            st.markdown("<div class='sidebar-section-title'>Filter extra columns</div>", unsafe_allow_html=True)

            mirgene_filter = st.selectbox(
                "Database:",
                ["Show all", "In both", "Only in miRBase"],
                key="db_filter",
            )

            classes = sorted(df["Class_miRBase"].dropna().unique()) if "Class_miRBase" in df.columns else []
            classes_selected = st.multiselect(
                "Class:",
                classes,
                default=[],
                key="class_filter",
            )

    def apply_preset(preset_name: str):
        for k in FILTER_KEYS:
            st.session_state.pop(k, None)

        st.session_state["show_adv"] = True
        st.session_state["sb_conservation"] = "Show all"
        st.session_state["sb_expression"] = "Show all"
        st.session_state["sb_structure"] = "Show all"
        st.session_state["sb_hsa"] = "Show all"
        st.session_state["show_repeat_plot"] = False

        st.session_state["search_any"] = ""
        st.session_state["ms_family"] = []
        st.session_state["ms_repeat"] = []
        st.session_state["db_filter"] = "Show all"
        st.session_state["class_filter"] = []
        st.session_state["show_class_cols"] = False

        # clear show-cols selections explicitly (optional but clearer)
        for sys_name in SYSTEM_TISSUES.keys():
            st.session_state[showcols_key(sys_name)] = []
            st.session_state[f"tree_pos_{sys_name}"] = []
            st.session_state[f"tree_neg_{sys_name}"] = []

        if preset_name == "cardio_mouse":
            st.session_state["cons_species_found"] = ["M. musculus"]
            st.session_state["cons_species_na"] = []
            st.session_state["cons_stability_choice"] = "Stable (R/D)"

            # ✅ Show only the tissues you want as columns (individual, not whole system)
            st.session_state[showcols_key("1. Cardiorespiratory system")] = [
                "heart", "lung",
            ]

            # Filter: expressed in the same tissues (as before)
            st.session_state["tree_pos_1. Cardiorespiratory system"] = [
                "heart", "ventricle", "artery", "vein",
                "blood", "plasma", "serum", "platelet",
                "lung", "bronchus", "pleurae", "larynx", "pharynx"
            ]
            st.session_state["tree_neg_1. Cardiorespiratory system"] = []

        elif preset_name == "brain_primates":
            st.session_state["cons_species_found"] = ["P. troglodytes", "P. paniscus"]
            st.session_state["cons_species_na"] = ["M. mulatta", "L. catta"]
            st.session_state["cons_stability_choice"] = "Stable (R/D)"

            # ✅ Show extra columns -> Show species columns:
            st.session_state["show_species_cols"] = [
                "P. troglodytes",
                "P. paniscus",
                "M. mulatta",
                "L. catta",
            ]

            # ✅ Show (columns) a reasonable neuro subset (edit as you like)
            st.session_state[showcols_key("3. Neuro-Endocrine system")] = [
                "brain", "cerebellum",
            ]

        st.session_state["page"] = 1  # MCGPT: reset pagination when applying presets
        st.rerun()

    with st.sidebar.expander("Example use cases", expanded=False):
        st.markdown(
            "<div style='font-size: 15px; line-height: 1.2; margin-top: 2px;'>"
            "Apply a preset configuration of filters."
            "</div>",
            unsafe_allow_html=True
        )

        # keep doc link (main section)
        st.sidebar.markdown(doc_jump_link("doc_use_cases", "Docs"), unsafe_allow_html=True)

        b1, b2 = st.columns(2)
        with b1:
            if st.button("Cardio + mouse", use_container_width=True):
                apply_preset("cardio_mouse")
        with b2:
            if st.button("Brain + great apes", use_container_width=True):
                apply_preset("brain_primates")

    st.sidebar.markdown("---")
    if any_filter_active():
        # (Reset is a main doc anchor; icon could be made inline too, but left like this)
        st.sidebar.markdown(doc_jump_link("doc_filter_reset", "Docs (Reset)"), unsafe_allow_html=True)
        if st.sidebar.button("Reset all filters", use_container_width=True, key="reset_bottom"):
            for k in FILTER_KEYS:
                st.session_state.pop(k, None)
            st.session_state["show_adv"] = False
            st.session_state["page"] = 1  # MCGPT: reset pagination
            st.rerun()

    # -----------------------------------------------------------
    # APPLY FILTERS
    # -----------------------------------------------------------
    filtered = df.copy()

    def apply_pass_choice(data: pd.DataFrame, choice: str, helper_col: str) -> pd.DataFrame:
        if not choice or choice == "Show all":
            return data
        if choice == "PASSED":
            return data[data[helper_col] == "TRUE"]
        if choice == "NOT PASSED":
            return data[data[helper_col] == "FALSE"]
        return data

    filtered = apply_pass_choice(filtered, conservation_choice, "_Conservation_tf")
    filtered = apply_pass_choice(filtered, expression_choice, "_Expression_tf")
    filtered = apply_pass_choice(filtered, structure_choice, "_Structure_tf")

    if hsa_choice != "Show all":
        hsa_flag = filtered["hsa-specificity"].astype(str).str.strip().str.upper()
        if hsa_choice == "Only hsa-specific":
            filtered = filtered[hsa_flag == "YES"]
        elif hsa_choice == "Not hsa-specific":
            filtered = filtered[hsa_flag == "NO"]

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

        if "no family – miRBase" in family_selected:
            fam_mask |= (mirbase_flag == "NO")
        if "miRNAs in family – miRBase" in family_selected:
            fam_mask |= (mirbase_flag == "YES")

        if "no family – MirGeneDB" in family_selected:
            fam_mask |= (mirgenedb_flag == "NO")
        if "miRNAs in family – MirGeneDB" in family_selected:
            fam_mask |= (mirgenedb_flag == "YES")

        filtered = filtered[fam_mask]

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

        if stability_choice and stability_choice != "All":
            allowed_val = True if stability_choice.startswith("Stable") else False
            filtered = filtered[tmp_found.isin([allowed_val]).all(axis=1)]

    if tissues_filter:
        tissue_num = filtered[tissues_filter].apply(pd.to_numeric, errors="coerce")
        expressed_mask = (tissue_num >= 1.5).all(axis=1)
        filtered = filtered[expressed_mask]

    if tissues_not_filter:
        tissue_num_not = filtered[tissues_not_filter].apply(pd.to_numeric, errors="coerce")
        not_expressed_mask = (tissue_num_not < 1.5).all(axis=1)
        filtered = filtered[not_expressed_mask]

    if search_term:
        mask = filtered.astype(str).apply(lambda col: col.str.contains(search_term, case=False, na=False)).any(axis=1)
        filtered = filtered[mask]

    # -----------------------------------------------------------
    # ✅ NEW: compute tissues_to_show from per-system show-cols keys
    # (works even if Advanced is closed, because session_state persists)
    # -----------------------------------------------------------
    tissues_to_show_set = set()
    for sys_name, sys_tissues in SYSTEM_TISSUES.items():
        picked = st.session_state.get(showcols_key(sys_name), []) or []
        for t in picked:
            if t in tissue_sidebar_names:
                tissues_to_show_set.add(t)
    tissues_to_show = sorted(tissues_to_show_set)

    # -----------------------------------------------------------
    # MCGPT: Stable order + manual pagination (50 rows/page)
    # - avoids huge internal table scroll
    # - keeps page deterministic when filters change
    # -----------------------------------------------------------
    ROWS_PER_PAGE = 50  # MCGPT: change to 100 etc. if needed

    # Reset pagination whenever filter state changes (robust, even with list-valued widgets)
    _filter_sig = tuple((k, repr(st.session_state.get(k, None))) for k in FILTER_KEYS)
    if st.session_state.get("_filter_sig") != _filter_sig:
        st.session_state["page"] = 1
        st.session_state["_filter_sig"] = _filter_sig

    if "page" not in st.session_state:
        st.session_state["page"] = 1

    # Stable ordering (use padj if present; otherwise miRNA name)
    _sort_cols = []
    if "padj" in filtered.columns:
        _sort_cols.append("padj")
    if "miRNA" in filtered.columns:
        _sort_cols.append("miRNA")
    if _sort_cols:
        filtered_sorted = filtered.sort_values(_sort_cols, ascending=[True]*len(_sort_cols)).reset_index(drop=True)
    else:
        filtered_sorted = filtered.reset_index(drop=True)

    total_rows = len(filtered_sorted)
    total_pages = max(1, (total_rows - 1) // ROWS_PER_PAGE + 1)

    # Clamp page in range
    st.session_state["page"] = max(1, min(st.session_state["page"], total_pages))

    # Prev / Next controls (compact)
    nav_c1, nav_c2, nav_c3 = st.columns([1, 2, 1])
    with nav_c1:
        if st.button("← Prev", disabled=st.session_state["page"] == 1, use_container_width=True):
            st.session_state["page"] -= 1
            st.rerun()
    with nav_c3:
        if st.button("Next →", disabled=st.session_state["page"] == total_pages, use_container_width=True):
            st.session_state["page"] += 1
            st.rerun()
    with nav_c2:
        st.markdown(
            f"""
            <div style="display:flex; justify-content:center; align-items:center; height:100%;">
              <div style="font-weight:800;">Page {st.session_state['page']} / {total_pages}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    start = (st.session_state["page"] - 1) * ROWS_PER_PAGE
    end = start + ROWS_PER_PAGE
    page_filtered = filtered_sorted.iloc[start:end].copy()

    st.caption(f"Showing rows {start+1}–{min(end, total_rows)} of {total_rows}")

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
    # MCGPT: display only current page (downloads still use full filtered set)
    df_display = page_filtered.copy()

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
        "miRNA", "Conservation", "Expression", "Structure",
        "MirGeneDB family", "miRBase family", "hsa-specificity", "Repeat Class",
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
        + ["MirGeneDB family", "miRBase family", "hsa-specificity", "Repeat Class"]
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
        "_Expression_tf", "_Structure_tf",
        "_miRBase_family_flag", "_MirGeneDB_family_flag",
    ]
    helper_cols_present = [c for c in helper_cols if c in df_display.columns]
    df_display = df_display[visible_cols + helper_cols_present]

    # -----------------------------------------------------------
    # PREP TABLE EXPORT (TSV CLEAN)
    # -----------------------------------------------------------
    def prepare_tsv_export(df_disp, helper_cols_present_local):
        export_df = df_disp.copy()
        export_df = export_df.drop(columns=helper_cols_present_local, errors="ignore")
        export_df.columns = export_df.columns.str.replace(r"<.*?>", "", regex=True)
        return export_df

    # ✅ FIX 2: prepare TSV export from FULL filtered set (not just the current page)
    df_export_full = filtered_sorted.copy()

    df_export_full["Conservation"] = df_export_full["Conservation_display"]
    df_export_full["Expression"] = df_export_full["Expression_display"]
    df_export_full["Structure"] = df_export_full["Structure_display"]

    df_export_full["miRBase family"] = df_export_full["miRBase_family_display"]
    df_export_full["MirGeneDB family"] = df_export_full["MirGeneDB_family_display"]

    df_export_full = df_export_full.rename(columns=animal_display_names)

    if "sequence" in df_export_full.columns:
        df_export_full = df_export_full.drop(columns=["sequence"])

    df_export_full = df_export_full.rename(columns={
        "Repeat_Class": "Repeat Class",
        "Class_miRBase": "Class miRBase",
        "Class_MirGeneDB": "Class MirGeneDB",
    })

    helper_cols_present_full = [c for c in helper_cols if c in df_export_full.columns]
    df_export_full = df_export_full[visible_cols + helper_cols_present_full]
    tsv_export_df = prepare_tsv_export(df_export_full, helper_cols_present_full)

    # -----------------------------------------------------------
    # TABLE STYLING (UNCHANGED)
    # -----------------------------------------------------------
    NA_SPECIES_COLOR = "#D9D9D9"
    TRUE_COLOR = "#009E73"
    FALSE_COLOR = "#D55E00"
    FAM_YES_COLOR = "#f4a582"
    FAM_NO_COLOR = "#92c5de"

    REPEAT_NOREPEAT_COLOR = "#c7e9c0"
    REPEAT_OTHER_COLOR = "#e6c28a"

    TISSUE_HIGH_BG = "#BDE131"
    TISSUE_LOW_BG = "#FEE08B"

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
            .applymap(
                lambda _v: "color: transparent !important; text-shadow: 0 0 0 transparent !important;",
                subset=["hsa-specificity"],
            )
        )

    if "Repeat Class" in df_display.columns:
        styled_df = styled_df.applymap(bg_repeat, subset=["Repeat Class"])

    if visible_tissue_cols:
        styled_df = styled_df.format({c: fmt_2dec for c in visible_tissue_cols}, na_rep="")
        styled_df = styled_df.applymap(tissue_bg, subset=visible_tissue_cols)

    if visible_class_cols:
        styled_df = styled_df.applymap(class_bg, subset=visible_class_cols)

    def style_row(row):
        styles = ["font-weight: 700; font-size: 10px;"] * len(row)
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
    # CSS — TABLE + LEGEND (RESPONSIVE)  (-2px everywhere)
    # -----------------------------------------------------------
    custom_css = r"""
    <style>

    /* ✅ IMPORTANT: assicurati che nessun parent tagli l’overflow orizzontale
       (così lo scroll orizzontale lo fa SOLO il browser) */
    div[data-testid="stAppViewContainer"],
    div[data-testid="stMain"],
    section.main,
    div.block-container{
      overflow: visible !important;
    }

    /* =======================================================
       TABLE WRAPPER: NO INTERNAL SCROLL — browser scroll only
       + bordo che si adatta alla larghezza reale della tabella
    ======================================================= */
    .table-container{
      max-height: none;
      overflow: visible !important;          /* ✅ niente scroll interno */
      border: 2px solid var(--table-border);
      margin-bottom: 14px;

      display: inline-block !important;      /* ✅ shrink-to-fit */
      width: max-content !important;         /* ✅ segue la tabella */
      max-width: none !important;            /* ✅ non forzare 100% */
      -webkit-overflow-scrolling: touch;
    }

    .table-inner{
      display: inline-block !important;
      width: max-content !important;
    }

    /* la tabella: larga quanto serve, ma almeno quanto la pagina */
    .table-inner table{
      border-collapse: separate !important;
      border-spacing: 0 !important;

      table-layout: fixed !important;
      width: max-content !important;         /* ✅ cresce con le colonne */
      min-width: 100% !important;            /* ✅ almeno piena pagina */
    }

    /* celle */
    .table-inner th,
    .table-inner td{
      border: 1px solid var(--table-border) !important;
      border-radius: 7px !important;

      line-height: 1 !important;
      min-height: 36px !important;
      padding: 7px 7px !important;

      font-size: clamp(10px, 0.9vw + 5px, 16px) !important;

      width: clamp(110px, 8vw, 150px) !important;
      min-width: clamp(110px, 8vw, 150px) !important;
      max-width: clamp(150px, 10vw, 180px) !important;

      white-space: nowrap !important;
      overflow: hidden !important;

      text-align: center !important;
      font-weight: 700 !important;
      color: black !important;
      vertical-align: middle !important;
    }

    /* header sticky */
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

    /* prima colonna sticky */
    .table-inner th:first-child{
      position: sticky !important;
      left: 0;
      z-index: 30 !important;

      width: clamp(160px, 12vw, 210px) !important;
      min-width: clamp(160px, 12vw, 210px) !important;
      max-width: clamp(210px, 16vw, 260px) !important;

      background-color: var(--table-first-th-bg) !important;
      color: color-mix(in srgb, var(--text) 95%, transparent) !important;
      background-clip: padding-box;
    }

    .table-inner td:first-child{
      position: sticky !important;
      left: 0;
      z-index: 25 !important;

      width: clamp(160px, 12vw, 210px) !important;
      min-width: clamp(160px, 12vw, 210px) !important;
      max-width: clamp(210px, 16vw, 260px) !important;

      background-color: var(--table-first-td-bg) !important;
      color: color-mix(in srgb, var(--text) 95%, transparent) !important;
      font-weight: 800 !important;
      background-clip: padding-box;
    }

    /* =======================================================
       LEGEND
    ======================================================= */
    .legend-wrap{
      display: flex;
      flex-wrap: wrap;
      gap: 12px 18px;
      align-items: flex-start;
      margin-top: 8px;
      margin-bottom: 10px;
    }

    .legend-card{
      flex: 1 1 240px;
      min-width: 240px;
      font-size: 14px;
      font-weight: 400;
      line-height: 1.35;
    }

    .legend-title{
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 6px;
    }

    .legend-row{
      display: flex;
      flex-wrap: wrap;
      gap: 8px 12px;
      align-items: center;
    }

    .legend-item{
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }

    .swatch{
      width: 16px;
      height: 16px;
      border-radius: 999px;
      display: inline-block;
      vertical-align: middle;
      border: 1px solid color-mix(in srgb, var(--text) 35%, transparent);
      box-sizing: border-box;
    }

    @media (max-width: 900px){
      .table-inner table{
        table-layout: auto !important;
      }

      .table-inner th,
      .table-inner td{
        padding: 6px 6px !important;
        border-radius: 6px !important;

        white-space: normal !important;
        word-break: break-word !important;
      }

      .legend-card{
        min-width: 210px;
        font-size: 12px;
      }
      .legend-title{
        font-size: 14px;
      }
    }

    </style>
    """

    # -----------------------------------------------------------
    # ROW COUNT
    # -----------------------------------------------------------
    # MCGPT: show total filtered rows (not just page size)
    st.write(f"Rows shown (filtered total): **{len(filtered_sorted)}**")

    # -----------------------------------------------------------
    # LEGEND (ABOVE TABLE)
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

    species_filter_active = bool(species_found_cols or species_na_sidebar)
    if visible_species_cols or species_filter_active:
        legend_cards.append(f"""
<div class="legend-card">
  <div class="legend-title">Species conservation</div>
  <div class="legend-row">
    <span class="legend-item"><span class="swatch" style="background:#fdb863;"></span>Stable structure</span>
    <span class="legend-item"><span class="swatch" style="background:#b2abd2;"></span>Unstable structure</span>
    <span class="legend-item"><span class="swatch" style="background:{NA_SPECIES_COLOR};"></span>Not found</span>
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

    legend_html = f"<div class='legend-wrap'>{''.join(legend_cards)}</div><div style='height:6px'></div>"

    # -----------------------------------------------------------
    # ✅ FIX (warning): remove Styler <style> from HTML and inject separately
    # -----------------------------------------------------------
    m = re.search(r"(<style.*?</style>)", html_table, flags=re.S)
    styler_css = m.group(1) if m else ""
    html_table_only = html_table.replace(styler_css, "")

    # 1) CSS custom (your table + legend)
    st.markdown(custom_css, unsafe_allow_html=True)

    # 2) CSS generated by pandas Styler (colors etc.)
    if styler_css:
        st.markdown(styler_css, unsafe_allow_html=True)

    # 3) HTML legend + table (NO <style> inside)
    st.markdown(
        legend_html
        + "<div class='table-container'><div class='table-inner'>"
        + html_table_only
        + "</div></div>",
        unsafe_allow_html=True
    )

    # -----------------------------------------------------------
    # DOWNLOAD BUTTONS (TSV + FASTA)
    # -----------------------------------------------------------
    tsv_bytes = tsv_export_df.to_csv(index=False, sep="\t").encode("utf-8")

    dl_col, _ = st.columns([2, 10])
    with dl_col:
        st.download_button(
            "Download table (TSV)",
            data=tsv_bytes,
            file_name="mirna_filtered_table.tsv",
            mime="text/tab-separated-values",
            key="dl_tsv",
            use_container_width=False,
        )

        st.download_button(
            "Get FASTA",
            # MCGPT: export FASTA for full filtered set (not just current page)
            data=generate_fasta(filtered_sorted).encode("utf-8"),
            file_name="mirna_selected.fasta",
            mime="text/plain",
            key="dl_fasta",
            use_container_width=False,
        )

    # -----------------------------------------------------------
    # MCGPT: scale chart sizes according to UI_SCALE
    # -----------------------------------------------------------
    def _s(px: float) -> float:
        return float(px) * UI_SCALE

    # -----------------------------------------------------------
    # BARPLOT (Repeat distribution) — THEME-AWARE + shown on demand
    # -----------------------------------------------------------
    ucscgb_palette = ["#009ADE", "#7CC242", "#F98B2A", "#E4002B", "#B7312C", "#E78AC3", "#00A4A6", "#00458A"]

    # ✅ FIX: updated labels in order list
    repeat_order = [
        "LINE", "SINE", "LTR",
        "DNA repeats",
        "Satellite repeats", "Simple repeats",
        "Low complexity repeats",
        "No repeat", "tRNA", "RC"
    ]

    show_repeat_plot = st.session_state.get("show_repeat_plot", False)

    if show_repeat_plot:
        st.subheader("Repeat class distribution")
        st.markdown("<div class='plot-card'>", unsafe_allow_html=True)

        # MCGPT: compute distribution on full filtered set (not just current page)
        if "Repeat_Class" in filtered_sorted.columns and filtered_sorted["Repeat_Class"].notna().any():
            repeat_counts = filtered_sorted.groupby("Repeat_Class").size().reset_index(name="Count")
            repeat_counts["Percent"] = (repeat_counts["Count"] / repeat_counts["Count"].sum() * 100).round(2)

            barplot = (
                alt.Chart(repeat_counts)
                .mark_bar(
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
                            labelAngle=0,
                            labelFontSize=_s(10.5),
                            titleFontSize=_s(14),
                            titlePadding=_s(34),
                        )
                    ),
                    y=alt.Y(
                        "Count:Q",
                        title="Count",
                        axis=alt.Axis(
                            labelFontSize=_s(12),
                            titleFontSize=_s(14)
                        )
                    ),
                    color=alt.Color(
                        "Repeat_Class:N",
                        scale=alt.Scale(domain=repeat_order, range=ucscgb_palette),
                        legend=None
                    ),
                    tooltip=["Repeat_Class", "Count", "Percent"]
                )
                .properties(height=_s(560))
                .configure(background="transparent")
                .configure_view(fill="transparent", strokeOpacity=0)
                .configure_axis(
                    labelColor="currentColor",
                    titleColor="currentColor",
                    labelFontSize=_s(12),
                    titleFontSize=_s(14),
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

    st.markdown("---")
    st.caption("pre-miRNA Annotation Browser — Streamlit App")


# ===========================================================
# TAB 2 — DOCUMENTATION (split into sections + granular anchors)
# ✅ CHANGED: updated tissue “Show columns” description (individual tissues)
# ===========================================================
with tab_docs:

    # -----------------------------
    # TOP / Overview
    # -----------------------------
    st.markdown('<div id="doc_overview" class="doc-anchor"></div>', unsafe_allow_html=True)
    st.markdown(
        r"""
# miR-RF human pre-miRNA Explorer

An interactive **Streamlit** web application for exploring, filtering, and exporting human pre-miRNA annotations generated by the **miR-RF** workflow, as described in:

> *"An operational workflow for the systematic annotation of human miRNAs"*

This application enables dynamic interrogation and subsetting of human pre-miRNAs based on:

- **Predicted structural stability**
- **Evolutionary conservation**
- **Tissue expression patterns**

Users can define flexible, multi-parameter filtering strategies tailored to specific biological questions, and export selected subsets for downstream analyses.
The app is designed to support both exploratory data analysis and hypothesis-driven investigation of human pre-miRNA candidates, along with their sequence.

---

### Overview

Human pre-miRNAs are displayed in an interactive table featuring:

- **Sticky header** and **sticky first column** for improved navigation
- **Color-coded cells** with an integrated legend indicating:
  - Pass/fail status for **structure**, **conservation**, and **expression**
  - **miRNA family membership**
  - **Human (hsa) specificity**
  - **Repeat element presence**
  - **Species-level structural stability** and “not found” status
  - **Tissue expression threshold** (RPMM ≥ 1.5 vs < 1.5)
  - **miRBase / MirGeneDB structural classes** (R/D/I/S), when enabled

---

### Integrated Annotation 

The browser combines annotations described in:

> *"An operational workflow for the systematic annotation of human miRNAs"*

- **miR-RF structural stability classes** (R/D/I/S)
- **Multi-species conservation profiles**, including human specificity
- **Tissue expression values** (RPMM)
- **miRNA family context** (miRBase / MirGeneDB)
- **Repeat annotation**

All displayed results correspond to the analyses reported in the accompanying manuscript and are provided as a reusable resource to support downstream computational and experimental studies.
"""
    )

    st.markdown("---")

    # -----------------------------
    # Key features
    # -----------------------------
    st.markdown('<div id="doc_key_features" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(2, "adv", "Key features")
    st.markdown(
        """
Filters can be combined freely: **any combination of filters can be applied simultaneously**.

All selected filters are combined using **logical AND**.  
This means that only pre-miRNAs satisfying *all* active criteria will be displayed in the table.

Results update automatically whenever filter settings are modified.
"""
    )

    st.markdown('<div id="doc_filter_search_any" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(3, "global", "Search by name")
    st.markdown(
        """
Search for one or more miRNAs across **all rows** of the table.

- Matching is **case-insensitive**.
- The search performs a **partial match**: rows are retained if any cell **contains** the input text.
- **Regular expressions (regex)** are supported for advanced queries (e.g. `^hsa-` to match entries starting with *hsa-let*).
"""
    )

    st.markdown('<div id="doc_filter_conservation_pf" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(3, "cons1", "Conservation")
    st.markdown(
        """
Keep or exclude human pre-miRNAs based on their **evolutionary conservation** across the selected species.

- **Show all** *(default)*: no filter applied.
- **PASSED**: evolutionarily conserved according to the criteria defined in the manuscript (detected in ≥ 3 species).
- **NOT PASSED**: not conserved under the specified criteria.
"""
    )

    st.markdown('<div id="doc_filter_expression_pf" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(3, "tissue1", "Expression")
    st.markdown(
        """
Keep or exclude human pre-miRNAs based on evidence of **expression**.

- **Show all** *(default)*: no filter applied.
- **PASSED**: expressed according to the criteria defined in the paper (RPMM ≥ in at least one tissue).
- **NOT PASSED**: not conserved under the specified criteria.
"""
    )

    st.markdown('<div id="doc_filter_structure_pf" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(3, "structure", "Structural Classification Filter (miRBase / MirGeneDB)")
    st.markdown(
        """
Keep or exclude human pre-miRNAs according to their **structural classification** in miRBase or MirGeneDB.

- **Show all** *(default)*: no filter applied.
- **PASSED**: pre-miRNA classified as **R** or **D** (structurally robust).
- **NOT PASSED**: pre-miRNA classified as **I** or **S** (structurally unstable or weakly supported).
"""
    )

    st.markdown('<div id="doc_filter_hsa" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(3, "hsa", "hsa specificity")
    st.markdown(
        """
Filter human-specific or non human-specific pre-miRNAs.

- **Show all**: no filter applied.
- **Only hsa-specific**: retain only pre-miRNAs annotated as human-specific.
- **Not hsa-specific**: exclude human-specific premiRNAs and retain all other entries.
"""
    )

    st.markdown('<div id="doc_filter_family" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(3, "fam", "miRNA Family Membership")
    st.markdown(
        """
Filter pre-miRNAs based on family annotations from **miRBase** and/or **MirGeneDB**.

- **no family**: pre-miRNAs not assigned to any family in the selected databases.
- **miRNAs in family**: pre-miRNAs annotated as belonging to a family (the family name is displayed when available).
"""
    )

    st.markdown('<div id="doc_filter_repeat" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(3, "rep", "Repeat class")
    st.markdown(
        """
Filter miRNAs based on the presence and type of **overlapping repeat elements**.

- Select one or more repeat classes (e.g. **LINE**, **SINE**, **LTR**, **DNA repeats**, **Low complexity repeats**).
- If multiple classes are selected, miRNAs overlapping **any** of the chosen categories are retained (logical OR).
"""
    )

    st.markdown('<div id="doc_filter_plot_repeat" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(3, "barplot", "Show repeat class distribution")
    st.markdown(
        """
Enable **“Show repeat class distribution”** to visualize the repeat composition of the **current filtered subset**.

- The bar plot reports **counts** and **percentages** per each repeat class.
- This visualization helps assess whether applied filters enrich for specific repeat categories.
"""
    )

    st.markdown('<div id="doc_filter_reset" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(3, "reset", "Reset all filters")
    st.markdown(
        """
Use **Reset all filters** to clear selections and restore default settings.

- The button is shown only when at least one filter is active.
- It also resets navigation-dependent state (e.g. pagination).
"""
    )

    st.markdown("---")

    # -----------------------------
    # Advanced options
    # -----------------------------
    st.markdown('<div id="doc_advanced" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(2, "adv2", "Advanced options")

    st.markdown('<div id="doc_advanced_options" class="doc-anchor"></div>', unsafe_allow_html=True)
    st.markdown(
        f"{doc_icon_html('adv2')}Enable **Advanced options** in the sidebar to unlock additional controls and column display options.",
        unsafe_allow_html=True
    )

    st.markdown('<div id="doc_adv_conservation" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(3, "cons2", "Evolutionary conservation (advanced)")
    st.markdown("""
- **Show species columns**: display per-species conservation.  
- **Filter by**: 
    - **Found in** selected species 
    - **Not found in** selected species.  
- Optional: stratify by structural stability when **Found in** is active: **Stable (R/D)** vs **Unstable (S/I)**.  
""")

    st.markdown('<div id="doc_adv_tissue" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(3, "tissue2", "Tissue expression (advanced)")
    st.markdown("""
- **Show tissue columns** by selecting **individual tissues** (grouped by anatomical system, with icons).  
- **Filter by**:  
  - **Expressed in**: selected tissues with **RPMM ≥ 1.5** (all selected must pass)  
  - **Not expressed in**: selected tissues with **RPMM < 1.5** (all selected must pass)  
""")

    st.markdown('<div id="doc_adv_db_class" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(3, "database", "Database / class (advanced)")
    st.markdown("""
- **Show Class columns** (miRBase / MirGeneDB).  
- **Database filter**: 
    - entries present in both databases 
    - entries present in miRBase.  
- **Class filter**: filter by structural class (R, D, I, S).  
""")

    st.markdown("---")

    # -----------------------------
    # Data export
    # -----------------------------
    st.markdown('<div id="doc_export" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(2, "export", "Data export")
    st.markdown(
        """
The currently filtered dataset can be exported as:

- **TSV table** (only visible columns; clean formatting)  
- **FASTA file** for the filtered subset (from the `sequence` column)

These exports are intended to support downstream analyses and custom pipelines.
"""
    )

    st.markdown("---")

    # -----------------------------
    # Example use cases
    # -----------------------------
    st.markdown('<div id="doc_use_cases" class="doc-anchor"></div>', unsafe_allow_html=True)
    st.markdown("## Example use cases")

    st.markdown(
        """
    **Using the pre-miRNA Annotation Browser as a support tool**, the application can be used to narrow the search space by combining a set of complementary filters.
    """,
        unsafe_allow_html=True
    )

    # ---- Use case 1 (TITLE WITH ICON) ----
    st.markdown(
        f"### {doc_icon_html('mouseCuore')}Use case 1 — Cardiovascular-associated miRNAs conserved in mouse",
        unsafe_allow_html=True
    )

    st.markdown(
        """
    This use case focuses on human pre-miRNAs conserved in *Mus musculus*, structurally robust, and expressed in cardiovascular-related tissues or fluids.

    **Conservation support**
    - In **Advanced options -> Evolutionary conservation**, select *M. musculus* under **Found in**.  
    - This restricts the table to pre-miRNAs with detectable conservation in mouse.
    - In **Advanced options -> Evolutionary conservation**, select **Stable (R/D)** under **Structure**.

    **Tissue expression context**
    - In **Advanced options -> Tissue expression**, select specific tissues under  
    - **Show tissue columns (select tissues by system)** (e.g. heart, artery, blood...) to display their columns.
    - In **Advanced options -> Tissue expression**, select tissues under **Expressed in (select tissues by system)** to filter by RPMM≥1.5.

    ---
    """,
        unsafe_allow_html=True
    )

    # ---- Use case 2 (TITLE WITH ICON) ----
    st.markdown(
        f"### {doc_icon_html('scimmiaBrain')}Use case 2 — Brain-associated miRNAs conserved in primates",
        unsafe_allow_html=True
    )

    st.markdown(
        """
    This use case focuses on human pre-miRNAs conserved in *Pan troglodytes* and *Pan paniscus* and showing evidence of expression in neural tissues.

    **Conservation support**
    - In **Advanced options -> Evolutionary conservation**, select *P. troglodytes* and *P. paniscus* under **Found in**.
    - In **Advanced options -> Evolutionary conservation**, select **Stable (R/D)** under **Structure**.
    - In **Advanced options -> Evolutionary conservation**, select *M. mulatta* and *L. catta* under **Not found in**.

    **Tissue expression context**
    - In **Advanced options -> Tissue expression**, select individual tissues under  
      **Show tissue columns (select tissues by system)** (e.g. brain, cortex, cerebellum, hippocampus, neuron...).  
      This option displays the corresponding tissue expression columns but does not filter the results.
    """,
        unsafe_allow_html=True
    )

    st.markdown("---")
    st.markdown("License: CC BY 4.0")

