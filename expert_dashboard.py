"""
expert_dashboard.py — agricultural-expert review queue (SIH26131)

Shows every case the AI escalated (low confidence, or a disease outside
its knowledge base). An expert picks one, enters the real diagnosis and
treatment, and submits:

  1. The farmer-facing case is marked resolved -- app.py can read it back
     via care_advisor.check_resolution(case_id).
  2. If it's a genuinely new (plant, disease) pair, it's added to the
     treatments knowledge base (treatments.add_treatment) so the next
     identical case is answered automatically instead of being escalated
     again -- this is the feedback loop that improves the system over time.

Run with:
    streamlit run expert_dashboard.py
"""

import json
import time

import streamlit as st
from PIL import Image

import treatments
from care_advisor import RESOLVED_DIR, load_queue, save_queue

st.set_page_config(page_title="CropForesight AI — Expert Review", page_icon="🧑‍🌾", layout="centered")
st.title("🧑‍🌾 Expert Review Queue")
st.caption("Cases the AI couldn't confidently resolve — SIH26131 / CropForesight AI")

pending_cases = [c for c in load_queue() if c["status"] == "pending"]

if not pending_cases:
    st.success("No pending cases. ✅")
else:
    case = st.selectbox(
        "Select a case to review",
        pending_cases,
        format_func=lambda c: (
            f"{c['case_id']} — AI guess: {c['ai_plant_guess']} / "
            f"{c['ai_disease_guess']} ({c['ai_confidence']}%)"
        ),
    )

    st.image(Image.open(case["image_path"]), caption=f"Case {case['case_id']}", use_container_width=True)
    st.write(f"**AI's best guess:** {case['ai_plant_guess']} — {case['ai_disease_guess']} ({case['ai_confidence']}% confidence)")
    st.write(f"**Submitted:** {case['submitted_at']}")

    with st.form(key=f"review_{case['case_id']}"):
        expert_plant = st.text_input("Confirmed plant", value=case["ai_plant_guess"])
        expert_disease = st.text_input("Confirmed disease / pest", value="")
        expert_treatment = st.text_area("Recommended treatment / cure")
        expert_notes = st.text_area("Notes for the farmer (optional)")
        submitted = st.form_submit_button("Submit expert diagnosis")

    if submitted:
        if not expert_disease.strip() or not expert_treatment.strip():
            st.error("Please fill in both the disease and the treatment fields.")
        else:
            # 1. Resolve the farmer-facing case
            resolution = {
                "case_id": case["case_id"],
                "plant": expert_plant,
                "disease": expert_disease,
                "treatment": expert_treatment,
                "notes": expert_notes,
                "resolved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            RESOLVED_DIR.mkdir(parents=True, exist_ok=True)
            (RESOLVED_DIR / f"{case['case_id']}.json").write_text(json.dumps(resolution, indent=2))

            # 2. Mark it resolved in the queue so it drops out of this list
            full_queue = load_queue()
            for c in full_queue:
                if c["case_id"] == case["case_id"]:
                    c["status"] = "resolved"
            save_queue(full_queue)

            # 3. Feed the new knowledge back into the treatment database
            if treatments.get_treatment(expert_plant, expert_disease) is None:
                treatments.add_treatment(
                    plant=expert_plant,
                    disease=expert_disease,
                    recommendation=expert_treatment,
                    cultural_practice=expert_notes or "No additional notes provided.",
                )
                st.info("This was a new case — added to the knowledge base so future diagnoses of it won't need escalation.")

            st.success(f"Case {case['case_id']} resolved and sent back to the farmer.")
            st.rerun()
