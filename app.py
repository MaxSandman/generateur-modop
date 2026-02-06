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

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Nomadia SmartDoc", page_icon="⚡", layout="wide")

# --- DESIGN SYSTEM NOMADIA ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    .stApp { background-color: #F8FAFC; font-family: 'Inter', sans-serif; }
    
    .nomadia-header { 
        text-align: center; font-size: 40px; font-weight: 800; color: #0B192E; 
        margin-top: 20px; text-transform: uppercase; letter-spacing: -1px;
    }
    .highlight { color: #A3E671; }
    .subtitle { color: #64748B; text-align: center; font-size: 16px; margin-bottom: 30px; }

    /* WORKFLOW STEPPER */
    .stepper-container {
        display: flex; justify-content: space-between; margin-bottom: 40px; 
        padding: 0 50px; position: relative;
    }
    .step {
        background: white; border: 2px solid #E2E8F0; color: #64748B;
        padding: 10px 20px; border-radius: 50px; font-weight: bold; font-size: 14px;
        z-index: 2; width: 30%; text-align: center;
    }
    .step.active {
        border-color: #A3E671; background-color: #F0FDF4; color: #0B192E; box-shadow: 0 4px 6px rgba(163, 230, 113, 0.1);
    }
    .step-line {
        position: absolute; top: 50%; left: 10%; right: 10%; height: 2px; background: #E2E8F0; z-index: 1; transform: translateY(-50%);
    }

    /* ZONES */
    .zone-card {
        background-color: white; border-radius: 15px; padding: 30px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.03); border: 1px solid #E2E8F0; margin-
