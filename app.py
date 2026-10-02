import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import json

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
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

# Custom styling
st.markdown("""
<style>
    .metric-box { background-color: #f8f9fa; border-radius: 8px; padding: 15px; border-left: 5px solid #007bff; margin-bottom: 10px; }
    .verdict-strong { background-color: #d4edda; color: #155724; padding: 10px; border-radius: 5px; font-weight: bold; }
    .stButton>button { background-color: #007bff; color: white; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

st.title("🏛️ 360° Forensic Property & Comprehensive Risk Audit")
st.markdown("**Executive Acquisition & Structural Advisory System (v6.0) — Dublin Residential Market**")
st.markdown("---")

# Session state for persistent audit results and temporary estimations
if "audit_report" not in st.session_state:
    st.session_state.audit_report = None
if "custom_works" not in st.session_state:
    st.session_state.custom_works = []
if "temp_est" not in st.session_state:
    st.session_state.temp_est = None

# --- TWO-COLUMN INTERFACE ---
col_inputs, col_output = st.columns(2)

with col_inputs:
    st.header("1. Core Property & Buyer Profile")
    target_address = st.text_input("Property Address & Postal Code", value="12 Connolly Gardens, Inchicore, Dublin 8 (D08 F5P6)")
    daft_url = st.text_input("Listing URL (Daft.ie / MyHome.ie)", value="https://www.daft.ie/for-sale/12-connolly-gardens-inchicore-dublin-8/6655188")
    
    c1, c2 = st.columns(2)
    asking_price = c1.number_input("Asking Price (€)", min_value=50000, value=525000, step=5000)
    floor_area = c2.number_input("Floor Area (m²)", min_value=20.0, value=94.59, step=1.0)
    
    c3, c4 = st.columns(2)
    budget_max = c3.number_input("Max Budget Ceiling (€)", min_value=100000, value=750000, step=10000)
    target_ber = c4.selectbox("Target Mortgage Tier", ["AIB Green Mortgage (B3 or better)", "Standard Mortgage (Any BER)", "Net-Zero A-Rating Target"])
    
    st.markdown("---")
    st.header("2. BER Certificate Analysis")
    ber_pdf = st.file_uploader("Upload Official SEAI BER Report (PDF)", type=["pdf"])
    
    extracted_ber = "D1"
    energy_kwh = 245
    
    if ber_pdf is not None and model:
        with st.spinner("AI parsing official SEAI BER PDF..."):
            try:
                pdf_bytes = ber_pdf.read()
                pdf_part = {"mime_type": "application/pdf", "data": pdf_bytes}
                prompt = """
                Parse this SEAI BER PDF certificate. Return ONLY a valid JSON object with:
                {"ber_rating": "letter grade e.g. D1", "energy_kwh": numeric value in kWh/m2/yr, "dwelling_type": "string"}
                Do not include backticks or markdown formatting.
                """
                response = model.generate_content([prompt, pdf_part])
                cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
                data = json.loads(cleaned_text)
                extracted_ber = data.get("ber_rating", "D1")
                energy_kwh = float(data.get("energy_kwh", 245))
                st.success(f"Parsed: **{extracted_ber}** ({energy_kwh} kWh/m²/yr)")
            except Exception as e:
                st.error(f"Error reading PDF: {e}. Defaulting to manual selection.")
                
    ber_list = ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3", "D1", "D2", "E1", "E2", "F", "G"]
    current_ber = st.selectbox("Current BER Rating", ber_list, index=ber_list.index(extracted_ber) if extracted_ber in ber_list else 9)

    st.markdown("---")
    st.header("3. Standard Energy Retrofit Measures")
    standard_works = st.multiselect(
        "Select SEAI-eligible measures you plan to carry out:",
        ["Heat Pump System", "Solar PV (10 Panels + Inverter)", "External Wall Insulation (EWI)", "Internal Dry-Lining (IWI)", "Attic Insulation Top-up", "Triple Glazed Windows & Doors", "Demand Controlled Ventilation (DCV)"],
        default=["Heat Pump System", "Solar PV (10 Panels + Inverter)"]
    )

    st.markdown("---")
    st.header("4. Add Custom Desired Works")
    
    # 📸 Section 4 Specific Photo Uploader for structural works
    uploaded_structural_photo = st.file_uploader("Upload Wall Photo, Architectural Floorplan, or Sketch for Custom Works", type=["jpg", "png", "jpeg"])
    
    with st.expander("➕ Add Custom Non-Energy Renovations (AI Costed)", expanded=True):
        new_work_name = st.text_input("Work Description", placeholder="e.g. Knock down wall between kitchen and dining to install RSJ beam and custom crittall partition")
        
        if st.button("🤖 Ask AI to Estimate Cost & Specs", use_container_width=True):
            if not new_work_name:
                st.warning("Please enter a work description first!")
            elif not model:
                st.error("Add your free Gemini API key to Streamlit secrets to run live AI estimates.")
            else:
                with st.spinner("AI estimating cost, materials, structural engineering needs, and safety protocols..."):
                    try:
                        # Prepare payload with image if available
                        payload = []
                        if uploaded_structural_photo:
                            uploaded_structural_photo.seek(0)
                            payload.append(Image.open(uploaded_structural_photo))
                        
                        est_prompt = f"""
      
