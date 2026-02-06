import streamlit as st
import google.generativeai as genai
import cv2
import os
import tempfile
import time
import re
import zipfile
from docx import Document
from docx.shared import Inches
from fpdf import FPDF

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Nomadia SmartDoc", page_icon="⚡", layout="wide")

# --- DESIGN SYSTEM NOMADIA ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    .stApp { background-color: #F8FAFC; font-family: 'Inter', sans-serif; }
    
    .nomadia-header { 
        text-align: center; font-size: 40px; font-weight: 800; color: #0B192E; 
        margin-top: 20px; text-transform: uppercase; letter-spacing: -1px;
    }
    .highlight { color: #A3E671; }
    .subtitle { color: #64748B; text-align: center; font-size: 16px; margin-bottom: 30px; }

    /* WORKFLOW STEPPER */
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
        border-color: #A3E671; background-color: #F0FDF4; color: #0B192E; box-shadow: 0 4px 6px rgba(163, 230, 113, 0.1);
    }
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

    .summary-box {
        background-color: #F0F9FF; border-left: 5px solid #00D2B4; padding: 20px; border-radius: 8px; color: #0B192E; margin-bottom: 25px;
    }

    .stButton>button { 
        background-color: #0B192E !important; color: #A3E671 !important; 
        border: none !important; border-radius: 8px !important; 
        padding: 12px 20px !important; font-weight: bold !important; width: 100%;
    }
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

# --- HEADER & STEPPER ---
st.markdown('<div class="nomadia-header">NOMADIA <span class="highlight">SMARTDOC</span></div>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Générateur de documentation technique automatisé</p>', unsafe_allow_html=True)

current_step = 1
if 'steps' in st.session_state: current_step = 3
elif 'processing' in st.session_state: current_step = 2

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
    
    if uploaded_file:
        with st.expander("👁️ Voir la vidéo source"):
            st.video(uploaded_file)
        
        col_c, col_btn, col_d = st.columns([1, 2, 1])
        with col_btn:
            if st.button("LANCER L'ANALYSE INTELLIGENTE"):
                st.session_state.processing = True
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- ZONE 2 : TRAITEMENT ---
if 'processing' in st.session_state and 'steps' not in st.session_state:
    st.markdown('<div class="zone-card"><div class="zone-title">🧠 Traitement en cours</div>', unsafe_allow_html=True)
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.markdown("**Préparation de la vidéo...**")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tfile:
            tfile.write(uploaded_file.read())
            video_path = tfile.name
        
        myfile = genai.upload_file(path=video_path)
        progress_bar.progress(20)
        
        while myfile.state.name == "PROCESSING":
            time.sleep(2)
            myfile = genai.get_file(myfile.name)
        progress_bar.progress(50)
        
        # --- DETECTION DYNAMIQUE DU MODELE ---
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target_model = next((m for m in models if "gemini-1.5-flash" in m
