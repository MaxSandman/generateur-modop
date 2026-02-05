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

# --- DESIGN SYSTEM NOMADIA (Basé sur ton image) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
    
    .stApp { background-color: #FFFFFF; font-family: 'Inter', sans-serif; }
    
    /* Header & Titles */
    .main-title { color: #0B192E; font-size: 50px; font-weight: 800; text-align: center; margin-bottom: 0px; }
    .highlight { color: #A3E671; }
    .subtitle { color: #64748B; text-align: center; font-size: 18px; margin-bottom: 40px; }
    
    /* Upload Box */
    .upload-container {
        border: 2px dashed #A3E671;
        border-radius: 20px;
        padding: 40px;
        text-align: center;
        background-color: #FDFDFD;
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #A3E671 !important;
        color: #0B192E !important;
        border: none !important;
        border-radius: 30px !important;
        padding: 15px 40px !important;
        font-weight: bold !important;
        font-size: 18px !important;
        transition: 0.3s;
        display: block;
        margin: 0 auto;
    }
    .stButton>button:hover { transform: scale(1.05); background-color: #92D460 !important; }

    /* Cards 01, 02, 03 */
    .card {
        border: 1px solid #F0FDF4;
        border-radius: 20px;
        padding: 20px;
        background: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        height: 100%;
    }
    .card-num { color: #A3E671; font-size: 30px; font-weight: bold; }
    .card-title { color: #0B192E; font-weight: bold; font-size: 18px; margin: 10px 0; }
    .card-text { color: #64748B; font-size: 14px; }
    
    /* Result Area */
    .result-area { background-color: #F8FAFC; border-radius: 20px; padding: 30px; margin-top: 30px; border: 1px solid #E2E8F0; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIQUE D'EXTRACTION ---
def extract_frame(video_path, timestamp_str):
    try:
        parts = list(map(int, timestamp_str.split(':')))
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
if api_key: genai.configure(api_key=api_key)
else: st.stop()

# --- UI : HEADER ---
st.markdown('<div style="text-align:right"><span style="background:#F0FDF4; color:#22C55E; padding:5px 15px; border-radius:20px; font-size:12px; font-weight:bold">AI POWERED SUITE</span></div>', unsafe_allow_html=True)
st.markdown('<h1 class="main-title">Générateur de <span class="highlight">mode opératoire</span></h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Optimisez vos déploiements. Transformez vos démonstrations vidéos<br>en guides techniques structurés pour vos clients et collaborateurs.</p>', unsafe_allow_html=True)

# --- UI : UPLOAD CENTER ---
container = st.container()
with container:
    uploaded_file = st.file_uploader("", type=['mp4', 'mov'], label_visibility="collapsed")
    
    if not uploaded_file:
        st.markdown("""
            <div class="upload-container">
                <img src="https://cdn-icons-png.flaticon.com/512/3097/3097412.png" width="60" style="margin-bottom:20px">
                <h3>Analysez vos manipulations</h3>
                <p style="color:#64748B">Glissez votre vidéo ici pour que l'IA Nomadia génère votre manuel technique.</p>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.video(uploaded_file)
        if st.button("DÉMARRER L'ANALYSE"):
            with st.spinner("L'intelligence Nomadia analyse vos flux..."):
                tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                tfile.write(uploaded_file.read())
                video_path = tfile.name

                myfile = genai.upload_file(path=video_path)
                while myfile.state.name == "PROCESSING":
                    time.sleep(3)
                    myfile = genai.get_file(myfile.name)

                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = "Rédige un guide pas à pas. Format strict par bloc : TITRE: [Nom] DESC: [Action] TIME: [MM:SS] Séparateur: ---"
                response = model.generate_content([prompt, myfile])
                
                # Parsing & Extraction Images
                steps = []
                for block in response.text.split('---'):
                    t = re.search(r"TITRE: (.*)", block)
                    d = re.search(r"DESC: (.*)", block)
                    ts = re.search(r"TIME: (.*)", block)
                    if t and d and ts:
                        clean_ts = ts.group(1).replace('[','').replace(']','')
                        steps.append({"title": t.group(1), "desc": d.group(1), "time": clean_ts, "img": extract_frame(video_path, clean_ts)})
                
                st.session_state.steps = steps
                os.remove(video_path)

st.write("---")

# --- UI : RESULT & EXPORT ---
if 'steps' in st.session_state:
    st.markdown('<div class="result-area">', unsafe_allow_html=True)
    st.subheader("🛠️ Manuel Technique Généré")
    
    for i, step in enumerate(st.session_state.steps):
        c1, c2 = st.columns([0.4, 0.6])
        with c1:
            if step['img']: st.image(step['img'], use_container_width=True)
        with c2:
            st.markdown(f"**Étape {i+1} : {step['title']}**")
            st.caption(f"⏱ Timestamp: {step['time']}")
            st.write(step['desc'])
        st.write("")

    st.divider()
    st.subheader("📥 Exportation Professionnelle")
    ex1, ex2, ex3 = st.columns(3)
    
    with ex1:
        # Word
        doc = Document()
        doc.add_heading("SmartDoc Nomadia", 0)
        for s in st.session_state.steps:
            doc.add_heading(s['title'], level=1)
            doc.add_paragraph(s['desc'])
            if s['img']: doc.add_picture(s['img'], width=Inches(4))
        doc_p = "doc.docx"
        doc.save(doc_p)
        st.download_button("📂 Export Word (.docx)", open(doc_p,"rb"), "Guide_Nomadia.docx")

    with ex2:
        # Confluence
        conf = "h1. Guide Nomadia\n"
        for s in st.session_state.steps: conf += f"h3. {s['title']}\n{s['desc']}\n\n"
        st.download_button("🔵 Export Confluence", conf, "confluence.txt")

    with ex3:
        # PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "NOMADIA SMARTDOC", ln=True)
        pdf.set_font("Arial", size=10)
        for s in st.session_state.steps:
            pdf.ln(5)
            pdf.multi_cell(0, 10, f"{s['title']} : {s['desc']}")
        pdf_p = "doc.pdf"
        pdf.output(pdf_p)
        st.download_button("📕 Export PDF", open(pdf_p,"rb"), "Guide_Nomadia.pdf")
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- UI : FOOTER CARDS ---
else:
    st.write("")
    f1, f2, f3 = st.columns(3)
    with f1:
        st.markdown('<div class="card"><div class="card-num">01</div><div class="card-title">Capture Vidéo</div><div class="card-text">Enregistrez vos manipulations ou votre écran directement.</div></div>', unsafe_allow_html=True)
    with f2:
        st.markdown('<div class="card"><div class="card-num">02</div><div class="card-title">Intelligence IA</div><div class="card-text">L\'IA Nomadia analyse les flux et génère la structure technique.</div></div>', unsafe_allow_html=True)
    with f3:
        st.markdown('<div class="card"><div class="card-num">03</div><div class="card-title">Export Pro</div><div class="card-text">Générez votre documentation brandée Nomadia en un clic.</div></div>', unsafe_allow_html=True)
