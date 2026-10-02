import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import json

# --- PAGE SETUP ---
st.set_page_config(page_title="Dublin Property Forensics & Audit", layout="wide", page_icon="🏡")

# Initialize Gemini Client via Streamlit Secrets
api_key = st.secrets.get("GEMINI_API_KEY", "")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

st.title("🏡 Dublin Property Forensics & Comprehensive Retrofit Audit")
st.markdown("Automate property analysis, inspect images/BER documents, and compute precise pathways to **B3** and **A** ratings.")
st.markdown("---")

# Session State for Dynamic Custom Works
if "custom_works" not in st.session_state:
    st.session_state.custom_works = []

# --- LEFT COLUMN: DATA INGESTION & AUDIT INPUTS ---
col_input, col_audit = st.columns()

with col_input:
    st.header("1. Property Identifiers")
    daft_url = st.text_input("Daft.ie / MyHome Listing URL", placeholder="https://www.daft.ie/for-sale/...")
    eircode = st.text_input("Eircode", value="D14 F8H3")
    asking_price = st.number_input("Asking Price (€)", min_value=50000, value=650000, step=10000)
    floor_area = st.number_input("Floor Area (m²)", min_value=20, value=85, step=5)
    
    st.markdown("---")
    st.header("2. BER Certificate Analysis")
    ber_pdf = st.file_uploader("Upload Official SEAI BER PDF", type=["pdf"])
    
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
    with st.expander("➕ Add Custom Non-Energy Renovations", expanded=True):
        new_work_name = st.text_input("Work Description", placeholder="e.g. Knock down kitchen wall & install steel beam")
        col_w1, col_w2 = st.columns(2)
        new_work_cost = col_w1.number_input("Estimated Cost (€)", min_value=0, value=5000, step=500)
        causes_delay = col_w2.checkbox("Requires Vacating House?", value=False)
        
        if st.button("Add Work Item"):
            if new_work_name:
                st.session_state.custom_works.append({
                    "name": new_work_name,
                    "cost": new_work_cost,
                    "vacate": causes_delay
                })
                st.rerun()

    if st.session_state.custom_works:
        st.write("**Current Custom Works List:**")
        for idx, item in enumerate(st.session_state.custom_works):
            st.caption(f"• **{item['name']}** — €{item['cost']:,} ({'Unhabitable during work' if item['vacate'] else 'Habitable'})")
        if st.button("Clear Custom Works"):
            st.session_state.custom_works = []
            st.rerun()

    st.markdown("---")
    st.header("5. Visual Forensics Media")
    uploaded_photo = st.file_uploader("Upload Inspection Photo (Fuse box, damp, walls, cracks)", type=["jpg", "png", "jpeg"])

# --- COMPUTATION & ROADMAP LOGIC ---
def calculate_pathways(current_rating, area):
    # Pathway to B3 (Green Mortgage target: <= 125 kWh/m2/yr)
    b3_steps = [
        {"measure": "Attic Insulation (300mm quilt)", "gross": 2200, "grant": 1500, "net": 700, "note": "Low disruption, high heat retention"},
        {"measure": "Heat Pump System with Radiator Upgrades", "gross": 14000, "grant": 6500, "net": 7500, "note": "Replaces oil/gas boiler; requires HLI check"},
        {"measure": "Demand Controlled Ventilation (DCV)", "gross": 3800, "grant": 1500, "net": 2300, "note": "Eliminates condensation & manages fresh air"}
    ]
    
    # Pathway to A2/A3 (Maximum Value & Net Zero: <= 50 kWh/m2/yr)
    a_steps = b3_steps + [
        {"measure": "External Wall Insulation (EWI) 100mm EPS", "gross": 18000, "grant": 8000, "net": 10000, "note": "Eliminates all exterior thermal bridging"},
        {"measure": "Solar PV (4kWp system + 5kWh battery)", "gross": 8500, "grant": 2100, "net": 6400, "note": "Offsets electrical loads and heat pump running cost"},
        {"measure": "High Performance Triple Glazing", "gross": 12000, "grant": 0, "net": 12000, "note": "Acoustic insulation + U-value < 0.8 W/m²K"}
    ]
    return b3_steps, a_steps

b3_path, a_path = calculate_pathways(current_ber, floor_area)

# Compute custom works totals
custom_cost_total = sum(item["cost"] for item in st.session_state.custom_works)
any_custom_unhabitable = any(item["vacate"] for item in st.session_state.custom_works)

# Grant lookups for selected standard works
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

# Habitability
is_unhabitable = (
    "Internal Dry-Lining (IWI)" in standard_works or 
    any_custom_unhabitable
)

# Valuation Projections (4% CAGR baseline + 11% B3+ Green Premium)
cagr = 0.04
resale_3yr = (asking_price + total_out_of_pocket) * ((1 + cagr) ** 3) * 1.11
resale_5yr = (asking_price + total_out_of_pocket) * ((1 + cagr) ** 5) * 1.11

# --- RIGHT COLUMN: COMPREHENSIVE AUDIT REPORT ---
with col_audit:
    st.header("📋 Comprehensive Audit & Retrofit Blueprint")
    
    tab_report, tab_b3, tab_a, tab_vision = st.tabs([
        "📄 Full Audit Report", 
        "🎯 Roadmap to B3", 
        "🏆 Roadmap to A-Rating", 
        "👁️ Visual Forensics"
    ])
    
    with tab_report:
        st.subheader("Executive Audit Summary")
        if daft_url:
            st.caption(f"Target Listing: [{daft_url}]({daft_url})")
            
        m1, m2, m3 = st.columns(3)
        m1.metric("Current Asking Baseline", f"€{asking_price:,}")
        m2.metric("Net Works Budget", f"€{total_out_of_pocket:,}")
        m3.metric("Projected 5-Yr Resale", f"€{int(resale_5yr):,}")
        
        st.markdown("#### 1. Financial Breakdown")
        fin_data = [
            {"Category": "Standard Energy Retrofit (Gross)", "Amount (€)": f"€{selected_gross:,}"},
            {"Category": "SEAI Grant Subsidies (Deductions)", "Amount (€)": f"-€{selected_grants:,}"},
            {"Category": "Custom Desired Works (Net)", "Amount (€)": f"€{custom_cost_total:,}"},
            {"Category": "Total Out-of-Pocket Capital Required", "Amount (€)": f"€{total_out_of_pocket:,}"}
        ]
        st.table(pd.DataFrame(fin_data))
        
        st.markdown("#### 2. Habitability & Timeline Projection")
        if is_unhabitable:
            st.error("🔴 **Status: Property Unhabitable During Major Works**")
            st.markdown("- **Estimated Delay:** 8–12 weeks before move-in.")
            st.markdown("- **Drivers:** Wall dry-lining or custom invasive structural renovations selected.")
        else:
            st.success("🟢 **Status: Habitable on Day 1 (Phased External Works)**")
            st.markdown("- Works can be carried out externally (Heat Pump, Solar PV, EWI) while residing in the home.")

    with tab_b3:
        st.subheader("🎯 Minimum Retrofit Roadmap to B3 (Green Mortgage Tier)")
        st.info("💡 Achieving **B3** unlocks green mortgage rates (~0.50% to 0.75% interest discount) and provides the best return on investment.")
        
        b3_df = pd.DataFrame(b3_path)
        b3_df.columns = ["Recommended Measure", "Gross (€)", "SEAI Grant (€)", "Net (€)", "Technical Specification"]
        st.dataframe(b3_df, use_container_width=True)
        
        total_b3_net = sum(item["net"] for item in b3_path)
        st.markdown(f"**Total Net Cost to Achieve B3:** `€{total_b3_net:,}`")

    with tab_a:
        st.subheader("🏆 Deep Retrofit Roadmap to A2/A3 (Net Zero Standard)")
        st.info("💡 An **A-Rating** delivers maximum market resilience, eliminates fossil fuels, and commands an additional 10–14% resale premium in Dublin.")
        
        a_df = pd.DataFrame(a_path)
        a_df.columns = ["Recommended Measure", "Gross (€)", "SEAI Grant (€)", "Net (€)", "Technical Specification"]
        st.dataframe(a_df, use_container_width=True)
        
        total_a_net = sum(item["net"] for item in a_path)
        st.markdown(f"**Total Net Cost to Achieve A-Rating:** `€{total_a_net:,}`")

    with tab_vision:
        st.subheader("👁️ AI Visual Risk & Forensic Inspection")
        if uploaded_photo and model:
            img = Image.open(uploaded_photo)
            st.image(img, caption="Inspection Media", use_container_width=True)
            if st.button("Run Forensic Vision Analysis"):
                with st.spinner("Analyzing building conditions via Gemini 1.5 Flash..."):
                    v_prompt = """
                    Act as an expert building surveyor in Dublin. Inspect this residential property image:
                    1. Identify risks: damp marks, stepped structural cracking, outdated wiring/fuse boards, or cosmetic flips masking defects.
                    2. Estimate remedial costs in EUR.
                    3. Highlight if this defect interferes with reaching BER B3 or A rating.
                    """
                    v_res = model.generate_content([v_prompt, img])
                    st.markdown(v_res.text)
        elif not model:
            st.warning("Add your free Gemini API key to Streamlit secrets to run live vision checks.")
        else:
            st.caption("Upload a photo in section 5 to trigger forensic visual checks.")
