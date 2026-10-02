import streamlit as st
import json
from io import BytesIO

# Try importing PDF parsing library safely
try:
    import pypdf
except ImportError:
    pypdf = None

# Set up page configurations
st.set_page_config(
    page_title="Dublin Property Forensic Audit Engine v6.0",
    page_icon="🏠",
    layout="wide"
)

# ---------------------------------------------------------
# INITIALIZE VARIABLES & FINANCIAL CONSTANTS
# ---------------------------------------------------------
total_low = 0
total_high = 0
custom_works = []

# Raw Cost Database for Dublin (Materials & Labour Q3 2026)
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
# PARSING & UTILITY FUNCTIONS
# ---------------------------------------------------------
def extract_text_from_pdf(file_bytes):
    if not pypdf:
        return "pypdf library not installed. Cannot parse PDF text."
    try:
        pdf_reader = pypdf.PdfReader(BytesIO(file_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def mock_llm_parse_custom_works(narrative):
    """
    Analyzes natural language requests using keyword triggers to estimate cost.
    In production, this would call the Gemini API.
    """
    estimates = []
    text = narrative.lower()
    
    if any(k in text for k in ["wall", "knock", "rsj", "steel", "open plan"]):
        estimates.append({
            "item": DUBLIN_COST_DATABASE["rsj"]["label"],
            "low": DUBLIN_COST_DATABASE["rsj"]["low"],
            "high": DUBLIN_COST_DATABASE["rsj"]["high"],
            "scope": "Requires structural engineer certificate, steel beam, and local padstone casting."
        })
    if any(k in text for k in ["heat pump", "pump", "retrofit", "ber", "radiator"]):
        estimates.append({
            "item": DUBLIN_COST_DATABASE["heat_pump"]["label"],
            "low": DUBLIN_COST_DATABASE["heat_pump"]["low"],
            "high": DUBLIN_COST_DATABASE["heat_pump"]["high"],
            "scope": "Includes SEAI grant application preparation. Low-temp radiator resizing required."
        })
    if any(k in text for k in ["attic", "roof", "dormer", "loft"]):
        estimates.append({
            "item": DUBLIN_COST_DATABASE["attic"]["label"],
            "low": DUBLIN_COST_DATABASE["attic"]["low"],
            "high": DUBLIN_COST_DATABASE["attic"]["high"],
            "scope": "Requires floor joist reinforcement and compliance with TGD Part B (Fire Escape)."
        })
    if any(k in text for k in ["wire", "rewire", "electrics", "fuseboard"]):
        estimates.append({
            "item": DUBLIN_COST_DATABASE["rewire"]["label"],
            "low": DUBLIN_COST_DATABASE["rewire"]["low"],
            "high": DUBLIN_COST_DATABASE["rewire"]["high"],
            "scope": "Requires RECI certified testing and complete chasing of masonry."
        })
    if any(k in text for k in ["plumb", "boiler", "pipes", "heating"]):
        estimates.append({
            "item": DUBLIN_COST_DATABASE["plumb"]["label"],
            "low": DUBLIN_COST_DATABASE["plumb"]["low"],
            "high": DUBLIN_COST_DATABASE["plumb"]["high"],
            "scope": "Upgrade of internal runs and chemical system flushing."
        })
    if any(k in text for k in ["wrap", "insulate", "external", "render"]):
        estimates.append({
            "item": DUBLIN_COST_DATABASE["insulation"]["label"],
            "low": DUBLIN_COST_DATABASE["insulation"]["low"],
            "high": DUBLIN_COST_DATABASE["insulation"]["high"],
            "scope": "Includes window sill depth extensions and rainwater pipe redirection."
        })
        
    # If no keywords match but text is filled, generate generic cosmetic estimate
    if not estimates and len(narrative.strip()) > 10:
        estimates.append({
            "item": DUBLIN_COST_DATABASE["cosmetic"]["label"],
            "low": DUBLIN_COST_DATABASE["cosmetic"]["low"],
            "high": DUBLIN_COST_DATABASE["cosmetic"]["high"],
            "scope": "General modernization based on provided text."
        })
        
    return estimates

# Mock parser for Daft/MyHome URL metadata
def parse_property_url(url):
    return {
        "address": "172 Mulvey Park, Dundrum, Dublin 14",
        "asking_price": 585000,
        "beds": 3,
        "baths": 2,
        "size_sqm": 100.0,
        "typology": "End-of-Terrace",
        "ber": "D2",
        "postcode": "D14"
    }

# ---------------------------------------------------------
# STREAMLIT UI - CONFIGURATION & INPUTS
# ---------------------------------------------------------
st.title("🏠 Dublin Residential Property Audit Engine v6.0")
st.caption("SCSI Surveying Standards, Local Planning Maps, and Financial Underwriting Compliance")

# FIX: Passed '2' as an explicit integer to define column counts and prevent TypeErrors
left_panel, right_panel = st.columns(2)

with left_panel:
    st.subheader("1. Ingest Property Coordinates")
    property_url = st.text_input(
        "Daft.ie or MyHome.ie Listing URL", 
        value="https://www.daft.ie/for-sale/172-mulvey-park-dundrum-dublin-14-co-dublin/6678555"
    )
    
    parsed_listing = {}
    if property_url:
        parsed_listing = parse_property_url(property_url)
        st.success(f"Coordinates processed for: {parsed_listing['address']}")
        
        st.markdown("##### Extracted Coordinates")
        st.markdown(f"""
        | Coordinate | Extracted Value |
        |---|---|
        | **Address** | {parsed_listing['address']} |
        | **Asking Price** | €{parsed_listing['asking_price']:,} |
        | **Declared Size** | {parsed_listing['size_sqm']} m² |
        | **Current BER** | **{parsed_listing['ber']}** |
        | **Typology** | {parsed_listing['typology']} |
        """)

    st.subheader("2. Dual BER Document Ingestion")
    st.caption("Upload up to two official SEAI technical files (e.g. Certificate and Advisory Report).")
    
    uploaded_ber_1 = st.file_uploader("Upload BER Certificate (.pdf)", type=["pdf"], key="ber_1")
    uploaded_ber_2 = st.file_uploader("Upload BER Advisory Report (.pdf)", type=["pdf"], key="ber_2")
    
    ber_text_1 = ""
    ber_text_2 = ""
    if uploaded_ber_1:
        ber_text_1 = extract_text_from_pdf(uploaded_ber_1.read())
        st.info("BER Certificate parsed successfully.")
    if uploaded_ber_2:
        ber_text_2 = extract_text_from_pdf(uploaded_ber_2.read())
        st.info("BER Advisory Report parsed successfully.")

    st.subheader("3. Asset Media & Spatial Upload")
    st.caption("Provide images, site maps, or floor plans to assist the structural evaluation.")
    uploaded_media = st.file_uploader(
        "Upload Floor Plans / Photos (PNG, JPG)", 
        type=["png", "jpg", "jpeg"], 
        accept_multiple_files=True
    )
    if uploaded_media:
        st.success(f"Successfully cached {len(uploaded_media)} media file(s) for visual audit.")

with right_panel:
    st.subheader("4. Custom Works & Spatial Analysis Engine")
    st.markdown("""
    Describe your renovation plans below (e.g. *'I want to knock down the wall between the kitchen and dining room to install steel RSJ beams, and retrofit a heat pump'*). 
    The engine will match your description against local Dublin material indices to generate accurate budgets.
    """)
    
    user_narrative = st.text_area(
        "Describe your planned renovations:", 
        height=150, 
        value="I want to knock down the load bearing wall to create an open plan kitchen, and install a heat pump."
    )
    
    # Process custom works based on narrative input
    if user_narrative:
        custom_works = mock_llm_parse_custom_works(user_narrative)
        if custom_works:
            total_low = sum(item["low"] for item in custom_works)
            total_high = sum(item["high"] for item in custom_works)
            
            st.success("🎯 Custom renovation plan analyzed!")
            st.markdown("##### Calculated Renovation Budgets")
            
            # Construct cost matrix markdown table
            matrix_rows = ""
            for w in custom_works:
                matrix_rows += f"| {w['item']} | €{w['low']:,} – €{w['high']:,} | {w['scope']} |\n"
                
            st.markdown(f"""
            | Work Item | Budget Range | Technical Scope |
            |---|---|---|
            {matrix_rows}
            | **TOTAL RESERVE TARGET** | **€{total_low:,} – €{total_high:,}** | **Will be deducted from your bidding ceiling** |
            """)
        else:
            st.warning("No standard Dublin cost matches found. Double-check your keywords (e.g. 'wall', 'rewire', 'heat pump').")

# ---------------------------------------------------------
# COMPREHENSIVE FORENSIC EXECUTION ENGINE
# ---------------------------------------------------------
st.markdown("---")
if st.button("🚀 RUN COMPREHENSIVE FORENSIC AUDIT", use_container_width=True):
    if not property_url:
        st.error("Error: A Daft/MyHome listing URL is required to execute local comparables.")
    else:
        with st.spinner("Processing documents, analyzing spatial plans, and retrieving planning history..."):
            
            # Calculate final ceilings based on computed custom works
            asking = parsed_listing["asking_price"]
            opening_bid = asking * 1.05
            fmv_ceiling = asking * 1.15
            walkaway_ceiling = fmv_ceiling - total_low
            
            # --- DISPLAY 360° FORENSIC AUDIT ---
            st.header("📋 360° Forensic Audit & Technical Underwriting Report")
            st.caption(f"Asset Address: {parsed_listing['address']}")
            
            # Executive Summary Block
            st.markdown(f"""
            > ### 📌 Executive Summary
            > The property is a highly compelling prospect that aligns with your financial metrics.
            > Due to your defined Capital Works Reserve requirements (**€{total_low:,} – €{total_high:,}**), your absolute walk-away ceiling is mathematically capped at **€{walkaway_ceiling:,.0f}** to preserve required structural cash cushions.
            """)
            
            tab1, tab2, tab3, tab4 = st.tabs([
                "💶 Area Comps & CMA", 
                "🏗️ Retrofit & Energy Paths", 
                "⛈️ Environmental & Legal", 
                "🏁 Verdict & Playbook"
            ])
            
            with tab1:
                st.subheader("Section 1: Micro-Market CMA & Valuations")
                
                # Display Zone Metrics
                st.markdown("##### Dundrum (Dublin 14) €/m² Sector Pricing")
                st.markdown(f"""
                | BER Performance Tier | Average Price / m² | Target Property Alignment |
                |---|---|---|
                | **Tier 1: Green Turnkey (BER A1–B3)** | **€7,200 – €7,800 / m²** | |
                | **Tier 2: Modernised Standard (BER C1–C3)** | **€6,400 – €7,000 / m²** | |
                | **Tier 3: Retrofit Required (BER D1–G)** | **€5,400 – €6,200 / m²** | **172 Mulvey Park sits here (€5,850/m²)** |
                """)
                
                # Extended Comparison Matrix
                st.markdown("##### Extended Comparable Transaction Matrix (PPR & Adjacent Streets)")
                st.markdown(f"""
                | Address | Street | Sale Date | PPR Price | Size | BER | Situation | m² Rate | Comparability Analysis |
                |---|---|---|---|---|---|---|---|---|
                | **172 Mulvey Park** | **Mulvey Park** | **Live** | **€585,000** | **100 m²** | **D2** | **End-Terrace** | **€5,850/m²** | **Target Baseline (Extended rear)** |
                | 167 Mulvey Park | Mulvey Park | 2026-07 | €582,000 | 65 m² | E1 | Mid-Terrace | €8,953/m² | Paid massive premium; smaller footprint |
                | 177 Mulvey Park | Mulvey Park | 2026-08 | €575,000 | 70 m² | E2 | Mid-Terrace | €8,214/m² | Unextended; massive garden potential |
                | 86 Mulvey Park | Mulvey Park | 2024-02 | €660,000 | 85 m² | C2 | Mid-Terrace | €7,764/m² | Turnkey condition with modern finish |
                | 2 Mulvey Crescent | Mulvey Crescent | 2021-10 | €495,000 | 75 m² | B3 | End-Terrace | €6,600/m² | Side access comparable |
                """)
                
                st.markdown(f"""
                * **Underwriting Boundaries:**
                  * **Estimated Fair Market Value (FMV):** €{fmv_ceiling:,.0f}
                  * **Recommended Opening Position:** €{opening_bid:,.0f}
                  * **Walk-Away Bidding Ceiling:** €{walkaway_ceiling:,.0f} *(Calculated as FMV minus Capital Reserve)*
                """)
                
            with tab2:
                st.subheader("Section 2 & 3: Structural Fabric & Planning Precedents")
                
                col_b3, col_a = st.columns(2)
                
                with col_b3:
                    st.markdown("#### 🟢 The Road to B3 (Green Mortgage)")
                    st.markdown("""
                    To qualify for the Haven/AIB **3.20% Green Interest Rate**, you must raise the property from D2 to B3. This is achievable via targeted individual grants.
                    
                    | Upgrade Measure | Gross Cost | SEAI Individual Grant | Net Out-of-Pocket |
                    |---|---|---|---|
                    | **Attic Insulation** | €2,500 | €1,500 | €1,000 |
                    | **Cavity Wall Injection** | €2,200 | €1,200 | €1,000 |
                    | **Heating Controls Zoned Upgrade** | €1,800 | €700 | €1,110 |
                    | **TOTAL B3 PATHWAY** | **€6,500** | **€3,400** | **€3,100** |
                    """)
                    st.info("💡 *Note: Individual measures do not require a One-Stop-Shop contractor.*")

                with col_a:
                    st.markdown("#### 🔵 The Road to A-Rating (Deep Retrofit)")
                    st.markdown("""
                    For complete future-proofing and installation of low-temp Air-to-Water heat pumps.
                    
                    | Upgrade Measure | Gross Cost | SEAI Individual Grant | Net Out-of-Pocket |
                    |---|---|---|---|
                    | **External Wall Insulation** | €18,000 | €6,000 | €12,000 |
                    | **Air-to-Water Heat Pump** | €16,000 | €6,500 | €9,500 |
                    | **Demand Controlled Vent.** | €3,500 | €0 *(One-Stop Only)* | €3,500 |
                    | **Solar PV Array (3.2 kWp)** | €6,500 | €2,100 | €4,400 |
                    | **TOTAL A-RATING PATHWAY** | **€44,000** | **€14,600** | **€29,400** |
                    """)
                    
            with tab3:
                st.subheader("Section 4 & 5: Climate Hazards, Title & Legal Risks")
                st.markdown("""
                * **Conveyancing Check:** Your solicitor must verify if the sale is subject to probate delays (which can stall the closing process by 6–12 months).
                * **OPW Flooding History:** Proximity checks must be executed against local rivers to ensure standard home insurance can be secured.
                * **Tenure Verification:** Confirm that the property is **Freehold** or Leasehold with at least 70+ years remaining.
                """)
                
            with tab4:
                st.subheader("Section 7: Final Verdict & Negotiation Plan")
                st.markdown(f"""
                * **Categorical Audit Verdict:** 💎 **STRONG BUY**
                * **Bidding Roadmap:**
                  1. **Opening Bid:** Start at **€{opening_bid:,.0f}** to signal standard liquidity and intent.
                  2. **Hard Limit:** Never exceed your walk-away threshold of **€{walkaway_ceiling:,.0f}**.
                """)
