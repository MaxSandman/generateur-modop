import streamlit as st
import google.generativeai as genai
import cv2
import os
import tempfile
import time
import re
import zipfile
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from fpdf import FPDF

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Nomadia SmartDoc", page_icon="⚡", layout="wide")

# --- DESIGN SYSTEM NOMADIA ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    .stApp { background-color: #F8FAFC; font-family: 'Inter', sans-serif; }
    
    /* Header */
    .nomadia-header { 
        text-align: center; font-size: 40px; font-weight: 800; color: #0B192E; 
        margin-top: 20px; text-transform: uppercase; letter-spacing: -1px;
    }
    .highlight { color: #A3E671; }
    .subtitle { color: #64748B; text-align: center; font-size: 16px; margin-bottom: 30px; }

    /* WORKFLOW STEPPER (1-2-3) */
    .stepper-container {
        display: flex; justify-content: space-between; margin-bottom: 40px; 
        padding: 0 50px; position: relative;
    }
    .step {
        background: white; border: 2px solid #E2E8F0; color: #64748B;
        padding: 10px 20px; border-radius: 50px; font-weight: bold; font-size: 14px;
        z-index: 2; width: 30%; text-align: center;
    }
    .step.active {
        border-color: #A3E671; background-color: #F0FDF4; color: #0B192E; box-shadow: 0 4px 6px rgba(163, 230, 113, 0.2);
    }
    /* Ligne connecteur */
    .step-line {
        position: absolute; top: 50%; left: 10%; right: 10%; height: 2px; background: #E2E8F0; z-index: 1; transform: translateY(-50%);
    }

    /* ZONES */
    .zone-card {
        background-color: white; border-radius: 15px; padding: 30px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.03); border: 1px solid #E2E8F0; margin-bottom: 20px;
    }
    .zone-title {
        font-size: 18px; font-weight: 700; color: #0B192E; margin-bottom: 15px; border-bottom: 2px solid #A3E671; display: inline-block; padding-bottom: 5px;
    }

    /* Upload Styling */
    .upload-box { border: 2px dashed #CBD5E1; border-radius: 12px; padding: 40px; text-align: center; background: #F8FAFC; }
    
    /* Summary Box */
    .summary-box {
        background-color: #F0F9FF; border-left: 5px solid #00D2B4; padding: 20px; border-radius: 8px; color: #0B192E; margin-bottom: 25px;
    }

    /* Buttons */
    .stButton>button { 
        background-color: #0B192E !important; color: #A3E671 !important; 
        border: none !important; border-radius: 8px !important; 
        padding: 12px 20px !important; font-weight: bold !important; width: 100%;
    }
    .stButton>button:hover { background-color: #1a2f4d !important; }
    
    </style>
    """, unsafe_allow_html=True)

# --- FONCTION EXTRACTION ---
def extract_frame(video_path, timestamp_str):
    try:
        ts = timestamp_str.replace('[','').replace(']','').strip()
        parts = list(map(int, ts.split(':')))
        seconds = parts[0] * 60 + parts[1] if len(parts) == 2 else parts[0]
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened(): return None
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(seconds * fps))
        ret, frame = cap.read()
        
        if ret:
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            cv2.imwrite(tfile.name, frame)
            cap.release()
            return tfile.name
        cap.release()
    except: return None
    return None

# --- API ---
api_key = st.sidebar.text_input("🔑 Clé API", type="password", value=st.secrets.get("GEMINI_API_KEY", ""))
if api_key: genai.configure(api_key=api_key)
else: st.stop()

# --- HEADER ---
st.markdown('<div class="nomadia-header">NOMADIA <span class="highlight">SMARTDOC</span></div>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Générateur de documentation technique automatisé</p>', unsafe_allow_html=True)

# --- WORKFLOW STATE MANAGEMENT ---
# On gère l'état visuel (1, 2 ou 3) selon la présence de résultats
current_step = 1
if 'steps' in st.session_state: current_step = 3
elif 'processing' in st.session_state: current_step = 2

# Affichage du Stepper HTML
st.markdown(f"""
    <div class="stepper-container">
        <div class="step-line"></div>
        <div class="step {'active' if current_step >= 1 else ''}">1. IMPORT VIDÉO</div>
        <div class="step {'active' if current_step >= 2 else ''}">2. ANALYSE IA</div>
        <div class="step {'active' if current_step >= 3 else ''}">3. RÉSULTAT & EXPORT</div>
    </div>
""", unsafe_allow_html=True)

# --- ZONE 1 : IMPORT ---
if 'steps' not in st.session_state:
    st.markdown('<div class="zone-card"><div class="zone-title">📡 Source Média</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("", type=['mp4', 'mov'], label_visibility="collapsed")
    
    if not uploaded_file:
        st.markdown('<div class="upload-box">📂 Glissez votre vidéo de démonstration ici</div>', unsafe_allow_html=True)
    else:
        with st.expander("👁️ Voir la vidéo source (masquée par défaut)"):
            st.video(uploaded_file)
        
        col_c, col_btn, col_d = st.columns([1, 2, 1])
        with col_btn:
            if st.button("LANCER L'ANALYSE INTELLIGENTE"):
                st.session_state.processing = True
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- ZONE 2 : TRAITEMENT (Automatique après clic) ---
if 'processing' in st.session_state and 'steps' not in st.session_state and uploaded_file:
    st.markdown('<div class="zone-card"><div class="zone-title">🧠 Traitement en cours</div>', unsafe_allow_html=True)
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 1. Upload
        status_text.markdown("**Envoi de la vidéo vers Nomadia AI...**")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tfile:
            tfile.write(uploaded_file.read())
            video_path = tfile.name
        
        myfile = genai.upload_file(path=video_path)
        progress_bar.progress(25)
        
        # 2. Waiting
        status_text.markdown("**Analyse des séquences et des actions...**")
        while myfile.state.name == "PROCESSING":
            time.sleep(2)
            myfile = genai.get_file(myfile.name)
        progress_bar.progress(50)
        
        # 3. Generation (Prompt mis à jour pour le Résumé)
        status_text.markdown("**Rédaction du guide technique et du résumé...**")
        model = genai.GenerativeModel("models/gemini-1.5-flash")
        
        prompt = """
        Tu es un expert technique chez Nomadia. Analyse cette vidéo.
        
        1. Commence IMPERATIVEMENT par un bloc "RESUME" contenant 3 phrases synthétiques expliquant la procédure vue dans la vidéo.
        2. Ensuite, détaille chaque étape (Titre, Description, Timestamp).
        
        Format de réponse STRICT :
        RESUME: [Le résumé global ici]
        ---
        TITRE: [Titre Etape 1]
        DESC: [Description précise]
        TIME: [MM:SS]
        ---
        TITRE: [Titre Etape 2]...
        """
        
        response = model.generate_content([prompt, myfile])
        progress_bar.progress(80)
        
        # 4. Parsing
        status_text.markdown("**Extraction des captures d'écran HD...**")
        
        # Récupération du résumé
        summary_match = re.search(r"RESUME: (.*?)(?=---)", response.text, re.DOTALL)
        summary_text = summary_match.group(1).strip() if summary_match else "Résumé non généré."
        
        # Récupération des étapes
        steps = []
        blocks = response.text.split('---')
        for block in blocks:
            t = re.search(r"TITRE: (.*)", block)
            d = re.search(r"DESC: (.*)", block)
            ts = re.search(r"TIME: (.*)", block)
            if t and d and ts:
                steps.append({
                    "title": t.group(1).strip(),
                    "desc": d.group(1).strip(),
                    "time": ts.group(1).strip(),
                    "img": extract_frame(video_path, ts.group(1))
                })
        
        st.session_state.steps = steps
        st.session_state.summary = summary_text
        
        progress_bar.progress(100)
        del st.session_state.processing
        # os.remove(video_path) # Optionnel selon usage
        st.rerun()

    except Exception as e:
        st.error(f"Erreur : {str(e)}")
        del st.session_state.processing

# --- ZONE 3 : RESULTAT & EXPORT ---
if 'steps' in st.session_state:
    # 3.1 LE RÉSUMÉ (En haut, bien visible)
    st.markdown('<div class="zone-card">', unsafe_allow_html=True)
    st.markdown('<div class="zone-title">📋 Synthèse de la procédure</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="summary-box"><strong>📌 Résumé IA :</strong><br>{st.session_state.summary}</div>', unsafe_allow_html=True)
    
    # 3.2 LES BOUTONS D'EXPORT (Juste sous le résumé)
    st.markdown('<div class="zone-title" style="margin-top:20px;">💾 Exports Disponibles</div>', unsafe_allow_html=True)
    
    # --- Generation Fichiers ---
    # WORD
    doc = Document()
    doc.add_heading('Nomadia SmartDoc', 0)
