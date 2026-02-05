import streamlit as st
import google.generativeai as genai
import cv2
import os
import tempfile
import time
import re
from docx import Document
from docx.shared import Inches
from fpdf import FPDF

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Modop Studio by Nomadia", page_icon="🛰️", layout="wide")

# --- STYLE CSS NOMADIA (LUMINEUX) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp { background-color: #FFFFFF; color: #002344; font-family: 'Inter', sans-serif; }
    h1, h2, h3 { color: #002344 !important; font-weight: 700 !important; }
    .stButton>button { background: #00D2B4; color: white !important; border-radius: 8px; border: none; font-weight: 600; }
    .stButton>button:hover { background-color: #00B5A0; }
    .output-box { background-color: #F8FAFC; padding: 20px; border-radius: 12px; border: 1px solid #E2E8F0; }
    .confluence-code { background-color: #F4F5F7; border-left: 5px solid #0052CC; padding: 10px; font-family: monospace; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTION D'EXTRACTION D'IMAGES ---
def extract_frame(video_path, timestamp_str):
    """Extrait une image de la vidéo à un timestamp donné (format MM:SS ou SS)"""
    try:
        # Conversion du timestamp en secondes
        parts = list(map(int, timestamp_str.split(':')))
        if len(parts) == 2: seconds = parts[0] * 60 + parts[1]
        else: seconds = parts[0]
        
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(seconds * fps))
        ret, frame = cap.read()
        if ret:
            img_path = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg').name
            cv2.imwrite(img_path, frame)
            cap.release()
            return img_path
        cap.release()
    except:
        return None
    return None

# --- API ---
api_key = st.sidebar.text_input("🔑 Clé API Gemini", type="password", value=st.secrets.get("GEMINI_API_KEY", ""))
if api_key:
    genai.configure(api_key=api_key)
else:
    st.stop()

# --- HEADER ---
st.markdown("<h1>Modop <span style='color:#00D2B4'>Studio</span> 🚀</h1>", unsafe_allow_html=True)
st.divider()

col1, col2 = st.columns([0.4, 0.6], gap="large")

with col1:
    st.subheader("📽️ Source Vidéo")
    uploaded_file = st.file_uploader("Fichier MP4/MOV", type=['mp4', 'mov'])
    
    if uploaded_file:
        st.video(uploaded_file)
        if st.button("Générer le Guide Illustré"):
            with st.spinner("Analyse et extraction des images..."):
                tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                tfile.write(uploaded_file.read())
                video_path = tfile.name

                myfile = genai.upload_file(path=video_path)
                while myfile.state.name == "PROCESSING":
                    time.sleep(4)
                    myfile = genai.get_file(myfile.name)

                # Prompt ultra-précis pour forcer le découpage propre
                prompt = """Analyse cette vidéo et crée un guide pas à pas. 
                Pour chaque action importante, donne :
                1. Un titre court à l'action.
                2. Une description précise.
                3. Le timestamp EXACT au format [MM:SS].
                
                Format de ta réponse :
                TITRE: [Nom de l'étape]
                DESC: [Description]
                TIME: [MM:SS]
                ---"""
                
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content([prompt, myfile])
                
                # Parsing de la réponse pour extraire les images
                steps = []
                raw_text = response.text
                blocks = raw_text.split('---')
                
                for block in blocks:
                    title = re.search(r"TITRE: (.*)", block)
                    desc = re.search(r"DESC: (.*)", block)
                    time_stamp = re.search(r"TIME: \[(.*?)\]", block)
                    
                    if title and desc and time_stamp:
                        img = extract_frame(video_path, time_stamp.group(1))
                        steps.append({
                            "title": title.group(1),
                            "desc": desc.group(1),
                            "time": time_stamp.group(1),
                            "img": img
                        })
                
                st.session_state.steps = steps
                st.session_state.raw_text = raw_text

with col2:
    st.subheader("📄 Guide Opérationnel")
    
    if 'steps' in st.session_state:
        tabs = st.tabs(["👁️ Aperçu", "📂 Export Word", "🔵 Export Confluence", "📕 Export PDF"])
        
        with tabs[0]:
            for i, step in enumerate(st.session_state.steps):
                st.markdown(f"### Étape {i+1}: {step['title']}")
                if step['img']: st.image(step['img'], caption=f"Action à {step['time']}")
                st.write(step['desc'])
                st.divider()

        with tabs[1]:
            doc = Document()
            doc.add_heading('Mode Opératoire - Nomadia', 0)
            for step in st.session_state.steps:
                doc.add_heading(step['title'], level=1)
                doc.add_paragraph(f"Timestamp : {step['time']}")
                doc.add_paragraph(step['desc'])
                if step['img']: doc.add_picture(step['img'], width=Inches(5))
            
            doc_path = "modop.docx"
            doc.save(doc_path)
            with open(doc_path, "rb") as f:
                st.download_button("📥 Télécharger le Word avec Images", f, "Guide_Illustre.docx")

        with tabs[2]:
            st.info("Copiez ce code dans un bloc 'Éditeur Wiki' ou 'Code' de Confluence")
            conf_text = "h1. Mode Opératoire\n"
            for step in st.session_state.steps:
                conf_text += f"*Step: {step['title']}* (at {step['time']})\n{step['desc']}\n\n"
            st.code(conf_text, language="markdown")

        with tabs[3]:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(40, 10, 'Mode Operatoire Technique')
            pdf.ln(20)
            pdf.set_font("Arial", size=11)
            for step in st.session_state.steps:
                pdf.multi_cell(0, 10, f"Etape: {step['title']} ({step['time']})\n{step['desc']}\n")
                pdf.ln(5)
            
            pdf_path = "modop.pdf"
            pdf.output(pdf_path)
            with open(pdf_path, "rb") as f:
                st.download_button("📥 Télécharger le PDF", f, "Guide.pdf")
