"""`python -m app.db.schema_dump` regenerates app/db/schema.sql from the models."""
from app.db.database import SCHEMA_PATH, render_schema_sql

if __name__ == "__main__":
    SCHEMA_PATH.write_text(render_schema_sql(), encoding="utf-8", newline="\n")
    print(f"Wrote {SCHEMA_PATH}")
