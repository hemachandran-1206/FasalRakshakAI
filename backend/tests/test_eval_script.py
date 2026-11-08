import sys
from pathlib import Path

import pandas as pd
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import eval_vqa_sample as ev  # noqa: E402


class Stub:
    """Always says Tomato / Late Blight, 90% (crop restriction changes nothing here)."""
    def predict_disease(self, image, top_k=3, crop=None):
        return [{"plant": "Tomato", "disease": "Late Blight", "confidence": 90.0}]


def test_true_label_mapping():
    assert ev.true_label("pepper bell", "healthy") == ("pepper", "Healthy")
    assert ev.true_label("peas", "ascochyta blight") == ("pea", "Ascochyta Blight")
    assert ev.true_label("apple", "unknown") == ("apple", None)
    assert ev.true_label("grape", "leaf blight") == ("grape", "Leaf Blight (Isariopsis Leaf Spot)")


def test_evaluate_and_summarise_on_a_tiny_synthetic_sample(tmp_path):
    (tmp_path / "tomato").mkdir(); (tmp_path / "rice").mkdir(); (tmp_path / "grape").mkdir()
    import random
    rnd = random.Random(0)
    def img(p):
        im = Image.new("RGB", (260, 260)); im.putdata([(rnd.randrange(256),) * 3 for _ in range(260 * 260)]); im.save(p)
    rows = [("t1.jpg", "tomato", "late blight"), ("t2.jpg", "tomato", "early blight"), ("r1.jpg", "rice", "blast"),
            ("g1.jpg", "grape", "downy mildew"), ("t3.jpg", "tomato", "unknown")]
    for f, c, d in rows:
        img(tmp_path / c / f)
    pd.DataFrame([dict(image_id=f, filename=f, crop=c, disease=d, category="disease", severity="UNKNOWN", image_path=f"{c}/{f}")
                  for f, c, d in rows]).to_csv(tmp_path / "labels.csv", index=False)
    pd.DataFrame([dict(image_id=f, dataset_source="PlantVQA") for f, _, _ in rows]).to_csv(tmp_path / "qa_annotations.csv", index=False)

    df = ev.evaluate(tmp_path, Stub())
    assert len(df) == 5
    t1 = df[df.image_id == "t1.jpg"].iloc[0]
    assert t1.in_space and t1.free_correct and t1.masked_correct and t1.masked_status == "diagnosed" and t1.free_status == "likely"
    assert not df[df.image_id == "t2.jpg"].iloc[0].masked_correct                      # stub says late blight, truth early blight
    assert df[df.image_id == "r1.jpg"].iloc[0].masked_status == "escalated"            # rice: unsupported -> expert
    g1 = df[df.image_id == "g1.jpg"].iloc[0]
    assert g1.supported and not g1.in_space                                           # grape downy mildew is outside the label space

    s = ev.summarise(df)
    assert s["accuracy_by_source"].loc["PlantVQA", "n"] == 2
    assert s["accuracy_by_source"].loc["PlantVQA", "crop_selected_top1"] == 0.5
    assert s["unsupported_crops_to_expert_share"]["sent_to_expert"] == 1
