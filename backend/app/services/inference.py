"""Disease classifier (MobileNetV2) + pest detector (YOLO11). Adapted from the original inference.py:
no dependency on care_advisor, and pest detection runs on an in-memory PIL image (no temp file)."""
from __future__ import annotations

from typing import Optional

from PIL import Image

from .labels import CANONICAL, validate_against

DISEASE_MODEL_NAME = "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification"
PEST_MODEL_REPO = "Yudsky/pest-detection-yolo11"
PEST_MODEL_FILE = "best.pt"


class CropForesightPipeline:
    def __init__(self, device: Optional[str] = None):
        # heavy imports kept inside so tests / tooling can import this module without torch installed
        import torch
        from huggingface_hub import hf_hub_download
        from transformers import MobileNetV2ForImageClassification, MobileNetV2ImageProcessor
        from ultralytics import YOLO

        self.torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.disease_processor = MobileNetV2ImageProcessor.from_pretrained(DISEASE_MODEL_NAME)
        self.disease_model = MobileNetV2ForImageClassification.from_pretrained(DISEASE_MODEL_NAME)
        validate_against(self.disease_model.config.id2label)
        self.disease_model.to(self.device).eval()
        self.pest_model = YOLO(hf_hub_download(repo_id=PEST_MODEL_REPO, filename=PEST_MODEL_FILE))

    def predict_disease(self, image: Image.Image, top_k: int = 3, crop: Optional[str] = None) -> list[dict]:
        """Top-k (plant, disease, confidence %). If `crop` (a model crop name such as 'Tomato') is given, classes of
        other crops are masked out before the softmax, so the model can only choose between that crop's classes."""
        torch = self.torch
        inputs = self.disease_processor(images=image, return_tensors="pt").to(self.device)
        with torch.no_grad():
            logits = self.disease_model(**inputs).logits[0]
        if crop:
            keep = torch.tensor([CANONICAL[i][0].lower() == crop.lower() for i in range(len(CANONICAL))], device=logits.device)
            if not keep.any():
                raise ValueError(f"no model classes for crop '{crop}'")
            logits = logits.masked_fill(~keep, float("-inf"))
        probs = torch.softmax(logits, dim=-1)
        top_probs, top_idxs = torch.topk(probs, k=min(top_k, int((probs > 0).sum())))
        return [{"plant": CANONICAL[i][0], "disease": CANONICAL[i][1], "confidence": round(p * 100, 2)}
                for p, i in zip(top_probs.tolist(), top_idxs.tolist())]

    def predict_pests(self, image: Image.Image, conf: float = 0.25) -> list[dict]:
        results = self.pest_model.predict(source=image, conf=conf, verbose=False,
                                          device=0 if self.device == "cuda" else "cpu")
        dets = []
        for r in results:
            for box in r.boxes:
                dets.append({
                    "pest": r.names[int(box.cls[0])],
                    "confidence": round(float(box.conf[0]) * 100, 2),
                    "bbox_xyxy": [round(v, 1) for v in box.xyxy[0].tolist()],
                })
        return dets
