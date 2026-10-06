"""Blueprint exposing workout and progress tracking endpoints."""
from flask import Blueprint, jsonify, request

from .db import get_db
from .logic import (
    WORKOUT_TYPES,
    total_workout_minutes,
    weekly_adherence_average,
)

bp = Blueprint("workouts", __name__, url_prefix="/api")


def _client_exists(name):
    return get_db().execute(
        "SELECT 1 FROM clients WHERE name = ?", (name,)
    ).fetchone() is not None


@bp.post("/workouts")
def create_workout():
    """Log a workout for an existing client."""
    payload = request.get_json(silent=True) or {}
    errors = {}

    client_name = (payload.get("client_name") or "").strip()
    if not client_name:
        errors["client_name"] = "client_name is required."

    workout_type = (payload.get("workout_type") or "").strip()
    if workout_type not in WORKOUT_TYPES:
        errors["workout_type"] = (
            f"workout_type must be one of: {', '.join(WORKOUT_TYPES)}."
        )

    duration = payload.get("duration_min")
    try:
        duration_int = int(duration)
        if duration_int <= 0:
            errors["duration_min"] = "duration_min must be greater than zero."
    except (TypeError, ValueError):
        errors["duration_min"] = "duration_min must be a number."
        duration_int = None

    if not errors and not _client_exists(client_name):
        return jsonify({"errors": {"client_name": "Unknown client."}}), 404

    if errors:
        return jsonify({"errors": errors}), 400

    db = get_db()
    db.execute(
        """
        INSERT INTO workouts (client_name, date, workout_type, duration_min, notes)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            client_name,
            (payload.get("date") or "").strip(),
            workout_type,
            duration_int,
            (payload.get("notes") or "").strip() or None,
        ),
    )
    db.commit()

    return jsonify({"message": "Workout logged.", "client_name": client_name}), 201


@bp.get("/workouts")
def list_workouts():
    """List workouts, optionally filtered by ``?client_name=``."""
    client_name = request.args.get("client_name")
    db = get_db()

    if client_name:
        rows = db.execute(
            """
            SELECT date, workout_type, duration_min, notes
            FROM workouts WHERE client_name = ? ORDER BY date DESC
            """,
            (client_name,),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT date, workout_type, duration_min, notes FROM workouts ORDER BY date DESC"
        ).fetchall()

    workouts = [dict(row) for row in rows]
    return jsonify(
        {
            "workouts": workouts,
            "count": len(workouts),
            "total_minutes": total_workout_minutes(workouts),
        }
    )


@bp.post("/progress")
def create_progress():
    """Record a weekly adherence figure for a client."""
    payload = request.get_json(silent=True) or {}
    errors = {}

    client_name = (payload.get("client_name") or "").strip()
    week = (payload.get("week") or "").strip()
    if not client_name:
        errors["client_name"] = "client_name is required."
    if not week:
        errors["week"] = "week is required."

    try:
        adherence = int(payload.get("adherence"))
        if not 0 <= adherence <= 100:
            errors["adherence"] = "adherence must be between 0 and 100."
    except (TypeError, ValueError):
        errors["adherence"] = "adherence must be a number."
        adherence = None

    if not errors and not _client_exists(client_name):
        return jsonify({"errors": {"client_name": "Unknown client."}}), 404

    if errors:
        return jsonify({"errors": errors}), 400

    db = get_db()
    db.execute(
        "INSERT INTO progress (client_name, week, adherence) VALUES (?, ?, ?)",
        (client_name, week, adherence),
    )
    db.commit()

    return jsonify({"message": "Progress recorded.", "week": week}), 201


@bp.get("/progress/<string:client_name>")
def get_progress(client_name):
    """Return the adherence history and average for a client."""
    db = get_db()
    rows = db.execute(
        "SELECT week, adherence FROM progress WHERE client_name = ? ORDER BY id",
        (client_name,),
    ).fetchall()

    records = [{"week": r["week"], "adherence": r["adherence"]} for r in rows]
    return jsonify(
        {
            "client_name": client_name,
            "progress": records,
            "average": weekly_adherence_average(
                [(r["week"], r["adherence"]) for r in rows]
            ),
        }
    )
