import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import io
import uuid
import os
from dotenv import load_dotenv
from fpdf import FPDF

# Load environment variables from a .env file if it exists
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="Automated Report Generator",
    page_icon="📄",
    layout="wide"
)

# --- App Title and Description ---
st.title("🤖 Automated Report Generator")
st.markdown("Welcome! This tool helps you create professional audit reports. Describe an observation, set a priority, optionally upload an image, and let AI generate the recommendation.")

# --- Gemini API Configuration ---
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY")
    except (FileNotFoundError, AttributeError):
        api_key = None

if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("🚨 Google API Key not found! Please create a `.env` file with `GOOGLE_API_KEY='YOUR_KEY'` for local development, or set it in Streamlit secrets for deployment.")
    st.stop()

# --- Session State Initialization ---
if 'observations' not in st.session_state:
    st.session_state.observations = []

# --- Helper Functions ---
def generate_recommendation_with_image(image, text):
    """Calls the Gemini Vision model for recommendations based on image and text."""
    vision_model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = f"""
    You are an expert safety auditor reviewing an observation.
    Based on the following image and text, provide a concise, actionable recommendation to rectify the issue.
    The tone should be professional and clear.
    Observation: "{text}"
    """
    try:
        response = vision_model.generate_content([prompt, image])
        return response.text
    except Exception as e:
        st.error(f"An error occurred while generating the recommendation: {e}")
        return None

def generate_recommendation_text_only(text):
    """Calls the Gemini text model for recommendations based on text only."""
    text_model = genai.GenerativeModel('gemini-pro')
    prompt = f"""
    You are an expert safety auditor reviewing an observation.
    Based on the following text, provide a concise, actionable recommendation to rectify the issue.
    The tone should be professional and clear.
    Observation: "{text}"
    """
    try:
        response = text_model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"An error occurred while generating the recommendation: {e}")
        return None

def to_pdf(observations_list):
    """Converts the list of observations to a PDF file."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "Audit Report", ln=True, align="C")
    pdf.ln(10)

    for i, obs in enumerate(observations_list):
        pdf.set_font("Arial", "B", 12)
        pdf.cell(200, 10, f"Observation #{len(observations_list) - i}", ln=True)
        
        # Priority
        pdf.set_font("Arial", "B", 10)
        pdf.cell(30, 10, "Priority:")
        pdf.set_font("Arial", "", 10)
        pdf.cell(160, 10, obs["priority"], ln=True)

        # Observation Text
        pdf.set_font("Arial", "B", 10)
        pdf.multi_cell(0, 10, "Observation:")
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 5, obs["observation_text"])
        pdf.ln(5)

        # Recommendation Text
        pdf.set_font("Arial", "B", 10)
        pdf.multi_cell(0, 10, "Recommendation:")
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 5, obs["recommendation"])
        pdf.ln(5)

        # Image
        if obs["image"]:
            try:
                # Save PIL image to a byte stream
                img_byte_arr = io.BytesIO()
                obs["image"].save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                
                # Add image to PDF
                pdf.image(io.BytesIO(img_byte_arr), w=100)
                pdf.ln(5)
            except Exception as e:
                pdf.set_font("Arial", "I", 8)
                pdf.cell(0, 10, f"(Could not embed image: {e})", ln=True)

        pdf.cell(0, 5, "-"*80, ln=True, align="C")
        pdf.ln(5)

    return pdf.output(dest='S').encode('latin-1')


# --- Input Form Section ---
st.subheader("Add New Observation")
with st.form(key="report_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        observation_text = st.text_area(
            "Describe the Observation (Required)",
            height=150,
            placeholder="e.g., Exposed electrical wiring found near the main walkway..."
        )
        priority = st.selectbox(
            "Set Priority",
            ("Low", "Medium", "High"),
            index=1 # Default to Medium
        )
    with col2:
        uploaded_image = st.file_uploader(
            "Upload Observation Image (Optional)",
            type=["png", "jpg", "jpeg", "webp"],
            help="Upload an image that clearly shows the observation."
        )
    
    submit_button = st.form_submit_button(
        label="Add Observation & Generate Recommendation", 
        use_container_width=True, 
        type="primary"
    )

# --- Main Logic for Form Submission ---
if submit_button:
    if not observation_text.strip():
        st.warning("⚠️ Please provide a description for the observation.")
    else:
        with st.spinner("🧠 AI is thinking... Please wait."):
            recommendation = None
            image = None
            if uploaded_image:
                image = Image.open(uploaded_image)
                recommendation = generate_recommendation_with_image(image, observation_text)
            else:
                recommendation = generate_recommendation_text_only(observation_text)
            
            if recommendation:
                new_observation = {
                    "id": str(uuid.uuid4()),
                    "image": image,
                    "observation_text": observation_text,
                    "priority": priority,
                    "recommendation": recommendation
                }
                st.session_state.observations.insert(0, new_observation)
                st.success("✅ Observation added successfully!")

st.markdown("---")

# --- Displaying the Report ---
st.header("Generated Report")

if not st.session_state.observations:
    st.info("Your report is currently empty. Add observations to begin.")
else:
    # --- Action Buttons (Download and Clear) ---
    col1, col2 = st.columns([0.2, 1])
    with col1:
        pdf_data = to_pdf(st.session_state.observations)
        st.download_button(
           label="📥 Download Report (PDF)",
           data=pdf_data,
           file_name="audit_report.pdf",
           mime="application/pdf",
           use_container_width=True
        )
    with col2:
        if st.button("Clear Entire Report", use_container_width=True):
            st.session_state.observations = []
            st.rerun()

    # --- Report Table ---
    st.markdown("### Observations and Recommendations")
    
    # Table Header
    header_cols = st.columns([0.1, 0.2, 0.1, 0.25, 0.3, 0.05])
    header_fields = ["Sr. No.", "Image", "Priority", "Observation", "Recommendation", ""]
    for col, field in zip(header_cols, header_fields):
        col.markdown(f"**{field}**")

    # Table Rows
    for i, obs in enumerate(st.session_state.observations):
        cols = st.columns([0.1, 0.2, 0.1, 0.25, 0.3, 0.05])
        cols[0].write(str(len(st.session_state.observations) - i))
        
        if obs['image']:
            cols[1].image(obs['image'], use_column_width=True)
        else:
            cols[1].markdown("*(No Image)*")
        
        priority_color = {"Low": "green", "Medium": "orange", "High": "red"}
        cols[2].markdown(f"**<p style='color:{priority_color[obs['priority']]}'>{obs['priority']}</p>**", unsafe_allow_html=True)
        
        cols[3].write(obs['observation_text'])
        cols[4].write(obs['recommendation'])
        
        if cols[5].button("❌", key=f"remove_{obs['id']}"):
            st.session_state.observations = [o for o in st.session_state.observations if o['id'] != obs['id']]
            st.rerun()
        st.markdown("---")
