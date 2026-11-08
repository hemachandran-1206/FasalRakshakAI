import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import care, catalogue, labels, treatments

# the raw class names of the PlantVillage MobileNetV2 checkpoint, in class-id order (from your stage-1 notebook output)
RAW = ["Apple Scab", "Apple with Black Rot", "Cedar Apple Rust", "Healthy Apple", "Healthy Blueberry Plant",
       "Cherry with Powdery Mildew", "Healthy Cherry Plant", "Corn (Maize) with Cercospora and Gray Leaf Spot",
       "Corn (Maize) with Common Rust", "Corn (Maize) with Northern Leaf Blight", "Healthy Corn (Maize) Plant",
       "Grape with Black Rot", "Grape with Esca (Black Measles)", "Grape with Isariopsis Leaf Spot", "Healthy Grape Plant",
       "Orange with Citrus Greening", "Peach with Bacterial Spot", "Healthy Peach Plant", "Bell Pepper with Bacterial Spot",
       "Healthy Bell Pepper Plant", "Potato with Early Blight", "Potato with Late Blight", "Healthy Potato Plant",
       "Healthy Raspberry Plant", "Healthy Soybean Plant", "Squash with Powdery Mildew", "Strawberry with Leaf Scorch",
       "Healthy Strawberry Plant", "Tomato with Bacterial Spot", "Tomato with Early Blight", "Tomato with Late Blight",
       "Tomato with Leaf Mold", "Tomato with Septoria Leaf Spot", "Tomato with Spider Mites",
       "Tomato with Target Spot", "Tomato with Yellow Leaf Curl Virus", "Tomato with Mosaic Virus", "Healthy Tomato Plant"]


def test_label_table_matches_the_checkpoint_and_rejects_a_mismatch():
    labels.validate_against(dict(enumerate(RAW)))
    bad = dict(enumerate(RAW)); bad[3], bad[4] = bad[4], bad[3]
    with pytest.raises(RuntimeError):
        labels.validate_against(bad)
    with pytest.raises(RuntimeError):
        labels.validate_against({0: "x"})


def test_every_disease_class_has_stored_advice_and_healthy_is_recognised():
    for crop, disease in labels.CANONICAL.values():
        if disease == "Healthy":
            assert treatments.is_healthy_label(disease)
        else:
            assert treatments.get_treatment(crop, disease), f"no advice for {crop} / {disease}"


def test_only_crops_with_a_real_choice_are_ai_supported():
    assert labels.assessable_crops() == {"Apple", "Cherry", "Corn", "Grape", "Peach", "Pepper", "Potato", "Strawberry", "Tomato"}
    flags = {c["id"]: c["ai_supported"] for c in catalogue.crops()}
    assert flags["tomato"] and flags["corn"] and not flags["rice"] and not flags["wheat"] and not flags["citrus"] and not flags["squash"]


def test_catalogue_aliases_and_canonical_names():
    assert catalogue.get_crop("Peas")["id"] == "pea" and catalogue.get_crop("pepper bell")["id"] == "pepper"
    assert catalogue.get_crop("Eggplant (Brinjal)")["id"] == "eggplant" and catalogue.get_crop("nonsense") is None
    assert catalogue.canonical_crop_name(" tomato ") == "Tomato" and catalogue.canonical_crop_name("Dragonfruit") == "Dragonfruit"
    assert catalogue.canonical_disease_name("tomato", "late BLIGHT") == "Late Blight"
    assert catalogue.canonical_disease_name("wheat", "yellow rust (stripe rust)") == "Yellow Rust (Stripe Rust)"
    assert catalogue.canonical_disease_name("tomato", "Brand New Rot") == "Brand New Rot"


def test_catalogue_endpoint():
    r = TestClient(app).get("/api/catalogue").json()["crops"]
    tomato = next(c for c in r if c["id"] == "tomato")
    assert tomato["ai_supported"] and "Late Blight" in tomato["diseases"] and any(c["id"] == "wheat" for c in r)


@pytest.mark.parametrize("conf,crop_sel,ok,expected", [
    (95, True, True, ("diagnosed", None)), (95, False, True, ("likely", "crop_not_selected")),
    (95, True, False, ("likely", "poor_photo")), (55, True, True, ("likely", "medium_confidence")),
    (39.9, True, True, ("escalated", "low_confidence")), (40, True, True, ("likely", "medium_confidence")),
    (70, True, True, ("diagnosed", None))])
def test_triage_table(conf, crop_sel, ok, expected):
    assert care.triage("Tomato", "Late Blight", conf, crop_selected=crop_sel, quality_ok=ok) == expected


def test_unknown_disease_without_advice_escalates_even_when_confident():
    assert care.triage("Tomato", "Some New Disease", 95, crop_selected=True, quality_ok=True) == ("escalated", "no_advice")
