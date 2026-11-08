import io
import uuid

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import db as dbmod
from app.main import app
from app.models import Detection, ExpertReview, ReviewHistory, User
from app.services import security

PW = "correct-horse-battery"


def make_user(email, role, name=None):
    with dbmod.SessionLocal() as s:
        u = User(email=email, role=role, full_name=name or email.split("@")[0], password_hash=security.hash_password(PW))
        s.add(u); s.commit()
        return u.id


def make_review(conf=40.0, crop="Tomato", disease="Early Blight", with_image=False, tmp_path=None):
    with dbmod.SessionLocal() as s:
        path = "x"
        det_id = uuid.uuid4()
        if with_image:
            path = str(tmp_path / f"{det_id}.jpg"); Image.new("RGB", (8, 8), "green").save(path)
        d = Detection(id=det_id, image_path=path, crop=crop, disease=disease, confidence=conf, top_k=[], pests=[],
                      care_status="escalated", latitude=30.97123, longitude=76.52456)
        d.review = ExpertReview(status="pending", needs_attention=True)
        d.review.history.append(ReviewHistory(action="created", to_status="pending"))
        s.add(d); s.commit()
        return d.review.id


def login(c, email, password=PW):
    r = c.post("/api/auth/login", data={"username": email, "password": password})
    return r


def auth(c, email):
    return {"Authorization": f"Bearer {login(c, email).json()['access_token']}"}


@pytest.fixture
def c():
    return TestClient(app)


def test_login_me_wrong_password_and_throttle(c):
    make_user("a@x.org", "admin")
    ok = login(c, "A@X.org ")             # case/space-insensitive email
    assert ok.status_code == 200 and ok.json()["user"]["role"] == "admin"
    assert "password" not in ok.text
    me = c.get("/api/auth/me", headers=auth(c, "a@x.org")).json()
    assert me["email"] == "a@x.org"
    assert login(c, "a@x.org", "wrong").status_code == 401
    assert login(c, "nobody@x.org").status_code == 401
    for _ in range(5):
        login(c, "a@x.org", "wrong")
    assert login(c, "a@x.org").status_code == 429       # locked even with the right password


def test_endpoints_require_the_right_role(c):
    make_user("a@x.org", "admin"); make_user("e@x.org", "expert")
    rid = make_review()
    assert c.get("/api/admin/reviews").status_code == 401
    assert c.get("/api/admin/reviews", headers={"Authorization": "Bearer junk"}).status_code == 401
    assert c.get("/api/admin/reviews", headers=auth(c, "e@x.org")).status_code == 403
    assert c.get("/api/expert/reviews", headers=auth(c, "a@x.org")).status_code == 403
    assert c.get(f"/api/reviews/{rid}/image").status_code == 401
    assert c.get("/api/admin/reviews", headers=auth(c, "a@x.org")).status_code == 200


def test_admin_creates_experts_with_validation(c):
    make_user("a@x.org", "admin"); h = auth(c, "a@x.org")
    body = {"email": "New@Lab.org", "full_name": "Dr New", "password": "longenough-pass"}
    r = c.post("/api/admin/experts", json=body, headers=h)
    assert r.status_code == 201 and r.json()["role"] == "expert" and r.json()["email"] == "new@lab.org"
    assert c.post("/api/admin/experts", json=body, headers=h).status_code == 409
    assert c.post("/api/admin/experts", json={**body, "email": "z@z.org", "password": "short"}, headers=h).status_code == 422
    assert login(c, "new@lab.org", "longenough-pass").status_code == 200
    assert [e["email"] for e in c.get("/api/admin/experts", headers=h).json()] == ["new@lab.org"]


def test_full_workflow_correct_and_history(c, tmp_path):
    make_user("a@x.org", "admin", "Admin A"); eid = make_user("e@x.org", "expert", "Dr E")
    rid = make_review(with_image=True, tmp_path=tmp_path)
    ha, he = auth(c, "a@x.org"), auth(c, "e@x.org")
    q = c.get("/api/admin/reviews?status=pending&needs_attention=true", headers=ha).json()
    assert len(q) == 1 and q[0]["ai_disease"] == "Early Blight"
    assert c.get("/api/expert/reviews", headers=he).json() == []                 # nothing assigned yet
    assert c.get(f"/api/admin/reviews/{rid}", headers=ha).json()["latitude"] == 30.97123   # admin: exact GPS

    a = c.post(f"/api/admin/reviews/{rid}/assign", json={"expert_id": str(eid)}, headers=ha)
    assert a.status_code == 200 and a.json()["status"] == "assigned"
    mine = c.get("/api/expert/reviews", headers=he).json()
    assert [m["id"] for m in mine] == [str(rid)]
    d = c.get(f"/api/expert/reviews/{rid}", headers=he).json()
    assert d["latitude"] == 30.97 and d["longitude"] == 76.52                    # expert: rounded GPS
    assert c.get(f"/api/reviews/{rid}/image", headers=he).status_code == 200

    r = c.post(f"/api/expert/reviews/{rid}/decision", headers=he,
               json={"decision": "correct", "crop": "Tomato", "disease": "Septoria Leaf Spot", "notes": "ring spots"})
    assert r.status_code == 200 and r.json()["status"] == "corrected"
    assert r.json()["ai_disease"] == "Early Blight"                               # AI prediction preserved
    assert r.json()["expert_disease"] == "Septoria Leaf Spot"
    assert [(h["action"], h["actor_name"]) for h in r.json()["history"]] == [
        ("created", "System"), ("assigned", "Admin A"), ("corrected", "Dr E")]
    # completed -> locked
    assert c.post(f"/api/expert/reviews/{rid}/decision", headers=he, json={"decision": "confirm"}).status_code == 409
    assert c.post(f"/api/admin/reviews/{rid}/assign", json={"expert_id": str(eid)}, headers=ha).status_code == 409


def test_confirm_inconclusive_and_correction_rules(c):
    make_user("a@x.org", "admin"); eid = make_user("e@x.org", "expert")
    ha, he = auth(c, "a@x.org"), auth(c, "e@x.org")
    r1, r2, r3 = make_review(), make_review(), make_review()
    for r in (r1, r2, r3):
        c.post(f"/api/admin/reviews/{r}/assign", json={"expert_id": str(eid)}, headers=ha)
    ok = c.post(f"/api/expert/reviews/{r1}/decision", headers=he, json={"decision": "confirm"}).json()
    assert ok["status"] == "confirmed" and ok["expert_disease"] == "Early Blight"
    assert c.post(f"/api/expert/reviews/{r2}/decision", headers=he, json={"decision": "inconclusive"}).status_code == 422
    assert c.post(f"/api/expert/reviews/{r2}/decision", headers=he,
                  json={"decision": "inconclusive", "notes": "photo too blurry"}).json()["status"] == "inconclusive"
    bad = {"decision": "correct", "crop": "Tomato"}
    assert c.post(f"/api/expert/reviews/{r3}/decision", headers=he, json=bad).status_code == 422
    same = {"decision": "correct", "crop": "tomato", "disease": "early blight"}
    assert c.post(f"/api/expert/reviews/{r3}/decision", headers=he, json=same).status_code == 422


def test_experts_cannot_touch_each_others_cases_or_unassigned_ones(c, tmp_path):
    make_user("a@x.org", "admin"); e1 = make_user("e1@x.org", "expert"); make_user("e2@x.org", "expert")
    ha, h2 = auth(c, "a@x.org"), auth(c, "e2@x.org")
    rid = make_review(with_image=True, tmp_path=tmp_path)
    assert c.post(f"/api/expert/reviews/{rid}/decision", headers=h2, json={"decision": "confirm"}).status_code == 404
    c.post(f"/api/admin/reviews/{rid}/assign", json={"expert_id": str(e1)}, headers=ha)
    assert c.get(f"/api/expert/reviews/{rid}", headers=h2).status_code == 404
    assert c.get(f"/api/reviews/{rid}/image", headers=h2).status_code == 404
    assert c.post(f"/api/expert/reviews/{rid}/decision", headers=h2, json={"decision": "confirm"}).status_code == 404
    # cannot assign to a non-expert
    admin_id = make_user("a2@x.org", "admin")
    assert c.post(f"/api/admin/reviews/{rid}/assign", json={"expert_id": str(admin_id)}, headers=ha).status_code == 422


def test_reassign_logs_and_verified_reports_feed_hotspots(c):
    make_user("a@x.org", "admin"); e1 = make_user("e1@x.org", "expert"); e2 = make_user("e2@x.org", "expert")
    ha, h2 = auth(c, "a@x.org"), auth(c, "e2@x.org")
    ids = [make_review(conf=90.0, disease="Late Blight", crop="Potato") for _ in range(5)]
    for rid in ids:
        c.post(f"/api/admin/reviews/{rid}/assign", json={"expert_id": str(e1)}, headers=ha)
        d = c.post(f"/api/admin/reviews/{rid}/assign", json={"expert_id": str(e2)}, headers=ha).json()
        assert d["history"][-1]["action"] == "reassigned"
        c.post(f"/api/expert/reviews/{rid}/decision", headers=h2, json={"decision": "confirm"})
    hot = c.get("/api/hotspots").json()["hotspots"]
    assert len(hot) == 1 and hot[0]["verified_count"] == 5 and hot[0]["confirmed"] is True
    ex = {e["email"]: e["open_cases"] for e in c.get("/api/admin/experts", headers=ha).json()}
    assert ex == {"e1@x.org": 0, "e2@x.org": 0}


def test_change_password(c):
    make_user("e@x.org", "expert"); h = auth(c, "e@x.org")
    assert c.post("/api/auth/change-password", headers=h, json={"current_password": "bad", "new_password": "a-new-long-pass"}).status_code == 401
    assert c.post("/api/auth/change-password", headers=h, json={"current_password": PW, "new_password": "short"}).status_code == 422
    assert c.post("/api/auth/change-password", headers=h, json={"current_password": PW, "new_password": "a-new-long-pass"}).status_code == 204
    assert login(c, "e@x.org").status_code == 401 and login(c, "e@x.org", "a-new-long-pass").status_code == 200


def test_timestamps_are_always_utc_labelled(c):
    make_user("a@x.org", "admin"); rid = make_review()
    d = c.get(f"/api/admin/reviews/{rid}", headers=auth(c, "a@x.org")).json()
    assert d["created_at"].endswith(("Z", "+00:00")) and d["history"][0]["created_at"].endswith(("Z", "+00:00"))


def test_expert_corrections_are_stored_with_catalogue_names(c):
    make_user("a@x.org", "admin"); eid = make_user("e@x.org", "expert")
    ha, he = auth(c, "a@x.org"), auth(c, "e@x.org")
    r1, r2 = make_review(), make_review()
    for r in (r1, r2):
        c.post(f"/api/admin/reviews/{r}/assign", json={"expert_id": str(eid)}, headers=ha)
    d1 = c.post(f"/api/expert/reviews/{r1}/decision", headers=he,
                json={"decision": "correct", "crop": " tomato", "disease": "SEPTORIA leaf spot"}).json()
    assert (d1["expert_crop"], d1["expert_disease"]) == ("Tomato", "Septoria Leaf Spot")
    d2 = c.post(f"/api/expert/reviews/{r2}/decision", headers=he,
                json={"decision": "correct", "crop": "Wheat", "disease": "yellow rust (stripe rust)"}).json()
    assert (d2["expert_crop"], d2["expert_disease"]) == ("Wheat", "Yellow Rust (Stripe Rust)")
