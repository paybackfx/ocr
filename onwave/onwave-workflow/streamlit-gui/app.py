import streamlit as st
import requests
import json
import fitz # PyMuPDF
import base64
import io
from PIL import Image

# ==========================================
# CONFIG
# ==========================================
WEBHOOK_URL = "http://n8n:5678/webhook/insurance-ocr-openrouter"
MAX_FILES = 6
ACCEPTED_EXTENSIONS = ["jpg", "jpeg", "png", "pdf"]

# ==========================================
# PAGE CONFIG
# ==========================================
st.set_page_config(
    page_title="Imtiaz Taamine — OCR Intelligent",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# CUSTOM CSS — IMTIAZ TAAMINE BRAND
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    * { font-family: 'Inter', sans-serif; box-sizing: border-box; }

    /* === BACKGROUND === */
    .stApp, .main {
        background: #0a1628 !important;
    }

    /* === HIDE STREAMLIT DECORATIONS === */
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 1.5rem !important; }

    /* === TOP HEADER BAR === */
    .it-header {
        background: linear-gradient(135deg, #0d1f45 0%, #122055 100%);
        border-bottom: 3px solid #E91E8C;
        padding: 1.2rem 2rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-radius: 0 0 16px 16px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 30px rgba(233, 30, 140, 0.2);
    }

    .it-logo-group {
        display: flex;
        align-items: center;
        gap: 1.2rem;
    }

    .it-logo-squares {
        display: flex;
        gap: 0;
        width: 40px;
        height: 40px;
        position: relative;
    }

    .it-brand-name {
        font-size: 1.5rem;
        font-weight: 800;
        color: white;
        letter-spacing: 0.08em;
        line-height: 1;
    }

    .it-brand-sub {
        font-size: 0.75rem;
        font-weight: 400;
        color: #5BC8F5;
        letter-spacing: 0.15em;
        text-transform: uppercase;
    }

    .it-badge {
        background: linear-gradient(135deg, #E91E8C, #c0186c);
        color: white;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.05em;
    }

    /* === SECTION TITLE === */
    .it-section-title {
        color: white;
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* === UPLOAD ZONE === */
    [data-testid="stFileUploader"] {
        border: 2px dashed rgba(91, 200, 245, 0.4) !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        background: rgba(13, 31, 69, 0.6) !important;
        transition: all 0.3s ease !important;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: #5BC8F5 !important;
        background: rgba(13, 31, 69, 0.9) !important;
    }
    [data-testid="stFileUploader"] label {
        color: #94a8c7 !important;
    }

    /* === ANALYZE BUTTON (primary only) === */
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #E91E8C 0%, #c0186c 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.8rem 2.5rem !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        letter-spacing: 0.04em !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
        text-transform: uppercase !important;
        box-shadow: 0 4px 20px rgba(233, 30, 140, 0.4) !important;
    }
    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="baseButton-primary"]:hover {
        background: linear-gradient(135deg, #ff2fa0 0%, #E91E8C 100%) !important;
        box-shadow: 0 6px 30px rgba(233, 30, 140, 0.6) !important;
        transform: translateY(-2px) !important;
    }

    /* === DEFAULT SECONDARY BUTTONS === */
    .stButton > button[kind="secondary"],
    .stButton > button[data-testid="baseButton-secondary"] {
        background: rgba(46, 59, 78, 0.8) !important;
        color: #94a8c7 !important;
        border: 1px solid rgba(91, 200, 245, 0.2) !important;
        border-radius: 10px !important;
        padding: 0.5rem 1.2rem !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        transition: all 0.2s ease !important;
        box-shadow: none !important;
    }
    .stButton > button[kind="secondary"]:hover,
    .stButton > button[data-testid="baseButton-secondary"]:hover {
        background: rgba(233, 30, 140, 0.5) !important;
        color: white !important;
        border-color: #E91E8C !important;
        transform: none !important;
        box-shadow: 0 0 12px rgba(233, 30, 140, 0.3) !important;
    }

    /* === FILE BADGES === */
    .it-file-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        background: rgba(91, 200, 245, 0.1);
        border: 1px solid rgba(91, 200, 245, 0.3);
        color: #5BC8F5;
        border-radius: 8px;
        padding: 0.3rem 0.8rem;
        font-size: 0.8rem;
        font-weight: 500;
        margin: 0.25rem;
    }

    /* === RESULT CARDS === */
    .it-card {
        background: linear-gradient(135deg, #0d1f45 0%, #122055 100%);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 0.75rem 0;
        border-top: 3px solid transparent;
        box-shadow: 0 4px 24px rgba(0,0,0,0.3);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .it-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    }
    .it-card.cg   { border-top-color: #5BC8F5; }
    .it-card.cin  { border-top-color: #8DC63F; }
    .it-card.pc   { border-top-color: #E91E8C; }

    .it-card-title {
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 1.2rem;
        display: flex;
        align-items: center;
        gap: 0.6rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .it-card-title.cg  { color: #5BC8F5; }
    .it-card-title.cin { color: #8DC63F; }
    .it-card-title.pc  { color: #E91E8C; }

    .it-field {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.55rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    .it-field:last-child { border-bottom: none; }

    .it-label {
        color: #7a94b8;
        font-size: 0.8rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .it-value {
        color: #e8f0ff;
        font-size: 0.9rem;
        font-weight: 600;
        text-align: right;
        max-width: 60%;
    }
    .it-value.highlight {
        color: #5BC8F5;
        font-size: 1rem;
        font-weight: 700;
    }
    .it-value.green { color: #8DC63F; }
    .it-value.pink  { color: #E91E8C; }

    /* === BANNERS === */
    .it-success {
        background: rgba(141, 198, 63, 0.1);
        border: 1px solid rgba(141, 198, 63, 0.4);
        color: #8DC63F;
        border-radius: 12px;
        padding: 0.9rem 1.5rem;
        text-align: center;
        font-weight: 600;
        font-size: 0.95rem;
        margin: 1rem 0;
    }
    .it-error {
        background: rgba(233, 30, 140, 0.1);
        border: 1px solid rgba(233, 30, 140, 0.4);
        color: #E91E8C;
        border-radius: 12px;
        padding: 0.9rem 1.5rem;
        text-align: center;
        font-weight: 600;
        font-size: 0.95rem;
        margin: 1rem 0;
    }

    /* === METRICS === */
    [data-testid="stMetric"] {
        background: rgba(13, 31, 69, 0.8);
        border: 1px solid rgba(91, 200, 245, 0.15);
        border-radius: 12px;
        padding: 1rem;
    }
    [data-testid="stMetric"] label { color: #7a94b8 !important; font-size: 0.8rem !important; }
    [data-testid="stMetricValue"] { color: white !important; font-weight: 700 !important; }

    /* === FOOTER === */
    .it-footer {
        text-align: center;
        color: #3a5070;
        font-size: 0.78rem;
        padding: 2rem 0 1rem;
        letter-spacing: 0.05em;
    }

    /* === PDF24-STYLE PAGE CARDS — FIXED SIZE === */
    .page-card {
        background: #1a2234;
        border: 2px solid #2e3b4e;
        border-radius: 10px;
        width: 180px;
        height: 180px;
        margin: 0 auto;
        position: relative;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .page-card.selected {
        border-color: #E91E8C !important;
        box-shadow: 0 0 16px rgba(233, 30, 140, 0.4);
    }
    .page-card-wrap {
        text-align: center;
    }
    .page-card .page-badge {
        position: absolute;
        top: 4px;
        right: 6px;
        background: rgba(0,0,0,0.6);
        color: #fff;
        font-size: 10px;
        font-weight: 700;
        border-radius: 4px;
        padding: 2px 6px;
        z-index: 2;
    }
    .page-card .select-badge {
        position: absolute;
        top: 4px;
        left: 6px;
        background: #E91E8C;
        color: #fff;
        font-size: 10px;
        font-weight: 700;
        border-radius: 4px;
        padding: 2px 6px;
        z-index: 2;
    }
    .page-card img {
        max-height: 100%;
        max-width: 100%;
        display: block;
        object-fit: contain;
        transition: transform 0.35s ease;
    }
    /* === BUTTONS ROW UNDER CARD === */
    .page-btns-row {
        margin-top: -1.5rem !important;
    }
    .page-btns-row [data-testid="column"] {
        padding: 0 2px !important;
    }
    .page-btns-row .stButton > button {
        min-height: 0 !important;
        height: 26px !important;
        width: 26px !important;
        padding: 0 !important;
        font-size: 12px !important;
        line-height: 1 !important;
        border-radius: 5px !important;
    }


    /* === DIVIDER === */
    hr { border-color: rgba(91, 200, 245, 0.1) !important; margin: 1.5rem 0 !important; }

    /* === CODE FIELD COPY BUTTON — INLINE AFTER TEXT === */
    [data-testid="stCode"] {
        position: relative !important;
    }
    [data-testid="stCode"] > div {
        display: flex !important;
        align-items: center !important;
    }
    [data-testid="stCode"] pre {
        flex: 0 1 auto !important;
        overflow: visible !important;
    }
    [data-testid="stCode"] button {
        position: static !important;
        flex-shrink: 0 !important;
        opacity: 0.5 !important;
        margin-left: 4px !important;
    }
    [data-testid="stCode"] button:hover {
        opacity: 1 !important;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# HEADER
# ==========================================
st.markdown("""
<div class="it-header">
    <div class="it-logo-group">
        <svg width="44" height="44" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="0" y="20" width="44" height="44" fill="#E91E8C" rx="4"/>
          <rect x="36" y="0" width="44" height="44" fill="#5BC8F5" rx="4"/>
          <rect x="18" y="55" width="28" height="28" fill="#8DC63F" rx="4"/>
        </svg>
        <div>
            <div class="it-brand-name">IMTIAZ TAAMINE</div>
            <div class="it-brand-sub">Extraction Intelligente de Documents</div>
        </div>
    </div>
    <div class="it-badge">🦅 OCR Propulsé par IA</div>
</div>
""", unsafe_allow_html=True)


# ==========================================
# HELPER FUNCTIONS
# ==========================================
def render_card(title: str, icon: str, css_class: str, data: dict):
    if not data or all(v in ("", "-", None) for v in data.values()):
        return

    labels_fr = {
        "immatriculation":              "Immatriculation",
        "numero_chassis":               "N° Châssis",
        "date_1ere_mise_en_circulation": "Date 1ère MRC",
        "marque":                       "Marque",
        "modele":                       "Modèle",
        "puissance_fiscale":            "Puissance Fiscale",
        "type_carburant":               "Carburant",
        "proprietaire":                 "Propriétaire",
        "nombre_places":                "Nb. Places",
        "ptac":                         "PTAC",
        "numero_cin":                   "N° CIN",
        "nom":                          "Nom",
        "prenom":                       "Prénom",
        "date_naissance":               "Date de Naissance",
        "adresse":                      "Adresse",
        "date_expiration":              "Date d'Expiration",
        "numero_permis":                "N° Permis",
        "categories":                   "Catégories",
        "date_fin_validite":            "Date Fin Validité",
        "nom_complet":                  "Nom Complet",
    }

    highlight_keys = {"immatriculation", "numero_cin", "numero_permis", "numero_chassis"}
    color_map = {"cg": "#5BC8F5", "cin": "#8DC63F", "pc": "#E91E8C"}
    accent = color_map.get(css_class, "#5BC8F5")

    # Card header
    st.markdown(f"""
    <div class="it-card {css_class}">
        <div class="it-card-title {css_class}">{icon} {title}</div>
    </div>
    """, unsafe_allow_html=True)

    # Fields using native Streamlit
    for key, value in data.items():
        if not value or value == "" or value is None:
            continue
        label = labels_fr.get(key, key.replace("_", " ").title())
        col_l, col_r = st.columns([1, 1.5])
        with col_l:
            st.markdown(f'<p style="color:#7a94b8;font-size:0.78rem;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin:0;padding:4px 0">{label}</p>', unsafe_allow_html=True)
        with col_r:
            color = accent if key in highlight_keys else "#e8f0ff"
            weight = "700" if key in highlight_keys else "500"
            st.markdown(f'<p style="color:{color};font-size:0.9rem;font-weight:{weight};text-align:right;margin:0;padding:4px 0">{value}</p>', unsafe_allow_html=True)
        st.markdown('<hr style="border:none;border-top:1px solid rgba(255,255,255,0.05);margin:0"/>', unsafe_allow_html=True)
    st.markdown("")


def send_to_webhook(files):
    multipart_files = [(("data"), (f.name, f.getvalue(), f.type)) for f in files]
    response = requests.post(WEBHOOK_URL, files=multipart_files, timeout=120)
    response.raise_for_status()
    return response.json()


# ==========================================
# UPLOAD SECTION
# ==========================================
st.markdown('<div class="it-section-title">📎 Importation des Documents</div>', unsafe_allow_html=True)
st.markdown('<p style="color:#5a7498; font-size:0.85rem; margin-bottom:1rem;">Glissez vos documents d\'assurance (CIN recto/verso, Carte Grise recto/verso, Permis). Maximum 6 fichiers.</p>', unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "📂 Déposez vos fichiers ici — JPG, PNG, PDF",
    type=ACCEPTED_EXTENSIONS,
    accept_multiple_files=True,
    help="Accepte JPG, PNG et PDF. Max 6 fichiers.",
    label_visibility="collapsed"
)

if uploaded_files:
    if len(uploaded_files) > MAX_FILES:
        st.markdown(f'<div class="it-error">⚠️ Maximum {MAX_FILES} fichiers autorisés. Vous en avez sélectionné {len(uploaded_files)}.</div>', unsafe_allow_html=True)
    else:
        badges = "".join([
            f'<span class="it-file-badge">📄 {f.name} <span style="opacity:0.6">({len(f.getvalue())//1024} KB)</span></span>'
            for f in uploaded_files
        ])
        st.markdown(f'<div style="margin:0.75rem 0 1.25rem">{badges}</div>', unsafe_allow_html=True)

        if st.button(f"🔍 Analyser {len(uploaded_files)} document{'s' if len(uploaded_files) > 1 else ''}", type="primary"):
            with st.spinner("🔄 Extraction en cours — Analyse IA des documents..."):
                try:
                    st.session_state["results_list"] = send_to_webhook(uploaded_files)
                    st.session_state["pdf_bytes"] = None # Reset
                    st.session_state.pop("page_rotations", None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur d'analyse: {str(e)}")

# ==========================================
# RESULTS DISPLAY (outside uploaded_files block so it survives rerun)
# ==========================================
if "results_list" in st.session_state and st.session_state["results_list"]:
    try:
        results_list = st.session_state["results_list"]

        if not isinstance(results_list, list):
            results_list = [results_list]

        first_res = results_list[0] if results_list else {}

        if first_res.get("success") is False:
            error_msg = first_res.get("error", "Erreur inconnue")
            st.markdown(f'<div class="it-error">❌ {error_msg}</div>', unsafe_allow_html=True)
            if first_res.get("raw"):
                with st.expander("Réponse brute"):
                    st.code(json.dumps(first_res.get("raw"), indent=2, ensure_ascii=False))
        else:
            st.markdown('<div class="it-success">✅ Extraction terminée avec succès !</div>', unsafe_allow_html=True)

            filenames = first_res.get("filenames", ["N/A"])

            # Metrics
            c1, c2 = st.columns(2)
            with c1: st.metric("📁 Fichiers analysés", len(filenames))
            with c2: st.metric("📑 Documents trouvés", len(results_list))

            # PDF Download (from first item since OpenCV generated it once)
            output_pdf = first_res.get("output_pdf", "")
            debug_pdf = first_res.get("debug_pdf", "")

            if output_pdf:
                if "pdf_bytes" not in st.session_state or not st.session_state.get("pdf_bytes"):
                    st.session_state["pdf_bytes"] = base64.b64decode(output_pdf)

                # --- INTERACTIVE GALLERY (Native Streamlit) ---
                st.markdown("---")
                st.markdown('<div class="it-section-title">🔄 Aperçu et Correction de Rotation</div>', unsafe_allow_html=True)

                pdf_doc = fitz.open(stream=st.session_state["pdf_bytes"], filetype="pdf")
                n_pages = len(pdf_doc)

                # Initialize rotation state per page
                if "page_rotations" not in st.session_state:
                    st.session_state["page_rotations"] = [0] * n_pages
                elif len(st.session_state["page_rotations"]) != n_pages:
                    st.session_state["page_rotations"] = [0] * n_pages

                # Initialize selection state per page
                if "page_selections" not in st.session_state:
                    st.session_state["page_selections"] = [False] * n_pages
                elif len(st.session_state["page_selections"]) != n_pages:
                    st.session_state["page_selections"] = [False] * n_pages

                # Global rotation buttons
                def rotate_all(direction):
                    st.session_state["page_rotations"] = [(r + direction) % 360 for r in st.session_state["page_rotations"]]

                gcol1, gcol2, gcol3 = st.columns([1, 1, 1])
                with gcol2:
                    bcol1, bcol2 = st.columns(2)
                    with bcol1:
                        st.button("↺", key="rot_all_ccw", help="Rotation antihoraire (toutes les pages)", use_container_width=True, on_click=rotate_all, args=(-90,))
                    with bcol2:
                        st.button("↻", key="rot_all_cw", help="Rotation horaire (toutes les pages)", use_container_width=True, on_click=rotate_all, args=(90,))

                st.markdown("<p style='text-align:center;color:#7a94b8;font-size:0.85rem;margin:0.25rem 0 1rem'>... ou cliquer directement sur une page pour la faire pivoter</p>", unsafe_allow_html=True)
                st.markdown('<hr style="border:none;border-top:1px solid rgba(91,200,245,0.1);margin:0 0 1.5rem"/>', unsafe_allow_html=True)

                # Render pages as a gallery grid (small, uniform size)
                cols_per_row = min(n_pages, 4)
                for row_start in range(0, n_pages, cols_per_row):
                    row_pages = list(range(row_start, min(row_start + cols_per_row, n_pages)))
                    cols = st.columns(cols_per_row)
                    for col_idx, page_idx in enumerate(row_pages):
                        with cols[col_idx]:
                            page = pdf_doc[page_idx]
                            rot = st.session_state["page_rotations"][page_idx]
                            is_selected = st.session_state["page_selections"][page_idx]
                            pix = page.get_pixmap(dpi=100)
                            img_bytes = pix.tobytes("png")
                            img_b64 = base64.b64encode(img_bytes).decode()

                            # Compute scale so rotated image fits inside fixed card
                            iw, ih = pix.width, pix.height
                            if rot in (90, 270) and iw != ih:
                                scale = min(iw, ih) / max(iw, ih)
                                img_transform = f"transform:rotate({rot}deg) scale({scale:.3f});"
                            elif rot:
                                img_transform = f"transform:rotate({rot}deg);"
                            else:
                                img_transform = ""

                            selected_css = " selected" if is_selected else ""
                            select_badge = '<span class="select-badge">✓</span>' if is_selected else ""
                            st.markdown(
                                f'<div class="page-card-wrap">'
                                f'<div class="page-card{selected_css}">'
                                f'{select_badge}'
                                f'<span class="page-badge">{page_idx + 1}</span>'
                                f'<img src="data:image/png;base64,{img_b64}" style="{img_transform}"/>'
                                f'</div></div>',
                                unsafe_allow_html=True
                            )
                            def rotate_page(idx):
                                st.session_state["page_rotations"][idx] = (st.session_state["page_rotations"][idx] + 90) % 360

                            def toggle_select(idx):
                                st.session_state["page_selections"][idx] = not st.session_state["page_selections"][idx]

                            # Tiny buttons under image — centered and tight
                            sel_label = "✓" if is_selected else "☐"
                            spacer1, btn1, btn2, spacer2 = st.columns([0.8, 0.05, 0.05, 1.1], gap="small")
                            with btn1:
                                st.markdown('<div class="page-btns-row">', unsafe_allow_html=True)
                                st.button("↻", key=f"rot_page_{page_idx}", on_click=rotate_page, args=(page_idx,))
                                st.markdown('</div>', unsafe_allow_html=True)
                            with btn2:
                                st.markdown('<div class="page-btns-row">', unsafe_allow_html=True)
                                st.button(sel_label, key=f"sel_page_{page_idx}", on_click=toggle_select, args=(page_idx,))
                                st.markdown('</div>', unsafe_allow_html=True)

                # Merge section
                selected_indices = [i for i, s in enumerate(st.session_state["page_selections"]) if s]
                if len(selected_indices) >= 2:
                    st.markdown('<hr style="border:none;border-top:1px solid rgba(91,200,245,0.1);margin:1rem 0"/>', unsafe_allow_html=True)
                    st.markdown(f'<p style="text-align:center;color:#E91E8C;font-size:0.9rem;font-weight:600;margin:0.5rem 0">🔗 {len(selected_indices)} pages sélectionnées (pages {", ".join(str(i+1) for i in selected_indices)})</p>', unsafe_allow_html=True)

                    _, merge_col, _ = st.columns([1, 2, 1])
                    with merge_col:
                        if st.button("🔗 Fusionner les pages sélectionnées", key="merge_pages", type="primary", use_container_width=True):
                            # Merge selected pages into one tall image
                            images = []
                            for idx in selected_indices:
                                pg = pdf_doc[idx]
                                rot = st.session_state["page_rotations"][idx]
                                pix = pg.get_pixmap(dpi=300)
                                img = Image.open(io.BytesIO(pix.tobytes("png")))
                                if rot:
                                    img = img.rotate(-rot, expand=True)
                                images.append(img)

                            # Stack vertically: uniform width, concatenated height
                            max_w = max(img.width for img in images)
                            resized = []
                            for img in images:
                                if img.width != max_w:
                                    ratio = max_w / img.width
                                    img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
                                resized.append(img)

                            total_h = sum(img.height for img in resized)
                            merged = Image.new("RGB", (max_w, total_h), (255, 255, 255))
                            y_offset = 0
                            for img in resized:
                                merged.paste(img, (0, y_offset))
                                y_offset += img.height

                            # Build a new PDF: merged page replaces first selected, remove others
                            new_doc = fitz.open(stream=st.session_state["pdf_bytes"], filetype="pdf")
                            # Convert merged image to PDF page
                            img_buffer = io.BytesIO()
                            merged.save(img_buffer, format="PNG")
                            img_buffer.seek(0)

                            # Insert merged image as a new page at the position of the first selected page
                            insert_pos = selected_indices[0]
                            img_rect = fitz.Rect(0, 0, merged.width * 72 / 300, merged.height * 72 / 300)
                            new_page = new_doc.new_page(pno=insert_pos, width=img_rect.width, height=img_rect.height)
                            new_page.insert_image(img_rect, stream=img_buffer.read())

                            # Delete original selected pages (shifted by 1 because we inserted one)
                            pages_to_delete = sorted([i + 1 if i >= insert_pos else i for i in selected_indices], reverse=True)
                            for p in pages_to_delete:
                                new_doc.delete_page(p)

                            st.session_state["pdf_bytes"] = new_doc.tobytes()
                            new_doc.close()

                            # Reset selections and rotations for new page count
                            new_n = fitz.open(stream=st.session_state["pdf_bytes"], filetype="pdf").page_count
                            st.session_state["page_rotations"] = [0] * new_n
                            st.session_state["page_selections"] = [False] * new_n
                            st.rerun()

            if output_pdf or debug_pdf:
                st.markdown("---")
                st.markdown('<div class="it-section-title">📥 Documents Générés</div>', unsafe_allow_html=True)

                col_pdf1, col_pdf2 = st.columns(2)

                def apply_rotations_to_pdf(raw_bytes):
                    """Apply user rotations to a PDF and return new bytes."""
                    rotations = st.session_state.get("page_rotations", [])
                    if not any(r != 0 for r in rotations):
                        return raw_bytes  # No rotation needed
                    doc = fitz.open(stream=raw_bytes, filetype="pdf")
                    for i, rot in enumerate(rotations):
                        if i < len(doc) and rot != 0:
                            doc[i].set_rotation((doc[i].rotation + rot) % 360)
                    out = doc.tobytes()
                    doc.close()
                    return out

                if output_pdf:
                    pdf_bytes = st.session_state.get("pdf_bytes", base64.b64decode(output_pdf))
                    rotated_pdf = apply_rotations_to_pdf(pdf_bytes)
                    with col_pdf1:
                        st.download_button(
                            label="👁️ Télécharger PDF Client (Crop Clean)",
                            data=rotated_pdf,
                            file_name="document_client.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            help="Image claire et redressée, idéale pour le dossier client."
                        )

                if debug_pdf:
                    debug_bytes = base64.b64decode(debug_pdf)
                    rotated_debug = apply_rotations_to_pdf(debug_bytes)
                    with col_pdf2:
                        st.download_button(
                            label="🔍 Télécharger PDF Debug (Filtres IA)",
                            data=rotated_debug,
                            file_name="document_debug_llm.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            help="Image avec les filtres OpenCV (ce que l'IA a réellement analysé)."
                        )

            st.markdown("---")

            for item_idx, res_item in enumerate(results_list):
                extracted = res_item.get("extracted_data", res_item)
                if isinstance(extracted, list) and len(extracted) > 0:
                    extracted = extracted[0]
                elif isinstance(extracted, list):
                    extracted = {}

                # Check if extracted actually has any data
                has_data = any(isinstance(v, dict) and any(val not in ("", None, "NULL", "null", "-") for val in v.values()) for v in extracted.values())

                if has_data:
                    doc_title = f"📋 Document {item_idx + 1}" if len(results_list) > 1 else "📋 Données JSON complètes"
                    with st.expander(f"{doc_title} — clic sur la valeur pour copier", expanded=True):
                        section_icons = {"carte_grise": "🚗", "cin": "🪪", "permis_conduire": "🚦"}
                        section_colors = {"carte_grise": "#5BC8F5", "cin": "#8DC63F", "permis_conduire": "#E91E8C"}
                        labels_map = {
                            "immatriculation": "Immatriculation", "numero_chassis": "N° Châssis",
                            "date_1ere_mise_en_circulation": "Date 1ère MRC", "marque": "Marque",
                            "modele": "Modèle", "puissance_fiscale": "Puissance Fiscale",
                            "type_carburant": "Carburant", "proprietaire": "Propriétaire",
                            "nombre_places": "Nb. Places", "ptac": "PTAC",
                            "numero_cin": "N° CIN", "nom": "Nom", "prenom": "Prénom",
                            "date_naissance": "Date de Naissance", "adresse": "Adresse",
                            "date_expiration": "Date d'Expiration", "numero_permis": "N° Permis",
                            "categories": "Catégories", "date_fin_validite": "Date Fin Validité",
                            "nom_complet": "Nom Complet",
                        }
                        for section, fields in extracted.items():
                            if section.lower() in ("orientation", "orientation_per_image", "orientations", "metadata"):
                                continue
                            if isinstance(fields, dict) and any(v not in ("", None, "NULL", "null", "-") for v in fields.values()):
                                icon = section_icons.get(section, "📄")
                                color = section_colors.get(section, "#5BC8F5")
                                title = section.replace("_", " ").title()
                                st.markdown(f'<p style="color:{color};font-weight:700;font-size:0.95rem;margin:1rem 0 0.4rem;text-transform:uppercase;letter-spacing:0.08em">{icon} {title}</p>', unsafe_allow_html=True)
                                for key, value in fields.items():
                                    label = labels_map.get(key, key.replace("_", " ").title())
                                    col_l, col_r = st.columns([1, 2])
                                    with col_l:
                                        st.markdown(f'<p style="color:#7a94b8;font-size:0.78rem;font-weight:600;text-transform:uppercase;margin:0;padding:6px 0">{label}</p>', unsafe_allow_html=True)
                                    with col_r:
                                        if value and value not in ("", None, "NULL", "null", "-"):
                                            st.code(str(value), language=None)
                                        else:
                                            st.markdown('<p style="color:#E91E8C;font-weight:600;font-size:0.85rem;padding:6px 0;margin:0">NULL</p>', unsafe_allow_html=True)

                txt = res_item.get("txt_report")
                if txt:
                    txt_title = f"📝 Rapport texte (Doc {item_idx + 1})" if len(results_list) > 1 else "📝 Rapport texte"
                    with st.expander(txt_title):
                        st.code(txt, language="text")

    except requests.exceptions.Timeout:
        st.markdown('<div class="it-error">⏱️ Le serveur met trop de temps à répondre. Réessayez avec moins de fichiers.</div>', unsafe_allow_html=True)
    except requests.exceptions.ConnectionError:
        st.markdown('<div class="it-error">🔌 Impossible de joindre le serveur. Vérifiez que Docker est lancé.</div>', unsafe_allow_html=True)
    except Exception as e:
        st.markdown(f'<div class="it-error">❌ Erreur inattendue : {str(e)}</div>', unsafe_allow_html=True)

# ==========================================
# FOOTER
# ==========================================
st.markdown("---")
st.markdown("""
<div class="it-footer">
    🦅 <strong>IMTIAZ TAAMINE</strong> &nbsp;|&nbsp; Plateforme OCR Intelligente &nbsp;|&nbsp;
    CIN &bull; Carte Grise &bull; Permis de Conduire<br>
    Propulsé par Google Gemini Vision &bull; OpenCV &bull; n8n
</div>
""", unsafe_allow_html=True)
