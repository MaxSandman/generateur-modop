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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
    .stApp { background-color: #FFFFFF; font-family: 'Inter', sans-serif; }
    .main-title { color: #0B192E; font-size: 50px; font-weight: 800; text-align: center; margin-bottom: 0px; }
    .highlight { color: #A3E671; }
    .subtitle { color: #64748B; text-align: center; font-size: 18px; margin-bottom: 40px; }
    .upload-container { border: 2px dashed #A3E671; border-radius: 20px; padding: 40px; text-align: center; background-color: #FDFDFD; }
    .stButton>button { background-color: #A3E671 !important; color: #0B192E !important; border: none !important; border-radius: 30px !important; padding: 15px 40px !important; font-weight: bold !important; font-size: 18px !important; display: block; margin: 0 auto; }
    .card { border: 1px solid #F0FDF4; border-radius: 20px; padding: 20px; background: white; box-shadow: 0 4px 15px rgba(0,0,0,0.05); height: 100%; }
    .card-num { color: #A3E671; font-size: 30px; font-weight: bold; }
    .card-title { color: #0B192E; font-weight: bold; font-size: 18px; margin: 10px 0; }
    .card-text { color: #64748B; font-size: 14px; }
    .result-area { background-color: #F8FAFC; border-radius: 20px; padding: 30px; margin-top: 30px; border: 1px solid #E2E8F0; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIQUE D'EXTRACTION ---
def extract_frame(video_path, timestamp_str):
    try:
        ts = timestamp_str.replace('[','').replace(']','').strip()
        parts = list(map(int, ts.split(':')))
        seconds = parts[0] * 60 + parts[1] if len(parts) == 2 else parts[0]
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
