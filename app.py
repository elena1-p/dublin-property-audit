import streamlit as st
import re
import json
import datetime
from io import BytesIO

# Safely import optional dependencies
try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import folium
    from streamlit_folium import st_folium
except ImportError:
    folium = None

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

# Set up page configurations
st.set_page_config(
    page_title="360° Forensic Property & Risk Audit Portal (v6.0)",
    page_icon="🏛️",
    layout="wide"
)

# Initialize Session State Report Container
if "audit_report" not in st.session_state:
    st.session_state.audit_report = ""

# ---------------------------------------------------------
# CONSTANTS & COST DATABASE (Materials & Labour Q3 2026)
# ---------------------------------------------------------
DUBLIN_COST_DATABASE = {
    "rsj": {"low": 8000, "high": 12000, "label": "Knock down load-bearing wall & Install steel RSJ"},
    "heat_pump": {"low": 16000, "high": 20000, "label": "Air-to-Water Heat Pump & Radiator retrofitting"},
    "attic": {"low": 25000, "high": 35000, "label": "Attic Dormer Conversion (Habitable standards)"},
    "rewire": {"low": 8000, "high": 12000, "label": "Full Electrical Rewiring"},
    "plumb": {"low": 6000, "high": 10000, "label": "Plumbing Upgrade & New Boiler"},
    "insulation": {"low": 12000, "high": 18000, "label": "External Wall Insulation (EWI)"},
    "cosmetic": {"low": 5000, "high": 15000, "label": "General Internal Cosmetics (Plastering/Painting)"}
}

# ---------------------------------------------------------
# UTILITY PARSING FUNCTIONS
# ---------------------------------
