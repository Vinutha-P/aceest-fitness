"""SQLite database helpers for ACEest Fitness & Gym.

The connection is bound to the Flask application context so that each
request gets its own connection and it is closed automatically when the
request context tears down.
"""
import sqlite3

import click
from flask import current_app, g


def get_db():
    """Return the SQLite connection for the current application context."""
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exc=None):
    """Close the database connection if one was opened."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    age INTEGER,
    height REAL,
    weight REAL,
    program TEXT,
    calories INTEGER,
    target_weight REAL,
    target_adherence INTEGER,
    membership_status TEXT DEFAULT 'Active',
    membership_end TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    date TEXT NOT NULL,
    workout_type TEXT NOT NULL,
    duration_min INTEGER NOT NULL,
    notes TEXT,
    FOREIGN KEY (client_name) REFERENCES clients (name)
);

CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    week TEXT NOT NULL,
    adherence INTEGER NOT NULL,
    FOREIGN KEY (client_name) REFERENCES clients (name)
);
"""


def init_db():
    """Create all tables if they do not yet exist and seed baseline data."""
    db = get_db()
    db.executescript(SCHEMA)
    seed(db)
    db.commit()


def seed(db):
    """Insert a small amount of reference data when the tables are empty."""
    if db.execute("SELECT COUNT(*) FROM clients").fetchone()[0] == 0:
        db.executemany(
            """
            INSERT INTO clients (name, age, height, weight, program, calories,
                                 target_weight, target_adherence, membership_status,
                                 membership_end)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("Arjun Mehta", 28, 178.0, 84.5, "Fat Loss (FL)", 2000,
                 75.0, 80, "Active", "2026-12-31"),
                ("Priya Sharma", 24, 165.0, 58.0, "Muscle Gain (MG)", 3200,
                 62.0, 85, "Active", "2026-10-15"),
            ],
        )

    if db.execute("SELECT COUNT(*) FROM workouts").fetchone()[0] == 0:
        db.executemany(
            """
            INSERT INTO workouts (client_name, date, workout_type, duration_min, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("Arjun Mehta", "2026-09-28", "Strength", 60, "Back Squat 5x5"),
                ("Arjun Mehta", "2026-09-30", "Cardio", 35, "Tempo run"),
                ("Priya Sharma", "2026-09-29", "Hypertrophy", 55, "Bench Press 4x10"),
            ],
        )

    if db.execute("SELECT COUNT(*) FROM progress").fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO progress (client_name, week, adherence) VALUES (?, ?, ?)",
            [
                ("Arjun Mehta", "W1", 62),
                ("Arjun Mehta", "W2", 71),
                ("Arjun Mehta", "W3", 80),
                ("Priya Sharma", "W1", 74),
                ("Priya Sharma", "W2", 85),
            ],
        )


@click.command("init-db")
def init_db_command():
    """Flask CLI command: ``flask --app app init-db``."""
    init_db()
    click.echo("Initialised the database.")


@click.command("seed-db")
def seed_db_command():
    """Flask CLI command: ``flask --app app seed-db``."""
    db = get_db()
    seed(db)
    db.commit()
    click.echo("Seeded the database.")


def register_commands(app):
    """Attach the CLI database commands to the application."""
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_db_command)
