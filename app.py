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
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="Nomadia SmartDoc", page_icon="⚡", layout="centered")

# --- STYLE CSS (MODERNE & FIXE) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');
    .stApp { background-color: #F4F7FA; font-family: 'Plus Jakarta Sans', sans-serif; }
    
    .header-title { text-align: center; font-weight: 800; color: #0B192E; margin-bottom: 1rem; font-size: 32px; }
    .header-title span { color: #A3E671; }

    /* Stepper */
    .stepper-box { display: flex; justify-content: center; gap: 30px; margin-bottom: 2rem; }
    .step-item { display: flex; align-items: center; gap: 8px; color: #94A3B8; font-size: 13px; font-weight: 600; }
    .step-item.active { color: #0B192E; }
    .step-dot { width: 10px; height: 10px; border-radius: 50%; background: #E2E8F0; }
    .active .step-dot { background: #A3E671; box-shadow: 0 0 10px #A3E671; }

    /* Zone Centrale */
    .main-card { background: white; padding: 30px; border-radius: 24px; border: 1px solid #E2E8F0; box-shadow: 0 10px 30px rgba(0,0,0,0.03); }
    
    /* Uploader Custom */
    div[data-testid="stFileUploadDropzone"] { border: 2px dashed #A3E671 !important; background: #F0FDF4 !important; border-radius: 16px !important; }
    
    /* Summary Card */
    .summary-box { background: #0B192E; color: white; padding: 25px; border-radius: 20px; margin-bottom: 20px; border-left: 6px solid #A3E671; }
    
    /* Fix pour les boutons d'export */
    .stDownloadButton button { width: 100% !important; background: white !important; color: #0B192E !important; border: 1px solid #E2E8F0 !important; border-radius: 12px !important; font-weight: 700 !important; }
    .stDownloadButton button:hover { border-color: #A3E671 !important; color: #A3E671 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTION EXTRACTION ---
def extract_frame(video_bytes, timestamp_str):
    try:
        ts = timestamp_str.replace('[','').replace(']','').strip()
        parts = list(map(int, ts.split(':')))
        seconds = parts[0] * 60 + parts[1] if len(parts) == 2 else parts[0]
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
            tmp.write(video_bytes)
            video_path = tmp.name
            
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(seconds * fps))
        ret, frame = cap.read()
        if ret:
            img_tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            cv2.imwrite(img_tmp.name, frame)
            cap.release()
            os.remove(video_path)
            return img_tmp.name
        cap.release()
        os.remove(video_path)
    except: return None
    return None

# --- SIDEBAR ---
with st.sidebar:
    st.subheader("🔑 Configuration")
    api_key = st.text_input("Clé API Gemini", type="password", value=st.secrets.get("GEMINI_API_KEY", ""))
    if api_key: genai.configure(api_key=api_key)

st.markdown('<div class="header-title">NOMADIA <span>SMARTDOC</span></div>', unsafe_allow_html=True)

# --- GESTION ÉTATS ---
if 'steps' in st.session_state: cur = 3
elif 'processing' in st.session_state: cur = 2
else: cur = 1

st.markdown(f"""
    <div class="stepper-box">
        <div class="step-item {'active' if cur==1 else ''}"><div class="step-dot"></div> IMPORT</div>
        <div class="step-item {'active' if cur==2 else ''}"><div class="step-dot"></div> ANALYSE</div>
        <div class="step-item {'active' if cur==3 else ''}"><div class="step-dot"></div> RÉSULTAT</div>
    </div>
""", unsafe_allow_html=True)

# --- ÉTAPE 1 : IMPORT ---
if cur == 1:
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload", type=['mp4', 'mov'], label_visibility="collapsed")
    if uploaded_file:
        # Zone vidéo réduite
        col_v1, col_v2, col_v3 = st.columns([1, 2, 1])
        with col_v2:
            st.video(uploaded_file)
        
        if st.button("🚀 LANCER L'ANALYSE", use_container_width=True):
            st.session_state.processing = True
            st.session_state.temp_video = uploaded_file.getvalue()
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- ÉTAPE 2 : ANALYSE ---
elif cur == 2:
    st.markdown('<div class="main-card" style="text-align:center;">', unsafe_allow_html=True)
    with st.status("🔮 L'IA rédige votre guide...", expanded=True) as status:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tfile:
                tfile.write(st.session_state.temp_video)
                video_path = tfile.name
            
            myfile = genai.upload_file(path=video_path)
            while myfile.state.name == "PROCESSING": time.sleep(1); myfile = genai.get_file(myfile.name)
            
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target = next((m for m in models if "flash" in m), models[0])
            model = genai.GenerativeModel(target)
            
            prompt = "Analyse cette vidéo technique. Format : RESUME: [Description globale] --- TITRE: [Etape] TIME: [MM:SS] DESC: [Action précise] ---"
            response = model.generate_content([prompt, myfile])
            
            summary = re.search(r"RESUME: (.*?)(?=---)", response.text, re.DOTALL)
            st.session_state.summary = summary.group(1).strip() if summary else "Analyse terminée."
            
            steps_data = []
            for block in response.text.split('---')[1:]:
                t, ts, d = re.search(r"TITRE: (.*)", block), re.search(r"TIME: (.*)", block), re.search(r"DESC: (.*)", block)
                if t and ts:
                    img_path = extract_frame(st.session_state.temp_video, ts.group(1))
                    steps_data.append({
                        "title": t.group(1).strip(), "time": ts.group(1).strip(), 
                        "desc": d.group(1).strip() if d else "", "img": img_path
                    })
            
            st.session_state.steps = steps_data
            status.update(label="Analyse terminée !", state="complete")
            del st.session_state.processing
            st.rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")
            del st.session_state.processing
    st.markdown('</div>', unsafe_allow_html=True)

# --- ÉTAPE 3 : RÉSULTATS ---
elif cur == 3:
    st.markdown(f'<div class="summary-box"><strong>📌 Résumé :</strong><br>{st.session_state.summary}</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown("<p style='font-weight:700; font-size:14px; margin-bottom:15px;'>💾 TÉLÉCHARGEMENTS</p>", unsafe_allow_html=True)
    
    # --- GÉNÉRATION WORD ---
    doc = Document()
    doc.add_heading('Guide Technique Nomadia', 0)
    doc.add_paragraph(st.session_state.summary)
    for s in st.session_state.steps:
        doc.add_heading(f"{s['title']} ({s['time']})", level=2)
        doc.add_paragraph(s['desc'])
        if s['img']: doc.add_picture(s['img'], width=Inches(4))
    
    doc_io = io.BytesIO()
    doc.save(doc_io)
    doc_io.seek(0)

    # --- GÉNÉRATION PDF ---
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "NOMADIA SMARTDOC", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, st.session_state.summary)
    for s in st.session_state.steps:
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"{s['title']} ({s['time']})", ln=True)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 7, s['desc'])
        if s['img']: pdf.image(s['img'], w=100)
    
    pdf_bytes = pdf.output(dest='S').encode('latin-1')

    col1, col2, col3 = st.columns(3)
    col1.download_button("📘 WORD", data=doc_io, file_name="guide.docx")
    col2.button("🗂️ CONFLUENCE (Soon)")
    col3.download_button("📕 PDF", data=pdf_bytes, file_name="guide.pdf")
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 ANALYSER UNE AUTRE VIDÉO", use_container_width=True):
        for k in ['steps', 'summary', 'temp_video']: st.session_state.pop(k, None)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # --- DÉTAILS ---
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🔎 DÉTAIL DES ÉTAPES (VÉRIFICATION)"):
        for s in st.session_state.steps:
            c1, c2 = st.columns([0.4, 0.6])
            with c1:
                if s['img'] and os.path.exists(s['img']): st.image(s['img'])
                else: st.caption("Image non extraite")
            with c2:
                st.markdown(f"**{s['title']}** ({s['time']})")
                st.write(s['desc'])
            st.divider()
