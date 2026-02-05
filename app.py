import streamlit as st
import google.generativeai as genai
import os
import tempfile
import time
from docx import Document

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Modop Studio by Nomadia", page_icon="🛰️", layout="wide")

# --- DESIGN NOMADIA ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    .stApp { background-color: #FFFFFF; color: #002344; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #002344; }
    [data-testid="stSidebar"] * { color: white !important; }
    h1, h2, h3 { color: #002344 !important; font-weight: 700 !important; }
    .stButton>button { background: #00D2B4; color: white !important; border-radius: 8px; border: none; font-weight: 600; padding: 0.6rem 1.5rem; width: 100%; }
    .stButton>button:hover { background-color: #00B5A0; color: white !important; }
    .output-box { background-color: #F8FAFC; padding: 25px; border-radius: 12px; border: 1px solid #E2E8F0; color: #002344; }
    </style>
    """, unsafe_allow_html=True)

# --- API ---
api_key = st.sidebar.text_input("🔑 Clé API Gemini", type="password", value=st.secrets.get("GEMINI_API_KEY", ""))

if api_key:
    genai.configure(api_key=api_key)
else:
    st.info("Veuillez saisir votre clé API Gemini.")
    st.stop()

# --- HEADER ---
st.markdown("<h1 style='margin-bottom: 0;'>Modop <span style='color:#00D2B4'>Studio</span></h1>", unsafe_allow_html=True)
st.divider()

col1, col2 = st.columns([0.45, 0.55], gap="large")

with col1:
    st.subheader("📽️ Source Vidéo")
    uploaded_file = st.file_uploader("Déposez votre vidéo", type=['mp4', 'mov'])
    
    if uploaded_file:
        st.video(uploaded_file)
        
        if st.button("Lancer la rédaction"):
            status_zone = st.empty()
            
            try:
                # --- DETECTION DYNAMIQUE DU MODELE ---
                # On cherche un modèle qui supporte la vidéo et le contenu
                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                # On essaie de trouver flash dans la liste, sinon on prend le premier
                target = next((m for m in models if 'flash' in m), models[0])
                status_zone.info(f"Connexion établie avec : {target}")

                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tfile:
                    tfile.write(uploaded_file.read())
                    video_path = tfile.name

                myfile = genai.upload_file(path=video_path)
                
                with st.spinner("Analyse en cours..."):
                    while myfile.state.name == "PROCESSING":
                        time.sleep(5)
                        myfile = genai.get_file(myfile.name)
                    
                    if myfile.state.name == "ACTIVE":
                        # Utilisation du nom exact renvoyé par Google
                        model = genai.GenerativeModel(target)
                        prompt = "Analyse cette vidéo technique et rédige un mode opératoire en Markdown : Titre, Introduction, Tableau des étapes (Action | Timestamp), Points de vigilance."
                        
                        response = model.generate_content([prompt, myfile])
                        st.session_state.modop_text = response.text
                        status_zone.empty()
                    else:
                        st.error(f"Erreur d'activation : {myfile.state.name}")

                os.remove(video_path)
                
            except Exception as e:
                st.error(f"Erreur : {str(e)}")

with col2:
    st.subheader("📄 Guide Rédigé")
    if 'modop_text' in st.session_state:
        st.markdown(f'<div class="output-box">{st.session_state.modop_text}</div>', unsafe_allow_html=True)
        
        doc = Document()
        doc.add_heading('Mode Opératoire - Nomadia', 0)
        doc.add_paragraph(st.session_state.modop_text)
        doc_path = "export_modop.docx"
        doc.save(doc_path)
        
        st.divider()
        with open(doc_path, "rb") as f:
            st.download_button("💾 Télécharger Word", f, "Modop_Nomadia.docx")
    else:
        st.write("Le guide apparaîtra ici.")
