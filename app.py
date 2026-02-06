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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    .stApp { background-color: #FFFFFF; font-family: 'Inter', sans-serif; }
    
    /* Header Styles */
    .nomadia-header { 
        text-align: center; 
        font-size: 50px; 
        font-weight: 800; 
        color: #0B192E; 
        margin-bottom: 10px;
        text-transform: uppercase;
        letter-spacing: -1px;
    }
    .highlight { color: #A3E671; } /* Vert Nomadia */
    
    .subtitle { color: #64748B; text-align: center; font-size: 18px; margin-bottom: 30px; }
    
    /* Upload Box */
    .upload-container { border: 2px dashed #A3E671; border-radius: 20px; padding: 40px; text-align: center; background-color: #FDFDFD; }
    
    /* Buttons */
    .stButton>button { 
        background-color: #A3E671 !important; 
        color: #0B192E !important; 
        border: none !important; 
        border-radius: 30px !important; 
        padding: 12px 30px !important; 
        font-weight: bold !important; 
        font-size: 16px !important; 
        width: 100%;
        transition: 0.3s;
    }
    .stButton>button:hover { transform: scale(1.02); background-color: #92D460 !important; }
    
    /* Result Area */
    .result-area { background-color: #F8FAFC; border-radius: 20px; padding: 30px; margin-top: 20px; border: 1px solid #E2E8F0; }
    
    /* Progress Bar Color */
    .stProgress > div > div > div > div { background-color: #A3E671; }
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
            path = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg').name
            cv2.imwrite(path, frame)
            cap.release()
            return path
        cap.release()
    except: return None
    return None

# --- API KEY ---
api_key = st.sidebar.text_input("🔑 Clé API", type="password", value=st.secrets.get("GEMINI_API_KEY", ""))
if api_key: genai.configure(api_key=api_key)
else: st.stop()

# --- HEADER NOMADIA ---
st.markdown('<div class="nomadia-header">NOMADIA <span class="highlight">SMARTDOC</span></div>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Transformez vos démonstrations vidéos en documentation technique structurée.</p>', unsafe_allow_html=True)

# --- UPLOAD SECTION ---
uploaded_file = st.file_uploader("", type=['mp4', 'mov'], label_visibility="collapsed")

if not uploaded_file:
    st.markdown('<div class="upload-container"><h3>📂 Analysez vos manipulations</h3><p>Glissez votre vidéo ici.</p></div>', unsafe_allow_html=True)
else:
    # MODIFICATION: Vidéo cachée par défaut pour gagner de la place
    with st.expander("👁️ Voir la vidéo source (Cliquer pour déplier)"):
        st.video(uploaded_file)
    
    col_btn1, col_btn2, col_btn3 = st.columns([1,2,1])
    with col_btn2:
        start_btn = st.button("🚀 DÉMARRER L'ANALYSE")

    if start_btn:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.markdown("🔍 **Initialisation de l'IA Nomadia...**")
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target_model = next((m for m in available_models if "1.5-flash" in m), available_models[0])
            progress_bar.progress(10)

            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tfile:
                tfile.write(uploaded_file.read())
                video_path = tfile.name
            
            status_text.markdown("📤 **Envoi sécurisé vers le cloud...**")
            myfile = genai.upload_file(path=video_path)
            progress_bar.progress(30)
            
            status_text.markdown("🧠 **Analyse des actions et rédaction...**")
            while myfile.state.name == "PROCESSING":
                time.sleep(2)
                myfile = genai.get_file(myfile.name)
            
            model = genai.GenerativeModel(target_model)
            prompt = "Rédige un guide technique détaillé. Format strict par bloc : TITRE: [Nom] DESC: [Action détaillée] TIME: [MM:SS] Séparateur: ---"
            response = model.generate_content([prompt, myfile])
            progress_bar.progress(70)
            
            status_text.markdown("📸 **Extraction des captures d'écran...**")
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
            progress_bar.progress(100)
            status_text.success("✅ Documentation générée !")
            time.sleep(1)
            status_text.empty()
            progress_bar.empty()
            os.remove(video_path)
            st.rerun() # Force le rafraichissement pour afficher les résultats

        except Exception as e:
            st.error(f"Erreur : {str(e)}")

# --- RESULTATS & EXPORTS ---
if 'steps' in st.session_state:
    st.markdown('<div class="result-area">', unsafe_allow_html=True)
    st.subheader("📝 Guide Généré")
    
    for i, step in enumerate(st.session_state.steps):
        c1, c2 = st.columns([0.3, 0.7])
        with c1:
            if step['img']: st.image(step['img'], use_container_width=True,  output_format="JPEG")
        with c2:
            st.markdown(f"**Étape {i+1} : {step['title']}**")
            st.caption(f"⏱ Timestamp: {step['time']}")
            st.write(step['desc'])
        st.divider()
    
    # --- ZONE D'EXPORT ---
    st.subheader("💾 Exporter le résultat")
    
    # Préparation des fichiers en mémoire
    # 1. Word
    doc = Document()
    doc.add_heading('Nomadia SmartDoc', 0)
    for s in st.session_state.steps:
        doc.add_heading(s['title'], level=1)
        doc.add_paragraph(f"Temps : {s['time']}")
        doc.add_paragraph(s['desc'])
        if s['img']: 
            try: doc.add_picture(s['img'], width=Inches(4))
            except: pass
    doc_path = "export_nomadia.docx"
    doc.save(doc_path)

    # 2. Confluence (Texte brut + syntaxe)
    conf_text = "h1. Guide Nomadia\n\n"
    for s in st.session_state.steps:
        conf_text += f"h2. {s['title']} ({s['time']})\n{s['desc']}\n\n"

    # 3. PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "NOMADIA SMARTDOC", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=11)
    for s in st.session_state.steps:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"{s['title']} ({s['time']})", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(0, 10, s['desc'])
        pdf.ln(5)
    pdf_path = "export_nomadia.pdf"
    pdf.output(pdf_path)

    # Affichage des 3 boutons
    col_ex1, col_ex2, col_ex3 = st.columns(3)
    
    with col_ex1:
        with open(doc_path, "rb") as f:
            st.download_button("📘 Télécharger Word", f, "Guide_Nomadia.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    with col_ex2:
        st.download_button("🔵 Texte Confluence", conf_text, "Guide_Confluence.txt", mime="text/plain")

    with col_ex3:
        with open(pdf_path, "rb") as f:
            st.download_button("📕 Télécharger PDF", f, "Guide_Nomadia.pdf", mime="application/pdf")
            
    st.markdown('</div>', unsafe_allow_html=True)
