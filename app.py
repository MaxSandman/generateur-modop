import streamlit as st
import google.generativeai as genai
import cv2
import os
import tempfile
from docx import Document
from fpdf import FPDF

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Gemini Modop Studio",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- STYLE CSS (LOOK AI STUDIO) ---
st.markdown("""
    <style>
    .stApp { background-color: #131314; color: #e3e3e3; }
    [data-testid="stSidebar"] { background-color: #1e1f20; border-right: 1px solid #444746; }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #ffffff; font-family: 'Google Sans', sans-serif; }
    .stFileUploader { background-color: #1e1f20; border: 1px dashed #444746; border-radius: 8px; }
    .stButton>button { 
        background-color: #a8c7fa; color: #062e6f; border-radius: 20px; 
        font-weight: 600; border: none; padding: 0.5rem 2rem; width: 100%;
    }
    .stButton>button:hover { background-color: #d3e3fd; color: #041e49; }
    .stDownloadButton>button { 
        background-color: transparent; color: #a8c7fa; border: 1px solid #444746; 
        border-radius: 8px; width: 100%;
    }
    .output-box { 
        background-color: #1e1f20; padding: 20px; border-radius: 12px; 
        border: 1px solid #444746; line-height: 1.6;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INITIALISATION API ---
# On essaie de récupérer la clé dans les secrets, sinon dans la barre latérale
api_key = st.sidebar.text_input("🔑 Clé API Gemini", type="password", value=st.secrets.get("GEMINI_API_KEY", ""))

if not api_key:
    st.warning("Veuillez configurer votre clé API dans les paramètres ou la barre latérale.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- INTERFACE PRINCIPALE ---
st.title("✨ Gemini Modop Studio")
st.caption("Transformez vos captures vidéo en documentation professionnelle structurée.")

col1, col2 = st.columns([0.4, 0.6], gap="large")

with col1:
    st.subheader("📹 Source Vidéo")
    uploaded_file = st.file_uploader("Glissez-déposez votre enregistrement", type=['mp4', 'mov', 'avi'])
    
    if uploaded_file:
        st.video(uploaded_file)
        
        # Bouton d'action
        if st.button("🚀 Générer la documentation"):
            with st.spinner("Analyse multimodale en cours..."):
                # Sauvegarde temporaire pour l'envoi
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tfile:
                    tfile.write(uploaded_file.read())
                    video_path = tfile.name

                # Upload vers Google Gemini
                google_video_file = genai.upload_file(path=video_path)
                
                # Prompt spécifique Modop
                prompt = """Tu es un expert en documentation technique. Analyse cette vidéo et crée un mode opératoire pour Confluence.
                Structure : 
                1. Titre H1
                2. Objectif de la fonctionnalité
                3. Tableau des étapes : | Étape | Action | Interface | Timestamp |
                4. Liste des points d'attention (audio/visuel).
                Réponds en Markdown."""
                
                response = model.generate_content([prompt, google_video_file])
                st.session_state.modop_text = response.text
                
                # Nettoyage fichier temporaire
                os.remove(video_path)

with col2:
    st.subheader("📄 Documentation Générée")
    
    if 'modop_text' in st.session_state:
        st.markdown(f'<div class="output-box">{st.session_state.modop_text}</div>', unsafe_allow_html=True)
        
        st.divider()
        st.subheader("📥 Exportation")
        
        # Génération des fichiers d'export
        export_col1, export_col2 = st.columns(2)
        
        # -- Export WORD --
        doc = Document()
        doc.add_heading('Mode Opératoire Technique', 0)
        doc.add_paragraph(st.session_state.modop_text)
        doc_path = "modop_export.docx"
        doc.save(doc_path)
        
        with export_col1:
            with open(doc_path, "rb") as f:
                st.download_button("💾 Télécharger en Word (.docx)", f, "Modop_Gemini.docx")
        
        # -- Export PDF --
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, st.session_state.modop_text.encode('latin-1', 'replace').decode('latin-1'))
        pdf_path = "modop_export.pdf"
        pdf.output(pdf_path)
        
        with export_col2:
            with open(pdf_path, "rb") as f:
                st.download_button("📕 Télécharger en PDF (.pdf)", f, "Modop_Gemini.pdf")
    else:
        st.info("En attente d'une vidéo pour commencer l'analyse...")

st.sidebar.divider()
st.sidebar.markdown("### À propos")
st.sidebar.write("Outil conçu pour simplifier la rédaction des MODOP via l'IA multimodale.")
