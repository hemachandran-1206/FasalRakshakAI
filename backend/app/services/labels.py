"""Canonical (crop, disease) for each of the 38 classes of the PlantVillage MobileNetV2 checkpoint.

The original `_parse_disease_label` could not read 16 of the 38 raw labels (e.g. 'Healthy Apple', 'Apple Scab',
'Cedar Apple Rust') and treated all 12 'Healthy ...' classes as unknown diseases, so healthy leaves were escalated
to experts. This table (validated in your notebook, stage 1) replaces the parsing. Index = model class id."""

CANONICAL = {
    0: ("Apple", "Apple Scab"),              1: ("Apple", "Black Rot"),
    2: ("Apple", "Cedar Apple Rust"),        3: ("Apple", "Healthy"),
    4: ("Blueberry", "Healthy"),             5: ("Cherry", "Powdery Mildew"),
    6: ("Cherry", "Healthy"),
    7: ("Corn", "Cercospora Leaf Spot (Gray Leaf Spot)"),
    8: ("Corn", "Common Rust"),              9: ("Corn", "Northern Leaf Blight"),
    10: ("Corn", "Healthy"),                 11: ("Grape", "Black Rot"),
    12: ("Grape", "Esca (Black Measles)"),
    13: ("Grape", "Leaf Blight (Isariopsis Leaf Spot)"),
    14: ("Grape", "Healthy"),
    15: ("Orange", "Haunglongbing (Citrus Greening)"),
    16: ("Peach", "Bacterial Spot"),         17: ("Peach", "Healthy"),
    18: ("Pepper", "Bacterial Spot"),        19: ("Pepper", "Healthy"),
    20: ("Potato", "Early Blight"),          21: ("Potato", "Late Blight"),
    22: ("Potato", "Healthy"),               23: ("Raspberry", "Healthy"),
    24: ("Soybean", "Healthy"),              25: ("Squash", "Powdery Mildew"),
    26: ("Strawberry", "Leaf Scorch"),       27: ("Strawberry", "Healthy"),
    28: ("Tomato", "Bacterial Spot"),        29: ("Tomato", "Early Blight"),
    30: ("Tomato", "Late Blight"),           31: ("Tomato", "Leaf Mold"),
    32: ("Tomato", "Septoria Leaf Spot"),
    33: ("Tomato", "Spider Mites (Two-Spotted Spider Mite)"),
    34: ("Tomato", "Target Spot"),
    35: ("Tomato", "Tomato Yellow Leaf Curl Virus"),
    36: ("Tomato", "Tomato Mosaic Virus"),   37: ("Tomato", "Healthy"),
}


def validate_against(id2label: dict) -> None:
    """Fail loudly at startup if the checkpoint's classes are not the ones this table was written for."""
    if len(id2label) != len(CANONICAL):
        raise RuntimeError(f"model has {len(id2label)} classes, label table has {len(CANONICAL)}")
    for i, (crop, disease) in CANONICAL.items():
        raw = id2label[i].lower()
        if crop.lower() not in raw and not (crop == "Corn" and "corn" in raw):
            raise RuntimeError(f"class {i} '{id2label[i]}' does not match canonical crop '{crop}'")
        if (disease == "Healthy") != ("healthy" in raw):
            raise RuntimeError(f"class {i} '{id2label[i]}' healthy flag disagrees with the label table")


def classes_by_crop() -> dict:
    out: dict = {}
    for crop, disease in CANONICAL.values():
        out.setdefault(crop, []).append(disease)
    return out


def assessable_crops() -> set:
    """Crops where crop-restricted prediction is meaningful: at least 2 classes, at least one a disease.
    (Orange, Squash, Blueberry, Raspberry, Soybean have a single class, so the model could only ever echo it.)"""
    return {c for c, ds in classes_by_crop().items() if len(ds) >= 2 and any(d != "Healthy" for d in ds)}
