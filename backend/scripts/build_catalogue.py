"""Build app/data/catalogue.json (crops, aliases, diseases, AI-support flag) from the PlantExpertVQA sample's labels.csv.
    python scripts/build_catalogue.py path/to/labels.csv
Re-run whenever you get a bigger labels file. Manual additions (Punjab crops absent from the sample) are in EXTRA_CROPS."""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services import labels  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "app" / "data" / "catalogue.json"

# dataset folder name -> (crop id, display name)
CROP_MAP = {
    "pea": ("pea", "Pea"), "peas": ("pea", "Pea"),
    "pepper": ("pepper", "Pepper / Capsicum"), "pepper bell": ("pepper", "Pepper / Capsicum"),
    "eggplant": ("eggplant", "Eggplant (Brinjal)"), "eggplant brinjal": ("eggplant", "Eggplant (Brinjal)"),
    "citrus": ("citrus", "Citrus (orange, lemon, kinnow)"), "orange": ("citrus", "Citrus (orange, lemon, kinnow)"),
    "lemon": ("citrus", "Citrus (orange, lemon, kinnow)"),
    "corn": ("corn", "Corn (Maize)"), "bitter gourd": ("bitter_gourd", "Bitter gourd"),
    "bottle gourd": ("bottle_gourd", "Bottle gourd"), "arabian jasmine": ("jasmine", "Jasmine"),
}
MODEL_CROP = {"apple": "Apple", "blueberry": "Blueberry", "cherry": "Cherry", "corn": "Corn", "grape": "Grape",
              "citrus": "Orange", "peach": "Peach", "pepper": "Pepper", "potato": "Potato", "raspberry": "Raspberry",
              "soybean": "Soybean", "squash": "Squash", "strawberry": "Strawberry", "tomato": "Tomato"}

# dataset disease text -> canonical name (model class names are reused so the AI label space and the catalogue agree)
DISEASE_MAP = {
    ("apple", "scab"): "Apple Scab", ("apple", "rust"): "Cedar Apple Rust", ("apple", "black rot"): "Black Rot",
    ("grape", "black rot"): "Black Rot", ("grape", "leaf blight"): "Leaf Blight (Isariopsis Leaf Spot)",
    ("grape", "isariopsis leaf spot"): "Leaf Blight (Isariopsis Leaf Spot)",
    ("citrus", "huanglongbing"): "Haunglongbing (Citrus Greening)",
    ("tomato", "yellow leaf curl virus"): "Tomato Yellow Leaf Curl Virus",
    ("tomato", "spider mites"): "Spider Mites (Two-Spotted Spider Mite)",
    ("tomato", "mosaic virus"): "Tomato Mosaic Virus",
    ("corn", "maize streak virus"): "Maize Streak Virus", ("corn", "maize lethal necrosis"): "Maize Lethal Necrosis",
    ("bitter_gourd", "gourd anthracnose"): "Anthracnose", ("bitter_gourd", "gourd downy mildew"): "Downy Mildew",
    ("bottle_gourd", "gourd anthracnose"): "Anthracnose", ("jasmine", "jasmine anthracnose"): "Anthracnose",
    ("cotton", "leaf hopper jassids"): "Leaf Hopper (Jassids)",
}
SKIP = {"unknown"}                                      # no ground truth
NON_DISEASE = {"senescence": "Natural senescence", "senescence or dry": "Natural senescence", "natural_senescence": "Natural senescence",
               "nutritional deficiency": "Nutritional deficiency", "wilted": "Wilting (cause unclear)"}

# Punjab crops / diseases missing from the sample. Used ONLY as dropdown suggestions for experts; they carry no advice.
# Verify against PAU's package of practices before relying on them.
EXTRA_CROPS = {
    "wheat": ("Wheat", ["Yellow Rust (Stripe Rust)", "Brown Rust (Leaf Rust)", "Powdery Mildew", "Karnal Bunt", "Loose Smut"]),
    "mustard": ("Mustard", ["Alternaria Blight", "White Rust", "Powdery Mildew", "Downy Mildew"]),
    "sugarcane": ("Sugarcane", ["Red Rot", "Smut", "Pokkah Boeng"]),
}


def canon_disease(crop_id: str, raw: str) -> str | None:
    d = raw.strip().lower()
    if d in SKIP:
        return None
    if d == "healthy":
        return "Healthy"
    if d in NON_DISEASE:
        return NON_DISEASE[d]
    if (crop_id, d) in DISEASE_MAP:
        return DISEASE_MAP[(crop_id, d)]
    return d.title()


def main(labels_csv: str):
    df = pd.read_csv(labels_csv)
    crops: dict = {}
    counts, diseases, aliases = Counter(), defaultdict(set), defaultdict(set)
    for _, r in df.iterrows():
        folder = str(r.crop).strip().lower()
        if folder == "unknown":
            continue
        cid, name = CROP_MAP.get(folder, (folder.replace(" ", "_"), folder.title()))
        crops[cid] = name
        aliases[cid] |= {folder, cid, name.lower()}
        counts[cid] += 1
        d = canon_disease(cid, str(r.disease))
        if d:
            diseases[cid].add(d)

    supported = labels.assessable_crops()
    for cid, mc in MODEL_CROP.items():              # make sure every AI class is in the list, even if absent from the sample
        crops.setdefault(cid, mc)
        diseases[cid] |= {d for d in labels.classes_by_crop()[mc]}
    out = []
    for cid, name in sorted(crops.items(), key=lambda kv: kv[1]):
        mc = MODEL_CROP.get(cid)
        out.append({"id": cid, "name": name, "model_crop": mc, "ai_supported": bool(mc and mc in supported),
                    "aliases": sorted(aliases[cid] | {cid, name.lower()}),
                    "diseases": sorted(d for d in diseases[cid] if d != "Healthy") + (["Healthy"] if "Healthy" in diseases[cid] else []),
                    "sample_images": counts[cid], "source": "dataset"})
    for cid, (name, ds) in EXTRA_CROPS.items():
        out.append({"id": cid, "name": name, "model_crop": None, "ai_supported": False, "aliases": [cid, name.lower()],
                    "diseases": sorted(ds) + ["Healthy"], "sample_images": 0, "source": "manual (verify with PAU)"})
    out.sort(key=lambda c: c["name"])
    payload = {"version": 1, "generated_from": "PlantExpertVQA sample labels.csv + manual Punjab additions", "crops": out}
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False))
    sup = [c["name"] for c in out if c["ai_supported"]]
    print(f"{len(out)} crops written to {OUT}\nAI-supported ({len(sup)}): {', '.join(sup)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "labels.csv")
