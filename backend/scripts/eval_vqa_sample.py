"""Measure the pipeline on the PlantExpertVQA sample (380 labelled images) and tell you where to set the thresholds.

    python scripts/eval_vqa_sample.py --root "../datasets/samples/PlantExpertVQA_Sample" [--limit 50]

--root is the folder holding labels.csv, qa_annotations.csv and the crop folders. Writes results/vqa_sample_eval.csv.
Read the output with these caveats in mind:
  * 'PlantVillageVQA' images come from the dataset the model was trained on, so they flatter the model. Judge it by 'PlantVQA'.
  * Only crops/diseases inside the model's label space can be scored for accuracy. For everything else the question is
    different: does the system avoid a confident wrong answer and hand the case to an expert?
  * ~10 images per crop is a SMALL test set. Treat differences of a few points as noise.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_catalogue as bc  # noqa: E402
from app.services import care, catalogue, labels, quality  # noqa: E402


def true_label(folder_crop: str, raw_disease: str):
    """-> (crop_id, canonical disease or None if the dataset says 'unknown')"""
    folder = str(folder_crop).strip().lower()
    cid, _ = bc.CROP_MAP.get(folder, (folder.replace(" ", "_"), None))
    return cid, bc.canon_disease(cid, str(raw_disease))


def evaluate(root: Path, pipeline, limit: int | None = None) -> pd.DataFrame:
    lab = pd.read_csv(root / "labels.csv")
    qa = pd.read_csv(root / "qa_annotations.csv", usecols=["image_id", "dataset_source"])
    src = qa.groupby("image_id").dataset_source.first()
    lab["source"] = lab.image_id.map(src).fillna("unknown")
    if limit:
        lab = lab.sample(min(limit, len(lab)), random_state=0)
    by_crop = labels.classes_by_crop()
    rows = []
    for r in lab.itertuples():
        path = root / r.image_path
        if not path.exists() or str(r.crop).lower() == "unknown":
            continue
        img = Image.open(path).convert("RGB")
        cid, true_d = true_label(r.crop, r.disease)
        crop = catalogue.get_crop(cid)
        model_crop = crop["model_crop"] if crop else None
        supported = bool(crop and crop["ai_supported"])
        in_space = bool(supported and true_d and (true_d == "Healthy" or true_d in by_crop[model_crop]))
        try:
            ok = not quality.check(img)["warnings"]
        except quality.PhotoTooSmall:
            ok = False
        free = pipeline.predict_disease(img)[0]
        row = dict(image_id=r.image_id, source=r.source, crop_id=cid, true_disease=true_d, supported=supported, in_space=in_space,
                   free_crop=free["plant"], free_disease=free["disease"], free_conf=free["confidence"],
                   free_status=care.triage(free["plant"], free["disease"], free["confidence"], crop_selected=False, quality_ok=ok)[0])
        row["free_correct"] = bool(in_space and free["plant"] == model_crop and free["disease"] == true_d)
        row["free_crop_correct"] = bool(supported and free["plant"] == model_crop)
        if supported:
            m = pipeline.predict_disease(img, crop=model_crop)[0]
            row.update(masked_disease=m["disease"], masked_conf=m["confidence"],
                       masked_status=care.triage(m["plant"], m["disease"], m["confidence"], crop_selected=True, quality_ok=ok)[0])
            row["masked_correct"] = bool(in_space and m["disease"] == true_d)
        else:
            row.update(masked_disease=None, masked_conf=None, masked_status="escalated", masked_correct=False)   # unsupported crop -> expert
        rows.append(row)
    return pd.DataFrame(rows)


def summarise(df: pd.DataFrame) -> dict:
    out = {}
    s = df[df.in_space]
    out["accuracy_by_source"] = s.groupby("source").agg(
        n=("image_id", "size"), free_top1=("free_correct", "mean"), free_crop_right=("free_crop_correct", "mean"),
        crop_selected_top1=("masked_correct", "mean")).round(3)
    out["tiers_with_crop_selected"] = s.groupby("masked_status").agg(
        n=("image_id", "size"), correct=("masked_correct", "mean"), mean_conf=("masked_conf", "mean")).round(3)
    out["tiers_without_crop"] = s.groupby("free_status").agg(n=("image_id", "size"), correct=("free_correct", "mean")).round(3)
    sup_out = df[df.supported & ~df.in_space & df.true_disease.notna()]       # supported crop, disease the model cannot name
    out["out_of_label_space_supported_crops"] = sup_out.groupby("masked_status").size().rename("n").to_frame()
    out["unsupported_crops_to_expert_share"] = pd.Series({"images": int((~df.supported).sum()),
                                                          "sent_to_expert": int(((~df.supported) & (df.masked_status == "escalated")).sum())})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "results" / "vqa_sample_eval.csv"))
    a = ap.parse_args()
    from app.services.inference import CropForesightPipeline
    df = evaluate(Path(a.root), CropForesightPipeline(), a.limit)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.out, index=False)
    pd.set_option("display.width", 200)
    print(f"\n{len(df)} images scored; per-image results in {a.out}\n")
    for name, table in summarise(df).items():
        print(f"== {name}\n{table}\n")
    print("Use 'tiers_with_crop_selected' to choose thresholds: 'diagnosed' should be right far more often than 'likely'.")
    print("If 'diagnosed' is still wrong often, raise CONFIDENCE_THRESHOLD or keep everything at 'likely' until you fine-tune.")


if __name__ == "__main__":
    main()
