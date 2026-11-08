import pytest
from fastapi.testclient import TestClient

from app import db as dbmod
from app.main import app
from app.models import Advisory, Detection, ExpertReview, User
from app.services import advisories, i18n, security
from tests.test_cases import PW, make

HI = {"crop": "Potato", "disease": "Late Blight", "language": "hi",
      "management": "हिंदी प्रबंधन सलाह", "prevention": "हिंदी रोकथाम", "source": "PAU"}


@pytest.fixture
def c():
    return TestClient(app)


def user(role, email):
    with dbmod.SessionLocal() as s:
        u = User(email=email, full_name=email.split("@")[0], role=role, password_hash=security.hash_password(PW))
        s.add(u); s.commit()


def auth(c, email):
    tok = c.post("/api/auth/login", data={"username": email, "password": PW}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_draft_is_never_served_then_verified_is(c):
    make()
    user("admin", "a@x.org")
    h = auth(c, "a@x.org")
    r = c.put("/api/admin/advisories", json=HI, headers=h)
    assert r.status_code == 200 and r.json()["verification_status"] == "draft"
    # draft hi -> farmer still sees English + pending note
    care = c.get("/api/cases/K7M2-QX9P?lang=hi").json()["ai"]["care"]
    assert "fungicide" in care["recommendation"] and care["translation_pending"] is True and care["translation_note"]
    assert c.post(f"/api/admin/advisories/{r.json()['id']}/verify", headers=h).json()["verification_status"] == "verified"
    care = c.get("/api/cases/K7M2-QX9P?lang=hi").json()["ai"]["care"]
    assert care["recommendation"] == HI["management"] and care["language"] == "hi" and care["translation_pending"] is False
    assert "fungicide" in c.get("/api/cases/K7M2-QX9P").json()["ai"]["care"]["recommendation"]     # default stays English


def test_editing_verified_row_returns_to_draft(c):
    make()
    user("admin", "a@x.org")
    h = auth(c, "a@x.org")
    aid = c.put("/api/admin/advisories", json=HI, headers=h).json()["id"]
    c.post(f"/api/admin/advisories/{aid}/verify", headers=h)
    c.put("/api/admin/advisories", json={**HI, "management": "बदला हुआ"}, headers=h)
    assert c.get("/api/advisories/Potato/Late Blight?lang=hi").json()["translation_pending"] is True


def test_verify_needs_both_fields_and_staff_only(c):
    user("admin", "a@x.org")
    h = auth(c, "a@x.org")
    aid = c.put("/api/admin/advisories", json={**HI, "prevention": ""}, headers=h).json()["id"]
    assert c.post(f"/api/admin/advisories/{aid}/verify", headers=h).status_code == 422
    assert c.get("/api/admin/advisories").status_code == 401
    assert c.put("/api/admin/advisories", json=HI).status_code == 401


def test_unknown_language_falls_back_to_english_and_bad_language_rejected(c):
    make()
    assert c.get("/api/cases/K7M2-QX9P?lang=fr").json()["ai"]["care"]["status"] == "diagnosed"
    user("admin", "a@x.org")
    assert c.put("/api/admin/advisories", json={**HI, "language": "fr"}, headers=auth(c, "a@x.org")).status_code == 422


def test_fixed_messages_translated_and_complete():
    for key, by_lang in i18n.TEXT.items():
        assert set(by_lang) == set(i18n.LANGS), key
        if key != "translation_pending":
            assert all(by_lang.values()), key
    make_c = TestClient(app)
    make(status="pending")
    assert make_c.get("/api/cases/K7M2-QX9P?lang=pa").json()["message"] == i18n.TEXT["case_awaiting_review"]["pa"]
    assert make_c.get("/api/cases/K7M2-QX9P").json()["message"] == i18n.TEXT["case_awaiting_review"]["en"]


def test_public_advisory_endpoint_and_languages(c):
    assert [l["code"] for l in c.get("/api/languages").json()] == ["en", "hi", "pa"]
    assert c.get("/api/advisories/Potato/Late Blight?lang=pa").json()["language"] == "en"
    assert c.get("/api/advisories/Potato/Nonexistent?lang=en").status_code == 404


def test_csv_export_import_roundtrip_makes_drafts(c):
    user("admin", "a@x.org")
    h = auth(c, "a@x.org")
    csv_text = c.get("/api/admin/advisories/export.csv", headers=h).text
    assert "Late Blight,hi" in csv_text and csv_text.count("\n") > 26 * 3
    filled = csv_text.replace("Potato,Late Blight,hi,,,,,", "Potato,Late Blight,hi,,रोकथाम,प्रबंधन,PAU,")
    r = c.post("/api/admin/advisories/import", files={"file": ("a.csv", filled.encode(), "text/csv")}, headers=h).json()
    assert r["errors"] == [] and r["imported_as_draft"] >= 26      # all English template rows + the filled hi row
    rows = c.get("/api/admin/advisories?language=hi", headers=h).json()
    assert len(rows) == 1 and rows[0]["verification_status"] == "draft"
    assert c.post("/api/admin/advisories/import", files={"file": ("a.csv", b"foo,bar\n1,2", "text/csv")}, headers=h).status_code == 422


def test_import_is_admin_only(c):
    user("expert", "e@x.org")
    assert c.post("/api/admin/advisories/import", files={"file": ("a.csv", b"x", "text/csv")}, headers=auth(c, "e@x.org")).status_code == 403


def test_expert_advice_becomes_english_draft_without_overwriting(c):
    make(crop="Potato", disease="Early Blight", status="assigned")
    user("admin", "a@x.org"); user("expert", "e@x.org")
    with dbmod.SessionLocal() as s:
        e = s.query(User).filter_by(email="e@x.org").one()
        s.query(ExpertReview).update({"assigned_expert_id": e.id}); s.commit()
        rid = s.query(ExpertReview).one().id
    h = auth(c, "e@x.org")
    r = c.post(f"/api/expert/reviews/{rid}/decision", headers=h, json={
        "decision": "correct", "crop": "Tomato", "disease": "Leaf Mold", "advice_management": "Improve ventilation."})
    assert r.status_code == 422                                     # both fields or neither
    r = c.post(f"/api/expert/reviews/{rid}/decision", headers=h, json={
        "decision": "correct", "crop": "Tomato", "disease": "Leaf Mold", "advice_management": "Improve ventilation.",
        "advice_prevention": "Space plants."})
    assert r.status_code == 200
    with dbmod.SessionLocal() as s:
        adv = s.query(Advisory).one()
        assert (adv.language, adv.verification_status, adv.management) == ("en", "draft", "Improve ventilation.")
        assert advisories.suggest_from_expert(s, crop="Tomato", disease="Leaf Mold", management="x", prevention="y",
                                              expert_name="n") is None
