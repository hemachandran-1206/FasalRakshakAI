"""
care_advisor.py — decides what happens after a diagnosis (SIH26131)

Given the disease classifier's top prediction (plant, disease, confidence),
either:
  (a) returns a treatment recommendation from the knowledge base, or
  (b) escalates the case to a human agricultural expert when the
      diagnosis is uncertain (low confidence) or the knowledge base has
      no entry for it yet.

Escalated cases are written to disk (data/escalation_queue.json +
data/pending_review/<case_id>.jpg) so expert_dashboard.py -- a separate
process -- can pick them up. Once an expert responds there, the answer is
written to data/resolved/<case_id>.json for the farmer-facing app to read,
and (if it's new information) added back into the treatments knowledge
base via treatments.add_treatment(). That round trip is the feedback loop.
"""

import json
import time
import uuid
from pathlib import Path
from typing import Optional

from PIL import Image

import treatments

CONFIDENCE_THRESHOLD = 70.0  # below this, don't trust the AI's own diagnosis

DATA_DIR = Path("data")
PENDING_DIR = DATA_DIR / "pending_review"
RESOLVED_DIR = DATA_DIR / "resolved"
QUEUE_FILE = DATA_DIR / "escalation_queue.json"

PENDING_DIR.mkdir(parents=True, exist_ok=True)
RESOLVED_DIR.mkdir(parents=True, exist_ok=True)


def load_queue() -> list:
    if QUEUE_FILE.exists():
        try:
            return json.loads(QUEUE_FILE.read_text())
        except json.JSONDecodeError:
            return []
    return []


def save_queue(queue: list) -> None:
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(queue, indent=2))


def get_care_response(image: Image.Image, plant: str, disease: str, confidence: float) -> dict:
    """
    Main entry point -- call this after the disease classifier gives its
    top prediction. Returns a dict the farmer-facing app can render
    directly; one of three shapes depending on "status".
    """
    if treatments.is_healthy_label(disease):
        return {
            "status": "healthy",
            "message": f"No disease detected on this {plant.lower()} plant -- it looks healthy. Keep up regular monitoring.",
        }

    if confidence >= CONFIDENCE_THRESHOLD:
        info = treatments.get_treatment(plant, disease)
        if info is not None:
            return {
                "status": "diagnosed",
                "plant": plant,
                "disease": disease,
                "confidence": confidence,
                "recommendation": info["recommendation"],
                "cultural_practice": info["cultural_practice"],
            }

    # Low confidence OR no matching knowledge-base entry -> escalate to a human
    case_id = _escalate_case(image, plant, disease, confidence)
    return {
        "status": "escalated",
        "case_id": case_id,
        "message": (
            "We couldn't confidently identify a treatment for this case. "
            "It's been forwarded to our agricultural experts for review -- "
            "check back with this case ID once they've responded."
        ),
    }


def _escalate_case(image: Image.Image, plant: str, disease: str, confidence: float) -> str:
    case_id = uuid.uuid4().hex[:8]
    saved_image_path = PENDING_DIR / f"{case_id}.jpg"
    image.save(saved_image_path)

    queue = load_queue()
    queue.append({
        "case_id": case_id,
        "image_path": str(saved_image_path),
        "ai_plant_guess": plant,
        "ai_disease_guess": disease,
        "ai_confidence": confidence,
        "submitted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "pending",
    })
    save_queue(queue)
    return case_id


def check_resolution(case_id: str) -> Optional[dict]:
    """Lets the farmer-facing app poll whether an expert has responded yet."""
    resolved_file = RESOLVED_DIR / f"{case_id}.json"
    if resolved_file.exists():
        return json.loads(resolved_file.read_text())
    return None
