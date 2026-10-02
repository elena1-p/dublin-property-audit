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
# INITIALIZE GLOBAL AUDIT STATE & GEOGRAPHIC BASES
# ---------------------------------------------------------
total_low = 0
total_high = 0
custom_works = []

map_lat, map_lon = 53.3402, -6.3156  # Default Dublin Coordinates (D08 Inchicore)
is_d08 = True
is_d14 = False

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
    replacements = {
        "€": "EUR ", "²": " sqm", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", "•": "*",
        "🏡": "", "📊": "", "📋": "", "👁️": "", "📄": "", "🎯": "", "🏆": "", "🕵️‍♂️": "", "🗺️": "", "🚩": "",
        "🟢": "[Habitable] ", "🔴": "[Unhabitable] ", "🟡": "[Attention] ", "🔵": "[Water Hazard] ",
        "⚠️": "Warning: ", "🎉": "Exempt: "
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
        
    text = re.sub(r"\|[-:| ]+\|", "", text)
    text = text.replace("|", "  ")
    
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

    # Map state configuration derived dynamically from URL
    is_d08 = "D08" in extracted_postcode or "D8" in extracted_postcode
    is_d14 = "D14" in extracted_postcode or "DUNDRUM" in extracted_street.upper()
    if is_d14:
        map_lat, map_lon = 53.2950, -6.2450
    else:
        map_lat, map_lon = 53.3402, -6.3156

    st.subheader("2. BER Document Ingestion (Combined Slot)")
    ber_pdfs = st.file_uploader(
        "Upload SEAI Technical Files (PDFs)", 
        type=["pdf"], 
        accept_multiple_files=True,
      
