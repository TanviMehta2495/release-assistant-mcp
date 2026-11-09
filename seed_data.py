"""Creates a small SQLite database of sample releases for the Release Assistant MCP server."""
import sqlite3
from pathlib import Path

RELEASES = [
    # service, version, status, tests_passed, change_ticket, error_budget_remaining_pct
    ("checkout-api", "2.4.0", "in_review", 1, "CHG-1042", 38.5),
    ("payments-service", "1.9.3", "in_review", 0, "CHG-1043", 61.0),
    ("search-api", "3.1.0", "planned", 1, None, 12.0),
    ("inventory-sync", "5.0.2", "in_review", 1, "CHG-1045", -4.0),
    ("web-frontend", "8.2.1", "deployed", 1, "CHG-1039", 72.3),
]
APPROVALS = [("checkout-api", "Priya"), ("checkout-api", "Marcus"), ("payments-service", "Priya"),
             ("inventory-sync", "Marcus"), ("inventory-sync", "Lena"), ("web-frontend", "Lena"),
             ("web-frontend", "Priya")]


def seed(db_path: Path) -> None:
    db_path = Path(db_path)
    db_path.unlink(missing_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript("""
            CREATE TABLE releases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT NOT NULL,
                version TEXT NOT NULL,
                status TEXT NOT NULL,
                tests_passed INTEGER NOT NULL,
                change_ticket TEXT,
                error_budget_remaining_pct REAL NOT NULL
            );
            CREATE TABLE approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                release_id INTEGER NOT NULL REFERENCES releases(id),
                approver TEXT NOT NULL
            );
        """)
        conn.executemany(
            "INSERT INTO releases (service, version, status, tests_passed, change_ticket, error_budget_remaining_pct) "
            "VALUES (?, ?, ?, ?, ?, ?)", RELEASES)
        ids = dict(conn.execute("SELECT service, id FROM releases").fetchall())
        conn.executemany("INSERT INTO approvals (release_id, approver) VALUES (?, ?)",
                         [(ids[s], a) for s, a in APPROVALS])


if __name__ == "__main__":
    path = Path(__file__).parent / "releases.db"
    seed(path)
    print(f"Seeded {path}")
