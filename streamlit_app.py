import streamlit as st
import os
import base64
import json
import re
from datetime import datetime
from PIL import Image

# Page configuration
st.set_page_config(
    page_title="📊 Form Processing Tool",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = []
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Title
st.title("📊 Form Processing Tool")
st.markdown("Upload forms to extract and analyze text using AI")

# Test API keys availability
def check_api_keys():
    try:
        mistral_key = st.secrets["MISTRAL_API_KEY"]
        groq_key = st.secrets["GROQ_API_KEY"]
        return mistral_key, groq_key, True
    except Exception as e:
        return "", "", False

mistral_key, groq_key, keys_available = check_api_keys()

if not keys_available:
    st.error("⚠️ API keys not configured. Please add MISTRAL_API_KEY and GROQ_API_KEY to Streamlit secrets.")
    st.info("Go to your app dashboard > Settings > Secrets to add the keys.")
    st.stop()

# Try to import required libraries
try:
    from mistralai import Mistral
    from groq import Groq
    
    # Initialize clients
    mistral_client = Mistral(api_key=mistral_key)
    groq_client = Groq(api_key=groq_key)
    
    st.success("✅ All libraries loaded and API keys configured")
except ImportError as e:
    st.error(f"❌ Library import failed: {e}")
    st.stop()
except Exception as e:
    st.error(f"❌ API client initialization failed: {e}")
    st.stop()

# Basic functions
def encode_image(image_file):
    try:
        return base64.b64encode(image_file.getvalue()).decode('utf-8')
    except Exception as e:
        st.error(f"Error encoding image: {e}")
        return None

def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def process_with_mistral_ocr(base64_image, file_extension):
    try:
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract all text from this image clearly and accurately."
                    },
                    {
                        "type": "image_url",
                        "image_url": f"data:image/{file_extension};base64,{base64_image}"
                    }
                ]
            }
        ]
        
        response = mistral_client.chat.complete(
            model="pixtral-12b-2409",
            messages=messages
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        st.error(f"OCR processing error: {str(e)}")
        return None

def extract_key_values_simple(text):
    try:
        lines = text.splitlines()
        key_value_pairs = []
        
        for line in lines:
            line = line.strip()
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key and value:
                        key_value_pairs.append(f"{key}: {value}")
        
        if key_value_pairs:
            return "Key-Value Pairs Found:\n" + "\n".join(key_value_pairs)
        else:
            return "No clear key-value pairs detected in the text."
            
    except Exception as e:
        return f"Error extracting key-values: {str(e)}"

def summarize_with_groq(text):
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an AI that creates concise summaries of document content."},
                {"role": "user", "content": f"Summarize this document text:\n\n{text}"}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Error generating summary: {str(e)}"

# Main interface
tab1, tab2 = st.tabs(["📤 Document Processing", "📈 Results"])

with tab1:
    st.header("📤 Upload Document")
    
    uploaded_file = st.file_uploader(
        "Choose an image file",
        type=["jpg", "jpeg", "png"],
        help="Upload JPG or PNG images"
    )
    
    if uploaded_file:
        # Display image
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Document", width=400)
        
        # Process button
        if st.button("🚀 Process Document", type="primary"):
            with st.spinner("Processing..."):
                try:
                    # Encode image
                    base64_img = encode_image(uploaded_file)
                    if not base64_img:
                        st.error("Failed to encode image")
                        st.stop()
                    
                    # Get file extension
                    ext = uploaded_file.name.split(".")[-1].lower()
                    if ext == "jpg":
                        ext = "jpeg"
                    
                    # OCR
                    st.info("Extracting text...")
                    ocr_text = process_with_mistral_ocr(base64_img, ext)
                    
                    if not ocr_text:
                        st.error("Failed to extract text")
                        st.stop()
                    
                    # Analysis
                    st.info("Analyzing content...")
                    key_values = extract_key_values_simple(ocr_text)
                    summary = summarize_with_groq(ocr_text)
                    
                    # Store results
                    result = {
                        'filename': uploaded_file.name,
                        'timestamp': get_timestamp(),
                        'text': ocr_text,
                        'key_values': key_values,
                        'summary': summary
                    }
                    
                    st.session_state.processed_data.append(result)
                    st.success("✅ Document processed successfully!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Processing failed: {str(e)}")

with tab2:
    st.header("📋 Processing Results")
    
    if st.session_state.processed_data:
        latest_doc = st.session_state.processed_data[-1]
        
        st.subheader(f"Latest: {latest_doc['filename']}")
        st.write(f"Processed: {latest_doc['timestamp']}")
        
        # Results tabs
        result_tab1, result_tab2, result_tab3 = st.tabs(["📄 Text", "🔑 Key-Values", "📝 Summary"])
        
        with result_tab1:
            st.text_area("Extracted Text", latest_doc['text'], height=300)
            st.download_button(
                "Download Text",
                data=latest_doc['text'],
                file_name=f"{latest_doc['filename']}_extracted.txt"
            )
        
        with result_tab2:
            st.text_area("Key-Value Analysis", latest_doc['key_values'], height=300)
        
        with result_tab3:
            st.text_area("AI Summary", latest_doc['summary'], height=300)
        
        # All documents
        if len(st.session_state.processed_data) > 1:
            st.subheader("📊 All Processed Documents")
            for i, doc in enumerate(st.session_state.processed_data):
                with st.expander(f"{doc['filename']} - {doc['timestamp']}"):
                    st.write("**Summary:**", doc['summary'][:200] + "...")
    else:
        st.info("No documents processed yet. Upload a document in the first tab.")

# Clear data button
if st.session_state.processed_data:
    if st.button("🗑️ Clear All Data"):
        st.session_state.processed_data = []
        st.success("All data cleared!")
        st.rerun()

# Footer
st.divider()
st.caption("📊 Form Processing Tool - OCR by Mistral AI - Analysis by Groq LLaMA")
