"""Advisory workflow helper.
  python scripts/advisories_tool.py seed-english        # copy the built-in English knowledge base into the table (as drafts)
  python scripts/advisories_tool.py export out.csv      # template: every built-in disease x en/hi/pa, fill the blanks
  python scripts/advisories_tool.py import in.csv       # load translated rows (as drafts)
  python scripts/advisories_tool.py verify --language hi [--yes]   # verify all drafts of a language after review
Drafts are never shown to farmers. Verify only text a qualified person has read."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models import Advisory, User  # noqa: E402
from app.services import advisories, treatments  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["seed-english", "export", "import", "verify"])
    ap.add_argument("path", nargs="?")
    ap.add_argument("--language")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if a.cmd == "seed-english":
            n = 0
            for e in treatments._BUILTIN.values():
                if not advisories._find(db, e["plant"], e["disease"], "en"):
                    advisories.upsert(db, crop=e["plant"], disease=e["disease"], language="en", management=e["recommendation"],
                                      prevention=e["cultural_practice"], source="FasalRakshak built-in knowledge base")
                    n += 1
            db.commit()
            print(f"seeded {n} English drafts")
        elif a.cmd == "export":
            Path(a.path or "advisories.csv").write_text(advisories.export_csv(db), encoding="utf-8")
            print("written", a.path or "advisories.csv")
        elif a.cmd == "import":
            print(advisories.import_csv(db, Path(a.path).read_text(encoding="utf-8")))
            db.commit()
        else:
            drafts = list(db.scalars(select(Advisory).where(Advisory.verification_status == "draft",
                                                            *([Advisory.language == a.language] if a.language else []))))
            admin = db.scalar(select(User).where(User.role == "admin"))
            if not admin:
                sys.exit("create an admin first (scripts/create_admin.py)")
            print(f"{len(drafts)} drafts to verify")
            if not a.yes and input("Have these been reviewed by a qualified person? type 'yes': ") != "yes":
                sys.exit("aborted")
            for d in drafts:
                try:
                    advisories.verify(db, d, admin)
                except ValueError as e:
                    print("skip", d.crop, d.disease, d.language, e)
            db.commit()


if __name__ == "__main__":
    main()
