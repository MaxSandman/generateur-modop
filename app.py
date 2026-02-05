import streamlit as st
# ... (tes autres imports)

# --- CONFIGURATION DU DESIGN "STUDIO" ---
st.set_page_config(page_title="Gemini Modop Studio", layout="wide")

# Injection de CSS pour le look Dark Mode / Professional
st.markdown("""
    <style>
    /* Fond principal sombre */
    .stApp {
        background-color: #131314;
        color: #e3e3e3;
    }
    /* Style des zones de dépôt de fichiers */
    .stFileUploader {
        background-color: #1e1f20;
        border: 2px dashed #444746;
        border-radius: 12px;
        padding: 20px;
    }
    /* Style des boutons (plus arrondis, bleus Google) */
    .stButton>button {
        background-color: #004a77;
        color: #c2e7ff;
        border-radius: 20px;
        border: none;
        padding: 10px 25px;
    }
    /* Barre latérale plus foncée */
    [data-testid="stSidebar"] {
        background-color: #1e1f20;
    }
    </style>
    """, unsafe_allow_status=True)

st.title("✨ Gemini Modop Studio")
st.caption("L'intelligence artificielle au service de votre documentation informatique.")

st.set_page_config(page_title="IA Modop Studio", layout="wide")

st.title("🚀 Générateur de Modop Automatique")
st.info("Déposez une vidéo, l'IA rédige le guide et prépare vos fichiers Word/PDF.")

# Configuration de la clé API via la barre latérale
api_key = st.sidebar.text_input("Clé API Gemini", type="password")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    uploaded_file = st.file_uploader("Charger la vidéo de démo", type=['mp4', 'mov'])

    if uploaded_file:
        # Création d'un fichier temporaire pour la vidéo
        tfile = tempfile.NamedTemporaryFile(delete=False) 
        tfile.write(uploaded_file.read())
        
        if st.button("Analyser et Générer les documents"):
            with st.spinner("L'IA analyse la vidéo et extrait les étapes..."):
                # 1. Envoi à Gemini pour analyse
                video_file = genai.upload_file(path=tfile.name)
                prompt = "Analyse cette vidéo technique. Liste les étapes. Pour chaque étape, donne : un titre, une description courte et le timestamp en secondes (ex: 12)."
                response = model.generate_content([prompt, video_file])
                
                st.markdown("### 📝 Aperçu du Mode Opératoire")
                st.write(response.text)
                
                # Note : En version hébergée gratuite, l'extraction d'images directe 
                # peut être limitée par la puissance du serveur, mais le texte est prêt !
                
                st.success("Analyse terminée !")
                
                # Bouton de téléchargement (Exemple Word simplifié)
                doc = Document()
                doc.add_heading('Mode Opératoire', 0)
                doc.add_paragraph(response.text)
                doc.save('modop.docx')
                
                with open("modop.docx", "rb") as file:
                    st.download_button("📥 Télécharger le guide (Word)", file, "mon_modop.docx")
else:
    st.warning("Veuillez entrer votre clé API Gemini dans la barre latérale pour commencer.")
