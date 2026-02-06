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

# --- CONFIGURATION & THÈME ---
st.set_page_config(page_title="Nomadia SmartDoc", page_icon="⚡", layout="centered")

# --- DESIGN SYSTEM FOCUS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');
    
    :root {
        --primary: #A3E671;
        --dark: #0B192E;
        --bg: #F8FAFC;
    }

    .stApp { background-color: var(--bg); font-family: 'Plus Jakarta Sans', sans-serif; }
    
    /* Titre discret */
    .header-title {
        text-align: center; font-weight: 800; color: var(--dark);
        margin-bottom: 2rem; font-size: 28px;
    }
    .header-title span { color: var(--primary); }

    /* Stepper minimaliste */
    .stepper-box {
        display: flex; justify-content: center; gap: 40px;
        margin-bottom: 3rem; padding-bottom: 1rem;
        border-bottom: 1px solid #E2E8F0;
    }
    .step-item { display: flex; align-items: center; gap: 8px; color: #94A3B8; font-size: 14px; font-weight: 600; }
    .step-item.active { color: var(--dark); }
    .step-dot { width: 10px; height: 10px; border-radius: 50%; background: #E2E8F0; }
    .active .step-dot { background: var(--primary); box-shadow: 0 0 10px var(--primary); }

    /* Zone Centrale Unique */
    .main-card {
        background: white; padding: 40px; border-radius: 24px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.05);
        border: 1px solid #E2E8F0;
    }

    /* Résumé Premium */
    .summary-card {
        background: var(--dark); color: white; padding: 25px;
        border-radius: 16px; margin-bottom: 20px;
    }

    /* Boutons */
    .stButton>button {
        border-radius: 12px !important; padding: 12px 24px !important;
        font-weight: 700 !important; width: 100%; border: none !important;
    }
    .primary-btn button { background: var(--primary) !important; color: var(--dark) !important; }
    
    /* File Uploader Custom */
    [data-testid="stFileUploadDropzone"] {
        border: 2px dashed #A3E671 !important; background: #F0FDF4 !important;
        border-radius: 16px !important; padding: 40px !important;
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

# --- SIDEBAR DISCRÈTE ---
with st.sidebar:
    st.subheader("🔑 Connexion")
    api_key = st.text_input("Clé API Gemini", type="password", value=st.secrets.get("GEMINI_API_KEY", ""))
    if api_key: genai.configure(api_key=api_key)

# --- HEADER ---
st.markdown('<div class="header-title">NOMADIA <span>SMARTDOC</span></div>', unsafe_allow_html=True)

# --- STEPPER ---
cur = 3 if 'steps' in st.session_state else (2 if 'processing' in st.session_state else 1)
st.markdown(f"""
    <div class="stepper-box">
        <div class="step-item {'active' if cur==1 else ''}"><div class="step-dot"></div> IMPORT</div>
        <div class="step-item {'active' if cur==2 else ''}"><div class="step-dot"></div> ANALYSE</div>
        <div class="step-item {'active' if cur==3 else ''}"><div class="step-dot"></div> RESULTAT</div>
    </div>
""", unsafe_allow_html=True)

# --- ÉTAPE 1 : IMPORT CENTRAL ---
if 'steps' not in st.session_state and 'processing' not in st.session_state:
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown("<h4 style='text-align:center; margin-bottom:20px;'>Déposez votre vidéo de démonstration</h4>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("", type=['mp4', 'mov'], label_visibility="collapsed")
    
    if uploaded_file:
        st.video(uploaded_file)
        st.markdown('<div class="primary-btn" style="margin-top:20px;">', unsafe_allow_html=True)
        if st.button("LANCER L'ANALYSE"):
            st.session_state.processing = True
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- ÉTAPE 2 : ANALYSE ---
if 'processing' in st.session_state and 'steps' not in st.session_state:
    st.markdown('<div class="main-card" style="text-align:center;">', unsafe_allow_html=True)
    with st.spinner("L'IA examine chaque frame pour rédiger votre guide..."):
        try:
            # Code de traitement identique mais sans affichage parasite
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tfile:
                tfile.write(uploaded_file.read())
                video_path = tfile.name
            myfile = genai.upload_file(path=video_path)
            while myfile.state.name == "PROCESSING": time.sleep(1); myfile = genai.get_file(myfile.name)
            
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target_model = next((m for m in models if "flash" in m), models[0])
            model = genai.GenerativeModel(target_model)
            
            prompt = "RESUME: [Résumé] --- TITRE: [Titre] DESC: [Action] TIME: [MM:SS] ---"
            response = model.generate_content([prompt, myfile])
            
            summary = re.search(r"RESUME: (.*?)(?=---)", response.text, re.DOTALL)
            st.session_state.summary = summary.group(1).strip() if summary else "Analyse terminée."
            
            steps = []
            for block in response.text.split('---')[1:]:
                t, ts, d = re.search(r"TITRE: (.*)", block), re.search(r"TIME: (.*)", block), re.search(r"DESC: (.*)", block)
                if t and ts:
                    steps.append({"title": t.group(1).strip(), "time": ts.group(1).strip(), "desc": d.group(1).strip() if d else "", "img": extract_frame(video_path, ts.group(1))})
            
            st.session_state.steps = steps
            del st.session_state.processing
            st.rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")
            del st.session_state.processing
    st.markdown('</div>', unsafe_allow_html=True)

# --- ÉTAPE 3 : RÉSULTAT ---
if 'steps' in st.session_state:
    # Zone Résumé
    st.markdown(f"""
        <div class="summary-card">
            <h5 style="margin:0 0 10px 0; color:#A3E671;">📌 Résumé de la procédure</h5>
            <p style="margin:0; font-size:15px; line-height:1.6;">{st.session_state.summary}</p>
        </div>
    """, unsafe_allow_html=True)

    # Zone Exports
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown("<h5 style='margin-bottom:20px;'>💾 Télécharger les documents</h5>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    # (Logique de génération Word/PDF/ZIP à remettre ici comme précédemment)
    c1.button("📘 Word")
    c2.button("🗂️ Confluence")
    c3.button("📕 PDF")
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Analyser une autre vidéo", use_container_width=True):
        for k in ['steps','summary']: st.session_state.pop(k, None)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Zone Détail repliée
    with st.expander("🔎 Voir le pas à pas détaillé"):
        for step in st.session_state.steps:
            col_i, col_t = st.columns([0.4, 0.6])
            if step['img']: col_i.image(step['img'])
            col_t.markdown(f"**{step['title']}** ({step['time']})\n\n{step['desc']}")
            st.divider()
