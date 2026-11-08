"""
CropForesight AI — Streamlit demo (SIH26131)

Upload a leaf/plant photo -> get an instant disease diagnosis + pest
detections, drawn on the image. This is the quickest way to *show*
working progress rather than just describe it.

Run with:
    streamlit run app.py
"""

from typing import List, Dict

import streamlit as st
from PIL import Image, ImageDraw

from inference import CropForesightPipeline
from care_advisor import get_care_response, check_resolution

st.set_page_config(page_title="CropForesight AI", page_icon="🌾", layout="centered")


@st.cache_resource(show_spinner="Loading models (first run only, ~1-2 min)...")
def load_pipeline() -> CropForesightPipeline:
    return CropForesightPipeline()


def draw_pest_boxes(image: Image.Image, detections: List[Dict]) -> Image.Image:
    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)
    for det in detections:
        x1, y1, x2, y2 = det["bbox_xyxy"]
        draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
        draw.text((x1, max(y1 - 12, 0)), f"{det['pest']} {det['confidence']}%", fill="red")
    return annotated


st.title("🌾 FasalRakshak AI")
st.caption("Smart Crop Disease & Pest Early-Warning System — SIH26131")

uploaded_file = st.file_uploader("Upload a leaf / plant photo", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file).convert("RGB")
    st.image(image, caption="Uploaded image", use_container_width=True)

    pipeline = load_pipeline()

    with st.spinner("Running diagnosis..."):
        temp_path = "temp_upload.jpg"
        image.save(temp_path)  # ultralytics needs a file path, not just a PIL image

        disease_results = pipeline.predict_disease(image)
        pest_results = pipeline.predict_pests(temp_path)

    st.subheader("🩺 Disease Diagnosis & Care")
    top = disease_results[0]
    care_response = get_care_response(
        image=image,
        plant=top["plant"],
        disease=top["disease"],
        confidence=top["confidence"],
    )

    if care_response["status"] == "healthy":
        st.success(care_response["message"])
    elif care_response["status"] == "diagnosed":
        st.warning(f"**Diagnosis:** {care_response['plant']} — {care_response['disease']} ({care_response['confidence']}%)")
        st.markdown(f"**Recommended treatment:** {care_response['recommendation']}")
        st.markdown(f"**Cultural practice:** {care_response['cultural_practice']}")
    else:  # escalated
        st.info(f"🧑‍🌾 {care_response['message']}")
        st.code(f"Case ID: {care_response['case_id']}", language=None)
        resolution = check_resolution(care_response["case_id"])
        if resolution:
            st.success(f"**Expert response received:** {resolution['treatment']}")

    with st.expander("See other possibilities"):
        for r in disease_results[1:]:
            st.write(f"{r['plant']} — {r['disease']}: {r['confidence']}%")

    st.subheader("🐛 Pest Detections")
    if pest_results:
        annotated_image = draw_pest_boxes(image, pest_results)
        st.image(annotated_image, caption="Detected pests", use_container_width=True)
        for d in pest_results:
            st.write(f"- **{d['pest']}** — {d['confidence']}% confidence")
    else:
        st.info("No pests detected above the confidence threshold.")
else:
    st.info("Upload a photo to get started.")
