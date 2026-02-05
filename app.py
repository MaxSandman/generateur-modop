import streamlit as st
import google.generativeai as genai
import cv2
import os
from docx import Document
from fpdf import FPDF
import tempfile

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
