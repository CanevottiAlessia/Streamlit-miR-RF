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

            const wanted = (tabText || '').toLowerCase();
            const target = Array.from(tabs).find(b => {
              const txt = (b.innerText || b.textContent || '').trim().toLowerCase();
              return txt === wanted || txt.includes(wanted);
            });

            if (target) { target.click(); return true; }
            return false;
          }

          function scrollToId(id) {
            const doc = window.parent.document;
            const el = doc.getElementById(id);
            if (el) {
              el.scrollIntoView({ behavior: "smooth", block: "start" });
              return true;
            }
            return false;
          }

          function waitAndScroll(sectionId) {
            let tries = 0;
            const t = setInterval(() => {
              tries++;
              const ok = scrollToId(sectionId);
              if (ok || tries >= 50) {
                clearInterval(t);
                try { window.parent.sessionStorage.removeItem("mirrf_pending_doc_id"); } catch(e) {}
              }
            }, 120);
          }

          // Global function called by our click handlers
          window.parent.mirrfNav = function(sectionId) {
            if (!sectionId) return false;
            try { window.parent.sessionStorage.setItem("mirrf_pending_doc_id", sectionId); } catch(e) {}
            clickTabByText("Documentation");
            waitAndScroll(sectionId);
            return false;
          };

          // Bind clicks to all <a data-doc-id="..."> links (Streamlit-safe)
          function bindDocLinks() {
            const root = window.parent.document;
            const links = root.querySelectorAll('a[data-doc-id]');

            links.forEach(a => {
              if (a.getAttribute("data-doc-bound") === "1") return;
              a.setAttribute("data-doc-bound", "1");
              a.style.cursor = "pointer";

              a.addEventListener("click", function(e){
                e.preventDefault();
                e.stopPropagation();
                const id = a.getAttribute("data-doc-id");
                if (id && window.parent.mirrfNav) window.parent.mirrfNav(id);
                return false;
              }, true);
            });
          }

          function consumePendingDocTarget() {
            try {
              const pending = window.parent.sessionStorage.getItem("mirrf_pending_doc_id");
              if (pending) waitAndScroll(pending);
            } catch(e) {}
          }

          // Streamlit re-renders often -> rebind periodically
          setInterval(bindDocLinks, 500);
          setInterval(consumePendingDocTarget, 500);
          setTimeout(bindDocLinks, 50);
          setTimeout(consumePendingDocTarget, 250);

        })();
        </script>
        """,
        height=0,
    )


def doc_jump_link(section_id: str, label: str = "Docs") -> str:
    return f"""
    <a href="#{section_id}" data-doc-id="{section_id}"
       onclick="if (window.parent && window.parent.mirrfNav) {{ window.parent.mirrfNav('{section_id}'); }} return false;"
       style="text-decoration:none; font-weight:700;">
       ℹ️ {label}
    </a>
    """


def doc_jump_icon(section_id: str, title: str = "Docs") -> str:
    return f"""
    <a href="#{section_id}" data-doc-id="{section_id}"
       onclick="if (window.parent && window.parent.mirrfNav) {{ window.parent.mirrfNav('{section_id}'); }} return false;"
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
    # Load the complete table.
    # The main App page will use only Default == yes rows,
    # while the Sensitivity analysis page can explore all candidate rows.
    return pd.read_csv("s8_new", sep="\t")


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
    "High confidence miRNA",
    "miRBase high confidence miRNA",
    "Experimental evidence",
    "Overlap",
    "Default",
]
for c in expected_cols:
    if c not in df.columns:
        df[c] = pd.NA

df["Class_MirGeneDB"] = df["Class_MirGeneDB"].fillna("—")
df["Class_MirGeneDB"] = df["Class_MirGeneDB"].replace(["nan", "NaN", "NA", None, pd.NA, ""], "—")

df["miRBase family"] = df["miRBase family"].fillna("NO")
df["MirGeneDB family"] = df["MirGeneDB family"].replace(["nan", "NaN", "", "<NA>"], pd.NA)


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
# NEW EVIDENCE / CONFIDENCE HELPERS
# -----------------------------------------------------------
def normalize_bool_like(x):
    if pd.isna(x):
        return pd.NA

    s = str(x).strip().lower()

    if s in ["true", "t", "yes", "y", "si", "sì", "1"]:
        return "TRUE"

    if s in ["false", "f", "no", "n", "0"]:
        return "FALSE"

    return pd.NA


# Prefer the current column name, but keep compatibility with older files.
_high_conf_source_col = None
for _candidate_col in ["High confidence miRNA", "miRBase high confidence miRNA"]:
    if _candidate_col in df.columns and df[_candidate_col].notna().any():
        _high_conf_source_col = _candidate_col
        break

if _high_conf_source_col is not None:
    df["_High_confidence_tf"] = df[_high_conf_source_col].apply(normalize_bool_like)
else:
    df["_High_confidence_tf"] = pd.NA

# Standardize the visible/helper columns used by the rest of the app.
df["High confidence miRNA"] = df["_High_confidence_tf"].map({
    "TRUE": "TRUE",
    "FALSE": "FALSE",
}).fillna("NA")
df["miRBase high confidence miRNA"] = df["High confidence miRNA"]

def normalize_experimental_level(x):
    """
    Experimental evidence is encoded as a numeric validation level:
    2 = Stringent filter
    1 = Lenient filter
    0 = No pass
    """
    if pd.isna(x):
        return pd.NA

    s = str(x).strip()

    try:
        val = int(float(s))
        if val in [0, 1, 2]:
            return val
    except Exception:
        pass

    low = s.lower()
    if low in ["stringent", "stringent filter", "2"]:
        return 2
    if low in ["lenient", "lenient filter", "1"]:
        return 1
    if low in ["no pass", "not passed", "not pass", "false", "0"]:
        return 0

    return pd.NA


if "Experimental evidence" in df.columns:
    df["_Experimental_evidence_level"] = df["Experimental evidence"].map(normalize_experimental_level)
    # Keep colored evidence cells visually empty, but show NA when the value is missing.
    df["Experimental evidence"] = df["_Experimental_evidence_level"].map({
        2: "",
        1: "",
        0: "",
    }).fillna("NA")
else:
    df["_Experimental_evidence_level"] = pd.NA
    df["Experimental evidence"] = "NA"

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
    "sb_hsa",
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
    "db_mirbase_full",
    "db_mirbase_hc",
    "db_mirgendb",
    "filtering_preset_db_sources",
    "class_filter",
    "show_high_conf_col",
    "show_exp_evidence_col",
    "show_overlap_col",
    "high_conf_filter",
    "experimental_evidence_filter",
    "apply_ablation_to_main",
    "sens_expression_cutoff",
    "sens_min_tissues",
    "sens_min_species",
    "sens_conservation_mode",
    "sens_stable_classes",
    "sens_high_conf_filter",
    "show_two_criteria_summary",
    "show_three_criteria_summary",
    "show_stable_plus_one_summary",
    "filtering_rule",
    "filtering_mode",
    "custom_use_conservation",
    "custom_use_expression",
    "custom_use_structure",
    "custom_min_criteria",
    "_last_custom_selected_count",
    "_last_filtering_mode_rendered",
]
for sys_name in SYSTEM_TISSUES.keys():
    FILTER_KEYS.append(f"tree_pos_{sys_name}")
    FILTER_KEYS.append(f"tree_neg_{sys_name}")

# -----------------------------------------------------------
# ABLATION DEFAULT SESSION STATE
# -----------------------------------------------------------
# These keys are part of FILTER_KEYS, so they must exist before the App
# page computes the pagination/filter signature. Otherwise, clicking Next/Prev
# can look like a filter change and reset the table to page 1.
if st.session_state.get("_filtering_defaults_version") != "v42":
    st.session_state["sens_expression_cutoff"] = 1.5
    st.session_state["sens_min_tissues"] = 1
    st.session_state["sens_min_species"] = 3
    st.session_state["sens_conservation_mode"] = "Recovered orthologs (TRUE or FALSE)"
    st.session_state["sens_stable_classes"] = ["R", "D"]
    st.session_state["sens_high_conf_filter"] = "Show all"
    st.session_state["show_two_criteria_summary"] = True
    st.session_state["show_three_criteria_summary"] = True
    st.session_state["show_stable_plus_one_summary"] = True
    st.session_state["filtering_rule"] = "At least 2 of 3 criteria"
    st.session_state["filtering_mode"] = "Default"
    st.session_state["filtering_preset_db_sources"] = ["miRBase-full", "miRBase-HC", "MirGeneDB"]
    st.session_state["custom_use_conservation"] = True
    st.session_state["custom_use_expression"] = True
    st.session_state["custom_use_structure"] = True
    st.session_state["custom_min_criteria"] = 2
    st.session_state["_last_custom_selected_count"] = 3
    st.session_state["_filtering_defaults_version"] = "v42"
st.session_state.setdefault("apply_ablation_to_main", False)
st.session_state.setdefault("show_two_criteria_summary", True)
st.session_state.setdefault("show_three_criteria_summary", True)
st.session_state.setdefault("show_stable_plus_one_summary", True)
st.session_state.setdefault("filtering_rule", "At least 2 of 3 criteria")
st.session_state.setdefault("filtering_mode", "Default")
st.session_state.setdefault("custom_use_conservation", True)
st.session_state.setdefault("custom_use_expression", True)
st.session_state.setdefault("custom_use_structure", True)
st.session_state.setdefault("custom_min_criteria", 2)


def reset_all_filters():
    """
    Reset the app to the true initial state.

    This does not only pop keys: it also writes the expected default values back
    explicitly, so reset behaves the same whether the button is clicked from the
    top sidebar, bottom sidebar, or after widgets have already been rendered.
    """
    # Clear all known UI/filter keys.
    for k in FILTER_KEYS:
        st.session_state.pop(k, None)

    # Clear old/stale keys from previous app versions too.
    stale_keys = [
        "sb_conservation", "sb_expression", "sb_structure",
        "show_cleavage_cols",
        "main_prev_page", "main_next_page",
        "reset_top", "reset_bottom",
        "_filter_sig",
        "_switch_to_app_after_apply",
        "_filtering_defaults_version",
        "_db_defaults_version",
        "_pending_sidebar_db_sources",
        "apply_filtering_criteria_button",
        "reset_filtering_criteria_button",
    ]
    for k in stale_keys:
        st.session_state.pop(k, None)

    # Main sidebar defaults.
    st.session_state["search_any"] = ""
    st.session_state["sb_hsa"] = "Show all"
    st.session_state["ms_family"] = []
    st.session_state["ms_repeat"] = []
    st.session_state["show_repeat_plot"] = False
    st.session_state["show_adv"] = False
    st.session_state["db_filter"] = ["miRBase-full", "miRBase-HC", "MirGeneDB"]
    st.session_state["db_mirbase_full"] = True
    st.session_state["db_mirbase_hc"] = True
    st.session_state["db_mirgendb"] = True
    st.session_state["filtering_preset_db_sources"] = ["miRBase-full", "miRBase-HC", "MirGeneDB"]
    st.session_state["_db_defaults_version"] = "v19"

    # Removed/neutral legacy filters.
    st.session_state["sb_conservation"] = "Show all"
    st.session_state["sb_expression"] = "Show all"
    st.session_state["sb_structure"] = "Show all"

    # Advanced options defaults.
    st.session_state["show_species_cols"] = []
    st.session_state["cons_species_found"] = []
    st.session_state["cons_species_na"] = []
    st.session_state["cons_stability_choice"] = "All"

    st.session_state["show_class_cols"] = False
    st.session_state["class_filter"] = []

    st.session_state["show_high_conf_col"] = False
    st.session_state["show_exp_evidence_col"] = False
    st.session_state["show_overlap_col"] = False
    st.session_state["high_conf_filter"] = "Show all"
    st.session_state["experimental_evidence_filter"] = "Show all"

    # Per-system tissue show/filter controls.
    for sys_name in SYSTEM_TISSUES.keys():
        st.session_state[showcols_key(sys_name)] = []
        st.session_state[f"tree_pos_{sys_name}"] = []
        st.session_state[f"tree_neg_{sys_name}"] = []

    # Filtering criteria page defaults.
    st.session_state["apply_ablation_to_main"] = False
    st.session_state["sens_expression_cutoff"] = 1.5
    st.session_state["sens_min_tissues"] = 1
    st.session_state["sens_min_species"] = 3
    st.session_state["sens_conservation_mode"] = "Recovered orthologs (TRUE or FALSE)"
    st.session_state["sens_stable_classes"] = ["R", "D"]
    st.session_state["sens_high_conf_filter"] = "Show all"
    st.session_state["show_two_criteria_summary"] = True
    st.session_state["show_three_criteria_summary"] = True
    st.session_state["show_stable_plus_one_summary"] = True
    st.session_state["filtering_rule"] = "At least 2 of 3 criteria"
    st.session_state["filtering_mode"] = "Default"
    st.session_state["filtering_preset_db_sources"] = ["miRBase-full", "miRBase-HC", "MirGeneDB"]
    st.session_state["custom_use_conservation"] = True
    st.session_state["custom_use_expression"] = True
    st.session_state["custom_use_structure"] = True
    st.session_state["custom_min_criteria"] = 2

    # Pagination/default version.
    st.session_state["page"] = 1
    st.session_state["_filtering_defaults_version"] = "v42"





def any_filter_active() -> bool:
    if (st.session_state.get("search_any", "") or "").strip():
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
    current_db = set(st.session_state.get("db_filter", ["miRBase-full", "miRBase-HC", "MirGeneDB"]) or [])
    default_db = {"miRBase-full", "miRBase-HC", "MirGeneDB"}
    if current_db != default_db:
        return True
    if st.session_state.get("show_high_conf_col", False):
        return True
    if st.session_state.get("show_exp_evidence_col", False):
        return True
    if st.session_state.get("show_overlap_col", False):
        return True
    if st.session_state.get("high_conf_filter", "Show all") != "Show all":
        return True
    if st.session_state.get("experimental_evidence_filter", "Show all") != "Show all":
        return True

    if st.session_state.get("apply_ablation_to_main", False):
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
    df[animal_cols].apply(lambda r: r.isin([True]).sum(), axis=1) if animal_cols else pd.NA
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


def family_name_or_single(flag_val, name_val, empty_as=""):
    if pd.isna(flag_val):
        return "NA"

    flag = str(flag_val).strip().upper()

    if flag in ["", "NAN", "NA", "—", "<NA>"]:
        return "NA"

    if flag == "YES":
        if pd.isna(name_val) or str(name_val).strip() in ["", "nan", "NaN", "NA", "<NA>"]:
            return "NA"
        return str(name_val).strip()

    # NO means the annotation exists and the miRNA is single / not in family.
    # The cell stays blue via the helper flag, but the text is intentionally blank.
    if flag == "NO":
        return empty_as

    return "NA"


df["miRBase_family_display"] = df.apply(
    lambda r: family_name_or_single(
        r.get("miRBase family", "NO"),
        r.get("family_name_mirbase", pd.NA),
        empty_as=""
    ),
    axis=1
)

df["MirGeneDB_family_display"] = df.apply(
    lambda r: family_name_or_single(
        r.get("MirGeneDB family", "—"),
        r.get("family_name_mirgene", pd.NA),
        empty_as=""
    ),
    axis=1
)


# -----------------------------------------------------------
# Keep two dataset views:
# - df_all: complete candidate table, used by Sensitivity analysis
# - df: default manuscript catalog, used by the main App page
# -----------------------------------------------------------
df_all = df.copy()

# The visible default catalog is computed from the current default criteria
# after the filtering helper functions are defined.
df = df_all.copy()


# -----------------------------------------------------------
# ABLATION HELPERS
# -----------------------------------------------------------
def overlap_missing(data: pd.DataFrame) -> pd.Series:
    """
    Keep only rows where Overlap is missing / NA.
    Numeric 0 is NOT treated as missing here.
    """
    if "Overlap" not in data.columns:
        return pd.Series(True, index=data.index)

    overlap_raw = data["Overlap"]
    overlap_str = overlap_raw.astype("string").str.strip()

    return (
        overlap_raw.isna()
        | overlap_str.isna()
        | overlap_str.isin(["", "NA", "NaN", "nan", "NAN", "<NA>"])
    )


def filtering_uses_full_input() -> bool:
    """
    Database-specific Default presets are defined over the full input table.
    Other Filtering criteria setups keep the missing/NA Overlap candidate universe.
    Database-specific Default presets do not apply evidence criteria.
    """
    return st.session_state.get("filtering_mode", "Default") in [
        "miRBase-full",
        "miRBase-HC",
        "MirGeneDB",
    ]


def get_filtering_candidate_universe(data: pd.DataFrame) -> pd.DataFrame:
    """
    Candidate universe for Filtering criteria calculations.
    - miRBase-full / miRBase-HC / MirGeneDB: all input rows.
    - Other setups: rows with missing/NA Overlap.
    """
    if filtering_uses_full_input():
        return data.copy()
    return data[overlap_missing(data)].copy()


def ablation_settings_are_default() -> bool:
    """
    Return True when the ablation panel is set to the manuscript default criteria.
    In this case, the ablation catalog should match the Default == yes catalog.
    """
    cutoff = float(st.session_state.get("sens_expression_cutoff", 1.5))
    min_tissues = int(st.session_state.get("sens_min_tissues", 1))
    min_species = int(st.session_state.get("sens_min_species", 3))
    mode = st.session_state.get("sens_conservation_mode", "Recovered orthologs (TRUE or FALSE)")
    stable_classes = {
        str(x).strip().upper()
        for x in (st.session_state.get("sens_stable_classes", ["R", "D"]) or [])
    }
    high_conf = "Show all"
    filtering_rule = st.session_state.get("filtering_rule", "At least 2 of 3 criteria")
    filtering_mode = st.session_state.get("filtering_mode", "Default")

    return (
        filtering_mode in ["Default", "miRBase-full", "miRBase-HC", "MirGeneDB"]
        and abs(cutoff - 1.5) < 1e-9
        and min_tissues == 1
        and min_species == 3
        and str(mode).startswith("Recovered")
        and stable_classes == {"R", "D"}
        and high_conf == "Show all"
        and filtering_rule == "At least 2 of 3 criteria"
    )



def compute_ablation_catalog(data: pd.DataFrame) -> pd.DataFrame:
    """
    Compute the filtering-retained catalog from the complete candidate table.
    In ablation mode, miRNA/s are retained when they pass at least 2 of the 3
    selected evidence criteria: expression, conservation and structure.
    High-confidence status can be applied as an additional optional filter.
    """
    sens_base = get_filtering_candidate_universe(data)

    # Database-specific Default presets represent the source/catalog itself.
    # Therefore criteria are intentionally disabled for these presets:
    # - miRBase-full: full input universe, then miRBase-full source filter
    # - miRBase-HC: active candidate universe, then miRBase-HC source filter
    # - MirGeneDB: active candidate universe, then MirGeneDB source filter
    if st.session_state.get("filtering_mode", "Default") in [
        "miRBase-full",
        "miRBase-HC",
        "MirGeneDB",
    ]:
        return sens_base.copy()

    sens_expression_cutoff = float(st.session_state.get("sens_expression_cutoff", 1.5))
    sens_min_tissues = int(st.session_state.get("sens_min_tissues", 1))
    sens_min_species = int(st.session_state.get("sens_min_species", 3))
    sens_conservation_mode = "Recovered orthologs (TRUE or FALSE)"
    sens_stable_classes = st.session_state.get("sens_stable_classes", ["R", "D"]) or []
    sens_high_conf_filter = "Show all"

    # Dynamic expression criterion
    if tissue_cols:
        sens_tissue_num = sens_base[tissue_cols].apply(pd.to_numeric, errors="coerce")
        sens_base["Sensitivity expression count"] = (sens_tissue_num >= sens_expression_cutoff).sum(axis=1)
        sens_base["Sensitivity expression pass"] = sens_base["Sensitivity expression count"] >= sens_min_tissues
    else:
        sens_base["Sensitivity expression count"] = 0
        sens_base["Sensitivity expression pass"] = False

    # Dynamic conservation criterion
    # Count only TRUE values, i.e. species in which the ortholog is found
    # with stable structural support. FALSE values are not counted.
    if animal_cols:
        sens_base["Sensitivity conservation count"] = sens_base[animal_cols].apply(
            lambda r: r.isin([True]).sum(),
            axis=1,
        )
        sens_base["Sensitivity conservation pass"] = sens_base["Sensitivity conservation count"] >= sens_min_species
    else:
        sens_base["Sensitivity conservation count"] = 0
        sens_base["Sensitivity conservation pass"] = False

    # Dynamic structure criterion: pass if either database class is in the selected stable classes
    stable_set = {str(x).strip().upper() for x in sens_stable_classes}
    mirbase_class = sens_base["Class_miRBase"].astype(str).str.strip().str.upper()
    mirgenedb_class = sens_base["Class_MirGeneDB"].astype(str).str.strip().str.upper()
    sens_base["Sensitivity structure pass"] = mirbase_class.isin(stable_set) | mirgenedb_class.isin(stable_set)

    sens_base["Sensitivity evidence count"] = (
        sens_base["Sensitivity expression pass"].astype(int)
        + sens_base["Sensitivity conservation pass"].astype(int)
        + sens_base["Sensitivity structure pass"].astype(int)
    )

    filtering_rule = st.session_state.get("filtering_rule", "At least 2 of 3 criteria")
    filtering_mode = st.session_state.get("filtering_mode", "Default")

    if filtering_mode == "Custom":
        custom_cols = []
        if st.session_state.get("custom_use_conservation", True):
            custom_cols.append("Sensitivity conservation pass")
        if st.session_state.get("custom_use_expression", True):
            custom_cols.append("Sensitivity expression pass")
        if st.session_state.get("custom_use_structure", True):
            custom_cols.append("Sensitivity structure pass")

        selected_custom_count = len(custom_cols)
        custom_min = int(st.session_state.get("custom_min_criteria", min(2, selected_custom_count)))
        custom_min = max(0, min(custom_min, selected_custom_count))

        if selected_custom_count == 0:
            sens_base["Sensitivity retained"] = custom_min == 0
        else:
            sens_base["Sensitivity custom evidence count"] = sum(
                sens_base[c].astype(int) for c in custom_cols
            )
            sens_base["Sensitivity retained"] = sens_base["Sensitivity custom evidence count"] >= custom_min
    elif filtering_rule == "At least 2 of 3 criteria":
        sens_base["Sensitivity retained"] = sens_base["Sensitivity evidence count"] >= 2
    elif filtering_rule == "All 3 criteria":
        sens_base["Sensitivity retained"] = sens_base["Sensitivity evidence count"] == 3
    elif filtering_rule in [
        "Stable structural class + at least one other criterion",
        "Stable structural class + at least one other criterion",
    ]:
        sens_base["Sensitivity retained"] = (
            sens_base["Sensitivity structure pass"]
            & (
                sens_base["Sensitivity conservation pass"]
                | sens_base["Sensitivity expression pass"]
            )
        )
    else:
        sens_base["Sensitivity retained"] = sens_base["Sensitivity evidence count"] >= 2

    if sens_high_conf_filter in ["High confidence", "High confidence (TRUE)"]:
        sens_base = sens_base[sens_base["_High_confidence_tf"] == "TRUE"]
    elif sens_high_conf_filter in ["Low confidence", "Low confidence (FALSE)"]:
        sens_base = sens_base[sens_base["_High_confidence_tf"] == "FALSE"]

    return sens_base[sens_base["Sensitivity retained"]].copy()


def get_main_catalog() -> pd.DataFrame:
    """
    Main table source.
    Default: manuscript catalog (Default == yes).
    If enabled by the expert user: filtering-retained catalog, which can include non-default rows.
    """
    if st.session_state.get("apply_ablation_to_main", False):
        return compute_ablation_catalog(df_all)
    return df.copy()


def get_default_overlap_catalog() -> pd.DataFrame:
    """
    Current default catalog computed from the default criteria:
    conservation >= 3 TRUE species, expression RPMM >= 1.5 in at least 1 tissue,
    structural class R/D, and at least 2 of these 3 evidence criteria.
    Only rows with missing/NA Overlap are considered.
    """
    base = df_all[overlap_missing(df_all)].copy()

    if base.empty:
        return base

    if tissue_cols:
        tissue_num = base[tissue_cols].apply(pd.to_numeric, errors="coerce")
        expression_pass = (tissue_num >= 1.5).sum(axis=1) >= 1
    else:
        expression_pass = pd.Series(False, index=base.index)

    if animal_cols:
        conservation_pass = base[animal_cols].apply(lambda r: r.isin([True]).sum(), axis=1) >= 3
    else:
        conservation_pass = pd.Series(False, index=base.index)

    mirbase_class = base["Class_miRBase"].astype(str).str.strip().str.upper()
    mirgenedb_class = base["Class_MirGeneDB"].astype(str).str.strip().str.upper()
    structure_pass = mirbase_class.isin(["R", "D"]) | mirgenedb_class.isin(["R", "D"])

    evidence_count = (
        expression_pass.astype(int)
        + conservation_pass.astype(int)
        + structure_pass.astype(int)
    )

    return base[evidence_count >= 2].copy()


# Main App default catalog computed from the current default criteria.
df = get_default_overlap_catalog().copy()


def get_active_filtering_database_sources():
    """
    Database sources used by the Filtering criteria page.

    Preset setups are selected after sidebar widgets have already been
    instantiated, so they cannot safely modify sidebar checkbox widget keys.
    Instead, presets store an internal override used only for Filtering criteria
    calculations. Custom mode falls back to the sidebar database checkboxes.
    """
    preset_sources = st.session_state.get("filtering_preset_db_sources", None)
    if preset_sources is not None:
        return list(preset_sources or [])
    return list(st.session_state.get(
        "db_filter",
        ["miRBase-full", "miRBase-HC", "MirGeneDB"],
    ) or [])


def apply_database_source_filter(data: pd.DataFrame) -> pd.DataFrame:
    """
    Apply the active Filtering criteria database filter to any dataframe.

    All database sources are selected by default. If no database source is
    selected, this returns an empty dataframe.
    """
    selected = get_active_filtering_database_sources()

    if data is None or data.empty:
        return data.copy() if data is not None else pd.DataFrame()

    filtered = data.copy()
    db_mask = pd.Series(False, index=filtered.index)

    mirbase_class = filtered["Class_miRBase"].astype(str).str.strip().str.upper()
    mirgenedb_class = filtered["Class_MirGeneDB"].astype(str).str.strip().str.upper()

    mirbase_present = filtered["Class_miRBase"].notna() & ~mirbase_class.isin(["", "NA", "NAN", "—", "-", "<NA>"])
    mirgenedb_present = filtered["Class_MirGeneDB"].notna() & ~mirgenedb_class.isin(["", "NA", "NAN", "—", "-", "<NA>"])

    if "miRBase-full" in selected:
        # miRBase-full represents the full input source.
        db_mask |= pd.Series(True, index=filtered.index)
    if "miRBase-HC" in selected:
        db_mask |= filtered["_High_confidence_tf"] == "TRUE"
    if "MirGeneDB" in selected:
        db_mask |= mirgenedb_present

    return filtered[db_mask].copy()


def apply_filtering_page_sidebar_filters(data: pd.DataFrame) -> pd.DataFrame:
    """
    Apply the visible sidebar filters to a dataframe for the Filtering criteria page.

    This is used for applying visible sidebar filters to benchmark and retained counts.
    It intentionally mirrors the main visible filters:
    - Search by name / global search
    - Database
    - Filter Experimental evidence
    - hsa specificity
    - Repeat class

    The input should already be restricted to rows with missing/NA Overlap when
    the count is intended to stay inside the Filtering criteria candidate universe.
    """
    if data is None or data.empty:
        return data.copy() if data is not None else pd.DataFrame()

    filtered = data.copy()

    # Search box
    search_term = st.session_state.get("search_any", "")
    if search_term:
        filtered = filtered[
            filtered.astype(str)
            .apply(lambda col: col.str.contains(search_term, case=False, na=False))
            .any(axis=1)
        ]

    # Database checkboxes
    filtered = apply_database_source_filter(filtered)

    # Experimental evidence filter
    experimental_evidence_filter = st.session_state.get("experimental_evidence_filter", "Show all")
    if experimental_evidence_filter == "Pass stringent filter":
        filtered = filtered[filtered["_Experimental_evidence_level"] == 2]
    elif experimental_evidence_filter == "Pass lenient filter":
        filtered = filtered[filtered["_Experimental_evidence_level"] == 1]
    elif experimental_evidence_filter == "No pass":
        filtered = filtered[filtered["_Experimental_evidence_level"] == 0]

    # hsa-specificity
    hsa_choice = st.session_state.get("sb_hsa", "Show all")
    if hsa_choice != "Show all" and "hsa-specificity" in filtered.columns:
        hsa_flag = filtered["hsa-specificity"].astype(str).str.strip().str.upper()
        hsa_true = hsa_flag.isin(["YES", "TRUE", "1", "Y", "SI", "SÌ"])
        hsa_false = hsa_flag.isin(["NO", "FALSE", "0", "N"])
        if hsa_choice == "Only hsa-specific":
            filtered = filtered[hsa_true]
        elif hsa_choice == "Not hsa-specific":
            filtered = filtered[hsa_false]

    # Repeat class
    repeats_selected = st.session_state.get("ms_repeat", [])
    if repeats_selected and "Repeat_Class" in filtered.columns:
        filtered = filtered[filtered["Repeat_Class"].isin(repeats_selected)]

    return filtered.copy()


def current_conservation_count(data: pd.DataFrame) -> pd.Series:
    """
    Count conservation as the number of TRUE species.
    FALSE values are not counted.
    """
    if not animal_cols:
        return pd.Series(pd.NA, index=data.index)

    return data[animal_cols].apply(lambda r: r.isin([True]).sum(), axis=1)


def current_expression_count(data: pd.DataFrame) -> pd.Series:
    """
    Count expressed tissues according to the currently selected ablation RPMM cutoff.
    Default / non-ablation mode uses RPMM >= 1.5.
    """
    if not tissue_cols:
        return pd.Series(pd.NA, index=data.index)

    cutoff = 1.5
    if st.session_state.get("apply_ablation_to_main", False):
        cutoff = float(st.session_state.get("sens_expression_cutoff", 1.5))

    tissue_num = data[tissue_cols].apply(pd.to_numeric, errors="coerce")
    return (tissue_num >= cutoff).sum(axis=1)


def current_structure_pass(data: pd.DataFrame) -> pd.Series:
    """
    Evaluate structure pass/fail according to currently selected structural classes.
    Default / non-ablation mode uses the original Structure TRUE/FALSE flag.
    """
    if not st.session_state.get("apply_ablation_to_main", False):
        return data["_Structure_tf"].astype(str).str.upper().eq("TRUE")

    stable_classes = {
        str(x).strip().upper()
        for x in (st.session_state.get("sens_stable_classes", ["R", "D"]) or [])
    }

    if not stable_classes:
        return pd.Series(False, index=data.index)

    mirbase_class = data["Class_miRBase"].astype(str).str.strip().str.upper()
    mirgenedb_class = data["Class_MirGeneDB"].astype(str).str.strip().str.upper()

    return mirbase_class.isin(stable_classes) | mirgenedb_class.isin(stable_classes)



def compute_filtering_flags(data: pd.DataFrame) -> pd.DataFrame:
    """
    Compute expression, conservation and structure pass/fail flags using the
    current Filtering criteria controls. Used for the combination-count table.
    """
    out = data[overlap_missing(data)].copy()

    cutoff = float(st.session_state.get("sens_expression_cutoff", 1.5))
    min_tissues = int(st.session_state.get("sens_min_tissues", 1))
    min_species = int(st.session_state.get("sens_min_species", 3))
    stable_classes = {
        str(x).strip().upper()
        for x in (st.session_state.get("sens_stable_classes", ["R", "D"]) or [])
    }
    high_conf_filter = "Show all"

    if tissue_cols:
        tissue_num = out[tissue_cols].apply(pd.to_numeric, errors="coerce")
        out["_filter_expression_count"] = (tissue_num >= cutoff).sum(axis=1)
        out["_filter_expression_pass"] = out["_filter_expression_count"] >= min_tissues
    else:
        out["_filter_expression_count"] = 0
        out["_filter_expression_pass"] = False

    if animal_cols:
        out["_filter_conservation_count"] = out[animal_cols].apply(
            lambda r: r.isin([True]).sum(),
            axis=1,
        )
        out["_filter_conservation_pass"] = out["_filter_conservation_count"] >= min_species
    else:
        out["_filter_conservation_count"] = 0
        out["_filter_conservation_pass"] = False

    if stable_classes:
        mirbase_class = out["Class_miRBase"].astype(str).str.strip().str.upper()
        mirgenedb_class = out["Class_MirGeneDB"].astype(str).str.strip().str.upper()
        out["_filter_structure_pass"] = mirbase_class.isin(stable_classes) | mirgenedb_class.isin(stable_classes)
    else:
        out["_filter_structure_pass"] = False

    if high_conf_filter in ["High confidence", "High confidence (TRUE)"]:
        out = out[out["_High_confidence_tf"] == "TRUE"]
    elif high_conf_filter in ["Low confidence", "Low confidence (FALSE)"]:
        out = out[out["_High_confidence_tf"] == "FALSE"]

    return out


def build_filtering_combination_summary(data: pd.DataFrame) -> pd.DataFrame:
    """
    Report retained counts for the default rules or for the current custom rule.
    """
    flags = compute_filtering_flags(data)

    filtering_mode = st.session_state.get("filtering_mode", "Default")
    selected_rule = st.session_state.get("filtering_rule", "At least 2 of 3 criteria")

    evidence_count = (
        flags["_filter_conservation_pass"].astype(int)
        + flags["_filter_expression_pass"].astype(int)
        + flags["_filter_structure_pass"].astype(int)
    )

    if filtering_mode == "Custom":
        selected_labels = []
        selected_series = []

        if st.session_state.get("custom_use_conservation", True):
            selected_labels.append("Evolutionary conservation")
            selected_series.append(flags["_filter_conservation_pass"].astype(int))
        if st.session_state.get("custom_use_expression", True):
            selected_labels.append("Tissue Expression")
            selected_series.append(flags["_filter_expression_pass"].astype(int))
        if st.session_state.get("custom_use_structure", True):
            selected_labels.append("Structural class")
            selected_series.append(flags["_filter_structure_pass"].astype(int))

        selected_count = len(selected_series)
        custom_min = int(st.session_state.get("custom_min_criteria", min(2, selected_count)))
        custom_min = max(0, min(custom_min, selected_count))

        if selected_count == 0:
            retained = len(flags) if custom_min == 0 else 0
        else:
            custom_evidence_count = sum(selected_series)
            retained = int((custom_evidence_count >= custom_min).sum())

        label = " + ".join(selected_labels) if selected_labels else "No criteria selected"
        return pd.DataFrame([{
            "Applied": "✓",
            "Filtering rule": f"Custom: {label}; minimum passing = {custom_min}",
            "Retained miRNA/s": retained,
        }])

    rule_masks = {
        "At least 2 of 3 criteria": evidence_count >= 2,
        "All 3 criteria": (
            flags["_filter_conservation_pass"]
            & flags["_filter_expression_pass"]
            & flags["_filter_structure_pass"]
        ),
        "Stable structural class + at least one other criterion": (
            flags["_filter_structure_pass"]
            & (
                flags["_filter_conservation_pass"]
                | flags["_filter_expression_pass"]
            )
        ),
    }

    rows = []
    for rule_name, mask in rule_masks.items():
        rows.append({
            "Applied": "✓" if rule_name == selected_rule else "",
            "Filtering rule": rule_name,
            "Retained miRNA/s": int(mask.sum()),
        })

    return pd.DataFrame(rows)



def make_tsv_download(data: pd.DataFrame) -> bytes:
    """Convert a dataframe to TSV bytes for Streamlit download buttons."""
    if data is None:
        data = pd.DataFrame()
    return data.to_csv(index=False, sep="\t").encode("utf-8")


def safe_filename_label(label: str) -> str:
    """Make short, safe labels for generated TSV filenames."""
    return (
        str(label)
        .strip()
        .lower()
        .replace(" + ", "_plus_")
        .replace(" ", "_")
        .replace("/", "_")
        .replace("-", "_")
    )


def render_compact_html_table(data: pd.DataFrame, decimals: int = 2) -> None:
    """
    Render a compact HTML table that fits the page width better than st.dataframe
    for many narrow benchmark columns.
    """
    if data is None or data.empty:
        st.info("No data to display.")
        return

    display_df = data.copy()

    for col in display_df.columns:
        if pd.api.types.is_float_dtype(display_df[col]):
            if str(col).startswith("%"):
                display_df[col] = display_df[col].map(lambda x: f"{x:.2f}" if pd.notna(x) else "")
            else:
                display_df[col] = display_df[col].map(lambda x: f"{x:.{decimals}f}" if pd.notna(x) else "")

    html = display_df.to_html(index=False, escape=False)
    st.markdown(
        f"""
        <div class="compact-table-wrap">
            {html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def reorder_benchmark_columns(data: pd.DataFrame, include_selection: bool = True) -> pd.DataFrame:
    """
    Put Precision / Recall / F1 first in benchmark tables.
    Selection is hidden on-page and kept in downloaded TSV files.
    """
    if data is None or data.empty:
        return data.copy() if data is not None else pd.DataFrame()

    priority = ["Validation threshold", "Precision", "Recall", "F1"]
    if include_selection:
        priority = ["Selection"] + priority

    remaining = [c for c in data.columns if c not in priority]
    ordered = [c for c in priority if c in data.columns] + remaining
    return data[ordered].copy()


def build_validation_benchmark_table(catalogs: dict, reference_data: pd.DataFrame) -> pd.DataFrame:
    """
    Build a dynamic benchmark table against Experimental evidence.

    Universe = all candidate rows with missing/NA Overlap.

    NA Experimental evidence rows are never counted in TP, FP, FN,
    precision, recall, F1 or percentages. They are reported separately
    as "Experimental evidence NA included".

    Two benchmark thresholds are reported:
    - Stringent: supported = Experimental evidence level 2.
      not supported = Experimental evidence level 0 or 1.
    - Lenient: supported = Experimental evidence >= 1.
      not supported = Experimental evidence level 0.

    For each selection:
    - Supported included = selection ∩ supported Kim set
    - Not supported included = selection ∩ not-supported Kim set
    - Supported not included = supported Kim set \\ selection
    - Experimental evidence NA included = selection ∩ NA Kim set
    """
    if "miRNA" not in reference_data.columns or "_Experimental_evidence_level" not in reference_data.columns:
        return pd.DataFrame()

    ref = get_filtering_candidate_universe(reference_data)
    ref["miRNA"] = ref["miRNA"].astype(str)
    universe_set = set(ref["miRNA"])

    evidence_num = pd.to_numeric(ref["_Experimental_evidence_level"], errors="coerce")
    na_set = set(ref.loc[evidence_num.isna(), "miRNA"])

    threshold_definitions = [
        {
            "Validation threshold": "Stringent filter",
            "supported_mask": evidence_num == 2,
            "not_supported_mask": evidence_num.isin([0, 1]),
        },
        {
            "Validation threshold": "Lenient filter",
            "supported_mask": evidence_num >= 1,
            "not_supported_mask": evidence_num == 0,
        },
    ]

    rows = []

    def _safe_pct(num, den):
        if den == 0:
            return 0.0
        return (num / den) * 100

    def _safe_ratio(num, den):
        if den == 0:
            return 0.0
        return num / den

    for threshold in threshold_definitions:
        supported_set = set(ref.loc[threshold["supported_mask"], "miRNA"])
        not_supported_set = set(ref.loc[threshold["not_supported_mask"], "miRNA"])

        for label, catalog in catalogs.items():
            if catalog is None or "miRNA" not in catalog.columns:
                included_set = set()
            else:
                included_set = set(catalog["miRNA"].dropna().astype(str))

            included_set = included_set & universe_set

            tp = len(included_set & supported_set)
            fp = len(included_set & not_supported_set)
            fn = len(supported_set - included_set)
            na_included = len(included_set & na_set)

            precision = _safe_ratio(tp, tp + fp)
            recall = _safe_ratio(tp, tp + fn)
            f1 = _safe_ratio(2 * precision * recall, precision + recall)

            rows.append({
                "Selection": label,
                "Validation threshold": threshold["Validation threshold"],
                "Supported included": tp,
                "Not supported included": fp,
                "Supported not included": fn,
                "Experimental evidence NA included": na_included,
                "Supported total + NA included": tp + fn + na_included,
                "% Supported missed": round(_safe_pct(fn, tp + fn), 3),
                "% Not supported included": round(_safe_pct(fp, tp + fp), 3),
                "Precision": round(precision, 4),
                "Recall": round(recall, 4),
                "F1": round(f1, 4),
            })

    return pd.DataFrame(rows)



# ===========================================================
# TABS BAR (APP / SENSITIVITY / DOCUMENTATION)
# ===========================================================
tab_app, tab_sensitivity, tab_docs = st.tabs(["App", "Filtering criteria", "Documentation"])

# ✅ inject the tab switch + scroll router once
_inject_doc_nav_js()


# -----------------------------------------------------------
# Sidebar: Documentation (internal anchors, no new tab)
# (kept as main sections only)
# -----------------------------------------------------------
with st.sidebar.expander("Documentation", expanded=False):
    st.markdown("- " + doc_jump_link("doc_overview", "Overview"), unsafe_allow_html=True)
    st.markdown("- " + doc_jump_link("doc_key_features", "Main filters"), unsafe_allow_html=True)
    st.markdown("- " + doc_jump_link("doc_filter_database", "Database filter"), unsafe_allow_html=True)
    st.markdown("- " + doc_jump_link("doc_filtering_criteria", "Filtering criteria page"), unsafe_allow_html=True)
    st.markdown("- " + doc_jump_link("doc_advanced", "Advanced options"), unsafe_allow_html=True)
    st.markdown("- " + doc_jump_link("doc_adv_conservation", "Conservation details"), unsafe_allow_html=True)
    st.markdown("- " + doc_jump_link("doc_adv_tissue", "Expression details"), unsafe_allow_html=True)
    st.markdown("- " + doc_jump_link("doc_adv_db_class", "Structural class"), unsafe_allow_html=True)
    st.markdown("- " + doc_jump_link("doc_adv_confidence_evidence", "Experimental evidence"), unsafe_allow_html=True)
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
- Use Advanced options for additional column display controls  
- Export **TSV** / **FASTA** at the bottom of the table  
- Try the **Example use cases** presets at the bottom of the scrollable sidebar to quickly apply filter combinations  
- Use **Reset all filters** (bottom and top of the sidebar) to clear everything and start over
""")

    app_df = get_main_catalog()

    if st.session_state.get("apply_ablation_to_main", False):
        st.info(
            "Filtering criteria are currently applied to the main table. "
            "Conservation, Expression and Structure colors are evaluated against the selected filtering criteria."
        )

    # -----------------------------------------------------------
    # SIDEBAR: FILTERS + inline doc icons (FIXED: ℹ️ next to label)
    # -----------------------------------------------------------
    st.sidebar.header("Filters")

    # ✅ FIX 1: Reset all filters ALSO above the filters in the sidebar
    if any_filter_active():
        st.sidebar.markdown(doc_jump_link("doc_filter_reset", "Docs (reset)"), unsafe_allow_html=True)
        if st.sidebar.button("Reset all filters", use_container_width=True, key="reset_top"):
            reset_all_filters()
            st.rerun()

    search_term = sidebar_widget_inline_doc(
        st.sidebar.text_input,
        "Search by name:",
        "doc_filter_search_any",
        key="search_any",
    )

    # These top-level pass/fail filters were removed from the sidebar.
    # Keep them neutral so old browser/session state cannot silently filter rows.
    conservation_choice = "Show all"
    expression_choice = "Show all"
    structure_choice = "Show all"
    for _k in ["sb_conservation", "sb_expression", "sb_structure"]:
        st.session_state[_k] = "Show all"

    # Database/source filters: checkbox row, not mutually exclusive.
    # On first run after this version, start with all databases selected.
    # After that, user choices are preserved, including selecting none.
    if st.session_state.get("_db_defaults_version") != "v19":
        st.session_state["db_mirbase_full"] = True
        st.session_state["db_mirbase_hc"] = True
        st.session_state["db_mirgendb"] = True
        st.session_state["db_filter"] = ["miRBase-full", "miRBase-HC", "MirGeneDB"]
        st.session_state["_db_defaults_version"] = "v19"

    # Filtering-criteria presets are selected later in the script, but Streamlit
    # checkbox keys must be updated before the checkbox widgets are instantiated.
    # The preset callback stores the desired sidebar state here, then the next
    # rerun applies it safely at this point.
    pending_sidebar_db_sources = st.session_state.pop("_pending_sidebar_db_sources", None)
    if pending_sidebar_db_sources is not None:
        pending_sidebar_db_sources = list(pending_sidebar_db_sources or [])
        st.session_state["db_mirbase_full"] = "miRBase-full" in pending_sidebar_db_sources
        st.session_state["db_mirbase_hc"] = "miRBase-HC" in pending_sidebar_db_sources
        st.session_state["db_mirgendb"] = "MirGeneDB" in pending_sidebar_db_sources
        st.session_state["db_filter"] = pending_sidebar_db_sources

    sidebar_label_with_doc("Database:", "doc_filter_database")
    db_c1, db_c2, db_c3 = st.sidebar.columns(3)
    with db_c1:
        db_mirbase_full = st.checkbox("miRBase-full", key="db_mirbase_full")
    with db_c2:
        db_mirbase_hc = st.checkbox("miRBase-HC", key="db_mirbase_hc")
    with db_c3:
        db_mirgendb = st.checkbox("MirGeneDB", key="db_mirgendb")

    database_selected = []
    if db_mirbase_full:
        database_selected.append("miRBase-full")
    if db_mirbase_hc:
        database_selected.append("miRBase-HC")
    if db_mirgendb:
        database_selected.append("MirGeneDB")

    # Keep variable name used later, but it now stores a list of selected database sources.
    mirgene_filter = database_selected
    st.session_state["db_filter"] = database_selected

    # If a preset previously set the database sources, but the user now changes
    # the sidebar checkboxes manually, stop using the preset override.
    # This makes the Database checkboxes truly interactive again.
    active_preset_sources = st.session_state.get("filtering_preset_db_sources", None)
    if active_preset_sources is not None and sorted(database_selected) != sorted(list(active_preset_sources or [])):
        st.session_state["filtering_preset_db_sources"] = None

    exp_label_col, exp_doc_col = st.sidebar.columns([12, 1], vertical_alignment="center")
    with exp_label_col:
        show_exp_evidence_col = st.checkbox(
            "Show Experimental evidence (Kim et al. 2021)",
            value=False,
            key="show_exp_evidence_col",
        )
    with exp_doc_col:
        st.markdown(doc_jump_icon("doc_adv_confidence_evidence"), unsafe_allow_html=True)

    sidebar_label_with_doc("Filter Experimental evidence:", "doc_adv_confidence_evidence")
    experimental_evidence_filter = st.sidebar.selectbox(
        "Filter Experimental evidence:",
        [
            "Show all",
            "Pass stringent filter",
            "Pass lenient filter",
            "No pass",
        ],
        index=0,
        key="experimental_evidence_filter",
        label_visibility="collapsed",
    )

    hsa_sb_options = ["Show all", "Only hsa-specific", "Not hsa-specific"]
    hsa_choice = sidebar_widget_inline_doc(
        st.sidebar.radio,
        "hsa specificity:",
        "doc_filter_hsa",
        hsa_sb_options,
        index=0,
        key="sb_hsa",
        horizontal=True,
    )

    # Family filters removed. Keep neutral variable for downstream compatibility.
    family_selected = []

    repeats_selected = sidebar_widget_inline_doc(
        st.sidebar.multiselect,
        "Repeat class:",
        "doc_filter_repeat",
        sorted(app_df["Repeat_Class"].dropna().unique()) if "Repeat_Class" in app_df.columns else [],
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
    classes_selected = []

    show_high_conf_col = False
    show_overlap_col = False
    high_conf_filter = "Show all"
    experimental_evidence_filter = "Show all"

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
                f"<div style='margin-top:-2px; margin-bottom:6px;font-size:14px;'>{doc_jump_link('doc_adv_conservation', 'Docs (conservation)')}</div>",
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
                f"<div style='margin-top:-2px; margin-bottom:6px;font-size:14px;'>{doc_jump_link('doc_adv_tissue', 'Docs (expression)')}</div>",
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

        with st.sidebar.expander("Structural class", expanded=True):
            st.sidebar.markdown(
                f"<div style='margin-top:-2px; margin-bottom:6px;font-size:14px;'>{doc_jump_link('doc_adv_db_class', 'Docs (structural class)')}</div>",
                unsafe_allow_html=True
            )

            st.markdown("<div class='sidebar-section-title'>Show extra columns</div>", unsafe_allow_html=True)

            show_class_cols = st.checkbox(
                "Show Structural class columns",
                value=False,
                key="show_class_cols",
            )

            st.markdown("<hr class='subtle-hr'>", unsafe_allow_html=True)
            st.markdown("<div class='sidebar-section-title'>Filter extra columns</div>", unsafe_allow_html=True)

            classes_selected = st.multiselect(
                "Structural class:",
                ["R", "D", "I", "S"],
                default=[],
                key="class_filter",
            )




    def apply_preset(preset_name: str):
        reset_all_filters()

        st.session_state["show_adv"] = True
        st.session_state["sb_conservation"] = "Show all"
        st.session_state["sb_expression"] = "Show all"
        st.session_state["sb_structure"] = "Show all"
        st.session_state["sb_hsa"] = "Show all"
        st.session_state["show_repeat_plot"] = False

        st.session_state["search_any"] = ""
        st.session_state["ms_family"] = []
        st.session_state["ms_repeat"] = []
        st.session_state["db_filter"] = ["miRBase-full", "miRBase-HC", "MirGeneDB"]
        st.session_state["db_mirbase_full"] = True
        st.session_state["db_mirbase_hc"] = True
        st.session_state["db_mirgendb"] = True
        st.session_state["class_filter"] = []
        st.session_state["show_class_cols"] = False

        st.session_state["show_high_conf_col"] = False
        st.session_state["show_exp_evidence_col"] = False
        st.session_state["show_overlap_col"] = False
        st.session_state["high_conf_filter"] = "Show all"
        st.session_state["experimental_evidence_filter"] = "Show all"

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
        st.sidebar.markdown(doc_jump_link("doc_use_cases", "Docs (use cases)"), unsafe_allow_html=True)

        b1, b2 = st.columns(2)
        with b1:
            if st.button("Cardio + mouse", use_container_width=True):
                apply_preset("cardio_mouse")
        with b2:
            if st.button("Neuro + great apes", use_container_width=True):
                apply_preset("brain_primates")

    st.sidebar.markdown("---")
    if any_filter_active():
        # (Reset is a main doc anchor; icon could be made inline too, but left like this)
        st.sidebar.markdown(doc_jump_link("doc_filter_reset", "Docs (Reset)"), unsafe_allow_html=True)
        if st.sidebar.button("Reset all filters", use_container_width=True, key="reset_bottom"):
            reset_all_filters()
            st.rerun()

    # -----------------------------------------------------------
    # APPLY FILTERS
    # -----------------------------------------------------------
    filtered = app_df.copy()

    def apply_pass_choice(data: pd.DataFrame, choice: str, helper_col: str) -> pd.DataFrame:
        if not choice or choice == "Show all":
            return data
        if choice == "PASSED":
            return data[data[helper_col] == "TRUE"]
        if choice == "NOT PASSED":
            return data[data[helper_col] == "FALSE"]
        return data

    # Top-level Conservation / Expression / Structure pass-fail filters are not shown in the sidebar.
    # Advanced filtering remains available through the dedicated controls below.

    if hsa_choice != "Show all":
        hsa_flag = filtered["hsa-specificity"].astype(str).str.strip().str.upper()
        hsa_true = hsa_flag.isin(["YES", "TRUE", "1", "Y", "SI", "SÌ"])
        hsa_false = hsa_flag.isin(["NO", "FALSE", "0", "N"])
        if hsa_choice == "Only hsa-specific":
            filtered = filtered[hsa_true]
        elif hsa_choice == "Not hsa-specific":
            filtered = filtered[hsa_false]

    # Database/source filter.
    # This is always applied because all database checkboxes are selected by default.
    # If the user deselects all databases, db_mask remains all False and the table shows 0 rows.
    db_mask = pd.Series(False, index=filtered.index)

    mirbase_class = filtered["Class_miRBase"].astype(str).str.strip().str.upper()
    mirgenedb_class = filtered["Class_MirGeneDB"].astype(str).str.strip().str.upper()

    mirbase_present = filtered["Class_miRBase"].notna() & ~mirbase_class.isin(["", "NA", "NAN", "—", "-", "<NA>"])
    mirgenedb_present = filtered["Class_MirGeneDB"].notna() & ~mirgenedb_class.isin(["", "NA", "NAN", "—", "-", "<NA>"])

    if "miRBase-full" in mirgene_filter:
        db_mask |= mirbase_present
    if "miRBase-HC" in mirgene_filter:
        db_mask |= filtered["_High_confidence_tf"] == "TRUE"
    if "MirGeneDB" in mirgene_filter:
        db_mask |= mirgenedb_present

    filtered = filtered[db_mask]

    if classes_selected:
        mirbase_class = filtered["Class_miRBase"].astype(str).str.strip().str.upper()
        mirgenedb_class = filtered["Class_MirGeneDB"].astype(str).str.strip().str.upper()
        filtered = filtered[
            mirbase_class.isin(classes_selected)
            | mirgenedb_class.isin(classes_selected)
        ]

    high_conf_filter = st.session_state.get("high_conf_filter", "Show all")
    experimental_evidence_filter = st.session_state.get("experimental_evidence_filter", "Show all")

    if high_conf_filter in ["High confidence", "High confidence (TRUE)"]:
        filtered = filtered[filtered["_High_confidence_tf"] == "TRUE"]
    elif high_conf_filter in ["Low confidence", "Low confidence (FALSE)"]:
        filtered = filtered[filtered["_High_confidence_tf"] == "FALSE"]

    if experimental_evidence_filter == "Pass stringent filter":
        filtered = filtered[filtered["_Experimental_evidence_level"] == 2]
    elif experimental_evidence_filter == "Pass lenient filter":
        filtered = filtered[filtered["_Experimental_evidence_level"] == 1]
    elif experimental_evidence_filter == "No pass":
        filtered = filtered[filtered["_Experimental_evidence_level"] == 0]


    # Family filtering removed.


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
    def _go_prev_page():
        st.session_state["page"] = max(1, int(st.session_state.get("page", 1)) - 1)

    def _go_next_page():
        st.session_state["page"] = min(total_pages, int(st.session_state.get("page", 1)) + 1)

    nav_c1, nav_c2, nav_c3 = st.columns([1, 2, 1])
    with nav_c1:
        st.button(
            "← Prev",
            disabled=st.session_state["page"] == 1,
            use_container_width=True,
            key="main_prev_page",
            on_click=_go_prev_page,
        )
    with nav_c3:
        st.button(
            "Next →",
            disabled=st.session_state["page"] == total_pages,
            use_container_width=True,
            key="main_next_page",
            on_click=_go_next_page,
        )
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

    # Display counts are dynamic when ablation criteria are applied to the main table.
    # Otherwise they use the manuscript/default display logic.
    if st.session_state.get("apply_ablation_to_main", False):
        df_display["Conservation"] = current_conservation_count(df_display)
        df_display["Expression"] = current_expression_count(df_display)
    else:
        df_display["Conservation"] = df_display["Conservation_display"]
        df_display["Expression"] = df_display["Expression_display"]

    df_display["Structure"] = df_display["Structure_display"]
    df_display["_Structure_dynamic_tf"] = current_structure_pass(df_display).map(lambda x: "TRUE" if bool(x) else "FALSE")

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

    if "Class MirGeneDB" in df_display.columns:
        df_display["Class MirGeneDB"] = (
            df_display["Class MirGeneDB"]
            .replace(["—", "-", "", "nan", "NaN", "<NA>"], "NA")
            .fillna("NA")
        )

    mandatory_display_cols = [
        "miRNA", "Conservation", "Expression", "Structure",
        "MirGeneDB family", "miRBase family", "hsa-specificity", "Repeat Class",
    ]

    animals_to_show_display = [animal_display_names[c] for c in animals_to_show if c in animal_display_names]
    tissues_to_show_display = [c for c in tissues_to_show if c in df_display.columns]
    class_to_show_display = ["Class miRBase", "Class MirGeneDB"] if show_class_cols else []

    evidence_to_show_display = []

    if st.session_state.get("show_exp_evidence_col", False):
        evidence_to_show_display.append("Experimental evidence")


    evidence_to_show_display = [c for c in evidence_to_show_display if c in df_display.columns]

    desired_order = (
        ["miRNA", "Conservation"]
        + animals_to_show_display
        + ["Expression"]
        + tissues_to_show_display
        + ["Structure"]
        + class_to_show_display
        + evidence_to_show_display
        + ["MirGeneDB family", "miRBase family", "hsa-specificity", "Repeat Class"]
    )

    visible_cols = []
    for c in desired_order:
        if (
            (c in mandatory_display_cols)
            or (c in animals_to_show_display)
            or (c in tissues_to_show_display)
            or (c in class_to_show_display)
            or (c in evidence_to_show_display)
        ):
            if c in df_display.columns:
                visible_cols.append(c)

    if not visible_cols:
        visible_cols = [c for c in mandatory_display_cols if c in df_display.columns]

    helper_cols = [
        "_Conservation_tf",
        "_Expression_tf", "_Structure_tf", "_Structure_dynamic_tf",
        "_miRBase_family_flag", "_MirGeneDB_family_flag",
        "_High_confidence_tf", "_Experimental_evidence_level",
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

    if st.session_state.get("apply_ablation_to_main", False):
        df_export_full["Conservation"] = current_conservation_count(df_export_full)
        df_export_full["Expression"] = current_expression_count(df_export_full)
    else:
        df_export_full["Conservation"] = df_export_full["Conservation_display"]
        df_export_full["Expression"] = df_export_full["Expression_display"]

    df_export_full["Structure"] = df_export_full["Structure_display"]
    df_export_full["_Structure_dynamic_tf"] = current_structure_pass(df_export_full).map(lambda x: "TRUE" if bool(x) else "FALSE")

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

    if "Class MirGeneDB" in df_export_full.columns:
        df_export_full["Class MirGeneDB"] = (
            df_export_full["Class MirGeneDB"]
            .replace(["—", "-", "", "nan", "NaN", "<NA>"], "NA")
            .fillna("NA")
        )

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

    HIGH_CONF_TRUE_COLOR = "#F2B6C6"
    HIGH_CONF_FALSE_COLOR = "#D9D9D9"

    EXP_EVIDENCE_STRINGENT_COLOR = "#F2C94C"  # gold
    EXP_EVIDENCE_LENIENT_COLOR = "#D9F0D3"    # light green
    EXP_EVIDENCE_NOPASS_COLOR = "#E6E6E6"     # light gray
    EXP_EVIDENCE_NODATA_COLOR = "#FFFFFF"     # white
    OVERLAP_BG = "#d9f0a3"

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
        s = str(v).strip().upper()
        if s in ["YES", "TRUE", "1", "Y", "SI", "SÌ"]:
            return "background-color:#f1b6da;"
        if s in ["NO", "FALSE", "0", "N"]:
            return "background-color:#0072B2;"
        return ""

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


    def bg_dynamic_count(v, threshold):
        """
        Color a displayed count according to the current threshold.
        The comparison is intentionally >=, matching the ablation/filter criteria.
        """
        if pd.isna(v):
            return ""
        try:
            x = float(v)
        except Exception:
            return ""
        if x >= float(threshold):
            return f"background-color:{TRUE_COLOR};"
        return f"background-color:{FALSE_COLOR};"

    def bg_family(flag):
        if pd.isna(flag):
            return "background-color:white;"
        f = str(flag).strip().upper()
        if f == "YES":
            return f"background-color:{FAM_YES_COLOR};"
        if f == "NO":
            return f"background-color:{FAM_NO_COLOR};"
        if f in ["", "NAN", "NA", "—", "<NA>"]:
            return "background-color:white;"
        return "background-color:white;"

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
            return "background-color:white; color:black !important;"
        s = str(v).strip().upper()
        if s in ["NA", "—", "-", "", "NAN", "<NA>"]:
            return "background-color:white; color:black !important;"
        if s == "R":
            return f"background-color:{CLASS_R_BG}; color: white !important;"
        if s == "D":
            return f"background-color:{CLASS_D_BG}; color: black !important;"
        if s == "I":
            return f"background-color:{CLASS_I_BG}; color: white !important;"
        if s == "S":
            return f"background-color:{CLASS_S_BG}; color: black !important;"
        return ""

    def bg_high_conf(flag):
        if pd.isna(flag):
            return ""
        f = str(flag).upper()
        if f == "TRUE":
            return f"background-color:{HIGH_CONF_TRUE_COLOR}; color: black !important;"
        if f == "FALSE":
            return f"background-color:{HIGH_CONF_FALSE_COLOR}; color: black !important;"
        return ""

    def bg_experimental_evidence(level):
        if pd.isna(level):
            return f"background-color:{EXP_EVIDENCE_NODATA_COLOR}; color: black !important;"
        try:
            lvl = int(float(level))
        except Exception:
            return f"background-color:{EXP_EVIDENCE_NODATA_COLOR}; color: black !important;"
        if lvl == 2:
            return f"background-color:{EXP_EVIDENCE_STRINGENT_COLOR}; color: black !important;"
        if lvl == 1:
            return f"background-color:{EXP_EVIDENCE_LENIENT_COLOR}; color: black !important;"
        if lvl == 0:
            return f"background-color:{EXP_EVIDENCE_NOPASS_COLOR}; color: black !important;"
        return f"background-color:{EXP_EVIDENCE_NODATA_COLOR}; color: black !important;"

    def overlap_bg(v):
        if pd.isna(v):
            return ""
        return f"background-color:{OVERLAP_BG}; color: black !important;"

    visible_species_cols = [animal_display_names[c] for c in animals_to_show if c in animal_display_names]
    visible_species_cols = [c for c in visible_species_cols if c in df_display.columns]
    visible_tissue_cols = [c for c in tissues_to_show_display if c in df_display.columns]
    visible_class_cols = [c for c in class_to_show_display if c in df_display.columns]
    visible_overlap_cols = [
        c for c in ["Overlap"]
        if c in df_display.columns and c in evidence_to_show_display
    ]

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


    if visible_overlap_cols:
        styled_df = styled_df.applymap(overlap_bg, subset=visible_overlap_cols)

    conservation_color_threshold = (
        int(st.session_state.get("sens_min_species", 3))
        if st.session_state.get("apply_ablation_to_main", False)
        else 3
    )
    expression_color_threshold = (
        int(st.session_state.get("sens_min_tissues", 1))
        if st.session_state.get("apply_ablation_to_main", False)
        else 1
    )

    def style_row(row):
        styles = ["font-weight: 700; font-size: 10px;"] * len(row)
        idx = {c: i for i, c in enumerate(row.index)}

        if "Conservation" in idx:
            styles[idx["Conservation"]] += bg_dynamic_count(row["Conservation"], conservation_color_threshold)
        if "Expression" in idx:
            styles[idx["Expression"]] += bg_dynamic_count(row["Expression"], expression_color_threshold)
        if "Structure" in idx:
            if "_Structure_dynamic_tf" in idx:
                styles[idx["Structure"]] += bg_true_false(row["_Structure_dynamic_tf"])
            elif "_Structure_tf" in idx:
                styles[idx["Structure"]] += bg_true_false(row["_Structure_tf"])

        if "miRBase family" in idx and "_miRBase_family_flag" in idx:
            _flag = row["_miRBase_family_flag"]
            styles[idx["miRBase family"]] += bg_family(_flag)
            if str(_flag).strip().upper() == "NO":
                styles[idx["miRBase family"]] += "color: transparent !important; text-shadow: 0 0 0 transparent !important;"
        if "MirGeneDB family" in idx and "_MirGeneDB_family_flag" in idx:
            _flag = row["_MirGeneDB_family_flag"]
            styles[idx["MirGeneDB family"]] += bg_family(_flag)
            if str(_flag).strip().upper() == "NO":
                styles[idx["MirGeneDB family"]] += "color: transparent !important; text-shadow: 0 0 0 transparent !important;"

        if "miRBase high confidence miRNA" in idx and "_High_confidence_tf" in idx:
            styles[idx["miRBase high confidence miRNA"]] += (
                bg_high_conf(row["_High_confidence_tf"])
                + "color: transparent !important; text-shadow: 0 0 0 transparent !important;"
            )

        if "Experimental evidence" in idx and "_Experimental_evidence_level" in idx:
            styles[idx["Experimental evidence"]] += bg_experimental_evidence(row["_Experimental_evidence_level"])
            if not pd.isna(row["_Experimental_evidence_level"]):
                styles[idx["Experimental evidence"]] += (
                    "color: transparent !important; text-shadow: 0 0 0 transparent !important;"
                )
            else:
                styles[idx["Experimental evidence"]] += "color: black !important;"


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
    st.markdown('<div id="main_table_anchor" class="doc-anchor"></div>', unsafe_allow_html=True)

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

    if "miRBase high confidence miRNA" in evidence_to_show_display:
        legend_cards.append(f"""
<div class="legend-card">
  <div class="legend-title">miRBase high confidence miRNA</div>
  <div class="legend-row">
    <span class="legend-item"><span class="swatch" style="background:{HIGH_CONF_TRUE_COLOR};"></span>TRUE</span>
    <span class="legend-item"><span class="swatch" style="background:{HIGH_CONF_FALSE_COLOR};"></span>FALSE</span>
  </div>
</div>
""")

    if "Experimental evidence" in evidence_to_show_display:
        legend_cards.append(f"""
<div class="legend-card">
  <div class="legend-title">Experimental evidence</div>
  <div class="legend-row">
    <span class="legend-item"><span class="swatch" style="background:{EXP_EVIDENCE_STRINGENT_COLOR};"></span>Pass stringent filter</span>
    <span class="legend-item"><span class="swatch" style="background:{EXP_EVIDENCE_LENIENT_COLOR};"></span>Pass lenient filter</span>
    <span class="legend-item"><span class="swatch" style="background:{EXP_EVIDENCE_NOPASS_COLOR};"></span>No pass</span>
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
# TAB 2 — ABLATION ANALYSIS
# ===========================================================
with tab_sensitivity:
    st.markdown(
        """
        <style>
        /* Compact tables used in Filtering criteria benchmark. */
        .compact-table-wrap{
            width: 100%;
            overflow-x: visible;
            margin: 0.15rem 0 0.65rem 0;
        }
        .compact-table-wrap table{
            width: 100%;
            table-layout: fixed;
            border-collapse: collapse;
            font-size: clamp(14px, 0.98vw, 18px);
            line-height: 1.08;
        }
        .compact-table-wrap th,
        .compact-table-wrap td{
            border: 1px solid rgba(128,128,128,0.24);
            padding: 0.28rem 0.24rem;
            text-align: center;
            vertical-align: middle;
            white-space: normal;
            overflow-wrap: anywhere;
            word-break: normal;
        }
        .compact-table-wrap th{
            background: color-mix(in srgb, var(--text) 5%, transparent);
            font-weight: 900;
            color: var(--text);
        }
        .compact-table-wrap td{
            font-weight: 400;
        }
        .compact-table-wrap td:first-child{
            font-weight: 800;
        }
        .compact-table-wrap td:nth-child(2),
        .compact-table-wrap td:nth-child(3),
        .compact-table-wrap td:nth-child(4){
            font-weight: 800;
        }

        .min-criteria-card{
            border: 1px solid color-mix(in srgb, var(--text) 18%, transparent);
            border-radius: 14px;
            padding: 0.85rem 1rem 0.95rem 1rem;
            background: color-mix(in srgb, var(--bg) 94%, var(--text) 6%);
            margin: 0.25rem 0 1rem 0;
        }
        .min-criteria-card-title{
            font-weight: 800;
            font-size: 0.95rem;
            margin-bottom: 0.15rem;
        }
        .min-criteria-card-caption{
            opacity: 0.75;
            font-size: 0.80rem;
            margin-bottom: 0.55rem;
        }
        div[data-testid="stDownloadButton"] button{
            font-size: 0.78rem !important;
            padding: 0.22rem 0.45rem !important;
            min-height: 1.7rem !important;
            border-radius: 0.45rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("Filtering criteria")
    st.markdown(
        "Explore how the retained catalog size changes under alternative "
        "expression, conservation and structural-class criteria."
    )

    def _filtering_settings_changed():
        # Changing criteria only updates the counts on this page.
        # The main table is changed only after explicitly clicking
        # "Apply filtering criteria to main table" again.
        st.session_state["apply_ablation_to_main"] = False
        st.session_state["_switch_to_app_after_apply"] = False

    def _set_database_sources(sources):
        # Sidebar database checkboxes are instantiated before this page is rendered.
        # Streamlit does not allow changing their widget keys afterward.
        # Store preset database choices in a separate internal key for calculations,
        # and queue the same choice so the sidebar checkboxes update on the next rerun.
        sources = list(sources or [])
        st.session_state["filtering_preset_db_sources"] = sources
        st.session_state["_pending_sidebar_db_sources"] = sources

    def _set_filtering_defaults(database_sources=None):
        st.session_state["filtering_rule"] = "At least 2 of 3 criteria"
        st.session_state["sens_expression_cutoff"] = 1.5
        st.session_state["sens_min_tissues"] = 1
        st.session_state["sens_min_species"] = 3
        st.session_state["sens_stable_classes"] = ["R", "D"]
        st.session_state["custom_use_conservation"] = True
        st.session_state["custom_use_expression"] = True
        st.session_state["custom_use_structure"] = True
        st.session_state["custom_min_criteria"] = 2
        st.session_state["_last_custom_selected_count"] = 3
        if database_sources is not None:
            _set_database_sources(database_sources)

    def _set_database_only_defaults(database_sources):
        # Database/source defaults represent the selected catalog/source only.
        # Evidence criteria are intentionally neutral and displayed as 0 / empty.
        st.session_state["filtering_rule"] = "At least 2 of 3 criteria"
        st.session_state["sens_expression_cutoff"] = 0.0
        st.session_state["sens_min_tissues"] = 0
        st.session_state["sens_min_species"] = 0
        st.session_state["sens_stable_classes"] = []
        st.session_state["custom_use_conservation"] = True
        st.session_state["custom_use_expression"] = True
        st.session_state["custom_use_structure"] = True
        st.session_state["custom_min_criteria"] = 2
        st.session_state["_last_custom_selected_count"] = 3
        _set_database_sources(database_sources)

    def _set_kim_optimised_defaults():
        st.session_state["filtering_rule"] = "At least 2 of 3 criteria"
        st.session_state["sens_expression_cutoff"] = 0.5
        st.session_state["sens_min_tissues"] = 1
        st.session_state["sens_min_species"] = 3
        st.session_state["sens_stable_classes"] = ["R"]
        st.session_state["custom_use_conservation"] = True
        st.session_state["custom_use_expression"] = True
        st.session_state["custom_use_structure"] = True
        st.session_state["custom_min_criteria"] = 2
        st.session_state["_last_custom_selected_count"] = 3
        _set_database_sources(["miRBase-full", "miRBase-HC", "MirGeneDB"])

    def _set_custom_starting_defaults():
        # Reset the Custom panel to its initial/default configuration each time
        # the user enters Custom from another Filtering setup.
        st.session_state["filtering_preset_db_sources"] = None
        st.session_state.pop("_pending_sidebar_db_sources", None)
        st.session_state["filtering_rule"] = "At least 2 of 3 criteria"
        st.session_state["sens_expression_cutoff"] = 1.5
        st.session_state["sens_min_tissues"] = 1
        st.session_state["sens_min_species"] = 3
        st.session_state["sens_stable_classes"] = ["R", "D"]
        st.session_state["custom_use_conservation"] = True
        st.session_state["custom_use_expression"] = True
        st.session_state["custom_use_structure"] = True
        st.session_state["custom_min_criteria"] = 2
        st.session_state["_last_custom_selected_count"] = 3

    def _apply_filtering_setup_preset():
        setup = st.session_state.get("filtering_mode", "Default")

        if setup == "Default":
            _set_filtering_defaults(["miRBase-full", "miRBase-HC", "MirGeneDB"])
        elif setup == "miRBase-full":
            _set_database_only_defaults(["miRBase-full"])
        elif setup == "miRBase-HC":
            _set_database_only_defaults(["miRBase-HC"])
        elif setup == "MirGeneDB":
            _set_database_only_defaults(["MirGeneDB"])
        elif setup == "Kim et al. optimised":
            _set_kim_optimised_defaults()
        elif setup == "Custom":
            _set_custom_starting_defaults()

    def _filtering_mode_changed():
        _filtering_settings_changed()
        _apply_filtering_setup_preset()


    default_overlap = get_default_overlap_catalog()

    # Prevent stale navigation state from switching to the App tab when the
    # user changes only the Filtering setup.
    if not st.session_state.get("apply_ablation_to_main", False):
        st.session_state["_switch_to_app_after_apply"] = False

    filtering_mode = st.radio(
        "Filtering setup",
        [
            "Default",
            "miRBase-full",
            "miRBase-HC",
            "MirGeneDB",
            "Kim et al. optimised",
            "Custom",
        ],
        key="filtering_mode",
        horizontal=True,
        on_change=_filtering_mode_changed,
    )

    previous_filtering_mode = st.session_state.get("_last_filtering_mode_rendered", None)

    if filtering_mode == "Custom" and previous_filtering_mode != "Custom":
        _set_custom_starting_defaults()
    elif filtering_mode != "Custom" and previous_filtering_mode != filtering_mode:
        # Apply preset values only when the setup changes.
        # Do not re-apply on every rerun, otherwise sidebar Database checkboxes
        # are forced back to the preset and cannot be manually deselected.
        _apply_filtering_setup_preset()

    st.session_state["_last_filtering_mode_rendered"] = filtering_mode

    filtering_candidate_df = get_filtering_candidate_universe(df_all)
    filtering_base_df = apply_filtering_page_sidebar_filters(filtering_candidate_df)
    active_database_sources = get_active_filtering_database_sources()
    active_database_label = ", ".join(active_database_sources) if active_database_sources else "None"


    st.markdown(
        """
        <style>
        .criteria-title{
          font-size: 22px;
          font-weight: 800;
          line-height: 1.08;
          margin-bottom: 14px;
        }
        .criteria-subtitle{
          font-size: 13px;
          opacity: 0.75;
          margin-top: -6px;
          margin-bottom: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    c1, c2, c3 = st.columns(3, gap="large")

    with c1:
        with st.container(border=True):
            st.markdown("<div class='criteria-title'>Evolutionary<br>conservation</div>", unsafe_allow_html=True)
            if st.session_state.get("filtering_mode", "Default") == "Custom":
                st.checkbox("Use this criterion", key="custom_use_conservation", on_change=_filtering_settings_changed)
            st.markdown("<div class='criteria-subtitle'>Species-level stable conservation support</div>", unsafe_allow_html=True)
            sens_min_species = st.slider(
                "Minimum conserved species",
                min_value=0,
                max_value=max(1, len(animal_cols)),
                step=1,
                key="sens_min_species",
                on_change=_filtering_settings_changed,
                disabled=(filtering_mode != "Custom"),
            )

    with c2:
        with st.container(border=True):
            st.markdown("<div class='criteria-title'>Tissue Expression</div>", unsafe_allow_html=True)
            if st.session_state.get("filtering_mode", "Default") == "Custom":
                st.checkbox("Use this criterion", key="custom_use_expression", on_change=_filtering_settings_changed)
            st.markdown("<div class='criteria-subtitle'>Expression support across tissues</div>", unsafe_allow_html=True)
            sens_expression_cutoff = st.slider(
                "Expression RPMM threshold",
                min_value=0.0,
                max_value=10.0,
                step=0.1,
                key="sens_expression_cutoff",
                on_change=_filtering_settings_changed,
                disabled=(filtering_mode != "Custom"),
            )
            sens_min_tissues = st.number_input(
                "Minimum expressed tissues",
                min_value=0,
                max_value=max(1, len(tissue_cols)),
                step=1,
                key="sens_min_tissues",
                on_change=_filtering_settings_changed,
                disabled=(filtering_mode != "Custom"),
            )

    with c3:
        with st.container(border=True):
            st.markdown("<div class='criteria-title'>Structural class</div>", unsafe_allow_html=True)
            if st.session_state.get("filtering_mode", "Default") == "Custom":
                st.checkbox("Use this criterion", key="custom_use_structure", on_change=_filtering_settings_changed)
            st.markdown("<div class='criteria-subtitle'>Structural class</div>", unsafe_allow_html=True)

            structural_class_options = ["R", "D", "I", "S"]

            sens_stable_classes = st.multiselect(
                "Structural class",
                structural_class_options,
                key="sens_stable_classes",
                on_change=_filtering_settings_changed,
                disabled=(filtering_mode != "Custom"),
            )

    if filtering_mode == "Custom":
        active_custom_criteria = [
            st.session_state.get("custom_use_conservation", True),
            st.session_state.get("custom_use_expression", True),
            st.session_state.get("custom_use_structure", True),
        ]
        selected_custom_count = int(sum(active_custom_criteria))

        recommended_min_criteria = (
            selected_custom_count - 1
            if selected_custom_count >= 2
            else selected_custom_count
        )

        last_selected_custom_count = st.session_state.get(
            "_last_custom_selected_count",
            selected_custom_count,
        )

        if last_selected_custom_count != selected_custom_count:
            st.session_state["custom_min_criteria"] = recommended_min_criteria
            st.session_state["_last_custom_selected_count"] = selected_custom_count
        elif int(st.session_state.get("custom_min_criteria", recommended_min_criteria)) > selected_custom_count:
            st.session_state["custom_min_criteria"] = recommended_min_criteria

        st.markdown(
            """
            <div class="min-criteria-card">
              <div class="min-criteria-card-title">Minimum criteria to pass</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        min_col, _ = st.columns([1.25, 5])
        with min_col:
            st.number_input(
                "Minimum number of selected criteria that must pass",
                min_value=0,
                max_value=selected_custom_count,
                step=1,
                key="custom_min_criteria",
                label_visibility="collapsed",
                help="This number cannot be greater than the number of selected criteria.",
                on_change=_filtering_settings_changed,
            )

    st.markdown("---")

    # First compute the retained set from the full candidate table, then intersect
    # with the active Database selection. This makes the Database filter affect
    # the Filtering retained number exactly as it affects the main table.
    retained_sens_all = compute_ablation_catalog(df_all)
    retained_filters_only = apply_filtering_page_sidebar_filters(filtering_candidate_df)
    retained_sens = apply_filtering_page_sidebar_filters(retained_sens_all)

    db_only_preset = filtering_mode in ["miRBase-full", "miRBase-HC", "MirGeneDB"]

    if db_only_preset:
        st.metric("Retained by criteria + filters", len(retained_sens))
    else:
        top_m1, top_m2 = st.columns(2)
        top_m1.metric("Retained by criteria", len(retained_sens_all))
        top_m2.metric("Retained by criteria + filters", len(retained_sens))

    def _mark_apply_state():
        # Apply criteria to the App table, but never navigate automatically.
        if st.session_state.get("apply_ablation_to_main", False):
            st.session_state["_switch_to_app_after_apply"] = True
        else:
            st.session_state["_switch_to_app_after_apply"] = False

    st.checkbox(
        "Apply filtering criteria to main table",
        value=False,
        key="apply_ablation_to_main",
        help=(
            "Click this after choosing criteria to update the main App table with the filtering-retained catalog. "
            "If you later change criteria, this is automatically turned off until you apply again."
        ),
        on_change=_mark_apply_state,
    )

    # Do not automatically switch tabs.
    # The user can go to the App tab manually after applying filtering criteria.
    if st.session_state.pop("_switch_to_app_after_apply", False):
        st.info("Filtering criteria are applied. Open the App tab to view the updated main table.")

    if db_only_preset:
        st.caption(
            "Database/source presets do not use evidence criteria; the retained count shows the selected source after active sidebar filters."
        )
    else:
        st.caption(
            "Retained by criteria uses only the selected Filtering criteria. "
            "Retained by criteria + filters also applies the active sidebar filters."
        )

    if filtering_mode == "Custom":
        with st.container(border=True):
            st.subheader("Criteria combination summary")
            st.caption(
                "Custom setup shown after applying the active sidebar filters."
            )

            combination_summary_df = build_filtering_combination_summary(filtering_base_df)
            render_compact_html_table(combination_summary_df)
            st.download_button(
                "Download criteria combination summary (TSV)",
                data=make_tsv_download(combination_summary_df),
                file_name="criteria_combination_summary.tsv",
                mime="text/tab-separated-values",
                key="download_criteria_combination_summary",
                use_container_width=False,
            )

    with st.container(border=True):
        st.subheader("Experimental-evidence benchmark")
        st.caption(
            "Dynamic benchmark against Experimental evidence over the active Filtering criteria universe. "
            "The fixed Default is always shown as baseline. Separate sections show Criteria and Criteria + filters when relevant. "
            "Criteria applies only the selected Filtering criteria; Criteria + filters also applies the active visible sidebar filters. "
            "Rows with missing Experimental evidence are reported separately and are never counted in TP, FP, FN, precision, recall or F1."
        )

        benchmark_section_tables = []

        def show_benchmark_section(title: str, catalog: pd.DataFrame):
            st.markdown(f"#### {title}")
            section_df = build_validation_benchmark_table({title: catalog}, df_all)
            if section_df.empty:
                st.info("Experimental-evidence benchmark is unavailable because the required columns are missing.")
            else:
                section_download_df = reorder_benchmark_columns(section_df, include_selection=True)
                section_display_df = reorder_benchmark_columns(section_df, include_selection=False)
                if "Selection" in section_display_df.columns:
                    section_display_df = section_display_df.drop(columns=["Selection"])

                benchmark_section_tables.append(section_download_df)
                render_compact_html_table(section_display_df)

                dl_col, _ = st.columns([1.15, 7])
                with dl_col:
                    st.download_button(
                        "Download TSV",
                        data=make_tsv_download(section_download_df),
                        file_name=f"experimental_evidence_benchmark_{safe_filename_label(title)}.tsv",
                        mime="text/tab-separated-values",
                        key=f"download_benchmark_{safe_filename_label(title)}",
                        use_container_width=True,
                    )

        current_setup_label = str(filtering_mode)

        show_benchmark_section("Default", get_default_overlap_catalog())

        if db_only_preset:
            show_benchmark_section(f"{current_setup_label} + Filters", retained_sens)
        elif filtering_mode == "Custom":
            show_benchmark_section("Custom", retained_sens_all)
            show_benchmark_section("Custom + Filters", retained_sens)
        elif filtering_mode != "Default":
            show_benchmark_section(current_setup_label, retained_sens_all)
            show_benchmark_section(f"{current_setup_label} + Filters", retained_sens)
        elif len(retained_sens) != len(get_default_overlap_catalog()) or len(retained_filters_only) != len(filtering_candidate_df):
            show_benchmark_section("Default + Filters", retained_sens)

        if benchmark_section_tables:
            benchmark_all_df = reorder_benchmark_columns(
                pd.concat(benchmark_section_tables, ignore_index=True),
                include_selection=True,
            )
            dl_all_col, _ = st.columns([1.35, 7])
            with dl_all_col:
                st.download_button(
                    "Download all TSV",
                    data=make_tsv_download(benchmark_all_df),
                    file_name="experimental_evidence_benchmark_all_sections.tsv",
                    mime="text/tab-separated-values",
                    key="download_benchmark_all_sections",
                    use_container_width=True,
                )

            st.markdown("#### Precision / recall overview")
            st.caption(
                "Each point corresponds to a unique Precision/Recall/F1 combination among the benchmark rows shown above. "
                "The x-axis is Recall, the y-axis is Precision, and the label reports only F1. "
                "If multiple selections have identical Precision, Recall and F1, they are merged into one point and listed together in the legend/tooltip."
            )

            plot_df = benchmark_all_df.copy()
            if not plot_df.empty and {"Selection", "Precision", "Recall", "F1", "Validation threshold"}.issubset(plot_df.columns):
                # Use the same two-decimal precision shown in the benchmark tables.
                # This avoids showing multiple points when the displayed values are identical.
                plot_df["Precision_plot"] = pd.to_numeric(plot_df["Precision"], errors="coerce").round(2)
                plot_df["Recall_plot"] = pd.to_numeric(plot_df["Recall"], errors="coerce").round(2)
                plot_df["F1_plot"] = pd.to_numeric(plot_df["F1"], errors="coerce").round(2)

                def render_precision_recall_scatter(threshold_label: str):
                    threshold_df = plot_df[plot_df["Validation threshold"] == threshold_label].copy()
                    if threshold_df.empty:
                        return

                    # Merge identical visible points into a single plotted point.
                    grouped = (
                        threshold_df
                        .groupby(["Validation threshold", "Precision_plot", "Recall_plot", "F1_plot"], dropna=False)
                        .agg(
                            **{
                                "Selection group": ("Selection", lambda s: " / ".join(dict.fromkeys(s.astype(str)))),
                                "N selections": ("Selection", "nunique"),
                            }
                        )
                        .reset_index()
                    )

                    grouped["F1 label"] = grouped["F1_plot"].map(lambda x: f"{x:.2f}" if pd.notna(x) else "")
                    grouped["Legend"] = grouped.apply(
                        lambda r: (
                            f"{r['Selection group']} (same point)"
                            if int(r["N selections"]) > 1
                            else str(r["Selection group"])
                        ),
                        axis=1,
                    )

                    def stable_color_key(selection_group: str) -> str:
                        parts = [p.strip() for p in str(selection_group).split(" / ")]
                        if "Default" in parts:
                            return "Default"
                        if "Default + Filters" in parts:
                            return "Default + Filters"
                        if "Custom" in parts:
                            return "Custom"
                        if "Custom + Filters" in parts:
                            return "Custom + Filters"
                        if "Kim et al. optimised" in parts:
                            return "Kim et al. optimised"
                        if "Kim et al. optimised + Filters" in parts:
                            return "Kim et al. optimised + Filters"
                        if "miRBase-full + Filters" in parts:
                            return "miRBase-full + Filters"
                        if "miRBase-HC + Filters" in parts:
                            return "miRBase-HC + Filters"
                        if "MirGeneDB + Filters" in parts:
                            return "MirGeneDB + Filters"
                        return parts[0] if parts else "Selection"

                    color_map = {
                        "Default": "#1f77b4",
                        "Default + Filters": "#aec7e8",
                        "Custom": "#d62728",
                        "Custom + Filters": "#ff9896",
                        "Kim et al. optimised": "#2ca02c",
                        "Kim et al. optimised + Filters": "#98df8a",
                        "miRBase-full + Filters": "#9467bd",
                        "miRBase-HC + Filters": "#8c564b",
                        "MirGeneDB + Filters": "#e377c2",
                    }

                    grouped["Color key"] = grouped["Selection group"].map(stable_color_key)
                    grouped["Point color"] = grouped["Color key"].map(color_map).fillna("#7f7f7f")

                    # Label-only offsets, not point offsets: points remain at their true rounded coordinates.
                    grouped = grouped.reset_index(drop=True)
                    grouped["Label precision"] = [
                        min(1.0, max(0.0, float(p) + 0.060 + (i % 3) * 0.030))
                        for i, p in enumerate(grouped["Precision_plot"])
                    ]

                    st.markdown(f"##### {threshold_label}")

                    base = alt.Chart(grouped).encode(
                        x=alt.X(
                            "Recall_plot:Q",
                            title="Recall",
                            scale=alt.Scale(domain=[0, 1]),
                        ),
                        y=alt.Y(
                            "Precision_plot:Q",
                            title="Precision",
                            scale=alt.Scale(domain=[0, 1]),
                        ),
                        tooltip=[
                            alt.Tooltip("Legend:N", title="Selection(s)"),
                            alt.Tooltip("Selection group:N", title="Merged rows"),
                            alt.Tooltip("N selections:Q", title="Rows merged", format=".0f"),
                            alt.Tooltip("Precision_plot:Q", title="Precision", format=".2f"),
                            alt.Tooltip("Recall_plot:Q", title="Recall", format=".2f"),
                            alt.Tooltip("F1_plot:Q", title="F1", format=".2f"),
                        ],
                    )

                    points = base.mark_circle(size=230, opacity=0.90).encode(
                        color=alt.Color(
                            "Point color:N",
                            title=None,
                            scale=None,
                            legend=None,
                        ),
                    )

                    labels = alt.Chart(grouped).mark_text(
                        align="center",
                        baseline="bottom",
                        fontSize=18,
                        fontWeight="bold",
                    ).encode(
                        x=alt.X("Recall_plot:Q", title="Recall", scale=alt.Scale(domain=[0, 1])),
                        y=alt.Y("Label precision:Q", title="Precision", scale=alt.Scale(domain=[0, 1])),
                        text="F1 label:N",
                        color=alt.value("black"),
                    )

                    legend_rows = grouped[["Legend", "Point color"]].drop_duplicates().reset_index(drop=True)
                    legend_rows["x"] = 0
                    legend_rows["y"] = legend_rows.index

                    legend_points = alt.Chart(legend_rows).mark_circle(size=90).encode(
                        x=alt.X("x:Q", axis=None),
                        y=alt.Y("y:Q", axis=None, sort=None),
                        color=alt.Color("Point color:N", scale=None, legend=None),
                    )

                    legend_text = alt.Chart(legend_rows).mark_text(
                        align="left",
                        baseline="middle",
                        dx=8,
                        fontSize=17,
                        fontWeight="bold",
                    ).encode(
                        x=alt.X("x:Q", axis=None),
                        y=alt.Y("y:Q", axis=None, sort=None),
                        text="Legend:N",
                    )

                    legend_chart = (
                        (legend_points + legend_text)
                        .properties(width=260, height=max(70, 34 * len(legend_rows)))
                    )

                    main_chart = (points + labels).properties(width=680, height=310)

                    combined_chart = (
                        alt.hconcat(main_chart, legend_chart, spacing=8)
                        .configure_axis(
                            grid=True,
                            titleFontWeight="bold",
                            titleFontSize=16,
                            labelFontSize=12,
                        )
                        .configure_view(strokeOpacity=0)
                    )

                    st.altair_chart(combined_chart, use_container_width=True)

                render_precision_recall_scatter("Stringent filter")
                render_precision_recall_scatter("Lenient filter")




# ===========================================================
# TAB 3 — DOCUMENTATION (split into sections + granular anchors)
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

> *"miR-RF: a database-independent machine-learning workflow and integrative evidence framework for systematic annotation of human microRNAs"*

This application enables dynamic interrogation and subsetting of human pre-miRNA based on:

- **Predicted structural stability**
- **Evolutionary conservation**
- **Tissue expression patterns**
- **Experimental-evidence validation level** from Kim *et al.* 2021, when enabled

Users can define flexible, multi-parameter filtering strategies tailored to specific biological questions, and export selected subsets for downstream analyses.
The app is designed to support both exploratory data analysis and hypothesis-driven investigation of human pre-miRNA candidates, along with their sequence.

---

### Overview

Human pre-miRNA are displayed in an interactive table featuring:

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

> *"miR-RF: a database-independent machine-learning workflow and integrative evidence framework for systematic annotation of human microRNAs"*

- **miR-RF structural stability classes** (R/D/I/S)
- **Multi-species conservation profiles**, including human specificity
- **Tissue expression values** (RPMM)
- **miRNA family context** (miRBase / MirGeneDB)
- **Repeat annotation**
- **miRBase high-confidence miRNA annotation**, when used in Filtering criteria
- **Experimental evidence validation level**, when enabled from the sidebar

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
This means that only pre-miRNA satisfying *all* active criteria will be displayed in the table.

Results update automatically whenever filter settings are modified.
"""
    )

    st.markdown('<div id="doc_filter_search_any" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(3, "global", "Search by name")
    st.markdown(
        """
Search for one or more miRNA/s across **all rows** of the table.

- Matching is **case-insensitive**.
- The search performs a **partial match**: rows are retained if any cell **contains** the input text.
- **Regular expressions (regex)** are supported for advanced queries (e.g. `^hsa-` to match entries starting with *hsa-let*).
"""
    )

    st.markdown('<div id="doc_filter_database" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(3, "database-main", "Database filter")
    st.markdown(
        """
Filter entries according to database/source annotation. The options are not mutually exclusive: selecting multiple sources retains miRNA/s matching **any** selected source.

- **All three selected** *(default)*: retain miRNA/s matching at least one selected source.
- **No selection**: no database/source is selected, so the table contains 0 rows.
- **miRBase-full**: retain miRNA/s present in the full miRBase-derived annotation set.
- **miRBase-HC**: retain miRNA/s with `High confidence miRNA = TRUE`.
- **MirGeneDB**: retain miRNA/s present in MirGeneDB.

Selections are combined with logical **OR** within this filter.
"""
    )

    st.markdown('<div id="doc_filter_conservation_pf" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(3, "cons1", "Conservation")
    st.markdown(
        """
The visible **Conservation** column reports the number of species with `TRUE` conservation support.

- `TRUE` values are counted.
- `FALSE` and `NA` values are not counted.
- The current default manuscript threshold is **at least 3 TRUE conserved species**.
"""
    )

    st.markdown('<div id="doc_filter_expression_pf" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(3, "tissue1", "Expression")
    st.markdown(
        """
The visible **Expression** column reports the number of tissues with expression above the selected/default RPMM threshold.

- The default expression threshold is **RPMM ≥ 1.5**.
- The default minimum number of expressed tissues is **1**.
- Tissue-level values can be shown from **Advanced options → Tissue expression**.
"""
    )

    st.markdown('<div id="doc_filter_structure_pf" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(3, "structure", "Structural Classification Filter (miRBase / MirGeneDB)")
    st.markdown(
        """
Keep or exclude human pre-miRNA according to their **structural classification** in miRBase or MirGeneDB.

- **Show all** *(default)*: no filter applied.
- **PASSED**: pre-miRNA classified as **R** or **D** (structurally robust).
- **NOT PASSED**: pre-miRNA classified as **I** or **S** (structurally unstable or weakly supported).
"""
    )

    st.markdown('<div id="doc_filter_hsa" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(3, "hsa", "hsa specificity")
    st.markdown(
        """
Filter human-specific or non human-specific pre-miRNA.

- **Show all**: no filter applied.
- **Only hsa-specific**: retain only pre-miRNA annotated as human-specific.
- **Not hsa-specific**: exclude human-specific premiRNA/s and retain all other entries.
"""
    )

    st.markdown('<div id="doc_filter_family" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(3, "fam", "miRNA Family Membership")
    st.markdown(
        """
Filter pre-miRNA based on family annotations from **miRBase** and/or **MirGeneDB**.

- **no family**: pre-miRNA not assigned to any family in the selected databases.
- **miRNA/s in family**: pre-miRNA annotated as belonging to a family (the family name is displayed when available).
"""
    )

    st.markdown('<div id="doc_filter_repeat" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(3, "rep", "Repeat class")
    st.markdown(
        """
Filter miRNA/s based on the presence and type of **overlapping repeat elements**.

- Select one or more repeat classes (e.g. **LINE**, **SINE**, **LTR**, **DNA repeats**, **Low complexity repeats**).
- If multiple classes are selected, miRNA/s overlapping **any** of the chosen categories are retained (logical OR).
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
Use **Reset all filters** to clear selections and restore the initial app state.

- The button is shown only when at least one filter or display option is active.
- It resets main filters, advanced options, filtering criteria, pagination, and applied filtering-criteria state.
"""
    )

    st.markdown("---")

    # -----------------------------
    # Sensitivity analysis
    # -----------------------------
    st.markdown('<div id="doc_filtering_criteria" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(2, "adv2", "Filtering criteria")
    st.markdown(
        """
The **Filtering criteria** page is an expert page designed to evaluate how the retained catalog size changes under alternative analytical choices.

**What the page uses**

- The main **App** page opens on the default manuscript catalog (`Default = yes`).
- The **Filtering criteria** page uses the complete candidate table, so it can test rows outside the default catalog.

**Criteria that can be changed**

- **Evolutionary conservation**: minimum number of species with `TRUE` conservation support.
- **Tissue Expression**: RPMM threshold and minimum number of expressed tissues.
- **Structural class**: classes considered passing (`R`, `D`, `I`, `S`) and optional miRBase high-confidence restriction.

**Rules that can be compared**

- **At least 2 of 3 criteria**: retained if at least two criteria pass.
- **All 3 criteria**: retained only if conservation, expression and structural class all pass.
- **Stable structural class + at least one other criterion**: retained if structural class is stable and at least one other criterion passes.

The page reports the retained count and marks the selected rule in the criteria-combination summary. The main table changes only after selecting **Apply filtering criteria to main table**.
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
    """
    Enable **Advanced options** in the sidebar to unlock additional controls and column display options.
    
    **Important:**
    - **Show columns** only determines which columns are visible in the table. It does *not* filter the dataset.  
    - **Filter** options instead restrict the rows of the dataset based on the selected criteria.
    
    Users should apply row filters appropriately to ensure that the displayed columns correspond to the context of interest.
    """,
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
    doc_heading(3, "database", "Structural class (advanced)")
    st.markdown("""
- **Show Structural class columns** displays the miRBase and MirGeneDB structural class annotations.  
- **Structural class filter** retains rows where either miRBase or MirGeneDB has one of the selected classes (`R`, `D`, `I`, `S`).  
- Missing MirGeneDB class values are displayed as `NA`.  
""")

    st.markdown('<div id="doc_adv_confidence_evidence" class="doc-anchor"></div>', unsafe_allow_html=True)
    doc_heading(3, "adv", "Experimental evidence")
    st.markdown("""
- The sidebar control “Show Experimental evidence (Kim et al. 2021)” displays the experimental-evidence validation column in the main table.  
- The table uses color only for validation levels; missing values are shown as `NA`.  
- **Experimental evidence filter**: retain miRNA/s by validation level: **Pass stringent filter**, **Pass lenient filter**, or **No pass**.  
- The `Experimental evidence` annotation was processed from the experimental validation data reported by Kim *et al.* in **A quantitative map of human primary microRNA processing sites** (PMID: **34320405**), using **Supplementary Table S6** as the starting table.  
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
        f"### {doc_icon_html('mouseCuore')}Use case 1 - Cardiovascular-associated miRNA/s conserved in mouse",
        unsafe_allow_html=True
    )

    st.markdown(
        """
    This use case focuses on human pre-miRNA conserved in *Mus musculus*, structurally robust, and expressed in cardiovascular-related tissues and fluids.

    **Conservation support**
    - In **Advanced options -> Evolutionary conservation**, select *M. musculus* under **Found in**.  
        This restricts the table to pre-miRNA with detectable conservation in mouse.
    - In **Advanced options -> Evolutionary conservation**, select **Stable (R/D)** under **Structure**.

    **Tissue expression context**
    - In **Advanced options -> Tissue expression**, select tissues belonging to the **Cardiorespiratory** system (heart and lung), under "Show extra columns". 
    - In **Advanced options -> Tissue expression**, select tissues under **Expressed in (select tissues by system):** all cardiovascular-related tissues and fluids. 

    Under these conditions, **99 miRNA/s** are retained. For each entry, the app enables inspection of whether the miRNA:
    - is conserved in mouse;
    - displays expression across multiple cardiovascular tissues;
    - is classified as structurally stable (R or D).
    
    """,
        unsafe_allow_html=True
    )

    # ---- Use case 2 (TITLE WITH ICON) ----
    st.markdown(
        f"### {doc_icon_html('scimmiaBrain')}miRNA/s conserved in Great apes (human and Pan) and expressed in brain",
        unsafe_allow_html=True
    )

    st.markdown(
        """
    This use case identifies human pre-miRNA that are conserved in *Pan troglodytes* and *Pan paniscus* and show expression in neural tissues.

    **Conservation support**
    - In **Advanced options -> Evolutionary conservation**, select *P. troglodytes*, *P. paniscus*, *M. mulatta* and *L. catta* under **Show extra columns**.
    - In **Advanced options -> Evolutionary conservation**, select *P. troglodytes* and *P. paniscus* under **Found in**.
    - In **Advanced options -> Evolutionary conservation**, select **Stable (R/D)** under **Structure**.
    - In **Advanced options -> Evolutionary conservation**, select *M. mulatta* and *L. catta* under **Not found in**.

    **Tissue expression context**
    - In **Advanced options → Tissue expression**, select tissues belonging to the **Neuro-Endocrine system** (brain and cerebellum), under "Show extra columns".  
      This option displays the corresponding tissue expression columns but does not filter the results.

    Under these conditions, **29 miRNA/s** are retained. For each entry, the app enables inspection of whether the miRNA:
    - is conserved in *Pan troglodytes* and *Pan paniscus*;
    - not conserved in *Macaca mulatta* and *Lemur catta*;
    - is classified as structurally stable (R or D);
    - displays expression across neuro-endocrine tissues.
      
    """,
        unsafe_allow_html=True
    )

    st.markdown("---")
    st.markdown("License: CC BY 4.0")














