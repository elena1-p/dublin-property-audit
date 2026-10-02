import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import json
import folium
from streamlit_folium import st_folium
from fpdf import FPDF
import datetime
import requests
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

# Initialize Session State values for auto-fill fields
if "address" not in st.session_state:
    st.session_state.address = "12 Connolly Gardens, Inchicore, Dublin 8 (D08 F5P6)"
if "eircode" not in st.session_state:
    st.session_state.eircode = "D08 F5P6"
if "price" not in st.session_state:
    st.session_state.price = 525000
if "area" not in st.session_state:
    st.session_state.area = 94.59
if "ber" not in st.session_state:
    st.session_state.ber = "B2"
if "year" not in st.session_state:
    st.session_state.year = 1950
if "audit_report" not in st.session_state:
    st.session_state.audit_report = None
if "custom_works" not in st.session_state:
    st.session_state.custom_works = []
if "temp_est" not in st.session_state:
    st.session_state.temp_est = None

# PDF Text-cleaning helper to prevent Latin-1 encoding crashes in FPDF
def clean_pdf_text(text):
    replacements = {
        "€": "EUR ",
        "²": " sqm",
        "’": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "•": "*",
        "🏡": "", "📊": "", "📋": "", "👁️": "", "📄": "",
        "🎯": "", "🏆": "", "🕵️‍♂️": "", "🗺️": "", "🚩": "",
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
    
    # Document Header
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

# --- TWO-COLUMN INTERFACE ---
col_inputs, col_output = st.columns(2)

with col_inputs:
    st.header("1. Core Property & Buyer Profile")
    
    # Daft.ie / MyHome.ie URL Prefiller Console
    daft_url = st.text_input("Listing URL (Daft.ie / MyHome.ie)", value="https://www.daft.ie/for-sale/12-connolly-gardens-inchicore-dublin-8/6655188")
    
    if st.button("🔍 Import Listing Details from URL", use_container_width=True):
        if not daft_url:
            st.warning("Please enter a valid listing URL first!")
        elif not model:
            st.error("Connect your Gemini API Key in secrets to enable automatic pre-filling.")
        else:
            with st.spinner("AI parsing and pre-filling listing details..."):
                try:
                    # Let Gemini do the parsing via web-grounding/searching
                    ref_prompt = f"""
                    You are a real estate data scraper. Extract information for this Dublin property listing: {daft_url}
                    Using search and page reading tools, identify:
                    1. Property Address (full address)
                    2. Eircode (if mentioned, otherwise predict based on location or default to Dublin 8/14 format e.g. D08 F5P6)
                    3. Price (extract numeric value, e.g. 525000)
                    4. Floor Area in sqm (extract numeric value, e.g. 94.59)
                    5. BER Rating (extract e.g. B2, C3, D1)
                    6. Year of construction (if mentioned, otherwise predict based on era or default to 1950)
                    
                    Return ONLY a raw JSON block with the following keys, no markdown wrappers:
                    {{
                      "address": "string",
                      "eircode": "string",
                      "price": 525000,
                      "area": 94.59,
                      "ber": "B2",
                      "year": 1950
                    }}
                    """
                    response = model.generate_content(ref_prompt)
                    cleaned_json = response.text.replace("```json", "").replace("```", "").strip()
                    scraped_data = json.loads(cleaned_json)
                    
                    # Store in session state to dynamically auto-fill fields
                    st.session_state.address = scraped_data.get("address", st.session_state.address)
                    st.session_state.eircode = scraped_data.get("eircode", st.session_state.eircode)
                    st.session_state.price = int(scraped_data.get("price", st.session_state.price))
                    st.session_state.area = float(scraped_data.get("area", st.session_state.area))
                    st.session_state.ber = scraped_data.get("ber", st.session_state.ber)
                    st.session_state.year = int(scraped_data.get("year", st.session_state.year))
                    
                    st.success("🎉 Pre-filled successfully! Verify the fields below.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Auto-fill failed: {e}. You can manually adjust the fields below.")

    st.markdown("---")
    # Bind fields directly to Session State to enable dynamic updates
    target_address = st.text_input("Property Address & Postal Code", value=st.session_state.address)
    eircode = st.text_input("Eircode", value=st.session_state.eircode, max_chars=8)
    
    c1, c2 = st.columns(2)
    asking_price = c1.number_input("Asking Price (€)", min_value=50000, value=st.session_state.price, step=5000)
    floor_area = c2.number_input("Floor Area (m²)", min_value=20.0, value=st.session_state.area, step=1.0)
    
    c3, c4 = st.columns(2)
    budget_max = c3.number_input("Max Budget Ceiling (€)", min_value=100000, value=750000, step=10000)
    target_ber = c4.selectbox("Target Mortgage Tier", ["AIB Green Mortgage (B3 or better)", "Standard Mortgage (Any BER)", "Net-Zero A-Rating Target"])
    
    st.markdown("---")
    st.header("2. BER Certificate Analysis")
    ber_pdf = st.file_uploader("Upload Official SEAI BER Report (PDF)", type=["pdf"])
    
    extracted_ber = st.session_state.ber
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
    
    # Restored 'construction_year' input field to resolve NameError
    construction_year = st.number_input("Year of Construction", min_value=1850, max_value=2026, value=st.session_state.year)

    st.markdown("---")
    st.header("3. Standard Energy Retrofit Measures")
    standard_works = st.multiselect(
        "Select SEAI-eligible measures you plan to carry out:",
        ["Heat Pump System", "Solar PV (10 Panels + Inverter)", "External Wall Insulation (EWI)", "Internal Dry-Lining (IWI)", "Attic Insulation Top-up", "Triple Glazed Windows & Doors", "Demand Controlled Ventilation (DCV)"],
        default=["Heat Pump System", "Solar PV (10 Panels + Inverter)"]
    )

    st.markdown("---")
    st.header("4. Add Custom Desired Works")
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
                        payload = []
                        if uploaded_structural_photo:
                            uploaded_structural_photo.seek(0)
                            payload.append(Image.open(uploaded_structural_photo))
                        
                        est_prompt = f"""
                        You are an expert Irish Structural Engineer, Quantity Surveyor, and Building Contractor.
                        Analyze the following requested work: "{new_work_name}"
                        
                        Property Context:
                        - Built Year: {construction_year}
                        - Current Area: {floor_area} m²
                        
                        Based on the uploaded image (if any), the floor plan layout, the materials needed, and current 2026 Irish building construction market rates:
                        1. Estimate the cost range in EUR (provide an integer representing the average cost, e.g., 8500).
                        2. Identify structural implications (load-bearing walls, temporary structural shoring, party wall issues).
                        3. Specify needed materials (structural steel RSJ size, double-layer plasterboard, fire-rated insulation, etc.).
                        4. Assess if the property requires vacating the house during this specific renovation.
                        
                        Return ONLY a valid JSON object with the following keys. Do not wrap in markdown or backticks:
                        {{
                          "estimated_cost": 8500,
                          "materials_and_specs": "precise materials list string",
                          "structural_implications": "structural warnings and engineering requirement description",
                          "vacate_required": true
                        }}
                        """
                        payload.append(est_prompt)
                        res = model.generate_content(payload)
                        cleaned_res = res.text.replace("```json", "").replace("```", "").strip()
                        st.session_state.temp_est = json.loads(cleaned_res)
                    except Exception as e:
                        st.error(f"Cost estimation failed: {e}")
        
        # Display AI Estimation results and offer to add
        if st.session_state.temp_est:
            est = st.session_state.temp_est
            st.info(f"💡 **AI Estimated Cost:** €{est['estimated_cost']:,}")
            st.write(f"🔧 **Structural Specs:** {est['structural_implications']}")
            st.write(f"🧱 **Materials:** {est['materials_and_specs']}")
            st.write(f"🚨 **Requires Vacating:** {'Yes' if est['vacate_required'] else 'No'}")
            
            if st.button("✅ Accept AI Cost & Add to Custom Works"):
                st.session_state.custom_works.append({
                    "name": f"{new_work_name} (AI: €{est['estimated_cost']:,})",
                    "cost": est['estimated_cost'],
                    "vacate": est['vacate_required']
                })
                st.session_state.temp_est = None  # Clear temp cache
                st.rerun()

    if st.session_state.custom_works:
        st.write("**Current Custom Works List:**")
        for idx, item in enumerate(st.session_state.custom_works):
            st.caption(f"• **{item['name']}** — €{item['cost']:,} ({'Unhabitable during work' if item['vacate'] else 'Habitable'})")
        if st.button("Clear Custom Works"):
            st.session_state.custom_works = []
            st.rerun()

    st.markdown("---")
    st.header("5. General Visual Forensics Media")
    uploaded_photo = st.file_uploader("Upload Inspection Photo (Fuse box, damp, walls, cracks)", type=["jpg", "png", "jpeg"])
    if uploaded_photo:
        st.image(uploaded_photo, caption="Media ready for AI analysis", use_container_width=True)

    st.markdown("---")
    run_audit_btn = st.button("🚀 Run 360 Forensic Audit Protocol (v6.0)", type="primary", use_container_width=True)

# --- AUDIT EXECUTION ENGINE ---
with col_output:
    st.header("📋 Forensic Audit & Strategic Acquisition Report")
    
    # Compute calculations
    custom_cost_total = sum(item["cost"] for item in st.session_state.custom_works)
    any_custom_unhabitable = any(item["vacate"] for item in st.session_state.custom_works)
    
    grant_lookup = {
        "Heat Pump System": {"gross": 14000, "grant": 6500},
        "Solar PV (10 Panels + Inverter)": {"gross": 7500, "grant": 2100},
        "External Wall Insulation (EWI)": {"gross": 18000, "grant": 8000},
        "Internal Dry-Lining (IWI)": {"gross": 12000, "grant": 4500},
        "Attic Insulation Top-up": {"gross": 2200, "grant": 1500},
        "Triple Glazed Windows & Doors": {"gross": 12000, "grant": 0},
        "Demand Controlled Ventilation (DCV)": {"gross": 3800, "grant": 1500}
    }
    
    selected_gross = sum(grant_lookup[w]["gross"] for w in standard_works)
    selected_grants = sum(grant_lookup[w]["grant"] for w in standard_works)
    selected_net = selected_gross - selected_grants
    total_out_of_pocket = selected_net + custom_cost_total
    
    # Coordinate matching logic
    map_lat, map_lon = 53.3498, -6.2603
    is_d08 = "D08" in target_address or "D08" in eircode
    is_d14 = "D14" in target_address or "D14" in eircode
    
    if is_d08:
        map_lat, map_lon = 53.3402, -6.3156
    elif is_d14:
        map_lat, map_lon = 53.2950, -6.2450

    # Display Tabs
    tab_report, tab_map = st.tabs(["📄 Full Audit Report", "🗺️ Spatial & Planning Map"])
    
    with tab_report:
        if run_audit_btn:
            if not model:
                st.error("⚠️ GEMINI_API_KEY is not configured in Streamlit Secrets.")
            else:
                with st.spinner("Executing 360 Forensic Protocol across Dublin public records..."):
                    try:
                        content_payload = []
                        if ber_pdf is not None:
                            ber_pdf.seek(0)
                            content_payload.append({"mime_type": "application/pdf", "data": ber_pdf.read()})
                        if uploaded_photo is not None:
                            uploaded_photo.seek(0)
                            content_payload.append(Image.open(uploaded_photo))
                            
                        custom_works_str = "\n".join([f"- {item['name']}: €{item['cost']}" for item in st.session_state.custom_works])
                            
                        master_prompt = f"""
                        You are the Lead Forensic Building Surveyor, Real Estate Acquisition Strategist, and Legal Risk Auditor for high-value residential property purchases in Dublin, Ireland.
                        
                        Generate the complete, unedited, ultra-detailed **360 Forensic Property & Risk Audit (v6.0)** for the target property below.
                        
                        ### TARGET PROPERTY DATA:
                        - **Address:** {target_address}
                        - **Listing URL:** {daft_url}
                        - **Asking Price:** €{asking_price:,}
                        - **Certified Habitable Size:** {floor_area} m²
                        - **Current BER Rating:** {current_ber}
                        - **Year Built:** {construction_year}
                        - **Buyer Maximum Budget:** €{budget_max:,}
                        - **Target Mortgage Standard:** {target_ber}
                        - **Standard Energy Retrofit Measures Chosen:** {", ".join(standard_works)}
                        - **Custom Works Included:**
                        {custom_works_str}
                        
                        ---
                        ### EXECUTION PROTOCOL REQUIREMENTS:
                        Write out all 8 detailed sections with the exact structure, rigorous technical reasoning, and professional tone shown below:
                        
                        1. **EXECUTIVE SUMMARY & CLIENT SPECIFIC REQUEST:**
                           - Detail structural wall solutions, steel RSJ beam sizing, engineer certification, wall thickness, glass partition install.
                           - Incorporate the custom works cost analysis, and describe spatial changes.
                           
                        2. **SECTION 1: HYPER-LOCAL CMA, BER-INDEXED VALUATION & BIDDING CEILING:**
                           - Provide Area €/m² segmented by BER Performance Tiers (Tier 1: Turnkey Green A1-B3, Tier 2: C1-C3, Tier 3: D1-G).
                           - Typology micro-adjustments (e.g. End-of-Terrace side-access premium).
                           - **The \"True Sold €/m²\" Comparative Matrix Table:** Include target baseline and at least 2 real adjacent street sales from the PPR, adjusted with CSO multipliers (\"In Today's Money\"), true m², and adjusted €/m².
                           - **Underquote & Strategy Detection:** Quantify if the asking price is an underquote compared to neighboring sales.
                           - Provide **Fair Market Value**, **Aggressive Opening Bid**, and **Strict Walk-Away Ceiling**.
                           
                        3. **SECTION 2: PHOTOGRAPHIC FORENSICS & VISUAL DEFECT RADAR:**
                           - Analyze layout footprint, room compromises (Box Room warning if bedroom < 7.0 m²), and livability checks (Ground floor guest WC, utility room).
                           - Identify visual risks (fuse board type, signs of damp/condensation).
                           
                        4. **SECTION 3: ERA-SPECRIC FABRIC, SEAI RETROFIT & STRUCTURE:**
                           - Era Construction Profile (fabric, solid concrete/cavity wall, acoustic separation).
                           - Advise on step-by-step works to bring this property from current BER {current_ber} to B3 (Green Mortgage eligibility) and to an 'A' rating (Heat pump, Solar PV, MVHR) with grants.
                           - Timeline & Habitability Audit (Habitable on Day 1 vs move-in delays).
                           
                        5. **SECTION 4: COUNCIL PLANNING, ZONING & STREET PRECEDENTS:**
                           - Unauthorised works checks (does rear extension breach the 40 m² planning exemption threshold).
                           - Mandate specific legal documents required (Certificate of Exemption from Planning).
                           
                        6. **SECTION 5: ENVIRONMENTAL, CLIMATE & INFRASTRUCTURE HAZARDS:**
                           - OPW Flood Hazard evaluation (check proximity to River Camac, Poddle, or Dodder).
                           - State the mortgage dealbreaker rule: consequences of insurance flood exclusions on bank loan drawdown.
                           - EPA Radon Risk level.
                           
                        7. **SECTION 6: TITLE, LEGAL, TENANCY & GRANTS:**
                           - Freehold vs Leasehold, restrictive covenants on front facade.
                           - Eligibility for Vacant Property Refurbishment Grant.
                           - Probate / Executor sale risks and expected closing delays.
                           
                        8. **SECTION 7: LIFESTYLE, GARDEN & COMMUTE AUDIT:**
                           - Commute analysis to Dublin Tech Hubs (Grand Canal Dock, Barrow St) and City Centre (cycling greenways, Luas Red/Green line walking times).
                           - Garden orientation, natural light solar azimuth, child/pet safety.
                           
                        9. **SECTION 8: FINAL VERDICT & NEGOTIATION ACTION PLAN:**
                           - Categorical Verdict: (STRONG BUY / CONDITIONAL BUY / WALK AWAY).
                           - Top 2-3 Dealbreakers & Red Flags.
                           - Exact Bidding Plan (Opening bid, increment strategy, strict ceiling).
                           - 3 Critical Pre-Offer Questions for the Agent and Building Surveyor.
                           
                        Format everything in clean Markdown with clear bolding and tables.
                        """
                        content_payload.append(master_prompt)
                        response = model.generate_content(content_payload)
                        st.session_state.audit_report = response.text
                    except Exception as e:
                        st.error(f"Error during audit generation: {e}")

        # Display report & download buttons
        if st.session_state.audit_report:
            st.markdown(st.session_state.audit_report)
            
            st.markdown("### 📥 Export Executive Report")
            c_dl1, c_dl2 = st.columns(2)
            
            c_dl1.download_button(
                label="📥 Download Markdown Version",
                data=st.session_state.audit_report,
                file_name="Forensic_Audit_Report.md",
                mime="text/markdown"
            )
            
            # Generate clean PDF bytes on the fly
            pdf_data = generate_pdf_bytes(st.session_state.audit_report, target_address)
            c_dl2.download_button(
                label="📕 Download Structured PDF Version",
                data=pdf_data,
                file_name="Forensic_Audit_Report.pdf",
                mime="application/pdf"
            )
        else:
            st.info("👈 Enter the property parameters on the left and click **'Run 360 Forensic Audit Protocol'** to generate your audit.")

    with tab_map:
        st.subheader("🗺️ Dynamic GIS Spatial Hazards & Planning Precedents")
        
        # PPR CSV Uploader Console
        st.markdown("### 📂 Property Price Register (PPR) Dublin Database")
        uploaded_ppr_file = st.file_uploader("Upload Dublin PPR CSV database file (from propertypriceregister.ie)", type=["csv"])
        search_query = st.text_input("Filter PPR by Street/Estate Name (e.g. Connolly Gardens, Roebuck)", value="")
        
        csv_df = None
        if uploaded_ppr_file is not None:
            try:
                # Read PPR CSV securely with robust cleaning
                raw_df = pd.read_csv(uploaded_ppr_file, encoding='latin-1')
                # Standardize column headers
                raw_df.columns = [col.strip() for col in raw_df.columns]
                
                # Match address query
                if search_query:
                    csv_df = raw_df[raw_df['Address'].astype(str).str.contains(search_query, case=False, na=False)].copy()
                else:
                    csv_df = raw_df.head(20).copy()
                
                # Format price column dynamically
                price_col = [c for col in csv_df.columns for c in [col] if 'price' in col.lower() or 'sold' in col.lower() or 'valu' in col.lower()][0]
                csv_df['PriceClean'] = csv_df[price_col].astype(str).str.replace('€', '').str.replace(',', '').str.strip().astype(float)
                
                # Extract year and apply dynamic CSO multiplier to today's money
                date_col = [c for col in csv_df.columns for c in [col] if 'date' in col.lower() or 'sale' in col.lower()][0]
                csv_df['SaleYear'] = pd.to_datetime(csv_df[date_col], errors='coerce').dt.year.fillna(2025).astype(int)
                
                cso_index = {2026: 1.0, 2025: 1.06, 2024: 1.10, 2023: 1.22, 2022: 1.24, 2021: 1.35, 2020: 1.44}
                csv_df['CSO Multiplier'] = csv_df['SaleYear'].map(cso_index).fillna(1.44)
                csv_df['In Today Money (€)'] = (csv_df['PriceClean'] * csv_df['CSO Multiplier']).astype(int)
                
                st.write(f"🎉 **Found {len(csv_df)} records matching '{search_query}':**")
                st.dataframe(csv_df[[date_col, 'Address', price_col, 'In Today Money (€)']], use_container_width=True)
            except Exception as e:
                st.error(f"Error parsing PPR CSV: {e}. Check column headers format.")
        
        st.markdown("---")
        st.write("Visualizing flood plains, infrastructure corridors, and planning precedents within 500m:")
        
        # Build Folium Map
        m = folium.Map(location=[map_lat, map_lon], zoom_start=16)
        
        # Target Property Marker
        folium.Marker(
            [map_lat, map_lon],
            popup="🎯 **Target Property**",
            tooltip="Target Baseline",
            icon=folium.Icon(color="red", icon="home")
        ).add_to(m)
        
     
