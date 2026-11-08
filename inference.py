"""
CropForesight AI — combined inference pipeline (SIH26131)

Loads two pretrained models and runs both on a single leaf/plant photo:
  1. Disease classifier — MobileNetV2 fine-tuned on PlantVillage
     (linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification)
  2. Pest detector — YOLO11 fine-tuned on IP102
     (Yudsky/pest-detection-yolo11)

No training required — both models are pulled from the Hugging Face Hub
on first run and cached locally.

CLI usage:
    python inference.py path/to/leaf.jpg
    python inference.py path/to/leaf.jpg --top-k 5
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import torch
from PIL import Image
from transformers import MobileNetV2ImageProcessor, MobileNetV2ForImageClassification
# Note: this checkpoint's preprocessor_config.json predates the current
# transformers auto-detection format, so AutoImageProcessor/AutoModel can't
# resolve it. Loading the MobileNetV2-specific classes directly skips that
# detection step entirely and works fine.
from ultralytics import YOLO
from huggingface_hub import hf_hub_download

from care_advisor import get_care_response

DISEASE_MODEL_NAME = "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification"
PEST_MODEL_REPO = "Yudsky/pest-detection-yolo11"
PEST_MODEL_FILE = "best.pt"  # weights file on the HF repo


class CropForesightPipeline:
    """Wraps the disease classifier + pest detector behind one .predict(image_path) call."""

    def __init__(self, device: Optional[str] = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        print(f"[CropForesight] Loading disease classifier ({DISEASE_MODEL_NAME}) on {self.device} ...")
        self.disease_processor = MobileNetV2ImageProcessor.from_pretrained(DISEASE_MODEL_NAME)
        self.disease_model = MobileNetV2ForImageClassification.from_pretrained(DISEASE_MODEL_NAME)
        self.disease_model.to(self.device).eval()

        print(f"[CropForesight] Loading pest detector ({PEST_MODEL_REPO}) ...")
        pest_weights_path = hf_hub_download(repo_id=PEST_MODEL_REPO, filename=PEST_MODEL_FILE)
        self.pest_model = YOLO(pest_weights_path)

        print("[CropForesight] Models ready.\n")

    @staticmethod
    def _parse_disease_label(raw_label: str) -> tuple[str, str]:
        """
        Handles the label formats seen across different disease-model
        checkpoints:
          'Tomato___Late_blight'  -> ('Tomato', 'Late Blight')   (PlantVillage folder style)
          'Grape with Black Rot'  -> ('Grape', 'Black Rot')      (this checkpoint's actual style)
        Falls back to keeping the raw label as the disease name (rather than
        discarding it as "Unknown") if neither pattern matches, so a
        confident prediction never gets lost to a parsing gap.
        """
        raw_label = raw_label.strip()

        if "___" in raw_label:
            plant_part, disease_part = raw_label.split("___", 1)
            plant = plant_part.replace("_", " ").replace("(", "").replace(")", "").strip()
            disease_raw = disease_part.replace("_", " ").strip()
        elif " with " in raw_label.lower():
            idx = raw_label.lower().index(" with ")
            plant = raw_label[:idx].strip()
            disease_raw = raw_label[idx + len(" with "):].strip()
        else:
            plant = "Unknown Plant"
            disease_raw = raw_label

        disease = "Healthy" if disease_raw.lower() == "healthy" else disease_raw.title()
        return plant, disease

    def predict_disease(self, image: Image.Image, top_k: int = 3) -> list[dict]:
        """Returns the top_k most likely (plant, disease, confidence%) predictions."""
        inputs = self.disease_processor(images=image, return_tensors="pt").to(self.device)
        with torch.no_grad():
            logits = self.disease_model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)[0]
        top_probs, top_idxs = torch.topk(probs, k=min(top_k, probs.shape[-1]))

        results = []
        for prob, idx in zip(top_probs.tolist(), top_idxs.tolist()):
            raw_label = self.disease_model.config.id2label[idx]
            plant, disease = self._parse_disease_label(raw_label)
            results.append({
                "plant": plant,
                "disease": disease,
                "confidence": round(prob * 100, 2),
            })
        return results

    def predict_pests(self, image_path: str, conf: float = 0.25) -> list[dict]:
        """Returns pest detections with bounding boxes above the given confidence threshold."""
        results = self.pest_model.predict(source=image_path, conf=conf, verbose=False)
        detections = []
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                detections.append({
                    "pest": r.names[cls_id],
                    "confidence": round(float(box.conf[0]) * 100, 2),
                    "bbox_xyxy": [round(v, 1) for v in box.xyxy[0].tolist()],
                })
        return detections

    def predict(self, image_path: str) -> dict:
        """Runs both models on one image and returns a combined result dict."""
        image = Image.open(image_path).convert("RGB")
        return {
            "image": str(image_path),
            "disease_diagnosis": self.predict_disease(image),
            "pest_detections": self.predict_pests(image_path),
        }


def main():
    parser = argparse.ArgumentParser(
        description="CropForesight AI — disease + pest inference on a single image"
    )
    parser.add_argument("image", type=str, help="Path to a leaf/plant image")
    parser.add_argument("--top-k", type=int, default=3, help="Number of disease predictions to show")
    args = parser.parse_args()

    if not Path(args.image).exists():
        raise FileNotFoundError(f"Image not found: {args.image}")

    pipeline = CropForesightPipeline()
    result = pipeline.predict(args.image)

    print("=== Disease Diagnosis ===")
    for r in result["disease_diagnosis"][: args.top_k]:
        print(f"  {r['plant']} — {r['disease']}: {r['confidence']}%")

    print("\n=== Pest Detections ===")
    if result["pest_detections"]:
        for d in result["pest_detections"]:
            print(f"  {d['pest']}: {d['confidence']}%  (box: {d['bbox_xyxy']})")
    else:
        print("  No pests detected above the confidence threshold.")

    print("\n=== Cure / Next Step ===")
    top = result["disease_diagnosis"][0]
    image = Image.open(args.image).convert("RGB")
    care_response = get_care_response(
        image=image,
        plant=top["plant"],
        disease=top["disease"],
        confidence=top["confidence"],
    )
    if care_response["status"] == "healthy":
        print(f"  {care_response['message']}")
    elif care_response["status"] == "diagnosed":
        print(f"  Recommended treatment: {care_response['recommendation']}")
        print(f"  Cultural practice: {care_response['cultural_practice']}")
    else:  # escalated
        print(f"  {care_response['message']}")
        print(f"  Case ID: {care_response['case_id']}")


if __name__ == "__main__":
    main()
