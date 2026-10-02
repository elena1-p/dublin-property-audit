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
# UTILITY PARSING FUNCTIONS
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
    # Double-escaped backslashes to resolve the compile-time quote leak completely
    size_match = re.search(r"(?:dimension|area|floor\\s+area|size)\\s*[:\\-]?\\s*(\\d+(?:\\.\\d+)?)\\s*(?:sqm|m²|sq\\s*m)", text, re.IGNORECASE)
    if size_match:
        metrics["size"] = float(size_match.group(1))
    ber_match = re.search(r"\\b(A[1-3]|B[1-3]|C[1-3]|D[1-2]|E[1-2]|[FG])\\b", text)
    if ber_match:
        metrics["ber"] = ber_match.group(1)
    return metrics

def parse_dublin_url(url):
    if not url:
        return None
    clean_url = url.lower().replace("-", " ").replace("_", " ")
    postcode_match = re.search(r"dublin\\s+(\\d+[a-z]?)", clean_url)
    postcode = postcode_match.group(0).upper().strip() if postcode_match else "DUBLIN COUNTY"
    
    street_parts = []
    tokens = clean_url.split("/")
    target_token = tokens[-1] if tokens[-1] else (tokens[-2] if len(tokens) > 1 else "")
    target_token = re.sub(r"\\d{5,}", "", target_token)
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
    replacements = {
        "€": "EUR ", "²": " sqm", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", "•": "*"
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    text = re.sub(r"\\|[-:| ]+\\|", "", text)
    text = text.replace("|", "  ")
    return text.encode("latin-1", errors="ignore").decode("latin-1")

def generate_pdf_bytes(report_text, address):
    if not FPDF:
        return b"FPDF library is not installed."
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    
    pdf.set_font("Helvetica", style="B", size=14)
    pdf.cell(0, 10, "360 Forensic Property Audit Report", ln=True, align="C")
    pdf.set_font("Helvetica", size=9)
    pdf.cell(0, 6, "Property Address: " + address, ln=True, align="C")
    pdf.cell(0, 6, "Report Generated: " + datetime.date.today().strftime('%B %d, %Y'), ln=True, align="C")
    pdf.ln(8)
    
    cleaned_text = clean_pdf_text(report_text)
    for line in cleaned_text.split("\n"):
        if not line.strip():
            pdf.ln(3)
        elif line.strip().startswith("###"):
            pdf.set_font("Helvetica", style="B", size=10)
            pdf.multi_cell(0, 6, txt=line.replace("###", "").strip())
            pdf.set_font("Helvetica", size=9)
        elif line.strip().startswith("##") or line.strip().startswith("#"):
            pdf.set_font("Helvetica", style="B", size=12)
            pdf.ln(4)
            pdf.multi_cell(0, 7, txt=line.replace("##", "").replace("#", "").strip())
            pdf.set_font("Helvetica", size=9)
        else:
            pdf.multi_cell(0, 5, txt=line)
            
    return pdf.output(dest="S").encode("latin-1", errors="ignore")

def mock_llm_parse_custom_works(narrative):
    estimates = []
    text = narrative.lower()
    
    checks = {
        "rsj": (["wall", "knock", "rsj", "steel", "open plan"], "Requires structural engineer certificate."),
        "heat_pump": (["heat pump", "pump", "retrofit", "ber", "radiator"], "Includes SEAI grant preparation."),
        "attic": (["attic", "roof", "dormer", "loft"], "Requires floor joist reinforcement."),
        "rewire": (["wire", "rewire", "electrics"], "Full chasing of masonry walls."),
        "insulation": (["wrap", "insulate", "external", "ewi"], "Requires sill depth extensions.")
    }
    
    for key, (keywords, scope) in checks.items():
        if any(k in text for k in keywords):
            estimates.append({
                "item": DUBLIN_COST_DATABASE[key]["label"],
                "low": DUBLIN_COST_DATABASE[key]["low"],
                "high": DUBLIN_COST_DATABASE[key]["high"],
                "scope": scope
            })
    return estimates

# ---------------------------------------------------------
# STREAMLIT TWO-COLUMN UI LAYOUT
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

    # Establish geography and lat/lon bounds
    is_d08 = "D08" in extracted_postcode or "D8" in extracted_postcode
    is_d14 = "D14" in extracted_postcode or "DUNDRUM" in extracted_street.upper()
    map_lat, map_lon = (53.2950, -6.2450) if is_d14 else (53.3402, -6.3156)

    st.subheader("2. BER Document Ingestion (Combined Slot)")
    ber_pdfs = st.file_uploader("Upload SEAI Technical Files (PDFs)", type=["pdf"], accept_multiple_files=True, key="multi_ber")
    
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

    st.subheader("🔧 Planned Alterations & Custom Works")
    user_narrative = st.text_input("Custom Work Description", value="Knock down main wall to install RSJ beam, rewire, and install a heat pump")

    st.subheader("🛌 Bedroom Dimensions Audit")
    b1_w = st.number_input("Bedroom 1 Width (m)", value=3.0, step=0.1)
    b1_l = st.number_input("Bedroom 1 Length (m)", value=4.0, step=0.1)
    b2_w = st.number_input("Bedroom 2 Width (m)", value=3.0, step=0.1)
    b2_l = st.number_input("Bedroom 2 Length (m)", value=3.0, step=0.1)
    b3_w = st.number_input("Bedroom 3 Width (m)", value=2.2, step=0.1)
    b3_l = st.number_input("Bedroom 3 Length (m)", value=2.7, step=0.1)

    st.subheader("🚽 SCSI Spatial Metrics")
    guest_wc = st.checkbox("Downstairs Guest WC Present?", value=False)
    building_era = st.selectbox("Construction Era", ["Pre-1940 (Period)", "1940s-1960s", "1970s-1980s", "1990s-2006", "2014+"], index=1)

    st.subheader("💰 Buyer Parameters")
    budget_max = st.number_input("Max Budget Ceiling (€)", min_value=100000, value=750000, step=10000)
    target_ber = st.selectbox("Target Mortgage Tier", ["AIB Green Mortgage", "Standard Mortgage", "Net-Zero"])

    st.subheader("⚙️ Calibration")
  
