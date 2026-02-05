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
st.set_page_config(page_title="Nomadia SmartDoc", page_icon="⚡", layout="wide")

# --- DESIGN SYSTEM NOMADIA ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #FFFFFF; font-family: 'Inter', sans-serif; }
    .main-title { color: #0B192E; font-size: 50px; font-weight: 800; text-align: center; margin-bottom: 0px; }
    .highlight { color: #A3E671; }
    .subtitle { color: #64748B; text-align: center; font-size: 18px; margin-bottom: 40px; }
    .upload-container { border: 2px dashed #A3E671; border-radius: 20px; padding: 40px; text-align: center; background-color: #FDFDFD; }
    .stButton>button { background-color: #A3E671 !important; color: #0B192E !important; border: none !important; border-radius: 30px !important; padding: 15px 40px !important; font-weight: bold !important; font-size: 18px !important; display: block; margin: 0 auto; }
    .card { border: 1px solid #F0FDF4; border-radius: 20px; padding: 20px; background: white; box-shadow: 0 4px 15px rgba(0,0,0,0.05); height: 100%; }
    .card-num { color: #A3E671; font-size: 30px; font-weight: bold; }
    .card-title { color: #0B192E; font-weight: bold; font-size: 18px; margin: 10px 0; }
    .card-text { color: #64748B; font-size: 14px; }
    .result-area { background-color: #F8FAFC; border-radius: 20px; padding: 30px; margin-top: 30px; border: 1px solid #E2E8F0; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIQUE D'EXTRACTION ---
def extract_frame(video_path, timestamp_str):
    try:
        # Nettoyage du timestamp (ex: [01:22] -> 01:22)
        ts = timestamp_str.replace('[','').replace(']','').strip()
        parts = list(map(int, ts.split(':')))
        seconds = parts[0] * 60 + parts[1] if len(parts) == 2 else parts[0]
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(seconds * fps))
        ret, frame = cap.read()
        if ret:
            path = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg').name
            cv2.imwrite(path, frame)
            cap.release()
            return path
        cap.release()
    except: return None

# --- API ---
api_key = st.sidebar.text_input("🔑 Clé API", type="password", value=st.secrets.get("GEMINI_API_KEY", ""))
if api_key: 
    genai.configure(api_key=api_key)
else: 
    st.info("Veuillez saisir votre clé API dans la barre latérale.")
    st.stop()

# --- HEADER ---
st.markdown('<div style="text-align:right"><span style="background:#F0FDF4; color:#22C55E; padding:5px 15px; border-radius:20px; font-size:12px; font-weight:bold">AI POWERED SUITE</span></div>', unsafe_allow_html=True)
st.markdown('<h1 class="main-title">Générateur de <span class="highlight">mode opératoire</span></h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Optimisez vos déploiements Nomadia SmartDoc.</p>', unsafe_allow_html=True)

# --- UPLOAD ---
uploaded_file = st.file_uploader("", type=['mp4', 'mov'], label_visibility="collapsed")

if not uploaded_file:
    st.markdown('<div class="upload-container"><h3>Analysez vos manipulations</h3><p>Glissez votre vidéo ici.</p></div>', unsafe_allow_html=True)
else:
    st.video(uploaded_file)
    if st.button("DÉMARRER L'ANALYSE"):
        with st.spinner("Recherche du meilleur modèle IA disponible..."):
            try:
                # --- SÉCURITÉ : DÉTECTION DU MODÈLE ---
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                # Priorité : 1.5-flash (stable) -> 2.5-flash (nouveau) -> 1.5-pro -> premier de la liste
                if any("models/gemini-1.5-flash" in m for m in available_models):
                    target_model = "models/gemini-1.5-flash"
                elif any("models/gemini-2.5-flash" in m for m in available_models):
                    target_model = "models/gemini-2.5-flash"
                else:
                    target_model = available_models[0]

                tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                tfile.write(uploaded_file.read())
                video_path = tfile.name

                myfile = genai.upload_file(path=video_path)
                while myfile.state.name == "PROCESSING":
                    time.sleep(3)
                    myfile = genai.get_file(myfile.name)

                model = genai.GenerativeModel(target_model)
                prompt = "Rédige un guide technique. Format : TITRE: [Nom] DESC: [Action] TIME: [MM:SS] Séparateur: ---"
                response = model.generate_content([prompt, myfile])
                
                steps = []
                for block in response.text.split('---'):
                    t = re.search(r"TITRE: (.*)", block)
                    d = re.search(r"DESC: (.*)", block)
                    ts = re.search(r"TIME: (.*)", block)
                    if t and d and ts:
                        steps.append({"title": t.group(1), "desc": d.group(1), "time": ts.group(1), "img": extract_frame(video_path, ts.group(1))})
                
                st.session_state.steps = steps
                os.remove(video_path)
                st.rerun()

            except Exception as e:
                st.error(f"Erreur technique : {str(e)}")

# --- AFFICHAGE RÉSULTATS ---
if 'steps' in st.session_state:
    st.markdown('<div class="result-area">', unsafe_allow_html=True)
    for i, step in enumerate(st.session_state.steps):
        c1, c2 = st.columns([0.4, 0.6])
        with c1:
            if step['img']: st.image(step['img'])
        with c2:
            st.markdown(f"**Étape {i+
