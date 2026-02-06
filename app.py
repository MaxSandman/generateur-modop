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

# --- CONFIGURATION ---
st.set_page_config(page_title="Nomadia SmartDoc", page_icon="⚡", layout="centered")

# --- DESIGN SYSTEM ULTRA-MODERNE ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;800&display=swap');
    
    /* Global Reset */
    .stApp { background-color: #F4F7FA; font-family: 'Plus Jakarta Sans', sans-serif; }
    
    /* Header & Branding */
    .header-title { 
        text-align: center; font-weight: 800; color: #0B192E; 
        margin: 0 0 1rem 0; font-size: 32px; letter-spacing: -1px;
    }
    .header-title span { color: #A3E671; }

    /* Stepper Modern */
    .stepper-box { display: flex; justify-content: center; gap: 40px; margin-bottom: 2rem; }
    .step-item { display: flex; align-items: center; gap: 10px; color: #94A3B8; font-size: 14px; font-weight: 600; }
    .step-item.active { color: #0B192E; }
    .step-indicator { width: 12px; height: 12px; border-radius: 4px; background: #E2E8F0; transform: rotate(45deg); }
    .active .step-indicator { background: #A3E671; box-shadow: 0 0 15px rgba(163, 230, 113, 0.5); }

    /* Custom File Uploader - THE CORE CHANGE */
    div[data-testid="stFileUploadDropzone"] {
        border: 2px dashed #A3E671 !important;
        background: rgba(255, 255, 255, 0.8) !important;
        border-radius: 24px !important;
        padding: 60px 20px !important;
        transition: all 0.3s ease;
        min-height: 250px;
        display: flex;
        justify-content: center;
    }
    
    div[data-testid="stFileUploadDropzone"]:hover {
        background: #F0FDF4 !important;
        border-color: #0B192E !important;
        transform: translateY(-2px);
    }

    /* Modifie le texte à l'intérieur de l'uploader */
    div[data-testid="stFileUploadDropzone"] i { color: #A3E671 !important; }
    div[data-testid="stFileUploadDropzone"] span { 
        font-family: 'Plus Jakarta Sans', sans-serif !important; 
        color: #64748B !important;
        font-weight: 500;
    }

    /* Buttons Style */
    .stButton>button {
        background: #0B192E !important;
        color: white !important;
        border-radius: 14px !important;
        padding: 16px !important;
        font-weight: 700 !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(11, 25, 46, 0.15) !important;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background: #A3E671 !important;
        color: #0B192E !important;
        transform: scale(1.02);
    }

    /* Cards */
    .result-card {
        background: white;
        padding: 30px;
        border-radius: 28px;
        border: 1px solid rgba(226, 232, 240, 0.8);
        box-shadow: 0 20px 40px rgba(0,0,0,0.04);
    }
    
    .summary-box {
        background: #0B192E;
        color: white;
        padding: 30px;
        border-radius: 24px;
        margin-bottom: 25px;
        position: relative;
        overflow: hidden;
    }
    .summary-box::after {
        content: ""; position: absolute; top: -50%; right: -10%;
        width: 150px; height: 150px; background: rgba(163, 230, 113, 0.1);
        border-radius: 50%;
    }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIQUE BACKEND ---
def extract_frame(video_path, timestamp_str):
    try:
        ts = timestamp_str.replace('[','').replace(']','').strip()
        parts = list(map(int, ts.split(':')))
        seconds = parts[0] * 60 + parts[1] if len(parts) == 2 else parts[0]
        cap = cv2.VideoCapture(video_path)
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

# --- SIDEBAR ---
with st.sidebar:
    st.caption("NOMADIA GROUP")
    api_key = st.text_input("Clé API Gemini", type="password", value=st.secrets.get("GEMINI_API_KEY", ""))
    if api_key: genai.configure(api_key=api_key)

# --- HEADER ---
st.markdown('<div class="header-title">NOMADIA <span>SMARTDOC</span></div>', unsafe_allow_html=True)

# --- NAVIGATION STATE ---
if 'steps' in st.session_state:
    cur = 3
elif 'processing' in st.session_state:
    cur = 2
else:
    cur = 1

st.markdown(f"""
    <div class="stepper-box">
        <div class="step-item {'active' if cur==1 else ''}"><div class="step-indicator"></div> IMPORT</div>
        <div class="step-item {'active' if cur==2 else ''}"><div class="step-indicator"></div> ANALYSE</div>
        <div class="step-item {'active' if cur==3 else ''}"><div class="step-indicator"></div> RÉSULTAT</div>
    </div>
""", unsafe_allow_html=True)

# --- PHASE 1 : IMPORT ---
if cur == 1:
    # On encapsule tout dans un div vide pour remonter le contenu
    st.markdown('<div style="margin-top: -20px;">', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("", type=['mp4', 'mov'], label_visibility="collapsed")
    
    if uploaded_file:
        st.video(uploaded_file)
        if st.button("DÉMARRER L'ANALYSE INTELLIGENTE", use_container_width=True):
            st.session_state.processing = True
            st.session_state.temp_video = uploaded_file.read()
            st.rerun()
    else:
        st.markdown("<p style='text-align:center; color:#94A3B8; font-size:14px; margin-top:10px;'>Formats supportés : MP4, MOV. Max 200Mo.</p>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- PHASE 2 : ANALYSE ---
elif cur == 2:
    st.markdown('<div class="result-card" style="text-align:center;">', unsafe_allow_html=True)
    with st.status("🚀 Rédaction du guide technique...", expanded=True) as status:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tfile:
                tfile.write(st.session_state.temp_video)
                video_path = tfile.name
            
            myfile = genai.upload_file(path=video_path)
            while myfile.state.name == "PROCESSING": time.sleep(1); myfile = genai.get_file(myfile.name)
            
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target = next((m for m in models if "flash" in m), models[0])
            model = genai.GenerativeModel(target)
            
            prompt = "RESUME: [Résumé] --- TITRE: [Etape] TIME: [MM:SS] DESC: [Détail] ---"
            response = model.generate_content([prompt, myfile])
            
            summary_match = re.search(r"RESUME: (.*?)(?=---)", response.text, re.DOTALL)
            st.session_state.summary = summary_match.group(1).strip() if summary_match else "Analyse terminée."
            
            steps_data = []
            for block in response.text.split('---')[1:]:
                t, ts, d = re.search(r"TITRE: (.*)", block), re.search(r"TIME: (.*)", block), re.search(r"DESC: (.*)", block)
                if t and ts:
                    steps_data.append({
                        "title": t.group(1).strip(), "time": ts.group(1).strip(), 
                        "desc": d.group(1).strip() if d else "", "img": extract_frame(video_path, ts.group(1))
                    })
            
            st.session_state.steps = steps_data
            status.update(label="Analyse complétée !", state="complete")
            del st.session_state.processing
            st.rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")
            del st.session_state.processing
    st.markdown('</div>', unsafe_allow_html=True)

# --- PHASE 3 : RÉSULTATS ---
elif cur == 3:
    st.markdown(f"""
        <div class="summary-box">
            <div style="color:#A3E671; font-weight:800; font-size:12px; letter-spacing:2px; margin-bottom:10px;">SYNTHÈSE IA</div>
            <div style="font-size:16px; line-height:1.6; font-weight:500;">{st.session_state.summary}</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="result-card">', unsafe_allow_html=True)
    st.markdown("<p style='font-weight:800; margin-bottom:20px; font-size:13px; color:#64748B;'>DOCUMENTS GÉNÉRÉS</p>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.button("📘 Word (.docx)", use_container_width=True)
    c2.button("🗂️ Confluence", use_container_width=True)
    c3.button("📕 PDF (.pdf)", use_container_width=True)
    
    st.markdown("<div style='margin-top:25px;'></div>", unsafe_allow_html=True)
    if st.button("NOUVELLE ANALYSE VIDÉO", use_container_width=True):
        for key in ['steps', 'summary', 'temp_video']: st.session_state.pop(key, None)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("🔎 DÉTAIL DES ÉTAPES"):
        for s in st.session_state.steps:
            c_i, c_t = st.columns([0.4, 0.6])
            if s['img']: c_i.image(s['img'], use_container_width=True)
            c_t.markdown(f"**{s['title']}**")
            c_t.caption(f"Time : {s['time']}")
            c_t.write(s['desc'])
            st.divider()
