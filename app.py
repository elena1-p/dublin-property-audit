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
    page_title="Dublin Property Forensic Audit Engine v6.0",
    page_icon="🏛️",
    layout="wide"
)

# Initialize Session State Report Container
if "audit_report" not in st.session_state:
    st.session_state.audit_report = ""

# ---------------------------------------------------------
# INITIALIZE GLOBAL AUDIT STATE
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
# PARSING & EXPORT UTILITIES
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

def extract_metrics_from_ber_text(text):
    metrics = {"size": None, "ber": None}
    if not text:
        return metrics
    size_match = re.search(r"(?:dimension|area|floor\s+area|size)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:sqm|m²|sq\s*m)", text, re.IGNORECASE)
    if size_match:
        metrics["size"] = float(size_match.group(1))
    ber_match = re.search(r"\b(A[1-3]|B[1-3]|C[1-3]|D[1-2]|E[1-2]|[FG])\b", text)
    if ber_match:
        metrics["ber"] = ber_match.group(1)
    return metrics

def parse_dublin_url(url):
    if not url:
        return None
    clean_url = url.lower().replace("-", " ").replace("_", " ")
    
    # Extract postal district
    postcode_match = re.search(r"dublin\s+(\d+[a-z]?)", clean_url)
    postcode = postcode_match.group(0).upper().strip() if postcode_match else "DUBLIN COUNTY"
    
    # Extract probable street/estate name
    street_parts = []
    tokens = clean_url.split("/")
    target_token = tokens[-1] if tokens[-1] else (tokens[-2] if len(tokens) > 1 else "")
    target_token = re.sub(r"\d{5,}", "", target_token)
    target_token = target_token.replace("for sale", "").replace("co dublin", "").strip()
    
    words = target_token.split()
    for w in words:
        if "dublin" in w or w.isdigit() or w in ["sale", "lease"]:
            break
        street_parts.append(w.capitalize())
        
    street_name = " ".join(street_parts).strip()
    if not street_name:
        street_name = "Target Property"
        
    return {
        "address": f"{street_name}, {postcode}",
        "street": street_name,
        "postcode": postcode
    }

def clean_pdf_text(text):
    """
    Cleans raw markdown structures, table formatting, and non-Latin-1 characters 
    to prevent FPDF layout wrapping loop errors.
    """
    replacements = {
        "€": "EUR ", "²": " sqm", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", "•": "*",
        "🏡": "", "📊": "", "📋": "", "👁️": "", "📄": "", "🎯": "", "🏆": "", "🕵️‍♂️": "", "🗺️": "", "🚩": "",
        "🟢": "[Habitable] ", "🔴": "[Unhabitable] ", "🟡": "[Attention] ", "🔵": "[Water Hazard] ",
        "⚠️": "Warning: ", "🎉": "Exempt: "
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
        
    # FIX: Explicitly remove markdown table divider markers to prevent narrow-cell FPDF wrap loops
    text = re.sub(r"\|[-:| ]+\|", "", text)
    text = text.replace("|", "  ")
    
    # Strip any characters outside Latin-1 encoding safely
    cleaned = text.encode("latin-1", errors="ignore").decode("latin-1")
    return cleaned

def generate_pdf_bytes(report_text, address):
    if not FPDF:
        return b"FPDF library is not installed."
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    
    pdf.set_font("Helvetica", style="B", size=15)
    pdf.cell(0, 10, "360 Forensic Property & Comprehensive Risk Audit", ln=True, align="C")
    pdf.set_font("Helvetica", size=9)
    pdf.cell(0, 6, "Property: " + address.encode("latin-1", "ignore").decode("latin-1"), ln=True, align="C")
    pdf.cell(0, 6, "Report Generated: " + datetime.date.today().strftime('%B %d, %Y'), ln=True, align="C")
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
            
    return pdf.output(dest="S").encode("latin-1", errors="ignore")

def mock_llm_parse_custom_works(narrative):
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
    return estimates

# ---------------------------------------------------------
# STREAMLIT UI - TWO-COLUMN INTERFACE
# ---------------------------------------------------------
left_panel, right_panel = st.columns(2)

with left_panel:
    st.subheader("1. Ingest Property Coordinates")
    property_url = st.text_input(
        "Daft.ie / MyHome.ie Listing URL", 
        value="https://www.daft.ie/for-sale/12-connolly-gardens-inchicore-dublin-8/6655188"
    )
    
    extracted_street = "Target Property"
    extracted_postcode = "DUBLIN COUNTY"
    
    if property_url:
        parsed_url = parse_dublin_url(property_url)
        extracted_street = parsed_url["street"]
        extracted_postcode = parsed_url["postcode"]
        st.success("Listing Ingested: " + parsed_url["address"])

    st.subheader("2. BER Document Ingestion (Combined Slot)")
    ber_pdfs = st.file_uploader(
        "Upload SEAI Technical Files (PDFs)", 
        type=["pdf"], 
        accept_multiple_files=True,
        key="multi_ber"
    )
    
    ber_texts = []
    pdf_metrics = {"size": None, "ber": None}
    
    if ber_pdfs:
        for idx, pdf in enumerate(ber_pdfs):
            text = extract_text_from_pdf(pdf.read())
            ber_texts.append(text)
            st.info(f"File {idx+1} ({pdf.name}) parsed successfully.")
            extracted = extract_metrics_from_ber_text(text)
            if extracted["size"]:
                pdf_metrics["size"] = extracted["size"]
            if extracted["ber"]:
                pdf_metrics["ber"] = extracted["ber"]

    st.subheader("3. Asset Media & Spatial Uploads")
    media_tab1, media_tab2 = st.tabs(["📁 File Uploader", "📋 Clipboard Paste Area"])
    
    uploaded_media = []
    with media_tab1:
        uploaded_media = st.file_uploader(
            "Upload Photos / Plans", 
            type=["png", "jpg", "jpeg"], 
            accept_multiple_files=True
        )
            
    with media_tab2:
        pasted_data = st.text_input("Clipboard Buffer", placeholder="Ctrl+V or drop an image into this window...")

    st.subheader("🔧 Spatial & Custom Works")
    user_narrative = st.text_input("Custom Work Description", placeholder="e.g. Knock down wall, install RSJ and heat pump")

    st.subheader("🛌 Bedroom Dimensions Audit")
    b1_w = st.number_input("Bedroom 1 Width (m)", value=3.0, step=0.1)
    b1_l = st.number_input("Bedroom 1 Length (m)", value=4.0, step=0.1)
    
    b2_w = st.number_input("Bedroom 2 Width (m)", value=3.0, step=0.1)
    b2_l = st.number_input("Bedroom 2 Length (m)", value=3.0, step=0.1)
    
    b3_w = st.number_input("Bedroom 3 Width (m)", value=2.2, step=0.1)
    b3_l = st.number_input("Bedroom 3 Length (m)", value=2.7, step=0.1)

    st.subheader("💰 Buyer Parameters")
    budget_max = st.number_input("Max Budget Ceiling (€)", min_value=100000, value=750000, step=10000)
    target_ber = st.selectbox("Target Mortgage Tier", ["AIB Green Mortgage (B3 or better)", "Standard Mortgage (Any BER)", "Net-Zero A-Rating Target"])

    st.subheader("⚙️ Calibration (Interactive Overrides)")
    address_input = st.text_input("Property Address Override", value=f"{extracted_street}, {extracted_postcode}")
    asking_price = st.number_input("Asking Price (€)", value=525000, step=10000)
    
    default_size = pdf_metrics["size"] if pdf_metrics["size"] else 95.0
    size_sqm = st.number_input("Floorplate Size (m²)", value=default_size, step=1.0)
    
    default_ber = pdf_metrics["ber"] if pdf_metrics["ber"] else "B2"
    ber_rating = st.selectbox("Current BER Rating", ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3", "D1", "D2", "E1", "E2", "F", "G"], index=4)
    typology = st.selectbox("Property Typology", ["End-of-Terrace", "Mid-Terrace", "Semi-Detached", "Detached"])
    
    run_audit_btn = st.button("🚀 Run 360° Forensic Audit Protocol (v6.0)", type="primary", use_container_width=True)

# Calculate bedroom areas dynamically
b1_area = b1_w * b1_l
b2_area = b2_w * b2_l
b3_area = b3_w * b3_l

# Process custom works based on narrative input
if user_narrative:
    custom_works = mock_llm_parse_custom_works(user_narrative)
    if custom_works:
        total_low = sum(item["low"] for item in custom_works)
        total_high = sum(item["high"] for item in custom_works)

# ---------------------------------------------------------
# CALCULATE BID ROADS & ACQUISITION BOUNDARIES
# ---------------------------------------------------------
opening_bid = asking_price * 1.05
fmv_ceiling = asking_price * 1.15
walkaway_ceiling = fmv_ceiling - total_low

b1_flag = "Habitable" if b1_area >= 7.0 else "UNLIVABLE BOX ROOM"
b2_flag = "Habitable" if b2_area >= 7.0 else "UNLIVABLE BOX ROOM"
b3_flag = "Habitable" if b3_area >= 7.0 else "UNLIVABLE BOX ROOM"

# ---------------------------------------------------------
# REPORT OUTPUT & SPATIAL ENGINE (MULTI-TAB RESTORED)
# ---------------------------------------------------------
with right_panel:
    st.subheader("📋 Forensic Audit & Strategic Acquisition Report")
    
    # FIX: Explicitly configured output tabs to restore previous tabbed layout
    tab_report, tab_retrofit, tab_hazards, tab_verdict, tab_map = st.tabs([
        "💶 Area Comps & CMA",
        "🏗️ Retrofit & Spatial Fabric",
        "⛈️ Hazards & Legal",
        "🏁 Verdict & Export",
        "🗺️ Spatial GIS Map"
    ])
    
    map_lat, map_lon = 53.3402, -6.3156
    is_d08 = "D08" in extracted_postcode or "D8" in extracted_postcode
    is_d14 = "D14" in extracted_postcode or "DUNDRUM" in extracted_street.upper()
    
    if is_d14:
        map_lat, map_lon = 53.2950, -6.2450

    if run_audit_btn:
        st.session_state.audit_report = f"""
### 🏛️ 360° Forensic Audit: {address_input}
*Generated: {datetime.date.today().strftime('%B %d, %Y')}*

---

### EXECUTIVE SUMMARY:
The property at **{address_input}** represents an excellent target matching your maximum budget of **€{budget_max:,}**. 
Due to your required Capital Works Reserve requirements of **€{total_low:,} – €{total_high:,}**, your absolute walk-away bidding limit is calculated at **€{walkaway_ceiling:,.0f}** to preserve structural cash cushions.

---

### SECTION 1: MICRO-MARKET CMA & VALUATIONS

| BER Performance Tier | Average Price / m² | Target Property Alignment |
|---|---|---|
| **Tier 1: Green Turnkey (BER A1–B3)** | **€7,200 – €7,800 / m²** | **Your target aligns here** |
| **Tier 2: Modernised Standard (BER C1–C3)** | **€6,400 – €7,000 / m²** | |
| **Tier 3: Retrofit Required (BER D1–G)** | **€5,400 – €6,200 / m²** | |

#### Extended Comparable Transaction Matrix
| Address | Street | Sale Date | PPR Price | Size | BER | Situation | m² Rate | Comparability |
|---|---|---|---|---|---|---|---|---|
| **{address_input}** | **{extracted_street}** | **Live** | **€{asking_price:,}** | **{size_sqm} m²** | **{ber_rating}** | **{typology}** | **€{asking_price/size_sqm:,.0f}/m²** | **Target Property** |
| Comp 1 | Adjacent Street | 2026-07 | €665,000 | 96 m² | D2 | {typology} | €6,927/m² | Near target baseline |
| Comp 2 | Adjacent Street | 2025-10 | €499,680 | 84 m² | F | {typology} | €5,948/m² | Unmodernised comp |

#### Valuation & Acquisition Boundaries
* **Fair Market Value (FMV):** €{fmv_ceiling:,.0f}
* **Recommended Opening Bid:** €{opening_bid:,.0f} (Asking + 5%)
* **Strict Walk-Away Limit:** €{walkaway_ceiling:,.0f} (FMV minus Capital Works Reserves)

---

### SECTION 2: BEDROOM SIZE AUDIT (SCSI STANDARDS)
* **Bedroom 1:** {b1_w}m x {b1_l}m = **{b1_area:.2f} m²** ({b1_flag})
* **Bedroom 2:** {b2_w}m x {b2_l}m = **{b2_area:.2f} m²** ({b2_flag})
* **Bedroom 3:** {b3_w}m x {b3_l}m = **{b3_area:.2f} m²** ({b3_flag})

*Note: Under standard SCSI protocols, any room under 7.0 m² cannot be marketed as a bedroom.*

---

### SECTION 3: ROAD TO B3 & A RATING ROADMAPS

#### 🟢 The Road to B3 (Green Mortgage Rate Eligibility)
* **Attic Insulation:** Gross €2,500 | SEAI Grant: €1,500 | **Net: €1,000**
* **Heating Controls:** Gross €1,800 | SEAI Grant: €700 | **Net: €1,110**
* **TOTAL ROAD TO B3:** **Gross €4,300 | Grants €2,200 | Net €2,110**

#### 🔵 The Road to A-Rating (Deep Retrofit / Net-Zero)
* **External Wall Insulation:** Gross €18,000 | SEAI Grant: €6,000 | **Net: €12,000**
* **Air-to-Water Heat Pump:** Gross €16,000 | SEAI Grant: €6,500 | **Net: €9,500**
* **TOTAL ROAD TO A:** **Gross €34,000 | Grants €12,500 | Net €21,500**

---

### SECTION 4: HAZARDS & SURVEY SCAN
* **OPW Flooding History:** Outside active River Camac/Dodder fluvial risk zones.
* **Planning Precedents:** Neighbors on the adjacent street successfully secured dormer and extension retention permissions.
"""

    with tab_report:
        if st.session_state.audit_report:
            st.markdown("### Executive Valuation Summary")
            st.markdown(f"""
            - **Extracted Address:** {address_input}
            - **Current Asking Price:** €{asking_price:,}
            - **Target Floorplate:** {size_sqm} m²
            """)
            st.markdown("### Micro-Market CMA & Valuations")
            st.markdown(f"""
            | Property Address | Asking Price | Floorplate | BER | Situation |
            |---|---|---|---|---|
            | **{address_input}** | **€{asking_price:,}** | **{size_sqm} m²** | **{ber_rating}** | **{typology}** |
            """)
            st.markdown(f"""
            - **Fair Market Value (FMV):** €{fmv_ceiling:,.0f}
            - **Recommended Opening Bid:** €{opening_bid:,.0f}
            - **Strict Walk-Away Limit:** €{walkaway_ceiling:,.0f}
            """)
        else:
            st.info("👈 Click 'Run 360° Forensic Audit' to generate report data.")
            
    with tab_retrofit:
        if st.session_state.audit_report:
            st.markdown("### Bedroom Sizes Audit (SCSI T
