import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import json
import folium
from streamlit_folium import st_folium
from fpdf import FPDF
import datetime
import re

# --- PAGE SETUP ---
st.set_page_config(
    page_title="360° Forensic Property & Risk Audit Protocol (v6.0)", 
    layout="wide", 
    page_icon="🏛️"
)

# Initialize Gemini Client via Streamlit Secrets
api_key = st.secrets.get("GEMINI_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)
    has_model = True
else:
    has_model = False

# Self-Healing Dynamic Model Discovery Content Generator
def generate_ai_content(prompt, contents=None):
    if not api_key:
        raise Exception("GEMINI_API_KEY is missing from your Streamlit Secrets. Please add it to your Streamlit App settings.")
        
    discovered_models = []
    try:
        for m in genai.list_models():
            if "generateContent" in m.supported_methods:
                clean_name = m.name.replace("models/", "")
                discovered_models.append(clean_name)
    except Exception:
        discovered_models = [
            "gemini-1.5-flash", 
            "gemini-1.5-flash-latest", 
            "gemini-1.5-pro", 
            "gemini-1.5-pro-latest",
            "gemini-pro"
        ]
        
    preferred = [m for m in discovered_models if "1.5-flash" in m or m == "gemini-1.5-flash"]
    preferred += [m for m in discovered_models if "1.5-pro" in m or m == "gemini-1.5-pro"]
    preferred += [m for m in discovered_models if m not in preferred]
    
    if not preferred:
        preferred = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
        
    errors = []
    for model_name in preferred:
        try:
            model = genai.GenerativeModel(model_name)
            if contents:
                if isinstance(contents, list):
                    response = model.generate_content([prompt] + contents)
                else:
                    response = model.generate_content([prompt, contents])
            else:
                response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            err_msg = str(e)
            errors.append(f"🔴 **{model_name} failed:** {err_msg}")
            if "API_KEY_INVALID" in err_msg or "API key not valid" in err_msg or "403" in err_msg:
                raise Exception(f"API Key / Authentication Issue: {err_msg}")
            continue
            
    raise Exception("All models failed to respond. Details:\n\n" + "\n\n".join(errors))

# PDF Text-cleaning helper to prevent Latin-1 encoding crashes in FPDF
def clean_pdf_text(text):
    replacements = {
        "€": "EUR ", "²": " sqm", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", "•": "*",
        "🏡": "", "📊": "", "📋": "", "👁️": "", "📄": "", "🎯": "", "🏆": "", "🕵️‍♂️": "", "🗺️": "", "🚩": "",
        "🟢": "[Habitable] ", "🔴": "[Unhabitable] ", "🟡": "[Attention] ", "🔵": "[Water Hazard] ",
        "⚠️": "Warning: ", "🎉": "Exempt: "
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

# PDF Exporter function
def generate_pdf_bytes(report_text, address):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    
    pdf.set_font("Helvetica", style="B", size=15)
    pdf.cell(0, 10, "360 Forensic Property & Comprehensive Risk Audit", ln=True, align="C")
    pdf.set_font("Helvetica", size=9)
    pdf.cell(0, 6, f"Property: {address}", ln=True, align="C")
    pdf.cell(0, 6, f"Report Generated: {datetime.date.today().strftime('%B %d, %Y')}", ln=True, align="C")
    pdf.ln(8)
    
    cleaned_text = clean_pdf_text(report_text)
    for line in cleaned_text.split("\n"):
        if not line.strip():
            pdf.ln(3)
        elif line.strip().startswith("###"):
            pdf.set_font("Helvetica", style="B", size=11)
            pdf.multi_cell(0, 6, txt=line.replace("###", "").strip())
            pdf.set_font("Helvetica", size=9)
        elif line.strip().startswith("##") or line.strip().startswith("#"):
            pdf.set_font("Helvetica", style="B", size=13)
            pdf.ln(4)
            pdf.multi_cell(0, 7, txt=line.replace("##", "").replace("#", "").strip())
            pdf.set_font("Helvetica", size=9)
        else:
            pdf.multi_cell(0, 5, txt=line)
            
    return pdf.output()

st.title("🏛️ 360° Forensic Property & Comprehensive Risk Audit")
st.markdown("**Executive Acquisition & Structural Advisory System (v6.0) — Dublin Residential Market**")
st.markdown("---")

if "audit_report" not in st.session_state:
    st.session_state.audit_report = None

# --- TWO-COLUMN INTERFACE ---
col_inputs, col_output = st.columns(2)

with col_inputs:
    st.header("📥 Minimalist Acquisition Inputs")
    st.caption("Paste the property URL and optionally attach files; AI will extract, calculate, and populate all output specs.")
    
    daft_url = st.text_input("Daft.ie / MyHome.ie Listing URL", value="https://www.daft.ie/for-sale/12-connolly-gardens-inchicore-dublin-8/6655188")
    
    st.markdown("---")
    st.header("📄 Official Documents Upload")
    ber_pdf = st.file_uploader("Upload Official SEAI BER Report (PDF) [Optional]", type=["pdf"])
    
    st.markdown("---")
    st.header("🛠️ Planned Custom Renovations")
    uploaded_structural_photo = st.file_uploader("Upload Wall Photo, Architectural Floorplan, or Sketch for Custom Works [Optional]", type=["jpg", "png", "jpeg"])
    custom_work_description = st.text_input("Custom Work Description", placeholder="e.g. Knock down wall between kitchen and dining to install RSJ beam and custom crittall partition")
    
    st.markdown("---")
    st.header("💰 Buyer Parameters")
    budget_max = st.number_input("Max Budget Ceiling (€)", min_value=100000, value=750000, step=10000)
    target_ber = st.selectbox("Target Mortgage Tier", ["AIB Green Mortgage (B3 or better)", "Standard Mortgage (Any BER)", "Net-Zero A-Rating Target"])
    
    st.markdown("---")
    run_audit_btn = st.button("🚀 Run 360° Forensic Audit Protocol (v6.0)", type="primary", use_container_width=True)

# --- AUDIT EXECUTION ---
with col_output:
    st.header("📋 Forensic Audit & Strategic Acquisition Report")
    
    tab_report, tab_map = st.tabs(["📄 Full Audit Report", "🗺️ Spatial & Planning Map"])
    
    # Defaults
    map_lat, map_lon = 53.3498, -6.2603
    is_d08, is_d14 = False, False
    extracted_address = "Dublin property"
    
    with tab_report:
        if run_audit_btn:
            if not has_model and not api_key:
                st.error("⚠️ GEMINI_API_KEY is not configured in Streamlit Secrets.")
            else:
                with st.spinner("AI parsing listing, analyzing files, and generating comprehensive report..."):
                    try:
                        content_payload = []
                        if ber_pdf is not None:
                            ber_pdf.seek(0)
                            content_payload.append({"mime_type": "application/pdf", "data": ber_pdf.read()})
                        if uploaded_structural_photo is not None:
                            uploaded_structural_photo.seek(0)
                            content_payload.append(Image.open(uploaded_structural_photo))
                            
                        # Highly robust un-formatted raw string template to guarantee zero syntax crashes
                        master_prompt_template = """
                        You are the Lead Forensic Building Surveyor, Real Estate Acquisition Strategist, and Structural/Legal Risk Auditor for residential purchases in Dublin, Ireland.
                        
                        Given only the property URL: {URL}, perform web grounding to parse, extract, and analyze the property. 
                        
                        ### CLIENT SPECIFIC ACQUISITION PARAMETERS:
                        - **Max Buyer Budget:** EUR {BUDGET}
                        - **Mortgage Target:** {TARGET_MORTGAGE}
                        - **Custom Renovation Requested:** "{CUSTOM_RENOVATION}"
                        
                        Generate the complete, unedited, ultra-detailed **360° FORENSIC PROPERTY & COMPREHENSIVE RISK AUDIT (v6.0)** report. Include the following sections and structural tables:
                        
                        ### 🏡 DYNAMIC PROPERTY CARD (Extract and Display First):
                        - **Property Address** (Extracted from Daft/MyHome listing)
                        - **Eircode** (Identify precisely based on location / search, or default to D08 F5P6 if Inchicore, D14 if Roebuck)
                        - **Asking Price** (Extracted from Daft/MyHome listing)
                        - **Certified Habitable Size (sqm)** (Extracted from Daft/MyHome listing or BER)
                        - **Current BER Rating** (Extracted from Daft/MyHome listing or parsed BER PDF if attached)
                        - **Year of Construction** (Extract or estimate based on era, e.g. 1950)
                        
                        ---
                        ### AUDIT SECTIONS REQUIRED:
                        
                        1. **EXECUTIVE SUMMARY & STRUCTURAL WORK ASSESSMENT:**
                           - DIRECTLY analyze the custom work inquiry ("{CUSTOM_RENOVATION}"). Inspect the attached image if provided.
                           - Provide estimated structural engineering specs, RSJ steel beam requirement, and estimated cost range in EUR.
                           
                        2. **SECTION 1: HYPER-LOCAL CMA, BER-INDEXED VALUATION & BIDDING CEILING:**
                           - Area €/m² segmented by BER Performance Tiers (Tier 1: Turnkey Green A1-B3, Tier 2: C1-C3, Tier 3: D1-G).
                           - Typology micro-adjustments (e.g. End-of-Terrace side-access premium).
                           - **The "True Sold €/m²" Comparative Matrix Table:** Render a structured Markdown table comparing the target property against at least 2 real/representative adjacent street sales from the Property Price Register (PPR), adjusted with CSO index multipliers ("In Today's Money"), true m², and adjusted €/m².
                           - **Underquote & Strategy Detection:** Quantify if the asking price is an underquote compared to neighboring sales.
                           - Provide **Fair Market Value**, **Aggressive Opening Bid**, and **Strict Walk-Away Ceiling** (Ensure this ceiling subtracts the custom works estimate and energy retrofit net costs).
                           
                        3. **SECTION 2: PHOTOGRAPHIC FORENSICS & VISUAL DEFECT RADAR:**
                           - Identify visual risks (box rooms < 7sqm, fuse board types, signs of damp/condensation).
                           
                        4. **SECTION 3: ERA-SPECIFIC FABRIC, RETROFIT PATHWAYS & COSTING:**
                           - Era Construction Profile (fabric, solid concrete/cavity wall, acoustic separation).
               
