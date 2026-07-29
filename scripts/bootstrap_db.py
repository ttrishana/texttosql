"""Create roles + database on an existing Postgres you manage yourself.

Use this instead of Docker when pointing at a local install (Postgres.app /
Homebrew) or a cloud Postgres (Neon / Supabase). Give it a SUPERUSER (or
role-and-db-creating) connection URL; role names / passwords / db name are taken
from ADMIN_DATABASE_URL and READONLY_DATABASE_URL in your .env.

    python scripts/bootstrap_db.py "postgresql://postgres:pw@localhost:5432/postgres"

Then:  python scripts/init_db.py    (loads schema + data as the admin role)

For an embedded, zero-install Postgres instead, set EMBEDDED_DB=true and just run
init_db.py — no superuser URL needed.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from texttosql.db.bootstrap import bootstrap_from_settings  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    bootstrap_from_settings(sys.argv[1])
    print("Roles + database ready. Next: python scripts/init_db.py")


if __name__ == "__main__":
    main()
