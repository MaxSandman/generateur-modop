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

# --- STYLE CSS (CORRIGÉ) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');
    .stApp { background-color: #F8FAFC; font-family: 'Plus Jakarta Sans', sans-serif; }
    
    .header-title { text-align: center; font-weight: 800; color: #0B192E; margin-bottom: 1rem; font-size: 28px; }
    .header-title span { color: #A3E671; }

    /* Stepper */
    .stepper-box { display: flex; justify-content: center; gap: 30px; margin-bottom: 2rem; }
    .step-item { display: flex; align-items: center; gap: 8px; color: #94A3B8; font-size: 13px; font-weight: 600; }
    .step-item.active { color: #0B192E; }
    .step-dot { width: 8px; height: 8px; border-radius: 50%; background: #E2E8F0; }
    .active .step-dot { background: #A3E671; box-shadow: 0 0 8px #A3E671; }

    /* Cards */
    .main-card { background: white; padding: 30px; border-radius: 20px; border: 1px solid #E2E8F0; box-shadow: 0 10px 25px rgba(0,0,0,0.03); }
    .summary-card { background: #0B192E; color: white; padding: 25px; border-radius: 16px; margin-bottom: 20px; border-left: 5px solid #A3E671; }
    
    /* Buttons */
    .stButton>button { border-radius: 10px !important; font-weight: 700 !important; }
    div[data-testid="stFileUploadDropzone"] { border: 2px dashed #A3E671 !important; background: #F0FDF4 !important; border-radius: 12px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- BACKEND FUNCTIONS ---
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
    st.subheader("🔑 Configuration")
    api_key = st.text_input("Clé API Gemini", type="password", value=st.secrets.get("GEMINI_API_KEY", ""))
    if api_key: genai.configure(api_key=api_key)

st.markdown('<div class="header-title">NOMADIA <span>SMARTDOC</span></div>', unsafe_allow_html=True)

# --- LOGIQUE D'ÉTAT ---
if 'steps' in st.session_state:
    cur = 3
elif 'processing' in st.session_state:
    cur = 2
else:
    cur = 1

# --- STEPPER ---
st.markdown(f"""
    <div class="stepper-box">
        <div class="step-item {'active' if cur==1 else ''}"><div class="step-dot"></div> IMPORT</div>
        <div class="step-item {'active' if cur==2 else ''}"><div class="step-dot"></div> ANALYSE</div>
        <div class="step-item {'active' if cur==3 else ''}"><div class="step-dot"></div> RESULTAT</div>
    </div>
""", unsafe_allow_html=True)

# --- FLUX DE TRAVAIL ---

# ÉTAPE 1 : IMPORT (Uniquement si rien n'est en cours et pas de résultat)
if cur == 1:
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload", type=['mp4', 'mov'], label_visibility="collapsed")
    if uploaded_file:
        st.video(uploaded_file)
        if st.button("🚀 LANCER L'ANALYSE", use_container_width=True):
            st.session_state.processing = True
            st.session_state.temp_video = uploaded_file.read()
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ÉTAPE 2 : ANALYSE (Uniquement pendant le traitement)
elif cur == 2:
    st.markdown('<div class="main-card" style="text-align:center;">', unsafe_allow_html=True)
    with st.status("🔮 L'IA rédige votre guide...", expanded=True) as status:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tfile:
                tfile.write(st.session_state.temp_video)
                video_path = tfile.name
            
            myfile = genai.upload_file(path=video_path)
            while myfile.state.name == "PROCESSING": time.sleep(1); myfile = genai.get_file(myfile.name)
            
            # Détection modèle
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target = next((m for m in models if "flash" in m), models[0])
            model = genai.GenerativeModel(target)
            
            prompt = "RESUME: [Global] --- TITRE: [Etape] TIME: [MM:SS] DESC: [Détail] ---"
            response = model.generate_content([prompt, myfile])
            
            # Parsing
            summary_match = re.search(r"RESUME: (.*?)(?=---)", response.text, re.DOTALL)
            st.session_state.summary = summary_match.group(1).strip() if summary_match else "Prêt."
            
            steps_data = []
            for block in response.text.split('---')[1:]:
                t, ts, d = re.search(r"TITRE: (.*)", block), re.search(r"TIME: (.*)", block), re.search(r"DESC: (.*)", block)
                if t and ts:
                    steps_data.append({
                        "title": t.group(1).strip(), "time": ts.group(1).strip(), 
                        "desc": d.group(1).strip() if d else "", "img": extract_frame(video_path, ts.group(1))
                    })
            
            st.session_state.steps = steps_data
            status.update(label="Analyse terminée !", state="complete")
            del st.session_state.processing
            st.rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")
            del st.session_state.processing
    st.markdown('</div>', unsafe_allow_html=True)

# ÉTAPE 3 : RÉSULTATS (Uniquement quand les étapes sont prêtes)
elif cur == 3:
    # 1. Résumé
    st.markdown(f"""
        <div class="summary-card">
            <div style="color:#A3E671; font-weight:800; margin-bottom:8px; font-size:12px; letter-spacing:1px;">SYNTHÈSE</div>
            <div style="font-size:15px; line-height:1.5;">{st.session_state.summary}</div>
        </div>
    """, unsafe_allow_html=True)

    # 2. Exports
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown("<p style='font-weight:700; margin-bottom:15px; font-size:14px;'>💾 EXPORTS</p>", unsafe_allow_html=True)
    
    # Génération réelle pour les boutons
    # PDF express pour l'exemple
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", size=12); pdf.cell(200, 10, txt="Guide Nomadia", ln=1)
    pdf_file = pdf.output(dest='S').encode('latin-1')

    col1, col2, col3 = st.columns(3)
    col1.download_button("📘 WORD", data=b"", file_name="guide.docx", use_container_width=True)
    col2.download_button("🗂️ CONFLUENCE", data=b"", file_name="pack.zip", use_container_width=True)
    col3.download_button("📕 PDF", data=pdf_file, file_name="guide.pdf", use_container_width=True)
    
    st.markdown("<hr style='border-top:1px solid #EEE; margin:20px 0;'>", unsafe_allow_html=True)
    if st.button("🔄 NOUVELLE ANALYSE", use_container_width=True):
        for key in ['steps', 'summary', 'temp_video']: st.session_state.pop(key, None)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # 3. Détails
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🔎 VOIR LE DÉTAIL DES ÉTAPES"):
        for s in st.session_state.steps:
            c_i, c_t = st.columns([0.4, 0.6])
            if s['img']: c_i.image(s['img'])
            c_t.markdown(f"**{s['title']}** ({s['time']})\n\n{s['desc']}")
            st.divider()
