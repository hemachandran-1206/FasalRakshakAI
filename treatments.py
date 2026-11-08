"""
treatments.py — crop disease treatment knowledge base (SIH26131)

Maps each (plant, disease) pair the disease classifier can output to a
treatment recommendation. Deliberately avoids exact chemical dosages --
product approval and dosage vary by state and crop stage, so every
recommendation ends with a prompt to confirm specifics with a local Krishi
Vigyan Kendra (KVK) or agricultural extension officer. The AI's job is
triage + general guidance; a human expert handles anything specific or
anything not yet in this knowledge base.

Lookups are normalized (lowercased, punctuation stripped) so small
formatting differences in how a label comes out of the model
("Corn (maize)" vs "corn_maize" vs "Corn Maize") don't cause a false miss.

Entries added by an expert via expert_dashboard.py are persisted to
data/treatments_overrides.json and checked first on every lookup -- this
is the "update our knowledge base" feedback loop.
"""

import json
import re
from pathlib import Path
from typing import Optional

DISCLAIMER = (
    "Confirm the exact product and dosage with your local Krishi Vigyan "
    "Kendra (KVK) or agricultural extension officer before applying."
)

OVERRIDES_FILE = Path("data") / "treatments_overrides.json"


def _normalize(text: str) -> str:
    """Lowercase and strip everything except letters/digits."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


# Built-in knowledge base: the 26 diseases the PlantVillage-trained disease
# model can output. General guidance only -- see DISCLAIMER above.
# Format: (plant, disease, type, recommendation, cultural_practice)
_RAW_ENTRIES = [
    ("Apple", "Apple Scab", "fungal",
     f"Apply a protectant fungicide (captan- or mancozeb-based) starting at bud break, repeating every 7-10 days during wet spring weather. {DISCLAIMER}",
     "Rake and destroy fallen leaves in autumn to reduce overwintering spores; prune for better air circulation."),
    ("Apple", "Black Rot", "fungal",
     f"Apply a copper- or captan-based fungicide during the growing season, especially after hail or pruning wounds. {DISCLAIMER}",
     "Remove mummified fruit and cankered wood, which harbor the fungus over winter."),
    ("Apple", "Cedar Apple Rust", "fungal",
     f"Apply a protectant fungicide (myclobutanil- or mancozeb-based) from pink bud stage through early summer. {DISCLAIMER}",
     "Remove nearby juniper/cedar trees where possible -- they host the alternate stage of this fungus."),
    ("Cherry", "Powdery Mildew", "fungal",
     f"Apply a sulfur-based or systemic fungicide (e.g. myclobutanil) at first sign of white powdery patches. {DISCLAIMER}",
     "Prune for airflow and avoid excess nitrogen fertilization, which encourages the soft new growth the fungus favors."),
    ("Corn", "Cercospora Leaf Spot Gray Leaf Spot", "fungal",
     f"A foliar fungicide (strobilurin or triazole class) is usually only justified for severe outbreaks on susceptible hybrids. {DISCLAIMER}",
     "Rotate crops, till under infected residue, and plant resistant hybrids -- this disease survives in crop debris."),
    ("Corn", "Common Rust", "fungal",
     f"Fungicide treatment (triazole/strobilurin) is rarely needed except in severe outbreaks. {DISCLAIMER}",
     "Plant resistant hybrids and avoid very late planting, which exposes young plants to peak rust spore periods."),
    ("Corn", "Northern Leaf Blight", "fungal",
     f"A foliar fungicide can help if caught early on a susceptible hybrid, but resistant hybrids are the primary defense. {DISCLAIMER}",
     "Rotate crops and manage residue -- the fungus overwinters in old corn debris."),
    ("Grape", "Black Rot", "fungal",
     f"Apply a protectant fungicide (mancozeb- or myclobutanil-based) from early shoot growth through veraison. {DISCLAIMER}",
     "Remove mummified berries and infected canes during dormant pruning -- they're the main source of reinfection."),
    ("Grape", "Esca Black Measles", "fungal",
     "There is no curative fungicide once a vine is infected with this trunk disease.",
     "Prune out and destroy infected wood, avoid large pruning cuts in wet weather, and protect fresh wounds."),
    ("Grape", "Leaf Blight Isariopsis Leaf Spot", "fungal",
     f"A copper-based fungicide can help manage outbreaks. {DISCLAIMER}",
     "Improve canopy airflow through leaf pulling/pruning and remove fallen infected leaves."),
    ("Orange", "Haunglongbing Citrus Greening", "bacterial",
     "There is currently no cure for this disease once a tree is infected.",
     "Control the Asian citrus psyllid vector with locally recommended insecticides, remove and destroy infected trees promptly to limit spread, and only plant certified disease-free nursery stock."),
    ("Peach", "Bacterial Spot", "bacterial",
     f"Apply copper-based bactericide sprays during dormancy and early season. {DISCLAIMER}",
     "Plant resistant varieties where available and avoid overhead irrigation, which spreads the bacteria."),
    ("Pepper", "Bacterial Spot", "bacterial",
     f"Apply a copper-based bactericide, often combined with mancozeb to slow resistance buildup. {DISCLAIMER}",
     "Use certified disease-free seed/transplants, avoid working fields when foliage is wet, and rotate crops."),
    ("Potato", "Early Blight", "fungal",
     f"Apply a chlorothalonil- or mancozeb-based fungicide on a 7-10 day schedule once symptoms appear. {DISCLAIMER}",
     "Rotate crops, avoid water stress, and maintain balanced fertilization -- stressed plants are more susceptible."),
    ("Potato", "Late Blight", "fungal",
     f"Apply a copper-based or systemic fungicide (e.g. a metalaxyl + mancozeb combination) promptly and preventatively during cool, wet weather. {DISCLAIMER}",
     "Destroy volunteer potatoes and infected tubers, avoid overhead irrigation, and use certified disease-free seed potatoes -- this disease can destroy a crop very fast."),
    ("Squash", "Powdery Mildew", "fungal",
     f"Apply a sulfur- or potassium-bicarbonate-based fungicide at first sign of white patches. {DISCLAIMER}",
     "Plant resistant varieties and ensure good spacing/airflow between plants."),
    ("Strawberry", "Leaf Scorch", "fungal",
     f"Apply a fungicide (captan- or myclobutanil-based) during wet periods. {DISCLAIMER}",
     "Remove old infected leaves after harvest and avoid overhead watering."),
    ("Tomato", "Bacterial Spot", "bacterial",
     f"Apply a copper-based bactericide, often combined with mancozeb. {DISCLAIMER}",
     "Use disease-free seed/transplants, avoid overhead watering, and rotate crops."),
    ("Tomato", "Early Blight", "fungal",
     f"Apply a chlorothalonil- or mancozeb-based fungicide on a 7-10 day schedule. {DISCLAIMER}",
     "Remove and destroy lower infected leaves, and mulch around the base to reduce soil splash onto foliage."),
    ("Tomato", "Late Blight", "fungal",
     f"Apply a copper-based or systemic fungicide immediately -- this disease can destroy a crop within days in cool, wet weather. {DISCLAIMER}",
     "Remove and destroy infected plants quickly to stop it spreading, avoid overhead watering, and improve airflow."),
    ("Tomato", "Leaf Mold", "fungal",
     f"Apply a chlorothalonil-based fungicide, especially in humid/greenhouse conditions. {DISCLAIMER}",
     "Improve ventilation, reduce humidity, and avoid overhead watering."),
    ("Tomato", "Septoria Leaf Spot", "fungal",
     f"Apply a chlorothalonil- or copper-based fungicide. {DISCLAIMER}",
     "Remove lower infected leaves, mulch, and rotate crops -- the fungus survives in soil debris."),
    ("Tomato", "Spider Mites Two Spotted Spider Mite", "pest",
     f"Apply a miticide (e.g. abamectin-based) for heavy infestations, or insecticidal soap/neem oil for lighter ones. {DISCLAIMER}",
     "Encourage natural predators (predatory mites) and avoid drought-stressing plants, which favors mite outbreaks."),
    ("Tomato", "Target Spot", "fungal",
     f"Apply a chlorothalonil-based fungicide. {DISCLAIMER}",
     "Rotate crops, remove infected plant debris, and improve airflow around plants."),
    ("Tomato", "Tomato Yellow Leaf Curl Virus", "viral",
     "There is no chemical cure for this virus once a plant is infected.",
     "Control the whitefly vector that spreads it, remove and destroy infected plants promptly, use resistant/tolerant varieties, and consider reflective mulches to deter whiteflies."),
    ("Tomato", "Tomato Mosaic Virus", "viral",
     "There is no chemical cure for this virus once a plant is infected.",
     "Remove and destroy infected plants, disinfect hands/tools between plants (it spreads easily by contact, including via tobacco products), and use resistant varieties."),
]

_BUILTIN = {}
for _plant, _disease, _dtype, _rec, _cultural in _RAW_ENTRIES:
    _BUILTIN[(_normalize(_plant), _normalize(_disease))] = {
        "plant": _plant,
        "disease": _disease,
        "type": _dtype,
        "recommendation": _rec,
        "cultural_practice": _cultural,
    }


def _load_overrides() -> dict:
    if OVERRIDES_FILE.exists():
        try:
            return json.loads(OVERRIDES_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _save_overrides(overrides: dict) -> None:
    OVERRIDES_FILE.parent.mkdir(parents=True, exist_ok=True)
    OVERRIDES_FILE.write_text(json.dumps(overrides, indent=2))


def is_healthy_label(disease: str) -> bool:
    return _normalize(disease) == _normalize("healthy")


def get_treatment(plant: str, disease: str) -> Optional[dict]:
    """
    Looks up treatment info for a (plant, disease) pair. Checks
    expert-added entries first (an expert's answer can correct/replace a
    built-in one), then falls back to the built-in knowledge base.
    Returns None if nothing is known -- the caller should escalate to a
    human expert in that case.
    """
    key = f"{_normalize(plant)}|{_normalize(disease)}"
    overrides = _load_overrides()
    if key in overrides:
        return overrides[key]

    return _BUILTIN.get((_normalize(plant), _normalize(disease)))


def add_treatment(plant: str, disease: str, recommendation: str, cultural_practice: str) -> None:
    """
    Called by expert_dashboard.py when a human expert resolves a case the
    AI couldn't handle. Persists the new knowledge to disk so future
    diagnoses of the same (plant, disease) are answered automatically
    instead of being escalated again.
    """
    overrides = _load_overrides()
    key = f"{_normalize(plant)}|{_normalize(disease)}"
    overrides[key] = {
        "plant": plant,
        "disease": disease,
        "type": "expert-provided",
        "recommendation": recommendation,
        "cultural_practice": cultural_practice,
    }
    _save_overrides(overrides)
