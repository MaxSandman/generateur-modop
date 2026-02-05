import streamlit as st
import google.generativeai as genai
import cv2
import os
import tempfile
from docx import Document
from fpdf import FPDF

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Modop Studio by Nomadia",
    page_icon="🛰️",
    layout="wide"
)

# --- STYLE CSS (100% THÈME CLAIR & NOMADIA) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    /* Global - Fond clair */
    .stApp {
        background-color: #FFFFFF;
        color: #002344;
        font-family: 'Inter', sans-serif;
    }

    /* Barre latérale - Bleu Marine Professionnel */
    [data-testid="stSidebar"] {
        background-color: #002344;
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }

    /* Titres */
    h1, h2, h3 {
        color: #002344 !important;
        font-weight: 700 !important;
    }

    /* Bouton principal (Vert Nomadia) */
    .stButton>button {
        background: #00D2B4;
        color: white !important;
        border-radius: 8px;
        border: none;
        font-weight: 600;
        padding: 0.6rem 1.5rem;
        transition: 0.3s;
    }
    
    .stButton>button:hover {
        background-color: #00B5A0;
        border: none;
        color: white !important;
    }

    /* Zone de texte (Le rendu du Modop) */
    .output-box {
        background-color: #F8FAFC;
        padding: 25px;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        color: #002344;
        font-size: 15px;
    }

    /* Input et Uploader */
    .stFileUploader {
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        background-color: #F8FAFC;
    }

    /* Séparateurs */
    hr {
        border-top: 1px solid #E2E8F0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INITIALISATION API ---
api_key = st.sidebar.text_input("🔑 Clé API Gemini", type="password", value=st.secrets.get("GEMINI_API_KEY", ""))

if not api_key:
    st.info("Veuillez saisir votre clé API Gemini dans la barre latérale pour activer le service.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- HEADER ---
st.markdown("<h1 style='margin-bottom: 0;'>Modop <span style='color:#00D2B4'>Studio</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #64748B;'>Génération automatique de documentations techniques</p>", unsafe_allow_html=True)
st.divider()

# --- LAYOUT ---
col1, col2 = st.columns([0.45, 0.55], gap="large")

with col1:
    st.subheader("📽️ Source Vidéo")
    uploaded_file = st.file_uploader("Sélectionnez votre enregistrement MP4 ou MOV", type=['mp4', 'mov'])
    
    if uploaded_file:
        st.video(uploaded_file)
        if st.button("Lancer la rédaction"):
            with st.spinner("Analyse intelligente en cours..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tfile:
                    tfile.write(uploaded_file.read())
                    video_path = tfile.name

                google_video_file = genai.upload_file(path=video_path)
                
                prompt = """Analyse cette vidéo de démonstration logicielle.
                Rédige un mode opératoire clair et structuré en Markdown :
                1. Titre de la procédure
                2. Introduction (ce que l'utilisateur va accomplir)
                3. Tableau des étapes (Étape | Action | Timestamp)
                4. Conclusion ou points de vigilance.
                Utilise un français professionnel et concis."""
                
                response = model.generate_content([prompt, google_video_file])
                st.session_state.modop_text = response.text
                os.remove(video_path)

with col2:
    st.subheader("📄 Guide Rédigé")
    
    if 'modop_text' in st.session_state:
        st.markdown(f'<div class="output-box">{st.session_state.modop_text}</div>', unsafe_allow_html=True)
        
        st.divider()
        st.subheader("📥 Exportation")
        
        exp_col1, exp_col2 = st.columns(2)
        
        # Word
        doc = Document()
        doc.add_heading('Mode Opératoire - IA Générative', 0)
        doc.add_paragraph(st.session_state.modop_text)
        doc_path = "modop_final.docx"
        doc.save(doc_path)
        
        with exp_col1:
            with open(doc_path, "rb") as f:
                st.download_button("💾 Export Word (.docx)", f, "Modop_Nomadia.docx")
        
        # PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=11)
        # Nettoyage des caractères spéciaux pour le PDF
        clean_text = st.session_state.modop_text.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 10, clean_text)
        pdf_path = "modop_final.pdf"
        pdf.output(pdf_path)
        
        with exp_col2:
            with open(pdf_path, "rb") as f:
                st.download_button("📑 Export PDF (.pdf)", f, "Modop_Nomadia.pdf")
    else:
        st.write("Le guide utilisateur apparaîtra ici après l'analyse de votre vidéo.")

st.sidebar.markdown("---")
st.sidebar.caption("Propulsé par Gemini 1.5 Flash • 2026")
