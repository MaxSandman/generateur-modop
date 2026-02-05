import streamlit as st
import google.generativeai as genai
import cv2
import os
import tempfile
from docx import Document
from fpdf import FPDF

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Modop Studio by Nomadia",
    page_icon="🛰️",
    layout="wide"
)

# --- STYLE CSS (100% THÈME CLAIR & NOMADIA) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    /* Global - Fond clair */
    .stApp {
        background-color: #FFFFFF;
        color: #002344;
        font-family: 'Inter', sans-serif;
    }

    /* Barre latérale - Bleu Marine Professionnel */
    [data-testid="stSidebar"] {
        background-color: #002344;
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }

    /* Titres */
    h1, h2, h3 {
        color: #002344 !important;
        font-weight: 700 !important;
    }

    /* Bouton principal (Vert Nomadia) */
    .stButton>button {
        background: #00D2B4;
        color: white !important;
        border-radius: 8px;
        border: none;
        font-weight: 600;
        padding: 0.6rem 1.5rem;
        transition: 0.3s;
    }
    
    .stButton>button:hover {
        background-color: #00B5A0;
        border: none;
        color: white !important;
    }

    /* Zone de texte (Le rendu du Modop) */
    .output-box {
        background-color: #F8FAFC;
        padding: 25px;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        color: #002344;
        font-size: 15px;
    }

    /* Input et Uploader */
    .stFileUploader {
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        background-color: #F8FAFC;
    }

    /* Séparateurs */
    hr {
        border-top: 1px solid #E2E8F0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- INITIALISATION API ---
api_key = st.sidebar.text_input("🔑 Clé API Gemini", type="password", value=st.secrets.get("GEMINI_API_KEY", ""))

if not api_key:
    st.info("Veuillez saisir votre clé API Gemini dans la barre latérale pour activer le service.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- HEADER ---
st.markdown("<h1 style='margin-bottom: 0;'>Modop <span style='color:#00D2B4'>Studio</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #64748B;'>Génération automatique de documentations techniques</p>", unsafe_allow_html=True
