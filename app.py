import streamlit as st
import os

from ocr_engine import extract_text
from llm_client import run_qwen
from extractor import clean_data
from export_excel import export_excel
from export_pdf import export_pdf

UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

st.set_page_config(page_title="Drink AI (EasyOCR)", layout="centered")

st.title("🥤 Drink Menu AI (EasyOCR + Qwen + Ollama)")

uploaded_file = st.file_uploader(
    "Upload drink menu image",
    type=["png", "jpg", "jpeg"]
)

if uploaded_file:

    file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.read())

    st.image(file_path, caption="Uploaded Image", use_container_width=True)

    if st.button("🚀 Process Menu"):

        status = st.status("Running pipeline...", expanded=True)

        # STEP 1 OCR
        status.write("👁️ Extracting text using EasyOCR...")
        text = extract_text(file_path)

        with st.expander("📄 OCR Output"):
            st.text(text)

        # STEP 2 Qwen
        status.write("🧠 Sending text to Qwen2.5-VL...")
        raw = run_qwen(text)

        with st.expander("🔍 Raw Qwen Output"):
            st.code(raw)

        # STEP 3 CLEAN
        status.write("🧹 Cleaning data...")
        data = clean_data(raw)

        status.write(f"📊 Extracted {len(data)} items")

        st.subheader("Result Table")
        st.table(data)

        # STEP 4 EXPORT
        status.write("💾 Exporting files...")

        excel_path = "drinks.xlsx"
        pdf_path = "drinks.pdf"

        export_excel(data, excel_path)
        export_pdf(data, pdf_path)

        status.update(label="Done ✔", state="complete")

        # DOWNLOAD
        with open(excel_path, "rb") as f:
            st.download_button("⬇️ Excel", f, file_name="drinks.xlsx")

        with open(pdf_path, "rb") as f:
            st.download_button("⬇️ PDF", f, file_name="drinks.pdf")