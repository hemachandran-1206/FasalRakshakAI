"""Tiny idempotent schema upgrades for databases created by an earlier phase (create_all never alters tables).
Replace with Alembic once the schema stabilises."""
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from .models import Detection
from .services import cases


def ensure_schema(engine) -> None:
    insp = inspect(engine)
    cols = {c["name"] for c in insp.get_columns("detections")}
    with engine.begin() as conn:
        for name, ddl in (("case_code", "VARCHAR(12)"), ("triage", "JSON")):     # columns added after the first release
            if name not in cols:
                conn.execute(text(f"ALTER TABLE detections ADD COLUMN {name} {ddl}"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_detections_case_code ON detections (case_code)"))
    with Session(engine) as db:      # give pre-existing detections a code
        for det in db.query(Detection).filter(Detection.case_code.is_(None)).all():
            det.case_code = cases.unique_code(db)
            db.flush()
        db.commit()
