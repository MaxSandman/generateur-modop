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
    .stButton>button:hover { background-color: #00B5A0; color: white !important; border: none; }
    .output-box { background-color: #F8FAFC; padding: 25px; border-radius: 12px; border: 1px solid #E2E8F0; color: #002344; }
    </style>
    """, unsafe_allow_html=True)

# --- API ---
api_key = st.sidebar.text_input("🔑 Clé API Gemini", type="password", value=st.secrets.get("GEMINI_API_KEY", ""))

if not api_key:
    st.info("Veuillez saisir votre clé API Gemini dans la barre latérale.")
    st.stop()

genai.configure(api_key=api_key)

# --- HEADER ---
st.markdown("<h1 style='margin-bottom: 0;'>Modop <span style='color:#00D2B4'>Studio</span></h1>", unsafe_allow_html=True)
st.divider()

col1, col2 = st.columns([0.45, 0.55], gap="large")

with col1:
    st.subheader("📽️ Source Vidéo")
    uploaded_file = st.file_uploader("Étape 1 : Déposez votre vidéo", type=['mp4', 'mov'])
    
    if uploaded_file:
        st.video(uploaded_file)
        
        if st.button("Étape 2 : Lancer la rédaction"):
            status_zone = st.empty()
            
            try:
                # 1. Sauvegarde locale temporaire
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tfile:
                    tfile.write(uploaded_file.read())
                    video_path = tfile.name

                # 2. Upload vers Google
                status_zone.info("☁️ Envoi du fichier vers Google...")
                myfile = genai.upload_file(path=video_path)
                
                # 3. Boucle d'attente
                with st.spinner("Analyse du contenu vidéo par l'IA..."):
                    while myfile.state.name == "PROCESSING":
                        time.sleep(5)
                        myfile = genai.get_file(myfile.name)
                    
                    if myfile.state.name == "FAILED":
                        status_zone.error("Le traitement de la vidéo a échoué.")
                        st.stop()
                    
                    if myfile.state.name == "ACTIVE":
                        status_zone.success("✅ Vidéo analysée !")
                        
                        # 4. GÉNÉRATION AVEC NOM DE MODÈLE PRÉCIS
                        status_zone.info("✍️ Rédaction du mode opératoire...")
                        # Utilisation du nom de modèle complet pour éviter l'erreur 404
                        model = genai.GenerativeModel(model_name="models/gemini-1.5-flash-latest")
                        
                        prompt = "Analyse cette vidéo technique et rédige un mode opératoire clair en Markdown. Structure : Titre, Introduction, Tableau des étapes (Étape | Action | Timestamp), Points de vigilance."
                        
                        response = model.generate_content([prompt, myfile])
                        st.session_state.modop_text = response.text
                        status_zone.empty()

                os.remove(video_path)
                
            except Exception as e:
                st.error(f"Désolé, une erreur est survenue : {e}")

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
            st.download_button("💾 Télécharger le document Word", f, "Modop_Nomadia.docx")
    else:
        st.write("Le guide apparaîtra ici après l'analyse.")
