"""Insert clearly-marked DEMO reports around Ropar so the hotspot map has something to show.
    python scripts/seed_demo.py          # add demo data
    python scripts/seed_demo.py --clear  # remove ONLY the demo rows (image_path = 'demo://seed')
Demo rows are fake. Never use them as evidence; clear them before real testing or submission."""
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db import Base, SessionLocal, engine   # noqa: E402
from app.models import Detection, ExpertReview, ReviewHistory   # noqa: E402
from app.migrations import ensure_schema   # noqa: E402
from app.services import cases   # noqa: E402

MARK = "demo://seed"
CLUSTERS = [  # crop, disease, centre lat/lon, n reports
    ("Potato", "Late Blight", 30.97, 76.52, 7),      # -> hotspot
    ("Tomato", "Early Blight", 30.99, 76.55, 5),     # -> hotspot (exactly at threshold)
    ("Tomato", "Late Blight", 31.30, 76.80, 3),      # below threshold -> plain markers
]


def main():
    Base.metadata.create_all(engine)
    ensure_schema(engine)
    with SessionLocal() as db:
        deleted = [d for d in db.query(Detection).filter_by(image_path=MARK)]
        for d in deleted:
            if d.review:
                db.query(ReviewHistory).filter_by(review_id=d.review.id).delete()
                db.delete(d.review)
            db.delete(d)
        db.commit()
        if "--clear" in sys.argv:
            print(f"removed {len(deleted)} demo detections"); return
        rnd, now = random.Random(7), datetime.now(timezone.utc)
        n = 0
        for crop, disease, lat, lon, count in CLUSTERS:
            for _ in range(count):
                det = Detection(case_code=cases.unique_code(db), image_path=MARK, crop=crop, disease=disease, confidence=round(rnd.uniform(60, 95), 1),
                                top_k=[], pests=[], care_status="diagnosed",
                                latitude=lat + rnd.uniform(-0.02, 0.02), longitude=lon + rnd.uniform(-0.02, 0.02),
                                created_at=now - timedelta(hours=rnd.uniform(1, 150)))
                det.review = ExpertReview(status="pending")
                db.add(det); n += 1
        db.commit()
        print(f"added {n} demo detections (clear with --clear)")


if __name__ == "__main__":
    main()
